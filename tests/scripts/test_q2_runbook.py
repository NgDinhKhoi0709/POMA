"""Static safety checks for the Q2 experiment runbook."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK = PROJECT_ROOT / "scripts" / "run_q2_experiments.ps1"


def test_runbook_declares_complete_symmetric_matrix():
    """Keep every Q2 system, finalizer, and safety boundary reviewable."""
    text = RUNBOOK.read_text(encoding="utf-8")

    for required in (
        "openrouter/qwen/qwen3-8b",
        "openrouter/google/gemma-3-4b-it",
        "zero_shot",
        "cot",
        "task_decomposition",
        "few_shot",
        "poma",
        "an-common",
        "an-native",
        "gsa",
        "single-required",
        "--candidate-policy all",
        "--candidate-policy first",
        "--bootstrap-samples 10000",
        "--seed 20260729",
        "raw",
        "finalized",
    ):
        assert required in text

    assert "[string]$Phase = 'DryRun'" in text
    assert "[int]$PreflightLimit = 5" in text
    assert "[string]$OutputRoot = 'outputs/q2_revision'" in text
    assert "Invoke-Expression" not in text
    assert "API_KEY" not in text


def test_runbook_delimits_exit_code_before_a_colon():
    """Keep the DryRun script parseable by PowerShell."""
    text = RUNBOOK.read_text(encoding="utf-8")

    assert "${LASTEXITCODE}:" in text
