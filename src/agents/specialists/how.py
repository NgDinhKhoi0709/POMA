"""How specialist â€” process / method extraction from table evidence."""

from src.agents.specialists._base_specialist import BaseSpecialistAgent


class HowAgent(BaseSpecialistAgent):
    name = "How"
    prompt_name = "specialists/how"
