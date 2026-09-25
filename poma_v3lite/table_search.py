"""Stage 3 "Search Table" step: find table rows that mention the evidence an LLM asked for.

No LLM call. Given the cell texts or entity names named by ``IdentifyMissingEvidence``, return the
rows of the Flatten V1 grid that contain them, plus the header rows, so the re-answer step sees the
region of the table the first attempt may have missed.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from preprocessing.variants import Grid

_WORD = re.compile(r"\w+", re.UNICODE)


def _fold(text: str) -> str:
    """Lowercase and strip diacritics so ``Hà Nội`` matches ``ha noi``."""
    value = unicodedata.normalize("NFD", str(text).lower())
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return value.replace("đ", "d")


def _terms(text: str) -> list[str]:
    return [token for token in _WORD.findall(_fold(text)) if len(token) > 1]


def search_rows(table_data: dict[str, Any], queries: list[str], *, max_rows: int = 12) -> list[int]:
    """Body-row indices whose text covers a query, best-covering first then in table order."""
    grid = Grid.from_table_data(table_data).cleaned()
    scored: list[tuple[float, int]] = []
    for index, row in enumerate(grid.rows):
        if index < grid.n_head:
            continue
        row_text = _fold(" | ".join(row))
        best = 0.0
        for query in queries:
            terms = _terms(query)
            if not terms:
                continue
            phrase = _fold(query).strip()
            if phrase and phrase in row_text:
                best = max(best, 1.0)
                continue
            covered = sum(1 for term in terms if term in row_text)
            best = max(best, covered / len(terms))
        if best > 0:
            scored.append((best, index))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return sorted(index for _, index in scored[:max_rows])


def render_rows(table_data: dict[str, Any], indices: list[int]) -> str:
    """Render header rows plus the given body rows in original order, Flatten V1 style."""
    grid = Grid.from_table_data(table_data).cleaned()
    keep = set(indices)
    lines: list[str] = []
    for index, row in enumerate(grid.rows):
        if index < grid.n_head:
            lines.append(" | ".join(f"{cell} <header>" for cell in row))
        elif index in keep:
            lines.append(" | ".join(row))
    return "\n".join(lines)
