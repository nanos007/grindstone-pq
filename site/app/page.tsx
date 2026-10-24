import Link from "next/link";
import { ArrowRight, AlertTriangle } from "lucide-react";
import Hero from "@/components/home/Hero";
import SectionBand from "@/components/ui/SectionBand";
import FadeIn from "@/components/ui/FadeIn";
import FeatureCard from "@/components/ui/FeatureCard";
import StatTile from "@/components/ui/StatTile";
import { data } from "@/lib/data";
import { compact } from "@/lib/format";

const h = data.headline;

const findings = [
  {
    title: "The analytic models are accurate",
    body: "Every measured mean is within 2 % of the analytic expectation, and the distributions are geometric down to the 10⁻⁴…10⁻⁶ tail.",
  },
  {
    title: "Budget for 7× the average grind",
    body: "The worst case in 1,000 signatures takes about 7× the mean grind (p99.9 = 6.73–7.05×). Wallets need a progress bar, not a timeout at the mean.",
  },
  {
    title: "Faster signers save 596–1,052 bytes",
    body: "A GPU-class or desktop signer saves 149–263 vB per input against a hardware-wallet-safe set: 17–23 % of a simple payment.",
  },
  {
    title: "The cost model under-prices FIPS 205",
    body: "Under the NIST hash construction a FORS+C/PORS+FP attempt costs 6–7 compressions, not 4. Storing a 4-byte counter halves FORS+C grinding.",
  },
  {
    title: "Nodes never pay",
    body: "Verification cost goes down, never up, at every shortlisted point.",
  },
];

const explore = [
  { title: "Results", body: "Calibration of all 37 grind configs and the OQ-3 overgrinding sweep.", href: "/results/" },
  { title: "Signer explorer", body: "Pick a signer and a time budget; get the smallest signature that fits.", href: "/explorer/" },
  { title: "Method", body: "Kernels, reference checks, hardware and threats to validity.", href: "/method/" },
  { title: "Paper", body: "The full draft with every table, plus the executive summary.", href: "/paper/" },
  { title: "Reproduce", body: "One command re-derives every number from the published dataset.", href: "/reproduce/" },
];

export default function Home() {
  return (
    <>
      <Hero />

      <SectionBand card>
        <FadeIn>
          <h2 className="font-display text-3xl font-normal text-ink mb-10" style={{ letterSpacing: "-0.5px" }}>
            The campaign in numbers
          </h2>
        </FadeIn>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "Grinds, all reference-verified", value: compact(h.samples, 2), note: `${h.configs} configurations serving 40 parameter sets` },
            { label: "Fit to the analytic model", value: `Σz² = ${h.sum_z2.toFixed(1)}`, note: `${h.dof} degrees of freedom, p = 0.36` },
            { label: "Laptop GPU, raw SHA-256", value: `${(h.gpu_raw / 1e9).toFixed(2)} G/s`, note: "RTX 4050 Laptop at 45 W, sustained" },
            { label: "Laptop CPU, SHA-NI", value: `${Math.round(h.cpu_12t / 1e6)} M/s`, note: `12 threads sustained; ${Math.round(h.cpu_1t / 1e6)} M/s on one` },
          ].map((s, i) => (
            <FadeIn key={s.label} delay={i * 0.08}>
              <StatTile {...s} />
            </FadeIn>
          ))}
        </div>
      </SectionBand>

      <SectionBand>
        <FadeIn>
          <p className="text-xs font-medium tracking-widest uppercase text-accent-steel mb-4">Key findings</p>
          <h2 className="font-display text-3xl md:text-4xl font-normal text-ink mb-10 max-w-2xl" style={{ letterSpacing: "-0.5px" }}>
            Signature size is a signer-hardware decision. The BIP should say which.
          </h2>
        </FadeIn>
        <div className="grid md:grid-cols-2 gap-4">
          {findings.map((f, i) => (
            <FadeIn key={f.title} delay={i * 0.06} className={i === findings.length - 1 ? "md:col-span-2" : ""}>
              <FeatureCard className="h-full">
                <p className="text-xs text-muted mb-3" style={{ fontVariantNumeric: "tabular-nums" }}>
                  0{i + 1}
                </p>
                <h3 className="text-base font-medium text-ink mb-2">{f.title}</h3>
                <p className="text-sm text-body leading-relaxed">{f.body}</p>
              </FeatureCard>
            </FadeIn>
          ))}
        </div>
        <FadeIn>
          <p className="text-sm text-body leading-relaxed mt-10 max-w-2xl">
            <span className="font-medium text-ink">Recommendation.</span> State the signer-hardware assumption explicitly and
            consider two named parameter profiles, “hardware-wallet-safe” and “heavy signer”, rather than one set or a free menu.
          </p>
        </FadeIn>
      </SectionBand>

      <SectionBand dark>
        <FadeIn>
          <div className="flex gap-4 items-start max-w-3xl">
            <AlertTriangle size={22} className="text-accent-amber shrink-0 mt-1" aria-hidden />
            <div>
              <h2 className="font-display text-2xl md:text-3xl font-normal text-on-dark mb-4" style={{ letterSpacing: "-0.5px" }}>
                What we do not claim
              </h2>
              <ul className="space-y-3 text-sm text-on-dark-soft leading-relaxed">
                <li>
                  <span className="text-on-dark">The smallest heavy-signer sets are measured, not endorsed.</span> They force one WOTS+C
                  chain to zero (z = 1). The SPHINCS+C proofs are stated for general z, so the open point is narrow: independent
                  review, plus a verifier that checks the zeroed chain.
                </li>
                <li>
                  <span className="text-on-dark">Hardware-wallet timings are derived, not measured.</span> They use published chip
                  speeds; tries remain the primary, hardware-independent metric.
                </li>
                <li>
                  <span className="text-on-dark">One laptop, one run.</span> Conservative by design: a 45 W power cap and no
                  vendor-specific tuning.
                </li>
              </ul>
              <Link href="/method/#threats" className="inline-flex items-center gap-1 text-sm text-primary font-medium mt-6 hover:gap-2 transition-all">
                All threats to validity <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </FadeIn>
      </SectionBand>

      <SectionBand>
        <FadeIn>
          <h2 className="font-display text-3xl font-normal text-ink mb-12" style={{ letterSpacing: "-0.5px" }}>
            Explore
          </h2>
        </FadeIn>
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {explore.map((c, i) => (
            <FadeIn key={c.href} delay={i * 0.08}>
              <Link href={c.href} className="group block bg-surface-card rounded-xl p-6 hover:bg-surface-cream-strong transition-colors h-full">
                <h3 className="font-sans text-base font-medium text-ink mb-2">{c.title}</h3>
                <p className="text-sm text-muted leading-relaxed mb-4">{c.body}</p>
                <span className="inline-flex items-center gap-1 text-sm text-primary font-medium group-hover:gap-2 transition-all">
                  Explore <ArrowRight size={14} />
                </span>
              </Link>
            </FadeIn>
          ))}
        </div>
      </SectionBand>
    </>
  );
}
