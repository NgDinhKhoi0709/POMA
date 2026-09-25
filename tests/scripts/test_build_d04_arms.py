"""D04 arm materialization: overrides only on R2-gated items and keeps provenance."""

import json

from scripts.build_d04_arms import apply_override, latest_planner_records


def _artifact(path, answers):
    path.write_text(json.dumps({
        "manifest": {},
        "predictions": [{"qa_id": k, "table_id": "t", "prediction": [v]} for k, v in answers.items()],
    }), encoding="utf-8")


def _log(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


def test_override_only_on_gated_items_and_records_provenance(tmp_path):
    reader = tmp_path / "reader.json"
    _artifact(reader, {"a": "1", "b": "2", "c": "3", "d": "4"})
    log = tmp_path / "planner.jsonl"
    _log(log, [
        {"qa_id": "a", "exec_status": "ok", "exec_rendered": "9", "ops": ["count"]},
        {"qa_id": "b", "exec_status": "ok", "exec_rendered": "Có", "ops": ["compare", "count"]},
        {"qa_id": "c", "exec_status": "error", "ops": ["sum"]},
        # d has no planner record -> reader kept and counted as missing
    ])
    out = tmp_path / "out.json"
    manifest = apply_override(reader, latest_planner_records(log), log, out)
    preds = {r["qa_id"]: r["prediction"][0] for r in json.loads(out.read_text())["predictions"]}
    assert preds == {"a": "9", "b": "2", "c": "3", "d": "4"}
    assert manifest["override_qa_ids"] == ["a"]
    assert manifest["planner_missing_qa_ids"] == ["d"]
    assert len(manifest["source_sha256"]) == 64 and len(manifest["planner_log_sha256"]) == 64


def test_infra_error_lines_are_ignored_and_later_success_wins(tmp_path):
    log = tmp_path / "planner.jsonl"
    _log(log, [
        {"qa_id": "a", "infra_error": "timeout"},
        {"qa_id": "a", "exec_status": "ok", "exec_rendered": "5", "ops": ["sum"]},
    ])
    assert latest_planner_records(log)["a"]["exec_rendered"] == "5"


def test_replacement_control_uses_other_system_on_same_gate(tmp_path):
    reader, cot = tmp_path / "reader.json", tmp_path / "cot.json"
    _artifact(reader, {"a": "1", "b": "2"})
    _artifact(cot, {"a": "77", "b": "88"})
    log = tmp_path / "planner.jsonl"
    _log(log, [{"qa_id": "a", "exec_status": "ok", "exec_rendered": "9", "ops": ["avg"]},
               {"qa_id": "b", "exec_status": "ok", "exec_rendered": "3", "ops": ["project"]}])
    from scripts.build_d04_arms import load_predictions
    out = tmp_path / "control.json"
    apply_override(reader, latest_planner_records(log), log, out, replacement=load_predictions(cot))
    preds = {r["qa_id"]: r["prediction"][0] for r in json.loads(out.read_text())["predictions"]}
    assert preds == {"a": "77", "b": "2"}
