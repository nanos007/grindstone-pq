# Draft email to Kudinov & Nick (not sent; for owner review)

**To:** Mikhail Kudinov, Jonas Nick
**Subject:** Byte-level questions on WOTS+C / FORS+C / PORS+FP grinding (ePrint 2025/2203, SPHINCS-Parameters@ceee8ed)

Dear Mikhail, dear Jonas,

I'm preparing GRINDSTONE, an open measurement of grinding-cost distributions (mean and tails, CPU and consumer GPU) for the WOTS+C, FORS+C and PORS+FP rows in your paper and repo. Everything uses SHA-256 only at n = 16. I'd like the kernels to match what you have in mind, so I have a few short questions. My current defaults are in brackets. A one-word answer to each would already help.

1. **H_msg cost.** costs.sage sets `C_Hmsg = 2`, and §13.2 says a 256-bit digest gives two compression calls. With the FIPS 205 SHA2 construction, MGF1-SHA-256(R‖PK.seed‖SHA-256(R‖PK.seed‖PK.root‖M), m), I count 2 + 2 = 4 for M = 32 B. Adding PRF_msg (HMAC, 2 with cached ipad/opad) gives 6 per R-grinding attempt rather than 4. Did you intend a single-SHA-256 H_msg, or is 4 the right figure? [Default: FIPS 205, so 6 per attempt.]
2. **|R|.** The paper sets the PRF_msg output to 256 bits, and Table 1/2 sizes include a 32-byte R. The repo switched to `randomness_size = 16` in 31e2cdb. Which should we treat as canonical? [16]
3. **WOTS+C tweak and counter.** For Th(P, T*_adrs, m‖count): which ADRS type value should we use, and does the counter go after m (4 bytes, big-endian, starting at 0) or inside the ADRS as in the SPHINCS+C code? The SHRINCS draft uses type 22, a 16-bit counter and alignment padding. [Type 7, keypair = leaf, ADRSc‖m‖ctr4_BE.]
4. **FORS+C zero bits.** Should we read "last a bits" as base_2b(md, a, k)[k−1] = 0, i.e. bits [(k−1)a, ka) of the FIPS 205 digest? The SPHINCS+C code instead checks a separate prefix field. [Yes, the last a-bit chunk of md.]
5. **R-grinding counter.** Where does the counter go in PRF_msg(SK.prf, opt, m, counter)? [HMAC message = opt_rand ‖ M ‖ ctr4_BE.]
6. **PORS+FP with SHA-256 only.** Is a 512-bit H_msg via two MGF1-SHA-256 blocks acceptable? Is τ (the first h bits, Alg. 1) split as idx_tree = τ >> h′? Should the probability of getting fewer than k distinct indices (about 0.1–1.3% for your rows by my count) be in the expected-work figures? [Yes, yes, we will include it.]
7. **Minor.** The zero-chain range in §5, [w−1−z+1, w−1]: did you mean the last z digits, [len1−z+1, len1]? (SPHINCS+C uses the first z.)

I'll share the data and code before anything goes public. Thank you for the paper and the scripts; they made this study possible.

Best regards,
George Nanos
