import json
from pathlib import Path

import pytest


@pytest.fixture
def open_vitabqa_files(tmp_path: Path) -> tuple[Path, Path]:
    qas = {
        "qas": [
            {
                "qa_id": "q1",
                "table_id": "t1",
                "question": "Ai đứng đầu bảng?",
                "answer": "An",
                "hints": ["who"],
            },
            {
                "qa_id": "q2",
                "table_id": "t1",
                "question": "Có bao nhiêu người?",
                "answer": "2",
                "hints": ["mathematical_reasoning"],
            },
        ]
    }
    tables = {
        "table": [
            {
                "table_id": "t1",
                "table_title": "Xếp hạng",
                "table_dict": {
                    "table_rows": [["Tên", "Hạng"], ["An", "1"], ["Bình", "2"]]
                },
            }
        ]
    }
    qas_path = tmp_path / "qas.json"
    tables_path = tmp_path / "tables.json"
    qas_path.write_text(json.dumps(qas, ensure_ascii=False), encoding="utf-8")
    tables_path.write_text(json.dumps(tables, ensure_ascii=False), encoding="utf-8")
    return qas_path, tables_path
