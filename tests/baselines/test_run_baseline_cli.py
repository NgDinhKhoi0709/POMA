import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from scripts.run_baseline import build_parser


class _DirectBaselineClient:
    def __init__(self) -> None:
        self.calls = []

    def generate_with_usage(self, model, prompt, config, **kwargs):
        self.calls.append((model, prompt, config, kwargs))
        return (
            '{"final_answer": "Guatemala"}',
            {
                "prompt_tokens": 10,
                "completion_tokens": 2,
                "total_tokens": 12,
                "cost_usd": 0.000003,
            },
        )


class _PartiallyFailingDirectBaselineClient:
    def generate_with_usage(self, _model, prompt, _config, **_kwargs):
        if "Question that fails" in prompt:
            raise RuntimeError("terminal structured generation failure")
        return (
            '{"final_answer": "Hanoi"}',
            {
                "prompt_tokens": 10,
                "completion_tokens": 2,
                "total_tokens": 12,
                "cost_usd": None,
            },
        )

    def shutdown(self):
        return None


def test_direct_baseline_writes_canonical_structured_record(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Catch direct runs that retain heuristic answer-field artifacts."""
    from baseline.llm_client import GenConfig
    from baseline.run import process_one_qa

    representation = ModuleType("preprocessing.representation")
    representation.create_representation = lambda table: SimpleNamespace(
        to_string=lambda: table["table_str"]
    )
    monkeypatch.setitem(sys.modules, "preprocessing.representation", representation)

    output_path = tmp_path / "direct.jsonl"
    client = _DirectBaselineClient()
    process_one_qa(
        {
            "qa_id": "q1",
            "table_id": "t1",
            "question": "Which country is listed?",
            "answer": "Guatemala",
        },
        {"t1": {"table_str": "Country <header>|Name <header>|Guatemala"}},
        ["openai/gpt-4o-mini"],
        {"openai/gpt-4o-mini": output_path},
        client,
        GenConfig(),
        sleep_s=0.0,
        prompt_style="few_shot",
    )

    record = json.loads(output_path.read_text(encoding="utf-8"))
    assert record["prediction"] == ["Guatemala"]
    assert "predicted_answer" not in record
    assert record["schema_name"] == "baseline_few_shot.v1"
    assert record["structured_output"] == {"final_answer": "Guatemala"}
    assert client.calls[0][2].text_format["type"] == "json_schema"
    assert client.calls[0][2].require_parameters is True


def test_direct_baseline_skip_existing_uses_qa_id(tmp_path: Path) -> None:
    from baseline.run import _load_existing_qa_ids

    output_path = tmp_path / "direct.jsonl"
    output_path.write_text(
        json.dumps({"qa_id": "q1", "prediction": ["Guatemala"]}) + "\n",
        encoding="utf-8",
    )

    assert _load_existing_qa_ids(output_path) == {"q1"}


def test_terminal_generation_failure_is_recorded_scored_and_returns_nonzero(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Catch paid generation failures being printed, dropped, and scored on a subset."""
    import run_baseline
    from baseline import run as baseline_run
    from evaluation.run import evaluate_files

    qas_path = tmp_path / "qas.json"
    qas_path.write_text(
        json.dumps(
            {
                "qas": [
                    {
                        "qa_id": "q1",
                        "table_id": "t1",
                        "question": "Question that succeeds",
                        "answer": "Hanoi",
                    },
                    {
                        "qa_id": "q2",
                        "table_id": "t2",
                        "question": "Question that fails",
                        "answer": "Hue",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    tables_path = tmp_path / "tables.json"
    tables_path.write_text(
        json.dumps(
            {
                "table": [
                    {
                        "table_id": "t1",
                        "table_html": (
                            "<table><tr><th>City</th></tr>"
                            "<tr><td>Hanoi</td></tr></table>"
                        ),
                    },
                    {
                        "table_id": "t2",
                        "table_html": (
                            "<table><tr><th>City</th></tr>"
                            "<tr><td>Hue</td></tr></table>"
                        ),
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        baseline_run,
        "LLMZeroShotClient",
        _PartiallyFailingDirectBaselineClient,
    )
    output_dir = tmp_path / "outputs"

    exit_code = run_baseline.main(
        [
            "--qas",
            str(qas_path),
            "--tables",
            str(tables_path),
            "--models",
            "openai/test-model",
            "--output_dir",
            str(output_dir),
            "--id",
            "failure-integration",
            "--max_workers",
            "1",
            "--no-eval",
        ]
    )

    output_path = output_dir / "failure-integration/openai_test-model.jsonl"
    records = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert exit_code == 1
    assert [record["qa_id"] for record in records] == ["q1", "q2"]
    assert records[1]["error"] == {
        "type": "RuntimeError",
        "message": "terminal structured generation failure",
    }
    assert "prediction" not in records[1]
    assert records[1]["prompt_style"] == "zero_shot"

    report = evaluate_files(output_path, qas_path, metrics=["f1"])
    assert report["coverage"] == {
        "evaluated_ids": ["q1", "q2"],
        "missing_predictions": [],
        "extra_predictions": [],
    }
    assert report["metrics"]["f1"]["count"] == 2


def test_interrupt_does_not_start_qas_beyond_worker_bound(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Catch eager submission and waiting shutdown starting late paid calls."""
    from baseline import run as baseline_run

    qas = [
        {
            "qa_id": f"q{index}",
            "table_id": "t1",
            "question": f"Question {index}",
        }
        for index in range(1, 7)
    ]
    started: list[str] = []

    def fake_process_one_qa(qa, *_args, **_kwargs):
        qa_id = qa["qa_id"]
        started.append(qa_id)
        if qa_id == "q1":
            raise KeyboardInterrupt("stop paid baseline run")
        return qa_id

    class _Client:
        def shutdown(self):
            return None

    monkeypatch.setattr(
        baseline_run,
        "load_dataset_pair",
        lambda *_args: (qas, {"t1": {}}),
    )
    monkeypatch.setattr(baseline_run, "process_one_qa", fake_process_one_qa)
    monkeypatch.setattr(baseline_run, "LLMZeroShotClient", _Client)
    monkeypatch.setattr(baseline_run, "tqdm", None)

    with pytest.raises(KeyboardInterrupt, match="stop paid baseline run"):
        baseline_run.run_batch_zeroshot(
            qas_path=tmp_path / "qas.json",
            tables_path=tmp_path / "tables.json",
            models=["openai/test-model"],
            output_dir=tmp_path / "outputs",
            max_workers=1,
        )

    assert started == ["q1"]


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
