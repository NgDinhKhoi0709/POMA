"""Who specialist â€” person entity extraction."""

from src.agents.specialists._base_specialist import BaseSpecialistAgent


class WhoAgent(BaseSpecialistAgent):
    name = "Who"
    prompt_name = "specialists/who"
