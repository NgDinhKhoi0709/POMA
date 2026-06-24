"""MathematicalReasoning specialist - pure LLM mathematical reasoning."""

from __future__ import annotations

from src.agents.specialists._base_specialist import BaseSpecialistAgent


class MathematicalReasoningAgent(BaseSpecialistAgent):
    name = "MathematicalReasoning"
    prompt_name = "specialists/mathematical_reasoning"
