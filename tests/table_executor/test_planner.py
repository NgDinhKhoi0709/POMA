"""D04 planner protocol: parsing, deterministic execution, and the frozen R2 gate."""

import json

from src.table_executor.ast_executor import TableView
from src.table_executor.planner import (
    extract_json_object,
    ops_used,
    r2_override,
    render_value,
    run_plan,
    serialize,
)

TABLE = {
    "table_title": "Dân số",
    "table_dict": {
        "table_rows": [
            ["Quận", "Dân số"],
            ["A", "95.664"],
            ["B", "31.527"],
            ["C", "19.456"],
            ["D", "-"],
        ]
    },
}
SELECT = {"op": "select", "args": {"scope": "body"}, "input": []}


def _reply(ast):
    return json.dumps({"plan": "x", "route": "ast" if ast else "text", "ast": ast})


def test_serialize_indexes_columns_and_rows():
    text, truncated = serialize(TABLE)
    assert "CỘT: [0]=Quận | [1]=Dân số" in text
    assert "1: A | 95.664" in text
    assert not truncated


def test_count_with_vietnamese_threshold_is_executed():
    ast = {"op": "count", "args": {}, "input": [
        {"op": "filter", "args": {"column": 1, "lt": 30000}, "input": [SELECT]}]}
    outcome = run_plan(_reply(ast), TableView.from_dataset(TABLE), "Có bao nhiêu quận?")
    assert outcome["status"] == "ok"
    assert outcome["rendered"] == "1"  # 19.456; '-' is skipped and 31.527 > 30000


def test_fenced_json_and_prose_are_parsed_but_garbage_is_parse_error():
    fenced = "```json\n" + _reply(None) + "\n```"
    assert extract_json_object(fenced)["route"] == "text"
    assert extract_json_object("Kết quả: " + _reply(None))["route"] == "text"
    outcome = run_plan("not json", TableView.from_dataset(TABLE), "q")
    assert outcome["status"] == "parse_error"


def test_bad_column_is_error_not_exception():
    ast = {"op": "count", "args": {}, "input": [
        {"op": "filter", "args": {"column": 9, "equals": "A"}, "input": [SELECT]}]}
    assert run_plan(_reply(ast), TableView.from_dataset(TABLE), "q")["status"] == "error"


def test_render_value_formats_numbers_and_yes_no():
    assert render_value(3.0, "q") == "3"
    assert render_value(2.5, "q") == "2.5"
    assert render_value(True, "Đúng không?") == "Đúng"
    assert render_value(False, "Có phải không?") == "Không"


def test_r2_gate_is_frozen():
    base = {"exec_status": "ok", "exec_rendered": "7", "ops": ["count", "filter", "select"]}
    assert r2_override(base) == "7"
    assert r2_override({**base, "ops": ["compare", "count"]}) is None  # boolean route excluded
    assert r2_override({**base, "ops": ["project", "filter"]}) is None  # lookup stays with reader
    assert r2_override({**base, "exec_status": "empty"}) is None
    assert r2_override({**base, "exec_status": "error"}) is None
    assert r2_override({**base, "exec_rendered": "  "}) is None
    assert r2_override({**base, "ops": ["argmax", "project"]}) == "7"


def test_ops_used_walks_nested_input():
    ast = {"op": "sum", "args": {}, "input": [{"op": "project", "args": {"column": 1}, "input": [SELECT]}]}
    assert ops_used(ast) == ["sum", "project", "select"]
