"""D10 / H1: question-aware row selection for long tables, with conservative fallbacks.

The goal is fewer input tokens. Rows are chosen with plain lexical scoring (no LLM call), kept in their
original order under the untouched header rows, and rendered in Flatten V1. Because Flatten V1 repeats
merged-cell values into every row, a kept row never loses its span labels. The table is returned in full
whenever the question or the table makes row selection risky: short tables, cues that the answer needs
many rows (counting, comparison, superlatives, lists), no lexical overlap, or a negligible saving.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Callable, List, Sequence

from .variants import ARMS, Grid, render_table, render_v1

MIN_TABLE_TOKENS = 2000
KEEP_RATIO_LIMIT = 0.8

# Frozen before any run: a question matching any cue needs whole-column or multi-row reasoning.
AGGREGATION_CUES = re.compile("|".join([
    r"bao nhiêu", r"\bmấy\b", r"tổng", r"trung bình", r"số lượng", r"\bđếm\b", r"liệt kê", r"sắp xếp", r"xếp theo",
    r"thứ tự", r"\bnhất\b", r"\bhơn\b", r"\bkém\b", r"so với", r"chênh lệch", r"\bcùng\b", r"giống", r"khác nhau",
    r"tất cả", r"toàn bộ", r"\bmỗi\b", r"\bnhững\b", r"\bcác\b", r"đầu tiên", r"cuối cùng", r"\btăng\b", r"\bgiảm\b",
]))


@dataclass(frozen=True)
class Reduction:
    text: str
    reduced: bool
    reason: str  # short_table | aggregation_cue | no_lexical_signal | few_rows | reduced
    rows_total: int
    rows_kept: int


def _norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", str(text)).lower().split())


def _words(text: str) -> List[str]:
    return re.findall(r"\w+", _norm(text))


def _terms(text: str) -> List[str]:
    words = _words(text)
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]


def bm25_scores(docs: Sequence[Sequence[str]], query: Sequence[str], k1: float = 1.5, b: float = 0.75) -> List[float]:
    n = len(docs)
    avg = sum(len(d) for d in docs) / max(1, n)
    df = Counter(t for d in docs for t in set(d))
    idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
    scores = []
    for doc in docs:
        tf = Counter(doc)
        total = 0.0
        for term in set(query):
            if term in tf:
                total += idf[term] * tf[term] * (k1 + 1) / (tf[term] + k1 * (1 - b + b * len(doc) / avg))
        scores.append(total)
    return scores


def _rank(body: Sequence[Sequence[str]], question: str) -> tuple[List[int], List[float], List[int]]:
    """(rows by descending BM25, BM25 scores, rows in that order holding a cell named in the question)."""
    scores = bm25_scores([_terms(" ".join(row)) for row in body], _terms(question))
    order = sorted(range(len(body)), key=lambda i: (-scores[i], i))
    padded = f" {' '.join(_words(question))} "
    named = [
        i for i in order
        if any(len(_norm(c)) >= 2 and _words(c) and f" {' '.join(_words(c))} " in padded for c in body[i])
    ]
    return order, scores, named


def select_rows(body: Sequence[Sequence[str]], question: str, k: int) -> List[int]:
    """Indices (ascending) of the top-``k`` BM25 rows plus up to ``k`` rows holding a cell named in the question."""
    order, _, named = _rank(body, question)
    return sorted(set(order[:k]) | set(named[:k]))


def reduce_table(
    table_data: dict,
    question: str,
    *,
    k: int,
    token_count: Callable[[str], int],
    min_tokens: int = MIN_TABLE_TOKENS,
    arm: str = "v1_raw",
) -> Reduction:
    """Table text for ``question`` under ``arm``: reduced when safe, otherwise identical to ``render_table``.

    ``arm`` picks the serializer and whether the grid is cleaned first, exactly as in ``variants.ARMS``. The
    2000-token gate is measured on the string that would actually be sent, so a compact serializer is gated
    on its own size rather than on Flatten V1's. With the default ``v1_raw`` the behaviour is D10's.
    """
    render, clean = ARMS[arm]
    grid = Grid.from_table_data(table_data)
    if clean:
        grid = grid.cleaned()
    full = render_table(table_data, arm)
    body = list(grid.rows[grid.n_head:])
    total = len(body)

    def keep_full(reason: str) -> Reduction:
        return Reduction(full, False, reason, total, total)

    if token_count(full) <= min_tokens:
        return keep_full("short_table")
    if AGGREGATION_CUES.search(_norm(question)):
        return keep_full("aggregation_cue")
    order, scores, named = _rank(body, question)
    if not body or (max(scores) == 0.0 and not named):
        return keep_full("no_lexical_signal")
    kept = sorted(set(order[:k]) | set(named[:k]))
    if len(kept) >= KEEP_RATIO_LIMIT * total:
        return keep_full("few_rows")
    rows = grid.rows[: grid.n_head] + tuple(body[i] for i in kept)
    mask = grid.header_mask[: grid.n_head] + tuple(grid.header_mask[grid.n_head + i] for i in kept)
    rendered = render(Grid(rows, mask, grid.n_head))
    text = rendered if rendered.strip() else render_v1(grid)
    note = f"[Ghi chú: bảng gốc có {total} hàng dữ liệu; chỉ hiển thị {len(kept)} hàng liên quan đến câu hỏi.]"
    return Reduction(f"{text}\n{note}", True, "reduced", total, len(kept))
