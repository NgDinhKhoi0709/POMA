"""Inbound request data-class."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class QARequest:
    question: str
    table_flattened: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def hints(self) -> List[str]:
        return self.metadata.get("hints", [])
