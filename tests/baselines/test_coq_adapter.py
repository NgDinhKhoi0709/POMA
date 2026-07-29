from pathlib import Path

import pytest

from baselines.chain_of_query.convert_open_vitabqa import convert_open_vitabqa
from baselines.chain_of_query.run_open_vitabqa import (
    require_fallback_mode,
    run_open_vitabqa,
)
from baselines.contracts import RunPaths, read_jsonl
from utils.database import MYSQLDB


def test_convert_open_vitabqa_for_coq(open_vitabqa_files) -> None:
    qas_path, tables_path = open_vitabqa_files
    records = convert_open_vitabqa(qas_path, tables_path, limit=1)
    assert records[0]["qa_id"] == "q1"
    assert records[0]["table_id"] == "t1"
    assert records[0]["question"] == "Ai đứng đầu bảng?"
    assert records[0]["answer"] == "An"
    assert records[0]["hints"] == ["who"]
    assert records[0]["table"]["title"] == "Xếp hạng"
    assert records[0]["table"]["table"] == {
        "header": ["Tên", "Hạng"],
        "rows": [["An", "1"], ["Bình", "2"]],
    }


def test_require_fallback_mode_rejects_full_chainofquery() -> None:
    with pytest.raises(RuntimeError, match="coq_base_sql_fallback"):
        require_fallback_mode(
            {
                "pipeline_mode": "full_chainofquery",
                "fallback_reason": "",
            }
        )


def _fake_prediction(record: dict) -> dict:
    return {
        "qa_id": record["qa_id"],
        "key": record["qa_id"],
        "table_id": record["table_id"],
        "source_split": "test",
        "question": record["question"],
        "response": "An",
        "prediction": "An",
        "answer": record["answer"],
        "model": "gpt-4o-mini",
        "method": "coq",
        "prompt_tokens": 10,
        "completion_tokens": 2,
        "total_tokens": 12,
        "api_calls": 2,
        "cost_usd": 0.000003,
        "latency_s": 0.1,
        "error": None,
        "stage": "chainofquery_open_vitabqa",
        "pipeline_mode": "coq_base_sql_fallback",
        "fallback_reason": "Missing full pipeline modules: column_selector",
        "valid_sql": True,
        "final_sql": 'SELECT "Tên" FROM "Xếp hạng" LIMIT 1',
        "log": {"sqls": []},
    }


def test_coq_mock_run_preserves_fallback(
    open_vitabqa_files, tmp_path: Path, monkeypatch
) -> None:
    qas_path, tables_path = open_vitabqa_files
    paths = RunPaths.create(tmp_path, "coq", "mock")
    monkeypatch.setattr(
        "baselines.chain_of_query.run_open_vitabqa._run_one",
        lambda record, **kwargs: _fake_prediction(record),
    )

    outcome = run_open_vitabqa(
        qas_path=qas_path,
        tables_path=tables_path,
        run_paths=paths,
        model="openai/gpt-4o-mini",
        limit=1,
        max_workers=1,
        resume=False,
        overwrite=False,
    )

    record = read_jsonl(paths.results_jsonl)[0]
    assert record["pipeline_mode"] == "coq_base_sql_fallback"
    assert record["fallback_reason"]
    assert outcome["pipeline_mode"] == "coq_base_sql_fallback"
    assert paths.meta_json.exists()


def test_mysqldb_close_removes_sqlite_file_on_windows(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    database = MYSQLDB(
        tables=[
            {
                "title": "ranking",
                "table": {
                    "header": ["name", "rank"],
                    "rows": [["An", 1]],
                },
            }
        ]
    )
    db_path = Path(database.db_path)
    assert db_path.exists()

    database.close()

    assert database._closed is True
    assert not db_path.exists()
