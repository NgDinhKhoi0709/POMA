"""Offline probe: does a BM25 + PhoBERT hybrid retrieve the answer row at a smaller k than BM25 alone?

No API call. The question this answers is not "is the retriever accurate" — BM25 already reaches
recall@20 = 99.2% on the questions H1 actually reduces — but "can we keep fewer rows for the same
recall", because every dropped row is prompt tokens saved.

**Decision rule, fixed before running:** build the hybrid into the pipeline only if
``recall@3`` of the hybrid is at least ``recall@20`` of BM25 on the same slice. Anything less and the
extra model, its GPU dependency and its latency are not paid for.

Slice (same filters as the BM25 measurement it must beat): tables with at least ``--min-rows`` body
rows after cleaning, the gold answer appearing verbatim in exactly one row, and questions *without* an
aggregation cue, since H1 returns those tables in full and never retrieves for them.

Scores are combined two ways, both reported: min-max normalised sum with weight ``--alpha`` on the
dense score, and reciprocal rank fusion (rank-based, scale-free). Rows named verbatim in the question
are added exactly as ``preprocessing.reduction`` does, so the comparison isolates the ranker.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.normalization import normalize_text  # noqa: E402
from preprocessing.reduction import AGGREGATION_CUES, _norm, _rank  # noqa: E402
from preprocessing.variants import Grid  # noqa: E402

KS = (1, 2, 3, 5, 8, 10, 20)


def minmax(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    return [0.0] * len(values) if hi - lo < 1e-12 else [(v - lo) / (hi - lo) for v in values]


def rrf(order: list[int], n: int, k: int = 60) -> list[float]:
    """Reciprocal rank fusion contribution; ``order`` is row indices best-first."""
    score = [0.0] * n
    for rank, idx in enumerate(order):
        score[idx] = 1.0 / (k + rank + 1)
    return score


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, default=PROJECT_ROOT / "dataset/qas_train.json")
    parser.add_argument("--tables", type=Path, default=PROJECT_ROOT / "dataset/table.json")
    parser.add_argument("--model", default="vinai/phobert-large")
    parser.add_argument("--limit", type=int, default=500, help="questions in the slice")
    parser.add_argument("--min-rows", type=int, default=25)
    parser.add_argument("--alpha", type=float, default=0.5, help="weight on the dense score")
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    import torch
    from pyvi import ViTokenizer
    from transformers import AutoModel, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModel.from_pretrained(args.model).to(device).eval()

    @torch.no_grad()
    def embed(texts: list[str]) -> "torch.Tensor":
        out = []
        for start in range(0, len(texts), args.batch_size):
            chunk = [ViTokenizer.tokenize(t)[: args.max_length * 8] for t in texts[start : start + args.batch_size]]
            enc = tok(chunk, padding=True, truncation=True, max_length=args.max_length, return_tensors="pt").to(device)
            hidden = model(**enc).last_hidden_state
            mask = enc["attention_mask"].unsqueeze(-1).float()
            pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
            out.append(torch.nn.functional.normalize(pooled, dim=-1).cpu())
        return torch.cat(out)

    tables = {str(t["table_id"]): t for t in json.loads(args.tables.read_text(encoding="utf-8"))["table"]}
    qas = json.loads(args.qas.read_text(encoding="utf-8"))["qas"]

    cache: dict[str, tuple[list[tuple[str, ...]], "torch.Tensor"]] = {}
    hits = {name: {k: 0 for k in KS} for name in ("bm25", "dense", "hybrid_sum", "hybrid_rrf")}
    total = 0
    worse: list[dict] = []

    for qa in qas:
        if total >= args.limit:
            break
        table_id = str(qa["table_id"])
        table = tables.get(table_id)
        if table is None:
            continue
        gold = normalize_text(qa.get("answer", ""))
        if not gold or gold == "null" or len(gold) < 2:
            continue
        if AGGREGATION_CUES.search(_norm(str(qa["question"]))):
            continue
        if table_id not in cache:
            grid = Grid.from_table_data(table).cleaned()
            body = list(grid.rows[grid.n_head:])
            cache[table_id] = (body, embed([" | ".join(r) for r in body]) if body else None)
        body, row_vecs = cache[table_id]
        if len(body) < args.min_rows or row_vecs is None:
            continue
        gold_rows = [i for i, row in enumerate(body) if any(normalize_text(c) == gold for c in row)]
        if len(gold_rows) != 1:
            continue
        gold_row = gold_rows[0]
        total += 1

        bm25_order, bm25_scores, named = _rank(body, str(qa["question"]))
        query = embed([str(qa["question"])])[0]
        dense_scores = (row_vecs @ query).tolist()
        dense_order = sorted(range(len(body)), key=lambda i: (-dense_scores[i], i))

        b_norm, d_norm = minmax(list(bm25_scores)), minmax(dense_scores)
        mixed = [(1 - args.alpha) * b + args.alpha * d for b, d in zip(b_norm, d_norm)]
        sum_order = sorted(range(len(body)), key=lambda i: (-mixed[i], i))
        fused = [a + b for a, b in zip(rrf(bm25_order, len(body)), rrf(dense_order, len(body)))]
        rrf_order = sorted(range(len(body)), key=lambda i: (-fused[i], i))

        orders = {"bm25": bm25_order, "dense": dense_order, "hybrid_sum": sum_order, "hybrid_rrf": rrf_order}
        for name, order in orders.items():
            for k in KS:
                if gold_row in set(order[:k]) | set(named[:k]):
                    hits[name][k] += 1
        if gold_row in set(bm25_order[:3]) and gold_row not in set(rrf_order[:3]):
            worse.append({"qa_id": str(qa["qa_id"]), "question": str(qa["question"])[:90],
                          "gold": str(qa["answer"])[:40],
                          "bm25_rank": bm25_order.index(gold_row), "hybrid_rank": rrf_order.index(gold_row)})

    report = {
        "n": total,
        "slice": {"source": str(args.qas), "min_rows": args.min_rows,
                  "filters": "gold verbatim in exactly one body row; no aggregation cue; cleaned grid"},
        "model": args.model, "alpha": args.alpha,
        "recall": {name: {f"@{k}": round(100 * v[k] / total, 2) for k in KS} for name, v in hits.items()},
        "decision_rule": "adopt only if hybrid recall@3 >= bm25 recall@20",
        "hybrid_rrf_at_3": round(100 * hits["hybrid_rrf"][3] / total, 2),
        "bm25_at_20": round(100 * hits["bm25"][20] / total, 2),
        "bm25_top3_lost_by_hybrid": worse[:15],
    }
    report["verdict"] = (
        "ADOPT" if report["hybrid_rrf_at_3"] >= report["bm25_at_20"]
        else f"REJECT (hybrid@3 {report['hybrid_rrf_at_3']} < bm25@20 {report['bm25_at_20']})"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("n", "recall", "hybrid_rrf_at_3", "bm25_at_20", "verdict")},
                     ensure_ascii=False, indent=1))
    print(f"-> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
