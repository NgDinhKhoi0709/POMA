"""D09: per-arm EM by table_type stratum, token/cost/latency and structured-output health.

Correctness is the same frozen ``evaluation.exact_match`` scorer used by ``audit_d01.py``.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation import exact_match  # noqa: E402
from evaluation.io import align_records, load_json_records, load_qas_records  # noqa: E402
from scripts.build_d09_artifacts import load_records  # noqa: E402

STRATA = ("normal", "merged_value_only", "merged_header_only", "both")


def stratum(table_type: list[str]) -> str:
    header, value = "contain_merged_header" in table_type, "contain_merged_value" in table_type
    if header and value:
        return "both"
    if header:
        return "merged_header_only"
    return "merged_value_only" if value else "normal"


def analyze(qas: Path, tables: Path, records: Path, arms_dir: Path) -> dict[str, Any]:
    table_type = {str(t["table_id"]): t.get("table_type", []) for t in json.loads(tables.read_text(encoding="utf-8"))["table"]}
    qa_table = {str(q["qa_id"]): str(q["table_id"]) for q in json.loads(qas.read_text(encoding="utf-8"))["qas"]}
    per_arm = load_records(records)
    report: dict[str, Any] = {}
    for arm, rows in sorted(per_arm.items()):
        path = arms_dir / f"{arm}.json"
        if not path.exists():
            continue
        samples, _ = align_records(load_json_records(path), load_qas_records(qas), candidate_policy="single-required")
        correct = {s.qa_id: exact_match.score_sample(s).value == 1.0 for s in samples}
        by_stratum: dict[str, list[bool]] = {name: [] for name in STRATA}
        for qa_id, ok in correct.items():
            by_stratum[stratum(table_type[qa_table[qa_id]])].append(ok)
        values = list(rows.values())
        report[arm] = {
            "n": len(correct),
            "em": round(sum(correct.values()) / len(correct), 4),
            "em_by_stratum": {k: {"n": len(v), "em": round(sum(v) / len(v), 4) if v else None} for k, v in by_stratum.items()},
            "mean_table_chars": round(statistics.mean(r["table_chars"] for r in values)),
            "mean_prompt_tokens": round(statistics.mean(r["prompt_tokens"] or 0 for r in values)),
            "mean_completion_tokens": round(statistics.mean(r["completion_tokens"] or 0 for r in values)),
            "mean_elapsed_s": round(statistics.mean(r["elapsed_s"] for r in values), 1),
            "cost_usd": round(sum(r["cost_usd"] or 0 for r in values), 4),
            "schema_invalid": sum(not r["schema_valid"] for r in values),
            "repair_attempted": sum(bool(r["repair_attempted"]) for r in values),
        }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, required=True)
    parser.add_argument("--tables", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--arms-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.qas, args.tables, args.records, args.arms_dir)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
