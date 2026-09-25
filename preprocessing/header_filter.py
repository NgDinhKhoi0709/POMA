"""D13: LLM header filtering, then a compact sub-table.

The pipeline is the one proposed by the author:

1. Parse to a rectangular grid (same ``HTMLTableParser`` pass every arm uses) and clean it with
   ``Grid.cleaned`` (citation markers, empty rows/columns, image/link-only columns).
2. Build a **header-only view**: every cell that does not carry a ``<header>`` tag has its value
   erased, so the model sees the matrix skeleton and the header cells alone. Each header cell gets a
   stable ``[Hk]`` id, which is what the model returns.
3. The model selects the header ids the question needs.
4. ``apply_selection`` keeps the columns and the rows those headers sit in and renders the result in
   Flatten V1.

Selecting nothing on an axis is a no-op on that axis (all columns, or all body rows, are kept) and is
recorded as a fallback reason rather than silently reducing to the control.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from .variants import Grid, render_v1

ID_RE = re.compile(r"H(\d+)")


@dataclass(frozen=True)
class HeaderView:
    """The blanked matrix sent to the filter, plus the id -> (row, col) map it is keyed by."""

    text: str
    positions: Dict[str, Tuple[int, int]]

    @property
    def n_headers(self) -> int:
        return len(self.positions)


@dataclass(frozen=True)
class Compact:
    """Result of applying a header selection to a grid."""

    text: str
    kept_cols: Tuple[int, ...]
    kept_rows: Tuple[int, ...]
    n_cols: int
    n_rows: int
    selected: Tuple[str, ...]
    unknown_ids: Tuple[str, ...]
    fallback: str  # "" | no_selection | parse_error | all_cols | all_rows | all_cols+all_rows


def build_header_view(grid: Grid) -> HeaderView:
    """Blank every non-header cell and label each header cell ``[Hk]``, keeping the matrix shape."""
    positions: Dict[str, Tuple[int, int]] = {}
    lines: List[str] = []
    counter = 0
    for i, (row, mask) in enumerate(zip(grid.rows, grid.header_mask)):
        cells: List[str] = []
        for j, (value, is_header) in enumerate(zip(row, mask)):
            if is_header:
                counter += 1
                key = f"H{counter}"
                positions[key] = (i, j)
                text = str(value or "").strip()
                cells.append(f"[{key}] {text} <header>" if text else f"[{key}] <header>")
            else:
                cells.append("")
        lines.append("|".join(cells))
    return HeaderView("\n".join(lines), positions)


def apply_selection(grid: Grid, view: HeaderView, selected: Sequence[str], *, parse_error: bool = False) -> Compact:
    """Compact table holding the columns and rows of the selected headers, rendered in Flatten V1."""
    width = grid.width
    n_rows = len(grid.rows)
    clean_ids: List[str] = []
    unknown: List[str] = []
    for raw in selected:
        match = ID_RE.search(str(raw).upper())
        key = f"H{match.group(1)}" if match else str(raw)
        if key in view.positions:
            if key not in clean_ids:
                clean_ids.append(key)
        else:
            unknown.append(str(raw))

    cols = sorted({view.positions[k][1] for k in clean_ids})
    body_rows = sorted({view.positions[k][0] for k in clean_ids if view.positions[k][0] >= grid.n_head})

    reasons: List[str] = []
    if parse_error:
        reasons.append("parse_error")
    if not clean_ids:
        reasons.append("no_selection")
    if not cols:
        cols = list(range(width))
        if not parse_error and clean_ids:
            reasons.append("all_cols")
    if not body_rows:
        body_rows = list(range(grid.n_head, n_rows))
        if not parse_error and clean_ids:
            reasons.append("all_rows")

    keep_rows = list(range(grid.n_head)) + body_rows
    sub = Grid(
        tuple(tuple(grid.rows[i][j] for j in cols) for i in keep_rows),
        tuple(tuple(grid.header_mask[i][j] for j in cols) for i in keep_rows),
        grid.n_head,
    )
    text = render_v1(sub)
    if not text.strip():  # never send an empty table
        text = render_v1(grid)
        cols, keep_rows = list(range(width)), list(range(n_rows))
        reasons.append("empty_result")
    return Compact(
        text=text,
        kept_cols=tuple(cols),
        kept_rows=tuple(keep_rows),
        n_cols=width,
        n_rows=n_rows,
        selected=tuple(clean_ids),
        unknown_ids=tuple(unknown),
        fallback="+".join(reasons),
    )


def prepare(table_data: dict) -> Tuple[Grid, HeaderView]:
    """Cleaned grid and its header-only view for one dataset table record."""
    grid = Grid.from_table_data(table_data)
    cleaned = grid.cleaned()
    return cleaned, build_header_view(cleaned)


FILTER_PROMPT = (
    "Bạn nhận một BẢNG đã bị xóa hết giá trị, chỉ còn lại các ô tiêu đề. "
    "Mỗi ô tiêu đề có một mã dạng [Hk].\n"
    "Hãy chọn những tiêu đề cần thiết để trả lời CÂU HỎI. Phải chọn đủ hai nhóm:\n"
    "1. Cột chứa giá trị cần lấy ra, cần so sánh hoặc cần tính toán.\n"
    "2. Cột chứa giá trị dùng để xác định đúng hàng (tên riêng, mốc thời gian, hạng mục, "
    "hoặc bất kỳ điều kiện nào nêu trong câu hỏi). Thiếu nhóm này thì không dò được hàng.\n"
    "Nếu bảng có tiêu đề nằm ở cột bên trái thì chọn thêm tiêu đề của các hàng cần thiết.\n"
    "Thà chọn thừa còn hơn bỏ sót: nếu không chắc một tiêu đề có cần hay không, hãy chọn nó.\n"
    'Trả về đúng một JSON: {"selected_headers":["H1","H4"]}.\n\n'
    "BẢNG (chỉ tiêu đề):\n{header_view}\n\nCÂU HỎI: {question}\n"
)


def build_filter_prompt(question: str, view: HeaderView) -> str:
    return FILTER_PROMPT.replace("{header_view}", view.text).replace("{question}", str(question).strip())
