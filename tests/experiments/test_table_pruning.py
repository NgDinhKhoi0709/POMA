from experiments.table_representation.pruning import prune_all, prune_table, tokenize
from experiments.table_representation.run_prune import main


FLAT_HTML = """
<table>
  <tr><th>Name</th><th>Year</th><th>City</th></tr>
  <tr><td>POMA</td><td>2026</td><td>Hà Nội</td></tr>
  <tr><td>SEA-LION</td><td>2024</td><td>Singapore</td></tr>
  <tr><td>Qwen</td><td>2025</td><td>Hangzhou</td></tr>
</table>
"""


def _table() -> dict:
    return {
        "table_id": "demo",
        "table_title": "Models",
        "table_html": FLAT_HTML,
    }


def test_lexical_subtable_keeps_matching_row_and_drops_unrelated_city_column():
    pruned = prune_table(_table(), "Năm phát hành của POMA là gì?", method="lexical_subtable")
    assert "POMA" in pruned.text
    assert "2026" in pruned.text
    assert "SEA-LION" not in pruned.text
    assert "Hangzhou" not in pruned.text
    assert pruned.n_rows_after < pruned.n_rows_before
    assert pruned.n_chars_after < pruned.n_chars_before


def test_aggregation_question_keeps_all_data_rows():
    pruned = prune_table(
        _table(),
        "Có bao nhiêu mô hình trong bảng?",
        method="lexical_subtable",
    )
    assert pruned.skipped_row_prune is True
    assert "POMA" in pruned.text
    assert "SEA-LION" in pruned.text
    assert "Qwen" in pruned.text


def test_even_sample_is_not_question_aware():
    pruned = prune_table(_table(), "POMA", method="even_sample", max_rows=2)
    assert "POMA" in pruned.text or "Qwen" in pruned.text


def test_clean_only_strips_wiki_citations():
    dirty = {
        "table_id": "cite",
        "table_title": "",
        "table_html": "<table><tr><th>Name</th></tr><tr><td>POMA[12]</td></tr></table>",
    }
    pruned = prune_table(dirty, "POMA", method="clean_only")
    assert "POMA" in pruned.text
    assert "[12]" not in pruned.text


def test_identity_char_counts_include_title_on_both_sides():
    pruned = prune_table(_table(), "POMA", method="identity")
    assert pruned.text.startswith("TITLE:")
    assert pruned.n_chars_before == pruned.n_chars_after
    assert pruned.char_save_ratio == 0.0


def test_rank_lookup_question_does_not_skip_row_prune():
    pruned = prune_table(
        _table(),
        "Album có tựa đề album1 xếp hạng thứ mấy trên bảng xếp hạng US Heat?",
        method="lexical_subtable",
    )
    assert pruned.skipped_row_prune is False


def test_lexical_subtable_drops_parent_only_sibling_columns():
    table = {
        "table_id": "charts",
        "table_title": "San Holo",
        "table_html": """
        <table>
          <tr>
            <th rowspan="2">Tựa đề</th>
            <th colspan="3">Vị trí trên bảng xếp hạng</th>
          </tr>
          <tr>
            <th>US Dance</th>
            <th>US Heat</th>
            <th>NLD</th>
          </tr>
          <tr>
            <td>album1</td>
            <td>7</td>
            <td>20</td>
            <td>80</td>
          </tr>
          <tr>
            <td>bb u ok?</td>
            <td>3</td>
            <td>5</td>
            <td>—</td>
          </tr>
        </table>
        """,
    }
    pruned = prune_table(
        table,
        "Album có tựa đề album1 xếp hạng thứ mấy trên bảng xếp hạng US Heat?",
        method="lexical_subtable",
    )
    assert pruned.skipped_row_prune is False
    assert "album1" in pruned.text
    assert "20" in pruned.text
    assert "bb u ok" not in pruned.text
    assert "US Heat" in pruned.text
    assert "NLD" not in pruned.text


def test_tokenize_drops_stopwords_and_keeps_entities():
    tokens = tokenize("Album có tựa đề album1 xếp hạng US Heat")
    assert "album1" in tokens
    assert "heat" in tokens
    assert "có" not in tokens


def test_tokenize_keeps_vietnamese_words_intact():
    tokens = tokenize("xếp hạng thứ mấy trên bảng")
    assert "xếp" in tokens
    assert "hạng" in tokens
    assert "thứ" in tokens
    assert "th" not in tokens
    assert "ếp" not in tokens
    assert "ạng" not in tokens


def test_narrative_detail_cells_do_not_keep_unrelated_rows():
    table = {
        "table_id": "charts_detail",
        "table_title": "San Holo",
        "table_html": """
        <table>
          <tr>
            <th rowspan="2">Tựa đề</th>
            <th rowspan="2">Chi tiết</th>
            <th colspan="3">Vị trí trên bảng xếp hạng</th>
          </tr>
          <tr>
            <th>US Dance</th>
            <th>US Heat</th>
            <th>NLD</th>
          </tr>
          <tr>
            <td>album1</td>
            <td>Phát hành: 21 tháng 9 năm 2018 Hãng phát hành: bitbird Định dạng: Digital download</td>
            <td>7</td>
            <td>20</td>
            <td>80</td>
          </tr>
          <tr>
            <td>bb u ok?</td>
            <td>Phát hành: 4 tháng 6 năm 2021 Hãng phát hành: bitbird Định dạng: Digital download</td>
            <td>3</td>
            <td>5</td>
            <td>—</td>
          </tr>
        </table>
        """,
    }
    pruned = prune_table(
        table,
        "Album có tựa đề album1 xếp hạng thứ mấy trên bảng xếp hạng US Heat?",
        method="lexical_subtable",
    )
    assert "album1" in pruned.text
    assert "20" in pruned.text
    assert "bb u ok" not in pruned.text
    assert "Chi tiết" not in pruned.text
    assert "bitbird" not in pruned.text
    assert "NLD" not in pruned.text
    assert "US Heat" in pruned.text


def test_unknown_method_raises():
    import pytest

    with pytest.raises(ValueError, match="Unknown prune method"):
        prune_table(_table(), "POMA", method="not-real")


def test_cli_prunes_from_inline_question(tmp_path):
    tables_path = tmp_path / "table.json"
    import json

    tables_path.write_text(json.dumps({"demo": _table()}, ensure_ascii=False), encoding="utf-8")
    output_dir = tmp_path / "out"
    code = main(
        [
            "--tables",
            str(tables_path),
            "--dataset-dir",
            str(tmp_path),
            "--table-id",
            "demo",
            "--question",
            "POMA năm bao nhiêu?",
            "--methods",
            "identity,lexical_subtable",
            "--output",
            str(output_dir),
            "--compare",
        ]
    )
    assert code == 0
    text = (output_dir / "demo" / "lexical_subtable.txt").read_text(encoding="utf-8")
    assert "POMA" in text
    sizes = json.loads((output_dir / "demo" / "sizes.json").read_text(encoding="utf-8"))
    assert {row["method"] for row in sizes} == {"identity", "lexical_subtable"}


def test_prune_all_covers_registered_methods():
    results = prune_all(_table(), "POMA")
    assert [item.method for item in results] == [
        "identity",
        "clean_only",
        "even_sample",
        "lexical_rows",
        "lexical_cols",
        "lexical_subtable",
    ]
