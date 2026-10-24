import type { Param } from "./data";

/**
 * Smallest shortlisted signature whose p99 full signing time fits the budget.
 * Same rule as analysis/nb_03_pareto.py: total_p99 / rate <= budget, then the minimum sig_bytes
 * (first in file order on ties, like pandas idxmin). `scripts/check_explorer.mjs` checks it against
 * analysis/out/03_pareto/smallest_per_budget.md.
 */
export function smallestWithin(params: Param[], limit: number, rate: number, budgetS: number): Param | null {
  let best: Param | null = null;
  for (const p of params) {
    if (p.limit !== limit || p.total_p99 / rate > budgetS) continue;
    if (!best || p.bytes < best.bytes) best = p;
  }
  return best;
}

/** Smallest hardware-wallet-safe set at this limit: the baseline that savings are quoted against. */
export function hwSafeBaseline(params: Param[], limit: number): Param | null {
  let best: Param | null = null;
  for (const p of params) {
    if (p.limit === limit && p.profile === "hw_wallet_safe" && (!best || p.bytes < best.bytes)) best = p;
  }
  return best;
}

/** Witness bytes count 1/4 vbyte each. */
export const bytesToVbytes = (bytes: number) => bytes / 4;
