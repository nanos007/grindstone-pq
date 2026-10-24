"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, Cpu } from "lucide-react";
import Segmented from "@/components/ui/Segmented";
import BadgePill from "@/components/ui/BadgePill";
import { data, PROFILE_LABEL, type Param } from "@/lib/data";
import { bytesToVbytes, hwSafeBaseline, smallestWithin } from "@/lib/explorer";
import { compact, duration, int, pow2 } from "@/lib/format";
import { useWidth } from "@/lib/useWidth";

const LIMITS = [20, 30, 40];
const PRESETS = [
  { s: 1, label: "1 s" },
  { s: 10, label: "10 s" },
  { s: 120, label: "2 min" },
  { s: 600, label: "10 min" },
];
const FEERATES = [2, 10, 50];
const LOG_MIN = -3; // 1 ms
const LOG_MAX = 4; // ~2.8 h

const KIND_NOTE: Record<string, string> = {
  measured: "measured in this study",
  derived: "derived from published chip speeds",
  cited: "cited benchmark",
};

export default function Explorer() {
  const [limit, setLimit] = useState(30);
  const [classId, setClassId] = useState("class2");
  const [logBudget, setLogBudget] = useState(1); // 10 s
  const [feerate, setFeerate] = useState(10);

  const cls = data.ladder.find((c) => c.id === classId)!;
  const budget = 10 ** logBudget;
  const best = useMemo(() => smallestWithin(data.params, limit, cls.rate, budget), [limit, cls.rate, budget]);
  const base = useMemo(() => hwSafeBaseline(data.params, limit), [limit]);
  const saved = best && base ? base.bytes - best.bytes : 0;

  return (
    <div className="grid lg:grid-cols-[1fr_1.1fr] gap-8">
      {/* Controls */}
      <div className="space-y-8">
        <Control title="Signatures per key">
          <Segmented label="Signature limit" value={limit} onChange={setLimit} options={LIMITS.map((L) => ({ value: L, label: pow2(L) }))} />
        </Control>

        <Control title="Signer">
          <div className="grid sm:grid-cols-2 gap-2" role="radiogroup" aria-label="Signer class">
            {data.ladder.map((c) => (
              <button
                key={c.id}
                role="radio"
                aria-checked={c.id === classId}
                onClick={() => setClassId(c.id)}
                className={`text-left rounded-xl p-3 border transition-colors ${
                  c.id === classId ? "bg-surface-card border-primary" : "bg-canvas border-hairline hover:bg-surface-soft"
                }`}
              >
                <span className="block text-sm font-medium text-ink leading-snug">{c.label}</span>
                <span className="block text-xs text-muted mt-1">
                  {compact(c.rate)} compressions/s · {c.kind}
                </span>
              </button>
            ))}
          </div>
        </Control>

        <Control title={`p99 signing budget: ${duration(budget)}`}>
          <input
            type="range"
            min={LOG_MIN}
            max={LOG_MAX}
            step={0.01}
            value={logBudget}
            onChange={(e) => setLogBudget(+e.target.value)}
            className="w-full accent-[var(--color-primary)]"
            aria-label="p99 signing time budget"
            aria-valuetext={duration(budget)}
          />
          <div className="flex justify-between text-xs text-muted mt-1">
            <span>1 ms</span>
            <span>2.8 h</span>
          </div>
          <div className="flex flex-wrap gap-2 mt-3">
            {PRESETS.map((p) => (
              <button
                key={p.s}
                onClick={() => setLogBudget(Math.log10(p.s))}
                className={`px-3 py-1 text-xs font-medium rounded-full border transition-colors ${
                  Math.abs(budget - p.s) < 1e-6 ? "bg-primary text-on-primary border-primary" : "border-hairline text-muted hover:text-ink hover:bg-surface-soft"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </Control>

        <Control title="Fee rate">
          <Segmented label="Fee rate" value={feerate} onChange={setFeerate} options={FEERATES.map((f) => ({ value: f, label: `${f} sat/vB` }))} />
        </Control>
      </div>

      {/* Result */}
      <div className="space-y-4">
        <div className="bg-surface-dark text-on-dark rounded-2xl p-8" aria-live="polite">
          {best ? (
            <>
              <p className="text-sm text-on-dark-soft mb-1">Smallest signature within budget</p>
              <p className="text-6xl font-semibold tracking-tight">
                {int(best.bytes)} <span className="text-2xl font-medium text-on-dark-soft">bytes</span>
              </p>
              <p className="font-mono text-xs text-on-dark-soft mt-4 break-all">{best.id}</p>
              <div className="flex flex-wrap gap-2 mt-4">
                <BadgePill variant="steel">{PROFILE_LABEL[best.profile] ?? best.profile}</BadgePill>
                {best.layout && best.layout !== "-" && <BadgePill variant="muted">{best.layout}</BadgePill>}
              </div>

              <dl className="grid grid-cols-2 gap-4 mt-8 text-sm" style={{ fontVariantNumeric: "tabular-nums" }}>
                <Fact label="p99 signing time" value={duration(best.total_p99 / cls.rate)} />
                <Fact label="Mean signing time" value={duration(best.total_mean / cls.rate)} />
                <Fact label="Grinding share of work" value={`${(best.grind_share * 100).toFixed(1)} %`} />
                <Fact label="Verify cost" value={`${int(best.verify_comp)} compressions`} />
              </dl>

              {base && (
                <div className="mt-8 pt-6 border-t border-surface-dark-elevated">
                  {saved > 0 ? (
                    <p className="text-sm leading-relaxed">
                      <span className="text-on-dark font-medium">
                        {int(saved)} bytes smaller
                      </span>{" "}
                      than the smallest hardware-wallet-safe set ({int(base.bytes)} B): {int(bytesToVbytes(saved))} vB, or{" "}
                      <span className="text-on-dark font-medium">{int(bytesToVbytes(saved) * feerate)} sats</span> per input at {feerate} sat/vB.
                    </p>
                  ) : (
                    <p className="text-sm leading-relaxed">
                      This is the hardware-wallet-safe baseline for {pow2(limit)}; a faster signer or a larger budget buys smaller sets.
                    </p>
                  )}
                </div>
              )}
            </>
          ) : (
            <>
              <p className="text-sm text-on-dark-soft mb-1">Smallest signature within budget</p>
              <p className="text-3xl font-semibold">None fits</p>
              <p className="text-sm text-on-dark-soft mt-4 leading-relaxed">
                No shortlisted {pow2(limit)} set signs within {duration(budget)} at p99 on this signer. Raise the budget or pick a faster signer.
              </p>
            </>
          )}
        </div>

        {best?.z1 && (
          <div className="flex gap-3 bg-surface-soft border border-hairline rounded-xl p-4 text-sm text-body" role="note">
            <AlertTriangle size={18} className="text-warning shrink-0 mt-0.5" aria-hidden />
            <p>
              <span className="font-medium text-ink">Measured, not endorsed.</span> This set forces one WOTS+C chain to zero (z = 1). The
              SPHINCS+C proofs are stated for general z; independent review is pending, and verifiers must check the zeroed chain.
            </p>
          </div>
        )}

        <p className="flex gap-2 text-xs text-muted leading-relaxed">
          <Cpu size={14} className="shrink-0 mt-0.5" aria-hidden />
          {cls.label}: {compact(cls.rate)} SHA-256 compressions/s, {KIND_NOTE[cls.kind]}. Times are p99 of full signing work (tree building
          plus grinding) from 10⁵-sample resampling, divided by that rate.
        </p>

        <ParetoChart params={data.params.filter((p) => p.limit === limit)} rate={cls.rate} budget={budget} best={best} />
      </div>
    </div>
  );
}

function Control({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium tracking-widest uppercase text-muted mb-3">{title}</p>
      {children}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-on-dark-soft text-xs mb-1">{label}</dt>
      <dd className="text-on-dark">{value}</dd>
    </div>
  );
}

const PM = { top: 12, right: 16, bottom: 40, left: 52 };
const PH = 260;

/** Every shortlisted set at this limit: p99 signing time on the chosen signer against size. */
function ParetoChart({ params, rate, budget, best }: { params: Param[]; rate: number; budget: number; best: Param | null }) {
  const [ref, width] = useWidth<HTMLDivElement>(520);
  const [hover, setHover] = useState<Param | null>(null);
  const t = params.map((p) => p.total_p99 / rate);
  const x0 = Math.floor(Math.log10(Math.min(...t, budget)));
  const x1 = Math.ceil(Math.log10(Math.max(...t, budget)));
  const b0 = Math.floor(Math.min(...params.map((p) => p.bytes)) / 500) * 500;
  const b1 = Math.ceil(Math.max(...params.map((p) => p.bytes)) / 500) * 500;
  const pw = Math.max(120, width - PM.left - PM.right);
  const ph = PH - PM.top - PM.bottom;
  const sx = (s: number) => PM.left + ((Math.log10(s) - x0) / (x1 - x0)) * pw;
  const sy = (b: number) => PM.top + ph - ((b - b0) / (b1 - b0)) * ph;
  const span = x1 - x0;
  const xt = Array.from({ length: span + 1 }, (_, i) => 10 ** (x0 + i)).filter((_, i) => span <= 7 || i % 2 === 0);
  const yt = Array.from({ length: (b1 - b0) / 500 + 1 }, (_, i) => b0 + i * 500);

  return (
    <div ref={ref} className="relative bg-canvas border border-hairline rounded-xl p-4">
      <p className="text-sm font-medium text-ink mb-1">All shortlisted sets at this limit</p>
      <div className="flex flex-wrap gap-4 text-xs text-muted mb-2">
        <Key fill="var(--color-series-1)">Fits the budget</Key>
        <Key fill="var(--color-canvas)" stroke="var(--color-muted-soft)">Over budget</Key>
        <Key fill="var(--color-series-2)">Selected</Key>
      </div>
      <svg width={width - 32} height={PH} role="img" aria-label="Signature size against p99 signing time">
        {yt.map((b) => (
          <g key={b}>
            <line x1={PM.left} x2={PM.left + pw} y1={sy(b)} y2={sy(b)} stroke="var(--color-grid)" />
            <text x={PM.left - 8} y={sy(b) + 4} textAnchor="end" fontSize="11" fill="var(--color-muted)" style={{ fontVariantNumeric: "tabular-nums" }}>
              {int(b)}
            </text>
          </g>
        ))}
        {xt.map((s) => (
          <text key={s} x={sx(s)} y={PM.top + ph + 16} textAnchor="middle" fontSize="11" fill="var(--color-muted)">
            {duration(s)}
          </text>
        ))}
        <text x={PM.left + pw / 2} y={PH - 4} textAnchor="middle" fontSize="11" fill="var(--color-body)">
          p99 signing time (log scale) · y: signature bytes
        </text>
        <line x1={sx(budget)} x2={sx(budget)} y1={PM.top} y2={PM.top + ph} stroke="var(--color-primary)" strokeWidth={1.5} />
        <text x={sx(budget) + 6} y={PM.top + 12} fontSize="11" fill="var(--color-body)">
          budget
        </text>
        {params.map((p) => {
          const fits = p.total_p99 / rate <= budget;
          const sel = best?.id === p.id;
          return (
            <circle
              key={p.id}
              cx={sx(p.total_p99 / rate)}
              cy={sy(p.bytes)}
              r={sel ? 7 : hover?.id === p.id ? 6 : 4.5}
              fill={sel ? "var(--color-series-2)" : fits ? "var(--color-series-1)" : "var(--color-canvas)"}
              stroke={sel || fits ? "var(--color-canvas)" : "var(--color-muted-soft)"}
              strokeWidth={sel || fits ? 2 : 1.5}
              onMouseEnter={() => setHover(p)}
              onMouseLeave={() => setHover(null)}
              style={{ cursor: "default" }}
            />
          );
        })}
      </svg>
      {hover && (
        <div
          className="absolute z-10 pointer-events-none bg-canvas border border-hairline rounded-lg shadow-sm px-3 py-2 text-xs"
          style={{ left: Math.min(sx(hover.total_p99 / rate) + 24, width - 240), top: sy(hover.bytes) + 40 }}
        >
          <p className="font-mono text-ink">{hover.id}</p>
          <p className="text-body mt-1">
            {int(hover.bytes)} B · p99 {duration(hover.total_p99 / rate)} · {PROFILE_LABEL[hover.profile] ?? hover.profile}
          </p>
        </div>
      )}
    </div>
  );
}

function Key({ fill, stroke, children }: { fill: string; stroke?: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <svg width="12" height="12">
        <circle cx="6" cy="6" r="4.5" fill={fill} stroke={stroke ?? "var(--color-canvas)"} strokeWidth="1.5" />
      </svg>
      {children}
    </span>
  );
}
