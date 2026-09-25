"""D04: how many arithmetic-question errors are left for an executor to fix?

Uses only saved one-answer artifacts on the full 992-question test set and the frozen D01 scorer,
so no API call is made. Slices: the dataset's ``Sử dụng tính toán`` hint, and questions whose gold
answer is a plain number. Errors are an upper bound on what any executor override can gain.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation import exact_match  # noqa: E402
from evaluation.io import align_records, load_json_records, load_qas_records  # noqa: E402
from scripts.build_d04_arms import latest_planner_records, load_predictions  # noqa: E402
from src.table_executor.ast_executor import ExecutionError, parse_number  # noqa: E402
from src.table_executor.planner import r2_override  # noqa: E402

CALC_HINT = "Sử dụng tính toán"
NUMERIC = re.compile(r"-?\d[\d.,]*")


def correctness(path: Path, qas: Path) -> dict[str, bool]:
    samples, _ = align_records(load_json_records(path), load_qas_records(qas), candidate_policy="single-required")
    return {s.qa_id: exact_match.score_sample(s).value == 1.0 for s in samples}


def _same_number(a: str, b: str) -> bool:
    try:
        return abs(parse_number(a) - parse_number(b)) < 1e-6
    except ExecutionError:
        return False


def numeric_error_split(qas: list[dict], answers: dict[str, dict], ok: dict[str, bool]) -> dict[str, int]:
    """Split wrong answers on plain-number gold: format only, wrong value, or no number given."""
    split = {"wrong": 0, "same_number_different_format": 0, "wrong_value": 0, "no_numeric_prediction": 0}
    for q in qas:
        qa_id, gold = str(q["qa_id"]), str(q["answer"]).strip()
        if not NUMERIC.fullmatch(gold) or ok[qa_id]:
            continue
        prediction = answers[qa_id]["prediction"][0].strip()
        split["wrong"] += 1
        if not NUMERIC.fullmatch(prediction):
            split["no_numeric_prediction"] += 1
        elif _same_number(prediction, gold):
            split["same_number_different_format"] += 1
        else:
            split["wrong_value"] += 1
    return split


def measure(qas: Path, systems: dict[str, Path], planner_log: Path | None = None, subset_qas: Path | None = None) -> dict:
    items = json.loads(qas.read_text(encoding="utf-8"))["qas"]
    hints = {str(q["qa_id"]): q.get("hints", []) for q in items}
    gold = {str(q["qa_id"]): str(q["answer"]).strip() for q in items}
    ok = {name: correctness(path, qas) for name, path in systems.items()}
    slices = {
        "all": [i for i in hints],
        "calc_hint": [i for i in hints if CALC_HINT in hints[i]],
        "numeric_gold": [i for i in hints if NUMERIC.fullmatch(gold[i])],
        "calc_hint_and_numeric_gold": [i for i in hints if CALC_HINT in hints[i] and NUMERIC.fullmatch(gold[i])],
        "calc_hint_non_numeric_gold": [i for i in hints if CALC_HINT in hints[i] and not NUMERIC.fullmatch(gold[i])],
    }
    report: dict = {
        "n_questions": len(hints),
        "numeric_gold_error_split": {
            name: numeric_error_split(items, load_predictions(path), ok[name]) for name, path in systems.items()
        },
        "slices": {},
    }
    for name, ids in slices.items():
        row = {"n": len(ids), "wrong": {s: sum(not ok[s][i] for i in ids) for s in ok}}
        row["em"] = {s: round(100 * (1 - row["wrong"][s] / len(ids)), 2) if ids else None for s in ok}
        row["wrong_by_all_systems"] = sum(all(not ok[s][i] for s in ok) for i in ids)
        row["wrong_by_any_system"] = sum(any(not ok[s][i] for s in ok) for i in ids)
        report["slices"][name] = row
    if planner_log and subset_qas:
        planner = latest_planner_records(planner_log)
        sub = [str(q["qa_id"]) for q in json.loads(subset_qas.read_text(encoding="utf-8"))["qas"]]
        gated = {i for i in sub if r2_override(planner[i]) is not None}
        calc = [i for i in sub if CALC_HINT in hints[i]]
        report["subset_reach"] = {
            "subset_n": len(sub),
            "calc_hint_in_subset": len(calc),
            "gated": len(gated),
            "gated_and_calc_hint": len(gated & set(calc)),
            "calc_hint_wrong_by_fs": sum(not ok["few_shot"][i] for i in calc),
            "calc_hint_wrong_by_fs_and_gated": sum(not ok["few_shot"][i] and i in gated for i in calc),
            "gated_and_fs_wrong": sum(not ok["few_shot"][i] for i in gated),
            "calc_hint_fs_wrong_items": [
                {
                    "qa_id": i,
                    "gold": gold[i],
                    "few_shot": load_predictions(systems["few_shot"])[i]["prediction"][0],
                    "planner_status": planner[i].get("exec_status"),
                    "planner_ops": [op for op in planner[i].get("ops", []) if op not in ("select", "filter", "project")],
                    "planner_value": planner[i].get("exec_rendered"),
                }
                for i in calc if not ok["few_shot"][i]
            ],
        }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, default=Path("dataset/qas_test.json"))
    parser.add_argument("--system", action="append", required=True, help="NAME=PATH (full 992 one-answer artifacts)")
    parser.add_argument("--planner-log", type=Path)
    parser.add_argument("--subset-qas", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    systems = {}
    for spec in args.system:
        name, _, path = spec.partition("=")
        systems[name] = Path(path)
    report = measure(args.qas, systems, args.planner_log, args.subset_qas)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
