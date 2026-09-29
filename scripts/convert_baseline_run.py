"""Đổi results.jsonl của scripts/run_baseline.py (CoAgt, ...) sang định dạng mas_tqa để chấm chung
(scripts/score_lenient.py, scripts/bif_all.py).

    python scripts/convert_baseline_run.py outputs/baselines/coagt/<run>/results.jsonl \
        outputs/mas_tqa/qas_test/coagt.runq1.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def convert(rec: dict) -> dict:
    pred = rec.get("prediction")
    return {"qa_id": rec["qa_id"], "table_id": rec.get("table_id"), "question": rec["question"],
            "groundtruth": rec.get("answer"), "method": rec.get("method", "baseline"),
            "prediction": pred if isinstance(pred, list) else [str(pred or "")],
            "calls": rec.get("api_calls", 0), "prompt_tokens": rec.get("prompt_tokens", 0),
            "completion_tokens": rec.get("completion_tokens", 0)}


def main(src: str, dst: str) -> None:
    recs = {}
    for line in Path(src).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            recs[r["qa_id"]] = convert(r)  # trùng qa_id (chạy bù) thì giữ bản sau
    Path(dst).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs.values()), encoding="utf-8")
    print(f"{len(recs)} câu -> {dst}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
