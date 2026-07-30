"""Adapters that apply one answer-finalization policy to raw candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.agents.answer_normalization import AnswerNormalizationAgent
from src.agents.grounded_single_answer import GroundedSingleAnswerAgent
from src.contracts.finalization import AnswerCandidate, GroundedAnswerRequest


@dataclass(frozen=True)
class FinalizationSourceFailure:
    """A typed upstream failure that must not trigger a paid finalizer call."""

    error_type: str
    message: str


@dataclass(frozen=True)
class FinalizationRequest:
    """The context available to a finalizer for one table question."""

    qa_id: str
    table_id: str
    question: str
    table_flattened: str
    candidates: list[AnswerCandidate]
    native_question: str | None = None
    native_target: str | None = None
    source_failure: FinalizationSourceFailure | None = None


@dataclass(frozen=True)
class FinalizationResult:
    """A finalizer's prediction and audit information."""

    prediction: list[str]
    finalizer: str
    trace: dict[str, Any]
    usage: dict[str, Any]


def _usage_snapshot(agent: object) -> dict[str, int | float | None] | None:
    llm = getattr(agent, "_llm", None)
    field_names = (
        "total_prompt_tokens",
        "total_completion_tokens",
        "total_total_tokens",
        "total_cost_usd",
    )
    if not all(hasattr(llm, field_name) for field_name in field_names):
        return None
    return {
        "prompt_tokens": getattr(llm, "total_prompt_tokens"),
        "completion_tokens": getattr(llm, "total_completion_tokens"),
        "total_tokens": getattr(llm, "total_total_tokens"),
        "cost_usd": getattr(llm, "total_cost_usd"),
    }


def _usage_delta(
    before: dict[str, int | float | None] | None,
    agent: object,
) -> dict[str, int | float | None]:
    after = _usage_snapshot(agent)
    if before is None or after is None:
        return {}

    cost_before = before["cost_usd"]
    cost_after = after["cost_usd"]
    cost_usd: float | None
    if cost_before is None or cost_after is None:
        cost_usd = None
    else:
        cost_usd = float(cost_after) - float(cost_before)

    return {
        "prompt_tokens": int(after["prompt_tokens"]) - int(before["prompt_tokens"]),
        "completion_tokens": int(after["completion_tokens"])
        - int(before["completion_tokens"]),
        "total_tokens": int(after["total_tokens"]) - int(before["total_tokens"]),
        "cost_usd": cost_usd,
    }


class NativeAnswerNormalizationFinalizer:
    """Apply Answer Normalization with POMA's native target/source metadata."""

    def __init__(self, normalizer: AnswerNormalizationAgent) -> None:
        self._normalizer = normalizer

    def finalize(self, request: FinalizationRequest) -> FinalizationResult:
        before = _usage_snapshot(self._normalizer)
        prediction = self._normalizer.run_many(
            answers=[candidate.answer for candidate in request.candidates],
            question=request.native_question or request.question,
            target=request.native_target,
            specialist_names_by_answer=[
                candidate.source_name for candidate in request.candidates
            ],
        )
        return FinalizationResult(
            prediction=prediction,
            finalizer="an-native",
            trace={"mode": "an-native"},
            usage=_usage_delta(before, self._normalizer),
        )


class CommonAnswerNormalizationFinalizer:
    """Apply the shared Answer Normalization policy without POMA metadata."""

    def __init__(self, normalizer: AnswerNormalizationAgent) -> None:
        self._normalizer = normalizer

    def finalize(self, request: FinalizationRequest) -> FinalizationResult:
        before = _usage_snapshot(self._normalizer)
        prediction = self._normalizer.run_many(
            answers=[candidate.answer for candidate in request.candidates],
            question=request.question,
            target=None,
            specialist_names_by_answer=None,
        )
        return FinalizationResult(
            prediction=prediction,
            finalizer="an-common",
            trace={"mode": "an-common"},
            usage=_usage_delta(before, self._normalizer),
        )


class GroundedSingleAnswerFinalizer:
    """Ask GSA to select one table-grounded answer from raw candidates."""

    def __init__(self, grounded_agent: GroundedSingleAnswerAgent) -> None:
        self._grounded_agent = grounded_agent

    def finalize(self, request: FinalizationRequest) -> FinalizationResult:
        before = _usage_snapshot(self._grounded_agent)
        grounded_answer = self._grounded_agent.run(
            GroundedAnswerRequest(
                question=request.question,
                table_flattened=request.table_flattened,
                candidates=request.candidates,
            )
        )
        if not isinstance(grounded_answer.final_answer, str):
            raise ValueError("Grounded single-answer finalizer requires exactly one string")

        return FinalizationResult(
            prediction=[grounded_answer.final_answer],
            finalizer="gsa",
            trace={
                "mode": "gsa",
                "decision": grounded_answer.decision.value,
                "supporting_evidence": grounded_answer.supporting_evidence,
                "reason": grounded_answer.reason,
            },
            usage=_usage_delta(before, self._grounded_agent),
        )


__all__ = [
    "CommonAnswerNormalizationFinalizer",
    "FinalizationRequest",
    "FinalizationResult",
    "FinalizationSourceFailure",
    "GroundedSingleAnswerFinalizer",
    "NativeAnswerNormalizationFinalizer",
]
