"""Đợi baseline gpt-4o mini xong, rồi chạy MemView trên ba backbone cùng hạng.

Mỗi model: MemView đầy đủ, không memory, memory bảng khác. Prompt theo dòng model.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = (
    ("azure-4.1-mini", "41mini"),
    ("claude-haiku-4-5", "haiku45"),
    ("gemini-2.5-flash-lite", "flashlite"),
)
_BASELINE_MARKERS = (
    "run_baselines_azure.py",
    "run_baseline.py",
    "run_chain_of_table_open_vitabqa.py",
    "mad_debate",
)


def _env(model: str) -> dict[str, str]:
    env = os.environ.copy()
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    base = env["AZURE_BASE_URL"].rstrip("/")
    env.update({
        "VLLM_BASE_URL": base,
        "VLLM_API_KEY": env["AZURE_API_KEY"],
        "VLLM_MODEL": model,
        "OPENAI_BASE_URL": base,
        "OPENAI_API_KEY": env["AZURE_API_KEY"],
        "MAS_RETRIES": env.get("MAS_RETRIES", "8"),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
    })
    return env


def _baseline_commands() -> str:
    script = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Select-Object -ExpandProperty CommandLine"
    )
    out = subprocess.check_output(
        ["powershell", "-NoProfile", "-Command", script],
        text=True, encoding="utf-8", errors="replace",
    )
    return out


def _wait_baselines() -> None:
    while True:
        try:
            commands = _baseline_commands()
        except subprocess.CalledProcessError as exc:
            print(f"không đọc được tiến trình: {exc}", flush=True)
            time.sleep(30)
            continue
        if any(marker in commands for marker in _BASELINE_MARKERS):
            print("baseline còn chạy, đợi 60s", flush=True)
            time.sleep(60)
            continue
        print("baseline đã xong", flush=True)
        return


def _run_model(model: str, run: str) -> int:
    env = _env(model)
    log_dir = ROOT / "outputs" / "mas_tqa" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("suite_v10", run, {}),
        ("suite_v10_nomem", run, {}),
        ("suite_v10", f"{run}cross", {"MAS_MEMORY_SCOPE": "cross"}),
    ]
    procs = []
    for method, label, overlay in jobs:
        job_env = {**env, **overlay}
        log = log_dir / f"{method}.{label}.log"
        cmd = [
            sys.executable, "scripts/run_mas_tqa.py",
            "--method", method, "--qas", "dataset/qas_test.json",
            "--run", label, "--workers", "4",
        ]
        handle = log.open("a", encoding="utf-8")
        procs.append((model, label, subprocess.Popen(cmd, cwd=ROOT, env=job_env, stdout=handle, stderr=subprocess.STDOUT), handle))
        print(f"started {model} {method} run{label}", flush=True)
    code = 0
    for name, label, proc, handle in procs:
        status = proc.wait()
        handle.close()
        print(f"done {name} {label} exit {status}", flush=True)
        code = code or status
    return code


def main() -> None:
    _wait_baselines()
    code = 0
    for model, run in MODELS:
        code = code or _run_model(model, run)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
