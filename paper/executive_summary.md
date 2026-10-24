# GRINDSTONE: executive summary (DRAFT 2026-10-24)

**What.** We measured on commodity hardware how much signing work buys how many bytes in the hash-based
post-quantum signatures being considered for Bitcoin (Kudinov–Nick's SPHINCS+ variants with WOTS+C,
FORS+C and PORS+FP).

**Why it matters.** Bitcoin will likely need a quantum-safe signature within years, not decades. The
signature's size sets the fee of every future transaction that uses it, and its signing cost decides whether
hardware wallets can use it.

**Key findings.**
1. **The analytic models are accurate.** 11.16 million verified grinds: every mean within 2 % of the
   analytic value, and the distribution shape matches too.
2. **The worst case in 1,000 signatures takes about 7× the average grind** (p99.9 = 6.73–7.05× the mean).
   Wallets should budget for that, with a progress bar rather than a timeout at the mean. Because tree
   building dominates signing, the full signing time varies much less.
3. **A GPU-class or desktop signer saves 596–1,052 bytes per signature** against a hardware-wallet-safe set:
   149–263 vB, or 1,490–2,630 sats per input at 10 sat/vB (17–23 % of a simple payment). A laptop CPU with a
   1-second budget already gets 372–728 bytes of that.
4. **The standard cost model under-prices one design choice.** Under the NIST (FIPS 205) hash construction,
   each FORS+C/PORS+FP grinding attempt costs 6–7 hash compressions, not 4. Storing a 4-byte counter instead
   halves FORS+C grinding.
5. **Nodes never pay.** Verification cost goes down, never up, at every point.

**Recommendation.** The PQ-signature BIP should state its signer-hardware assumption explicitly and consider
two named parameter profiles ("hardware-wallet-safe" and "heavy signer") rather than one set or a free menu.

**Caveats.**
- The smallest "heavy signer" sets force one WOTS chain to zero (z = 1); their security needs a
  cryptographer's sign-off before anyone recommends them. The SPHINCS+C proofs are stated for general z,
  so the open point is narrow: independent review, plus a verifier that checks the zeroed chain.
- Hardware-wallet timings use published chip speeds, not our own measurements.

**Artifacts.** Open-source GPU grinder, dataset (CC-BY-4.0) and one-command reproduction:
`python -m runner.reproduce`.
