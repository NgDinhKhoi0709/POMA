"""Bounded table context for the hint-prediction stage."""

from __future__ import annotations

from typing import Protocol


class TokenCounter(Protocol):
    def encode(self, text: str) -> list[int] | list[str]:
        """Return tokens for ``text``."""


def _token_count(text: str, tokenizer: TokenCounter | None) -> int:
    return len(tokenizer.encode(text)) if tokenizer is not None else len(text.split())


def build_table_preview(
    table_flattened: str,
    *,
    tokenizer: TokenCounter | None = None,
    max_tokens: int = 1024,
) -> str:
    """Keep a deterministic, whole-line preview within ``max_tokens``.

    The preview prioritises title/header-like leading lines, then samples rows
    from the beginning, middle, and end.  It is only for HintPredictor;
    answer-producing stages continue to receive the complete table.
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if _token_count(table_flattened, tokenizer) <= max_tokens:
        return table_flattened

    lines = [line for line in table_flattened.splitlines() if line.strip()]
    if not lines:
        return table_flattened

    header_count = min(2, len(lines))
    prefix: list[str] = []
    for line in lines[:header_count]:
        candidate = "\n".join(prefix + [line])
        if _token_count(candidate, tokenizer) <= max_tokens:
            prefix.append(line)
        else:
            break

    marker = "[OMITTED_ROWS: rows not shown between sampled sections]"
    if len(prefix) < header_count:
        truncated = "[PREVIEW_TRUNCATED_BEFORE_ROWS]"
        candidate = "\n".join(prefix + [truncated])
        return candidate if _token_count(candidate, tokenizer) <= max_tokens else "\n".join(prefix)

    rows = lines[header_count:]
    if not rows:
        return "\n".join(prefix)

    order: list[int] = []
    for offset in range(len(rows)):
        for index in (offset, len(rows) // 2 + offset, len(rows) - 1 - offset):
            if 0 <= index < len(rows) and index not in order:
                order.append(index)

    selected: list[int] = []
    for index in order:
        candidate_rows = sorted(selected + [index])
        candidate = "\n".join(prefix + [rows[item] for item in candidate_rows] + [marker])
        if _token_count(candidate, tokenizer) <= max_tokens:
            selected.append(index)

    omitted = max(0, len(rows) - len(selected))
    marker = f"[OMITTED_ROWS: {omitted} rows not shown between sampled sections]"
    preview_lines = prefix + [rows[item] for item in sorted(selected)]
    if omitted:
        preview_lines.append(marker)
    return "\n".join(preview_lines)
