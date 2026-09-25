"""Deterministic executor for the small AST coverage-audit DSL.

Ported verbatim from RankA ``scripts/ast_executor.py`` (D04); do not change semantics
without re-registering the D04 protocol.

This module deliberately has no model dependency.  It works on the flattened
``table_dict.table_rows`` representation supplied by Open-ViTabQA.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable


CORE_OPERATORS = frozenset(
    {
        "select",
        "filter",
        "project",
        "argmax",
        "argmin",
        "count",
        "sum",
        "avg",
        "compare",
        "sort",
        "take",
        "set_union",
        "set_intersect",
        "render",
        "extract_span",
        "lookup_title",
        "const",
    }
)

OP_ARGUMENTS = {
    "select": frozenset({"scope"}),
    "filter": frozenset({"column", "equals", "contains", "gt", "ge", "lt", "le"}),
    "project": frozenset({"column"}),
    "argmax": frozenset({"column"}),
    "argmin": frozenset({"column"}),
    "count": frozenset(),
    "sum": frozenset(),
    "avg": frozenset(),
    "compare": frozenset({"relation"}),
    "sort": frozenset({"descending"}),
    "take": frozenset({"n"}),
    "set_union": frozenset(),
    "set_intersect": frozenset(),
    "render": frozenset({"separator"}),
    "extract_span": frozenset({"evidence_index"}),
    "lookup_title": frozenset(),
    "const": frozenset({"value"}),
}


class ExecutionError(ValueError):
    """Raised when a valid-looking AST cannot be executed deterministically."""


@dataclass(frozen=True)
class TableView:
    """A title and the dataset's rectangular table-row representation."""

    title: str
    rows: list[list[str]]

    def cell(self, row: int, column: int) -> str:
        if row < 0 or row >= len(self.rows):
            raise ExecutionError(f"row {row} is outside table bounds")
        if column < 0 or column >= len(self.rows[row]):
            raise ExecutionError(f"column {column} is outside table bounds for row {row}")
        return repair_text(self.rows[row][column])

    @classmethod
    def from_dataset(cls, table: dict[str, Any]) -> "TableView":
        table_dict = table.get("table_dict") or {}
        rows = table_dict.get("table_rows") or []
        if not isinstance(rows, list):
            raise ExecutionError("table_dict.table_rows must be a list")
        return cls(
            title=repair_text(table.get("table_title", "")),
            rows=[[repair_text(cell) for cell in row] for row in rows if isinstance(row, list)],
        )


@dataclass(frozen=True)
class RowSet:
    indexes: tuple[int, ...]


def repair_text(value: Any) -> str:
    """Recover the dataset's occasional UTF-8-as-Latin-1 strings."""
    text = str(value)
    try:
        return text.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return text


def normalize_text(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", repair_text(value)).casefold().split())


def parse_number(value: Any) -> float:
    """Parse a standalone decimal with either Vietnamese or English separators."""
    text = repair_text(value).strip().replace(" ", "")
    if not re.fullmatch(r"[+-]?[0-9][0-9.,]*", text):
        raise ExecutionError(f"numeric value required, got {value!r}")

    sign = ""
    if text[:1] in {"+", "-"}:
        sign, text = text[:1], text[1:]
    comma_count, dot_count = text.count(","), text.count(".")
    if comma_count and dot_count:
        decimal_at = max(text.rfind(","), text.rfind("."))
        decimal_mark = text[decimal_at]
        integer = text[:decimal_at].replace(",", "").replace(".", "")
        fraction = text[decimal_at + 1 :].replace(",", "").replace(".", "")
        normalized = f"{integer}.{fraction}" if fraction else integer
    elif comma_count or dot_count:
        mark = "," if comma_count else "."
        pieces = text.split(mark)
        if len(pieces) > 2:
            normalized = "".join(pieces)
        elif len(pieces) == 2 and len(pieces[1]) == 3:
            normalized = "".join(pieces)
        else:
            normalized = ".".join(pieces)
    else:
        normalized = text
    try:
        return float(sign + normalized)
    except ValueError as exc:
        raise ExecutionError(f"numeric value required, got {value!r}") from exc


def execute(ast: dict[str, Any], table: TableView, *, evidence: list[dict[str, Any]] | None = None) -> Any:
    """Execute one AST against ``table`` and return its raw deterministic value."""
    if not isinstance(ast, dict):
        raise ExecutionError("AST node must be an object")
    return _execute_node(ast, table, evidence or [])


def _execute_node(node: dict[str, Any], table: TableView, evidence: list[dict[str, Any]]) -> Any:
    op = node.get("op")
    args = node.get("args")
    inputs = node.get("input")
    if not isinstance(op, str):
        raise ExecutionError("AST node requires string op")
    if op not in CORE_OPERATORS:
        raise ExecutionError(f"unsupported operator: {op}")
    if not isinstance(args, dict):
        raise ExecutionError(f"operator {op} requires object args")
    _reject_unknown_args(op, args)
    if not isinstance(inputs, list):
        raise ExecutionError(f"operator {op} requires list input")
    values = [_execute_node(child, table, evidence) for child in inputs]

    if op == "select":
        _require_count(op, values, 0)
        if args.get("scope") != "body":
            raise ExecutionError("select only supports scope=body")
        return RowSet(tuple(range(1, len(table.rows))))

    if op == "filter":
        rows = _require_rowset(op, _one_input(op, values))
        column = _column(args, table, rows)
        conditions = [key for key in ("equals", "contains", "gt", "ge", "lt", "le") if key in args]
        if len(conditions) != 1:
            raise ExecutionError("filter requires exactly one of equals, contains, gt, ge, lt, le")
        key = conditions[0]
        if key in {"equals", "contains"}:
            needle = normalize_text(args[key])
            if key == "equals":
                matched = [row for row in rows.indexes if normalize_text(table.cell(row, column)) == needle]
            else:
                matched = [row for row in rows.indexes if needle in normalize_text(table.cell(row, column))]
        else:
            threshold = _threshold(args[key])
            compare = {"gt": lambda a: a > threshold, "ge": lambda a: a >= threshold,
                       "lt": lambda a: a < threshold, "le": lambda a: a <= threshold}[key]
            matched = []
            for row in rows.indexes:
                try:
                    number = parse_number(table.cell(row, column))
                except ExecutionError:
                    continue  # a non-numeric cell (header/total label) never satisfies a numeric bound
                if compare(number):
                    matched.append(row)
        return RowSet(tuple(matched))

    if op == "project":
        rows = _require_rowset(op, _one_input(op, values))
        column = _column(args, table, rows)
        return [table.cell(row, column) for row in rows.indexes]

    if op in {"argmax", "argmin"}:
        rows = _require_rowset(op, _one_input(op, values))
        if not rows.indexes:
            raise ExecutionError(f"{op} cannot choose from an empty row set")
        column = _column(args, table, rows)
        chooser = max if op == "argmax" else min
        numeric_rows = []
        for row in rows.indexes:
            try:
                numeric_rows.append((row, parse_number(table.cell(row, column))))
            except ExecutionError:
                continue  # '-', 'N/A', header/total labels are missing data, not candidates
        if not numeric_rows:
            raise ExecutionError(f"{op} found no numeric value in column {column}")
        winning_row = chooser(numeric_rows, key=lambda pair: pair[1])[0]
        return RowSet((winning_row,))

    if op == "count":
        value = _one_input(op, values)
        if isinstance(value, RowSet):
            return len(value.indexes)
        return len(_require_collection(op, value))

    if op in {"sum", "avg"}:
        collection = _require_collection(op, _one_input(op, values))
        numbers = [parse_number(value) for value in collection]
        if not numbers:
            raise ExecutionError(f"{op} cannot operate on an empty collection")
        total = sum(numbers)
        return total if op == "sum" else total / len(numbers)

    if op == "sort":
        collection = list(_require_collection(op, _one_input(op, values)))
        descending = args.get("descending", False)
        if not isinstance(descending, bool):
            raise ExecutionError("sort descending must be a boolean")
        return sorted(collection, key=_sortable_key, reverse=descending)

    if op == "take":
        collection = list(_require_collection(op, _one_input(op, values)))
        n = args.get("n")
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
            raise ExecutionError("take requires a non-negative integer n")
        return collection[:n]

    if op == "compare":
        left, right = _two_inputs(op, values)
        relation = args.get("relation")
        relations = {
            "eq": lambda a, b: a == b,
            "ne": lambda a, b: a != b,
            "gt": lambda a, b: a > b,
            "ge": lambda a, b: a >= b,
            "lt": lambda a, b: a < b,
            "le": lambda a, b: a <= b,
        }
        if relation not in relations:
            raise ExecutionError("compare relation must be one of eq|ne|gt|ge|lt|le")
        left, right = _comparable(left), _comparable(right)
        try:
            return relations[relation](left, right)
        except TypeError as exc:
            raise ExecutionError("compare inputs must be comparable") from exc

    if op in {"set_union", "set_intersect"}:
        left, right = _two_inputs(op, values)
        left_values = list(_require_collection(op, left))
        right_values = list(_require_collection(op, right))
        if op == "set_union":
            return _dedupe(left_values + right_values)
        right_keys = {normalize_text(value) for value in right_values}
        return _dedupe([value for value in left_values if normalize_text(value) in right_keys])

    if op == "render":
        value = _one_input(op, values)
        separator = args.get("separator", ", ")
        if not isinstance(separator, str):
            raise ExecutionError("render separator must be a string")
        if isinstance(value, RowSet):
            raise ExecutionError("render cannot render a row set directly")
        if isinstance(value, (list, tuple)):
            return separator.join(str(item) for item in value)
        return str(value)

    if op == "extract_span":
        _require_count(op, values, 0)
        index = args.get("evidence_index")
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(evidence):
            raise ExecutionError("extract_span evidence_index is outside supplied evidence")
        quote = evidence[index].get("quote")
        if not isinstance(quote, str) or not quote.strip():
            raise ExecutionError("extract_span requires a non-empty evidence quote")
        return quote

    if op == "const":
        _require_count(op, values, 0)
        value = args.get("value")
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            raise ExecutionError("const requires a string or number value")
        return value

    if op == "lookup_title":
        _require_count(op, values, 0)
        return repair_text(table.title)

    raise AssertionError(f"unhandled core operator: {op}")


def _require_count(op: str, values: list[Any], count: int) -> None:
    if len(values) != count:
        raise ExecutionError(f"operator {op} requires exactly {count} input node(s)")


def _reject_unknown_args(op: str, args: dict[str, Any]) -> None:
    unknown = sorted(set(args) - OP_ARGUMENTS[op])
    if unknown:
        raise ExecutionError(f"operator {op} has unsupported args: {', '.join(unknown)}")


def _one_input(op: str, values: list[Any]) -> Any:
    _require_count(op, values, 1)
    return values[0]


def _two_inputs(op: str, values: list[Any]) -> tuple[Any, Any]:
    _require_count(op, values, 2)
    return values[0], values[1]


def _require_rowset(op: str, value: Any) -> RowSet:
    if not isinstance(value, RowSet):
        raise ExecutionError(f"operator {op} requires a row set input")
    return value


def _require_collection(op: str, value: Any) -> Iterable[Any]:
    if isinstance(value, RowSet) or isinstance(value, (str, bytes)):
        raise ExecutionError(f"operator {op} requires a value collection")
    if not isinstance(value, (list, tuple)):
        raise ExecutionError(f"operator {op} requires a value collection")
    return value


def _column(args: dict[str, Any], table: TableView, rows: RowSet) -> int:
    column = args.get("column")
    if not isinstance(column, int) or isinstance(column, bool) or column < 0:
        raise ExecutionError("column must be a non-negative integer")
    candidates = rows.indexes or tuple(range(1, len(table.rows))) or tuple(range(len(table.rows)))
    if any(column >= len(table.rows[row]) for row in candidates):
        raise ExecutionError(f"column {column} is outside table bounds")
    return column


def _sortable_key(value: Any) -> tuple[int, Any]:
    try:
        return (0, parse_number(value))
    except ExecutionError:
        return (1, normalize_text(value))


def _dedupe(values: Iterable[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        key = normalize_text(value)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _comparable(value: Any) -> Any:
    """Unwrap a one-element list and prefer numeric over lexicographic order.

    Without this, ``compare`` on projected cells silently compared strings, so
    ``"10" > "9"`` was False.
    """
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise ExecutionError("compare needs a single value per side")
        value = value[0]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return parse_number(value)
    except ExecutionError:
        return normalize_text(value)


def _threshold(value: Any) -> float:
    if isinstance(value, bool):
        raise ExecutionError("numeric bound required")
    if isinstance(value, (int, float)):
        return float(value)
    return parse_number(value)
