"""D09: alternative table serializations and a conservative cleaning layer.

Every serializer works on one rectangular ``Grid`` built by the same ``HTMLTableParser`` pass that
Flatten V1 uses, so cell text is identical across arms and only layout differs. ``Grid.cleaned``
removes web-scrape noise (citation markers, empty/image/link-only columns) before any serializer
runs. Flatten V1 (``preprocessing.representation``) stays the untouched control.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

from .parser import HTMLTableParser

CITATION_RE = re.compile(r"\[(?:\d{1,3}|[a-z]|ghi chú \d+|cần dẫn nguồn)\]")
FILE_CELL_RE = re.compile(r"^(?:tập tin|tệp|file|image|hình):|\.(?:jpe?g|png|svg|gif|webp)$", re.IGNORECASE)
URL_CELL_RE = re.compile(r"^(?:https?://|www\.)\S+$", re.IGNORECASE)


@dataclass(frozen=True)
class Grid:
    """Header rows first (``n_head`` of them), then body rows; all rows have equal width."""

    rows: Tuple[Tuple[str, ...], ...]
    header_mask: Tuple[Tuple[bool, ...], ...]
    n_head: int

    @classmethod
    def from_table_data(cls, table_data: Dict[str, Any]) -> "Grid":
        parsed = HTMLTableParser().parse(str(table_data.get("table_html") or "").strip())
        cells = parsed.headers + parsed.rows
        width = max((len(row) for row in cells), default=0)
        rows, mask = [], []
        for row in cells:
            values = [str(cell.value or "").strip() for cell in row]
            flags = [bool(cell.is_header) for cell in row]
            rows.append(tuple(values + [""] * (width - len(values))))
            mask.append(tuple(flags + [False] * (width - len(flags))))
        return cls(tuple(rows), tuple(mask), len(parsed.headers))

    @property
    def width(self) -> int:
        return len(self.rows[0]) if self.rows else 0

    def cleaned(
        self,
        *,
        strip_citations: bool = True,
        drop_empty_columns: bool = True,
        drop_link_columns: bool = True,
        drop_empty_rows: bool = True,
    ) -> "Grid":
        """Conservative cleaning; falls back to ``self`` if nothing usable would remain."""
        rows = [list(row) for row in self.rows]
        if strip_citations:
            rows = [[_strip_citations(v) for v in row] for row in rows]
        body = rows[self.n_head:]
        keep = []
        for j in range(self.width):
            values = [row[j] for row in body if row[j]]
            if drop_empty_columns and not values:
                continue
            if drop_link_columns and values and all(FILE_CELL_RE.search(v) or URL_CELL_RE.match(v) for v in values):
                continue
            keep.append(j)
        keep_rows = [
            i for i in range(len(rows))
            if not (drop_empty_rows and i >= self.n_head and not any(rows[i][j] for j in keep))
        ]
        if not keep or len(keep_rows) <= self.n_head:
            return self
        n_head = sum(1 for i in keep_rows if i < self.n_head)
        return Grid(
            tuple(tuple(rows[i][j] for j in keep) for i in keep_rows),
            tuple(tuple(self.header_mask[i][j] for j in keep) for i in keep_rows),
            n_head,
        )

    def _split(self) -> Tuple[List[str], List[str], List[Tuple[str, ...]]]:
        """(banner captions, one key per column, body rows). Full-width identical header rows are banners."""
        banners: List[str] = []
        head: List[Tuple[str, ...]] = []
        for row in self.rows[: self.n_head]:
            if len(row) > 1 and row[0] and len(set(row)) == 1:
                banners.append(row[0])
            else:
                head.append(row)
        keys = []
        for j in range(self.width):
            parts: List[str] = []
            for row in head:
                if row[j] and (not parts or parts[-1] != row[j]):
                    parts.append(row[j])
            keys.append(" / ".join(parts) or f"Cột {j + 1}")
        return [f"Chú thích: {b}" for b in banners], keys, list(self.rows[self.n_head:])


def _strip_citations(value: str) -> str:
    return re.sub(r"\s{2,}", " ", CITATION_RE.sub("", value)).strip()


def render_v1(grid: Grid) -> str:
    """Flatten V1 layout over a grid (identical to ``FlattenedTable.to_string`` on an uncleaned grid)."""
    lines = []
    for row, mask in zip(grid.rows, grid.header_mask):
        cells = [((f"{v} <header>" if v else "<header>") if is_head else v) for v, is_head in zip(row, mask)]
        lines.append("|".join(cells))
    return "\n".join(lines)


def render_flatten_v2(table_data: Dict[str, Any]) -> str:
    """Flatten V1 minus columns that are empty in every body row of the original table (e.g. image columns)."""
    grid = Grid.from_table_data(table_data)
    return render_v1(grid.cleaned(strip_citations=False, drop_link_columns=False, drop_empty_rows=False))


def render_pipe_plain(grid: Grid) -> str:
    """Pipe rows without the ``<header>`` tag; header rows kept as they are."""
    return "\n".join("|".join(row) for row in grid.rows)


def render_pipe_path(grid: Grid) -> str:
    """One header line (multi-row headers joined as ``Cha / Con``), banners hoisted, no tag."""
    captions, keys, body = grid._split()
    return "\n".join(captions + ["|".join(keys)] + ["|".join(row) for row in body])


def render_pipe_nohdr(grid: Grid) -> str:
    """Pipe rows under one labelled schema line ``Cột: A|B|C``; no ``<header>`` tag, no header rows.

    Differs from ``render_pipe_path`` in two ways: the schema line carries the ``Cột:`` label so it cannot
    be mistaken for a data row, and a table whose header cells are all empty keeps its original header rows
    instead of degenerating into ``Cột 1|Cột 2|...`` (which would throw the real header away).
    """
    captions, keys, body = grid._split()
    synthetic = [key == f"Cột {j + 1}" for j, key in enumerate(keys)]
    if all(synthetic):
        return render_pipe_plain(grid)
    keys = ["" if fake else key for key, fake in zip(keys, synthetic)]  # never invent a column name
    return "\n".join(captions + ["Cột: " + "|".join(keys)] + ["|".join(row) for row in body])


def render_markdown(grid: Grid) -> str:
    captions, keys, body = grid._split()
    lines = captions + ["| " + " | ".join(keys) + " |", "| " + " | ".join("---" for _ in keys) + " |"]
    return "\n".join(lines + ["| " + " | ".join(row) + " |" for row in body])


def render_markdown_kv(grid: Grid) -> str:
    """One block per body row, one ``Tên cột: giá trị`` line per cell."""
    captions, keys, body = grid._split()
    out = list(captions)
    for i, row in enumerate(body, 1):
        out.append(f"## Hàng {i}")
        out.extend(f"{key}: {value}" for key, value in zip(keys, row))
        out.append("")
    return "\n".join(out).strip()


def render_row_anchor(grid: Grid) -> str:
    """StructLM / TableLlama style explicit ``col :`` and ``row i :`` anchors."""
    captions, keys, body = grid._split()
    lines = captions + ["col : | " + " | ".join(keys)]
    return "\n".join(lines + [f"row {i} : | " + " | ".join(row) for i, row in enumerate(body, 1)])


def render_json_columns(grid: Grid) -> str:
    """TableBench-style ``{"columns": [...], "data": [[...]]}``; never ASCII-escape Vietnamese."""
    captions, keys, body = grid._split()
    return "\n".join(captions + [json.dumps({"columns": keys, "data": [list(row) for row in body]}, ensure_ascii=False)])


# arm id -> (renderer, apply cleaning layer)
ARMS: Dict[str, Tuple[Callable[[Grid], str], bool]] = {
    "v1_raw": (render_v1, False),
    "v1_clean": (render_v1, True),
    "pipe_clean": (render_pipe_plain, True),
    "pipe_path_clean": (render_pipe_path, True),
    "pipe_nohdr": (render_pipe_nohdr, True),
    "markdown_clean": (render_markdown, True),
    "markdown_kv_clean": (render_markdown_kv, True),
    "row_anchor_clean": (render_row_anchor, True),
    "json_clean": (render_json_columns, True),
}


def render_table(table_data: Dict[str, Any], arm: str) -> str:
    """Serialize one dataset table record for the given arm id."""
    render, clean = ARMS[arm]
    grid = Grid.from_table_data(table_data)
    text = render(grid.cleaned() if clean else grid)
    return text if text.strip() else render_v1(grid)
