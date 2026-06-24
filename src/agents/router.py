"""
Router agent.

Pure-logic (no LLM call): maps canonical hints to specialist agent names.
The Router itself only returns specialist names.
"""

from __future__ import annotations

from typing import List

from src.contracts.enums import HINT_TO_AGENT


class RouterAgent:
    name = "Router"

    @staticmethod
    def route(hints: List[str]) -> List[str]:
        """Return de-duplicated specialist agent names for the given hints."""
        seen: set[str] = set()
        agents: List[str] = []
        for hint in hints:
            agent = HINT_TO_AGENT.get(hint)
            if agent and agent not in seen:
                seen.add(agent)
                agents.append(agent)
        return agents
