"""Chuyển outputs/d13/records.jsonl thành 3 file prediction một đáp án (một mỗi arm), để chạy BIF.

Theo đúng quy tắc lỗi của scripts/analyze_d13.py: bản ghi có "error" và thông điệp
"final_answer: None is not of type" được chấm là Null nghĩa đen; các lỗi khác là chuỗi rỗng
(BIF tự bỏ qua đáp án rỗng, không phải đoán số liệu).
"""
from __future__ import annotations

import json
from pathlib import Path

RECORDS = Path("outputs/d13/records.jsonl")
OUT_DIR = Path("outputs/d13/predictions")


def main() -> None:
    rows = [json.loads(line) for line in RECORDS.read_text(encoding="utf-8").splitlines()]
    arms: dict[str, list[dict]] = {}
    for row in rows:
        arm = row["arm"]
        if "error" in row:
            literal_null = "final_answer: None is not of type" in str(row.get("error", ""))
            prediction = ["Null"] if literal_null else [""]
        else:
            prediction = row.get("prediction") or [""]
        arms.setdefault(arm, []).append(
            {"qa_id": row["qa_id"], "table_id": row["table_id"], "prediction": prediction}
        )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for arm, preds in arms.items():
        out = OUT_DIR / f"{arm}.json"
        out.write_text(
            json.dumps({"manifest": {"source": "outputs/d13/records.jsonl", "arm": arm}, "predictions": preds},
                        ensure_ascii=False),
            encoding="utf-8",
        )
        print(arm, len(preds), "->", out)


if __name__ == "__main__":
    main()
