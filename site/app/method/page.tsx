import type { Metadata } from "next";
import { Cpu, ShieldCheck, Layers, GitCompare } from "lucide-react";
import PageHeader from "@/components/ui/PageHeader";
import SectionBand from "@/components/ui/SectionBand";
import FadeIn from "@/components/ui/FadeIn";
import FeatureCard from "@/components/ui/FeatureCard";
import BadgePill from "@/components/ui/BadgePill";
import InlineMd from "@/components/ui/InlineMd";
import { data } from "@/lib/data";

export const metadata: Metadata = {
  title: "Method",
  description: "Parameter points, byte layouts, GPU kernels, correctness checks, hardware and threats to validity.",
};

const steps = [
  {
    icon: Layers,
    title: "40 parameter points, 37 grinds",
    body: "The 29 Kudinov–Nick table rows, plus per signature limit a hardware-wallet-safe point (every grind ≤ 2¹² tries), a moderate and a maximal heavy-signer point, and two stress points. A grind's distribution depends only on (w, S, z), on (k, a) and the layout, or on (k, a, h, m_max), so 40 points need 37 configurations.",
  },
  {
    icon: GitCompare,
    title: "FIPS 205-faithful byte layouts",
    body: "The authors give no byte-level SHA-256 spec for FORS+C or PORS+FP, so we fixed layouts that follow FIPS 205. Tries do not depend on these choices; per-attempt cost and test vectors do. The open questions are drafted for the authors.",
  },
  {
    icon: Cpu,
    title: "Deterministic GPU kernels",
    body: "NVRTC-compiled CUDA, one kernel per layout. Threads stride counters and the lowest successful counter wins (atomicMin), so each result equals a sequential search. Many independent instances are batched per launch; each instance is one sample.",
  },
  {
    icon: ShieldCheck,
    title: "Every counter re-checked",
    body: "A campaign starts only after the E1 gate passes (10 configurations covering every acceptance path, 10⁴ instances each, full minimality check). All 11.16 M campaign counters were re-checked by the Python reference, and a separate SHA-NI CPU grinder reproduced every WOTS+C counter bit for bit.",
  },
];

const hardware = [
  ["GPU", "RTX 4050 Laptop, power-capped at 45 W, 10 Hz telemetry"],
  ["CPU", "Intel i5-13420H, SHA-NI, 12 threads"],
  ["Toolchain", "CuPy + NVRTC (no CUDA toolkit), Python reference, Zig-built CPU grinder"],
  ["Other signers", "Hardware-wallet MCUs, Raspberry Pi 5 and an 8× RTX 4090 server use cited or derived rates"],
];

const severityVariant = { Low: "muted", Medium: "default", High: "coral" } as const;

export default function Method() {
  return (
    <>
      <PageHeader eyebrow="Method" title="How the numbers were made">
        <p>
          The analytic model predicts the number of tries a grind needs: geometric with success probability p, so the mean is
          1/p and the 99th percentile about 4.61/p. GRINDSTONE measures it, configuration by configuration, and checks each
          result independently.
        </p>
      </PageHeader>

      <SectionBand className="!pt-0">
        <div className="grid md:grid-cols-2 gap-4">
          {steps.map((s, i) => (
            <FadeIn key={s.title} delay={i * 0.06}>
              <FeatureCard className="h-full">
                <s.icon size={20} className="text-accent-steel mb-4" aria-hidden />
                <h2 className="text-base font-medium text-ink mb-2">{s.title}</h2>
                <p className="text-sm text-body leading-relaxed">{s.body}</p>
              </FeatureCard>
            </FadeIn>
          ))}
        </div>
      </SectionBand>

      <SectionBand card>
        <FadeIn>
          <h2 className="font-display text-3xl font-normal text-ink mb-8" style={{ letterSpacing: "-0.5px" }}>
            Hardware
          </h2>
          <dl className="divide-y divide-hairline border-y border-hairline">
            {hardware.map(([k, v]) => (
              <div key={k} className="grid sm:grid-cols-[180px_1fr] gap-2 py-4">
                <dt className="text-sm font-medium text-ink">{k}</dt>
                <dd className="text-sm text-body">{v}</dd>
              </div>
            ))}
          </dl>
        </FadeIn>
      </SectionBand>

      <SectionBand id="threats">
        <FadeIn>
          <h2 className="font-display text-3xl font-normal text-ink mb-3" style={{ letterSpacing: "-0.5px" }}>
            Threats to validity
          </h2>
          <p className="text-sm text-body leading-relaxed mb-8 max-w-2xl">
            Everything that could make these numbers wrong or misleading, with how it is handled. The full discussion is in{" "}
            <code className="font-mono text-[0.85em] bg-surface-card px-1 rounded">kb/threats_to_validity.md</code>.
          </p>
        </FadeIn>
        <div className="overflow-x-auto border border-hairline rounded-xl">
          <table className="w-full text-sm">
            <thead className="bg-surface-soft text-ink">
              <tr>
                {["#", "Threat", "Severity", "Status"].map((h) => (
                  <th key={h} className="text-left font-medium px-4 py-3">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.threats.map((t) => (
                <tr key={t.id} className="border-t border-hairline-soft align-top">
                  <td className="px-4 py-3 text-muted" style={{ fontVariantNumeric: "tabular-nums" }}>
                    {t.id}
                  </td>
                  <td className="px-4 py-3 text-body min-w-[16rem]">
                    <InlineMd>{t.threat}</InlineMd>
                  </td>
                  <td className="px-4 py-3">
                    <BadgePill variant={severityVariant[t.severity] ?? "muted"}>{t.severity}</BadgePill>
                  </td>
                  <td className="px-4 py-3 text-body min-w-[14rem]">
                    <InlineMd>{t.status}</InlineMd>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionBand>
    </>
  );
}
