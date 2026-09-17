import json

from experiments.table_representation.run_sealion_gguf import (
    main,
    parse_final_answer,
    select_items,
)


def test_parse_final_answer_reads_json_and_maps_null():
    assert parse_final_answer('{"final_answer": "Hà Nội"}') == "Hà Nội"
    assert parse_final_answer('noise\n{"final_answer": null}\n') == "Null"


def test_select_items_honors_limit():
    items = [{"qa_id": str(i)} for i in range(20)]
    assert [row["qa_id"] for row in select_items(items, limit=10)] == [str(i) for i in range(10)]


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
