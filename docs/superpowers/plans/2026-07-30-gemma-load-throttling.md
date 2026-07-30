# Gemma-only Load Throttling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce Gemma request bursts and retry frequency without changing Qwen concurrency.

**Architecture:** Scope concurrency overrides to the Gemma Anaconda Prompt block in the Q2 runbook instead of the global `.env`. Protect the isolation requirement with a documentation regression test that compares the Qwen and Gemma sections.

**Tech Stack:** Markdown, Windows `cmd.exe`, Python 3.9+, pytest.

## Global Constraints

- Apply throttling only to `openrouter/google/gemma-3-4b-it`.
- Do not modify `.env`.
- Do not change the model, provider, prompt, schema, dataset, or output paths.
- Gemma direct baselines use one QA worker.
- Gemma POMA uses one batch worker and one internal specialist worker.
- Gemma LLM retries wait 30 seconds.
- Qwen commands retain their existing concurrency defaults.

---

### Task 1: Document and lock down Gemma-only throttling

**Files:**
- Modify: `docs/Q2_EXPERIMENT_RUNBOOK.md:335-500`
- Modify: `tests/scripts/test_q2_runbook.py`

**Interfaces:**
- Consumes: the Gemma-only terminal workflow in Section 6 of the runbook.
- Produces: copy-pasteable Gemma commands with isolated environment overrides and a regression test preventing Qwen leakage.

- [x] **Step 1: Write the failing documentation regression test**

Add the documentation path beside the existing script path:

```python
DOCUMENTED_RUNBOOK = PROJECT_ROOT / "docs" / "Q2_EXPERIMENT_RUNBOOK.md"
```

Add this test:

```python
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
```

- [x] **Step 2: Run the focused test and verify RED**

Run:

```powershell
conda run -n kltn python -m pytest tests/scripts/test_q2_runbook.py::test_documented_throttling_is_scoped_to_gemma -q
```

Expected: FAIL because the Gemma runbook section does not yet contain the throttling variables or worker flags.

- [x] **Step 3: Add Gemma-only setup, flags, and cleanup**

In Section 6.5, after the Gemma path variables, add:

```bat
set "POMA_PARALLEL_WORKERS=1"
set "POMA_LLM_RETRY_DELAY=30"
```

Change the Gemma baseline generation command to include:

```text
--max_workers 1
```

Change the Gemma POMA generation command to include:

```text
--workers 1
```

At the end of the Gemma workflow, document cleanup for terminals that will later
run Qwen:

```bat
set "POMA_PARALLEL_WORKERS="
set "POMA_LLM_RETRY_DELAY="
```

State that closing the dedicated Gemma terminal performs the same cleanup.

- [x] **Step 4: Run verification**

Run:

```powershell
conda run -n kltn python -m pytest tests/scripts/test_q2_runbook.py -q
git diff --check -- docs/Q2_EXPERIMENT_RUNBOOK.md tests/scripts/test_q2_runbook.py
```

Expected: all runbook tests pass and `git diff --check` exits zero.

- [x] **Step 5: Commit**

```powershell
git add docs/Q2_EXPERIMENT_RUNBOOK.md tests/scripts/test_q2_runbook.py
git commit -m "docs: throttle Gemma experiment requests"
```
