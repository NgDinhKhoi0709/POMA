"""Chạy một phương pháp (hoặc suite nhiều phương pháp dùng chung tầng đầu) trên endpoint vLLM tự host.

Biến môi trường: VLLM_BASE_URL (vd. http://<ip>:<port>/v1), VLLM_API_KEY, VLLM_MODEL (mặc định Qwen/Qwen3-8B).

python scripts/run_mas_tqa.py --method fs --qas outputs/mas_tqa/qas_dev_200.json --run 1
python scripts/run_mas_tqa.py --method suite --run 1   # knn_fs, evid, cascade3, memxam
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.io import load_qas_records  # noqa: E402
from mas_tqa.client import VLLMClient  # noqa: E402
from mas_tqa.methods import METHODS, SUITES  # noqa: E402

SUITE_MEMBERS = {"suite": ["knn_fs", "evid", "cascade3", "cascade3b", "judge_only", "memxam"]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--method", required=True, choices=sorted(METHODS) + sorted(SUITES))
    ap.add_argument("--qas", default="outputs/mas_tqa/qas_dev_200.json")
    ap.add_argument("--run", default="1", help="Nhãn lần chạy (để chạy lặp ≥3 lần).")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out-dir", default="outputs/mas_tqa")
    args = ap.parse_args()

    names = SUITE_MEMBERS.get(args.method, [args.method])
    qas = load_qas_records(ROOT / args.qas)[: args.limit]
    qas.sort(key=lambda q: q["table_id"])  # cùng bảng liền nhau để tận dụng prefix cache
    base = ROOT / args.out_dir / Path(args.qas).stem
    base.mkdir(parents=True, exist_ok=True)
    outs = {n: base / f"{n}.run{args.run}.jsonl" for n in names}
    done = set.intersection(*[
        {json.loads(line)["qa_id"] for line in p.read_text(encoding="utf-8").splitlines() if line.strip()}
        if p.exists() else set()
        for p in outs.values()
    ])
    todo = [q for q in qas if q["qa_id"] not in done]
    print(f"{args.method} run{args.run}: {len(todo)} câu cần chạy ({len(done)} đã có) -> {base}", flush=True)

    client, lock = VLLMClient(), threading.Lock()
    fn = SUITES.get(args.method) or (lambda c, qa: {args.method: METHODS[args.method](c, qa)})
    t0 = time.time()

    def one(qa: dict) -> dict:
        s = time.time()
        results = fn(client, qa)
        recs = {}
        for name, res in results.items():
            u = res.pop("usage")
            recs[name] = {
                "qa_id": qa["qa_id"], "table_id": qa["table_id"], "question": qa["question"],
                "groundtruth": qa["answer"], "method": name, "run": args.run,
                "calls": u.calls, "prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens,
                "elapsed_s": round(time.time() - s, 2), **res,
            }
        return recs

    handles = {n: p.open("a", encoding="utf-8") for n, p in outs.items()}
    try:
        with ThreadPoolExecutor(args.workers) as ex:
            futs = [ex.submit(one, q) for q in todo]
            for i, f in enumerate(as_completed(futs), 1):
                try:
                    recs = f.result()
                except Exception as e:  # ghi lỗi để không mất cả lượt chạy
                    print(f"[error] {e!r}", flush=True)
                    continue
                with lock:
                    for name, rec in recs.items():
                        handles[name].write(json.dumps(rec, ensure_ascii=False) + "\n")
                        handles[name].flush()
                if i % 25 == 0:
                    print(f"  {i}/{len(todo)}  {time.time() - t0:.0f}s", flush=True)
    finally:
        for h in handles.values():
            h.close()
    print(f"xong trong {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
