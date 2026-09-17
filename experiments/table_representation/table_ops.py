"""Deterministic table operators for questions an 8B model routinely misses.

These are question-gated tools over the parsed grid, not extra EM candidates.
They fire only on frequency-rank, list, climate-extremum, and filtered min/max
lookups. Yes/No, why, and count questions stay with the LLM.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from preprocessing.representation import FlattenedTable

_NUMBER_RE = re.compile(r"^[-+]?\d[\d.,]*%?$")
_TOKEN_RE = re.compile(r"[0-9]+(?:[.,][0-9]+)+|[^\W_]+", re.UNICODE)
_ORDINALS = {
    "nhất": 1,
    "1": 1,
    "hai": 2,
    "2": 2,
    "ba": 3,
    "3": 3,
    "tư": 4,
    "4": 4,
}
_FREQ_RANK_RE = re.compile(
    r"(?:nhiều|phổ biến|sử dụng nhiều)\s+thứ\s+(\d+|nhất|hai|ba|tư)",
    re.IGNORECASE,
)
_EXTREMUM_RE = re.compile(
    r"(thấp|cao|ít|nhỏ|lớn|nhiều)\s+(?:\S+\s+){0,3}nhất",
    re.IGNORECASE,
)
_WHY_RE = re.compile(r"\b(tại sao|vì sao|vì thế nào)\b", re.IGNORECASE)
_COUNT_RE = re.compile(r"bao nhiêu", re.IGNORECASE)
_LIST_RE = re.compile(r"liệt kê", re.IGNORECASE)
_STOPWORDS = {
    "của", "và", "các", "là", "trong", "với", "một", "được", "cho", "này",
    "có", "không", "năm", "bao", "nhiêu", "gì", "nào", "ai", "ở", "tại",
    "người", "thuộc", "đến", "từ", "mà", "the", "of", "and", "a", "an",
}


@dataclass(frozen=True)
class TableOpResult:
    op: str
    value: str


def table_op_answer(table: Dict[str, Any], question: str) -> Optional[TableOpResult]:
    """Return a tool answer when the question matches a supported operator."""
    q = _nfc(question)
    if not q or _WHY_RE.search(q) or _COUNT_RE.search(q) or _is_yesno(q):
        return None

    flattened = FlattenedTable.from_table_data(table)
    rows = FlattenedTable._normalize_rows(flattened.rows)
    mask = FlattenedTable._normalize_header_mask(flattened.header_mask, rows)
    if not rows:
        return None
    body_start = _body_start(mask)
    header_rows = rows[:body_start] or [rows[0]]
    body_rows = rows[body_start:] if body_start < len(rows) else rows[1:]
    headers = _column_headers(header_rows, len(rows[0]))

    rank = parse_frequency_rank(q)
    if rank is not None:
        value = _frequency_rank_value(rows, mask, rank)
        if value:
            return TableOpResult("frequency_rank", value)

    if _LIST_RE.search(q):
        value = _list_rows(headers, body_rows, q)
        if value:
            return TableOpResult("list_rows", value)

    month_row = _month_header_row(rows)
    if month_row is not None and _climate_question(q):
        value = _climate_extremum(rows, month_row, q)
        if value:
            return TableOpResult("climate_extremum", value)

    if month_row is not None:
        return None

    if _EXTREMUM_RE.search(q):
        value = _filtered_extremum(headers, body_rows, q)
        if value:
            return TableOpResult("filtered_extremum", value)
    return None


def parse_frequency_rank(question: str) -> Optional[int]:
    q = _nfc(question)
    match = _FREQ_RANK_RE.search(q)
    if not match:
        return None
    token = match.group(1).lower()
    if token in _ORDINALS:
        return _ORDINALS[token]
    if token.isdigit():
        return int(token)
    return None


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").strip()


def _lower(text: str) -> str:
    return _nfc(text).lower()


def _is_yesno(question: str) -> bool:
    q = _lower(question)
    return bool(
        "có phải" in q
        or "phải không" in q
        or "đúng không" in q
        or q.endswith("không?")
        or " không?" in q
    )


def _climate_question(question: str) -> bool:
    q = _lower(question)
    if " và " in q:
        return False
    if not _EXTREMUM_RE.search(q):
        return False
    return "khi nào" in q or "tháng nào" in q


def _body_start(mask: Sequence[Sequence[bool]]) -> int:
    if not mask:
        return 0
    count = 0
    for row in mask:
        if row and sum(1 for flag in row if flag) >= max(1, len(row) // 2):
            count += 1
            continue
        break
    return count if count else 1


def _column_headers(header_rows: Sequence[Sequence[str]], n_cols: int) -> List[str]:
    names = [""] * n_cols
    for row in header_rows:
        for j, cell in enumerate(row[:n_cols]):
            text = str(cell or "").strip()
            if text and not names[j]:
                names[j] = text
            elif text and text not in names[j]:
                names[j] = text
    return names


def _is_numeric(text: str) -> bool:
    return bool(_NUMBER_RE.match(str(text or "").strip()))


def _parse_number(text: str) -> Optional[float]:
    raw = str(text or "").strip()
    if not raw:
        return None
    raw = raw.split("(")[0].strip().rstrip("%")
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", raw):
        raw = raw.replace(".", "").replace(",", ".")
    elif raw.count(",") == 1 and raw.count(".") == 0:
        raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def _frequency_rank_value(
    rows: Sequence[Sequence[str]],
    mask: Sequence[Sequence[bool]],
    rank: int,
) -> Optional[str]:
    counts: Dict[str, int] = {}
    order: List[str] = []
    for i, row in enumerate(rows):
        flags = mask[i] if i < len(mask) else []
        for j, cell in enumerate(row):
            if j < len(flags) and flags[j]:
                continue
            text = str(cell or "").strip()
            if not text or _is_numeric(text):
                continue
            if text not in counts:
                order.append(text)
                counts[text] = 0
            counts[text] += 1
    ranked = sorted(order, key=lambda value: (-counts[value], order.index(value)))
    if 1 <= rank <= len(ranked):
        return ranked[rank - 1]
    return None


def _cell_values_in_question(question: str, cells: Iterable[str]) -> List[str]:
    q = _lower(question)
    found: List[str] = []
    seen = set()
    for cell in cells:
        text = str(cell or "").strip()
        key = _lower(text)
        if len(key) < 3 or key in seen:
            continue
        if key in q:
            seen.add(key)
            found.append(text)
    return found


def _row_has_values(row: Sequence[str], required: Sequence[str]) -> bool:
    blob = " | ".join(_lower(str(cell or "")) for cell in row)
    return all(_lower(item) in blob for item in required)


def _header_overlap(question: str, header: str) -> int:
    q_tokens = {tok.lower() for tok in _TOKEN_RE.findall(_lower(question))}
    h_tokens = {tok.lower() for tok in _TOKEN_RE.findall(_lower(header))}
    q_tokens -= _STOPWORDS
    h_tokens -= _STOPWORDS
    return len(q_tokens & h_tokens)


_LIST_TARGET_BONUS = ("ca sĩ", "hạng mục", "tên", "người", "cầu thủ", "tòa nhà")
_LIST_TARGET_PENALTY = ("ngày", "date", "kết quả", "năm", "chú thích", "host")


def _pick_target_column(
    headers: Sequence[str],
    question: str,
    *,
    list_mode: bool = False,
) -> Optional[int]:
    scored: List[Tuple[int, int, int]] = []
    q = _lower(question)
    for idx, header in enumerate(headers):
        if not str(header or "").strip():
            continue
        overlap = _header_overlap(question, header)
        header_l = _lower(header)
        if list_mode:
            overlap += sum(4 for token in _LIST_TARGET_BONUS if token in header_l and (token in q or token == "tên"))
            overlap -= sum(3 for token in _LIST_TARGET_PENALTY if token in header_l)
            if "tên" in q and any(token in header_l for token in ("ca sĩ", "tên", "người")):
                overlap += 3
        if overlap <= 0:
            continue
        scored.append((overlap, -idx, idx))
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][2]


def _list_rows(
    headers: Sequence[str],
    body_rows: Sequence[Sequence[str]],
    question: str,
) -> Optional[str]:
    target = _pick_target_column(headers, question, list_mode=True)
    if target is None:
        # leftmost mostly-text column
        for idx, header in enumerate(headers):
            if header and not _is_numeric(header):
                target = idx
                break
    if target is None:
        return None
    cells = list(headers) + [cell for row in body_rows for cell in row]
    header_keys = {_lower(header) for header in headers}
    required = [
        value
        for value in _cell_values_in_question(question, cells)
        if _lower(value) not in header_keys
    ]
    years = re.findall(r"(?:19|20)\d{2}", question)
    values: List[str] = []
    seen = set()
    for row in body_rows:
        if required and not _row_has_values(row, required):
            continue
        if years and not any(year in " ".join(str(cell) for cell in row) for year in years):
            continue
        if target >= len(row):
            continue
        text = str(row[target] or "").strip()
        key = _lower(text)
        if not text or key in seen:
            continue
        seen.add(key)
        values.append(text)
    if not values:
        return None
    return ", ".join(values)


def _month_header_row(rows: Sequence[Sequence[str]]) -> Optional[int]:
    for idx, row in enumerate(rows):
        if not row:
            continue
        first = _lower(str(row[0] or ""))
        if first not in {"tháng", "month"}:
            continue
        month_cols = 0
        for cell in row[1:]:
            text = str(cell or "").strip()
            if _lower(text) in {"năm", "year"}:
                continue
            if re.fullmatch(r"\d{1,2}", text):
                month_cols += 1
        if month_cols >= 4:
            return idx
    return None


def _extremum_want_max(question: str) -> bool:
    match = _EXTREMUM_RE.search(_lower(question))
    if not match:
        return True
    return match.group(1) in {"cao", "lớn", "nhiều"}


def _climate_extremum(
    rows: Sequence[Sequence[str]],
    month_row_idx: int,
    question: str,
) -> Optional[str]:
    header = rows[month_row_idx]
    metric_rows = []
    for idx, row in enumerate(rows):
        if idx == month_row_idx:
            continue
        label = str(row[0] or "").strip()
        if label and _lower(label) in _lower(question):
            metric_rows.append(row)
    if len(metric_rows) != 1:
        return None
    want_max = _extremum_want_max(question)
    best_idx: Optional[int] = None
    best_val: Optional[float] = None
    for j, cell in enumerate(header):
        if j == 0 or _lower(str(cell or "")) in {"năm", "year"}:
            continue
        if not re.fullmatch(r"\d{1,2}", str(cell or "").strip()):
            continue
        if j >= len(metric_rows[0]):
            continue
        number = _parse_number(str(metric_rows[0][j]))
        if number is None:
            continue
        if (
            best_val is None
            or (want_max and number > best_val)
            or (not want_max and number < best_val)
        ):
            best_val = number
            best_idx = j
    if best_idx is None:
        return None
    return str(header[best_idx]).strip()


def _numeric_columns(headers: Sequence[str], body_rows: Sequence[Sequence[str]]) -> List[int]:
    n_cols = len(headers)
    scored: List[Tuple[int, int]] = []
    for j in range(n_cols):
        count = 0
        for row in body_rows:
            if j < len(row) and _parse_number(str(row[j])) is not None:
                count += 1
        if count >= max(2, len(body_rows) // 3):
            scored.append((count, j))
    return [idx for _, idx in sorted(scored, reverse=True)]


def _filtered_extremum(
    headers: Sequence[str],
    body_rows: Sequence[Sequence[str]],
    question: str,
) -> Optional[str]:
    cells = list(headers) + [cell for row in body_rows for cell in row]
    required = _cell_values_in_question(question, cells)
    # Drop header labels that are just describing the metric.
    required = [
        value
        for value in required
        if _lower(value) not in {_lower(h) for h in headers}
        and not _is_numeric(value)
    ]
    filtered = [row for row in body_rows if not required or _row_has_values(row, required)]
    if not filtered:
        filtered = list(body_rows)
    numeric_cols = _numeric_columns(headers, filtered)
    if not numeric_cols:
        return None
    metric_col = numeric_cols[0]
    overlap_cols = [
        idx
        for idx in numeric_cols
        if _header_overlap(question, headers[idx]) > 0
    ]
    if overlap_cols:
        metric_col = overlap_cols[0]
    want_max = _extremum_want_max(question)
    best_row = None
    best_val: Optional[float] = None
    for row in filtered:
        if metric_col >= len(row):
            continue
        number = _parse_number(str(row[metric_col]))
        if number is None:
            continue
        if (
            best_val is None
            or (want_max and number > best_val)
            or (not want_max and number < best_val)
        ):
            best_val = number
            best_row = row
    if best_row is None:
        return None
    target = _pick_target_column(question=question, headers=headers)
    if target is None or target == metric_col:
        for idx, header in enumerate(headers):
            if idx == metric_col:
                continue
            values = [str(row[idx]).strip() for row in filtered if idx < len(row)]
            numeric_share = sum(1 for value in values if _parse_number(value) is not None) / max(1, len(values))
            if numeric_share < 0.5:
                target = idx
                break
    if target is None or target >= len(best_row):
        return None
    text = str(best_row[target] or "").strip()
    return text or None
