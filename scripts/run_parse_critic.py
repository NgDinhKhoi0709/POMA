"""Chạy Parse-Critic cho mọi bảng của một tập câu hỏi (cache theo bảng).

python scripts/run_parse_critic.py --qas outputs/mas_tqa/qas_dev_200.json
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.io import load_qas_records  # noqa: E402
from mas_tqa.client import VLLMClient  # noqa: E402
from mas_tqa.parse_critic import critique, load_cache  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--qas", default="outputs/mas_tqa/qas_dev_200.json")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    tids = sorted({q["table_id"] for q in load_qas_records(ROOT / args.qas)})
    todo = [t for t in tids if t not in load_cache()]
    print(f"{len(tids)} bảng, cần chạy {len(todo)}", flush=True)
    client = VLLMClient()
    with ThreadPoolExecutor(args.workers) as ex:
        for i, rec in enumerate(ex.map(lambda t: critique(client, t), todo), 1):
            if i % 20 == 0:
                print(f"  {i}/{len(todo)}", flush=True)
    cache = load_cache()
    flagged = [t for t in tids if t in cache and not cache[t]["ok"]]
    print(f"xong: {len(flagged)}/{len(tids)} bảng bị agent đánh giá parse chưa trung thành", flush=True)


if __name__ == "__main__":
    main()
