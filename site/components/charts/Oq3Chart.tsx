"use client";

import { useMemo, useState } from "react";
import Segmented from "@/components/ui/Segmented";
import { data, type Oq3Row } from "@/lib/data";
import { compact, duration, int, pct } from "@/lib/format";
import { useWidth } from "@/lib/useWidth";

type Metric = "expected" | "p99_mcu" | "p99_cpu";

const METRICS: { value: Metric; label: string; axis: string; fmt: (v: number) => string }[] = [
  { value: "expected", label: "Expected tries", axis: "Expected tries per layer", fmt: compact },
  { value: "p99_mcu", label: "p99 · hardware wallet", axis: "p99 grind time, software-SHA Cortex-M4", fmt: duration },
  { value: "p99_cpu", label: "p99 · laptop CPU", axis: "p99 grind time, i5-13420H SHA-NI, 12 threads", fmt: duration },
];

const SERIES = [
  { w: 4, color: "var(--color-series-1)", label: "w = 4" },
  { w: 16, color: "var(--color-series-2)", label: "w = 16" },
];

const M = { top: 16, right: 64, bottom: 44, left: 64 };
const H = 340;

/** OQ-3 overgrinding: raising S cuts verifier chain steps and multiplies signer grinding. */
export default function Oq3Chart() {
  const [metric, setMetric] = useState<Metric>("expected");
  const [view, setView] = useState<"chart" | "table">("chart");
  const [hover, setHover] = useState<Oq3Row | null>(null);
  const [ref, width] = useWidth<HTMLDivElement>();
  const m = METRICS.find((x) => x.value === metric)!;

  const series = useMemo(
    () => SERIES.map((s) => ({ ...s, rows: data.oq3.filter((r) => r.w === s.w).sort((a, b) => a.saved - b.saved) })),
    [],
  );

  const values = data.oq3.map((r) => r[metric]);
  const y0 = Math.floor(Math.log10(Math.min(...values)));
  const y1 = Math.ceil(Math.log10(Math.max(...values)));
  const plotW = Math.max(160, width - M.left - M.right);
  const plotH = H - M.top - M.bottom;
  const sx = (v: number) => M.left + (v / 0.5) * plotW;
  const sy = (v: number) => M.top + plotH - ((Math.log10(v) - y0) / (y1 - y0)) * plotH;
  const step = y1 - y0 > 8 ? 2 : 1;
  const yTicks = Array.from({ length: Math.floor((y1 - y0) / step) + 1 }, (_, i) => 10 ** (y0 + i * step));

  function onMove(e: React.MouseEvent<SVGRectElement>) {
    const box = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - box.left + M.left;
    const py = e.clientY - box.top + M.top;
    let best: Oq3Row | null = null;
    let bd = Infinity;
    for (const r of data.oq3) {
      const d = Math.hypot(sx(r.saved) - px, (sy(r[metric]) - py) * 0.5);
      if (d < bd) [best, bd] = [r, d];
    }
    setHover(best);
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <Segmented<Metric> label="Metric" value={metric} onChange={setMetric} options={METRICS} />
        <Segmented
          label="View"
          value={view}
          onChange={setView}
          options={[
            { value: "chart", label: "Chart" },
            { value: "table", label: "Table" },
          ]}
        />
      </div>

      <div className="flex flex-wrap items-center gap-5 text-xs text-muted mb-4">
        {SERIES.map((s) => (
          <span key={s.w} className="inline-flex items-center gap-2">
            <svg width="22" height="10">
              <line x1="1" x2="21" y1="5" y2="5" stroke={s.color} strokeWidth="2" />
              <circle cx="11" cy="5" r="4" fill={s.color} stroke="var(--color-canvas)" strokeWidth="2" />
            </svg>
            Winternitz {s.label}
          </span>
        ))}
      </div>

      <div ref={ref}>
        {view === "chart" ? (
          <div className="relative">
            <svg width={width} height={H} role="img" aria-label={`${m.axis} against chain steps saved`}>
              {yTicks.map((t) => (
                <g key={t}>
                  <line x1={M.left} x2={M.left + plotW} y1={sy(t)} y2={sy(t)} stroke="var(--color-grid)" />
                  <text x={M.left - 8} y={sy(t) + 4} textAnchor="end" fontSize="11" fill="var(--color-muted)" style={{ fontVariantNumeric: "tabular-nums" }}>
                    {m.fmt(t)}
                  </text>
                </g>
              ))}
              {[0, 0.1, 0.2, 0.3, 0.4, 0.5].map((t) => (
                <text key={t} x={sx(t)} y={M.top + plotH + 18} textAnchor="middle" fontSize="11" fill="var(--color-muted)">
                  {t * 100}%
                </text>
              ))}
              <line x1={M.left} x2={M.left + plotW} y1={M.top + plotH} y2={M.top + plotH} stroke="var(--color-grid)" />
              <text x={M.left + plotW / 2} y={H - 6} textAnchor="middle" fontSize="12" fill="var(--color-body)">
                Verifier chain steps saved vs. mean S
              </text>
              <text transform={`translate(14 ${M.top + plotH / 2}) rotate(-90)`} textAnchor="middle" fontSize="12" fill="var(--color-body)">
                {m.axis}
              </text>

              {hover && <line x1={sx(hover.saved)} x2={sx(hover.saved)} y1={M.top} y2={M.top + plotH} stroke="var(--color-muted-soft)" />}

              {series.map((s) => {
                const pts = s.rows.map((r) => `${sx(r.saved)},${sy(r[metric])}`).join(" ");
                const last = s.rows[s.rows.length - 1];
                return (
                  <g key={s.w}>
                    <polyline points={pts} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
                    {s.rows.map((r) => (
                      <circle
                        key={r.id}
                        cx={sx(r.saved)}
                        cy={sy(r[metric])}
                        r={hover?.id === r.id ? 6 : 4}
                        fill={s.color}
                        stroke="var(--color-canvas)"
                        strokeWidth={2}
                      />
                    ))}
                    <text x={sx(last.saved) + 10} y={sy(last[metric]) + 4} fontSize="12" fill="var(--color-body)">
                      {s.label}
                    </text>
                  </g>
                );
              })}

              <rect
                x={M.left}
                y={M.top}
                width={plotW}
                height={plotH}
                fill="transparent"
                onMouseMove={onMove}
                onMouseLeave={() => setHover(null)}
              />
            </svg>

            {hover && (
              <div
                className="absolute z-10 w-60 pointer-events-none bg-canvas border border-hairline rounded-xl shadow-sm p-4 text-xs"
                style={{ top: Math.max(0, sy(hover[metric]) - 40), left: sx(hover.saved) > width / 2 ? sx(hover.saved) - 252 : sx(hover.saved) + 12 }}
                role="status"
              >
                <p className="font-mono text-ink mb-2">{hover.id}</p>
                <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-body" style={{ fontVariantNumeric: "tabular-nums" }}>
                  <dt className="text-muted">Chain steps</dt>
                  <dd>
                    {hover.chain_steps} (−{(hover.saved * 100).toFixed(0)} %)
                  </dd>
                  <dt className="text-muted">E[tries]</dt>
                  <dd>{int(hover.expected)}</dd>
                  <dt className="text-muted">Measured</dt>
                  <dd>
                    {pct(hover.ratio - 1)} vs analytic (n = {compact(hover.n)})
                  </dd>
                  <dt className="text-muted">p99 · HW wallet</dt>
                  <dd>{duration(hover.p99_mcu)}</dd>
                  <dt className="text-muted">p99 · laptop CPU</dt>
                  <dd>{duration(hover.p99_cpu)}</dd>
                </dl>
              </div>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto border border-hairline rounded-xl">
            <table className="w-full text-sm" style={{ fontVariantNumeric: "tabular-nums" }}>
              <thead className="bg-surface-soft text-ink">
                <tr>
                  {["Config", "Chain steps", "Saved", "E[tries]", "Measured vs analytic", "p99 HW wallet", "p99 laptop CPU"].map((h) => (
                    <th key={h} className="text-left font-medium px-3 py-2 whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {series.flatMap((s) => s.rows).map((r) => (
                  <tr key={r.id} className="border-t border-hairline-soft">
                    <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">{r.id}</td>
                    <td className="px-3 py-2">{r.chain_steps}</td>
                    <td className="px-3 py-2">{(r.saved * 100).toFixed(0)} %</td>
                    <td className="px-3 py-2">{int(r.expected)}</td>
                    <td className="px-3 py-2">{pct(r.ratio - 1)}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{duration(r.p99_mcu)}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{duration(r.p99_cpu)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
