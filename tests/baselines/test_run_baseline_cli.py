import json
from pathlib import Path

import pytest

from scripts.run_baseline import build_parser


def test_cli_defaults_to_gpt4o_mini_and_one_worker() -> None:
    args = build_parser().parse_args(["coagt", "--limit", "2"])
    assert args.model == "openai/gpt-4o-mini"
    assert args.max_workers == 1


def test_cli_rejects_resume_with_overwrite() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["coq", "--resume", "--overwrite"])


def test_cli_dispatches_and_evaluates(
    open_vitabqa_files, tmp_path: Path, monkeypatch
) -> None:
    from scripts import run_baseline

    qas_path, tables_path = open_vitabqa_files
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_dispatch(method, **kwargs):
        paths = kwargs["run_paths"]
        paths.root.mkdir(parents=True, exist_ok=True)
        record = {
            "qa_id": "q1",
            "table_id": "t1",
            "question": "Ai đứng đầu bảng?",
            "prediction": "An",
            "answer": "An",
            "model": "gpt-4o-mini",
            "method": method,
            "prompt_tokens": 10,
            "completion_tokens": 2,
            "total_tokens": 12,
            "api_calls": 1,
            "cost_usd": 0.000003,
            "latency_s": 0.1,
            "error": None,
            "num_collectors": 1,
            "temperatures": {
                "collector": 0.2,
                "synthesizer": 0.5,
                "refiner": 0.0,
            },
            "max_chunk_tokens": 1000,
        }
        paths.results_jsonl.write_text(
            json.dumps(record, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        paths.qas_subset.write_text(
            json.dumps(
                {
                    "qas": [
                        {
                            "qa_id": "q1",
                            "table_id": "t1",
                            "question": "Ai đứng đầu bảng?",
                            "answer": "An",
                            "hints": ["who"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return {"num_records": 1, "num_errors": 0}

    monkeypatch.setattr(run_baseline, "dispatch_run", fake_dispatch)
    exit_code = run_baseline.main(
        [
            "coagt",
            "--qas",
            str(qas_path),
            "--tables",
            str(tables_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--run-id",
            "mock",
            "--limit",
            "1",
        ]
    )
    assert exit_code == 0
    assert (tmp_path / "out/coagt/mock/eval/report.json").exists()


def test_cli_returns_nonzero_when_adapter_reports_errors(
    open_vitabqa_files, tmp_path: Path, monkeypatch
) -> None:
    from scripts import run_baseline

    qas_path, tables_path = open_vitabqa_files
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_dispatch(method, **kwargs):
        paths = kwargs["run_paths"]
        paths.root.mkdir(parents=True, exist_ok=True)
        paths.qas_subset.write_text('{"qas":[]}', encoding="utf-8")
        return {"num_records": 0, "num_errors": 1}

    monkeypatch.setattr(run_baseline, "dispatch_run", fake_dispatch)
    assert (
        run_baseline.main(
            [
                "coagt",
                "--qas",
                str(qas_path),
                "--tables",
                str(tables_path),
                "--output-dir",
                str(tmp_path / "out"),
                "--run-id",
                "errors",
                "--limit",
                "1",
            ]
        )
        == 1
    )
