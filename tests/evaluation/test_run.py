"""Tests for policy-aware evaluation reports."""

from __future__ import annotations

import json

from evaluation.run import candidate_statistics, evaluate_files


def test_candidate_statistics_use_nearest_rank_p95():
    assert candidate_statistics([1, 1, 2, 4, 10]) == {
        "count": 5,
        "mean": 3.6,
        "median": 2,
        "p95": 10,
        "max": 10,
        "k_equals_one_rate": 0.4,
    }


def test_evaluate_files_reports_policy_stats_and_preserves_failed_records(tmp_path):
    predictions = [
        {"qa_id": "one", "prediction": ["right"]},
        {"qa_id": "zero", "prediction": []},
        {"qa_id": "many", "prediction": ["wrong", "right"]},
    ]
    references = [
        {"qa_id": "one", "answer": "right"},
        {"qa_id": "zero", "answer": "right"},
        {"qa_id": "many", "answer": "right"},
    ]
    prediction_path = tmp_path / "predictions.json"
    qas_path = tmp_path / "qas.json"
    prediction_path.write_text(json.dumps(predictions), encoding="utf-8")
    qas_path.write_text(json.dumps(references), encoding="utf-8")

    report = evaluate_files(
        prediction_path,
        qas_path,
        metrics=["em"],
        candidate_policy="single-required",
    )

    assert report["candidate_policy"] == "single-required"
    assert report["source_candidate_statistics"] == {
        "count": 3,
        "mean": 1,
        "median": 1,
        "p95": 2,
        "max": 2,
        "k_equals_one_rate": 1 / 3,
    }
    assert report["evaluated_candidate_statistics"] == {
        "count": 3,
        "mean": 1 / 3,
        "median": 0,
        "p95": 1,
        "max": 1,
        "k_equals_one_rate": 1 / 3,
    }
    assert report["metrics"]["em"] == {"count": 3, "value": 1 / 3}
    assert report["candidate_policy_failures"] == [
        {"qa_id": "many", "candidate_count": 2, "error": "multiple-candidates"},
        {"qa_id": "zero", "candidate_count": 0, "error": "empty-candidates"},
    ]
