// Checks the explorer rule (lib/explorer.ts) against the notebook output it re-implements:
// analysis/out/03_pareto/smallest_per_budget.md and the hardware-wallet-safe baselines in fee_deltas.csv.
//   npm run check        (Node >= 23: runs the TypeScript module directly)
import { readFileSync } from "node:fs";
import { smallestWithin, hwSafeBaseline } from "../lib/explorer.ts";

const root = new URL("../../", import.meta.url);
const data = JSON.parse(readFileSync(new URL("site/content/data.json", root), "utf8"));
const md = readFileSync(new URL("analysis/out/03_pareto/smallest_per_budget.md", root), "utf8");
const classByLabel = Object.fromEntries(data.ladder.map((c) => [c.label, c]));

let n = 0;
const bad = [];
for (const line of md.split("\n").slice(2)) {
  const cells = line.split("|").slice(1, -1).map((s) => s.trim());
  if (cells.length < 6) continue;
  const [limit, label, , budget, bytes, paramId] = cells;
  const got = smallestWithin(data.params, +limit.slice(2), classByLabel[label].rate, +budget);
  const want = paramId === "none fits" ? null : paramId;
  n++;
  if ((got?.id ?? null) !== want || (want && got.bytes !== +bytes)) bad.push({ limit, label, budget, want, got: got?.id ?? null });
}

for (const f of data.fees) {
  const base = hwSafeBaseline(data.params, +String(f.sig_limit).slice(2));
  n++;
  if (base?.bytes !== f.vs_hw_wallet_safe_B) bad.push({ baseline: f.sig_limit, want: f.vs_hw_wallet_safe_B, got: base?.bytes });
}

if (bad.length) {
  console.error(`FAIL: ${bad.length} of ${n} checks`, bad);
  process.exit(1);
}
console.log(`ok: ${n} checks match the notebook`);
