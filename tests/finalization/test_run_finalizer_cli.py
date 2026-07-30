import json
import time
from pathlib import Path

import pytest

from scripts.run_finalizer import _use_structured_mode, build_parser, main
from src.contracts.structured_outputs import (
    CallContext,
    StructuredOutputMode,
    StructuredResult,
    schema_for_call,
)
from src.finalization.artifacts import ArtifactError, sha256_file
from src.services.structured_generation import StructuredGenerator


def _write_json(path: Path, value: object) -> Path:
    path.write_text(
        json.dumps(value, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _table(table_id: str, answer: str) -> dict[str, str]:
    return {
        "table_id": table_id,
        "table_html": (
            "<table><tr><th>City</th></tr>"
            f"<tr><td>{answer}</td></tr></table>"
        ),
    }


def _fixture_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    qas_path = _write_json(
        tmp_path / "qas.json",
        {
            "qas": [
                {
                    "qa_id": "q1",
                    "table_id": "t1",
                    "question": "Thành phố thứ nhất?",
                    "answer": "GOLD-SECRET-Q1",
                },
                {
                    "qa_id": "q2",
                    "table_id": "t2",
                    "question": "Thành phố thứ hai?",
                    "answer": "GOLD-SECRET-Q2",
                },
            ]
        },
    )
    tables_path = _write_json(
        tmp_path / "tables.json",
        {
            "table": [
                _table("t1", "Hà Nội"),
                _table("t2", "Huế"),
            ]
        },
    )
    source_path = _write_json(
        tmp_path / "raw.json",
        [
            {
                "qa_id": "q1",
                "groundtruth": "SOURCE-GOLD-Q1",
                "steps": {
                    "1_question_refiner": {
                        "normalized_question": "Thành phố thứ nhất?",
                        "target": "thành phố",
                    },
                    "3_specialists": [
                        {"agent_name": "Where", "answer": "Hà Nội"}
                    ]
                },
            },
            {
                "qa_id": "q2",
                "groundtruth": "SOURCE-GOLD-Q2",
                "steps": {
                    "1_question_refiner": {
                        "normalized_question": "Thành phố thứ hai?",
                        "target": "thành phố",
                    },
                    "3_specialists": [
                        {"agent_name": "Where", "answer": "Huế"}
                    ]
                },
            },
        ],
    )
    return source_path, qas_path, tables_path


class _FakeStructuredLLM:
    def __init__(
        self,
        prompts: list[str],
        *,
        interrupt_qa_id: str | None,
        incremental_path: Path,
    ) -> None:
        self._prompts = prompts
        self._interrupt_qa_id = interrupt_qa_id
        self._incremental_path = incremental_path
        self._qa_id: str | None = None
        self._logs: list[dict[str, object]] = []
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_total_tokens = 0
        self.total_cost_usd = None

    def set_qa_id(self, qa_id: str | None) -> None:
        self._qa_id = qa_id

    def get_call_logs(self) -> list[dict[str, object]]:
        return [dict(item) for item in self._logs]

    def generate_structured(self, prompt, *, schema, **_kwargs):
        self._prompts.append(prompt)
        assert "GOLD-SECRET" not in prompt
        assert "SOURCE-GOLD" not in prompt

        if self._qa_id == self._interrupt_qa_id:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if (
                    self._incremental_path.exists()
                    and len(
                        self._incremental_path.read_text(
                            encoding="utf-8"
                        ).splitlines()
                    )
                    >= 2
                ):
                    raise KeyboardInterrupt("simulated interruption")
                time.sleep(0.01)
            raise AssertionError("first result was not appended before interruption")

        answers = {"q1": "Hà Nội", "q2": "Huế"}
        data = {
            "final_answer": answers[self._qa_id],
            "supporting_evidence": [answers[self._qa_id]],
            "decision": "selected",
        }
        self.total_prompt_tokens += 2
        self.total_completion_tokens += 1
        self.total_total_tokens += 3
        self._logs.append(
            {
                "schema_valid": True,
                "repair_attempted": False,
                "repair_succeeded": False,
            }
        )
        return StructuredResult(
            data=data,
            raw_response=json.dumps(data, ensure_ascii=False),
            schema_name=schema.name,
            schema_valid=True,
            repair_attempted=False,
            repair_succeeded=False,
            prompt_tokens=2,
            completion_tokens=1,
            total_tokens=3,
            cost_usd=None,
        )


class _FakeLLMFactory:
    def __init__(
        self,
        *,
        interrupt_qa_id: str | None,
        incremental_path: Path,
    ) -> None:
        self.prompts: list[str] = []
        self.interrupt_qa_id = interrupt_qa_id
        self.incremental_path = incremental_path

    def __call__(self, _config):
        return _FakeStructuredLLM(
            self.prompts,
            interrupt_qa_id=self.interrupt_qa_id,
            incremental_path=self.incremental_path,
        )


class _BoundedInterruptLLM:
    def __init__(self, factory) -> None:
        self._factory = factory
        self._qa_id: str | None = None
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_total_tokens = 0
        self.total_cost_usd = None

    def set_qa_id(self, qa_id: str | None) -> None:
        self._qa_id = qa_id

    def get_call_logs(self):
        return []

    def generate_structured(self, _prompt, *, schema, **_kwargs):
        qa_id = self._qa_id
        self._factory.started.append(qa_id)
        if qa_id == "q1":
            raise KeyboardInterrupt("stop paid finalizer run")
        data = {
            "final_answer": str(qa_id),
            "supporting_evidence": [str(qa_id)],
            "decision": "selected",
        }
        return StructuredResult(
            data=data,
            raw_response=json.dumps(data),
            schema_name=schema.name,
            schema_valid=True,
            repair_attempted=False,
            repair_succeeded=False,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cost_usd=None,
        )


class _BoundedInterruptFactory:
    def __init__(self) -> None:
        self.started: list[str | None] = []

    def __call__(self, _config):
        return _BoundedInterruptLLM(self)


class _MetricsLLM:
    def __init__(self, *, fail_q1: bool) -> None:
        self._fail_q1 = fail_q1
        self._qa_id: str | None = None
        self._logs: list[dict[str, object]] = []
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_total_tokens = 0
        self.total_cost_usd = None

    def set_qa_id(self, qa_id: str | None) -> None:
        self._qa_id = qa_id

    def get_call_logs(self) -> list[dict[str, object]]:
        return [dict(item) for item in self._logs]

    def generate_structured(self, _prompt, *, schema, **_kwargs):
        self.total_prompt_tokens += 2
        self.total_completion_tokens += 1
        self.total_total_tokens += 3
        if self._qa_id == "q1" and self._fail_q1:
            self._logs.append(
                {
                    "schema_valid": False,
                    "repair_attempted": True,
                    "repair_succeeded": False,
                }
            )
            raise RuntimeError("repair remained invalid")

        call_number = len(self._logs) + 1
        repair_succeeded = self._qa_id == "q2" and call_number == 3
        self._logs.append(
            {
                "schema_valid": not repair_succeeded,
                "repair_attempted": repair_succeeded,
                "repair_succeeded": repair_succeeded,
            }
        )
        data = {"answers": [f"normalized-{self._qa_id}-{call_number}"]}
        return StructuredResult(
            data=data,
            raw_response=json.dumps(data),
            schema_name=schema.name,
            schema_valid=not repair_succeeded,
            repair_attempted=repair_succeeded,
            repair_succeeded=repair_succeeded,
            prompt_tokens=2,
            completion_tokens=1,
            total_tokens=3,
            cost_usd=None,
        )


class _MetricsLLMFactory:
    def __init__(self, *, fail_q1: bool) -> None:
        self.fail_q1 = fail_q1

    def __call__(self, _config):
        return _MetricsLLM(fail_q1=self.fail_q1)


def test_parser_accepts_approved_values() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "--source",
            "raw.json",
            "--source-kind",
            "poma-specialists",
            "--finalizer",
            "gsa",
            "--qas",
            "dataset/qas_test.json",
            "--tables",
            "dataset/table.json",
            "--model",
            "openrouter/qwen/qwen3-8b",
            "--output",
            "outputs/q2/gsa.json",
        ]
    )

    assert args.finalizer == "gsa"
    assert args.source_kind == "poma-specialists"
    assert args.max_workers == 1


@pytest.mark.parametrize(
    "argv",
    [
        [
            "--source",
            "raw.json",
            "--source-kind",
            "poma-specialists",
            "--finalizer",
            "gsa",
            "--qas",
            "qas.json",
            "--model",
            "openrouter/qwen/qwen3-8b",
            "--output",
            "gsa.json",
        ],
        [
            "--source",
            "raw.json",
            "--source-kind",
            "poma-specialists",
            "--finalizer",
            "unknown",
            "--qas",
            "qas.json",
            "--tables",
            "tables.json",
            "--model",
            "openrouter/qwen/qwen3-8b",
            "--output",
            "gsa.json",
        ],
        [
            "--source",
            "same.json",
            "--source-kind",
            "poma-specialists",
            "--finalizer",
            "gsa",
            "--qas",
            "qas.json",
            "--tables",
            "tables.json",
            "--model",
            "openrouter/qwen/qwen3-8b",
            "--output",
            "same.json",
        ],
    ],
    ids=["gsa-requires-tables", "unknown-finalizer", "source-is-output"],
)
def test_parser_rejects_invalid_cross_argument_contract(argv) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(argv)


@pytest.mark.parametrize(
    "flag_args",
    [
        ["--limit", "0"],
        ["--max-workers", "0"],
        ["--retry-failed"],
    ],
    ids=["non-positive-limit", "non-positive-workers", "retry-without-resume"],
)
def test_parser_rejects_invalid_run_controls(flag_args) -> None:
    argv = [
        "--source",
        "raw.json",
        "--source-kind",
        "direct-baseline",
        "--finalizer",
        "an-common",
        "--qas",
        "qas.json",
        "--tables",
        "tables.json",
        "--model",
        "openai/gpt-4o-mini",
        "--output",
        "final.json",
        *flag_args,
    ]

    with pytest.raises(SystemExit):
        build_parser().parse_args(argv)


def test_structured_output_override_changes_generator_transport_mode() -> None:
    """Catch a manifest-only override that leaves provider requests unchanged."""
    calls: list[tuple[str, dict[str, object]]] = []

    def generate_once(prompt, text_format):
        calls.append((prompt, text_format))
        return (
            '{"final_answer":"Hà Nội"}',
            {
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
                "cost_usd": None,
            },
        )

    with _use_structured_mode(StructuredOutputMode.JSON_OBJECT):
        StructuredGenerator(generate_once).generate(
            "Answer the question.",
            schema_for_call("baseline_zero_shot.v1"),
            CallContext(
                qa_id="q1",
                agent_name="test",
                prompt_name="test",
                model="openai/gpt-4o-mini",
            ),
        )

    assert calls[0][1] == {"type": "json_object"}
    assert "Return one JSON object matching this JSON Schema" in calls[0][0]


def test_jsonl_source_failure_is_materialized_without_a_paid_finalizer_call(
    tmp_path: Path,
) -> None:
    """Catch upstream typed failures being dropped or sent to a paid finalizer."""
    _, qas_path, tables_path = _fixture_files(tmp_path)
    source_path = tmp_path / "direct.jsonl"
    source_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "qa_id": "q1",
                        "table_id": "t1",
                        "prediction": ["Hà Nội"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "qa_id": "q2",
                        "table_id": "t2",
                        "prompt_style": "zero_shot",
                        "error": {
                            "type": "StructuredGenerationError",
                            "message": "repair remained invalid",
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "gsa.json"
    factory = _FakeLLMFactory(
        interrupt_qa_id=None,
        incremental_path=tmp_path / "gsa.jsonl",
    )

    exit_code = main(
        [
            "--source",
            str(source_path),
            "--source-kind",
            "direct-baseline",
            "--finalizer",
            "gsa",
            "--qas",
            str(qas_path),
            "--tables",
            str(tables_path),
            "--model",
            "openrouter/qwen/qwen3-8b",
            "--provider",
            "openrouter",
            "--output",
            str(output_path),
            "--max-workers",
            "1",
        ],
        llm_factory=factory,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert len(factory.prompts) == 1
    assert [record["qa_id"] for record in payload["predictions"]] == [
        "q1",
        "q2",
    ]
    assert payload["predictions"][1]["error"] == {
        "type": "StructuredGenerationError",
        "message": "repair remained invalid",
    }
    assert payload["manifest"]["counts"] == {
        "dataset": 2,
        "successful": 1,
        "failed": 1,
        "attempts": 2,
    }


def test_interrupt_does_not_start_finalizers_beyond_worker_bound(
    tmp_path: Path,
) -> None:
    """Catch eager submission and waiting shutdown starting late paid calls."""
    qas = [
        {
            "qa_id": f"q{index}",
            "table_id": f"t{index}",
            "question": f"Question {index}?",
        }
        for index in range(1, 7)
    ]
    qas_path = _write_json(tmp_path / "qas.json", {"qas": qas})
    tables_path = _write_json(
        tmp_path / "tables.json",
        {
            "table": [
                _table(f"t{index}", f"answer-{index}")
                for index in range(1, 7)
            ]
        },
    )
    source_path = _write_json(
        tmp_path / "direct.json",
        [
            {
                "qa_id": f"q{index}",
                "table_id": f"t{index}",
                "prediction": [f"answer-{index}"],
            }
            for index in range(1, 7)
        ],
    )
    output_path = tmp_path / "gsa.json"
    factory = _BoundedInterruptFactory()

    with pytest.raises(
        KeyboardInterrupt,
        match="stop paid finalizer run",
    ):
        main(
            [
                "--source",
                str(source_path),
                "--source-kind",
                "direct-baseline",
                "--finalizer",
                "gsa",
                "--qas",
                str(qas_path),
                "--tables",
                str(tables_path),
                "--model",
                "openrouter/qwen/qwen3-8b",
                "--provider",
                "openrouter",
                "--output",
                str(output_path),
                "--max-workers",
                "1",
            ],
            llm_factory=factory,
        )

    assert factory.started == ["q1"]


def test_fake_llm_interrupt_then_resume_is_append_safe(
    tmp_path: Path,
    capsys,
) -> None:
    source_path, qas_path, tables_path = _fixture_files(tmp_path)
    output_path = tmp_path / "gsa.json"
    incremental_path = tmp_path / "gsa.jsonl"
    argv = [
        "--source",
        str(source_path),
        "--source-kind",
        "poma-specialists",
        "--finalizer",
        "gsa",
        "--qas",
        str(qas_path),
        "--tables",
        str(tables_path),
        "--model",
        "openrouter/qwen/qwen3-8b",
        "--provider",
        "openrouter",
        "--output",
        str(output_path),
        "--max-workers",
        "1",
        "--structured-output-mode",
        "json_object",
    ]
    interrupted_factory = _FakeLLMFactory(
        interrupt_qa_id="q2",
        incremental_path=incremental_path,
    )

    with pytest.raises(KeyboardInterrupt, match="simulated interruption"):
        main(argv, llm_factory=interrupted_factory)

    interrupted_lines = incremental_path.read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(interrupted_lines) == 2
    assert json.loads(interrupted_lines[1])["qa_id"] == "q1"
    assert not output_path.exists()

    resumed_factory = _FakeLLMFactory(
        interrupt_qa_id=None,
        incremental_path=incremental_path,
    )
    assert main([*argv, "--resume"], llm_factory=resumed_factory) == 0

    lines = incremental_path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines[1:]]
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    manifest = payload["manifest"]
    header_manifest = json.loads(lines[0])["manifest"]

    assert [record["qa_id"] for record in records] == ["q1", "q2"]
    assert len({record["qa_id"] for record in records}) == 2
    assert [record["qa_id"] for record in payload["predictions"]] == [
        "q1",
        "q2",
    ]
    assert manifest["configuration_fingerprint"] == (
        header_manifest["configuration_fingerprint"]
    )
    assert manifest["source_sha256"] == sha256_file(source_path)
    assert manifest["counts"] == {
        "dataset": 2,
        "successful": 2,
        "failed": 0,
        "attempts": 2,
    }
    assert len(interrupted_factory.prompts) == 2
    assert len(resumed_factory.prompts) == 1

    stdout = capsys.readouterr().out
    for label in (
        "coverage:",
        "failures:",
        "schema-valid rate:",
        "repair rate:",
        "tokens:",
        "cost:",
        "incremental output:",
        "materialized output:",
    ):
        assert label in stdout


@pytest.mark.parametrize(
    "mutation",
    ["unrelated-source", "tampered-configuration"],
)
def test_resume_rejects_mismatched_existing_materialized_manifest(
    tmp_path: Path,
    mutation: str,
) -> None:
    """Catch a matching JSONL silently overwriting an unrelated JSON result."""
    source_path, qas_path, tables_path = _fixture_files(tmp_path)
    output_path = tmp_path / "gsa.json"
    incremental_path = tmp_path / "gsa.jsonl"
    argv = [
        "--source",
        str(source_path),
        "--source-kind",
        "poma-specialists",
        "--finalizer",
        "gsa",
        "--qas",
        str(qas_path),
        "--tables",
        str(tables_path),
        "--model",
        "openrouter/qwen/qwen3-8b",
        "--output",
        str(output_path),
        "--max-workers",
        "1",
    ]
    factory = _FakeLLMFactory(
        interrupt_qa_id=None,
        incremental_path=incremental_path,
    )
    assert main(argv, llm_factory=factory) == 0

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    if mutation == "unrelated-source":
        payload["manifest"]["source_sha256"] = "0" * 64
    else:
        payload["manifest"]["model"] = "openrouter/other/model"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    output_before = output_path.read_bytes()
    incremental_before = incremental_path.read_bytes()

    with pytest.raises(ArtifactError):
        main(
            [*argv, "--resume"],
            llm_factory=_FakeLLMFactory(
                interrupt_qa_id=None,
                incremental_path=incremental_path,
            ),
        )

    assert output_path.read_bytes() == output_before
    assert incremental_path.read_bytes() == incremental_before


def test_summary_aggregates_every_incremental_structured_call(
    tmp_path: Path,
    capsys,
) -> None:
    """Catch retries and multi-call QAs being collapsed to official records."""
    qas_path = _write_json(
        tmp_path / "qas.json",
        {
            "qas": [
                {"qa_id": "q1", "table_id": "t1", "question": "First?"},
                {"qa_id": "q2", "table_id": "t2", "question": "Second?"},
                {"qa_id": "q3", "table_id": "t3", "question": "Số nào?"},
            ]
        },
    )
    tables_path = _write_json(
        tmp_path / "tables.json",
        {
            "table": [
                _table("t1", "alpha"),
                _table("t2", "beta"),
                _table("t3", "42"),
            ]
        },
    )
    source_path = _write_json(
        tmp_path / "raw.json",
        [
                {
                    "qa_id": "q1",
                    "steps": {
                        "1_question_refiner": {
                            "normalized_question": "First?",
                            "target": None,
                        },
                        "3_specialists": [
                        {"agent_name": "What", "answer": "alpha"}
                    ]
                },
            },
                {
                    "qa_id": "q2",
                    "steps": {
                        "1_question_refiner": {
                            "normalized_question": "Second?",
                            "target": None,
                        },
                        "3_specialists": [
                        {"agent_name": "What", "answer": "beta"},
                        {"agent_name": "What", "answer": "gamma"},
                        {"agent_name": "What", "answer": "delta"},
                    ]
                },
            },
                {
                    "qa_id": "q3",
                    "steps": {
                        "1_question_refiner": {
                            "normalized_question": "Số nào?",
                            "target": None,
                        },
                        "3_specialists": [
                        {"agent_name": "MathematicalReasoning", "answer": "42"}
                    ]
                },
            },
        ],
    )
    output_path = tmp_path / "an.json"
    incremental_path = tmp_path / "an.jsonl"
    argv = [
        "--source",
        str(source_path),
        "--source-kind",
        "poma-specialists",
        "--finalizer",
        "an-common",
        "--qas",
        str(qas_path),
        "--tables",
        str(tables_path),
        "--model",
        "openrouter/qwen/qwen3-8b",
        "--output",
        str(output_path),
        "--max-workers",
        "1",
    ]

    assert main(argv, llm_factory=_MetricsLLMFactory(fail_q1=True)) == 1
    capsys.readouterr()
    assert (
        main(
            [*argv, "--resume", "--retry-failed"],
            llm_factory=_MetricsLLMFactory(fail_q1=False),
        )
        == 0
    )

    stdout = capsys.readouterr().out
    assert "schema-valid rate: 3/5 (60.0%)" in stdout
    assert "repair rate: 2/5 (40.0%)" in stdout
    assert "tokens: prompt=10 completion=5 total=15" in stdout

    lines = incremental_path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines[1:]]
    assert [record["qa_id"] for record in records] == [
        "q1",
        "q2",
        "q3",
        "q1",
    ]
    assert [
        record["trace"]["structured_calls"] for record in records
    ] == [1, 3, 0, 1]


def test_summary_reports_na_when_no_structured_calls(
    tmp_path: Path,
    capsys,
) -> None:
    qas_path = _write_json(
        tmp_path / "qas.json",
        {
            "qas": [
                {"qa_id": "q1", "table_id": "t1", "question": "Số nào?"}
            ]
        },
    )
    tables_path = _write_json(
        tmp_path / "tables.json",
        {"table": [_table("t1", "42")]},
    )
    source_path = _write_json(
        tmp_path / "raw.json",
        [
                {
                    "qa_id": "q1",
                    "steps": {
                        "1_question_refiner": {
                            "normalized_question": "Số nào?",
                            "target": None,
                        },
                        "3_specialists": [
                        {"agent_name": "MathematicalReasoning", "answer": "42"}
                    ]
                },
            }
        ],
    )
    output_path = tmp_path / "deterministic.json"

    assert (
        main(
            [
                "--source",
                str(source_path),
                "--source-kind",
                "poma-specialists",
                "--finalizer",
                "an-common",
                "--qas",
                str(qas_path),
                "--tables",
                str(tables_path),
                "--model",
                "openrouter/qwen/qwen3-8b",
                "--output",
                str(output_path),
            ],
            llm_factory=_MetricsLLMFactory(fail_q1=False),
        )
        == 0
    )

    stdout = capsys.readouterr().out
    assert "schema-valid rate: n/a" in stdout
    assert "repair rate: n/a" in stdout
