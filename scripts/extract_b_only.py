"""Tách dự đoán của riêng agent B từ trace MemView (suite_v10) thành một file dự đoán mas_tqa, để chấm bằng các
script chấm thông thường. Câu B không chạy (bảng Markdown-KV vượt ngữ cảnh) ghi dự đoán rỗng.

python scripts/extract_b_only.py --src memview_q.runv11test --dst b_only_q.runv11test
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="outputs/mas_tqa/qas_test")
    ap.add_argument("--src", default="memview_q.runv11test")
    ap.add_argument("--dst", default="b_only_q.runv11test")
    args = ap.parse_args()
    d = ROOT / args.dir
    out, missing = [], 0
    for line in (d / f"{args.src}.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        b = r.get("trace", {}).get("B")
        if b is None:
            missing, b = missing + 1, ""
        out.append({k: r[k] for k in ("qa_id", "table_id", "question", "groundtruth")}
                   | {"method": "b_only_q", "prediction": [b], "calls": 1, "prompt_tokens": 0, "completion_tokens": 0})
    (d / f"{args.dst}.jsonl").write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in out), encoding="utf-8")
    print(f"{len(out)} câu -> {args.dst}.jsonl (B không chạy: {missing})")


if __name__ == "__main__":
    main()
