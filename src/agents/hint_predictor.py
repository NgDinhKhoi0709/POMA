"""
HintPredictor agent.

Predicts canonical hints from the raw Vietnamese question and flattened table using an LLM.
"""

from __future__ import annotations

from typing import List

from src.agents.base_agent import BaseAgent
from src.contracts.enums import HintType
from src.errors import LLMContractError


class HintPredictorAgent(BaseAgent):
    name = "HintPredictor"
    prompt_name = "hint_predictor"

    def run(self, question: str, table_flattened: str) -> List[str]:
        """Predict canonical hints from the raw Vietnamese question and table context."""
        prompt = self._load_prompt(
            question=question,
            table_flattened=table_flattened,
        )

        data = self._call_llm_json(prompt)
        
        if "predicted_hints" not in data:
            raise LLMContractError("HintPredictor response is missing field: predicted_hints")

        raw_hints = data["predicted_hints"]
        if not isinstance(raw_hints, list):
            raise LLMContractError("HintPredictor field 'predicted_hints' must be a list")

        # Validate predicted hints against canonical HintType values
        canonical_values = {h.value for h in HintType}
        validated_hints: List[str] = []
        
        for hint in raw_hints:
            if not isinstance(hint, str):
                continue
            hint_clean = hint.strip()
            if hint_clean in canonical_values:
                if hint_clean not in validated_hints:
                    validated_hints.append(hint_clean)
            else:
                self._logger.warning("HintPredictor predicted invalid canonical hint: %s", hint_clean)

        return validated_hints
