"""YesNo specialist - boolean verification against table data."""

from __future__ import annotations

import re
import unicodedata

from src.agents.specialists._base_specialist import BaseSpecialistAgent
from src.contracts.responses import RefinedQuery, SpecialistResult


_HIGHER_THAN_RE = re.compile(r"\bcao hon\s+([-+]?\d+(?:[,.]\d+)?)\b")
_FLOOR_VALUE_RE = re.compile(r"\b(?:so tang|tang)\s*:\s*([-+]?\d+(?:[,.]\d+)?)\b")


def _fold_ascii(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _parse_number(text: str) -> float:
    return float(text.replace(",", "."))


class YesNoAgent(BaseSpecialistAgent):
    name = "YesNo"
    prompt_name = "specialists/yesno"

    def run(self, refined_query: RefinedQuery, table_flattened: str) -> SpecialistResult:
        result = super().run(refined_query, table_flattened)
        return self._correct_floor_comparison(refined_query, result)

    @staticmethod
    def _correct_floor_comparison(
        refined_query: RefinedQuery,
        result: SpecialistResult,
    ) -> SpecialistResult:
        question = _fold_ascii(refined_query.normalized_question)
        if "so tang" not in question:
            return result

        threshold_match = _HIGHER_THAN_RE.search(question)
        if threshold_match is None:
            return result

        evidence_text = " | ".join(item.text for item in result.evidence)
        value_match = _FLOOR_VALUE_RE.search(_fold_ascii(evidence_text))
        if value_match is None:
            return result

        value = _parse_number(value_match.group(1))
        threshold = _parse_number(threshold_match.group(1))
        corrected = "C\u00f3" if value > threshold else "Kh\u00f4ng"
        if result.answer == corrected:
            return result

        return SpecialistResult(
            agent_name=result.agent_name,
            answer=corrected,
            evidence=result.evidence,
            confidence=max(result.confidence, 0.95),
            reason=f"Corrected floor comparison from evidence: {value:g} > {threshold:g}.",
        )
