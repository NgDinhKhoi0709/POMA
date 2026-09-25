"""D04: describe the executor override slice (funnel, conditional accuracy, per-item table).

Correctness uses the same frozen ``evaluation.exact_match`` scorer as ``audit_d01.py``. The
numeric-equality column is a diagnostic only, to separate a wrong value from a formatting mismatch;
it never enters the reported EM.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation import exact_match  # noqa: E402
from evaluation.io import align_records, load_json_records, load_qas_records  # noqa: E402
from scripts.build_d04_arms import latest_planner_records, load_predictions  # noqa: E402
from src.table_executor.ast_executor import ExecutionError, parse_number  # noqa: E402
from src.table_executor.planner import R2_OPS, R2_EXCLUDED_OPS, r2_override  # noqa: E402

READERS = ("few_shot", "poma_first", "poma_gsa", "few_shot_gsa", "cot")


def _correct(path: Path, qas: Path) -> dict[str, bool]:
    samples, _ = align_records(load_json_records(path), load_qas_records(qas), candidate_policy="single-required")
    return {s.qa_id: exact_match.score_sample(s).value == 1.0 for s in samples}


def _same_number(a: str, b: str) -> bool | None:
    if not re.search(r"\d", a) or not re.search(r"\d", b):
        return None
    try:
        return abs(parse_number(a) - parse_number(b)) < 1e-6
    except ExecutionError:
        return None


def analyze(qas: Path, planner_log: Path, arms_dir: Path) -> dict[str, Any]:
    planner = latest_planner_records(planner_log)
    gold = {str(q["qa_id"]): q for q in json.loads(qas.read_text(encoding="utf-8"))["qas"]}
    status = collections.Counter(r.get("exec_status") for r in planner.values())
    ok = [r for r in planner.values() if r.get("exec_status") == "ok"]
    funnel = {
        "planner_records": len(planner),
        "status": dict(status),
        "ok_with_r2_op": sum(bool(set(r["ops"]) & R2_OPS) for r in ok),
        "ok_with_r2_op_excluded_by_compare": sum(
            bool(set(r["ops"]) & R2_OPS) and bool(set(r["ops"]) & R2_EXCLUDED_OPS) for r in ok
        ),
        "r2_gated": sum(r2_override(r) is not None for r in planner.values()),
        "table_truncated": sum(bool(r.get("table_truncated")) for r in planner.values()),
    }
    usage = {
        "cost_usd": round(sum(r.get("cost_usd") or 0 for r in planner.values()), 6),
        "providers": dict(collections.Counter(r.get("provider") for r in planner.values())),
        "mean_plan_s": round(sum(r.get("plan_s") or 0 for r in planner.values()) / max(1, len(planner)), 2),
    }
    gated = [qa_id for qa_id, r in planner.items() if r2_override(r) is not None]
    correct = {name: _correct(arms_dir / f"{name}.json", qas) for name in READERS}
    preds = {name: load_predictions(arms_dir / f"{name}.json") for name in READERS}
    r2_correct = _correct(arms_dir / "few_shot_r2.json", qas)
    slice_rows = []
    for qa_id in gated:
        record = planner[qa_id]
        value = record["exec_rendered"]
        gold_answer = gold[qa_id]["answer"]
        slice_rows.append({
            "qa_id": qa_id,
            "question": gold[qa_id]["question"],
            "gold": gold_answer,
            "executor": value,
            "ops": [op for op in record["ops"] if op in R2_OPS],
            "executor_correct": r2_correct[qa_id],
            "executor_numeric_equal": _same_number(value, gold_answer),
            **{f"{name}_answer": preds[name][qa_id]["prediction"][0] for name in READERS},
            **{f"{name}_correct": correct[name][qa_id] for name in READERS},
        })
    conditional = {"n": len(gated), "executor": sum(r["executor_correct"] for r in slice_rows)}
    for name in READERS:
        conditional[name] = sum(r[f"{name}_correct"] for r in slice_rows)
    conditional["executor_numeric_equal"] = sum(bool(r["executor_numeric_equal"]) for r in slice_rows)
    return {
        "funnel": funnel,
        "usage": usage,
        "conditional_correct_on_gated_slice": conditional,
        "gated_items": slice_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, required=True)
    parser.add_argument("--planner-log", type=Path, required=True)
    parser.add_argument("--arms-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.qas, args.planner_log, args.arms_dir)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("funnel", "usage", "conditional_correct_on_gated_slice")}, ensure_ascii=False, indent=2))
    for row in result["gated_items"]:
        print(f"{row['qa_id']:>12} gold={row['gold']!r} exec={row['executor']!r} fs={row['few_shot_answer']!r} "
              f"poma={row['poma_first_answer']!r} cot={row['cot_answer']!r} ops={row['ops']} "
              f"exec_ok={row['executor_correct']} fs_ok={row['few_shot_correct']} numeq={row['executor_numeric_equal']}")


if __name__ == "__main__":
    main()
