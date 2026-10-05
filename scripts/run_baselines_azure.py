"""Baseline trên Azure gpt-4o mini (model id azure-4o-mini), cùng bộ test với MemView.

Zero-shot, few-shot, few-shot 3 mẫu, multi-agent debate dùng prompt GPT trong mas_tqa.
CoAgt và Chain-of-Table gọi cùng endpoint. MemView không memory đã chạy riêng.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _env() -> dict[str, str]:
    env = os.environ.copy()
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    base = env["AZURE_BASE_URL"].rstrip("/")
    key = env["AZURE_API_KEY"]
    env.update({
        "VLLM_BASE_URL": base,
        "VLLM_API_KEY": key,
        "VLLM_MODEL": "azure-4o-mini",
        "OPENAI_BASE_URL": base,
        "OPENAI_API_KEY": key,
        "MAS_RETRIES": env.get("MAS_RETRIES", "8"),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
    })
    return env


def main() -> None:
    env = _env()
    log_dir = ROOT / "outputs" / "mas_tqa" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    jobs = [
        ("zs_qwen", [py, "scripts/run_mas_tqa.py", "--method", "zs_qwen", "--qas", "dataset/qas_test.json", "--run", "gpt4omini", "--workers", "6"]),
        ("fs_qwen", [py, "scripts/run_mas_tqa.py", "--method", "fs_qwen", "--qas", "dataset/qas_test.json", "--run", "gpt4omini", "--workers", "6"]),
        ("fs_qwen_sc3", [py, "scripts/run_mas_tqa.py", "--method", "fs_qwen_sc3", "--qas", "dataset/qas_test.json", "--run", "gpt4omini", "--workers", "4"]),
        ("mad_debate", [py, "scripts/run_mas_tqa.py", "--method", "mad_debate", "--qas", "dataset/qas_test.json", "--run", "gpt4omini", "--workers", "4"]),
        ("coagt", [py, "scripts/run_baseline.py", "coagt", "--model", "azure-4o-mini", "--max-workers", "4", "--run-id", "azure-4o-mini", "--resume", "--skip-eval"]),
        ("chain_of_table", [py, "baselines/chain_of_query/run_chain_of_table_open_vitabqa.py", "--model", "azure-4o-mini", "--workers", "4", "--out", "outputs/mas_tqa/qas_test/chain_of_table.rungpt4omini.jsonl"]),
    ]
    procs = []
    for name, cmd in jobs:
        log = log_dir / f"{name}.gpt4omini.log"
        handle = log.open("a", encoding="utf-8")
        procs.append((name, subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT), handle))
        print(f"started {name} -> {log}", flush=True)
    code = 0
    for name, proc, handle in procs:
        status = proc.wait()
        handle.close()
        print(f"done {name} exit {status}", flush=True)
        code = code or status
    raise SystemExit(code)


if __name__ == "__main__":
    main()
