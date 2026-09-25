# Kaggle Full-Test Zero-Shot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run zero-shot SEA-LION inference over all of `qas_test.json` from the Kaggle notebook.

**Architecture:** Extend the existing phase enum with `test`; reuse the runner's default unsampled selection branch and test-dataset routing. Point the notebook at that phase without adding a second inference loop.

**Tech Stack:** Python, Jupyter Notebook JSON, pytest.

## Global Constraints

- Use all records in `dataset/qas_test.json`.
- Run `zero_shot` mode only.
- Keep existing resumability and output archiving.
- Add no dependencies.

---

### Task 1: Define failing phase and notebook tests

**Files:**
- Modify: `tests/scripts/test_run_sea_lion_kaggle_eval.py`
- Modify: `tests/kaggle_eval/test_runner.py`
- Modify: `tests/notebooks/test_kaggle_sea_lion_poma_notebook.py`

- [ ] Assert the CLI accepts `--phase test`.
- [ ] Assert phase `test` resolves to `dataset/qas_test.json`.
- [ ] Assert the notebook contains `--phase test`, `--mode zero_shot`, and no execution outputs.
- [ ] Run focused tests and confirm they fail for the missing phase/notebook configuration.

### Task 2: Implement and verify

**Files:**
- Modify: `scripts/run_sea_lion_kaggle_eval.py`
- Modify: `src/kaggle_eval/runner.py`
- Modify: `notebooks/kaggle_sea_lion_poma.ipynb`

- [ ] Add `test` to parser and `RunConfig` phase choices.
- [ ] Route `test` to `qas_test.json`; default selection returns the full list.
- [ ] Update and clear the notebook.
- [ ] Run focused tests, notebook JSON validation, and syntax checks.
- [ ] Commit only task-related files and push `main`.
