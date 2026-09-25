# Compact Baseline Prompts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all four direct-baseline prompts concise and require only `{"final_answer": string | null}`, while removing prompt-version handling.

**Architecture:** Keep four templates so each experimental strategy remains distinct, but give all of them the same closed output contract. Return a plain string from the prompt builder, remove prompt-version metadata in the runner, and align the existing per-style structured schemas with nullable `final_answer`.

**Tech Stack:** Python 3.9+, pytest, existing JSON Schema contracts.

## Global Constraints

- Use only table evidence.
- Emit exactly one JSON object with only `final_answer`.
- Use JSON `null`, not the string `"Null"`, when the table cannot answer.
- Keep existing prompt-style names and schema names.
- Add no dependencies or abstractions.

---

### Task 1: Lock the compact prompt API and contract

**Files:**
- Modify: `tests/baselines/test_structured_prompt_styles.py`
- Modify: `tests/baselines/test_run_baseline_cli.py`
- Modify: `tests/services/test_structured_generation.py`

**Interfaces:**
- Consumes: `build_tableqa_prompt(question: str, table_str: str, prompt_style: str) -> str`
- Produces: regression coverage for prompt content, nullable baseline schemas, and absent `prompt_version` output metadata.

- [ ] **Step 1: Replace prompt-version assertions with the desired API assertions**

Parametrize all four styles, call `build_tableqa_prompt(...)` as a string, and assert table/question inclusion, `"final_answer"` inclusion, JSON `null` guidance, and absence of output fields `"reasoning"` and `"subproblems"`.

- [ ] **Step 2: Add runner metadata assertion**

In `test_direct_baseline_writes_canonical_structured_record`, assert `"prompt_version" not in record`.

- [ ] **Step 3: Replace obsolete task-decomposition domain test**

Remove the `baseline_task_decomposition.v1` case that requires non-empty `subproblems`; add a focused assertion that every baseline schema has exactly one nullable required property:

```python
for name in (
    "baseline_zero_shot.v1",
    "baseline_few_shot.v1",
    "baseline_cot.v1",
    "baseline_task_decomposition.v1",
):
    schema = STRUCTURED_SCHEMAS[name].json_schema
    assert schema["required"] == ["final_answer"]
    assert schema["properties"] == {"final_answer": _expected_nullable_shape}
```

- [ ] **Step 4: Run focused tests and verify RED**

Run: `python -m pytest tests/baselines/test_structured_prompt_styles.py tests/baselines/test_run_baseline_cli.py::test_direct_baseline_writes_canonical_structured_record tests/services/test_structured_generation.py -q`

Expected: failures because the builder still returns a tuple, version metadata still exists, and CoT/task-decomposition schemas still require extra fields.

---

### Task 2: Implement the minimum production changes

**Files:**
- Modify: `baseline/prompts.py`
- Modify: `baseline/run.py`
- Modify: `src/contracts/structured_outputs.py`

**Interfaces:**
- Produces: `build_tableqa_prompt(...) -> str`; `build_tableqa_prompt_flatten_v1_table_str(...) -> str`
- Preserves: `PROMPT_STYLES`, style validation, and existing per-style schema names.

- [ ] **Step 1: Compact all prompt templates**

Use `TABLE_STR:` and `QUESTION:` markers in each template. State that only table evidence may be used and output must be exactly `{{"final_answer": <string|null>}}`. Add one short internal-strategy sentence to CoT and task decomposition; retain only concise few-shot examples for answer and null.

- [ ] **Step 2: Remove prompt-version code**

Delete all prompt-version constants, `_PROMPT_VERSION_BY_STYLE`, `resolve_prompt_version`, and aliases. Make both builder functions return only the formatted prompt string.

- [ ] **Step 3: Remove runner version metadata**

Change `prompt, prompt_version = build_tableqa_prompt(...)` to `prompt = build_tableqa_prompt(...)`; remove `prompt_version` from success and error JSONL records.

- [ ] **Step 4: Align baseline schemas**

Give all four existing baseline schema names `_closed_object({"final_answer": _NULLABLE_STRING}, ["final_answer"])`. Remove the task-decomposition `subproblems` domain invariant.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `python -m pytest tests/baselines/test_structured_prompt_styles.py tests/baselines/test_run_baseline_cli.py::test_direct_baseline_writes_canonical_structured_record tests/services/test_structured_generation.py -q`

Expected: all pass.

- [ ] **Step 6: Run baseline regression suite**

Run: `python -m pytest tests/baselines -q`

Expected: all pass.
