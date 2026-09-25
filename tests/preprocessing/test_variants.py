"""D09 table serializations and the cleaning layer."""

import json
from pathlib import Path

import pytest

from preprocessing.representation import FlattenedTable
from preprocessing.variants import ARMS, Grid, render_table

HTML = (
    "<table>"
    "<tr><th>Quốc gia</th><th>Dân số</th><th>Hình ảnh</th><th>Nguồn</th></tr>"
    "<tr><td>Việt Nam</td><td>100 [1]</td><td></td><td>[2]</td></tr>"
    "<tr><td>Lào</td><td>7,5</td><td></td><td>[3]</td></tr>"
    "</table>"
)
TABLE = {"table_id": "t", "table_html": HTML}

MERGED = {
    "table_id": "m",
    "table_html": (
        "<table><tr><th colspan='3'>Bảng dân số</th></tr>"
        "<tr><th rowspan='2'>Quốc gia</th><th colspan='2'>Dân số</th></tr>"
        "<tr><th>2019</th><th>2020</th></tr>"
        "<tr><td>Việt Nam</td><td>96</td><td>97</td></tr></table>"
    ),
}


def test_v1_raw_matches_the_production_flatten_v1_string():
    assert render_table(TABLE, "v1_raw") == FlattenedTable.from_table_data(TABLE).to_string()
    assert render_table(MERGED, "v1_raw") == FlattenedTable.from_table_data(MERGED).to_string()


def test_v1_raw_matches_flatten_v1_on_every_dataset_table():
    tables = json.loads(Path("dataset/table.json").read_text(encoding="utf-8"))["table"]
    for table in tables:
        assert render_table(table, "v1_raw") == FlattenedTable.from_table_data(table).to_string(), table["table_id"]


def test_cleaning_strips_citations_and_drops_empty_and_citation_only_columns():
    text = render_table(TABLE, "v1_clean")
    assert text == "Quốc gia <header>|Dân số <header>\nViệt Nam|100\nLào|7,5"


def test_cleaning_drops_image_and_link_only_columns_but_keeps_mixed_columns():
    html = (
        "<table><tr><th>Tên</th><th>Ảnh</th><th>Web</th><th>Ghi chú</th></tr>"
        "<tr><td>A</td><td>Tập tin:a.jpg</td><td>https://x.vn/a</td><td>Tập tin:a.jpg</td></tr>"
        "<tr><td>B</td><td>Flag.svg</td><td>www.b.vn</td><td>bình thường</td></tr></table>"
    )
    grid = Grid.from_table_data({"table_html": html}).cleaned()
    assert [row[0] for row in grid.rows] == ["Tên", "A", "B"]
    assert grid.width == 2 and grid.rows[0] == ("Tên", "Ghi chú")


def test_cleaning_keeps_non_citation_brackets_and_falls_back_when_nothing_remains():
    html = "<table><tr><th>Tên</th></tr><tr><td>Đội [A-B] [x]</td></tr></table>"
    assert render_table({"table_html": html}, "pipe_clean") == "Tên\nĐội [A-B]"
    empty = "<table><tr><th>Tên</th></tr><tr><td></td></tr></table>"
    assert render_table({"table_html": empty}, "v1_clean") == "Tên <header>\n"


def test_cleaning_drops_all_empty_body_rows_only():
    html = "<table><tr><th>Tên</th><th>Số</th></tr><tr><td></td><td></td></tr><tr><td>A</td><td>1</td></tr></table>"
    assert render_table({"table_html": html}, "pipe_clean") == "Tên|Số\nA|1"


def test_pipe_path_hoists_banner_and_joins_multirow_headers():
    assert render_table(MERGED, "pipe_path_clean") == (
        "Chú thích: Bảng dân số\nQuốc gia|Dân số / 2019|Dân số / 2020\nViệt Nam|96|97"
    )


def test_markdown_and_markdown_kv_layouts():
    assert render_table(TABLE, "markdown_clean") == (
        "| Quốc gia | Dân số |\n| --- | --- |\n| Việt Nam | 100 |\n| Lào | 7,5 |"
    )
    assert render_table(TABLE, "markdown_kv_clean") == (
        "## Hàng 1\nQuốc gia: Việt Nam\nDân số: 100\n\n## Hàng 2\nQuốc gia: Lào\nDân số: 7,5"
    )


def test_row_anchor_and_json_layouts_do_not_escape_vietnamese():
    assert render_table(TABLE, "row_anchor_clean") == (
        "col : | Quốc gia | Dân số\nrow 1 : | Việt Nam | 100\nrow 2 : | Lào | 7,5"
    )
    payload = render_table(TABLE, "json_clean")
    assert "Quốc gia" in payload and "\\u" not in payload
    assert json.loads(payload) == {"columns": ["Quốc gia", "Dân số"], "data": [["Việt Nam", "100"], ["Lào", "7,5"]]}


def test_headerless_tables_get_positional_keys():
    html = "<table><tr><td>A</td><td>1</td></tr></table>"
    assert render_table({"table_html": html}, "row_anchor_clean") == "col : | Cột 1 | Cột 2\nrow 1 : | A | 1"


@pytest.mark.parametrize("arm", sorted(ARMS))
def test_every_arm_renders_non_empty_text_for_every_dataset_table(arm):
    tables = json.loads(Path("dataset/table.json").read_text(encoding="utf-8"))["table"]
    for table in tables:
        assert render_table(table, arm).strip(), (arm, table["table_id"])


# --- pipe_nohdr ----------------------------------------------------------------------------------------


def test_pipe_nohdr_labels_the_schema_line_and_drops_the_header_tag():
    lines = render_table(TABLE, "pipe_nohdr").split("\n")
    assert lines[0] == "Cột: Quốc gia|Dân số"
    assert lines[1] == "Việt Nam|100"
    assert all("<header>" not in line for line in lines)


def test_pipe_nohdr_joins_multi_row_headers_into_one_path_and_hoists_the_banner():
    lines = render_table(MERGED, "pipe_nohdr").split("\n")
    assert lines[0] == "Chú thích: Bảng dân số"
    assert lines[1].startswith("Cột: ") and "Dân số" in lines[1]
    assert lines[-1] == "Việt Nam|96|97"


def test_pipe_nohdr_leaves_an_empty_header_cell_blank_instead_of_inventing_a_name():
    html = "<table><tr><th></th><th>Tên</th></tr><tr><td>1</td><td>An</td></tr></table>"
    assert render_table({"table_id": "b", "table_html": html}, "pipe_nohdr").split("\n")[0] == "Cột: |Tên"


def test_pipe_nohdr_keeps_the_original_header_when_every_header_cell_is_empty():
    html = "<table><tr><th></th><th></th></tr><tr><td>1</td><td>An</td></tr></table>"
    table = {"table_id": "e", "table_html": html}
    out = render_table(table, "pipe_nohdr")
    assert out == render_table(table, "pipe_clean")
    assert "Cột" not in out
