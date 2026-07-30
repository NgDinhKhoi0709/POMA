"""File loading and qa_id alignment for evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping

from .contracts import AlignedSample, AlignmentCoverage
from .exceptions import (
    CandidatePolicyError,
    EmptyCandidateError,
    EvaluationDataError,
    MultipleCandidatesError,
)

CandidatePolicy = Literal["all", "first", "single-required"]


def load_json_records(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    if source.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("qas", "table", "tables", "predictions"):
            if isinstance(payload.get(key), list):
                return payload[key]
    raise EvaluationDataError(
        f"{source} must contain a JSON list, JSONL records, or a supported record list"
    )


def load_qas_records(path: str | Path) -> list[dict[str, Any]]:
    return load_json_records(path)


def extract_candidates(record: Mapping[str, Any]) -> list[str]:
    raw = None
    for key in ("prediction", "predicted_answer", "predictions", "answer"):
        if key in record:
            raw = record[key]
            break
    if isinstance(raw, (list, tuple)):
        return [str(value).strip() for value in raw if value is not None]
    if raw is None:
        return []
    return [str(raw).strip()]


def apply_candidate_policy(
    candidates: list[str], candidate_policy: CandidatePolicy = "all"
) -> list[str]:
    """Apply one explicit candidate policy to extracted predictions."""
    if candidate_policy == "all":
        return candidates
    if candidate_policy == "first":
        return candidates[:1]
    if candidate_policy == "single-required":
        if not candidates:
            raise EmptyCandidateError(len(candidates))
        if len(candidates) > 1:
            raise MultipleCandidatesError(len(candidates))
        return candidates
    raise EvaluationDataError(f"Unsupported candidate policy: {candidate_policy!r}")


def align_records(
    predictions: Iterable[Mapping[str, Any]],
    references: Iterable[Mapping[str, Any]],
    *,
    candidate_policy: CandidatePolicy = "all",
) -> tuple[list[AlignedSample], AlignmentCoverage]:
    """Align predictions to references while retaining policy failures."""
    prediction_by_id = {
        str(item["qa_id"]): item
        for item in predictions
        if item.get("qa_id") is not None
    }
    reference_by_id = {
        str(item["qa_id"]): item
        for item in references
        if item.get("qa_id") is not None
    }
    samples: list[AlignedSample] = []
    for qa_id in sorted(prediction_by_id.keys() & reference_by_id.keys()):
        prediction, reference = prediction_by_id[qa_id], reference_by_id[qa_id]
        source_candidates = extract_candidates(prediction)
        metadata = dict(reference)
        metadata["source_candidate_count"] = len(source_candidates)
        try:
            evaluated_candidates = apply_candidate_policy(
                source_candidates, candidate_policy
            )
        except CandidatePolicyError as error:
            evaluated_candidates = []
            metadata["candidate_policy_failure"] = {
                "candidate_count": error.candidate_count,
                "error": error.error_code,
            }
        metadata["evaluated_candidate_count"] = len(evaluated_candidates)
        samples.append(
            AlignedSample(
                qa_id=qa_id,
                prediction=evaluated_candidates or [""],
                reference=str(reference.get("answer", "")),
                hints=[str(value) for value in reference.get("hints", []) or []],
                table_id=reference.get("table_id"),
                metadata=metadata,
            )
        )
    return samples, AlignmentCoverage(
        evaluated_ids=[sample.qa_id for sample in samples],
        missing_predictions=sorted(reference_by_id.keys() - prediction_by_id.keys()),
        extra_predictions=sorted(prediction_by_id.keys() - reference_by_id.keys()),
    )
