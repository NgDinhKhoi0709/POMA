from pathlib import Path
import importlib
import os

from baselines.contracts import RunPaths, append_jsonl, read_jsonl
from baselines.coagt.agent_approach_open_vitabqa import (
    normalize_openai_model,
    run_open_vitabqa,
)
from baselines.coagt.convert_open_vitabqa import convert_open_vitabqa


def test_convert_open_vitabqa_for_coagt(open_vitabqa_files) -> None:
    qas_path, tables_path = open_vitabqa_files
    records = convert_open_vitabqa(qas_path, tables_path, limit=1)
    assert records == [
        {
            "ids": "q1",
            "title": "Xếp hạng",
            "statement": "Ai đứng đầu bảng?",
            "table_text": [["Tên", "Hạng"], ["An", "1"], ["Bình", "2"]],
            "answer": ["An"],
            "source_split": "test",
            "table_id": "t1",
            "hints": ["who"],
        }
    ]


def test_normalize_openai_model() -> None:
    assert normalize_openai_model("openai/gpt-4o-mini") == "gpt-4o-mini"


def test_prompt_module_does_not_overwrite_openai_key(monkeypatch) -> None:
    from baselines.coagt.utils import agents_prompt_wtq

    monkeypatch.setenv("OPENAI_API_KEY", "sentinel-key")
    importlib.reload(agents_prompt_wtq)
    assert os.environ["OPENAI_API_KEY"] == "sentinel-key"


def _fake_prediction(record: dict) -> dict:
    return {
        "qa_id": record["ids"],
        "key": record["ids"],
        "table_id": record["table_id"],
        "source_split": record["source_split"],
        "question": record["statement"],
        "response": "phân tích",
        "prediction": "An",
        "answer": record["answer"][0],
        "model": "gpt-4o-mini",
        "method": "coagt",
        "num_collectors": 1,
        "prompt_tokens": 10,
        "completion_tokens": 2,
        "total_tokens": 12,
        "api_calls": 3,
        "cost_usd": 0.000003,
        "latency_s": 0.1,
        "error": None,
        "stage": "coagt_open_vitabqa",
        "temperatures": {
            "collector": 0.2,
            "synthesizer": 0.5,
            "refiner": 0.0,
        },
        "max_chunk_tokens": 1000,
    }


def test_coagt_mock_run_writes_contract_records(
    open_vitabqa_files, tmp_path: Path, monkeypatch
) -> None:
    qas_path, tables_path = open_vitabqa_files
    paths = RunPaths.create(tmp_path, "coagt", "mock")
    monkeypatch.setattr(
        "baselines.coagt.agent_approach_open_vitabqa.run_sample",
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

    assert outcome["num_records"] == 1
    assert outcome["num_errors"] == 0
    assert read_jsonl(paths.results_jsonl)[0]["method"] == "coagt"
    assert paths.meta_json.exists()
    assert paths.qas_subset.exists()


def test_coagt_resume_skips_result_and_error_ids(
    open_vitabqa_files, tmp_path: Path, monkeypatch
) -> None:
    qas_path, tables_path = open_vitabqa_files
    paths = RunPaths.create(tmp_path, "coagt", "resume")
    append_jsonl(paths.results_jsonl, {"qa_id": "q1"})
    append_jsonl(paths.errors_jsonl, {"qa_id": "q2", "error": "old"})
    called: list[str] = []
    monkeypatch.setattr(
        "baselines.coagt.agent_approach_open_vitabqa.run_sample",
        lambda record, **kwargs: called.append(record["ids"]),
    )

    outcome = run_open_vitabqa(
        qas_path=qas_path,
        tables_path=tables_path,
        run_paths=paths,
        model="openai/gpt-4o-mini",
        limit=2,
        max_workers=1,
        resume=True,
        overwrite=False,
    )

    assert called == []
    assert outcome["skipped_existing"] == 2
