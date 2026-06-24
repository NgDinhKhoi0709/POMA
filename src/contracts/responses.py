"""Response data-classes shared across all agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RefinedQuery:
    normalized_question: str
    hints: List[str]
    target: Optional[str] = None
    constraints: List[str] = field(default_factory=list)


@dataclass
class EvidenceItem:
    text: str
    row_index: Optional[int] = None
    col: Optional[str] = None


@dataclass
class SpecialistResult:
    agent_name: str
    answer: Optional[str] = None
    evidence: List[EvidenceItem] = field(default_factory=list)
    confidence: float = 0.0
    reason: Optional[str] = None
