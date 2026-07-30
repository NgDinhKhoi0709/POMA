"""Select or synthesize one answer using only the table and candidates."""

from __future__ import annotations

import json
from typing import Any

from evaluation.normalization import normalize_text

from src.agents.base_agent import BaseAgent
from src.contracts.finalization import (
    GroundedAnswer,
    GroundedAnswerRequest,
    GroundedDecision,
)
from src.contracts.structured_outputs import validate_domain_payload
from src.errors import LLMContractError


class GroundedSingleAnswerAgent(BaseAgent):
    """Return one validated, table-grounded answer for ordered candidates."""

    name = "GroundedSingleAnswer"
    prompt_name = "grounded_single_answer"
    response_schema_name = "gsa.v1"

    def run(self, request: GroundedAnswerRequest) -> GroundedAnswer:
        """Produce a result whose decision satisfies the GSA semantic contract."""
        if not isinstance(request, GroundedAnswerRequest):
            raise ValueError("request must be a GroundedAnswerRequest")

        candidates = [
            {"source_name": candidate.source_name, "answer": candidate.answer}
            for candidate in request.candidates
        ]
        prompt = self._load_prompt(
            question=request.question,
            table_flattened=request.table_flattened,
            candidates=json.dumps(candidates, ensure_ascii=False),
        )
        data = self._call_llm_json(prompt)
        result = self._result_from_payload(data)

        if result.decision is GroundedDecision.SELECTED:
            normalized_answers = {
                normalize_text(candidate.answer) for candidate in request.candidates
            }
            if normalize_text(result.final_answer) not in normalized_answers:
                raise LLMContractError(
                    "GroundedSingleAnswer selected final_answer must match an input candidate"
                )
        return result

    @staticmethod
    def _result_from_payload(data: dict[str, Any]) -> GroundedAnswer:
        if not isinstance(data, dict):
            raise LLMContractError("GroundedSingleAnswer response must be an object")

        required = ("final_answer", "supporting_evidence", "decision")
        for field_name in required:
            if field_name not in data:
                raise LLMContractError(
                    f"GroundedSingleAnswer response is missing field: {field_name}"
                )

        answer = data["final_answer"]
        evidence = data["supporting_evidence"]
        decision = data["decision"]
        if not isinstance(answer, str):
            raise LLMContractError(
                "GroundedSingleAnswer field 'final_answer' must be a string"
            )
        if not isinstance(evidence, list) or not all(
            isinstance(item, str) for item in evidence
        ):
            raise LLMContractError(
                "GroundedSingleAnswer field 'supporting_evidence' must be a list of strings"
            )
        if not isinstance(decision, str):
            raise LLMContractError(
                "GroundedSingleAnswer field 'decision' must be a string"
            )

        try:
            result = GroundedAnswer(answer, GroundedDecision(decision), evidence)
        except ValueError as exc:
            raise LLMContractError(str(exc)) from exc

        try:
            validate_domain_payload(
                "gsa.v1",
                {
                    "final_answer": result.final_answer,
                    "supporting_evidence": result.supporting_evidence,
                    "decision": result.decision.value,
                },
            )
        except ValueError as exc:
            raise LLMContractError(str(exc)) from exc
        return result


__all__ = ["GroundedSingleAnswerAgent"]
