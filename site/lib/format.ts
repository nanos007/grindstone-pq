/** Compact count: 1,284 / 12.9K / 4.2M / 2.2G. */
export function compact(x: number, digits = 1): string {
  const abs = Math.abs(x);
  const units: [number, string][] = [
    [1e12, "T"],
    [1e9, "G"],
    [1e6, "M"],
    [1e3, "K"],
  ];
  for (const [v, s] of units) {
    if (abs >= v) return `${(x / v).toFixed(digits).replace(/\.0+$/, "")}${s}`;
  }
  return x.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

export const int = (x: number) => Math.round(x).toLocaleString("en-US");

/** Human time from seconds: 3.6 µs / 12 ms / 1.7 s / 12 min / 3.1 h. */
export function duration(s: number): string {
  const p = (x: number) => String(Number(x.toPrecision(2))); // 100, not 1.0e+2
  if (s < 1e-3) return `${p(s * 1e6)} µs`;
  if (s < 1) return `${p(s * 1e3)} ms`;
  if (s < 120) return `${p(s)} s`;
  if (s < 7200) return `${p(s / 60)} min`;
  return `${p(s / 3600)} h`;
}

/** Signed percent: +0.12 %, −1.66 %. */
export function pct(x: number, digits = 2): string {
  const v = (x * 100).toFixed(digits);
  return `${x >= 0 ? "+" : "−"}${v.replace("-", "")} %`;
}

export const pow2 = (L: number) => `2${String(L).replace(/\d/g, (d) => "⁰¹²³⁴⁵⁶⁷⁸⁹"[+d])}`;
