"""Serialize an Open-ViTabQA table into alternative LLM prompt formats.

All methods start from the same parsed logical grid used by Flatten V1:
merged ``rowspan``/``colspan`` cells are expanded, then each method chooses
a different text layout. ``raw_html`` is the exception and returns the
original ``table_html`` string from the dataset.
"""

from __future__ import annotations

import csv
import html
import io
import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from preprocessing.parser import HTMLTableParser, ParsedTable
from preprocessing.representation import FlattenedTable

METHOD_NAMES: Tuple[str, ...] = (
    "flatten_v1",
    "markdown",
    "html",
    "raw_html",
    "csv",
    "json_records",
    "json_triples",
    "markdown_kv",
    "tapex",
    "nl_sentences",
    "xml",
    "latex",
    "spreadsheet_a1",
    "inverted_index",
    "header_path",
    "df_loader",
)


@dataclass(frozen=True)
class EncodedTable:
    """One serialized table plus lightweight size stats."""

    method: str
    table_id: str
    title: str
    text: str
    n_chars: int
    n_lines: int
    n_rows: int
    n_cols: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "table_id": self.table_id,
            "title": self.title,
            "text": self.text,
            "n_chars": self.n_chars,
            "n_lines": self.n_lines,
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
        }


@dataclass(frozen=True)
class _Grid:
    table_id: str
    title: str
    rows: List[List[str]]
    header_mask: List[List[bool]]
    raw_html: str
    parsed: Optional[ParsedTable]


def encode_table(table_data: Dict[str, Any], method: str) -> EncodedTable:
    """Encode one table record with the named method."""
    if method not in METHOD_NAMES:
        raise ValueError(f"Unknown method {method!r}. Choose one of: {', '.join(METHOD_NAMES)}")
    grid = _grid_from_table_data(table_data)
    text = _ENCODERS[method](grid)
    return EncodedTable(
        method=method,
        table_id=grid.table_id,
        title=grid.title,
        text=text,
        n_chars=len(text),
        n_lines=0 if not text else text.count("\n") + 1,
        n_rows=len(grid.rows),
        n_cols=_n_cols(grid.rows),
    )


def encode_all(table_data: Dict[str, Any], methods: Optional[Sequence[str]] = None) -> List[EncodedTable]:
    """Encode one table with every requested method, defaulting to all methods."""
    selected = list(methods) if methods is not None else list(METHOD_NAMES)
    return [encode_table(table_data, method) for method in selected]


def _grid_from_table_data(table_data: Dict[str, Any]) -> _Grid:
    flattened = FlattenedTable.from_table_data(table_data)
    rows = FlattenedTable._normalize_rows(flattened.rows)
    header_mask = FlattenedTable._normalize_header_mask(flattened.header_mask, rows)
    raw_html = str(table_data.get("table_html") or "").strip()
    parsed = HTMLTableParser().parse(raw_html) if raw_html else None
    return _Grid(
        table_id=str(flattened.table_id or table_data.get("table_id") or ""),
        title=str(flattened.title or table_data.get("table_title") or ""),
        rows=rows,
        header_mask=header_mask,
        raw_html=raw_html,
        parsed=parsed,
    )


def _n_cols(rows: Sequence[Sequence[str]]) -> int:
    return max((len(row) for row in rows), default=0)


def _split_header_and_body(grid: _Grid) -> Tuple[List[List[str]], List[List[str]]]:
    n_header_rows = 0
    for mask_row in grid.header_mask:
        if mask_row and sum(1 for flag in mask_row if flag) > len(mask_row) // 2:
            n_header_rows += 1
        else:
            break
    return grid.rows[:n_header_rows], grid.rows[n_header_rows:]


def _compose_column_headers(header_rows: Sequence[Sequence[str]], n_cols: int) -> List[str]:
    headers: List[str] = []
    for col in range(n_cols):
        parts: List[str] = []
        for row in header_rows:
            value = str(row[col] if col < len(row) else "").strip()
            if value and (not parts or parts[-1] != value):
                parts.append(value)
        headers.append(" / ".join(parts) if parts else f"col_{col + 1}")
    return headers


def _escape_md_cell(value: str) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def _escape_latex(value: str) -> str:
    text = str(value or "")
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def _col_letter(index: int) -> str:
    n = index + 1
    letters = []
    while n:
        n, rem = divmod(n - 1, 26)
        letters.append(chr(65 + rem))
    return "".join(reversed(letters))


def _with_title(grid: _Grid, body: str) -> str:
    title = grid.title.strip()
    if not title:
        return body
    if not body:
        return f"TITLE: {title}"
    return f"TITLE: {title}\n{body}"


def _encode_flatten_v1(grid: _Grid) -> str:
    dummy = {
        "table_id": grid.table_id,
        "table_title": grid.title,
        "table_html": grid.raw_html,
        "table_type": [],
    }
    return FlattenedTable.from_table_data(dummy).to_string() if grid.raw_html else FlattenedTable(
        table_id=grid.table_id,
        title=grid.title,
        domain="",
        rows=grid.rows,
        header_mask=grid.header_mask,
    ).to_string()


def _encode_markdown(grid: _Grid) -> str:
    header_rows, body = _split_header_and_body(grid)
    n_cols = _n_cols(grid.rows)
    headers = _compose_column_headers(header_rows, n_cols) if header_rows else [
        f"col_{i + 1}" for i in range(n_cols)
    ]
    data_rows = body if body else grid.rows
    lines = [
        "| " + " | ".join(_escape_md_cell(h) for h in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in data_rows:
        padded = list(row) + [""] * (n_cols - len(row))
        lines.append("| " + " | ".join(_escape_md_cell(cell) for cell in padded[:n_cols]) + " |")
    return _with_title(grid, "\n".join(lines))


def _encode_html(grid: _Grid) -> str:
    header_rows, body = _split_header_and_body(grid)
    parts = ["<table>"]
    if header_rows:
        parts.append("<thead>")
        for row in header_rows:
            cells = "".join(f"<th>{html.escape(cell)}</th>" for cell in row)
            parts.append(f"<tr>{cells}</tr>")
        parts.append("</thead>")
    parts.append("<tbody>")
    data_rows = body if body else ([] if header_rows else grid.rows)
    for row in data_rows:
        cells = "".join(f"<td>{html.escape(cell)}</td>" for cell in row)
        parts.append(f"<tr>{cells}</tr>")
    parts.append("</tbody></table>")
    return _with_title(grid, "\n".join(parts))


def _encode_raw_html(grid: _Grid) -> str:
    return grid.raw_html


def _encode_csv(grid: _Grid) -> str:
    header_rows, body = _split_header_and_body(grid)
    n_cols = _n_cols(grid.rows)
    headers = _compose_column_headers(header_rows, n_cols) if header_rows else [
        f"col_{i + 1}" for i in range(n_cols)
    ]
    data_rows = body if body else grid.rows
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    for row in data_rows:
        padded = list(row) + [""] * (n_cols - len(row))
        writer.writerow(padded[:n_cols])
    return _with_title(grid, buffer.getvalue().rstrip("\n"))


def _encode_json_records(grid: _Grid) -> str:
    header_rows, body = _split_header_and_body(grid)
    n_cols = _n_cols(grid.rows)
    headers = _compose_column_headers(header_rows, n_cols) if header_rows else [
        f"col_{i + 1}" for i in range(n_cols)
    ]
    records = []
    for row in (body if body else grid.rows):
        padded = list(row) + [""] * (n_cols - len(row))
        record = {headers[i]: padded[i] for i in range(n_cols)}
        records.append(record)
    payload = {"title": grid.title, "records": records}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _encode_json_triples(grid: _Grid) -> str:
    header_rows, body = _split_header_and_body(grid)
    n_cols = _n_cols(grid.rows)
    headers = _compose_column_headers(header_rows, n_cols) if header_rows else [
        f"col_{i + 1}" for i in range(n_cols)
    ]
    triples = []
    for row_idx, row in enumerate(body if body else grid.rows, start=1):
        padded = list(row) + [""] * (n_cols - len(row))
        row_label = padded[0] if padded else str(row_idx)
        for col_idx, header in enumerate(headers):
            triples.append(
                {
                    "row": row_label,
                    "column": header,
                    "value": padded[col_idx],
                }
            )
    payload = {"title": grid.title, "triples": triples}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _encode_markdown_kv(grid: _Grid) -> str:
    header_rows, body = _split_header_and_body(grid)
    n_cols = _n_cols(grid.rows)
    headers = _compose_column_headers(header_rows, n_cols) if header_rows else [
        f"col_{i + 1}" for i in range(n_cols)
    ]
    blocks = []
    for row_idx, row in enumerate(body if body else grid.rows, start=1):
        padded = list(row) + [""] * (n_cols - len(row))
        lines = [f"- row: {row_idx}"]
        for header, value in zip(headers, padded):
            lines.append(f"  {header}: {value}")
        blocks.append("\n".join(lines))
    return _with_title(grid, "\n\n".join(blocks))


def _encode_tapex(grid: _Grid) -> str:
    header_rows, body = _split_header_and_body(grid)
    n_cols = _n_cols(grid.rows)
    headers = _compose_column_headers(header_rows, n_cols) if header_rows else [
        f"col_{i + 1}" for i in range(n_cols)
    ]
    parts = ["col: " + " | ".join(headers)]
    data_rows = body if body else grid.rows
    for idx, row in enumerate(data_rows, start=1):
        padded = list(row) + [""] * (n_cols - len(row))
        parts.append(f"row {idx}: " + " | ".join(padded[:n_cols]))
    return _with_title(grid, " ".join(parts))


def _encode_nl_sentences(grid: _Grid) -> str:
    header_rows, body = _split_header_and_body(grid)
    n_cols = _n_cols(grid.rows)
    headers = _compose_column_headers(header_rows, n_cols) if header_rows else [
        f"col_{i + 1}" for i in range(n_cols)
    ]
    sentences = []
    for row in (body if body else grid.rows):
        padded = list(row) + [""] * (n_cols - len(row))
        clauses = [f"{headers[i]} is {padded[i]}" for i in range(n_cols) if str(padded[i]).strip()]
        if clauses:
            sentences.append("; ".join(clauses) + ".")
    return _with_title(grid, " ".join(sentences))


def _encode_xml(grid: _Grid) -> str:
    header_rows, body = _split_header_and_body(grid)
    n_cols = _n_cols(grid.rows)
    headers = _compose_column_headers(header_rows, n_cols) if header_rows else [
        f"col_{i + 1}" for i in range(n_cols)
    ]
    parts = ["<table>"]
    if grid.title.strip():
        parts.append(f"  <title>{html.escape(grid.title)}</title>")
    for row in (body if body else grid.rows):
        padded = list(row) + [""] * (n_cols - len(row))
        parts.append("  <row>")
        for header, value in zip(headers, padded):
            parts.append(
                f'    <cell header="{html.escape(header)}">{html.escape(value)}</cell>'
            )
        parts.append("  </row>")
    parts.append("</table>")
    return "\n".join(parts)


def _encode_latex(grid: _Grid) -> str:
    header_rows, body = _split_header_and_body(grid)
    n_cols = _n_cols(grid.rows)
    headers = _compose_column_headers(header_rows, n_cols) if header_rows else [
        f"col_{i + 1}" for i in range(n_cols)
    ]
    spec = "l" * max(n_cols, 1)
    lines = [f"\\begin{{tabular}}{{{spec}}}"]
    lines.append(" & ".join(_escape_latex(h) for h in headers) + " \\\\")
    lines.append("\\hline")
    for row in (body if body else grid.rows):
        padded = list(row) + [""] * (n_cols - len(row))
        lines.append(" & ".join(_escape_latex(cell) for cell in padded[:n_cols]) + " \\\\")
    lines.append("\\end{tabular}")
    return _with_title(grid, "\n".join(lines))


def _encode_spreadsheet_a1(grid: _Grid) -> str:
    lines = []
    for row_idx, row in enumerate(grid.rows):
        cells = []
        for col_idx, value in enumerate(row):
            cells.append(f"{_col_letter(col_idx)}{row_idx + 1},{value}")
        lines.append("|".join(cells))
    return _with_title(grid, "\n".join(lines))


def _encode_inverted_index(grid: _Grid) -> str:
    mapping: Dict[str, List[str]] = {}
    for row_idx, row in enumerate(grid.rows):
        for col_idx, value in enumerate(row):
            text = str(value or "").strip()
            if not text:
                continue
            mapping.setdefault(text, []).append(f"{_col_letter(col_idx)}{row_idx + 1}")
    payload = {"title": grid.title, "value_to_addresses": mapping}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _encode_header_path(grid: _Grid) -> str:
    header_rows, body = _split_header_and_body(grid)
    n_cols = _n_cols(grid.rows)
    col_paths = _compose_column_headers(header_rows, n_cols) if header_rows else [
        f"col_{i + 1}" for i in range(n_cols)
    ]
    lines = []
    data_rows = body if body else grid.rows
    for row in data_rows:
        padded = list(row) + [""] * (n_cols - len(row))
        row_label = padded[0].strip() or "(unnamed row)"
        start = 1 if n_cols > 1 else 0
        for col_idx in range(start, n_cols):
            lines.append(f"{row_label} | {col_paths[col_idx]} | {padded[col_idx]}")
    return _with_title(grid, "\n".join(lines))


def _encode_df_loader(grid: _Grid) -> str:
    header_rows, body = _split_header_and_body(grid)
    n_cols = _n_cols(grid.rows)
    headers = _compose_column_headers(header_rows, n_cols) if header_rows else [
        f"col_{i + 1}" for i in range(n_cols)
    ]
    data_rows = body if body else grid.rows
    widths = [len(h) for h in headers]
    string_rows = []
    for row in data_rows:
        padded = [str(cell) for cell in row] + [""] * (n_cols - len(row))
        padded = padded[:n_cols]
        string_rows.append(padded)
        for i, cell in enumerate(padded):
            widths[i] = max(widths[i], len(cell))
    index_width = max(len(str(len(string_rows) - 1)), 1)
    header_line = " " * (index_width + 1) + "  ".join(
        header.ljust(widths[i]) for i, header in enumerate(headers)
    )
    body_lines = []
    for idx, row in enumerate(string_rows):
        cells = "  ".join(row[i].ljust(widths[i]) for i in range(n_cols))
        body_lines.append(f"{str(idx).rjust(index_width)} {cells}".rstrip())
    return _with_title(grid, "\n".join([header_line.rstrip()] + body_lines))


_ENCODERS: Dict[str, Callable[[_Grid], str]] = {
    "flatten_v1": _encode_flatten_v1,
    "markdown": _encode_markdown,
    "html": _encode_html,
    "raw_html": _encode_raw_html,
    "csv": _encode_csv,
    "json_records": _encode_json_records,
    "json_triples": _encode_json_triples,
    "markdown_kv": _encode_markdown_kv,
    "tapex": _encode_tapex,
    "nl_sentences": _encode_nl_sentences,
    "xml": _encode_xml,
    "latex": _encode_latex,
    "spreadsheet_a1": _encode_spreadsheet_a1,
    "inverted_index": _encode_inverted_index,
    "header_path": _encode_header_path,
    "df_loader": _encode_df_loader,
}


def compare_sizes(encoded: Iterable[EncodedTable]) -> List[Dict[str, Any]]:
    """Return size stats sorted by character count."""
    rows = [
        {
            "method": item.method,
            "n_chars": item.n_chars,
            "n_lines": item.n_lines,
            "n_rows": item.n_rows,
            "n_cols": item.n_cols,
        }
        for item in encoded
    ]
    return sorted(rows, key=lambda row: row["n_chars"])


_TOKEN_RE = re.compile(r"\S+")


def rough_token_count(text: str) -> int:
    """Whitespace token count used only for cheap size comparisons."""
    return len(_TOKEN_RE.findall(text or ""))
