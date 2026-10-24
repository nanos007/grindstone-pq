"use client";

import { useMemo, useState } from "react";
import Segmented from "@/components/ui/Segmented";
import { data, family, GRIND_FAMILIES, type ValidationRow } from "@/lib/data";
import { int, pct } from "@/lib/format";
import { useWidth } from "@/lib/useWidth";

type Filter = "All" | (typeof GRIND_FAMILIES)[number];

const DOMAIN = 0.035; // ±3.5 %: the largest |deviation| + CI is 3.1 %
const TICKS = [-0.03, -0.02, -0.01, 0, 0.01, 0.02, 0.03];
const ROW_H = 26;
const LABEL_W_WIDE = 200;
const LABEL_W_NARROW = 132;

/**
 * Forest plot: measured mean / analytic expectation − 1 per grind config, with its 95 % CI.
 * The ±2 % band is the plan's acceptance band (DoD §1.6). The re-run of the largest deviation at
 * n = 10⁵ is drawn as a second marker on its row.
 */
export default function CalibrationChart() {
  const [filter, setFilter] = useState<Filter>("All");
  const [view, setView] = useState<"chart" | "table">("chart");
  const [hover, setHover] = useState<string | null>(null);
  const [ref, width] = useWidth<HTMLDivElement>();

  const rows = useMemo(
    () =>
      data.validation
        .filter((r) => filter === "All" || family(r.grind) === filter)
        .sort(
          (a, b) =>
            GRIND_FAMILIES.indexOf(family(a.grind)) - GRIND_FAMILIES.indexOf(family(b.grind)) || a.ratio - b.ratio,
        ),
    [filter],
  );

  const labelW = width < 560 ? LABEL_W_NARROW : LABEL_W_WIDE;
  const plotW = Math.max(120, width - labelW - 16);
  const x = (d: number) => labelW + ((d + DOMAIN) / (2 * DOMAIN)) * plotW;
  const height = rows.length * ROW_H + 48;
  const rr = data.rerun;
  const hovered = rows.find((r) => r.id === hover) ?? null;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <Segmented<Filter>
          label="Grind family"
          value={filter}
          onChange={setFilter}
          options={["All", ...GRIND_FAMILIES].map((f) => ({ value: f as Filter, label: f }))}
        />
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

      <div className="flex flex-wrap items-center gap-5 text-xs text-muted mb-4" aria-hidden={view === "table"}>
        <span className="inline-flex items-center gap-2">
          <svg width="22" height="10">
            <line x1="1" x2="21" y1="5" y2="5" stroke="var(--color-series-1)" strokeWidth="2" />
            <circle cx="11" cy="5" r="4" fill="var(--color-series-1)" stroke="var(--color-canvas)" strokeWidth="2" />
          </svg>
          Campaign mean, 95 % CI
        </span>
        <span className="inline-flex items-center gap-2">
          <svg width="12" height="12">
            <circle cx="6" cy="6" r="4" fill="var(--color-series-2)" stroke="var(--color-canvas)" strokeWidth="2" />
          </svg>
          Re-run at n = 10⁵
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="inline-block w-4 h-3 rounded-sm bg-surface-card" /> ±2 % acceptance band
        </span>
      </div>

      <div ref={ref}>
      {view === "chart" ? (
        <div className="relative">
          <svg width={width} height={height} role="img" aria-label="Measured mean over analytic expectation per configuration">
            <rect x={x(-0.02)} y={20} width={x(0.02) - x(-0.02)} height={rows.length * ROW_H} fill="var(--color-surface-card)" opacity={0.6} />
            {TICKS.map((t) => (
              <g key={t}>
                <line x1={x(t)} x2={x(t)} y1={20} y2={20 + rows.length * ROW_H} stroke="var(--color-grid)" strokeWidth={t === 0 ? 1.5 : 1} />
                <text x={x(t)} y={12} textAnchor="middle" fontSize="11" fill="var(--color-muted)" style={{ fontVariantNumeric: "tabular-nums" }}>
                  {t === 0 ? "0" : `${t > 0 ? "+" : "−"}${Math.abs(t * 100)}%`}
                </text>
              </g>
            ))}
            {rows.map((r, i) => {
              const cy = 20 + i * ROW_H + ROW_H / 2;
              const d = r.ratio - 1;
              const isRerun = r.id === rr.id;
              const on = hover === r.id;
              return (
                <g
                  key={r.id}
                  tabIndex={0}
                  onMouseEnter={() => setHover(r.id)}
                  onMouseLeave={() => setHover(null)}
                  onFocus={() => setHover(r.id)}
                  onBlur={() => setHover(null)}
                  className="outline-none"
                  aria-label={`${r.id}: ${pct(d)} ± ${(r.ci95 * 100).toFixed(2)} %`}
                >
                  <rect x={0} y={cy - ROW_H / 2} width={width} height={ROW_H} fill={on ? "var(--color-surface-soft)" : "transparent"} />
                  <text x={labelW - 12} y={cy + 4} textAnchor="end" fontSize={width < 560 ? 10 : 11} fill={on ? "var(--color-ink)" : "var(--color-body)"} fontFamily="var(--font-mono)">
                    {r.id}
                  </text>
                  <line x1={x(d - r.ci95)} x2={x(d + r.ci95)} y1={cy} y2={cy} stroke="var(--color-series-1)" strokeWidth={2} strokeLinecap="round" />
                  <circle cx={x(d)} cy={cy} r={4.5} fill="var(--color-series-1)" stroke="var(--color-canvas)" strokeWidth={2} />
                  {isRerun && (
                    <>
                      <line x1={x(rr.ratio - 1 - rr.ci95)} x2={x(rr.ratio - 1 + rr.ci95)} y1={cy + 7} y2={cy + 7} stroke="var(--color-series-2)" strokeWidth={2} strokeLinecap="round" />
                      <circle cx={x(rr.ratio - 1)} cy={cy + 7} r={4.5} fill="var(--color-series-2)" stroke="var(--color-canvas)" strokeWidth={2} />
                    </>
                  )}
                </g>
              );
            })}
          </svg>

          {hovered && <Tooltip row={hovered} top={20 + rows.indexOf(hovered) * ROW_H + ROW_H} left={Math.min(x(hovered.ratio - 1) + 12, width - 260)} />}
        </div>
      ) : (
        <CalibrationTable rows={rows} />
      )}
      </div>
    </div>
  );
}

function Tooltip({ row, top, left }: { row: ValidationRow; top: number; left: number }) {
  const rr = row.id === data.rerun.id ? data.rerun : null;
  return (
    <div
      className="absolute z-10 w-64 pointer-events-none bg-canvas border border-hairline rounded-xl shadow-sm p-4 text-xs"
      style={{ top, left: Math.max(0, left) }}
      role="status"
    >
      <p className="font-mono text-ink mb-2">{row.id}</p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-body" style={{ fontVariantNumeric: "tabular-nums" }}>
        <dt className="text-muted">Deviation</dt>
        <dd>
          {pct(row.ratio - 1)} ± {(row.ci95 * 100).toFixed(2)} %
        </dd>
        <dt className="text-muted">z</dt>
        <dd>{row.z.toFixed(2)}</dd>
        <dt className="text-muted">E[tries]</dt>
        <dd>{int(row.expected)}</dd>
        <dt className="text-muted">Samples</dt>
        <dd>{int(row.n)}</dd>
        <dt className="text-muted">Verified</dt>
        <dd>{row.verified ? "all, by reference" : "no"}</dd>
        {rr && (
          <>
            <dt className="text-muted">Re-run</dt>
            <dd>
              {pct(rr.ratio - 1)} at n = {int(rr.n)}, z = {rr.z.toFixed(2)}
            </dd>
          </>
        )}
      </dl>
    </div>
  );
}

function CalibrationTable({ rows }: { rows: ValidationRow[] }) {
  return (
    <div className="overflow-x-auto border border-hairline rounded-xl">
      <table className="w-full text-sm" style={{ fontVariantNumeric: "tabular-nums" }}>
        <thead className="bg-surface-soft text-ink">
          <tr>
            {["Config", "Grind", "Samples", "E[tries]", "Deviation", "95 % CI", "z"].map((h) => (
              <th key={h} className="text-left font-medium px-3 py-2 whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-hairline-soft">
              <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">{r.id}</td>
              <td className="px-3 py-2 whitespace-nowrap">{r.grind}</td>
              <td className="px-3 py-2">{int(r.n)}</td>
              <td className="px-3 py-2">{int(r.expected)}</td>
              <td className="px-3 py-2">{pct(r.ratio - 1)}</td>
              <td className="px-3 py-2">±{(r.ci95 * 100).toFixed(2)} %</td>
              <td className="px-3 py-2">{r.z.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
