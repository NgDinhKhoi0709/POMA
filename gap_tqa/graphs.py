"""Graph = danh sách node theo từng lớp câu hỏi; interpreter chạy tuần tự trên một state.

Node nào đã có đáp án thì các node "đọc" phía sau tự bỏ qua; đó là cạnh fallback của graph.
Graph là dữ liệu (dict), nên vòng tự học sau này sửa graph bằng cách sửa dict, không sửa code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gap_tqa import nodes
from gap_tqa.table import Table, search


@dataclass
class State:
    question: str
    table: Table
    examples: str
    answer: str | None = None
    prompt_tokens: int = 0
    calls: int = 0
    trace: list[str] = field(default_factory=list)
    cell: tuple[int, int] | None = None


def _read(s: State, fmt: str, keep_rows=None, why: str = "") -> None:
    ans, tok = nodes.read(s.table, s.question, fmt, s.examples, keep_rows)
    s.prompt_tokens += tok
    s.calls += 1
    s.answer = ans
    s.trace.append(f"read[{fmt}{why}]={ans}")


def read_full(s: State, fmt: str = "v1_raw") -> None:
    if s.answer is None:
        _read(s, fmt)


def read_anchor(s: State, fmt: str = "v1_raw") -> None:
    """Chuỗi hành động người: tìm hàng neo bằng khớp chữ, chỉ đọc các hàng đó."""
    status, _, arows, _ = search(s.question, s.table.headers, s.table.rows, relaxed=False)
    if not arows:
        status, _, arows, _ = search(s.question, s.table.headers, s.table.rows, relaxed=True)
    if arows and len(arows) < len(s.table.rows):
        _read(s, fmt, set(arows), f":anchor{len(arows)}")


def expand_if_null(s: State, fmt: str = "v1_raw") -> None:
    if s.answer is None or s.answer.strip().lower() == "null":
        s.answer = None
        _read(s, fmt, why=":expand")


def locate(s: State) -> None:
    s.cell, tok = nodes.locate(s.table, s.question)
    s.prompt_tokens += tok
    s.calls += 1
    s.trace.append(f"locate={s.cell}")


def emit_cell(s: State) -> None:
    """Ô ngắn thì phát nguyên văn; ô dài thì đọc riêng hàng đó để trích đoạn; ID hỏng thì bỏ qua."""
    if s.cell is None:
        return
    r, c = s.cell
    value = nodes.clean_cell(s.table.rows[r][c])
    if not value or nodes.is_question_cell(value, s.question):
        s.trace.append("emit:skip")
        return
    if len(value.split()) <= nodes.EMIT_MAX_WORDS:
        s.answer = value
        s.trace.append(f"emit={value}")
    else:
        _read(s, "v1_raw", {r}, ":row")


def verbalize(s: State) -> None:
    if s.answer is not None:
        s.answer = nodes.verbalize(s.question, s.answer)


NODES = {
    "read_full": read_full,
    "read_anchor": read_anchor,
    "expand_if_null": expand_if_null,
    "locate": locate,
    "emit_cell": emit_cell,
    "verbalize": verbalize,
}

# arm -> {lớp câu hỏi | "*": [(node, tham số), ...]}
GRAPHS: dict[str, dict[str, list[tuple[str, dict]]]] = {
    "A0": {"*": [("read_full", {})]},
    "A1": {"*": [("read_full", {}), ("verbalize", {})]},
    "A2a": {"*": [("read_full", {"fmt": "pipe_nohdr"}), ("verbalize", {})]},
    "A2b": {"*": [("read_full", {"fmt": "markdown_kv_clean"}), ("verbalize", {})]},
    "A3": {"*": [("read_anchor", {}), ("expand_if_null", {}), ("verbalize", {})]},
    "A4": {
        "lookup": [("locate", {}), ("emit_cell", {}), ("read_full", {}), ("verbalize", {})],
        "*": [("read_full", {}), ("verbalize", {})],
    },
    # Chọn sau khi xem dev (A2a + A3 chỉ cho lớp lookup); phải xác nhận trên dữ liệu khác dev.
    "A5": {
        "lookup": [("read_anchor", {"fmt": "pipe_nohdr"}), ("expand_if_null", {"fmt": "pipe_nohdr"}),
                   ("verbalize", {})],
        "*": [("read_full", {"fmt": "pipe_nohdr"}), ("verbalize", {})],
    },
}


def run_graph(arm: str, cls: str, s: State) -> State:
    graph = GRAPHS[arm]
    for name, kwargs in graph.get(cls, graph["*"]):
        NODES[name](s, **kwargs)
    if s.answer is None:
        s.answer = "Null"
    return s
