"""
GRINDSTONE / Agent E -- "Fee & Weight Accountant"
=================================================

Translate post-quantum (PQ) signature bytes into Bitcoin weight units (WU),
virtual bytes (vB) and fees (sats).  Plain Python 3, standard library only.

Consensus accounting rules (primary sources)
--------------------------------------------
[BIP141]  github.com/bitcoin/bips/blob/master/bip-0141.mediawiki, "Transaction size
          calculations":  weight = base_size * 3 + total_size;
          vsize = ceil(weight / 4).
          => every non-witness byte costs 4 WU, every witness byte costs 1 WU.
          The segwit marker+flag (2 bytes) are witness data (1 WU each).
[BIP144]  witness serialization: per input, CompactSize(item count), then per item
          CompactSize(len) || bytes.
[BIP341]  P2TR control block = 33 + 32*m bytes (m = Merkle depth, 0..128).
[BIP342]  "Resource limits": "The existing limit of maximum 520 bytes per stack
          element remains, both in the initial stack and in push opcodes."
          and: "Since OP_SUCCESSx precedes size check of initial stack and push
          opcodes, an OP_SUCCESSx-derived opcode requiring stack elements bigger than
          520 bytes may uplift the limit in a softfork."
          Bitcoin Core src/script/interpreter.cpp ExecuteWitnessScript:
          "OP_SUCCESSx processing overrides everything, including stack element size
          limits"; MAX_SCRIPT_ELEMENT_SIZE = 520 (src/script/script.h).
          Policy: MAX_STANDARD_TAPSCRIPT_STACK_ITEM_SIZE = 80 (src/policy/policy.h)
          applies only to leaf version 0xc0 spends that do not hit OP_SUCCESSx
          (OP_SUCCESSx itself is non-standard until a soft fork defines it).
[BIP360]  P2MR (v0.12.1, bips master c0c5aea): output = OP_2 OP_PUSHBYTES_32 <merkle
          root> (34-byte scriptPubKey, SegWit v2).  Witness = initial stack ||
          leaf script || control block; control block = 1 + 32*m bytes (no internal
          key).  Depth-0 trees are anyone-can-spend, so m >= 1 in practice.
          Reference: "P2MR witness for a depth-1 tree (135 bytes)" with a 64-byte
          Schnorr sig, 34-byte leaf script <PUSH32 pk> OP_CHECKSIG, 33-byte control
          block; general case 103 + 32*m bytes.

Modelling assumptions for a PQ spend (all overridable)
------------------------------------------------------
A1  The PQ signature is a single witness stack element of `sig_bytes` bytes
    (no extra sighash-type byte unless the caller adds it to sig_bytes).
    Any sig > 520 B is only consensus-valid if the future PQ opcode is an
    OP_SUCCESSx-derived opcode that uplifts the 520-byte stack-element limit
    (BIP342 footnote above) or a new leaf version.  BIP-360 (Delving post
    2025-07-07, E. Heilman) plans PQ verification via OP_SUCCESSx
    ("OP_CHECKMLSIG"-style), "No new tapleaf version needed".  Weight accounting
    is identical either way: the element is witness data at 1 WU/byte plus its
    CompactSize prefix (3 bytes for 253..65535 bytes).
A2  Leaf script = <OP_PUSHBYTES_32 pk32> <OP_PQCHECKSIG>  = 34 bytes.  A 32-byte PQ
    public key matches SPHINCS+/SLH-DSA at n = 16 (PK.seed || PK.root) as used by
    Kudinov-Nick (ePrint 2025/2203).  Same shape as BIP-360's 34-byte Schnorr leaf.
A3  P2MR control block at depth m = 1: 1 + 32*1 = 33 bytes (BIP-360 default
    example).  Pass control_block_bytes=33+32*m for P2TR comparisons.
A4  No annex.  Input non-witness part = outpoint 36 + scriptSig len 1 + sequence 4
    = 41 bytes (164 WU).
A5  Typical spend: 1 input, 2 outputs, both P2MR (8 value + 1 len + 34 script =
    43 bytes each); version 4, locktime 4, segwit marker+flag 2 (witness).
A6  Per-input deltas are reported as exact WU/4 (may be fractional, e.g. 77.5 vB);
    whole-tx vsize uses ceil() as in BIP141.  Fees = vsize * feerate, no rounding
    to policy minima.  Tapscript sigops do not count toward BIP141 sigop-adjusted
    vsize (BIP342), so vsize == ceil(weight/4).
A7  Different schemes may have different public-key sizes; the delta functions
    keep the pubkey constant (32 B) unless told otherwise.
"""

from __future__ import annotations

import hashlib
import math
from typing import Dict, Iterable, List, Optional, Sequence

WITNESS_SCALE_FACTOR = 4
MAX_SCRIPT_ELEMENT_SIZE = 520           # consensus, BIP342 / script.h
MAX_STANDARD_TAPSCRIPT_STACK_ITEM_SIZE = 80  # policy, policy.h (leaf 0xc0)

# Defaults (see assumptions A2-A5)
PQ_PUBKEY_BYTES = 32
P2MR_DEPTH = 1
P2MR_SPK_BYTES = 34                      # OP_2 OP_PUSHBYTES_32 <32>
TXIN_NONWITNESS_BYTES = 32 + 4 + 1 + 4   # outpoint, empty scriptSig len, sequence
REFERENCE_FEERATES = (2, 10, 50)         # sat/vB

# Reference PQ signature sizes (bytes) -- Kudinov-Nick, ePrint 2025/2203 (see claims)
REFERENCE_SIGS = {
    "SPHINCS+ (KN) 2^20": 3128,
    "SPHINCS+ (KN) 2^30": 3440,
    "SPHINCS+ (KN) 2^40": 4036,
    "SHRINCS (stateful)": 324,
}


# ---------------------------------------------------------------------------
# Serialization primitives
# ---------------------------------------------------------------------------
def compact_size_len(n: int) -> int:
    """Bytes needed to encode integer n as a Bitcoin CompactSize."""
    if n < 0:
        raise ValueError("negative length")
    if n < 0xFD:
        return 1
    if n <= 0xFFFF:
        return 3
    if n <= 0xFFFFFFFF:
        return 5
    return 9


def witness_item_bytes(n: int) -> int:
    """Serialized size of one witness stack element of n bytes (prefix + data)."""
    return compact_size_len(n) + n


def p2mr_control_block_bytes(depth: int = P2MR_DEPTH) -> int:
    """BIP-360: 1 + 32*m.  (BIP-341 P2TR would be 33 + 32*m.)"""
    if not 0 <= depth <= 128:
        raise ValueError("Merkle depth must be in 0..128")
    return 1 + 32 * depth


def pq_leaf_script_bytes(pubkey_bytes: int = PQ_PUBKEY_BYTES) -> int:
    """<push(pubkey)> <PQ CHECKSIG opcode>.  Push opcode is 1 byte up to 75 bytes,
    OP_PUSHDATA1 (2 bytes) up to 255, OP_PUSHDATA2 (3 bytes) up to 520."""
    if pubkey_bytes <= 75:
        push = 1
    elif pubkey_bytes <= 0xFF:
        push = 2
    else:
        push = 3
    return push + pubkey_bytes + 1


# ---------------------------------------------------------------------------
# Input / transaction sizes
# ---------------------------------------------------------------------------
def pq_input_witness_bytes(
    sig_bytes: int,
    pubkey_bytes: int = PQ_PUBKEY_BYTES,
    leaf_script_bytes: Optional[int] = None,
    control_block_bytes: Optional[int] = None,
    extra_stack_items: Sequence[int] = (),
) -> int:
    """Serialized witness bytes (== WU) of one P2MR script-path input.

    Layout (BIP-360 / BIP-341 script path, no annex):
        CompactSize(#items) || item(sig) || [extra items] || item(leaf script)
        || item(control block)

    Defaults: leaf script = <PUSH pk> OP_PQCHECKSIG (34 B for a 32-B key),
    control block = 1 + 32*1 = 33 B (P2MR depth 1).
    Check: sig_bytes=64 -> 135 B, matching BIP-360's depth-1 Schnorr example.
    """
    if leaf_script_bytes is None:
        leaf_script_bytes = pq_leaf_script_bytes(pubkey_bytes)
    if control_block_bytes is None:
        control_block_bytes = p2mr_control_block_bytes(P2MR_DEPTH)
    items = [sig_bytes, *extra_stack_items, leaf_script_bytes, control_block_bytes]
    return compact_size_len(len(items)) + sum(witness_item_bytes(i) for i in items)


def pq_input_weight(sig_bytes: int, **kw) -> int:
    """Total WU of one P2MR PQ input: 41 non-witness bytes * 4 + witness bytes."""
    return TXIN_NONWITNESS_BYTES * WITNESS_SCALE_FACTOR + pq_input_witness_bytes(sig_bytes, **kw)


def tx_weight(
    n_inputs: int,
    n_outputs: int,
    sig_bytes: int,
    output_script_bytes: int = P2MR_SPK_BYTES,
    **input_kw,
) -> int:
    """Weight of a tx spending n_inputs identical P2MR PQ inputs to n_outputs
    outputs of `output_script_bytes` scriptPubKey (default P2MR, 34 B)."""
    out_bytes = 8 + compact_size_len(output_script_bytes) + output_script_bytes
    base = (
        4                                   # nVersion
        + compact_size_len(n_inputs)
        + n_inputs * TXIN_NONWITNESS_BYTES
        + compact_size_len(n_outputs)
        + n_outputs * out_bytes
        + 4                                 # nLockTime
    )
    witness = 2 + n_inputs * pq_input_witness_bytes(sig_bytes, **input_kw)  # marker+flag
    return base * WITNESS_SCALE_FACTOR + witness


def tx_vbytes(n_inputs: int = 1, n_outputs: int = 2, sig_bytes: int = 3128, **kw) -> int:
    """BIP141 virtual size, ceil(weight/4).  Default: 1-in / 2-out P2MR spend
    (both outputs P2MR, 43 B each).  Example: sig 3128 B -> weight 3751, 938 vB."""
    return math.ceil(tx_weight(n_inputs, n_outputs, sig_bytes, **kw) / WITNESS_SCALE_FACTOR)


def tx_fee_sats(feerate_sat_vb: float, **kw) -> float:
    return tx_vbytes(**kw) * feerate_sat_vb


# ---------------------------------------------------------------------------
# Deltas and tables
# ---------------------------------------------------------------------------
def delta_wu(sig_bytes_a: int, sig_bytes_b: int, **kw) -> int:
    """Per-input weight difference a - b (includes CompactSize prefix change)."""
    return pq_input_witness_bytes(sig_bytes_a, **kw) - pq_input_witness_bytes(sig_bytes_b, **kw)


def delta_vbytes(sig_bytes_a: int, sig_bytes_b: int, **kw) -> float:
    """Per-input vbyte difference (exact, may be fractional)."""
    return delta_wu(sig_bytes_a, sig_bytes_b, **kw) / WITNESS_SCALE_FACTOR


def delta_sats(sig_bytes_a: int, sig_bytes_b: int, feerate_sat_vb: float, **kw) -> float:
    """Per-input fee difference in sats at a given feerate (sat/vB)."""
    return delta_vbytes(sig_bytes_a, sig_bytes_b, **kw) * feerate_sat_vb


def delta_table(
    sig_sizes: Iterable[int],
    baseline: int,
    feerates: Sequence[float] = REFERENCE_FEERATES,
    **kw,
) -> List[Dict]:
    """Rows: sig size vs. baseline -> delta bytes/WU/vB and delta sats per input at
    each feerate; also full 1-in-2-out tx vsize for the larger sig."""
    rows = []
    for s in sig_sizes:
        row = {
            "sig_bytes": s,
            "baseline_bytes": baseline,
            "d_bytes": s - baseline,
            "d_wu": delta_wu(s, baseline, **kw),
            "d_vb": delta_vbytes(s, baseline, **kw),
            "tx_vsize_1in2out": tx_vbytes(1, 2, s),
        }
        for f in feerates:
            row[f"d_sats@{f}"] = delta_sats(s, baseline, f, **kw)
        rows.append(row)
    return rows


def format_table(rows: List[Dict], feerates: Sequence[float] = REFERENCE_FEERATES) -> str:
    hdr = ["sig B", "vs B", "dWU", "dvB"] + [f"dsats@{f}" for f in feerates] + ["tx vB (1in2out)"]
    lines = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    for r in rows:
        cells = [r["sig_bytes"], r["baseline_bytes"], r["d_wu"], f'{r["d_vb"]:g}']
        cells += [f'{r[f"d_sats@{f}"]:g}' for f in feerates] + [r["tx_vsize_1in2out"]]
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Raw transaction weight (for the sanity check against mainnet)
# ---------------------------------------------------------------------------
def _read_cs(b: bytes, i: int):
    x = b[i]
    if x < 0xFD:
        return x, i + 1
    w = {0xFD: 2, 0xFE: 4, 0xFF: 8}[x]
    return int.from_bytes(b[i + 1:i + 1 + w], "little"), i + 1 + w


def parse_tx_sizes(raw_hex: str) -> Dict:
    """Parse a raw (BIP144) transaction and return base/total size, weight, vsize,
    txid (from the stripped serialization) and per-input witness item sizes."""
    b = bytes.fromhex(raw_hex)
    i = 4
    segwit = b[i] == 0 and b[i + 1] != 0
    if segwit:
        i += 2
    body_start = i
    n_in, i = _read_cs(b, i)
    for _ in range(n_in):
        i += 36
        l, i = _read_cs(b, i)
        i += l + 4
    n_out, i = _read_cs(b, i)
    for _ in range(n_out):
        i += 8
        l, i = _read_cs(b, i)
        i += l
    body_end = i
    witnesses = []
    if segwit:
        for _ in range(n_in):
            n_items, i = _read_cs(b, i)
            items = []
            for _ in range(n_items):
                l, i = _read_cs(b, i)
                items.append(l)
                i += l
            witnesses.append(items)
    lock_end = i + 4
    if lock_end != len(b):
        raise ValueError("trailing or missing bytes")
    stripped = b[:4] + b[body_start:body_end] + b[i:lock_end]
    base, total = len(stripped), len(b)
    weight = base * (WITNESS_SCALE_FACTOR - 1) + total
    txid = hashlib.sha256(hashlib.sha256(stripped).digest()).digest()[::-1].hex()
    return {
        "base_size": base,
        "total_size": total,
        "weight": weight,
        "vsize": math.ceil(weight / WITNESS_SCALE_FACTOR),
        "txid": txid,
        "n_in": n_in,
        "n_out": n_out,
        "witness_items": witnesses,
    }


if __name__ == "__main__":
    for base_name, base in [("SHRINCS 324", 324), ("KN 2^20 3128", 3128)]:
        sigs = [s for s in (3128, 3440, 4036) if s != base]
        print(f"\nPer-input deltas vs {base_name} B (P2MR depth 1, 32-B pk):")
        print(format_table(delta_table(sigs, base)))
    print("\n1-in-2-out P2MR tx vsize:", {k: tx_vbytes(1, 2, v) for k, v in REFERENCE_SIGS.items()})
