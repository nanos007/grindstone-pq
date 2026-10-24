import type { Metadata } from "next";
import PageHeader from "@/components/ui/PageHeader";
import SectionBand from "@/components/ui/SectionBand";
import FadeIn from "@/components/ui/FadeIn";
import StatTile from "@/components/ui/StatTile";
import CalibrationChart from "@/components/charts/CalibrationChart";
import Oq3Chart from "@/components/charts/Oq3Chart";
import { data } from "@/lib/data";
import { compact, int, pct } from "@/lib/format";

export const metadata: Metadata = {
  title: "Results",
  description: "Measured grinding costs against the analytic model for all 37 configurations, and the OQ-3 overgrinding sweep.",
};

const h = data.headline;
const rr = data.rerun;
const maxDev = data.validation.reduce((a, b) => (Math.abs(b.ratio - 1) > Math.abs(a.ratio - 1) ? b : a));
const oq3Max = Math.max(...data.oq3.map((r) => Math.abs(r.ratio - 1)));

export default function Results() {
  return (
    <>
      <PageHeader eyebrow={`Run ${data.run}`} title="The models hold, to within 2 %">
        <p>
          Each grind configuration was sampled 2·10⁴ to 10⁶ times on the GPU, and every returned counter was re-checked by a
          pure-Python reference. The question is simple: does the measured mean number of tries match 1/p, and does the
          distribution have the geometric shape the analytic worst-case figures assume?
        </p>
      </PageHeader>

      <SectionBand className="!pt-0">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-16">
          <StatTile label="Configurations" value={String(h.configs)} note={`${compact(h.samples, 2)} grinds, ${h.outside_ci} outside their 95 % CI (1.9 expected)`} />
          <StatTile label="Goodness of fit" value={`Σz² = ${h.sum_z2.toFixed(1)}`} note={`${h.dof} degrees of freedom, p = 0.36`} />
          <StatTile label="Largest deviation" value={pct(maxDev.ratio - 1)} note={`${maxDev.id} at n = ${int(maxDev.n)}`} />
          <StatTile label="After the re-run" value={pct(rr.ratio - 1)} note={`n = ${int(rr.n)}, z = ${rr.z.toFixed(2)}: sampling noise`} />
        </div>

        <FadeIn>
          <h2 className="font-display text-3xl font-normal text-ink mb-3" style={{ letterSpacing: "-0.5px" }}>
            Measured mean against analytic expectation
          </h2>
          <p className="text-sm text-body leading-relaxed mb-8 max-w-2xl">
            Deviation of the measured mean from 1/p per configuration, with its 95 % confidence interval. The shaded band is the
            ±2 % acceptance threshold fixed before the campaign. Hover or focus a row for details.
          </p>
        </FadeIn>
        <CalibrationChart />
      </SectionBand>

      <SectionBand card id="oq3">
        <FadeIn>
          <p className="text-xs font-medium tracking-widest uppercase text-accent-steel mb-4">Open question 3 · run {data.oq3_run}</p>
          <h2 className="font-display text-3xl font-normal text-ink mb-3" style={{ letterSpacing: "-0.5px" }}>
            Overgrinding: trading signer work for verifier work
          </h2>
          <p className="text-sm text-body leading-relaxed mb-8 max-w-2xl">
            Raising the WOTS+C target sum S removes hash-chain steps from every verification at the same signature size, and
            multiplies the signer&apos;s grinding. All {data.oq3.length} sweep points match the analytic model to within{" "}
            {(oq3Max * 100).toFixed(2)} %. At w = 4, removing a third of the chain steps (S = 128) costs about 650× the grinding,
            which a laptop does in under a millisecond and a software-SHA hardware wallet in 1.7 s at p99.
          </p>
        </FadeIn>
        <div className="bg-canvas rounded-2xl p-4 md:p-8">
          <Oq3Chart />
        </div>
      </SectionBand>
    </>
  );
}
