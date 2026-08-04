import json
from src.kaggle_eval.jsonl_io import append_jsonl
from src.kaggle_eval.reporting import write_comparison_report, write_run_report


def test_write_run_report_handles_no_predictions_yet(tmp_path):
    qas = tmp_path / "qas.json"
    qas.write_text(json.dumps({"qas": []}), encoding="utf-8")

    report = write_run_report(
        tmp_path / "missing.jsonl",
        qas,
        tmp_path / "metrics.json",
    )

    assert report["status"] == "no_predictions"
    assert (tmp_path / "metrics.json").exists()

def test_write_comparison_report_aligns_same_ids_and_counts_wtl(tmp_path):
    qas = tmp_path / "qas.json"
    qas.write_text(json.dumps({"qas": [{"qa_id":"1","answer":"A"},{"qa_id":"2","answer":"B"}]}), encoding="utf-8")
    poma, zero = tmp_path / "poma.jsonl", tmp_path / "zero.jsonl"
    append_jsonl(poma, {"qa_id":"1","prediction":["A"]}); append_jsonl(poma, {"qa_id":"2","prediction":["wrong"]})
    append_jsonl(zero, {"qa_id":"1","prediction":["wrong"]}); append_jsonl(zero, {"qa_id":"2","prediction":["B"]})
    report = write_comparison_report(poma, zero, qas, tmp_path / "comparison.json")
    assert report["paired"]["count"] == 2
    assert report["win_tie_loss"]["poma_wins"] == 1
    assert report["win_tie_loss"]["zero_wins"] == 1
    assert "f1" in report["bootstrap_ci"]
