"""
Abstract base class for every agent in the pipeline.

Subclasses implement ``run`` with their own signature; the base class
provides shared helpers (LLM access, prompt loading, logging).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.contracts import schema_for_call
from src.services.llm_client import LLMClient
from src.services.prompt_loader import load_prompt


class BaseAgent(ABC):
    """Minimal contract every agent satisfies."""

    name: str = "BaseAgent"
    prompt_name: str = ""
    response_schema_name: str = ""

    def __init__(self, llm: Optional[LLMClient] = None) -> None:
        self._llm = llm or LLMClient()
        self._logger = logging.getLogger(f"agent.{self.name}")

    def _load_prompt(self, **kwargs: str) -> str:
        if not self.prompt_name:
            raise NotImplementedError(f"{self.name} has no prompt_name configured")
        return load_prompt(self.prompt_name, **kwargs)

    def _call_llm_text(self, prompt: str) -> str:
        return self._llm.generate_text(
            prompt,
            agent_name=self.name,
            prompt_name=self.prompt_name,
        )

    def _call_llm_json(self, prompt: str) -> Dict[str, Any]:
        if not self.response_schema_name:
            raise NotImplementedError(f"{self.name} has no response schema")
        result = self._llm.generate_structured(
            prompt,
            schema=schema_for_call(self.response_schema_name),
            agent_name=self.name,
            prompt_name=self.prompt_name,
        )
        return result.data
