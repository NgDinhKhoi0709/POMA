"""D13: score the header-filter run and report what the filter actually did.

Reads the resumable JSONL written by ``run_d13_header_filter.py`` and produces, for each arm:
EM and character-F1 (first candidate only, never best-of-K), paired bootstrap intervals against the
control, real API token and cost totals including the extra filter call, and — for ``hdrfilter`` —
the filter's own decisions: how much of the grid survived, how often it fell back, and whether the
gold answer survived into the compact table.

The answer-survival check is the recall diagnostic: for questions whose gold answer appears verbatim
in some cell of the full grid, it asks whether that cell is still present after filtering. A filter
that drops the answer cell cannot be rescued by any downstream solver.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.bootstrap import paired_bootstrap_ci  # noqa: E402
from evaluation.contracts import AlignedSample  # noqa: E402
from evaluation.f1 import score_sample as f1_sample  # noqa: E402
from evaluation.normalization import (  # noqa: E402
    exact_text_match,
    is_unanswerable_reference,
    prediction_is_unanswerable,
)
from preprocessing.header_filter import prepare  # noqa: E402

CONTROL = "v1_raw"


def norm(text: Any) -> str:
    return " ".join(unicodedata.normalize("NFC", str(text or "")).lower().split())


def em_score(prediction: list[str], qa: dict[str, Any]) -> float:
    """First candidate only; ``Null`` references use the project's unanswerable rule."""
    first = [prediction[0] if prediction else ""]
    if is_unanswerable_reference(qa["answer"]):
        return 1.0 if prediction_is_unanswerable(first) else 0.0
    return 1.0 if exact_text_match(first[0], qa["answer"], hints=qa.get("hints")) else 0.0


def f1_score(prediction: list[str], qa: dict[str, Any]) -> float:
    sample = AlignedSample(
        qa_id=str(qa["qa_id"]),
        prediction=[prediction[0] if prediction else ""],
        reference=str(qa["answer"]),
        hints=list(qa.get("hints") or []),
    )
    return float(f1_sample(sample).value)


def answer_survives(qa: dict[str, Any], table: dict[str, Any], record: dict[str, Any]) -> str:
    """``kept`` / ``dropped`` / ``not_in_table``: did the gold answer cell survive the filter?"""
    gold = norm(qa["answer"])
    if not gold or gold == "null":
        return "not_in_table"
    grid, _ = prepare(table)
    cols = record.get("kept_cols")
    if cols is None:
        return "not_in_table"
    kept_cols = set(cols)
    found_anywhere = False
    for row in grid.rows:
        for j, value in enumerate(row):
            cell = norm(value)
            # A cell counts as holding the answer when it is the answer or contains it verbatim:
            # gold answers are often the cell minus a parenthetical (``... (年度最佳作曲)``).
            if cell and (cell == gold or gold in cell):
                found_anywhere = True
                if j in kept_cols:
                    return "kept"
    return "dropped" if found_anywhere else "not_in_table"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=PROJECT_ROOT / "outputs/d13/records.jsonl")
    parser.add_argument("--qas", type=Path, default=PROJECT_ROOT / "outputs/d13/qas_d13_200.json")
    parser.add_argument("--tables", type=Path, default=PROJECT_ROOT / "dataset/table.json")
    parser.add_argument("--stats", type=Path, default=PROJECT_ROOT / "outputs/table_structure_stats.json")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "outputs/d13/report.json")
    args = parser.parse_args()

    qas = {str(q["qa_id"]): q for q in json.loads(args.qas.read_text(encoding="utf-8"))["qas"]}
    tables = {str(t["table_id"]): t for t in json.loads(args.tables.read_text(encoding="utf-8"))["table"]}
    stats = json.loads(args.stats.read_text(encoding="utf-8"))
    structural = {
        tid for tid, v in stats.items() if v["clusters"] >= 2 or v["mid_header"] or v["merged"] >= 5
    }

    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for line in args.records.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            key = (row["arm"], str(row["qa_id"]))
            if "error" not in row or key not in latest:
                latest[key] = row
    arms = sorted({arm for arm, _ in latest})

    em: dict[str, dict[str, float]] = defaultdict(dict)
    f1: dict[str, dict[str, float]] = defaultdict(dict)
    errors: dict[str, list[str]] = defaultdict(list)
    tokens: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for (arm, qa_id), row in latest.items():
        qa = qas.get(qa_id)
        if qa is None:
            continue
        if "error" in row:
            errors[arm].append(qa_id)
            # ``{"final_answer": null}`` is the model saying "not answerable" in a way the string
            # schema rejects. It is scored as the literal ``Null`` under the same rule on every arm,
            # because it carries the model's answer; any other contract failure scores 0.
            literal_null = "final_answer: None is not of type" in str(row.get("error", ""))
            prediction = ["Null"] if literal_null else [""]
            em[arm][qa_id] = em_score(prediction, qa) if literal_null else 0.0
            f1[arm][qa_id] = f1_score(prediction, qa) if literal_null else 0.0
        else:
            prediction = row.get("prediction") or [""]
            em[arm][qa_id] = em_score(prediction, qa)
            f1[arm][qa_id] = f1_score(prediction, qa)
        tokens[arm]["prompt_tokens"] += row.get("prompt_tokens") or 0
        tokens[arm]["completion_tokens"] += row.get("completion_tokens") or 0
        tokens[arm]["cost_usd"] += row.get("cost_usd") or 0.0
        tokens[arm]["filter_prompt_tokens"] += row.get("filter_prompt_tokens") or 0
        tokens[arm]["filter_completion_tokens"] += row.get("filter_completion_tokens") or 0
        tokens[arm]["cost_usd_filter"] += row.get("filter_cost_usd") or 0.0
        tokens[arm]["table_chars"] += row.get("table_chars") or 0

    shared = sorted(set.intersection(*[set(em[arm]) for arm in arms]))
    report: dict[str, Any] = {
        "n_questions_scored": len(shared),
        "arms": {},
        "structural_subset": {},
        "filter_behaviour": {},
        "errors": {arm: sorted(ids) for arm, ids in errors.items() if ids},
        "error_policy": "contract failures of the form final_answer=null are scored as the literal Null on every arm",
    }

    for arm in arms:
        vec_em = [em[arm][qid] for qid in shared]
        vec_f1 = [f1[arm][qid] for qid in shared]
        entry = {
            "EM": round(statistics.mean(vec_em) * 100, 2),
            "F1": round(statistics.mean(vec_f1) * 100, 2),
            "solver_prompt_tokens": int(tokens[arm]["prompt_tokens"]),
            "filter_prompt_tokens": int(tokens[arm]["filter_prompt_tokens"]),
            "total_prompt_tokens": int(tokens[arm]["prompt_tokens"] + tokens[arm]["filter_prompt_tokens"]),
            "completion_tokens": int(tokens[arm]["completion_tokens"] + tokens[arm]["filter_completion_tokens"]),
            "cost_usd": round(tokens[arm]["cost_usd"] + tokens[arm]["cost_usd_filter"], 6),
            "table_chars_total": int(tokens[arm]["table_chars"]),
            "errors": len(errors.get(arm, [])),
        }
        if arm != CONTROL and CONTROL in arms:
            ci = paired_bootstrap_ci(vec_em, [em[CONTROL][qid] for qid in shared])
            entry["EM_diff_vs_control"] = {
                "point": round(ci["point_estimate"] * 100, 2),
                "ci95": [round(ci["lower"] * 100, 2), round(ci["upper"] * 100, 2)],
            }
            wins = sum(1 for qid in shared if em[arm][qid] > em[CONTROL][qid])
            losses = sum(1 for qid in shared if em[arm][qid] < em[CONTROL][qid])
            entry["paired"] = {"wins": wins, "losses": losses, "ties": len(shared) - wins - losses}
        report["arms"][arm] = entry

    for label, ids in (
        ("structural_tables", [q for q in shared if str(qas[q]["table_id"]) in structural]),
        ("other_tables", [q for q in shared if str(qas[q]["table_id"]) not in structural]),
    ):
        report["structural_subset"][label] = {
            "n": len(ids),
            **{arm: round(statistics.mean([em[arm][q] for q in ids]) * 100, 2) for arm in arms if ids},
        }

    filt = [latest[("hdrfilter", qid)] for qid in shared if ("hdrfilter", qid) in latest]
    if filt:
        col_ratio, row_ratio, survive = [], [], Counter()
        fallbacks: Counter = Counter()
        for row in filt:
            if row.get("grid_cols"):
                col_ratio.append(len(row.get("kept_cols") or []) / row["grid_cols"])
            if row.get("grid_rows"):
                row_ratio.append((row.get("kept_rows_n") or 0) / row["grid_rows"])
            fallbacks[row.get("fallback") or "none"] += 1
            qa = qas[str(row["qa_id"])]
            survive[answer_survives(qa, tables[str(qa["table_id"])], row)] += 1
        dropped_ids = [
            str(row["qa_id"]) for row in filt
            if answer_survives(qas[str(row["qa_id"])], tables[str(qas[str(row["qa_id"])]["table_id"])], row) == "dropped"
        ]
        em_on_dropped = (
            round(statistics.mean([em["hdrfilter"][q] for q in dropped_ids]) * 100, 2) if dropped_ids else None
        )
        report["filter_behaviour"] = {
            "mean_columns_kept_ratio": round(statistics.mean(col_ratio), 4) if col_ratio else None,
            "mean_rows_kept_ratio": round(statistics.mean(row_ratio), 4) if row_ratio else None,
            "questions_with_any_row_selection": sum(1 for row in filt if "all_rows" not in (row.get("fallback") or "")),
            "fallback_counts": dict(fallbacks),
            "answer_cell_survival": dict(survive),
            "EM_when_answer_cell_dropped": em_on_dropped,
            "EM_control_on_those": (
                round(statistics.mean([em[CONTROL][q] for q in dropped_ids]) * 100, 2) if dropped_ids else None
            ),
            "unknown_id_calls": sum(1 for row in filt if row.get("unknown_ids")),
            "header_view_chars_total": sum(row.get("header_view_chars") or 0 for row in filt),
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
