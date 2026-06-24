"""
QuestionRefiner agent.

Responsibilities:
  - Normalise hint aliases -> canonical tokens (Option A).
  - Extract structured fields (target, constraints) from the raw question
    via an LLM call.
  - Does NOT answer the question.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.contracts.enums import HINT_ALIASES_TO_CANONICAL, HintType
from src.contracts.responses import RefinedQuery
from src.errors import LLMContractError

logger = logging.getLogger(__name__)


def _canonicalize_hints(raw_hints: List[str]) -> List[str]:
    """Map each hint to its canonical token; drop unknowns."""

    canonical_values = {h.value for h in HintType}
    result: List[str] = []
    seen = set()
    for h in raw_hints:
        c = HINT_ALIASES_TO_CANONICAL.get(h, h)
        if c in canonical_values and c not in seen:
            seen.add(c)
            result.append(c)
    return result


def _require_field(data: Dict[str, Any], key: str) -> Any:
    if key not in data:
        raise LLMContractError(f"QuestionRefiner response is missing field: {key}")
    return data[key]


def _require_string_field(data: Dict[str, Any], key: str) -> str:
    value = _require_field(data, key)
    if not isinstance(value, str):
        raise LLMContractError(f"QuestionRefiner field '{key}' must be a string")
    text = value.strip()
    if not text:
        raise LLMContractError(f"QuestionRefiner field '{key}' must be non-empty")
    return text


def _require_optional_string_field(data: Dict[str, Any], key: str) -> Optional[str]:
    value = _require_field(data, key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise LLMContractError(f"QuestionRefiner field '{key}' must be a string or null")
    text = value.strip()
    if not text:
        raise LLMContractError(f"QuestionRefiner field '{key}' must be null or non-empty")
    return text


def _require_constraints(data: Dict[str, Any]) -> List[str]:
    value = _require_field(data, "constraints")
    if not isinstance(value, list):
        raise LLMContractError("QuestionRefiner field 'constraints' must be a list")

    constraints: List[str] = []
    for item in value:
        if not isinstance(item, str):
            raise LLMContractError("QuestionRefiner constraints entries must be strings")
        text = item.strip()
        if not text:
            raise LLMContractError("QuestionRefiner constraints entries must be non-empty")
        constraints.append(text)
    return constraints


class QuestionRefinerAgent(BaseAgent):
    name = "QuestionRefiner"
    prompt_name = "question_refiner"

    def run(self, question: str, hints: List[str]) -> RefinedQuery:
        canonical_hints = _canonicalize_hints(hints)

        prompt = self._load_prompt(
            question=question,
            hints=json.dumps(hints, ensure_ascii=False),
        )

        try:
            data = self._call_llm_json(prompt)
        except LLMContractError:
            logger.warning(
                "QuestionRefiner LLM contract failed; falling back to raw question "
                "with empty target/constraints."
            )
            return RefinedQuery(
                normalized_question=question.strip() or question,
                hints=canonical_hints,
                target=None,
                constraints=[],
            )

        normalized_question = _require_string_field(data, "normalized_question")
        target = _require_optional_string_field(data, "target")
        constraints = _require_constraints(data)

        return RefinedQuery(
            normalized_question=normalized_question,
            hints=canonical_hints,
            target=target,
            constraints=constraints,
        )
