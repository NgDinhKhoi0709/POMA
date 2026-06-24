"""When specialist â€” temporal extraction (may invoke temporal tools)."""

from src.agents.specialists._base_specialist import BaseSpecialistAgent



class WhenAgent(BaseSpecialistAgent):
    name = "When"
    prompt_name = "specialists/when"
