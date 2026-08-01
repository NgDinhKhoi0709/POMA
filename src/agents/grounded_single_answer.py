"""Select or synthesize one answer using only the table and candidates."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from evaluation.normalization import normalize_text

from src.agents.base_agent import BaseAgent
from src.contracts.finalization import (
    GroundedAnswer,
    GroundedAnswerRequest,
    GroundedDecision,
)
from src.contracts.structured_outputs import (
    ResponseSchema,
    schema_for_call,
    validate_domain_payload,
)
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

        if not self._selected_answer_matches(result, request):
            repair_prompt = (
                f"{prompt}\n\n"
                "The previous JSON response failed semantic validation:\n"
                "GroundedSingleAnswer selected final_answer must match an input "
                "candidate.\n"
                "Previous JSON response:\n"
                f"{json.dumps(data, ensure_ascii=False)}\n\n"
                "Re-evaluate the decision label against the ordered candidates and "
                "return one corrected JSON object. Keep the answer and evidence only "
                "if they remain grounded in the table."
            )
            repaired_data = self._call_decision_repair(repair_prompt)
            result = self._result_from_payload(repaired_data)
            if not self._selected_answer_matches(result, request):
                raise LLMContractError(
                    "GroundedSingleAnswer selected final_answer must match an input candidate"
                )
        return result

    @staticmethod
    def _selected_answer_matches(
        result: GroundedAnswer,
        request: GroundedAnswerRequest,
    ) -> bool:
        if result.decision is not GroundedDecision.SELECTED:
            return True
        normalized_answers = {
            normalize_text(candidate.answer) for candidate in request.candidates
        }
        return normalize_text(result.final_answer) in normalized_answers

    def _call_decision_repair(self, prompt: str) -> dict[str, Any]:
        base_schema = schema_for_call(self.response_schema_name)
        repair_json_schema = deepcopy(base_schema.json_schema)
        repair_json_schema["properties"]["decision"]["enum"] = [
            "corrected",
            "synthesized",
            "null",
        ]
        repair_schema = ResponseSchema(
            name=base_schema.name,
            version=base_schema.version,
            json_schema=repair_json_schema,
        )
        result = self._llm.generate_structured(
            prompt,
            schema=repair_schema,
            agent_name=self.name,
            prompt_name=self.prompt_name,
        )
        return result.data

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
