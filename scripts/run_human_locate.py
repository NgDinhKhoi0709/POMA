"""Node Locate theo chuỗi hành động người đọc bảng, so với Locate trên cả bảng (dev, cặp ghép).

Arm FULL : 8B chọn ID ô trên toàn bộ bảng (triplet có đường dẫn header).
Arm HUMAN: tìm hàng neo tất định -> 8B chọn ID trên các hàng neo, hoặc trả THIẾU
           -> nới ra hàng neo + cột khớp -> vẫn THIẾU thì đọc cả bảng. Tối đa 3 bước.
Đo: tỉ lệ định vị đúng ô gold, độ hiệu chỉnh của THIẾU, số câu được bước mở rộng cứu, token.
Chỉ chạy trên câu dev có gold là ô hoặc đoạn trong ô.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from scripts.census_human_search import gold_cells, grid, search  # noqa: E402
from src.services.llm_client import LLMClient  # noqa: E402

PROMPT = """Bạn là bộ định vị ô trong bảng. Mỗi dòng dưới đây là một ô: ID | hàng | cột | giá trị.
Bảng: {title}
{cells}

Câu hỏi: {question}

Chọn đúng MỘT ID của ô chứa thông tin trả lời câu hỏi. Nếu không ô nào trong danh sách trên chứa đủ thông tin, trả lời THIẾU.
Chỉ in ra ID (ví dụ r3c2) hoặc THIẾU, không giải thích."""
ANSWER_RE = re.compile(r"\br\d+c\d+\b|THIẾU", re.IGNORECASE)


def render(headers, rows, view) -> str:
    ncol = max((len(r) for r in rows + headers), default=0)
    path = [" › ".join(dict.fromkeys(h[c] for h in headers if c < len(h) and h[c])) for c in range(ncol)]
    lines = []
    for r, c in sorted(view):
        label = next((v for v in rows[r] if v), "")
        lines.append(f"r{r}c{c} | {label[:60]} | {path[c] if c < ncol else ''} | {rows[r][c]}")
    return "\n".join(lines)


def ask(client: LLMClient, table, headers, rows, view, question) -> tuple[str, int]:
    prompt = PROMPT.format(title=table["table_title"], cells=render(headers, rows, view), question=question)
    before = client.total_prompt_tokens
    raw = client.generate_text(prompt, agent_name="human_locate")
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    found = ANSWER_RE.findall(raw)
    ans = found[-1].lower() if found else "parse_error"
    return ("THIẾU" if ans == "thiếu" else ans), client.total_prompt_tokens - before


def cell_id(r: int, c: int) -> str:
    return f"r{r}c{c}"


def run_one(q, table, headers, rows):
    client = LLMClient()
    client.set_qa_id(q["qa_id"])
    kind, gold = gold_cells(q["answer"], rows)
    gold_ids = {cell_id(*g) for g in gold}
    full = {(r, c) for r in range(len(rows)) for c in range(len(rows[r]))}

    pred_full, tok_full = ask(client, table, headers, rows, full, q["question"])

    status, _, arows, cols = search(q["question"], headers, rows, relaxed=False)
    if not arows and not cols:
        status, _, arows, cols = search(q["question"], headers, rows, relaxed=True)
    view_b = {(r, c) for r in arows for c in range(len(rows[r]))}
    if not view_b:  # không có hàng neo: bắt đầu từ các cột khớp
        view_b = {(r, c) for r in range(len(rows)) for c in cols if c < len(rows[r])}
    view_c = view_b | {(r, c) for r in range(len(rows)) for c in cols if c < len(rows[r])}
    steps, tok_human, pred_human = [], 0, "THIẾU"
    for name, view in (("B", view_b), ("C", view_c), ("FULL", full)):
        if not view or (steps and view == steps[-1][2]):
            continue
        pred_human, tok = ask(client, table, headers, rows, view, q["question"])
        tok_human += tok
        steps.append((name, pred_human, view))
        if pred_human != "THIẾU":
            break
    return {
        "qa_id": q["qa_id"],
        "table_type": str(table["table_type"]),
        "gold_kind": kind,
        "gold_ids": sorted(gold_ids),
        "search_status": status,
        "full": {"pred": pred_full, "hit": pred_full in gold_ids, "prompt_tokens": tok_full},
        "human": {
            "pred": pred_human,
            "hit": pred_human in gold_ids,
            "prompt_tokens": tok_human,
            "steps": [
                {"view": n, "pred": p, "view_cells": len(v), "gold_in_view": bool(gold & v)} for n, p, v in steps
            ],
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="outputs/human_locate/dev200.json")
    args = ap.parse_args()

    tables = {t["table_id"]: t for t in json.load(open("dataset/table.json", encoding="utf-8"))["table"]}
    grids = {tid: grid(t) for tid, t in tables.items()}
    qas = [q for q in json.load(open("dataset/qas_dev.json", encoding="utf-8"))["qas"]
           if gold_cells(q["answer"], grids[q["table_id"]][1])[1]]
    strata = defaultdict(list)
    for q in qas:
        strata[str(tables[q["table_id"]]["table_type"])].append(q)
    rng = random.Random(args.seed)
    sample = []
    for items in strata.values():  # phân tầng theo table_type, tỉ lệ theo kích thước tầng
        rng.shuffle(items)
        sample += items[: round(args.n * len(items) / len(qas))]

    with ThreadPoolExecutor(args.workers) as pool:
        records = list(pool.map(lambda q: run_one(q, tables[q["table_id"]], *grids[q["table_id"]]), sample))

    n = len(records)
    full_hit = [r["full"]["hit"] for r in records]
    human_hit = [r["human"]["hit"] for r in records]
    first = [r["human"]["steps"][0] for r in records if r["human"]["steps"]]
    summary = {
        "n": n,
        "locate_acc_full": round(100 * sum(full_hit) / n, 1),
        "locate_acc_human": round(100 * sum(human_hit) / n, 1),
        "human_wins": sum(h and not f for h, f in zip(human_hit, full_hit)),
        "human_losses": sum(f and not h for h, f in zip(human_hit, full_hit)),
        "prompt_tokens_full": sum(r["full"]["prompt_tokens"] for r in records),
        "prompt_tokens_human": sum(r["human"]["prompt_tokens"] for r in records),
        "parse_errors_full": sum(r["full"]["pred"] == "parse_error" for r in records),
        "parse_errors_human": sum(s["pred"] == "parse_error" for r in records for s in r["human"]["steps"]),
        "human_calls_per_q": round(sum(len(r["human"]["steps"]) for r in records) / n, 2),
        "step1_thieu_calibration": dict(Counter(
            ("gold_in_view" if s["gold_in_view"] else "gold_not_in_view") + "/" + ("THIẾU" if s["pred"] == "THIẾU" else "chọn ô")
            for s in first
        )),
        "step1_acc_when_gold_in_view": round(100 * sum(
            r["human"]["steps"][0]["pred"] in r["gold_ids"] for r in records
            if r["human"]["steps"] and r["human"]["steps"][0]["gold_in_view"]
        ) / max(1, sum(s["gold_in_view"] for s in first)), 1),
        "rescued_by_expansion": sum(
            r["human"]["hit"] and len(r["human"]["steps"]) > 1 for r in records
        ),
        "by_table_type": {
            t: {
                "n": len(rs),
                "full": round(100 * sum(r["full"]["hit"] for r in rs) / len(rs), 1),
                "human": round(100 * sum(r["human"]["hit"] for r in rs) / len(rs), 1),
            }
            for t, rs in sorted(
                ((t, [r for r in records if r["table_type"] == t]) for t in {r["table_type"] for r in records}),
                key=lambda kv: -len(kv[1]),
            )
        },
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
