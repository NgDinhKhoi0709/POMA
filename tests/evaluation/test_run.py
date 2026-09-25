"""Tests for policy-aware evaluation reports."""

from __future__ import annotations

import json

import pytest

from evaluation.exceptions import EvaluationDataError
from evaluation.run import candidate_statistics, evaluate_files
from run_eval import main as run_eval_main


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


@pytest.mark.parametrize(
    ("predictions", "references", "policy", "message"),
    [
        (
            [{"qa_id": "a", "prediction": ["x", "y"]}],
            [{"qa_id": "a", "answer": "x"}],
            "single-required", "candidate policy",
        ),
        (
            [{"qa_id": "a", "prediction": ["x"]}, {"qa_id": "a", "prediction": ["x"]}],
            [{"qa_id": "a", "answer": "x"}],
            "single-required", "duplicate prediction",
        ),
        (
            [{"qa_id": "a", "prediction": ["x"]}],
            [{"qa_id": "a", "answer": "x"}, {"qa_id": "b", "answer": "x"}],
            "single-required", "missing predictions",
        ),
        (
            [{"qa_id": "a", "prediction": ["x"]}, {"qa_id": "b", "prediction": ["y"]}],
            [{"qa_id": "a", "answer": "x"}],
            "single-required", "extra predictions",
        ),
        (
            [{"qa_id": "a", "prediction": [""]}],
            [{"qa_id": "a", "answer": "x"}],
            "single-required", "empty answers",
        ),
    ],
)
def test_strict_evaluation_rejects_invalid_publication_inputs(
    tmp_path, predictions, references, policy, message
):
    prediction_path = tmp_path / "predictions.json"
    qas_path = tmp_path / "qas.json"
    prediction_path.write_text(json.dumps(predictions), encoding="utf-8")
    qas_path.write_text(json.dumps(references), encoding="utf-8")

    with pytest.raises(EvaluationDataError, match=message):
        evaluate_files(
            prediction_path, qas_path, metrics=["em"],
            candidate_policy=policy, strict=True,
        )


def test_evaluation_report_records_exact_input_and_scorer_hashes(tmp_path):
    prediction_path = tmp_path / "predictions.json"
    qas_path = tmp_path / "qas.json"
    prediction_path.write_text('[{"qa_id":"a","prediction":["x"]}]', encoding="utf-8")
    qas_path.write_text('[{"qa_id":"a","answer":"x"}]', encoding="utf-8")

    report = evaluate_files(
        prediction_path, qas_path, metrics=["em"],
        candidate_policy="single-required", strict=True,
    )

    assert report["metrics"]["em"] == {"count": 1, "value": 1.0}
    assert len(report["provenance"]["prediction_sha256"]) == 64
    assert len(report["provenance"]["qas_sha256"]) == 64
    assert len(report["provenance"]["scorer_sha256"]) == 64


def test_strict_cli_exits_nonzero_without_writing_misleading_score(tmp_path, capsys):
    prediction_path = tmp_path / "predictions.json"
    qas_path = tmp_path / "qas.json"
    report_path = tmp_path / "report.json"
    prediction_path.write_text(
        '[{"qa_id":"a","prediction":["x","y"]}]', encoding="utf-8"
    )
    qas_path.write_text('[{"qa_id":"a","answer":"x"}]', encoding="utf-8")

    status = run_eval_main([
        "--pred", str(prediction_path), "--qas", str(qas_path),
        "--metrics", "em", "--candidate-policy", "single-required",
        "--strict", "--output", str(report_path),
    ])

    assert status == 2
    assert "candidate policy failures" in capsys.readouterr().err
    assert not report_path.exists()


def test_strict_evaluation_rejects_unknown_metric(tmp_path):
    prediction_path = tmp_path / "predictions.json"
    qas_path = tmp_path / "qas.json"
    prediction_path.write_text(
        '[{"qa_id":"a","prediction":["x"]}]', encoding="utf-8"
    )
    qas_path.write_text('[{"qa_id":"a","answer":"x"}]', encoding="utf-8")

    with pytest.raises(EvaluationDataError, match="unsupported metrics"):
        evaluate_files(
            prediction_path, qas_path, metrics=["unknown"],
            candidate_policy="single-required", strict=True,
        )
