"""Analyze actual specialist routing recorded in POMA traces."""

from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


def analyze_parallelism(
    traces: Iterable[Mapping[str, Any]],
    *,
    expected_qa_ids: Sequence[str] | None = None,
) -> dict[str, object]:
    """Summarize specialists per QA with strict trace coverage validation."""
    trace_by_id: dict[str, Mapping[str, Any]] = {}
    for trace in traces:
        if not isinstance(trace, Mapping) or trace.get("qa_id") is None:
            raise ValueError("Every POMA trace must contain qa_id")
        qa_id = str(trace["qa_id"])
        if qa_id in trace_by_id:
            raise ValueError(f"Duplicate trace qa_id: {qa_id!r}")
        trace_by_id[qa_id] = trace

    qa_ids = (
        [str(qa_id) for qa_id in expected_qa_ids]
        if expected_qa_ids is not None
        else list(trace_by_id)
    )
    if len(qa_ids) != len(set(qa_ids)):
        raise ValueError("Expected QA IDs must be unique")
    missing = [qa_id for qa_id in qa_ids if qa_id not in trace_by_id]
    extras = sorted(set(trace_by_id).difference(qa_ids))
    if missing:
        raise ValueError(f"Missing trace IDs: {missing}")
    if extras:
        raise ValueError(f"Unexpected trace IDs: {extras}")

    counts: list[int] = []
    for qa_id in qa_ids:
        trace = trace_by_id[qa_id]
        try:
            specialist_names = trace["steps"]["2_router"]["specialist_names"]
        except (KeyError, TypeError):
            specialist_names = None
        if (
            not isinstance(specialist_names, list)
            or not specialist_names
            or any(
                not isinstance(name, str) or not name.strip()
                for name in specialist_names
            )
        ):
            raise ValueError(
                f"Trace qa_id={qa_id!r} requires a non-empty "
                "steps.2_router.specialist_names list"
            )
        counts.append(len(specialist_names))

    count = len(counts)
    distribution = {
        str(value): frequency
        for value, frequency in sorted(Counter(counts).items())
    }
    return {
        "count": count,
        "distribution": distribution,
        "mean": sum(counts) / count if count else 0.0,
        "median": statistics.median(counts) if count else 0.0,
        "maximum": max(counts) if count else 0,
        "multi_specialist_rate": (
            sum(value > 1 for value in counts) / count if count else 0.0
        ),
    }


__all__ = ["analyze_parallelism"]
