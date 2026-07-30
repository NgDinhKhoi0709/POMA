"""Multilabel metrics for canonical POMA hint predictions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from src.contracts.enums import HINT_ALIASES_TO_CANONICAL, HintType

CANONICAL_HINTS = tuple(hint.value for hint in HintType)


def _canonical_hint(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Unknown hint: {value!r}")
    text = value.strip()
    canonical = HINT_ALIASES_TO_CANONICAL.get(text)
    if canonical is None:
        folded = text.casefold()
        canonical = next(
            (
                target
                for alias, target in HINT_ALIASES_TO_CANONICAL.items()
                if alias.casefold() == folded
            ),
            None,
        )
    if canonical is None:
        raise ValueError(f"Unknown hint: {value!r}")
    return canonical


def _canonical_set(values: object, qa_id: str) -> set[str]:
    if values is None:
        return set()
    if not isinstance(values, (list, tuple, set)):
        raise ValueError(f"Hints for qa_id={qa_id!r} must be a list")
    return {_canonical_hint(value) for value in values}


def _records_by_id(
    records: Iterable[Mapping[str, Any]],
    *,
    value_key: str,
) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for record in records:
        if not isinstance(record, Mapping) or record.get("qa_id") is None:
            raise ValueError("Every hint record must contain qa_id")
        qa_id = str(record["qa_id"])
        if qa_id in result:
            raise ValueError(f"Duplicate qa_id in hint records: {qa_id!r}")
        result[qa_id] = _canonical_set(record.get(value_key, []), qa_id)
    return result


def _prediction_map(
    predictions: Mapping[str, object] | Iterable[Mapping[str, Any]],
) -> dict[str, set[str]]:
    if isinstance(predictions, Mapping):
        return {
            str(qa_id): _canonical_set(values, str(qa_id))
            for qa_id, values in predictions.items()
        }
    return _records_by_id(predictions, value_key="predicted_hints")


def _class_metrics(
    true_positive: int,
    false_positive: int,
    false_negative: int,
) -> dict[str, float]:
    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    precision = (
        true_positive / precision_denominator if precision_denominator else 0.0
    )
    recall = true_positive / recall_denominator if recall_denominator else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        ),
    }


def evaluate_hint_metrics(
    qas: Iterable[Mapping[str, Any]],
    predictions: Mapping[str, object] | Iterable[Mapping[str, Any]],
) -> dict[str, object]:
    """Evaluate predicted hint sets over every QA, including missing outputs."""
    gold_by_id = _records_by_id(qas, value_key="hints")
    predicted_by_id = _prediction_map(predictions)
    qa_ids = list(gold_by_id)
    missing_ids = [qa_id for qa_id in qa_ids if qa_id not in predicted_by_id]
    extra_ids = sorted(set(predicted_by_id).difference(gold_by_id))
    pairs = [
        (gold_by_id[qa_id], predicted_by_id.get(qa_id, set()))
        for qa_id in qa_ids
    ]
    count = len(pairs)

    exact = sum(gold == predicted for gold, predicted in pairs)
    jaccard_values = [
        (
            len(gold & predicted) / len(gold | predicted)
            if gold | predicted
            else 1.0
        )
        for gold, predicted in pairs
    ]
    per_label: dict[str, dict[str, float | int]] = {}
    total_true_positive = 0
    total_false_positive = 0
    total_false_negative = 0
    for label in CANONICAL_HINTS:
        true_positive = sum(
            label in gold and label in predicted for gold, predicted in pairs
        )
        false_positive = sum(
            label not in gold and label in predicted for gold, predicted in pairs
        )
        false_negative = sum(
            label in gold and label not in predicted for gold, predicted in pairs
        )
        total_true_positive += true_positive
        total_false_positive += false_positive
        total_false_negative += false_negative
        per_label[label] = {
            "support": true_positive + false_negative,
            **_class_metrics(true_positive, false_positive, false_negative),
        }

    macro = {
        field: sum(float(values[field]) for values in per_label.values())
        / len(CANONICAL_HINTS)
        for field in ("precision", "recall", "f1")
    }
    return {
        "count": count,
        "coverage": {
            "predicted_ids": [qa_id for qa_id in qa_ids if qa_id in predicted_by_id],
            "missing_prediction_ids": missing_ids,
            "extra_prediction_ids": extra_ids,
        },
        "exact_set_accuracy": exact / count if count else 0.0,
        "jaccard": sum(jaccard_values) / count if count else 0.0,
        "micro": _class_metrics(
            total_true_positive,
            total_false_positive,
            total_false_negative,
        ),
        "macro": macro,
        "per_label": per_label,
    }


__all__ = ["CANONICAL_HINTS", "evaluate_hint_metrics"]
