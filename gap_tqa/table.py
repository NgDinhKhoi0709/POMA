"""Lưới ô span-aware, khớp keyword -> hàng neo / cột, và render bảng hoặc một view con của bảng."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from evaluation.normalization import normalize_text
from preprocessing.parser import HTMLTableParser
from preprocessing.variants import ARMS, Grid, render_v1

STOP = set(
    "gì nào ai bao nhiêu khi đâu tại sao vì như thế là của có được không đúng phải trong và các những "
    "một với cho từ theo này đó ở vào ra thì mà hay hoặc người nào đã sẽ đang bị bởi về tên số năm".split()
)
REF_RE = re.compile(r"\[\d+\]|\(.*?\)")


def syllables(text: str, strip_paren: bool = True) -> list[str]:
    text = REF_RE.sub(" ", text) if strip_paren else re.sub(r"\[\d+\]", " ", text)
    return re.findall(r"\w+", normalize_text(text))


def content(text: str, strip_paren: bool = True) -> set[str]:
    return {s for s in syllables(text, strip_paren) if s not in STOP}


def contained(cell: str, question_norm: str, strip_paren: bool = True) -> bool:
    """Ô (bỏ chú thích) xuất hiện nguyên cụm trong câu hỏi, theo ranh giới âm tiết."""
    c = " ".join(syllables(cell, strip_paren))
    return len(c) >= 2 and not c.isdigit() and f" {c} " in f" {question_norm} "


def overlap(cell: str, q_content: set[str], strip_paren: bool = True) -> float:
    c = content(cell, strip_paren)
    return len(c & q_content) / len(c) if c else 0.0


def grid(table: dict) -> tuple[list[list[str]], list[list[str]]]:
    """(các hàng header, các hàng dữ liệu). Bảng không có <th> thì coi hàng đầu là header."""
    parsed = HTMLTableParser().parse(table["table_html"])
    headers = [[c.value for c in row] for row in parsed.headers]
    rows = [[c.value for c in row] for row in parsed.rows]
    if not headers and rows:
        headers, rows = rows[:1], rows[1:]
    return headers, rows


def search(question: str, headers: list[list[str]], rows: list[list[str]], relaxed: bool):
    """Trả (trạng thái, ứng viên hàng x cột, hàng neo, cột khớp)."""
    qn = " ".join(syllables(question, strip_paren=False))
    qc = content(question, strip_paren=False)
    ncol = max((len(r) for r in rows + headers), default=0)
    # Mỗi cột giữ các tầng header riêng: khớp từng tầng rồi lấy max, để header nhiều tầng không bị phạt.
    col_levels = [list(dict.fromkeys(h[c] for h in headers if c < len(h) and h[c])) for c in range(ncol)]

    def col_hit(c: int) -> bool:
        return any(
            contained(lv, qn, False) or overlap(lv, qc, False) >= (0.5 if relaxed else 0.99)
            for lv in col_levels[c]
        )

    def cell_hit(v: str) -> bool:
        if contained(v, qn):
            return True
        return relaxed and len(syllables(v)) <= 10 and overlap(v, qc) >= 0.6

    cols = {c for c in range(ncol) if col_levels[c] and col_hit(c)}
    anchors = {(r, c) for r, row in enumerate(rows) for c, v in enumerate(row) if v and cell_hit(v)}
    anchor_rows = {r for r, _ in anchors}
    if anchor_rows and cols:
        cand = {(r, c) for r in anchor_rows for c in cols} - anchors or {(r, c) for r in anchor_rows for c in cols}
        return "đủ", cand, anchor_rows, cols
    if cols:
        return "thiếu hàng", {(r, c) for r in range(len(rows)) for c in cols if c < len(rows[r])}, anchor_rows, cols
    if anchor_rows:
        return "thiếu cột", {(r, c) for r in anchor_rows for c in range(len(rows[r]))}, anchor_rows, cols
    return "không thấy", set(), anchor_rows, cols


@dataclass(frozen=True)
class Table:
    record: dict
    headers: list[list[str]]
    rows: list[list[str]]

    @classmethod
    def of(cls, record: dict) -> "Table":
        return cls(record, *grid(record))

    def render(self, fmt: str, keep_rows: set[int] | None = None) -> str:
        """Render cả bảng, hoặc chỉ các hàng dữ liệu keep_rows (giữ nguyên mọi hàng header)."""
        g = _variants_grid(self.record["table_id"], self.record["table_html"])
        if keep_rows is not None:
            n_head = g.n_head or 1  # không có <th>: hàng đầu là header, khớp với grid()
            keep = list(range(n_head)) + [n_head + r for r in sorted(keep_rows)]
            g = Grid(tuple(g.rows[i] for i in keep if i < len(g.rows)),
                     tuple(g.header_mask[i] for i in keep if i < len(g.header_mask)), g.n_head)
        render, clean = ARMS[fmt]
        text = render(g.cleaned() if clean else g)
        return text if text.strip() else render_v1(g)


@lru_cache(maxsize=None)
def _variants_grid(table_id: str, html: str) -> Grid:
    return Grid.from_table_data({"table_html": html})
