"""Deterministic stratified QA selection for the Kaggle pilot."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


def table_length_bucket(token_count: int) -> str:
    if token_count < 1000:
        return "short"
    if token_count < 4000:
        return "medium"
    return "long"


def select_pilot_qas(
    qas: Sequence[dict[str, Any]],
    *,
    table_token_counts: Mapping[str, int],
    n: int = 200,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Select a seeded sample proportional to hint and table-length strata."""
    if len(qas) < n:
        raise ValueError(f"Need at least {n} QAs, received {len(qas)}")
    groups: dict[tuple[str, str], list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for index, qa in enumerate(qas):
        hints = qa.get("hints") or ["unknown"]
        hint = str(hints[0]) if hints else "unknown"
        bucket = table_length_bucket(int(table_token_counts.get(str(qa.get("table_id", "")), 0)))
        groups[(hint, bucket)].append((index, qa))
    rng = random.Random(seed)
    total = len(qas)
    quotas: dict[tuple[str, str], int] = {}
    remainders: list[tuple[float, tuple[str, str]]] = []
    for key, items in groups.items():
        exact = len(items) * n / total
        quotas[key] = int(exact)
        remainders.append((exact - quotas[key], key))

    for _, key in sorted(remainders, key=lambda item: (-item[0], item[1]))[: n - sum(quotas.values())]:
        quotas[key] += 1

    selected: list[tuple[int, dict[str, Any]]] = []
    for key in sorted(groups):
        items = groups[key]
        selected.extend(rng.sample(items, quotas[key]))
    return [qa for _, qa in sorted(selected, key=lambda item: item[0])]


def select_longest_table_qa(
    qas: Sequence[dict[str, Any]],
    *,
    table_char_counts: Mapping[str, int],
) -> dict[str, Any]:
    """Select a deterministic stress QA from the longest referenced table."""
    if not qas:
        raise ValueError("Cannot select a longest-table QA from an empty dataset")

    referenced = {
        str(qa.get("table_id", ""))
        for qa in qas
        if str(qa.get("table_id", "")) in table_char_counts
    }
    if not referenced:
        raise ValueError("No QA references a table with a measured character count")

    longest_table_id = max(
        referenced,
        key=lambda table_id: (table_char_counts[table_id], table_id),
    )
    candidates = [
        qa for qa in qas if str(qa.get("table_id", "")) == longest_table_id
    ]
    return max(
        candidates,
        key=lambda qa: (len(str(qa.get("question", ""))), str(qa.get("qa_id", ""))),
    )


def load_final_543_ids(path: Path | None = None) -> list[str]:
    candidate = path or Path("outputs/q2_revision/openrouter_google_gemma-3-4b-it/full/reports/poma_vs_zero_shot_543.json")
    if not candidate.exists():
        raise FileNotFoundError(f"Final 543 QA IDs not found at {candidate}; pass FINAL_IDS_PATH explicitly.")
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    values = payload.get("qa_ids", []) if isinstance(payload, dict) else payload
    if not isinstance(values, list):
        raise ValueError(f"Expected a JSON list of QA IDs in {candidate}")
    return [str(value) for value in values]
