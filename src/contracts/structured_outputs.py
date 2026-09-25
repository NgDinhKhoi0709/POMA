"""Structured-output contracts shared by POMA agents and baselines."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .enums import HintType


class StructuredContractError(ValueError):
    """Raised when a payload violates a structured-output domain invariant."""


@dataclass(frozen=True)
class ResponseSchema:
    name: str
    version: str
    json_schema: dict[str, Any]


@dataclass(frozen=True)
class CallContext:
    qa_id: str | None
    agent_name: str
    prompt_name: str
    model: str


class StructuredOutputMode(str, Enum):
    STRICT_JSON_SCHEMA = "strict_json_schema"
    JSON_OBJECT = "json_object"
    PROMPT_ONLY = "prompt_only"
    JSON_TEXT_EXTRACT = "json_text_extract"


@dataclass(frozen=True)
class StructuredResult:
    data: dict[str, Any]
    raw_response: str
    schema_name: str
    schema_valid: bool
    repair_attempted: bool
    repair_succeeded: bool
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float | None


def _closed_object(
    properties: dict[str, Any], required: list[str]
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


_NULLABLE_STRING = {"oneOf": [{"type": "string"}, {"type": "null"}]}
_STRING_LIST = {"type": "array", "items": {"type": "string"}}
_EVIDENCE_ITEM = _closed_object(
    {
        "text": {"type": "string"},
        "row_index": {"oneOf": [{"type": "integer"}, {"type": "null"}]},
        "col": _NULLABLE_STRING,
    },
    ["text", "row_index", "col"],
)


STRUCTURED_SCHEMAS: dict[str, ResponseSchema] = {
    "hint_predictor.v1": ResponseSchema(
        name="hint_predictor.v1",
        version="v1",
        json_schema=_closed_object(
            {
                "predicted_hints": {
                    "type": "array",
                    "items": {"type": "string", "enum": [hint.value for hint in HintType]},
                }
            },
            ["predicted_hints"],
        ),
    ),
    "question_refiner.v1": ResponseSchema(
        name="question_refiner.v1",
        version="v1",
        json_schema=_closed_object(
            {
                "normalized_question": {"type": "string"},
                "target": _NULLABLE_STRING,
                "constraints": _STRING_LIST,
            },
            ["normalized_question", "target", "constraints"],
        ),
    ),
    "specialist.v1": ResponseSchema(
        name="specialist.v1",
        version="v1",
        json_schema=_closed_object(
            {
                "answer": _NULLABLE_STRING,
                "evidence": {
                    "type": "array",
                    "items": {"oneOf": [{"type": "string"}, _EVIDENCE_ITEM]},
                },
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "reason": {"type": "string"},
            },
            ["answer", "evidence", "confidence", "reason"],
        ),
    ),
    "answer_normalization.v1": ResponseSchema(
        name="answer_normalization.v1",
        version="v1",
        json_schema=_closed_object({"answers": _STRING_LIST}, ["answers"]),
    ),
    "gsa.v1": ResponseSchema(
        name="gsa.v1",
        version="v1",
        json_schema=_closed_object(
            {
                "final_answer": {"type": "string"},
                "supporting_evidence": _STRING_LIST,
                "decision": {
                    "type": "string",
                    "enum": ["selected", "corrected", "synthesized", "null"],
                },
            },
            ["final_answer", "supporting_evidence", "decision"],
        ),
    ),
    "baseline_zero_shot.v1": ResponseSchema(
        name="baseline_zero_shot.v1",
        version="v1",
        json_schema=_closed_object({"final_answer": _NULLABLE_STRING}, ["final_answer"]),
    ),
    "header_filter.v1": ResponseSchema(
        name="header_filter.v1",
        version="v1",
        json_schema=_closed_object({"selected_headers": _STRING_LIST}, ["selected_headers"]),
    ),
    "baseline_few_shot.v1": ResponseSchema(
        name="baseline_few_shot.v1",
        version="v1",
        json_schema=_closed_object({"final_answer": _NULLABLE_STRING}, ["final_answer"]),
    ),
    "baseline_cot.v1": ResponseSchema(
        name="baseline_cot.v1",
        version="v1",
        json_schema=_closed_object({"final_answer": _NULLABLE_STRING}, ["final_answer"]),
    ),
    "baseline_task_decomposition.v1": ResponseSchema(
        name="baseline_task_decomposition.v1",
        version="v1",
        json_schema=_closed_object({"final_answer": _NULLABLE_STRING}, ["final_answer"]),
    ),
}


def schema_for_call(name: str) -> ResponseSchema:
    """Return the response schema registered for a POMA-owned LLM call."""
    try:
        return STRUCTURED_SCHEMAS[name]
    except KeyError as exc:
        raise StructuredContractError(
            f"Unknown structured output schema: {name}"
        ) from exc


def validate_domain_payload(name: str, data: dict[str, Any]) -> None:
    """Validate semantic invariants that are not captured by JSON Schema."""
    if name == "gsa.v1":
        decision = data["decision"]
        answer = data["final_answer"].strip()
        evidence = data["supporting_evidence"]
        if not answer:
            raise StructuredContractError("gsa final_answer must be non-empty")
        if decision == "null" and answer.lower() != "null":
            raise StructuredContractError("null decision requires final_answer=Null")
        if decision != "null" and not evidence:
            raise StructuredContractError("non-null GSA decisions require evidence")
    elif name == "hint_predictor.v1" and not data["predicted_hints"]:
        raise StructuredContractError("predicted_hints must be a non-empty list")
    elif name == "answer_normalization.v1" and not data["answers"]:
        raise StructuredContractError("answers must be a non-empty list")


__all__ = [
    "CallContext",
    "ResponseSchema",
    "STRUCTURED_SCHEMAS",
    "StructuredContractError",
    "StructuredOutputMode",
    "StructuredResult",
    "schema_for_call",
    "validate_domain_payload",
]
