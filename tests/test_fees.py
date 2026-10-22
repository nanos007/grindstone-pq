"""Sanity checks for kb/fees.py (offline; raw tx hex embedded).

Reference txs (weights/sizes as reported by mempool.space and blockstream.info
APIs, fetched 2026-10-22):

TX_A 37777defed8717c581b4c0509329550e344bdc14ac38f71fc050096887e535c8
     block 709635 (first taproot block); 2 P2TR inputs (0: key path, 1: script path
     <PUSH32 pk> OP_CHECKSIG, depth-1 control block 65 B) -> 1 P2WPKH output.
     Explorer: size 358, weight 727, vsize 182.
TX_B 6fb976ab49dcec017f1e201e84395983204ae1a7c2abf7ced0a85d692e442799
     block 767430 (ordinals inscription #0 reveal); 1 P2TR script-path input with an
     853-byte leaf script (CompactSize 0xfd prefix) and 33-B control block -> 1 P2WPKH.
     Explorer: size 1040, weight 1286, vsize 322 (fee 322 sat).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from kb import fees  # noqa: E402

TX_A_ID = "37777defed8717c581b4c0509329550e344bdc14ac38f71fc050096887e535c8"
TX_A_HEX = (
    "020000000001027bc0bba407bc67178f100e352bf6e047fae4cbf960d783586cb5e430b3b700"
    "e70000000000feffffff7bc0bba407bc67178f100e352bf6e047fae4cbf960d783586cb5e430"
    "b3b700e70100000000feffffff01b4ba0e0000000000160014173fd310e9db2c7e9550ce0f03"
    "f1e6c01d833aa90140134896c42cd95680b048845847c8054756861ffab7d4abab72f6508d67"
    "d1ec0c590287ec2161dd7884983286e1cd56ce65c08a24ee0476ede92678a93b1b180c03407b"
    "5d614a4610bf9196775791fcc589597ca066dcd10048e004cd4c7341bb4bb90cee4705192f3f"
    "7db524e8067a5222c7f09baf29ef6b805b8327ecd1e5ab83ca2220f5b059b9a72298ccbefff5"
    "9d9b943f7e0fc91d8a3b944a95e7b6390cc99eb5f4ac41c0d9dfdf0fe3c83e9870095d67fff5"
    "9a8056dad28c6dfb944bb71cf64b90ace9a7776b22a1185fb2dc9524f6b178e2693189bf0165"
    "5d7f38f043923668dc5af45bffd30a00"
)
TX_B_ID = "6fb976ab49dcec017f1e201e84395983204ae1a7c2abf7ced0a85d692e442799"
TX_B_HEX = (
    "01000000000101586379b362e6d8bbd0f722617e428940da2012357fd8e0eded0be66766da4b"
    "270000000000fdffffff01ce2500000000000016001461c57c484193abbaada4c50538b77d33"
    "c5a18f5f0340152b336f7b6fc69be82df72bb4653eed7e075da88c491c0ad76451fcf0514dd6"
    "67702aabdeca72cea1427124fc511da6d9ffb43b7e32b908fcef169b19dfc1f6fd5503204a3c"
    "a2cf35f7902df1215f823d977df1174048b062e03a44f71c2ee736a60cc5ac0063036f726401"
    "0109696d6167652f706e67004d080289504e470d0a1a0a0000000d4948445200000064000000"
    "6401030000004a2c071700000006504c5445ffffff00000055c2d37e000002ce4944415438cb"
    "95d44b6813411807f0944a13105d14b4146916c1b33d150b7d2ce45ab027295a4b0e1e4a5b4a"
    "2b4512fac8563c78509abb68051151aacda1600b4db2a1789162021e046d934dc921859addc4"
    "906c92dd9dbf21333b01c143e7f6e39bef3133ecbaceb824acb5d109d4da12b22ed2d68808a1"
    "bdb50e94b33ccd006c9ee8d624ac5b8ec4b4aa0464deed50559665a78cacc6ba1539c1044df6"
    "27c18a76a8a5c668090bac4118440719600dc2a8164086a804d5ac544c84984a5aa1aa950895"
    "f7260a556861aade5fea5c559d0d304da2528131ce4ea76a958a86793a9a9437eb65d302531d"
    "b51cca4c32718de86b02e8d8c13a92b7e5728e2a108031093b4d35370ff31ac80faa19d56dee"
    "59e20c8b45afdb3bc5a79f59dec373abc6974b2c2f985d18361e27584df92013d7234b32d5e0"
    "7ec3ab9f3f59a6b3f487b11191483fd5e02659d7fa1a7b549280f52d898854bd22929a8c6ef6"
    "28e3188bfb6d3f9520226dc8f03209782d4a84c9bd495e197d8d28bf794554c810d37e43c2b3"
    "9315a683cc6a776ac95176c1368e131653b0d3dcab751e51758d08a64984e72c26c3e8058eb8"
    "aa17b80419bfdf01192a11f8b92d035412b07d5781f32a32c9dfd7a1d25b5a8599d496615019"
    "0a36744d110109b16c4b960ad12f62aaa58ed371e2f78fd9f78a2d99776aaaf2a0324165a97f"
    "52f1694c5141a94e45bf41a13ac5ce624f5a69b4e4aa92ef4ba35fe70bb4437d73a0789c7bb1"
    "4d155a216e4bc8a7d86b3ed16d83d4242a0965d3ac3b6710b0928fe655c26e8228cd39231655"
    "0751888e48d1f9fc5244278b59a65b01a2dbe935a69ed4e1446891c1e58ddf781b8e38ba183b"
    "34035b8e041940860b0008dfa9787c22dfe90e1ab1dc1157e0657eb8ad398fef6a5bd31edfe5"
    "ffc5748fcf6b71cd020d1eebfad0ccfbc8f5a999c7e57ee4f15d6957319add7995cedde664bb"
    "5c684e5d73d4a103a4e8c8650266962bf4e67d24c125dae3f8e73f78b6f5177fb5c56a2d73fc"
    "4b0000000049454e44ae4260826821c04a3ca2cf35f7902df1215f823d977df1174048b062e0"
    "3a44f71c2ee736a60cc500000000"
)


@pytest.mark.parametrize(
    "raw,txid,size,weight,vsize",
    [
        (TX_A_HEX, TX_A_ID, 358, 727, 182),
        (TX_B_HEX, TX_B_ID, 1040, 1286, 322),
    ],
)
def test_mainnet_weight_matches_explorer(raw, txid, size, weight, vsize):
    r = fees.parse_tx_sizes(raw)
    assert r["txid"] == txid          # proves the stripped serialization is right
    assert r["total_size"] == size
    assert r["weight"] == weight
    assert r["vsize"] == vsize


def test_model_reproduces_real_p2tr_script_path_input():
    """Our input model, with a P2TR control block (33+32m), must reproduce the
    witness bytes of the real script-path input in TX_A (64-B sig, 34-B leaf)."""
    r = fees.parse_tx_sizes(TX_A_HEX)
    items = r["witness_items"][1]
    assert items == [64, 34, 65]
    real = 1 + sum(fees.witness_item_bytes(n) for n in items)
    assert real == 167
    assert fees.pq_input_witness_bytes(64, control_block_bytes=33 + 32 * 1) == real
    # Rebuild the whole tx weight from the model: key-path input (66 B witness),
    # script-path input (167 B), one P2WPKH output (22-B spk).
    base = 4 + 1 + 2 * 41 + 1 + (8 + 1 + 22) + 4
    wit = 2 + (1 + 65) + fees.pq_input_witness_bytes(64, control_block_bytes=65)
    assert base * 4 + wit == 727


def test_model_reproduces_inscription_reveal():
    r = fees.parse_tx_sizes(TX_B_HEX)
    assert r["witness_items"][0] == [64, 853, 33]
    model = fees.pq_input_witness_bytes(64, leaf_script_bytes=853, control_block_bytes=33)
    base = 4 + 1 + 41 + 1 + (8 + 1 + 22) + 4
    assert base * 4 + 2 + model == 1286


def test_bip360_reference_sizes():
    # BIP-360 "P2MR witness for a depth-1 tree (135 bytes)" and general 103+32m.
    assert fees.pq_input_witness_bytes(64) == 135
    for m in range(1, 7):
        assert fees.pq_input_witness_bytes(
            64, control_block_bytes=fees.p2mr_control_block_bytes(m)) == 103 + 32 * m


def test_compact_size():
    assert [fees.compact_size_len(n) for n in (0, 252, 253, 0xFFFF, 0x10000, 2**32)] == [1, 1, 3, 3, 5, 9]


def test_pq_examples():
    assert fees.pq_input_witness_bytes(3128) == 1 + 3 + 3128 + 35 + 34
    assert fees.tx_weight(1, 2, 3128) == 137 * 4 + 2 + 3201
    assert fees.tx_vbytes(1, 2, 3128) == 938
    assert fees.delta_wu(3128, 324) == 2804
    assert fees.delta_vbytes(3440, 3128) == 78
    assert fees.delta_sats(4036, 324, 50) == 46400
    # crossing the 253-byte CompactSize boundary adds 2 WU
    assert fees.delta_wu(253, 252) == 3
