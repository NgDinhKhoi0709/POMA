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
from src.finalization.artifacts import sha256_file
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
                    "3_specialists": [
                        {"agent_name": "Where", "answer": "Hà Nội"}
                    ]
                },
            },
            {
                "qa_id": "q2",
                "groundtruth": "SOURCE-GOLD-Q2",
                "steps": {
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
