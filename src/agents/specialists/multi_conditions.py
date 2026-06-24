"""MultiConditions specialist â€” multi-predicate row filtering."""

from src.agents.specialists._base_specialist import BaseSpecialistAgent


class MultiConditionsAgent(BaseSpecialistAgent):
    name = "MultiConditions"
    prompt_name = "specialists/multi_conditions"
