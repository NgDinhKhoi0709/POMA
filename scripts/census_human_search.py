"""Đo phần "tìm" của chuỗi hành động người đọc bảng, tất định, không gọi API.

Chuỗi được mô phỏng: đọc câu hỏi -> lấy keyword -> tìm hàng neo (ô có tên thực thể nằm trong câu hỏi)
và cột thuộc tính (header khớp câu hỏi) -> giao hàng x cột -> kiểm đủ/thiếu -> thiếu thì tìm tiếp với
luật khớp nới lỏng -> vẫn thiếu thì fallback đọc cả bảng.

Câu hỏi: ô gold có nằm trong tập ứng viên không (recall), tập ứng viên nhỏ cỡ nào so với cả bảng,
và cổng "đủ/thiếu" có tách được câu dễ khỏi câu khó không. Chỉ chạy trên train/dev.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.normalization import normalize_text  # noqa: E402
from gap_tqa.table import contained, grid, search, syllables  # noqa: E402,F401


def gold_cells(gold: str, rows: list[list[str]]) -> tuple[str, set[tuple[int, int]]]:
    g = normalize_text(gold)
    exact = {(r, c) for r, row in enumerate(rows) for c, v in enumerate(row) if normalize_text(v) == g}
    if exact:
        return "cell", exact
    if len(g) >= 2:
        span = {(r, c) for r, row in enumerate(rows) for c, v in enumerate(row) if g in normalize_text(v)}
        if span:
            return "span_in_cell", span
    return "other", set()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--splits", nargs="+", default=["train", "dev"])
    ap.add_argument("--out", default="outputs/graph_census/human_search.json")
    args = ap.parse_args()

    tables = {t["table_id"]: t for t in json.load(open("dataset/table.json", encoding="utf-8"))["table"]}
    grids = {tid: grid(t) for tid, t in tables.items()}
    report: dict[str, object] = {}

    for split in args.splits:
        qas = json.load(open(f"dataset/qas_{split}.json", encoding="utf-8"))["qas"]
        stats: dict[str, list] = defaultdict(list)
        by_type: dict[str, Counter] = defaultdict(Counter)
        for q in qas:
            headers, rows = grids[q["table_id"]]
            kind, gold = gold_cells(q["answer"], rows)
            if not gold:
                continue
            n_cells = sum(len(r) for r in rows) or 1
            status, cand, arows, cols = search(q["question"], headers, rows, relaxed=False)
            loop = False
            if status != "đủ":  # thiếu -> tìm tiếp với luật nới lỏng
                res2 = search(q["question"], headers, rows, relaxed=True)
                if res2[0] == "đủ" or (status == "không thấy" and res2[1]):
                    (status, cand, arows, cols), loop = res2, True
            hit = bool(gold & cand)
            stats[status].append((hit, len(cand), len(cand) / n_cells, loop, kind))
            ttype = str(tables[q["table_id"]]["table_type"])
            by_type[ttype]["n"] += 1
            if status == "đủ":
                row_view = {(r, c) for r in arows for c in range(len(rows[r]))}
                diag = by_type[ttype]
                diag["du"] += 1
                diag["hit_du"] += hit
                diag["row_ok"] += any(r in arows for r, _ in gold)
                diag["col_ok"] += any(c in cols for _, c in gold)
                diag["hit_row_view"] += bool(gold & row_view)
                stats["_row_view_size"].append(len(row_view))

        row_view_sizes = stats.pop("_row_view_size", [])
        n = sum(len(v) for v in stats.values())
        rep = {"n_answer_in_table": n, "of_split": len(qas)}
        for status, rows_ in sorted(stats.items(), key=lambda kv: -len(kv[1])):
            rep[status] = {
                "share_pct": round(100 * len(rows_) / n, 1),
                "gold_in_candidates_pct": round(100 * sum(r[0] for r in rows_) / len(rows_), 1),
                "median_candidates": statistics.median(r[1] for r in rows_) if rows_ else 0,
                "median_fraction_of_table_pct": round(100 * statistics.median(r[2] for r in rows_), 1) if rows_ else 0,
                "reached_by_relaxed_loop": sum(r[3] for r in rows_),
                "gold_kind": dict(Counter(r[4] for r in rows_)),
            }
        rep["recall_all_pct"] = round(100 * sum(r[0] for v in stats.values() for r in v) / n, 1)
        pct = lambda a, b: round(100 * a / b, 1) if b else None  # noqa: E731
        total = sum(by_type.values(), Counter())
        by_type["ALL"] = total
        rep["du_row_view_median_cells"] = statistics.median(row_view_sizes) if row_view_sizes else 0
        rep["by_table_type"] = {
            t: {
                "n": c["n"],
                "du_pct": pct(c["du"], c["n"]),
                "when_du": {
                    "gold_in_row_x_col_pct": pct(c["hit_du"], c["du"]),
                    "right_row_pct": pct(c["row_ok"], c["du"]),
                    "right_col_pct": pct(c["col_ok"], c["du"]),
                    "gold_in_full_anchor_rows_pct": pct(c["hit_row_view"], c["du"]),
                },
            }
            for t, c in sorted(by_type.items(), key=lambda kv: -kv[1]["n"])
        }
        report[split] = rep

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
