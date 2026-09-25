"""Describe the representation stage run: what differs between arms, how much, and at what token cost.

No API call. Reads the built one-answer arms, the JSONL records, the plan and (optionally) the per-arm
``run_eval.py`` reports that carry BIF. ``audit_d01.py`` owns significance; this adds what it cannot see:

* every question two arms answered differently, split into *style* (the same answer with words added or
  removed, or a ``Null`` not written as ``Null``) and *other* (a different answer, which is where content
  effects live but also where a different way of writing the same value lands). Words are compared token by
  token, not as substrings: the substring version of this check once counted ``5`` inside ``50`` as the same
  answer and reported 100% style.
* table-string tokens (what the serializer produces) next to API prompt tokens (what was billed).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation import exact_match  # noqa: E402
from evaluation.io import align_records, load_json_records, load_qas_records  # noqa: E402
from evaluation.normalization import normalize_text  # noqa: E402

PAIRS = [
    ("pipe_clean", "v1_raw"),
    ("pipe_nohdr", "v1_raw"),
    ("pipe_nohdr", "pipe_clean"),
    ("pipe_h1", "pipe_clean"),
]


def correctness(path: Path, qas: Path) -> dict[str, bool]:
    samples, _ = align_records(load_json_records(path), load_qas_records(qas), candidate_policy="single-required")
    return {s.qa_id: exact_match.score_sample(s).value == 1.0 for s in samples}


def predictions(path: Path) -> dict[str, str]:
    return {str(p["qa_id"]): str(p["prediction"][0]) for p in json.loads(path.read_text(encoding="utf-8"))["predictions"]}


_EDGE_PUNCT = ".,;:!?()[]{}\"'“”‘’«»"


def _tokens(text: str) -> list[str]:
    """Words of the normalised text with punctuation stripped from each word's ends only.

    Inside a word the punctuation stays, so ``1.5`` is not split into ``1`` and ``5`` (which would make it
    contain the answer ``5``), while ``Có,`` still matches ``Có``.
    """
    words = (word.strip(_EDGE_PUNCT) for word in normalize_text(text).split())
    return [word for word in words if word]


def _contiguous(a: list[str], b: list[str]) -> bool:
    """One token list occurs, in order and unbroken, inside the other."""
    if not a or not b:
        return False
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    return any(long_[i : i + len(short)] == short for i in range(len(long_) - len(short) + 1))


def classify(gold: str, pred_a: str, pred_b: str) -> str:
    """``null_format`` | ``extra_words`` | ``other`` for two answers of which exactly one is correct."""
    if normalize_text(gold) == "null":
        return "null_format"
    if _contiguous(_tokens(pred_a), _tokens(pred_b)):
        return "extra_words"
    return "other"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, required=True)
    parser.add_argument("--arms-dir", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--bif-dir", type=Path, help="Directory of <arm>.json reports from run_eval.py")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    qas = {str(q["qa_id"]): q for q in json.loads(args.qas.read_text(encoding="utf-8"))["qas"]}
    arms = sorted(p.stem for p in args.arms_dir.glob("*.json"))
    ok = {arm: correctness(args.arms_dir / f"{arm}.json", args.qas) for arm in arms}
    pred = {arm: predictions(args.arms_dir / f"{arm}.json") for arm in arms}
    report: dict[str, Any] = {"n_questions": len(qas), "em": {}, "pairs": {}}

    for arm in arms:
        report["em"][arm] = round(100 * sum(ok[arm].values()) / len(qas), 2)

    for arm, base in PAIRS:
        if arm not in ok or base not in ok:
            continue
        wins = [i for i in qas if ok[arm][i] and not ok[base][i]]
        losses = [i for i in qas if ok[base][i] and not ok[arm][i]]
        by_kind: dict[str, dict[str, list[str]]] = {}
        for direction, ids in (("wins", wins), ("losses", losses)):
            for i in ids:
                kind = classify(str(qas[i]["answer"]), pred[arm][i], pred[base][i])
                by_kind.setdefault(kind, {"wins": [], "losses": []})[direction].append(i)
        report["pairs"][f"{arm} vs {base}"] = {
            "delta_em_points": round(100 * (len(wins) - len(losses)) / len(qas), 2),
            "wins": len(wins),
            "losses": len(losses),
            "discordant": len(wins) + len(losses),
            "by_kind": {k: {"wins": len(v["wins"]), "losses": len(v["losses"])} for k, v in by_kind.items()},
            "other_examples": [
                {"qa_id": i, "gold": str(qas[i]["answer"])[:60], "arm": pred[arm][i][:60], "base": pred[base][i][:60],
                 "arm_correct": ok[arm][i]}
                for d in ("wins", "losses") for i in by_kind.get("other", {"wins": [], "losses": []})[d]
            ],
        }

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    ids_h1 = {i for i, v in plan["h1"].items() if v["h1_changed"]}
    tokens = {arm: [plan["h1"][i]["tokens"][arm] for i in qas] for arm in ("v1_raw", "pipe_clean", "pipe_nohdr", "pipe_h1")}
    records = [r for r in load_jsonl(args.records) if "error" not in r]
    base_rec = {(r["arm"], str(r["qa_id"])): r for r in records}
    api: dict[str, dict[str, float]] = {}
    for arm in ("v1_raw", "pipe_clean", "pipe_nohdr", "pipe_h1"):
        rows = []
        for i in qas:
            r = base_rec.get((arm, i)) or (base_rec.get(("pipe_clean", i)) if arm == "pipe_h1" else None)
            if r:
                rows.append(r)
        api[arm] = {
            "n": len(rows),
            "mean_prompt_tokens": round(sum(r.get("prompt_tokens", 0) for r in rows) / max(len(rows), 1), 1),
            "mean_completion_tokens": round(sum(r.get("completion_tokens", 0) for r in rows) / max(len(rows), 1), 1),
            "cost_usd": round(sum(r.get("cost_usd", 0.0) for r in rows), 4),
            "mean_answer_words": round(sum(len(_tokens(str(r["prediction"][0]))) for r in rows) / max(len(rows), 1), 2),
        }
    v1 = sum(tokens["v1_raw"]) / len(qas)
    report["table_string_tokens"] = {
        arm: {"mean": round(sum(v) / len(v), 1), "vs_v1_raw_pct": round(100 * (sum(v) / len(v) / v1 - 1), 2)}
        for arm, v in tokens.items()
    }
    report["api"] = api
    report["h1_changed_questions"] = len(ids_h1)
    if args.bif_dir:
        report["bif"] = {}
        for arm in arms:
            path = args.bif_dir / f"{arm}.json"
            if path.exists():
                metrics = json.loads(path.read_text(encoding="utf-8"))["metrics"]
                report["bif"][arm] = round(100 * metrics["bif"]["value"], 2)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("em", "table_string_tokens", "api")}, ensure_ascii=False, indent=1))
    for name, pair in report["pairs"].items():
        print(f"{name}: {pair['delta_em_points']:+} (thang {pair['wins']} / thua {pair['losses']}) {pair['by_kind']}")
    print(f"-> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
