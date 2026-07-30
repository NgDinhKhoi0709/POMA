import pytest

from evaluation.hint_metrics import evaluate_hint_metrics


def test_hint_metrics_use_aliases_and_the_complete_qas_denominator():
    qas = [
        {"qa_id": "q1", "hints": ["what", "where"]},
        {"qa_id": "q2", "hints": ["Who"]},
        {"qa_id": "q3", "hints": ["List"]},
        {"qa_id": "q4", "hints": ["How"]},
    ]
    predictions = [
        {"qa_id": "q1", "predicted_hints": ["What", "Where"]},
        {"qa_id": "q2", "predicted_hints": ["who", "list"]},
        {"qa_id": "q4", "predicted_hints": ["Why"]},
    ]

    result = evaluate_hint_metrics(qas, predictions)

    assert result["count"] == 4
    assert result["coverage"] == {
        "predicted_ids": ["q1", "q2", "q4"],
        "missing_prediction_ids": ["q3"],
        "extra_prediction_ids": [],
    }
    assert result["exact_set_accuracy"] == 0.25
    assert result["jaccard"] == 0.375
    assert result["micro"] == {
        "precision": 0.6,
        "recall": 0.6,
        "f1": 0.6,
    }
    assert result["macro"] == {
        "precision": 0.3,
        "recall": 0.3,
        "f1": 0.3,
    }
    assert result["per_label"]["Who"] == {
        "support": 1,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
    }
    assert result["per_label"]["List"] == {
        "support": 1,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
    }


def test_hint_metrics_accept_a_mapping_of_ids_to_predictions():
    result = evaluate_hint_metrics(
        [{"qa_id": "q1", "hints": ["Mathematical Reasoning"]}],
        {"q1": ["MathematicalReasoning"]},
    )

    assert result["exact_set_accuracy"] == 1.0
    assert result["per_label"]["MathematicalReasoning"]["support"] == 1


def test_hint_metrics_reject_unknown_labels_and_duplicate_ids():
    with pytest.raises(ValueError, match="Unknown hint"):
        evaluate_hint_metrics(
            [{"qa_id": "q1", "hints": ["unsupported"]}],
            {"q1": ["What"]},
        )

    with pytest.raises(ValueError, match="Duplicate qa_id"):
        evaluate_hint_metrics(
            [{"qa_id": "q1", "hints": ["What"]}],
            [
                {"qa_id": "q1", "predicted_hints": ["What"]},
                {"qa_id": "q1", "predicted_hints": ["Where"]},
            ],
        )
