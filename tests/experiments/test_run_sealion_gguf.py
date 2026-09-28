import json

from experiments.table_representation.run_sealion_gguf import (
    canonicalize_answer,
    expand_candidates,
    finalize_prediction,
    main,
    parse_final_answer,
    select_items,
    table_text,
    yesno_pair,
)


def test_parse_final_answer_reads_json_and_maps_null():
    assert parse_final_answer('{"final_answer": "Hà Nội"}') == "Hà Nội"
    assert parse_final_answer('noise\n{"final_answer": null}\n') == "Null"


def test_select_items_honors_limit():
    items = [{"qa_id": str(i)} for i in range(20)]
    assert [row["qa_id"] for row in select_items(items, limit=10)] == [str(i) for i in range(10)]


def test_yesno_pair_follows_question_wording():
    assert yesno_pair("Có phải có 3 tòa nhà cao từ 150m trở lên?") == ("Phải", "Không")
    assert yesno_pair("Năm 2020 % dân số thế giới có dưới 66.00% không?") == ("Có", "Không")
    assert yesno_pair("Shin Dong-yup đã nhận giải thưởng lớn năm 2002 đúng không?") == ("Đúng", "Không")


def test_canonicalize_maps_english_yes_to_phai():
    assert canonicalize_answer("Có phải A?", "Yes") == "Phải"
    assert canonicalize_answer("Có phải A?", "no") == "Không"


def test_expand_candidates_adds_year_and_question_span():
    years = expand_candidates("1709", question="Ấn vàng ra đời khi nào?")
    assert "1709" in years
    assert "Năm 1709" in years
    spans = expand_candidates(
        "23",
        question="Giữa 2 kênh tần số là 23 (UHF/VHF) và 28 (UHF/VHF) thì kênh nào?",
    )
    assert "23 (UHF/VHF)" in spans
    yesno = expand_candidates(
        "SNG.INV",
        question="Đội SNG.Invincible có tên viết tắt là SNG.INV đúng không?",
    )
    assert "Đúng" in yesno


def test_finalize_prediction_prefers_frequency_rank_over_llm():
    table = {
        "table_id": "vt",
        "table_title": "",
        "table_html": """
        <table>
          <tr><th>Số</th><th>VT</th></tr>
          <tr><td>1</td><td>HV</td></tr>
          <tr><td>2</td><td>HV</td></tr>
          <tr><td>3</td><td>TV</td></tr>
        </table>
        """,
    }
    prediction, op = finalize_prediction(
        question="Vị trí nào được sử dụng nhiều thứ 2 trong bảng dữ liệu này?",
        table=table,
        llm_answer="HV",
    )
    assert op == "frequency_rank"
    assert prediction[0] == "TV"


def test_auto_table_mode_uses_full_markdown_for_tiny_tables():
    table = {
        "table_id": "demo",
        "table_title": "Models",
        "table_html": "<table><tr><th>Name</th><th>Year</th></tr><tr><td>POMA</td><td>2026</td></tr></table>",
    }
    text, mode = table_text(table, "POMA năm nào?", "auto", max_rows=8, max_cols=6)
    assert mode == "markdown_full"
    assert "| Name | Year |" in text
    assert "POMA" in text


def test_table_text_html_and_header_path_are_full_encodings():
    table = {
        "table_id": "demo",
        "table_title": "Models",
        "table_html": "<table><tr><th>Name</th><th>Year</th></tr><tr><td>POMA</td><td>2026</td></tr></table>",
    }
    html, html_mode = table_text(table, "POMA năm nào?", "html", max_rows=8, max_cols=6)
    assert html_mode == "html"
    assert "<table>" in html
    assert "POMA" in html
    path, path_mode = table_text(table, "POMA năm nào?", "header_path", max_rows=8, max_cols=6)
    assert path_mode == "header_path"
    assert "POMA" in path
    assert "Year" in path or "year" in path.lower()


def test_cli_dry_run_lists_first_ten(tmp_path):
    tables_path = tmp_path / "table.json"
    qas_path = tmp_path / "qas_test.json"
    tables_path.write_text(
        json.dumps(
            {
                "demo": {
                    "table_id": "demo",
                    "table_title": "Models",
                    "table_html": "<table><tr><th>Name</th></tr><tr><td>POMA</td></tr></table>",
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    qas_path.write_text(
        json.dumps(
            {
                "qas": [
                    {"qa_id": f"id_{i}", "table_id": "demo", "question": "POMA?", "answer": "POMA"}
                    for i in range(12)
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output = tmp_path / "out"
    code = main(
        [
            "--tables",
            str(tables_path),
            "--dataset-dir",
            str(tmp_path),
            "--qas",
            str(qas_path),
            "--limit",
            "10",
            "--output",
            str(output),
            "--dry-run",
        ]
    )
    assert code == 0
    selected = json.loads((output / "selected_ids.json").read_text(encoding="utf-8"))
    assert selected == [f"id_{i}" for i in range(10)]
