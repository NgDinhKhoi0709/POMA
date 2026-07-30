"""Tests for evaluation record loading and candidate policies."""

from __future__ import annotations

import pytest

from evaluation.exceptions import (
    EmptyCandidateError,
    MultipleCandidatesError,
)
from evaluation.io import align_records, apply_candidate_policy, extract_candidates


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        ({"prediction": ["new", "second"]}, ["new", "second"]),
        ({"prediction": "new"}, ["new"]),
        ({"predicted_answer": ["legacy", "second"]}, ["legacy", "second"]),
        ({"predicted_answer": "legacy"}, ["legacy"]),
        ({"predictions": ["older", "second"]}, ["older", "second"]),
        ({"predictions": "older"}, ["older"]),
        ({"answer": ["oldest", "second"]}, ["oldest", "second"]),
        ({"answer": "oldest"}, ["oldest"]),
    ],
)
def test_extract_candidates_uses_canonical_and_legacy_keys_in_priority_order(
    record, expected
):
    assert extract_candidates(record) == expected


def test_extract_candidates_prefers_prediction_over_legacy_keys():
    assert extract_candidates(
        {
            "prediction": "canonical",
            "predicted_answer": "legacy",
            "predictions": "older",
            "answer": "oldest",
        }
    ) == ["canonical"]


def test_all_policy_preserves_every_candidate():
    assert apply_candidate_policy(["first", "second"], "all") == ["first", "second"]


def test_first_policy_keeps_only_the_first_candidate():
    assert apply_candidate_policy(["first", "second"], "first") == ["first"]


def test_single_required_policy_accepts_exactly_one_candidate():
    assert apply_candidate_policy(["only"], "single-required") == ["only"]


def test_single_required_policy_rejects_zero_candidates():
    with pytest.raises(EmptyCandidateError):
        apply_candidate_policy([], "single-required")


def test_single_required_policy_rejects_multiple_candidates():
    with pytest.raises(MultipleCandidatesError):
        apply_candidate_policy(["first", "second"], "single-required")


def test_single_required_policy_failure_remains_aligned_for_scoring():
    samples, coverage = align_records(
        [{"qa_id": "zero", "prediction": []}, {"qa_id": "many", "prediction": ["a", "b"]}],
        [{"qa_id": "zero", "answer": "answer"}, {"qa_id": "many", "answer": "answer"}],
        candidate_policy="single-required",
    )

    assert coverage.evaluated_ids == ["many", "zero"]
    assert [sample.prediction for sample in samples] == [[""], [""]]
    assert [sample.metadata["candidate_policy_failure"]["candidate_count"] for sample in samples] == [2, 0]
