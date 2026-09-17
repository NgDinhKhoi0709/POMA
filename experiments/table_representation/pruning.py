"""Query-aware table shrink for cheaper LLM prompts.

Keep headers plus the rows and columns that overlap the question. No extra
LLM call: scoring is lexical (TaBERT content-snapshot / TAP4LLM). Count and
aggregation questions skip row pruning so totals still see the full set.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from preprocessing.representation import FlattenedTable

PRUNE_METHODS: Tuple[str, ...] = (
    "identity",
    "clean_only",
    "even_sample",
    "lexical_rows",
    "lexical_cols",
    "lexical_subtable",
)

# Letters and digits as whole words (NFC). ASCII-first patterns split
# Vietnamese at the first diacritic (hạng → ạng) and create false overlap.
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_CITE_RE = re.compile(r"\[\s*\d+\s*\]")
_SPACE_RE = re.compile(r"\s+")

_STOPWORDS = {
    "của", "và", "các", "là", "trong", "với", "một", "được", "cho", "này",
    "có", "không", "năm", "bao", "nhiêu", "gì", "nào", "ai", "ở", "tại",
    "the", "of", "and", "a", "an", "in", "on", "to", "for", "is", "was",
    "by", "with", "from", "that", "this", "be",
}

_AGG_HINTS = (
    "tổng",
    "trung bình",
    "nhiều nhất",
    "ít nhất",
    "lớn nhất",
    "nhỏ nhất",
    "so sánh",
    "tất cả",
    "danh sách",
    "bao nhiêu",
    "how many",
    "average",
    "sum of",
)


@dataclass(frozen=True)
class PrunedTable:
    """A question-conditioned sub-table plus size stats."""

    method: str
    table_id: str
    question: str
    text: str
    kept_row_indices: Tuple[int, ...]
    kept_col_indices: Tuple[int, ...]
    n_rows_before: int
    n_cols_before: int
    n_rows_after: int
    n_cols_after: int
    n_chars_before: int
    n_chars_after: int
    skipped_row_prune: bool

    @property
    def cell_keep_ratio(self) -> float:
        before = max(1, self.n_rows_before * self.n_cols_before)
        after = self.n_rows_after * self.n_cols_after
        return after / before

    @property
    def char_save_ratio(self) -> float:
        if self.n_chars_before <= 0:
            return 0.0
        return 1.0 - (self.n_chars_after / self.n_chars_before)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "table_id": self.table_id,
            "question": self.question,
            "text": self.text,
            "kept_row_indices": list(self.kept_row_indices),
            "kept_col_indices": list(self.kept_col_indices),
            "n_rows_before": self.n_rows_before,
            "n_cols_before": self.n_cols_before,
            "n_rows_after": self.n_rows_after,
            "n_cols_after": self.n_cols_after,
            "n_chars_before": self.n_chars_before,
            "n_chars_after": self.n_chars_after,
            "cell_keep_ratio": round(self.cell_keep_ratio, 4),
            "char_save_ratio": round(self.char_save_ratio, 4),
            "skipped_row_prune": self.skipped_row_prune,
        }


def prune_table(
    table_data: Dict[str, Any],
    question: str,
    method: str = "lexical_subtable",
    *,
    max_rows: int = 8,
    max_cols: int = 6,
) -> PrunedTable:
    """Shrink one table to question-relevant rows and columns."""
    if method not in PRUNE_METHODS:
        raise ValueError(f"Unknown prune method {method!r}. Choose one of: {', '.join(PRUNE_METHODS)}")
    if max_rows < 1 or max_cols < 1:
        raise ValueError("max_rows and max_cols must be at least 1")

    flattened = FlattenedTable.from_table_data(table_data)
    rows = [[_clean_cell(cell) for cell in row] for row in FlattenedTable._normalize_rows(flattened.rows)]
    mask = FlattenedTable._normalize_header_mask(flattened.header_mask, rows)

    n_rows = len(rows)
    n_cols = max((len(row) for row in rows), default=0)
    header_count, body_start = _header_row_count(mask)
    q_tokens = tokenize(question)
    skip_rows = _is_aggregation_question(question)
    full_text = _grid_text(flattened, rows, mask)

    if method == "identity":
        kept_rows = list(range(n_rows))
        kept_cols = list(range(n_cols))
    elif method == "clean_only":
        kept_rows, kept_cols = _drop_empty(rows, mask)
    elif method == "even_sample":
        kept_cols = list(range(n_cols))
        body = list(range(body_start, n_rows))
        kept_body = _even_sample(body, max_rows)
        kept_rows = list(range(header_count)) + kept_body
    elif method == "lexical_rows":
        kept_cols = list(range(n_cols))
        kept_rows = _select_rows(rows, mask, q_tokens, max_rows, skip_rows)
    elif method == "lexical_cols":
        kept_rows = list(range(n_rows))
        kept_cols = _select_cols(rows, mask, q_tokens, max_cols)
    else:
        kept_cols = _select_cols(rows, mask, q_tokens, max_cols)
        kept_rows = _select_rows(rows, mask, q_tokens, max_rows, skip_rows, col_indices=kept_cols)

    kept_rows, kept_cols = _unique_sorted(kept_rows), _unique_sorted(kept_cols)
    sub_rows = [_take_cols(rows[i], kept_cols) for i in kept_rows]
    sub_mask = [_take_cols(mask[i], kept_cols) for i in kept_rows]
    text = _grid_text(flattened, sub_rows, sub_mask)

    return PrunedTable(
        method=method,
        table_id=str(flattened.table_id or table_data.get("table_id") or ""),
        question=question,
        text=text,
        kept_row_indices=tuple(kept_rows),
        kept_col_indices=tuple(kept_cols),
        n_rows_before=n_rows,
        n_cols_before=n_cols,
        n_rows_after=len(sub_rows),
        n_cols_after=len(kept_cols),
        n_chars_before=len(full_text),
        n_chars_after=len(text),
        skipped_row_prune=skip_rows and method in {"lexical_rows", "lexical_subtable"},
    )


def prune_all(
    table_data: Dict[str, Any],
    question: str,
    methods: Optional[Sequence[str]] = None,
    **kwargs: Any,
) -> List[PrunedTable]:
    selected = list(methods) if methods is not None else list(PRUNE_METHODS)
    return [prune_table(table_data, question, method, **kwargs) for method in selected]


def tokenize(text: str) -> Set[str]:
    """Lowercased alphanumeric tokens, minus a small Vietnamese/English stoplist."""
    normalized = unicodedata.normalize("NFC", text or "")
    tokens = {match.group(0).lower() for match in _TOKEN_RE.finditer(normalized)}
    return {token for token in tokens if token not in _STOPWORDS and (token.isdigit() or len(token) >= 2)}


def _with_title(title: str, body: str) -> str:
    title = (title or "").strip()
    if not title:
        return body
    if not body:
        return f"TITLE: {title}"
    return f"TITLE: {title}\n{body}"


def _grid_text(
    flattened: FlattenedTable,
    rows: Sequence[Sequence[str]],
    mask: Sequence[Sequence[bool]],
) -> str:
    body = FlattenedTable(
        table_id=flattened.table_id,
        title=flattened.title,
        domain=flattened.domain,
        rows=[list(row) for row in rows],
        header_mask=[list(flags) for flags in mask],
    ).to_string()
    return _with_title(flattened.title, body)


def _clean_cell(value: str) -> str:
    text = _CITE_RE.sub(" ", str(value or ""))
    return _SPACE_RE.sub(" ", text).strip()


def _header_row_count(mask: Sequence[Sequence[bool]]) -> Tuple[int, int]:
    count = 0
    for row in mask:
        if row and sum(1 for flag in row if flag) > len(row) // 2:
            count += 1
        else:
            break
    return count, count


def _is_aggregation_question(question: str) -> bool:
    lowered = (question or "").lower()
    return any(hint in lowered for hint in _AGG_HINTS)


def _overlap(tokens_a: Set[str], tokens_b: Set[str]) -> int:
    return len(tokens_a & tokens_b)


def _row_tokens(row: Sequence[str], col_indices: Optional[Sequence[int]] = None) -> Set[str]:
    if col_indices is None:
        cells: Iterable[str] = row
    else:
        cells = (row[i] for i in col_indices if i < len(row))
    tokens: Set[str] = set()
    for cell in cells:
        tokens |= tokenize(cell)
    return tokens


def _column_leaves(rows: Sequence[Sequence[str]], mask: Sequence[Sequence[bool]], n_cols: int) -> List[str]:
    """Last non-empty header cell per column (the unique leaf name)."""
    header_count, _ = _header_row_count(mask)
    leaves: List[str] = []
    for col in range(n_cols):
        leaf = ""
        for row in rows[:header_count]:
            value = str(row[col] if col < len(row) else "").strip()
            if value:
                leaf = value
        leaves.append(leaf or f"col_{col + 1}")
    return leaves


def _select_cols(
    rows: Sequence[Sequence[str]],
    mask: Sequence[Sequence[bool]],
    q_tokens: Set[str],
    max_cols: int,
) -> List[int]:
    n_cols = max((len(row) for row in rows), default=0)
    if n_cols == 0:
        return []
    leaves = _column_leaves(rows, mask, n_cols)
    scored: List[Tuple[int, int, int]] = []
    for col in range(n_cols):
        # Parent/merged headers are shared across siblings; only the leaf
        # name and cell values are discriminative (TAP4LLM column grounding).
        leaf_score = _overlap(tokenize(leaves[col]), q_tokens)
        value_score = 0
        for row, flags in zip(rows, mask):
            if col >= len(row):
                continue
            if col < len(flags) and flags[col]:
                continue
            value_score = max(value_score, _overlap(tokenize(row[col]), q_tokens))
        scored.append((leaf_score + value_score, leaf_score, col))
    scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
    kept = [0] if n_cols else []
    for total, _, col in scored:
        if col not in kept and (total > 0 or len(kept) < 2):
            kept.append(col)
        if len(kept) >= max_cols:
            break
    if len(kept) < min(2, n_cols):
        for col in range(n_cols):
            if col not in kept:
                kept.append(col)
            if len(kept) >= min(2, n_cols):
                break
    return kept


def _select_rows(
    rows: Sequence[Sequence[str]],
    mask: Sequence[Sequence[bool]],
    q_tokens: Set[str],
    max_rows: int,
    skip_row_prune: bool,
    col_indices: Optional[Sequence[int]] = None,
) -> List[int]:
    header_count, body_start = _header_row_count(mask)
    header_rows = list(range(header_count))
    body = list(range(body_start, len(rows)))
    if skip_row_prune or not body:
        return header_rows + body
    ranked = sorted(
        body,
        key=lambda idx: (
            -_overlap(_row_tokens(rows[idx], col_indices), q_tokens),
            idx,
        ),
    )
    positive = [idx for idx in ranked if _overlap(_row_tokens(rows[idx], col_indices), q_tokens) > 0]
    chosen = (positive or ranked)[:max_rows]
    return header_rows + sorted(chosen)


def _even_sample(indices: Sequence[int], limit: int) -> List[int]:
    if len(indices) <= limit:
        return list(indices)
    order: List[int] = []
    for offset in range(len(indices)):
        for probe in (offset, len(indices) // 2 + offset, len(indices) - 1 - offset):
            if 0 <= probe < len(indices) and indices[probe] not in order:
                order.append(indices[probe])
        if len(order) >= limit:
            break
    return sorted(order[:limit])


def _drop_empty(
    rows: Sequence[Sequence[str]],
    mask: Sequence[Sequence[bool]],
) -> Tuple[List[int], List[int]]:
    n_cols = max((len(row) for row in rows), default=0)
    kept_cols = [
        col
        for col in range(n_cols)
        if any(str(row[col]).strip() for row in rows if col < len(row))
    ]
    kept_rows = [
        idx
        for idx, row in enumerate(rows)
        if any(str(row[col]).strip() for col in kept_cols if col < len(row))
        or (idx < len(mask) and any(mask[idx]))
    ]
    if not kept_rows:
        kept_rows = list(range(len(rows)))
    if not kept_cols:
        kept_cols = list(range(n_cols))
    return kept_rows, kept_cols


def _take_cols(row: Sequence[Any], cols: Sequence[int]) -> List[Any]:
    filler: Any = False if row and isinstance(row[0], bool) else ""
    return [row[i] if i < len(row) else filler for i in cols]


def _unique_sorted(values: Iterable[int]) -> List[int]:
    return sorted(dict.fromkeys(int(value) for value in values))
