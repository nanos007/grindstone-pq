# bitcoindev / Delving Bitcoin post (DRAFT, not sent)

Fill in `[repo link]` before sending. Do not post before the Kudinov/Nick email has been answered or
deliberately skipped (threats §2.1), and before the z = 1 caveat is settled (threats §1.2).

```
Subject: Empirical grinding tails for WOTS+C/FORS+C/PORS+FP at 2^20-2^40 sig limits (data + CUDA)

1/ Ran 11.16M reference-verified grinds (10^5-10^6 per config, 37 configs) over Kudinov-Nick's SPHINCS-Parameters
   frontier on an RTX 4050 Laptop @ 45 W; means match 1/p within 1.7%, tails are textbook geometric
   (p99.9 = 6.73-7.05x mean vs 6.91 theory).
2/ So wallets should design for ~7x the mean grind, not the mean. But grinding is <= 18% of signing work
   (tree building dominates), so full-signing p99 for the hw-wallet-safe sets is ~2-3 min on a Cortex-M4
   (cited rate), ~25 ms on SHA-NI, ~3 ms on the GPU.
3/ Under FIPS 205's SHA-2 H_msg/PRF_msg, a FORS+C R-grind attempt is 6 compressions and PORS+FP 7, not the
   4 in costs.sage; the counter-in-H_msg layout is 3 and runs 2.1x faster on GPU (but stores 4 bytes).
4/ Frontier: a heavy-signer set is 596-1,052 B (149-263 vB per input, 17-23% of a 1-in/2-out spend) smaller
   than a hw-wallet-safe one; verification gets cheaper, never dearer. That is the "relative performance"
   gmaxwell said the one-vs-two-parameter-sets question depends on. (Smallest sets use z=1; caveats in repo.)
5/ Repo, parquet, `python -m runner.reproduce`: [repo link]. Happy to rerun any (h,d,a,k,w,S,z) you want.
```
