"""Chạy các arm GaP-TQA trên một split rồi chấm EM ghép cặp.

python -m gap_tqa.run --split dev --arms A0 A1 A2a A2b A3 A4 --routers rule gold
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

from evaluation import exact_match
from evaluation.bootstrap import paired_bootstrap_ci
from evaluation.io import align_records, load_json_records, load_qas_records
from gap_tqa import nodes
from gap_tqa.graphs import GRAPHS, State, run_graph
from gap_tqa.router import gold_class, route
from gap_tqa.table import Table

ROUTED = {"A4", "A5"}  # arm có graph khác nhau theo lớp


def score(pred_path: Path, qas_path: Path) -> dict[str, float]:
    samples, _ = align_records(load_json_records(pred_path), load_qas_records(qas_path),
                               candidate_policy="single-required")
    return {s.qa_id: exact_match.score_sample(s).value for s in samples}


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", default="dev", choices=["train", "dev"])
    ap.add_argument("--arms", nargs="+", default=list(GRAPHS))
    ap.add_argument("--routers", nargs="+", default=["rule", "gold"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sample", type=int, default=0, help="lấy ngẫu nhiên N câu (seed 23), bỏ câu dùng làm ví dụ")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--baseline", default="A1")
    args = ap.parse_args()

    qas_path = Path(f"dataset/qas_{args.split}.json")
    qas = json.load(open(qas_path, encoding="utf-8"))["qas"]
    qas = qas[: args.limit] if args.limit else qas
    examples = nodes.style_examples()
    if args.sample:
        qas = [q for q in qas if f"Hỏi: {q['question']}\n" not in examples + "\n"]
        random.Random(23).shuffle(qas)
        qas = qas[: args.sample]
    tables = {t["table_id"]: t for t in json.load(open("dataset/table.json", encoding="utf-8"))["table"]}
    parsed = {tid: Table.of(tables[tid]) for tid in {q["table_id"] for q in qas}}
    suffix = f"_first{args.limit}" if args.limit else f"_sample{args.sample}" if args.sample else ""
    out_dir = Path(f"outputs/gap_tqa/{args.split}{suffix}")
    out_dir.mkdir(parents=True, exist_ok=True)
    classes = {"rule": {q["qa_id"]: route(q["question"]) for q in qas},
               "gold": {q["qa_id"]: gold_class(q["hints"]) for q in qas}}

    runs = [(a, r) for a in args.arms for r in (args.routers if a in ROUTED else ["-"])]
    scores: dict[str, dict[str, float]] = {}
    meta: dict[str, dict[str, dict]] = {}
    for arm, router in runs:
        name = arm if router == "-" else f"{arm}_{router}"
        cls = classes["rule" if router == "-" else router]

        def one(q, arm=arm, cls=cls):
            s = run_graph(arm, cls[q["qa_id"]], State(q["question"], parsed[q["table_id"]], examples))
            return q, s

        with ThreadPoolExecutor(args.workers) as pool:
            done = list(pool.map(one, qas))
        path = out_dir / f"{name}.json"
        path.write_text(json.dumps({
            "manifest": {
                "system": "gap_tqa", "arm": arm, "router": router, "graph": GRAPHS[arm],
                "model": os.environ.get("POMA_LLM_MODEL"), "provider": "openrouter default (Alibaba for qwen3-8b)",
                "thinking": "provider default", "temperature": 0.0,
                "prompt_sha256": {k: hashlib.sha256(v.encode()).hexdigest()[:16]
                                  for k, v in {"read": nodes.READ_PROMPT, "locate": nodes.LOCATE_PROMPT,
                                               "examples": examples}.items()},
                "emit_max_words": nodes.EMIT_MAX_WORDS,
            },
            "predictions": [{"qa_id": q["qa_id"], "table_id": q["table_id"], "prediction": [s.answer],
                             "class": cls[q["qa_id"]], "calls": s.calls, "prompt_tokens": s.prompt_tokens,
                             "trace": s.trace} for q, s in done],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        scores[name] = score(path, qas_path)
        meta[name] = {q["qa_id"]: {"calls": s.calls, "tok": s.prompt_tokens} for q, s in done}
        print(f"{name}: EM {100 * sum(scores[name].values()) / len(scores[name]):.2f}", flush=True)

    ids = sorted(set.intersection(*(set(v) for v in scores.values())))
    qa = {q["qa_id"]: q for q in qas}
    ttype = {i: str(tables[qa[i]["table_id"]]["table_type"]) for i in ids}
    base = [scores[args.baseline][i] for i in ids] if args.baseline in scores else None
    report = {"split": args.split, "n": len(ids), "arms": {}}
    for name, sc in scores.items():
        a = [sc[i] for i in ids]
        entry = {
            "em": round(100 * sum(a) / len(ids), 2),
            "calls_per_q": round(sum(meta[name][i]["calls"] for i in ids) / len(ids), 2),
            "prompt_tokens": sum(meta[name][i]["tok"] for i in ids),
        }
        if base is not None and name != args.baseline:
            diff = paired_bootstrap_ci(a, base)["difference"]
            entry[f"vs_{args.baseline}"] = {k: round(100 * v, 2) for k, v in diff.items()}
            entry["wins"] = sum(x > y for x, y in zip(a, base))
            entry["losses"] = sum(x < y for x, y in zip(a, base))
        for key, groups in (("by_gold_class", classes["gold"]), ("by_table_type", ttype)):
            g = defaultdict(list)
            for i in ids:
                g[groups[i]].append(sc[i])
            entry[key] = {k: [len(v), round(100 * sum(v) / len(v), 1)] for k, v in sorted(g.items())}
        report["arms"][name] = entry
    report["router_acc_vs_gold_pct"] = round(100 * sum(classes["rule"][i] == classes["gold"][i] for i in ids) / len(ids), 1)
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
