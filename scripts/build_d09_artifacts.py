"""D09: turn the run's JSONL records into one-answer artifacts, one per arm, in the D01 schema.

Artifacts are ``{manifest, predictions:[{qa_id, table_id, prediction:[answer]}]}`` ordered like the
subset QAs, so ``scripts/audit_d01.py`` scores every arm with the same frozen scorer. An arm with a
question without a non-empty answer is reported and not written, unless ``--score-missing-as-wrong`` is given: then the
question gets the sentinel answer ``[NO_VALID_ANSWER]`` (never matches a gold answer) and the manifest
lists the affected QA ids. ``--splice ARM --base-arm BASE`` completes a partial arm (one that was only
called on the questions whose prompt differed from BASE) with BASE's answers for every other question;
the manifest lists the spliced ids.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_records(path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    """arm -> qa_id -> last successful record (failed attempts are ignored, later lines win)."""
    arms: dict[str, dict[str, dict[str, Any]]] = collections.defaultdict(dict)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if "error" not in row:
                arms[row["arm"]][str(row["qa_id"])] = row
    return arms


SENTINEL = "[NO_VALID_ANSWER]"


def splice_records(
    base: dict[str, dict[str, Any]], partial: dict[str, dict[str, Any]]
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """``partial`` completed with ``base`` for every question it lacks; also returns those spliced ids."""
    return {**base, **partial}, sorted(set(base) - set(partial))


def build_arm(
    records: dict[str, dict[str, Any]], ids: list[str], *, table_ids: dict[str, str] | None = None
) -> tuple[list[dict[str, Any]], list[str]]:
    """Predictions in ``ids`` order. Questions without a non-empty answer are listed; with ``table_ids`` they get the sentinel."""
    predictions, missing = [], []
    for qa_id in ids:
        row = records.get(qa_id)
        if row is None or not str(row["prediction"][0]).strip():  # no record, or an empty answer
            missing.append(qa_id)
            if table_ids is not None:
                predictions.append({"qa_id": qa_id, "table_id": table_ids[qa_id], "prediction": [SENTINEL]})
        else:
            predictions.append({"qa_id": qa_id, "table_id": row["table_id"], "prediction": [str(row["prediction"][0])]})
    return predictions, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--score-missing-as-wrong", action="store_true")
    parser.add_argument("--splice", action="append", default=[], help="partial arm to complete from --base-arm")
    parser.add_argument("--base-arm")
    args = parser.parse_args()
    if args.splice and not args.base_arm:
        parser.error("--splice requires --base-arm")

    qas = json.loads(args.qas.read_text(encoding="utf-8"))["qas"]
    ids = [str(q["qa_id"]) for q in qas]
    table_ids = {str(q["qa_id"]): str(q["table_id"]) for q in qas} if args.score_missing_as_wrong else None
    arms = load_records(args.records)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary, incomplete = {}, False
    for arm, records in sorted(arms.items()):
        spliced: list[str] = []
        if arm in args.splice:
            records, spliced = splice_records(arms[args.base_arm], records)
            spliced = [qa_id for qa_id in spliced if qa_id in set(ids)]
        predictions, missing = build_arm(records, ids, table_ids=table_ids)
        summary[arm] = {"count": len(predictions), "missing": len(missing)}
        if missing and not args.score_missing_as_wrong:
            incomplete = True
            continue
        manifest = {
            "transform": "d09-representation-arm.v1",
            "arm": arm,
            "source": str(args.records),
            "source_sha256": sha256(args.records),
            "subset_qas": str(args.qas),
            "subset_qas_sha256": sha256(args.qas),
            "count": len(predictions),
            "missing_scored_as_wrong": missing,
            "spliced_from_base": {"base_arm": args.base_arm, "qa_ids": spliced} if arm in args.splice else None,
            "prompt_versions": sorted({r["prompt_version"] for r in records.values()}),
        }
        (args.out_dir / f"{arm}.json").write_text(
            json.dumps({"manifest": manifest, "predictions": predictions}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(summary, indent=2))
    return 1 if incomplete else 0


if __name__ == "__main__":
    raise SystemExit(main())
