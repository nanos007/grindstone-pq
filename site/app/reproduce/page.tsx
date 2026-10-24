import type { Metadata } from "next";
import { ArrowUpRight } from "lucide-react";
import PageHeader from "@/components/ui/PageHeader";
import SectionBand from "@/components/ui/SectionBand";
import FadeIn from "@/components/ui/FadeIn";
import FeatureCard from "@/components/ui/FeatureCard";
import CodeBlock from "@/components/ui/CodeBlock";
import { data } from "@/lib/data";
import { REPO_URL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Reproduce",
  description: "Re-derive every number from the published dataset with one command, or re-run the campaign on your own GPU.",
};

const DATASET_SHA256 = "01e9fd2ca78f89e5c2525072705e8f32f42863054ffcbc7301341905bfe98d80";

const setup = `pip install -r env/requirements.txt
python -m env.check_env          # compiles a test kernel, records GPU/CPU/OS
python -m pytest -q              # -k "not gpu" for the CPU-only subset`;

const reproduce = `python -m runner.reproduce --analysis-only      # all notebooks on the published run
python -m runner.reproduce --hash ${data.run}  # check the dataset hash
python -m runner.reproduce                      # smoke campaign + all notebooks on it`;

const campaign = `python -m runner.run_campaign --smoke           # ~5 min end-to-end check
python -m runner.run_campaign                   # full campaign (~2.3 h GPU)
python -m runner.run_campaign --extra oq3       # OQ-3 overgrinding sweep (~15 min)
python analysis/build_notebooks.py              # rebuild + execute all notebooks`;

const bibtex = `@misc{nanos2026grindstone,
  author = {Nanos, Georgios},
  title  = {Grinding at the Edge: Empirical Signer-Cost Distributions
            for Bitcoin-Tuned Hash-Based Signatures},
  year   = {2026},
  note   = {Draft. Code and data: ${REPO_URL || "github.com/nanos007/grindstone-pq"}}
}`;

export default function Reproduce() {
  return (
    <>
      <PageHeader eyebrow="Open science" title="Check every number yourself">
        <p>
          The grinder, the reference implementation, the analysis notebooks and the dataset are open. Instance inputs derive
          from SHA-256(&quot;grindstone&quot; ‖ run_id ‖ i), so every one of the 11.16 M samples can be regenerated and re-verified.
        </p>
      </PageHeader>

      <SectionBand className="!pt-0">
        <div className="grid lg:grid-cols-[1fr_320px] gap-8 items-start">
          <div className="space-y-6">
            <FadeIn>
              <p className="text-sm text-body mb-3">
                Windows 11 or Linux, Python 3.12 and an NVIDIA GPU with a recent driver. No CUDA toolkit or compiler: kernels
                compile at run time through NVRTC, and the CPU grinder is built with the <code className="font-mono text-[0.85em] bg-surface-card px-1 rounded">ziglang</code> pip package.
              </p>
              <CodeBlock label="Set up" code={setup} />
            </FadeIn>
            <FadeIn>
              <CodeBlock label="Reproduce the analysis (CPU only)" code={reproduce} />
            </FadeIn>
            <FadeIn>
              <CodeBlock label="Run your own campaign" code={campaign} />
              <p className="text-xs text-muted mt-3 leading-relaxed">
                A campaign refuses to start unless the E1 gate passes: GPU counters must equal the Python reference bit for bit.
                Run on mains power with nothing else on the GPU; other load leaves tries correct but invalidates timing and energy.
              </p>
            </FadeIn>
          </div>

          <div className="space-y-4">
            <FeatureCard>
              <p className="text-xs font-medium tracking-widest uppercase text-muted mb-3">Published runs</p>
              <ul className="space-y-2 text-sm font-mono text-body">
                <li>{data.run} <span className="font-sans text-muted">· campaign</span></li>
                <li>{data.oq3_run} <span className="font-sans text-muted">· OQ-3</span></li>
                <li>{data.rerun_run} <span className="font-sans text-muted">· re-run</span></li>
              </ul>
              <p className="text-xs font-medium tracking-widest uppercase text-muted mt-6 mb-2">Dataset SHA-256</p>
              <p className="font-mono text-xs text-body break-all">{DATASET_SHA256}</p>
            </FeatureCard>
            <FeatureCard>
              <p className="text-xs font-medium tracking-widest uppercase text-muted mb-3">License</p>
              <p className="text-sm text-body">Code MIT. Data and figures CC-BY-4.0.</p>
              {REPO_URL && (
                <a
                  href={REPO_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-primary font-medium mt-4 hover:gap-2 transition-all"
                >
                  Source on GitHub <ArrowUpRight size={14} />
                </a>
              )}
            </FeatureCard>
          </div>
        </div>
      </SectionBand>

      <SectionBand card>
        <FadeIn>
          <h2 className="font-display text-3xl font-normal text-ink mb-6" style={{ letterSpacing: "-0.5px" }}>
            Cite
          </h2>
          <CodeBlock code={bibtex} />
        </FadeIn>
      </SectionBand>
    </>
  );
}
