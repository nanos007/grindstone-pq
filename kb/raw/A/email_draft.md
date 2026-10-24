# Draft email to Kudinov & Nick (not sent; for owner review)

**To:** Mikhail Kudinov, Jonas Nick
**Subject:** Measured grinding costs for your hash-based signature parameters (+ 5 short questions)

Dear Mikhail, dear Jonas,

I'm not a cryptographer, just an engineer who wanted to do something useful with his GPU for Bitcoin's
quantum question. Your paper (ePrint 2025/2203) and the SPHINCS-Parameters scripts made that possible.

I measured how long grinding actually takes for the WOTS+C, FORS+C and PORS+FP rows: 11.16 million grinds on a
45 W laptop GPU, each checked against a reference implementation. Your analytic means hold to within 2 %, and
the tails are geometric. Everything is public as a work in progress, with the draft paper (PDF), data and code:
https://grindstone-pq.vercel.app

If any of it is useful to you, I'd be glad. I had to choose some byte-level details myself, so I have five short
questions. A one-word answer is plenty, and no reply is fine too:

1. **H_msg cost.** With the FIPS 205 SHA-2 construction I count 6 compressions per R-grinding attempt, not 4 as in
   costs.sage. Is 4 intended (a single-SHA-256 H_msg)?
2. **|R|.** 16 bytes (repo) or 32 bytes (paper tables)?
3. **WOTS+C counter.** Does the 4-byte big-endian counter go after m, and which ADRS type should be used?
4. **FORS+C.** Is "last a bits are zero" the last a-bit chunk of md, i.e. base_2b(md, a, k)[k−1] = 0?
5. **z = 1.** My smallest GPU-signer sets zero one chain at w = 256. I read the SPHINCS+C proofs as covering
   general z, provided the verifier checks the zeroed chain. Is that right? Until I hear from you, those sets are
   labelled "measured, not endorsed".

I'll correct the draft based on your answers. Thank you for the paper and the scripts.

Best regards,
Georgios Nanos
georgios.nanos@rwth-aachen.de
