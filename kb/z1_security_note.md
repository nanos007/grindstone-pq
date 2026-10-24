# z = 1 security note (threats §1.2): prepared for sign-off

Status: **draft argument, not a sign-off.** Prepared 2026-10-24 for the owner and a reviewing cryptographer.
It answers the open question in threats §1.2: "SPHINCS+C defines forced-zero chains; we have not checked
that its security argument covers this exact parameterization."

Affected shortlist points (all `w = 256, S = 1912, z = 1`, 15 of 16 chains kept, −16 B per layer):
`L20-…-h24d2-k7a18-…-m94`, `L20-…-h32d2-k11a10-…-m68`, `L30-…-h33d3-k8a16-…-m94`, `L30-…-h32d2-k7a19-…-m96`,
`L40-…-h48d4-k9a13-…-m82`, `L40-…-h48d3-k9a13-…-m77` (`gpu_signer_moderate` / `gpu_signer_max`).

## 1. What the source proves

SPHINCS+C (Hülsing–Kudinov–Ronen–Yogev, ePrint 2022/778, v. 2022-09-14):
- **z is a general parameter.** §3: "Our scheme introduces two additional parameters S_{w,n}, z ∈ N." The
  encoding conditions are "1. Fixed sum: Σ_{i=1}^{len1} a_i = S_{w,n}. 2. Additional zero-chains:
  ∀ i ∈ [z] : a_i = 0." The scheme keeps ℓ = len1 − z chains. (H)
- **Verify enforces both conditions.** §3 and §5 Verify, step 5: "Verify that Σ_{i=1}^{len1} a_i = S_{w,n}
  and that ∀ i ∈ [z] : a_i = 0." Note the sum runs over **all len1** digits. (H)
- **The proofs carry z.** Thm B.2 (standalone, m-eTCR), Thm C.2 (EU-naCMA), Thm D.1 (d-EU-naCMA) and Thm 5.2
  (SPHINCS+C EU-CMA) are stated for the scheme as defined, z included. The reduction (Alg. 7) handles the
  forgery as (σ*_1, …, σ*_{len1−z}, s*). Both encoding conditions sit inside the predicate "+C". (H for the
  statements; M that no step silently assumes z = 0. A reader should check this against the PDF.)
- **No bound term depends on z.** Lemma E.4: Succ^{S-TCR(+C)} ≤ 32(q + ½)²/2ⁿ + 16q²/|P|. That term is
  independent of z, S and Pr[+C]. In Thm 5.2 the chain count l enters only the query bounds
  q₁ < 2^{h+1}(kt + l), q₂ < 2^{h+1}·l and q₃ < 2^{h+1}·l·w. Fewer chains make the bound slightly smaller. (H)

**Reading:** z = 1 at w = 256 is an instance of the parameter family that SPHINCS+C's theorems cover, and its
bound is no worse than z = 0. The forgery bits in our shortlist come from the repo's FORS/PORS model, which
has no WOTS+C term (B-022). That is consistent: the WOTS+C contribution is z-independent.

## 2. Why it holds (intuition a reviewer can check)

A WOTS forgery from a signature on digits a requires digits a′ with a′_i ≥ a_i on every chain that is kept.
- Kept chains: the sum over all len1 digits is S, and the z omitted digits are 0. So the kept digits of both
  a and a′ sum to S. Coordinatewise a′ ≥ a with equal sums forces a′ = a.
- So any forgery needs a fresh (m′, count′) whose 128-bit digest is exactly a, a target collision under
  Th+C. That is the S-TCR(+C) term, 2⁻ⁿ per query, the same as at z = 0.

## 3. Conditions the endorsement depends on (for the spec, not for our measurement)

1. **The verifier must bind the omitted digits.** It can check a_i = 0 explicitly, or sum over all len1
   digits as SPHINCS+C does; either suffices, because Σ_all = S together with a′ ≥ a on the kept chains
   forces the omitted digit to 0. **The failure case is a verifier that sums only the ℓ kept digits and
   skips the zero check.** The omitted digit is then free, the forgery target shrinks to 128 − z·lg w =
   120 bits, and security drops by 8 bits (Grover: 2⁶⁰). `costs.py` describes the condition as "remaining
   l summing to S". That is correct for counting probabilities, but it is not a verification rule. The
   GRINDSTONE grinder `ref/wots_c.py:accept` does both checks (mask on the trailing z·lg w bits, and the sum
   over all len1 digits).
2. **Which chains are zeroed is irrelevant to security.** SPHINCS+C zeroes the first z chains and KN the last
   z (ambiguity 2). GRINDSTONE uses the last (trailing bits of d). The argument in §2 is symmetric in
   position, so the choice matters for interoperability and test vectors only. A BIP must fix it.
3. **Tweak uniqueness for the kept chains.** If the ℓ kept chains are renumbered, every remaining chain hash
   still needs a distinct tweak (§5: "each hash invocation uses a different tweak"). This is standard, but
   it has to be in the spec.
4. **KN's instantiation must map onto SPHINCS+C's Th+C.** KN computes d = Th(P, T*_adrs, m‖count). That
   matches the shape of Th+C : P × T × {0,1}ⁿ × {0,1}^r → {0,1}ⁿ. A reviewer should confirm the T* tweak
   is unique per WOTS+C instance (ambiguity 3).
5. **Counter width.** E[tries] ≈ 2^17.5 per layer (B-022). With a 4-byte counter, exhaustion probability is
   (1 − p)^{2³²} ≈ e^{−2^{14.5}}, which is negligible (threats §1.3).

## 4. What still needs a human

- A cryptographer confirms the §1 reading, especially that no step in Alg. 7 / Alg. 9 assumes z = 0. The
  quotes above come from a text extraction of the PDF; check them against the PDF itself.
- The owner decides between the two wordings below.

## 5. Proposed wording (owner chooses one)

**Option A: signed off.** threats §1.2, status → "Low, resolved (conditional)":
> z = 1 is covered by SPHINCS+C's security theorems (ePrint 2022/778, Thms B.2/C.2/D.1/5.2), which define z
> as a general parameter. No bound term depends on z (Lemma E.4). This holds provided the verifier binds the
> omitted digits (explicit zero check, or sum over all len1 digits), kept chains have unique tweaks, and the
> zero-chain position is fixed by the spec. Reviewed by: ____.

paper §7 bullet:
> **z = 1 security (conditional).** Covered by the SPHINCS+C proofs, which bound z-independently. It
> requires the verifier to bind the omitted digit; a verifier that sums only the kept chains loses 8 bits.

executive_summary caveat:
> The smallest "heavy signer" sets force one WOTS chain to zero (z = 1). SPHINCS+C's security proof covers
> this, provided the verifier checks the zeroed chain.

**Option B: no sign-off (current state, unchanged).** Keep "measured, not endorsed" in threats §1.2,
paper §7 and the executive summary, and add one sentence so readers can see why the question is narrow:
> SPHINCS+C's theorems are stated for general z with no z-dependent bound term; what remains is
> independent review and the verifier rule in threats §1.2 / `kb/z1_security_note.md` §3.

## 6. Side finding (not a security issue)

`ref/wots_c.py:success_prob` computes ν(len1, S, w)/w^len1 · 2^{−z_bits}. That is correct for z_b (unused
bits, independent of the digit sum) but wrong for z zero chains, where the zeroed digit is part of the sum
(correct: ν(len1 − z, S, w)/w^len1, as in `costs.py:wots_c_success_prob`). It is only called with
z_bits = 0 (tests). The campaign's analytic values come from `costs.py`, and the z = 1 configs match them.
**Fixed 2026-10-24.** The trailing z_bits now cover unused bits first (z_b), then whole digits (z). A test
checks the result against `costs.py` for z = 1, 2.
