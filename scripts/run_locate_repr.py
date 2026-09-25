"""So sánh cách biểu diễn bảng cho node Locate (8B chỉ trả ID ô), trên đúng các câu của dev200.

triplet     : một dòng một ô, ID | nhãn hàng (ô đầu) | đường dẫn header | giá trị (như run_human_locate).
triplet_fix : như triplet + (1) tên cột trùng thì đánh số [1], [2]; (2) nhãn hàng lấy cột khoá
              (nhiều giá trị khác nhau nhất); (3) ô xuất hiện trong câu hỏi được đánh dấu.
grid        : một dòng lược đồ "Cột: c0 = ... | c1 = ..." (đã khử trùng tên), rồi mỗi hàng "rX: v0 | v1 | ...".
Cả ba đều dùng view toàn bảng, cùng lời dặn, cùng cách chấm.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from evaluation.bootstrap import paired_bootstrap_ci  # noqa: E402
from scripts.census_human_search import contained, grid, syllables  # noqa: E402
from scripts.run_human_locate import ANSWER_RE  # noqa: E402
from src.services.llm_client import LLMClient  # noqa: E402

HEAD = "Bạn là bộ định vị ô trong bảng. {how}\nBảng: {title}\n{cells}\n\nCâu hỏi: {question}\n\n"
TAIL = ("Chọn đúng MỘT ID của ô chứa thông tin trả lời câu hỏi (ô chứa đáp án, không phải ô lặp lại "
        "thông tin đã có trong câu hỏi). Chỉ in ra ID (ví dụ r3c2), không giải thích.")
HOW = {
    "triplet": "Mỗi dòng dưới đây là một ô: ID | hàng | cột | giá trị.",
    "triplet_fix": "Mỗi dòng dưới đây là một ô: ID | hàng | cột | giá trị.",
    "grid": "Dòng 'Cột' cho tên từng cột; mỗi dòng sau là một hàng. ID của ô = ID hàng + ID cột (ví dụ r3 và c2 thành r3c2).",
}


def paths(headers, rows, dedupe: bool) -> list[str]:
    ncol = max((len(r) for r in rows + headers), default=0)
    ps = [" › ".join(dict.fromkeys(h[c] for h in headers if c < len(h) and h[c])) for c in range(ncol)]
    if dedupe:
        seen = Counter(ps)
        k = Counter()
        for i, p in enumerate(ps):
            if seen[p] > 1:
                k[p] += 1
                ps[i] = f"{p} [{k[p]}]"
    return ps


def key_col(rows) -> int:
    ncol = max((len(r) for r in rows), default=1)
    distinct = [len({r[c] for r in rows if c < len(r) and r[c]}) for c in range(ncol)]
    return max(range(ncol), key=lambda c: (distinct[c], -c))


def render(kind: str, headers, rows, question: str) -> str:
    qn = " ".join(syllables(question, strip_paren=False))
    if kind == "grid":
        ps = paths(headers, rows, dedupe=True)
        lines = ["Cột: " + " | ".join(f"c{c} = {p}" for c, p in enumerate(ps))]
        lines += [f"r{r}: " + " | ".join(row) for r, row in enumerate(rows)]
        return "\n".join(lines)
    fix = kind == "triplet_fix"
    ps = paths(headers, rows, dedupe=fix)
    kc = key_col(rows) if fix else None
    lines = []
    for r, row in enumerate(rows):
        label = row[kc] if fix and kc < len(row) and row[kc] else next((v for v in row if v), "")
        for c, v in enumerate(row):
            mark = " (có trong câu hỏi)" if fix and v and contained(v, qn) else ""
            lines.append(f"r{r}c{c} | {label[:60]} | {ps[c] if c < len(ps) else ''} | {v}{mark}")
    return "\n".join(lines)


def locate(kind, q, table, headers, rows) -> tuple[str, int]:
    client = LLMClient()
    client.set_qa_id(q["qa_id"])
    prompt = HEAD.format(how=HOW[kind], title=table["table_title"],
                         cells=render(kind, headers, rows, q["question"]), question=q["question"]) + TAIL
    raw = re.sub(r"<think>.*?</think>", "", client.generate_text(prompt, agent_name=f"locate_{kind}"), flags=re.DOTALL)
    found = [a for a in ANSWER_RE.findall(raw) if a.lower() != "thiếu"]
    return (found[-1].lower() if found else "parse_error"), client.total_prompt_tokens


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--records", default="outputs/human_locate/dev200.json")
    ap.add_argument("--kinds", nargs="+", default=["triplet", "triplet_fix", "grid"])
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="outputs/human_locate/repr_dev200.json")
    args = ap.parse_args()

    tables = {t["table_id"]: t for t in json.load(open("dataset/table.json", encoding="utf-8"))["table"]}
    qas = {q["qa_id"]: q for q in json.load(open("dataset/qas_dev.json", encoding="utf-8"))["qas"]}
    base = json.load(open(args.records, encoding="utf-8"))["records"]
    base = base[: args.limit] if args.limit else base
    grids = {tid: grid(tables[tid]) for tid in {qas[r["qa_id"]]["table_id"] for r in base}}

    jobs = [(k, r) for r in base for k in args.kinds]

    def run(job):
        k, r = job
        q = qas[r["qa_id"]]
        return k, r["qa_id"], *locate(k, q, tables[q["table_id"]], *grids[q["table_id"]])

    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(run, jobs))

    gold = {r["qa_id"]: set(r["gold_ids"]) for r in base}
    ttype = {r["qa_id"]: r["table_type"] for r in base}
    hits = {k: {} for k in args.kinds}
    toks = Counter()
    errs = Counter()
    preds = {k: {} for k in args.kinds}
    for k, qid, pred, tok in results:
        hits[k][qid] = float(pred in gold[qid])
        preds[k][qid] = pred
        toks[k] += tok
        errs[k] += pred == "parse_error"
    ids = [r["qa_id"] for r in base]
    ref = args.kinds[0]
    summary = {"n": len(ids)}
    for k in args.kinds:
        a, b = [hits[k][i] for i in ids], [hits[ref][i] for i in ids]
        summary[k] = {
            "locate_acc": round(100 * sum(a) / len(ids), 1),
            "prompt_tokens": toks[k],
            "parse_errors": errs[k],
            **({} if k == ref else {
                f"vs_{ref}": paired_bootstrap_ci(a, b)["difference"],
                "wins": sum(x > y for x, y in zip(a, b)),
                "losses": sum(x < y for x, y in zip(a, b)),
            }),
            "by_table_type": {
                t: round(100 * sum(hits[k][i] for i in ids if ttype[i] == t) / sum(ttype[i] == t for i in ids), 1)
                for t in sorted(set(ttype.values()))
            },
        }
    Path(args.out).write_text(json.dumps({"summary": summary, "predictions": preds}, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
