import raw from "@/content/data.json";

export interface ValidationRow {
  id: string;
  grind: string;
  n: number;
  expected: number;
  ratio: number;
  ci95: number;
  z: number;
  ks_p_holm: number;
  p99: number;
  geo_p99: number;
  p999: number;
  geo_p999: number;
  comp_per_s: number;
  verified: boolean;
}

export interface Oq3Row {
  id: string;
  w: number;
  S: number;
  expected: number;
  ratio: number;
  n: number;
  chain_steps: number;
  saved: number;
  run: string;
  p99_mcu: number;
  p99_cpu: number;
}

export interface Param {
  id: string;
  layout: string;
  profile: string;
  variant: string;
  limit: number;
  bytes: number;
  total_p99: number;
  total_mean: number;
  grind_share: number;
  verify_comp: number;
  z1: boolean;
}

export interface SignerClass {
  id: string;
  label: string;
  rate: number;
  kind: "measured" | "derived" | "cited";
}

export interface SiteData {
  run: string;
  oq3_run: string;
  rerun_run: string;
  headline: {
    configs: number;
    samples: number;
    sum_z2: number;
    dof: number;
    outside_ci: number;
    gpu_raw: number;
    cpu_12t: number;
    cpu_1t: number;
  };
  rerun: { id: string; n: number; ratio: number; ci95: number; z: number; verified: boolean };
  validation: ValidationRow[];
  oq3: Oq3Row[];
  params: Param[];
  ladder: SignerClass[];
  threats: { id: string; threat: string; severity: "Low" | "Medium" | "High"; status: string }[];
}

export const data = raw as unknown as SiteData;

export const PROFILE_LABEL: Record<string, string> = {
  blockstream_ref: "Kudinov–Nick reference",
  hw_wallet_safe: "Hardware-wallet safe",
  gpu_signer_moderate: "Heavy signer (moderate)",
  gpu_signer_max: "Heavy signer (max)",
  wots_c_stress: "WOTS+C stress point",
  fors_c_stress: "FORS+C stress point",
};

export const GRIND_FAMILIES = ["WOTS+C", "FORS+C", "PORS+FP"] as const;

/** Family of a validation row, from the notebook's grind label (e.g. "FORS+C R", "FORS+C ctr"). */
export function family(grind: string): (typeof GRIND_FAMILIES)[number] {
  if (grind.startsWith("WOTS")) return "WOTS+C";
  if (grind.startsWith("PORS")) return "PORS+FP";
  return "FORS+C";
}
