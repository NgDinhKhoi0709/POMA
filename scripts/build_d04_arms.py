"""D04: materialize subset baselines and R2 executor-override arms as one-answer artifacts.

Every artifact uses the canonical ``{manifest, predictions:[{qa_id, table_id, prediction:[answer]}]}``
schema consumed by ``scripts/audit_d01.py`` so all arms share one scorer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.prepare_d01_artifacts import adapt_baseline  # noqa: E402
from src.table_executor.planner import r2_override  # noqa: E402

D01 = "outputs/d01/openrouter_qwen_qwen3-8b"
LEGACY = {
    "zero_shot": "outputs/baseline/qwen/full_zs/qwen3-8b.json",
    "cot": "outputs/baseline/qwen/full_cot/qwen3-8b.json",
}
CANONICAL = {
    "few_shot": f"{D01}/few_shot_adapted.json",
    "poma_first": f"{D01}/poma_first.json",
    "poma_gsa": f"{D01}/poma_gsa_with_first_fallback.json",
    "few_shot_gsa": f"{D01}/few_shot_gsa_with_raw_fallback.json",
}
OVERRIDE_READERS = ("few_shot", "poma_first", "poma_gsa", "few_shot_gsa")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_predictions(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(row["qa_id"]): row for row in payload["predictions"]}


def latest_planner_records(path: Path) -> dict[str, dict[str, Any]]:
    """Last successful planner record per qa_id (infra failures are ignored, later lines win)."""
    records: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if "infra_error" not in row:
            records[str(row["qa_id"])] = row
    return records


def _write(path: Path, manifest: dict[str, Any], predictions: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"manifest": manifest, "predictions": predictions}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def subset_artifact(source: Path, ids: list[str], qas_path: Path, output: Path) -> None:
    rows = load_predictions(source)
    missing = [qa_id for qa_id in ids if qa_id not in rows]
    if missing:
        raise ValueError(f"{source} lacks {len(missing)} subset ids, e.g. {missing[:3]}")
    predictions = [
        {"qa_id": qa_id, "table_id": rows[qa_id].get("table_id"), "prediction": [rows[qa_id]["prediction"][0]]}
        for qa_id in ids
    ]
    manifest = {
        "transform": "subset.v1",
        "source": str(source),
        "source_sha256": sha256(source),
        "subset_qas": str(qas_path),
        "subset_qas_sha256": sha256(qas_path),
        "count": len(predictions),
    }
    _write(output, manifest, predictions)


def apply_override(
    reader: Path,
    planner: dict[str, dict[str, Any]],
    planner_path: Path,
    output: Path,
    *,
    replacement: dict[str, dict[str, Any]] | None = None,
    transform: str = "d04-r2-override.v1",
) -> dict[str, Any]:
    """Replace the reader answer on R2-gated items.

    ``replacement`` swaps in another one-answer system's prediction instead of the executor value
    (equal-call prompted-computation control); the gate is still decided by the executor log.
    """
    rows = load_predictions(reader)
    predictions, gated, missing = [], [], []
    for qa_id, row in rows.items():
        answer = row["prediction"][0]
        record = planner.get(qa_id)
        if record is None:
            missing.append(qa_id)
        else:
            value = r2_override(record)
            if value is not None:
                gated.append(qa_id)
                if replacement is not None:
                    answer = replacement[qa_id]["prediction"][0]
                else:
                    answer = value
        predictions.append({"qa_id": qa_id, "table_id": row.get("table_id"), "prediction": [answer]})
    manifest = {
        "transform": transform,
        "source": str(reader),
        "source_sha256": sha256(reader),
        "planner_log": str(planner_path),
        "planner_log_sha256": sha256(planner_path),
        "count": len(predictions),
        "override_count": len(gated),
        "override_qa_ids": gated,
        "planner_missing_count": len(missing),
        "planner_missing_qa_ids": missing,
    }
    _write(output, manifest, predictions)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qas", type=Path, required=True, help="Frozen subset QAs file")
    parser.add_argument("--planner-log", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    root = PROJECT_ROOT
    qas = json.loads(args.qas.read_text(encoding="utf-8"))["qas"]
    ids = [str(q["qa_id"]) for q in qas]
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    sources: dict[str, Path] = {}
    for name, relative in LEGACY.items():
        adapted = out / "full" / f"{name}_adapted.json"
        adapted.parent.mkdir(parents=True, exist_ok=True)
        adapt_baseline(root / relative, adapted)
        sources[name] = adapted
    for name, relative in CANONICAL.items():
        sources[name] = root / relative

    subsets: dict[str, Path] = {}
    for name, source in sources.items():
        subsets[name] = out / f"{name}.json"
        subset_artifact(source, ids, args.qas, subsets[name])

    planner = latest_planner_records(args.planner_log)
    summary: dict[str, Any] = {}
    for name in OVERRIDE_READERS:
        manifest = apply_override(subsets[name], planner, args.planner_log, out / f"{name}_r2.json")
        summary[f"{name}_r2"] = {k: manifest[k] for k in ("override_count", "planner_missing_count")}
    control = apply_override(
        subsets["few_shot"], planner, args.planner_log, out / "few_shot_cot_gate.json",
        replacement=load_predictions(subsets["cot"]), transform="d04-cot-gate-control.v1",
    )
    summary["few_shot_cot_gate"] = {k: control[k] for k in ("override_count", "planner_missing_count")}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
