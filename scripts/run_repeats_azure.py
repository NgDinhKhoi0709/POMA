"""Hai lượt lặp MemView và baseline trên bốn backbone Azure.

Nhãn r2 và r3, không đụng file lần chạy đầu. Mỗi lượt, một model một lúc:
MemView (suite_v10), zero-shot, few-shot, few-shot 3 mẫu, debate, CoAgt, Chain-of-Table.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = (
    ("azure-4o-mini", "gpt4omini"),
    ("azure-4.1-mini", "41mini"),
    ("claude-haiku-4-5", "haiku45"),
    ("gemini-2.5-flash-lite", "flashlite"),
)
REPEATS = ("r2", "r3")


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


def _jobs(py: str, model: str, run: str, repeat: str) -> list[tuple[str, list[str]]]:
    qas = ["--qas", "dataset/qas_test.json", "--run", run]
    return [
        ("suite_v10", [py, "scripts/run_mas_tqa.py", "--method", "suite_v10", *qas, "--workers", "4"]),
        ("zs_qwen", [py, "scripts/run_mas_tqa.py", "--method", "zs_qwen", *qas, "--workers", "4"]),
        ("fs_qwen", [py, "scripts/run_mas_tqa.py", "--method", "fs_qwen", *qas, "--workers", "4"]),
        ("fs_qwen_sc3", [py, "scripts/run_mas_tqa.py", "--method", "fs_qwen_sc3", *qas, "--workers", "3"]),
        ("mad_debate", [py, "scripts/run_mas_tqa.py", "--method", "mad_debate", *qas, "--workers", "3"]),
        ("coagt", [py, "scripts/run_baseline.py", "coagt", "--model", model, "--max-workers", "3", "--run-id", f"{model}-{repeat}", "--resume", "--skip-eval"]),
        ("chain_of_table", [py, "baselines/chain_of_query/run_chain_of_table_open_vitabqa.py", "--model", model, "--workers", "3", "--out", f"outputs/mas_tqa/qas_test/chain_of_table.run{run}.jsonl"]),
    ]


def _run_model(model: str, run: str, repeat: str) -> int:
    env = _env(model)
    log_dir = ROOT / "outputs" / "mas_tqa" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    procs = []
    for name, cmd in _jobs(sys.executable, model, run, repeat):
        log = log_dir / f"{name}.{run}.log"
        handle = log.open("a", encoding="utf-8")
        procs.append((name, subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT), handle))
        print(f"started {model} {repeat} {name}", flush=True)
    code = 0
    for name, proc, handle in procs:
        status = proc.wait()
        handle.close()
        print(f"done {model} {repeat} {name} exit {status}", flush=True)
        code = code or status
    src = ROOT / "outputs" / "baselines" / "coagt" / f"{model}-{repeat}" / "results.jsonl"
    dst = ROOT / "outputs" / "mas_tqa" / "qas_test" / f"coagt.run{run}.jsonl"
    if src.exists():
        subprocess.run([sys.executable, "scripts/convert_baseline_run.py", str(src), str(dst)], cwd=ROOT, check=False)
    return code


def _eval() -> None:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    py = sys.executable
    methods = ("memview_q", "zs_qwen", "fs_qwen", "fs_qwen_sc3", "mad_debate", "chain_of_table", "coagt")
    files = [f"{method}.run{tag}{rep}" for _model, tag in MODELS for rep in ("", *REPEATS) for method in methods]
    log = ROOT / "outputs" / "mas_tqa" / "logs" / "eval_repeats.txt"
    with log.open("w", encoding="utf-8") as handle:
        subprocess.run([py, "scripts/score_paper_metrics.py", "--files", *files], cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT)
        for _model, tag in MODELS:
            for rep in ("", *REPEATS):
                run = f"{tag}{rep}"
                names = [f"{method}.run{run}" for method in methods]
                subprocess.run(
                    [py, "scripts/score_lenient.py", "--ref", f"memview_q.run{run}", "--files", *names],
                    cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT,
                )
    print(f"eval -> {log}", flush=True)


def main() -> None:
    code = 0
    for repeat in REPEATS:
        for model, tag in MODELS:
            code = code or _run_model(model, f"{tag}{repeat}", repeat)
    _eval()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
