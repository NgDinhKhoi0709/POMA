from pathlib import Path

import pytest

from baselines.contracts import RunPaths, validate_prediction


def common_record() -> dict:
    return {
        "qa_id": "q1",
        "table_id": "t1",
        "question": "Ai đứng đầu bảng?",
        "prediction": "An",
        "answer": "An",
        "model": "gpt-4o-mini",
        "method": "coagt",
        "prompt_tokens": 10,
        "completion_tokens": 2,
        "total_tokens": 12,
        "api_calls": 3,
        "cost_usd": 0.000003,
        "latency_s": 0.2,
        "error": None,
        "num_collectors": 1,
        "temperatures": {
            "collector": 0.2,
            "synthesizer": 0.5,
            "refiner": 0.0,
        },
        "max_chunk_tokens": 1000,
    }


def test_run_paths_reject_unsafe_run_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="run-id"):
        RunPaths.create(tmp_path, "coagt", "../escape")


def test_validate_common_coagt_record() -> None:
    validate_prediction(common_record(), "coagt")


def test_validate_coq_requires_fallback_metadata() -> None:
    record = common_record() | {"method": "coq"}
    with pytest.raises(ValueError, match="pipeline_mode"):
        validate_prediction(record, "coq")


def test_validate_coq_rejects_full_pipeline_label() -> None:
    record = common_record() | {
        "method": "coq",
        "pipeline_mode": "full_chainofquery",
        "fallback_reason": "missing agents",
        "valid_sql": True,
        "final_sql": "SELECT 1",
    }
    with pytest.raises(ValueError, match="coq_base_sql_fallback"):
        validate_prediction(record, "coq")


def test_validate_coagt_requires_method_metadata() -> None:
    record = common_record()
    del record["num_collectors"]
    with pytest.raises(ValueError, match="num_collectors"):
        validate_prediction(record, "coagt")
