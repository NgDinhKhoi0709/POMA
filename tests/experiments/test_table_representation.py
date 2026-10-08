import json
from pathlib import Path

import pytest

from experiments.table_representation.encodings import (
    METHOD_NAMES,
    compare_sizes,
    encode_all,
    encode_table,
)
from experiments.table_representation.run_encode import main


FLAT_HTML = """
<table>
  <tr><th>Name</th><th>Year</th></tr>
  <tr><td>POMA</td><td>2026</td></tr>
</table>
"""

MERGED_HTML = """
<table>
  <tr>
    <th rowspan="2">Item</th>
    <th colspan="2">2024</th>
  </tr>
  <tr>
    <th>Q1</th>
    <th>Q2</th>
  </tr>
  <tr>
    <td>Sales</td>
    <td>10</td>
    <td>20</td>
  </tr>
</table>
"""


def _table(html: str, table_id: str = "demo") -> dict:
    return {
        "table_id": table_id,
        "table_title": "Demo table",
        "table_domain": "test",
        "table_type": [],
        "table_html": html,
    }


def test_every_method_returns_non_empty_text_for_a_flat_table():
    table = _table(FLAT_HTML)
    encoded = encode_all(table)
    names = [item.method for item in encoded]
    assert names == list(METHOD_NAMES)
    for item in encoded:
        assert item.table_id == "demo"
        assert item.n_chars == len(item.text)
        assert "POMA" in item.text or "2026" in item.text


def test_flatten_v1_matches_production_header_tags():
    text = encode_table(_table(FLAT_HTML), "flatten_v1").text
    assert "Name <header>|Year <header>" in text
    assert "POMA|2026" in text


def test_markdown_keeps_pipe_grid_and_header_row():
    text = encode_table(_table(FLAT_HTML), "markdown").text
    assert "| Name | Year |" in text
    assert "| --- | --- |" in text
    assert "| POMA | 2026 |" in text


def test_tapex_uses_col_and_row_prefixes():
    text = encode_table(_table(FLAT_HTML), "tapex").text
    assert "col: Name | Year" in text
    assert "row 1: POMA | 2026" in text


def test_json_records_are_row_dictionaries():
    payload = json.loads(encode_table(_table(FLAT_HTML), "json_records").text)
    assert payload["records"] == [{"Name": "POMA", "Year": "2026"}]


def test_merged_header_is_composed_in_markdown_and_header_path():
    table = _table(MERGED_HTML, table_id="merged")
    markdown = encode_table(table, "markdown").text
    header_path = encode_table(table, "header_path").text
    assert "2024 / Q1" in markdown
    assert "2024 / Q2" in markdown
    assert "Sales | 2024 / Q1 | 10" in header_path
    assert "Sales | 2024 / Q2 | 20" in header_path


def test_raw_html_preserves_original_markup():
    table = _table(MERGED_HTML)
    text = encode_table(table, "raw_html").text
    assert 'colspan="2"' in text
    assert 'rowspan="2"' in text


def test_compare_sizes_orders_by_character_count():
    encoded = encode_all(_table(FLAT_HTML), methods=["csv", "xml", "json_records"])
    rows = compare_sizes(encoded)
    counts = [row["n_chars"] for row in rows]
    assert counts == sorted(counts)


def test_unknown_method_raises():
    with pytest.raises(ValueError, match="Unknown method"):
        encode_table(_table(FLAT_HTML), "not-a-method")


def test_cli_writes_sample_files(tmp_path: Path):
    tables_path = tmp_path / "table.json"
    tables_path.write_text(
        json.dumps({"demo": _table(FLAT_HTML)}, ensure_ascii=False),
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"
    code = main(
        [
            "--tables",
            str(tables_path),
            "--dataset-dir",
            str(tmp_path),
            "--table-id",
            "demo",
            "--methods",
            "flatten_v1,markdown,html",
            "--output",
            str(output_dir),
            "--compare",
        ]
    )
    assert code == 0
    table_dir = output_dir / "demo"
    assert (table_dir / "flatten_v1.txt").read_text(encoding="utf-8").count("|") >= 1
    sizes = json.loads((table_dir / "sizes.json").read_text(encoding="utf-8"))
    assert {row["method"] for row in sizes} == {"flatten_v1", "markdown", "html"}
