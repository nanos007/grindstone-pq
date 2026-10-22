"""Environment check: compiles a trivial NVRTC kernel and appends a manifest record."""
import json
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifest.jsonl"


def gpu_info():
    import cupy as cp

    k = cp.RawKernel(
        r'extern "C" __global__ void inc(unsigned *x){ x[threadIdx.x] += threadIdx.x; }',
        "inc",
        options=("--gpu-architecture=sm_89",),
    )
    x = cp.zeros(32, dtype=cp.uint32)
    k((1,), (32,), (x,))
    assert int(x.sum()) == sum(range(32)), "NVRTC smoke kernel failed"

    props = cp.cuda.runtime.getDeviceProperties(0)
    smi = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,driver_version,power.limit,clocks.max.sm,memory.total",
         "--format=csv,noheader"],
        capture_output=True, text=True,
    ).stdout.strip()
    return {
        "gpu_name": props["name"].decode(),
        "sm_count": props["multiProcessorCount"],
        "compute_capability": f'{props["major"]}.{props["minor"]}',
        "cuda_runtime": cp.cuda.runtime.runtimeGetVersion(),
        "cuda_driver": cp.cuda.runtime.driverGetVersion(),
        "nvrtc": ".".join(map(str, cp.cuda.nvrtc.getVersion())),
        "cupy": cp.__version__,
        "nvidia_smi": smi,
        "nvrtc_smoke": "ok",
    }


def cpu_info():
    import cpuinfo

    info = cpuinfo.get_cpu_info()
    flags = set(info.get("flags", []))
    return {
        "cpu_brand": info.get("brand_raw"),
        "cpu_count_logical": info.get("count"),
        "sha_ni": "sha" in flags or "sha_ni" in flags,
        "avx2": "avx2" in flags,
    }


def os_info():
    ram_gb = None
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_PhysicalMemory | ForEach-Object { $_.Capacity/1GB }) -join ','"],
            capture_output=True, text=True,
        ).stdout.strip()
        ram_gb = out
    except OSError:
        pass
    return {
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "ram_dimms_gb": ram_gb,
        "toolchain": "cupy+nvrtc (no nvcc/WSL); CPU baseline via ziglang cc",
    }


def main():
    rec = {
        "kind": "env_check",
        "run_id": str(uuid.uuid4()),
        "utc": datetime.now(timezone.utc).isoformat(),
        **gpu_info(),
        **cpu_info(),
        **os_info(),
    }
    try:
        r = subprocess.run(["git", "rev-parse", "--verify", "-q", "HEAD"],
                           cwd=ROOT, capture_output=True, text=True)
        rec["git_sha"] = r.stdout.strip() if r.returncode == 0 else None
    except OSError:
        rec["git_sha"] = None
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(json.dumps(rec, indent=2))


if __name__ == "__main__":
    main()
