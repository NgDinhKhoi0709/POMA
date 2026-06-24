"""Where specialist â€” location extraction."""

from src.agents.specialists._base_specialist import BaseSpecialistAgent


class WhereAgent(BaseSpecialistAgent):
    name = "Where"
    prompt_name = "specialists/where"
