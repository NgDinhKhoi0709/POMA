from types import SimpleNamespace

import pytest

from src.contracts.finalization import (
    AnswerCandidate,
    GroundedAnswer,
    GroundedDecision,
)
from src.finalization.finalizers import (
    CommonAnswerNormalizationFinalizer,
    FinalizationRequest,
    GroundedSingleAnswerFinalizer,
    NativeAnswerNormalizationFinalizer,
)


class _RecordingNormalizer:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def run_many(self, answers, question, target=None, specialist_names_by_answer=None):
        self.calls.append(
            {
                "answers": answers,
                "question": question,
                "target": target,
                "specialist_names_by_answer": specialist_names_by_answer,
            }
        )
        return self.result


class _RecordingGroundedAgent:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def run(self, request):
        self.calls.append(request)
        return self.result


class _UsageTrackingNormalizer(_RecordingNormalizer):
    def __init__(self, result):
        super().__init__(result)
        self._llm = SimpleNamespace(
            total_prompt_tokens=11,
            total_completion_tokens=7,
            total_total_tokens=18,
            total_cost_usd=None,
        )

    def run_many(self, *args, **kwargs):
        result = super().run_many(*args, **kwargs)
        self._llm.total_prompt_tokens += 3
        self._llm.total_completion_tokens += 2
        self._llm.total_total_tokens += 5
        return result


@pytest.fixture
def finalization_request():
    return FinalizationRequest(
        qa_id="qa-1",
        table_id="table-1",
        question="Which city?",
        table_flattened="[HEADER] city\n[ROW 1] Hanoi",
        candidates=[
            AnswerCandidate("WhereSpecialist", "Hanoi"),
            AnswerCandidate("Fallback", "Ha Noi"),
        ],
        native_target="city",
    )


def test_common_an_excludes_poma_metadata_and_preserves_answer_order(finalization_request):
    """Catch accidental target or source metadata leakage into common AN."""
    normalizer = _RecordingNormalizer(["Hanoi", "Ha Noi", "Hà Nội"])

    result = CommonAnswerNormalizationFinalizer(normalizer).finalize(finalization_request)

    assert normalizer.calls == [
        {
            "answers": ["Hanoi", "Ha Noi"],
            "question": "Which city?",
            "target": None,
            "specialist_names_by_answer": None,
        }
    ]
    assert result.prediction == ["Hanoi", "Ha Noi", "Hà Nội"]
    assert result.finalizer == "an-common"
    assert result.trace["mode"] == "an-common"
    assert result.usage == {}


def test_native_an_receives_only_native_target_and_source_names(finalization_request):
    """Catch native AN losing its established target and source semantics."""
    normalizer = _RecordingNormalizer(["Hanoi"])

    result = NativeAnswerNormalizationFinalizer(normalizer).finalize(finalization_request)

    assert normalizer.calls == [
        {
            "answers": ["Hanoi", "Ha Noi"],
            "question": "Which city?",
            "target": "city",
            "specialist_names_by_answer": ["WhereSpecialist", "Fallback"],
        }
    ]
    assert result.prediction == ["Hanoi"]
    assert result.finalizer == "an-native"
    assert result.trace["mode"] == "an-native"


def test_finalizer_preserves_unknown_usage_cost(finalization_request):
    """Catch an unknown provider cost being silently converted to zero."""
    normalizer = _UsageTrackingNormalizer(["Hanoi"])

    result = CommonAnswerNormalizationFinalizer(normalizer).finalize(finalization_request)

    assert result.usage == {
        "prompt_tokens": 3,
        "completion_tokens": 2,
        "total_tokens": 5,
        "cost_usd": None,
    }


def test_gsa_receives_table_and_returns_exactly_one_grounded_prediction(finalization_request):
    """Catch GSA bypassing its grounded request or emitting a best-of-K list."""
    grounded = _RecordingGroundedAgent(
        GroundedAnswer(
            final_answer="Hanoi",
            decision=GroundedDecision.SELECTED,
            supporting_evidence=["row 1 city: Hanoi"],
            reason="selected from the table",
        )
    )

    result = GroundedSingleAnswerFinalizer(grounded).finalize(finalization_request)

    assert len(grounded.calls) == 1
    grounded_request = grounded.calls[0]
    assert grounded_request.question == "Which city?"
    assert grounded_request.table_flattened == "[HEADER] city\n[ROW 1] Hanoi"
    assert grounded_request.candidates == finalization_request.candidates
    assert result.prediction == ["Hanoi"]
    assert result.finalizer == "gsa"
    assert result.trace == {
        "mode": "gsa",
        "decision": "selected",
        "supporting_evidence": ["row 1 city: Hanoi"],
        "reason": "selected from the table",
    }


def test_gsa_rejects_multiple_predictions_from_a_nonconforming_adapter(finalization_request):
    """Catch a GSA adapter that breaks the experiment's K=1 invariant."""
    grounded = _RecordingGroundedAgent(
        SimpleNamespace(
            final_answer=["Hanoi", "Ha Noi"],
            decision=GroundedDecision.SELECTED,
            supporting_evidence=["row 1 city: Hanoi"],
            reason="bad adapter",
        )
    )

    with pytest.raises(ValueError, match="exactly one"):
        GroundedSingleAnswerFinalizer(grounded).finalize(finalization_request)
