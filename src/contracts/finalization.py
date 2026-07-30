"""Immutable contracts for grounded answer finalization."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from evaluation.normalization import is_unanswerable_prediction


def _canonicalize_null(value: object) -> str:
    """Return the single pipeline spelling for any abstention value."""
    text = "" if value is None else str(value)
    if is_unanswerable_prediction(text):
        return "Null"
    return text


@dataclass(frozen=True)
class AnswerCandidate:
    """An ordered answer proposal supplied by one upstream source."""

    source_name: str
    answer: str

    def __post_init__(self) -> None:
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("AnswerCandidate source_name must be non-empty")
        object.__setattr__(self, "answer", _canonicalize_null(self.answer))


@dataclass(frozen=True)
class GroundedAnswerRequest:
    """The only context the grounded answer agent is allowed to receive."""

    question: str
    table_flattened: str
    candidates: list[AnswerCandidate]

    def __post_init__(self) -> None:
        if not isinstance(self.question, str) or not self.question.strip():
            raise ValueError("GroundedAnswerRequest question must be non-empty")
        if not isinstance(self.table_flattened, str) or not self.table_flattened.strip():
            raise ValueError("GroundedAnswerRequest table_flattened must be non-empty")
        if not isinstance(self.candidates, list) or not self.candidates:
            raise ValueError("GroundedAnswerRequest candidates must be non-empty")
        if not all(isinstance(candidate, AnswerCandidate) for candidate in self.candidates):
            raise ValueError("GroundedAnswerRequest candidates must be AnswerCandidate values")


class GroundedDecision(str, Enum):
    """How the final answer relates to the original candidate list."""

    SELECTED = "selected"
    CORRECTED = "corrected"
    SYNTHESIZED = "synthesized"
    NULL = "null"


@dataclass(frozen=True)
class GroundedAnswer:
    """A table-grounded final answer returned by the GSA agent."""

    final_answer: str
    decision: GroundedDecision
    supporting_evidence: list[str]
    reason: str = field(default="")

    def __post_init__(self) -> None:
        if not isinstance(self.final_answer, str) or not self.final_answer.strip():
            raise ValueError("GroundedAnswer final_answer must be non-empty")

        answer = _canonicalize_null(self.final_answer)
        object.__setattr__(self, "final_answer", answer)

        try:
            decision = GroundedDecision(self.decision)
        except (TypeError, ValueError) as exc:
            raise ValueError("GroundedAnswer decision is invalid") from exc
        object.__setattr__(self, "decision", decision)

        if not isinstance(self.supporting_evidence, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in self.supporting_evidence
        ):
            raise ValueError("GroundedAnswer supporting_evidence must contain strings")
        if decision is GroundedDecision.NULL and answer != "Null":
            raise ValueError("null decision requires final_answer=Null")
        if decision is not GroundedDecision.NULL and not self.supporting_evidence:
            raise ValueError("non-null GSA decisions require evidence")


__all__ = [
    "AnswerCandidate",
    "GroundedAnswer",
    "GroundedAnswerRequest",
    "GroundedDecision",
]
