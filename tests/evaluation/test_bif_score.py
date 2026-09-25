"""Unit tests for BIF logic without downloading model dependencies."""

from __future__ import annotations

import pytest

from evaluation.bif_score import BIFScorer, combine_bif_scores
from evaluation.contracts import AlignedSample
from evaluation.vinliscore import resolve_entailment_id


class _FakePhoBERT:
    def score_pairs(self, candidates, references):
        assert list(candidates) == ["first", "best", "only"]
        assert list(references) == ["gold-a", "gold-a", "gold-b"]
        return [0.2, 0.8, 0.4]


class _FakeNLI:
    metadata = {"entailment_id": 0}

    def entailment_scores(self, premises, hypotheses):
        assert list(premises) == ["gold-a", "gold-a", "gold-b"]
        assert list(hypotheses) == ["first", "best", "only"]
        return [0.4, 0.6, 0.9]


def test_bif_uses_the_paper_weight_order():
    assert combine_bif_scores([0.8], [0.2], 0.7) == pytest.approx([0.62])


@pytest.mark.parametrize("alpha", [-0.1, 1.1, float("inf")])
def test_bif_rejects_invalid_alpha(alpha):
    with pytest.raises(ValueError, match="alpha"):
        combine_bif_scores([0.5], [0.5], alpha)


def test_bif_selects_the_best_candidate_and_preserves_nli_direction():
    scorer = BIFScorer.from_scorers(_FakePhoBERT(), _FakeNLI(), alpha=0.5)
    metric, details = scorer.evaluate_samples(
        [
            AlignedSample("a", ["first", "best"], "gold-a"),
            AlignedSample("b", ["only"], "gold-b"),
        ]
    )

    assert [detail["candidate"] for detail in details] == ["best", "only"]
    assert metric == {
        "count": 2,
        "value": pytest.approx(0.675),
        "phobert_f1": pytest.approx(0.6),
        "nli_entailment": pytest.approx(0.75),
        "skipped_empty_predictions": 0,
    }


def test_entailment_mapping_uses_checkpoint_metadata_before_any_index_guess():
    assert resolve_entailment_id({"contradiction": 0, "entailment": 2}) == 2
    assert resolve_entailment_id({"LABEL_0": 0}, entailment_id=0) == 0
    with pytest.raises(ValueError, match="Cannot find"):
        resolve_entailment_id({"LABEL_0": 0})


def test_bif_skips_empty_predictions_in_non_strict_evaluation():
    scorer = BIFScorer.from_scorers(_FakePhoBERT(), _FakeNLI(), alpha=0.5)
    metric, details = scorer.evaluate_samples(
        [
            AlignedSample("a", ["first", "best"], "gold-a"),
            AlignedSample("b", ["only"], "gold-b"),
            AlignedSample("failed", [""], "gold-failed"),
        ]
    )

    assert len(details) == 2
    assert metric["count"] == 2
    assert metric["skipped_empty_predictions"] == 1
