import type { Metadata } from "next";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { isValidElement, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Download } from "lucide-react";
import SectionBand from "@/components/ui/SectionBand";
import { BASE_PATH, PAPER_PDF } from "@/lib/site";

export const metadata: Metadata = {
  title: "Paper (draft)",
  description: "Grinding at the Edge: Empirical Signer-Cost Distributions for Bitcoin-Tuned Hash-Based Signatures. Draft with executive summary.",
};

// Copied from ../paper by scripts/export_data.py, so the site builds from one directory.
const read = (f: string) => readFileSync(join(process.cwd(), "content", f), "utf8");

function text(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(text).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) return text(node.props.children);
  return "";
}

const slug = (s: string) =>
  s
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s-]/gu, "")
    .trim()
    .replace(/\s+/g, "-");

const components: Components = {
  h2: ({ children }) => <h2 id={slug(text(children))}>{children}</h2>,
  h3: ({ children }) => <h3 id={slug(text(children))}>{children}</h3>,
  table: ({ children }) => (
    <div className="table-wrap">
      <table>{children}</table>
    </div>
  ),
  // paper.md references figures/… relative to paper/; the site serves them from public/figures.
  img: ({ src, alt }) => (
    <span className="paper-figure">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={`${BASE_PATH}/${String(src).replace(/^\.?\//, "")}`} alt={alt ?? ""} loading="lazy" />
      {alt && <span className="paper-caption">{alt}</span>}
    </span>
  ),
  a: ({ href, children }) => (
    <a href={href} target={href?.startsWith("http") ? "_blank" : undefined} rel="noopener noreferrer">
      {children}
    </a>
  ),
};

export default function Paper() {
  const paper = read("paper.md");
  const summary = read("executive_summary.md").replace(/^# .*\n/, "");
  const toc = [...paper.matchAll(/^## (.+)$/gm)].map((m) => ({ title: m[1], id: slug(m[1]) }));

  return (
    <SectionBand className="!pt-16">
      <div className="grid lg:grid-cols-[200px_1fr] gap-12">
        <nav aria-label="Paper contents" className="hidden lg:block no-print">
          <div className="sticky top-24">
            <a
              href={`${BASE_PATH}/${PAPER_PDF}`}
              className="inline-flex items-center gap-2 bg-primary text-on-primary text-sm font-medium px-4 py-2 rounded-lg hover:bg-primary-active transition-colors mb-8"
            >
              <Download size={15} /> PDF
            </a>
            <p className="text-xs font-medium tracking-widest uppercase text-muted mb-4">Contents</p>
            <ul className="space-y-2 text-sm">
              <li>
                <a href="#summary" className="text-muted hover:text-ink transition-colors">
                  Executive summary
                </a>
              </li>
              {toc.map((t) => (
                <li key={t.id}>
                  <a href={`#${t.id}`} className="text-muted hover:text-ink transition-colors">
                    {t.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </nav>

        <div className="min-w-0 max-w-3xl">
          <a
            href={`${BASE_PATH}/${PAPER_PDF}`}
            className="lg:hidden no-print inline-flex items-center gap-2 bg-primary text-on-primary text-sm font-medium px-4 py-2 rounded-lg hover:bg-primary-active transition-colors mb-8"
          >
            <Download size={15} /> Download PDF
          </a>
          <aside id="summary" className="no-print bg-surface-card rounded-2xl p-6 md:p-8 mb-16 scroll-mt-24">
            <p className="text-xs font-medium tracking-widest uppercase text-accent-steel mb-4">Executive summary</p>
            <div className="prose-paper text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
                {summary}
              </ReactMarkdown>
            </div>
          </aside>
          <article className="prose-paper">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
              {paper}
            </ReactMarkdown>
          </article>
        </div>
      </div>
    </SectionBand>
  );
}
