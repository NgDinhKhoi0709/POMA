"""Pipeline trace dataclass for structured step-by-step output logging."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PipelineTrace:
    """Accumulates outputs from every pipeline step for debugging/analysis."""

    question_refiner: Optional[Dict[str, Any]] = None
    router: Optional[Dict[str, Any]] = None
    specialists: List[Dict[str, Any]] = field(default_factory=list)
    answer_normalization: Optional[Dict[str, Any]] = None
    llm_calls: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        steps: Dict[str, Any] = {}

        if self.question_refiner is not None:
            steps["1_question_refiner"] = self.question_refiner

        if self.router is not None:
            steps["2_router"] = self.router

        if self.specialists:
            steps["3_specialists"] = self.specialists

        if self.answer_normalization is not None:
            steps["4_answer_normalization"] = self.answer_normalization

        payload: Dict[str, Any] = {"steps": steps}
        if self.llm_calls:
            payload["llm_calls"] = self.llm_calls
        if self.error is not None:
            payload["error"] = self.error

        return payload

    @staticmethod
    def serialize_evidence(evidence_list) -> List[Dict[str, Any]]:
        """Convert a list of EvidenceItem dataclasses to plain dicts."""
        items = []
        for e in evidence_list:
            d: Dict[str, Any] = {"text": e.text}
            if e.row_index is not None:
                d["row_index"] = e.row_index
            if e.col is not None:
                d["col"] = e.col
            items.append(d)
        return items
