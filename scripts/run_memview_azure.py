"""Chạy MemView và các ablation trên Azure gpt-4o mini.

Đọc AZURE_BASE_URL và AZURE_API_KEY từ .env. Model id trên proxy là azure-4o-mini.
Ba tiến trình: MemView đầy đủ, không memory, memory khác bảng.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_env() -> dict[str, str]:
    env = os.environ.copy()
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    env["VLLM_BASE_URL"] = env["AZURE_BASE_URL"].rstrip("/")
    env["VLLM_API_KEY"] = env["AZURE_API_KEY"]
    env["VLLM_MODEL"] = "azure-4o-mini"
    env["MAS_RETRIES"] = env.get("MAS_RETRIES", "8")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    return env


def main() -> None:
    env = _load_env()
    log_dir = ROOT / "outputs" / "mas_tqa" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("suite_v10", "gpt4omini", {}),
        ("suite_v10_nomem", "gpt4omini", {}),
        ("suite_v10", "gpt4ominicross", {"MAS_MEMORY_SCOPE": "cross"}),
    ]
    extra = sys.argv[1:]
    procs = []
    for method, run, overlay in jobs:
        job_env = {**env, **overlay}
        log = log_dir / f"{method}.{run}.log"
        cmd = [
            sys.executable, "scripts/run_mas_tqa.py",
            "--method", method, "--qas", "dataset/qas_test.json",
            "--run", run, "--workers", "4", *extra,
        ]
        handle = log.open("a", encoding="utf-8")
        procs.append((method, run, subprocess.Popen(cmd, cwd=ROOT, env=job_env, stdout=handle, stderr=subprocess.STDOUT), handle))
        print(f"started {method} run{run} -> {log}", flush=True)
    code = 0
    for method, run, proc, handle in procs:
        status = proc.wait()
        handle.close()
        print(f"done {method} run{run} exit {status}", flush=True)
        code = code or status
    raise SystemExit(code)


if __name__ == "__main__":
    main()
