"""Behavioral safety checks for the Q2 experiment runbook."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK = PROJECT_ROOT / "scripts" / "run_q2_experiments.ps1"
DOCUMENTED_RUNBOOK = PROJECT_ROOT / "docs" / "Q2_EXPERIMENT_RUNBOOK.md"
MODELS = {
    "openrouter/qwen/qwen3-8b": "openrouter_qwen_qwen3-8b",
    "openrouter/google/gemma-3-4b-it": (
        "openrouter_google_gemma-3-4b-it"
    ),
}
DIRECT_GENERATORS = {
    "zero_shot",
    "cot",
    "task_decomposition",
    "few_shot",
}


def _run_powershell(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUNBOOK),
            *arguments,
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _parse_commands(stdout: str) -> list[list[str]]:
    commands = []
    for line in stdout.splitlines():
        if not line.startswith("'"):
            continue
        commands.append(
            [
                value.replace("''", "'")
                for value in re.findall(r"'((?:''|[^'])*)'", line)
            ]
        )
    return commands


def _run_guarded_preflight(
    *,
    limit: int,
    output_root: Path,
    fail_on_command: bool = True,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "Q2_TEST_RUNBOOK": str(RUNBOOK),
            "Q2_TEST_LIMIT": str(limit),
            "Q2_TEST_ROOT": str(output_root),
            "Q2_TEST_COMMAND_MODE": (
                "fail" if fail_on_command else "succeed"
            ),
        }
    )
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            (
                "function global:python { "
                "if ($env:Q2_TEST_COMMAND_MODE -eq 'fail') { "
                "throw 'COMMAND_EXECUTED' }; "
                "$global:LASTEXITCODE = 0 }; "
                "& $env:Q2_TEST_RUNBOOK -Phase Preflight "
                "-PreflightLimit ([int]$env:Q2_TEST_LIMIT) "
                "-OutputRoot $env:Q2_TEST_ROOT"
            ),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


def _arguments(command: list[str]) -> dict[str, str]:
    parsed = {}
    index = 2
    while index < len(command):
        option = command[index]
        if not option.startswith("--"):
            index += 1
            continue
        if index + 1 == len(command) or command[index + 1].startswith("--"):
            parsed[option] = ""
            index += 1
        else:
            parsed[option] = command[index + 1]
            index += 2
    return parsed


def test_dry_run_emits_complete_symmetric_matrix_without_writes(tmp_path):
    output_root = tmp_path / "q2"

    result = _run_powershell(
        "-Phase",
        "DryRun",
        "-OutputRoot",
        str(output_root),
    )

    assert result.returncode == 0, result.stderr
    assert not output_root.exists()
    commands = _parse_commands(result.stdout)
    assert len(commands) == 66

    baselines = [
        _arguments(command)
        for command in commands
        if command[1] == "run_baseline.py"
    ]
    poma_runs = [
        _arguments(command)
        for command in commands
        if command[1] == "run_poma.py"
    ]
    finalizers = [
        _arguments(command)
        for command in commands
        if command[1] == "scripts/run_finalizer.py"
    ]
    evaluations = [
        _arguments(command)
        for command in commands
        if command[1] == "run_eval.py"
    ]
    analyses = [
        _arguments(command)
        for command in commands
        if command[1] == "scripts/run_revision_analysis.py"
    ]
    assert (
        len(baselines),
        len(poma_runs),
        len(finalizers),
        len(evaluations),
        len(analyses),
    ) == (8, 2, 22, 32, 2)

    for model, slug in MODELS.items():
        model_baselines = [
            command for command in baselines if command["--models"] == model
        ]
        assert {
            command["--prompt-style"] for command in model_baselines
        } == DIRECT_GENERATORS
        assert all(command["--limit"] == "992" for command in model_baselines)
        assert all(
            f"{slug}\\full\\raw" in command["--output_dir"]
            for command in model_baselines
        )

        model_poma = [
            command for command in poma_runs if command["--model"] == model
        ]
        assert len(model_poma) == 1
        assert model_poma[0]["--limit"] == "992"
        assert f"{slug}\\full\\raw\\poma.json" in model_poma[0]["--output"]

        model_finalizers = [
            command for command in finalizers if command["--model"] == model
        ]
        direct = [
            command
            for command in model_finalizers
            if command["--source-kind"] == "direct-baseline"
        ]
        assert {
            (
                Path(command["--source"]).parent.name,
                command["--finalizer"],
            )
            for command in direct
        } == {
            (generator, finalizer)
            for generator in DIRECT_GENERATORS
            for finalizer in ("an-common", "gsa")
        }
        poma = [
            command
            for command in model_finalizers
            if command["--source-kind"] == "poma-specialists"
        ]
        assert {command["--finalizer"] for command in poma} == {
            "an-common",
            "an-native",
            "gsa",
        }

    for command in finalizers:
        assert command["--source"] != command["--output"]
        assert "\\full\\raw\\" in command["--source"]
        assert "\\full\\finalized\\" in command["--output"]
        if command["--finalizer"] == "an-native":
            assert command["--source-kind"] == "poma-specialists"

    for command in evaluations:
        prediction = command["--pred"]
        policy = command["--candidate-policy"]
        if prediction.endswith("\\raw\\poma.json"):
            assert policy == "first"
        elif "_an-common.json" in prediction or "_an-native.json" in prediction:
            assert policy == "all"
        else:
            assert policy == "single-required"

    for command in analyses:
        assert command["--bootstrap-samples"] == "10000"
        assert command["--seed"] == "20260729"
        assert "\\full\\reports\\revision_analysis.json" in command["--output"]


def test_preflight_uses_a_disjoint_phase_root(tmp_path):
    output_root = tmp_path / "valid-preflight"

    result = _run_guarded_preflight(
        limit=5,
        output_root=output_root,
        fail_on_command=False,
    )

    assert result.returncode == 0, result.stderr
    commands = _parse_commands(result.stdout)
    assert len(commands) == 67
    assert commands[0][1] == "scripts/create_qas_subset.py"
    matrix_commands = commands[1:]
    assert all(
        "\\preflight\\" in " ".join(command)
        for command in matrix_commands
    )
    assert not any(
        "\\full\\" in " ".join(command)
        for command in matrix_commands
    )


@pytest.mark.parametrize("limit", [0, 6, 992])
def test_preflight_rejects_out_of_range_limit_without_commands_or_files(
    tmp_path,
    limit,
):
    output_root = tmp_path / f"invalid-{limit}"

    result = _run_guarded_preflight(
        limit=limit,
        output_root=output_root,
    )

    assert result.returncode != 0
    assert _parse_commands(result.stdout) == []
    assert not output_root.exists()


def test_runbook_keeps_preflight_and_full_artifact_roots_distinct():
    text = RUNBOOK.read_text(encoding="utf-8")

    assert "Join-Path $backboneRoot $artifactPhase" in text
    assert "'preflight'" in text
    assert "'full'" in text
    assert "Invoke-Expression" not in text
    assert "API_KEY" not in text
    assert "${LASTEXITCODE}:" in text


def test_documented_throttling_is_scoped_to_gemma():
    text = DOCUMENTED_RUNBOOK.read_text(encoding="utf-8")
    qwen = text[text.index("### 6.2."):text.index("### 6.5.")]
    gemma = text[text.index("### 6.5."):text.index("### 6.8.")]

    assert "POMA_PARALLEL_WORKERS=1" not in qwen
    assert "POMA_LLM_RETRY_DELAY=30" not in qwen
    assert "--max_workers 1" not in qwen

    assert 'set "POMA_PARALLEL_WORKERS=1"' in gemma
    assert 'set "POMA_LLM_RETRY_DELAY=30"' in gemma
    assert "--max_workers 1" in gemma
    assert "--workers 1" in gemma
    assert 'set "POMA_PARALLEL_WORKERS="' in gemma
    assert 'set "POMA_LLM_RETRY_DELAY="' in gemma
