"""E6: nvidia-smi telemetry at 10 Hz, written to CSV while running and Parquet on stop."""
import subprocess
from pathlib import Path

import pandas as pd

FIELDS = "timestamp,power.draw,clocks.sm,temperature.gpu,clocks_event_reasons.active,pstate"
COLUMNS = ["timestamp", "power_w", "sm_mhz", "temp_c", "event_reasons", "pstate"]

# clocks_event_reasons bits (NVML): 0x4 SW power cap is the expected steady state at 45 W TGP;
# thermal and hardware slowdowns mark windows to discard.
SW_POWER_CAP = 0x4
THROTTLE_MASK = 0x8 | 0x20 | 0x40 | 0x80  # HW slowdown, SW thermal, HW thermal, HW power brake


class PowerLogger:
    def __init__(self, out_path, interval_ms=100):
        self.out_path = Path(out_path)
        self.csv_path = self.out_path.with_suffix(".csv")
        self.interval_ms = interval_ms
        self.proc = None

    def __enter__(self):
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.csv_path.open("w")
        self.proc = subprocess.Popen(
            ["nvidia-smi", f"--query-gpu={FIELDS}", "--format=csv,noheader,nounits",
             f"-lms", str(self.interval_ms)],
            stdout=self._fh, stderr=subprocess.DEVNULL,
        )
        return self

    def __exit__(self, *exc):
        self.proc.terminate()
        self.proc.wait(timeout=10)
        self._fh.close()
        df = load_csv(self.csv_path)
        df.to_parquet(self.out_path, index=False)
        self.csv_path.unlink()
        return False


def load_csv(path):
    df = pd.read_csv(path, header=None, names=COLUMNS, skipinitialspace=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y/%m/%d %H:%M:%S.%f")
    df["power_w"] = pd.to_numeric(df["power_w"], errors="coerce")
    df["sm_mhz"] = pd.to_numeric(df["sm_mhz"], errors="coerce")
    df["temp_c"] = pd.to_numeric(df["temp_c"], errors="coerce")
    df["event_reasons"] = df["event_reasons"].map(lambda s: int(str(s), 16))
    df["throttled"] = (df["event_reasons"] & THROTTLE_MASK) != 0
    return df


def energy_joules(df, t0, t1):
    """Integrate power over [t0, t1] (pandas Timestamps, local clock as nvidia-smi reports)."""
    w = df[(df.timestamp >= t0) & (df.timestamp <= t1)]
    if len(w) < 2:
        return float("nan")
    dt = w.timestamp.diff().dt.total_seconds().fillna(0)
    return float((w.power_w * dt).sum())
