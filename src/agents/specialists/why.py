"""Why specialist â€” causal explanation from table evidence."""

from src.agents.specialists._base_specialist import BaseSpecialistAgent


class WhyAgent(BaseSpecialistAgent):
    name = "Why"
    prompt_name = "specialists/why"
