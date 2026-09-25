"""Single public orchestration entry point for Open-ViTabQA evaluation."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from . import exact_match, f1, meteor, rouge1
from .answerability_f1 import evaluate_answerability
from .bif_score import BIFConfig, BIFScorer
from .cost import summarize_cost
from .contracts import AlignmentCoverage
from .exceptions import EvaluationDataError
from .io import (
    CandidatePolicy,
    align_records,
    extract_candidates,
    load_json_records,
    load_qas_records,
)
from .metrics_by_table_type import evaluate_by_table_type
from .rouge1_by_hint import evaluate_by_hint

DEFAULT_METRICS = ("f1", "em", "rouge1", "meteor")
SUPPORTED_METRICS = frozenset(
    (
        *DEFAULT_METRICS,
        "bif",
        "answerability_f1",
        "rouge1_by_hint",
        "cost",
        "metrics_by_table_type",
    )
)


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _scorer_sha256() -> str:
    """Fingerprint all local evaluator source files used by a report."""
    root = Path(__file__).resolve().parents[1]
    sources = sorted((root / "evaluation").rglob("*.py")) + [root / "run_eval.py"]
    digest = hashlib.sha256()
    for source in sources:
        digest.update(source.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _require_unique_ids(records: list[dict[str, Any]], label: str) -> None:
    ids: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping) or record.get("qa_id") is None:
            raise EvaluationDataError(f"{label} record {index} has no qa_id")
        qa_id = str(record["qa_id"])
        if not qa_id.strip():
            raise EvaluationDataError(f"{label} record {index} has an empty qa_id")
        ids.append(qa_id)
    duplicates = sorted(qa_id for qa_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise EvaluationDataError(f"duplicate {label} qa_id: {duplicates[:5]}")


def _require_valid_input(
    predictions: list[dict[str, Any]],
    coverage: AlignmentCoverage,
    candidate_policy_failures: list[dict[str, Any]],
) -> None:
    if coverage.missing_predictions:
        raise EvaluationDataError(
            f"missing predictions: {len(coverage.missing_predictions)} "
            f"(e.g. {coverage.missing_predictions[:5]})"
        )
    if coverage.extra_predictions:
        raise EvaluationDataError(
            f"extra predictions: {len(coverage.extra_predictions)} "
            f"(e.g. {coverage.extra_predictions[:5]})"
        )
    if candidate_policy_failures:
        raise EvaluationDataError(
            f"candidate policy failures: {len(candidate_policy_failures)} "
            f"(e.g. {candidate_policy_failures[:2]})"
        )
    empty_ids = []
    for record in predictions:
        candidates = extract_candidates(record)
        if not candidates or not candidates[0].strip():
            empty_ids.append(str(record["qa_id"]))
    if empty_ids:
        raise EvaluationDataError(
            f"empty answers: {len(empty_ids)} (e.g. {empty_ids[:5]})"
        )


def candidate_statistics(candidate_counts: Iterable[int]) -> dict[str, float | int]:
    """Summarize candidate counts, using nearest-rank p95."""
    counts = sorted(candidate_counts)
    count = len(counts)
    if not count:
        return {
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "p95": 0,
            "max": 0,
            "k_equals_one_rate": 0.0,
        }
    middle = count // 2
    median: float | int
    if count % 2:
        median = counts[middle]
    else:
        median = (counts[middle - 1] + counts[middle]) / 2
    return {
        "count": count,
        "mean": sum(counts) / count,
        "median": median,
        "p95": counts[math.ceil(0.95 * count) - 1],
        "max": counts[-1],
        "k_equals_one_rate": counts.count(1) / count,
    }


def _load_table_map(path: str | Path) -> dict[str, dict[str, Any]]:
    records = load_json_records(path)
    return {str(record["table_id"]): record for record in records if record.get("table_id") is not None}


def _core_metrics(samples: list, names: set[str]) -> dict[str, object]:
    result: dict[str, object] = {}
    if "f1" in names:
        result["f1"] = f1.aggregate(f1.score_sample(sample) for sample in samples)
    if "em" in names:
        result["em"] = exact_match.aggregate(exact_match.score_sample(sample) for sample in samples)
    if "rouge1" in names:
        result["rouge1"] = rouge1.aggregate(rouge1.score_sample(sample) for sample in samples)
    if "meteor" in names:
        result["meteor"] = meteor.aggregate(meteor.score_sample(sample) for sample in samples)
    return result


def evaluate_files(
    prediction_path: str | Path,
    qas_path: str | Path,
    *,
    tables_path: str | Path | None = None,
    output_path: str | Path | None = None,
    metrics: list[str] | tuple[str, ...] | None = None,
    fail_on_metric_error: bool = False,
    candidate_policy: CandidatePolicy = "all",
    strict: bool = False,
    bif_config: BIFConfig | None = None,
    bif_details_path: str | Path | None = None,
) -> dict[str, object]:
    """Evaluate one prediction file and optionally write one stable JSON report."""
    requested = set(metrics or DEFAULT_METRICS)
    if strict and requested - SUPPORTED_METRICS:
        raise EvaluationDataError(
            f"unsupported metrics: {sorted(requested - SUPPORTED_METRICS)}"
        )
    predictions = load_json_records(prediction_path)
    references = load_qas_records(qas_path)
    if strict:
        _require_unique_ids(predictions, "prediction")
        _require_unique_ids(references, "reference")
    samples, coverage = align_records(
        predictions, references, candidate_policy=candidate_policy
    )
    candidate_policy_failures = [
        {"qa_id": sample.qa_id, **sample.metadata["candidate_policy_failure"]}
        for sample in samples
        if "candidate_policy_failure" in sample.metadata
    ]
    if strict:
        _require_valid_input(predictions, coverage, candidate_policy_failures)
    report: dict[str, object] = {
        "inputs": {"predictions": str(prediction_path), "qas": str(qas_path)},
        "provenance": {
            "prediction_sha256": _sha256(prediction_path),
            "qas_sha256": _sha256(qas_path),
            "tables_sha256": _sha256(tables_path) if tables_path is not None else None,
            "scorer_sha256": _scorer_sha256(),
        },
        "strict": strict,
        "coverage": {
            "evaluated_ids": coverage.evaluated_ids,
            "missing_predictions": coverage.missing_predictions,
            "extra_predictions": coverage.extra_predictions,
        },
        "candidate_policy": candidate_policy,
        "source_candidate_statistics": candidate_statistics(
            sample.metadata["source_candidate_count"] for sample in samples
        ),
        "evaluated_candidate_statistics": candidate_statistics(
            sample.metadata["evaluated_candidate_count"] for sample in samples
        ),
        "candidate_policy_failures": candidate_policy_failures,
        "metrics": {},
        "metric_provenance": {},
        "analyses": {},
        "metric_errors": {},
    }
    try:
        report["metrics"] = _core_metrics(samples, requested)
        if "answerability_f1" in requested:
            report["analyses"]["answerability_f1"] = evaluate_answerability(samples)
        if "rouge1_by_hint" in requested:
            report["analyses"]["rouge1_by_hint"] = evaluate_by_hint(samples)
        if "cost" in requested:
            report["cost"] = summarize_cost(predictions)
        if "metrics_by_table_type" in requested:
            if tables_path is None:
                raise ValueError("tables_path is required for metrics_by_table_type")
            report["analyses"]["metrics_by_table_type"] = evaluate_by_table_type(samples, _load_table_map(tables_path))
        if "bif" in requested:
            if bif_config is None:
                raise ValueError(
                    "BIF was requested but no BIF configuration was supplied. "
                    "Pass --bif-nli-model."
                )
            bif_scorer = BIFScorer(bif_config)
            bif_metric, bif_details = bif_scorer.evaluate_samples(samples)
            report["metrics"]["bif"] = bif_metric
            report["metric_provenance"]["bif"] = bif_scorer.metadata
            if bif_details_path is not None:
                destination = Path(bif_details_path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(
                    json.dumps(bif_details, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
    except Exception as error:
        if fail_on_metric_error or strict:
            raise
        report["metric_errors"] = {"evaluation": str(error)}
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
