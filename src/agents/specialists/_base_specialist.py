"""
Shared base for all specialist agents.

Every specialist receives a ``RefinedQuery`` + ``table_flattened`` and
returns a ``SpecialistResult``.  The base class handles prompt rendering,
LLM call, and response parsing into the common envelope.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.contracts.responses import EvidenceItem, RefinedQuery, SpecialistResult
from src.errors import LLMContractError


class BaseSpecialistAgent(BaseAgent):
    """Subclasses only need to set ``name`` and ``prompt_name``."""

    def run(self, refined_query: RefinedQuery, table_flattened: str) -> SpecialistResult:
        prompt = self._load_prompt(
            normalized_question=refined_query.normalized_question,
            hints=json.dumps(refined_query.hints, ensure_ascii=False),
            target=refined_query.target or "",
            constraints=json.dumps(refined_query.constraints, ensure_ascii=False),
            table_flattened=table_flattened,
        )

        data = self._call_llm_json(prompt)
        return self._parse_result(data)

    def _parse_result(self, data: Dict[str, Any]) -> SpecialistResult:
        if "answer" not in data:
            raise LLMContractError(f"{self.name} response is missing field: answer")
        if "evidence" not in data:
            raise LLMContractError(f"{self.name} response is missing field: evidence")
        if "confidence" not in data:
            raise LLMContractError(f"{self.name} response is missing field: confidence")
        if "reason" not in data:
            raise LLMContractError(f"{self.name} response is missing field: reason")

        answer = _parse_answer(data["answer"], agent_name=self.name)
        evidence = _parse_evidence(data["evidence"], agent_name=self.name)
        confidence = _parse_confidence(data["confidence"], agent_name=self.name)
        reason = _parse_reason(data["reason"], agent_name=self.name)

        return SpecialistResult(
            agent_name=self.name,
            answer=answer,
            evidence=evidence,
            confidence=confidence,
            reason=reason,
        )


def _parse_answer(raw: Any, *, agent_name: str) -> str:
    if raw is None:
        return "Null"
    if isinstance(raw, (str, int, float, bool)):
        text = str(raw).strip()
        if not text:
            return "Null"
        if text.lower() == "null":
            return "Null"
        return text
    raise LLMContractError(f"{agent_name} field 'answer' must be a scalar or null")


def _parse_reason(raw: Any, *, agent_name: str) -> str:
    if not isinstance(raw, str):
        raise LLMContractError(f"{agent_name} field 'reason' must be a non-empty string")
    text = raw.strip()
    if not text:
        raise LLMContractError(f"{agent_name} field 'reason' must be a non-empty string")
    return text


def _parse_confidence(raw: Any, *, agent_name: str) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise LLMContractError(
            f"{agent_name} field 'confidence' must be numeric"
        ) from exc


def _parse_evidence(raw: Any, *, agent_name: str) -> List[EvidenceItem]:
    if not isinstance(raw, list):
        raise LLMContractError(f"{agent_name} field 'evidence' must be a list")
    items: List[EvidenceItem] = []
    for entry in raw:
        if isinstance(entry, dict):
            text = entry.get("text")
            if not isinstance(text, str) or not text.strip():
                raise LLMContractError(
                    f"{agent_name} evidence dict entries must include non-empty text"
                )
            items.append(EvidenceItem(
                text=text.strip(),
                row_index=entry.get("row_index"),
                col=entry.get("col"),
            ))
        elif isinstance(entry, str) and entry.strip():
            items.append(EvidenceItem(text=entry.strip()))
        else:
            raise LLMContractError(
                f"{agent_name} evidence entries must be non-empty strings or dicts"
            )
    return items
