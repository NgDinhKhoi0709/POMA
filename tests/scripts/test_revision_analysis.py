import json

import pytest

from scripts import run_revision_analysis


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_revision_analysis_cli_builds_one_mechanical_q2_report(
    tmp_path,
    monkeypatch,
):
    qas_path = _write(
        tmp_path / "qas.json",
        [
            {"qa_id": "q1", "answer": "yes", "hints": ["what"]},
            {"qa_id": "q2", "answer": "no", "hints": ["Who"]},
        ],
    )
    primary_path = _write(
        tmp_path / "primary.json",
        {
            "predictions": [
                {
                    "qa_id": "q1",
                    "prediction": ["yes"],
                    "trace": {
                        "decision": "selected",
                        "structured_calls": 1,
                        "schema_valid_calls": 1,
                        "repair_attempted_calls": 0,
                        "repair_succeeded_calls": 0,
                    },
                    "elapsed_s": 1.0,
                    "usage": {
                        "prompt_tokens": 4,
                        "completion_tokens": 1,
                        "total_tokens": 5,
                        "cost_usd": 0.01,
                    },
                },
                {
                    "qa_id": "q2",
                    "error": {"type": "SchemaError", "message": "bad"},
                    "trace": {
                        "structured_calls": 1,
                        "schema_valid_calls": 0,
                        "repair_attempted_calls": 1,
                        "repair_succeeded_calls": 0,
                    },
                    "elapsed_s": 3.0,
                    "usage": {
                        "prompt_tokens": 2,
                        "completion_tokens": 2,
                        "total_tokens": 4,
                        "cost_usd": None,
                    },
                },
            ]
        },
    )
    baseline_path = _write(
        tmp_path / "baseline.json",
        [
            {
                "qa_id": "q1",
                "prediction": ["no"],
                "trace": {"decision": "corrected"},
                "schema_valid": True,
            },
            {
                "qa_id": "q2",
                "prediction": ["no"],
                "trace": {"decision": "null"},
                "schema_valid": True,
            },
        ],
    )
    traces_path = _write(
        tmp_path / "traces.json",
        [
            {
                "qa_id": "q1",
                "predicted_hints": ["What"],
                "steps": {"2_router": {"specialist_names": ["What"]}},
                "llm_calls": [
                    {
                        "schema_valid": True,
                        "repair_attempted": False,
                        "prompt_tokens": 3,
                        "completion_tokens": 1,
                        "total_tokens": 4,
                        "cost_usd": 0.005,
                    }
                ],
                "elapsed_s": 2.0,
            },
            {
                "qa_id": "q2",
                "steps": {
                    "2_router": {
                        "specialist_names": ["Who", "MultiConditions"]
                    }
                },
                "llm_calls": [
                    {
                        "schema_valid": False,
                        "repair_attempted": True,
                        "repair_succeeded": True,
                        "prompt_tokens": 5,
                        "completion_tokens": 2,
                        "total_tokens": 7,
                        "cost_usd": None,
                    }
                ],
                "elapsed_s": 4.0,
            },
        ],
    )
    output_path = tmp_path / "analysis.json"
    evaluation_calls = []

    def fake_evaluate_files(prediction_path, qas_path_arg, **kwargs):
        evaluation_calls.append(
            (
                str(prediction_path),
                str(qas_path_arg),
                kwargs["metrics"],
                kwargs["fail_on_metric_error"],
            )
        )
        return {
            "metrics": {
                "f1": {"f1": 0.5},
                "em": {"value": 0.5},
                "rouge1": {"f1": 0.5},
                "meteor": {"value": 0.5},
            },
            "analyses": {
                "answerability_f1": {
                    "accuracy": 0.5,
                    "macro_f1": 0.5,
                }
            },
        }

    monkeypatch.setattr(
        run_revision_analysis,
        "evaluate_files",
        fake_evaluate_files,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_revision_analysis.py",
            "--system",
            f"poma={primary_path}",
            "--system",
            f"baseline={baseline_path}",
            "--primary-system",
            "poma",
            "--baseline-system",
            "baseline",
            "--qas",
            str(qas_path),
            "--poma-traces",
            str(traces_path),
            "--bootstrap-samples",
            "100",
            "--seed",
            "17",
            "--output",
            str(output_path),
        ],
    )

    run_revision_analysis.main()
    report = json.loads(output_path.read_text(encoding="utf-8"))

    expected_metrics = [
        "f1",
        "em",
        "rouge1",
        "meteor",
        "answerability_f1",
    ]
    assert evaluation_calls == [
        (str(primary_path), str(qas_path), expected_metrics, True),
        (str(baseline_path), str(qas_path), expected_metrics, True),
    ]
    assert report["configuration"] == {
        "bootstrap_samples": 100,
        "seed": 17,
    }
    assert report["hint_metrics"]["exact_set_accuracy"] == 0.5
    assert report["hint_metrics"]["coverage"]["missing_prediction_ids"] == [
        "q2"
    ]
    assert report["parallelism"]["distribution"] == {"1": 1, "2": 1}
    assert report["systems"]["poma"]["gsa_decisions"] == {
        "count": 1,
        "distribution": {"selected": 1},
    }
    assert report["systems"]["poma"]["structured_output"] == {
        "calls": 2,
        "missing_schema_telemetry_records": 0,
        "initial_schema_valid_rate": 0.5,
        "repair_attempt_rate": 0.5,
        "repair_success_rate": 0.0,
    }
    assert report["systems"]["poma"]["failure"]["failure_rate"] == 0.5
    assert report["systems"]["poma"]["cost"]["total_cost_usd"] is None
    assert report["systems"]["poma"]["latency"]["mean_s"] == 2.0
    comparison = report["comparison"]
    assert comparison["primary_system"] == "poma"
    assert comparison["baseline_system"] == "baseline"
    assert comparison["paired_bootstrap"]["em"]["point_estimate"] == 0.0
    assert (
        comparison["paired_bootstrap"]["answerability_f1"]["point_estimate"]
        == pytest.approx(-1 / 6)
    )
    assert report["poma_traces"]["structured_output"] == {
        "calls": 2,
        "missing_schema_telemetry_records": 0,
        "initial_schema_valid_rate": 0.5,
        "repair_attempt_rate": 0.5,
        "repair_success_rate": 1.0,
    }
    assert report["poma_traces"]["cost"]["total_cost_usd"] is None
    assert report["interpretation_gate"] == {
        "minimum_em_difference": 0.02,
        "observed_em_difference": 0.0,
        "paired_ci_excludes_zero": False,
        "passes_backbone_gate": False,
    }


def test_revision_analysis_rejects_duplicate_system_names(tmp_path):
    path = _write(tmp_path / "records.json", [])

    with pytest.raises(ValueError, match="Duplicate system name"):
        run_revision_analysis.parse_systems([f"same={path}", f"same={path}"])


def test_revision_analysis_rejects_incomplete_evaluator_reports():
    report = {
        "metrics": {
            "f1": {"f1": 1.0},
            "em": {"value": 1.0},
            "rouge1": {"f1": 1.0},
            "meteor": {"value": 1.0},
        },
        "analyses": {},
        "metric_errors": {},
    }

    with pytest.raises(
        run_revision_analysis.RevisionAnalysisError,
        match="answerability_f1",
    ):
        run_revision_analysis.validate_evaluation_report(
            report,
            system_name="poma",
        )

    report["analyses"]["answerability_f1"] = {}
    report["metrics"]["f1"] = None
    with pytest.raises(
        run_revision_analysis.RevisionAnalysisError,
        match="f1",
    ):
        run_revision_analysis.validate_evaluation_report(
            report,
            system_name="poma",
        )
