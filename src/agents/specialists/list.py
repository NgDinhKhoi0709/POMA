"""List specialist â€” enumerate items matching conditions."""

from src.agents.specialists._base_specialist import BaseSpecialistAgent


class ListAgent(BaseSpecialistAgent):
    name = "List"
    prompt_name = "specialists/list"
