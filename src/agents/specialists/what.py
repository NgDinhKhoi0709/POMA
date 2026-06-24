"""What specialist â€” entity / attribute extraction."""

from src.agents.specialists._base_specialist import BaseSpecialistAgent


class WhatAgent(BaseSpecialistAgent):
    name = "What"
    prompt_name = "specialists/what"
