# SEA-LION Kaggle POMA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Kaggle-ready SEA-LION v3 8B IT evaluation path for POMA with local 4-bit inference, compact prompts, 200-item dev pilot, optional 543-item final run, checkpointing, and paired zero-shot/POMA reports.

**Architecture:** Add local model support beside the existing OpenAI/OpenRouter path instead of replacing it. Keep POMA orchestration intact, add a compact prompt profile selected by config, and put Kaggle-specific selection, JSONL resume, runner, and report helpers in a small `src/kaggle_eval` package consumed by a thin notebook.

**Tech Stack:** Python 3.9+, pytest, transformers, bitsandbytes, torch, jsonschema, existing POMA `run_pipeline`, existing baseline prompt builder, existing evaluation metrics and bootstrap helpers.

## Global Constraints

- Model id: `aisingapore/Llama-SEA-LION-v3-8B-IT`.
- Runtime: `transformers` plus `bitsandbytes` with 4-bit NF4 quantization.
- Hardware target: one Kaggle T4 GPU, batch size one, sequential execution.
- Generation: `do_sample=False`; no chain-of-thought prompting; no temperature parameter when greedy decoding is used.
- Context: 32K-token window; maximum input budget is 28,672 tokens.
- Prompt profile: compact shared prompt profile; no model-specific rewrite for final comparison unless reported as a separate experiment.
- HintPredictor input: `table_preview` capped at 1,024 model tokens with title, headers, whole sampled rows from beginning, middle, and end, and omitted-row markers.
- Specialist agents and GroundedSingleAnswer receive the full flattened table.
- Context overflow behavior: record `context_overflow` and checkpoint; never silently truncate evidence table content.
- Structured output: accept raw JSON, fenced JSON, and text-wrapped JSON when exactly one object can be extracted; validate contracts; perform one repair call; record raw output and repair metadata.
- Pilot: 200 deterministic QA items from `dataset/qas_dev.json`, `seed=42`, stratified by hint and table length.
- Final: same 543 test QA IDs used for Gemma/Qwen comparisons; only runs when `RUN_FINAL_543 = True`.
- Notebook source modes: Kaggle Dataset mode and Git clone mode with explicit revision.
- Outputs: append-only JSONL under `/kaggle/working/` by default; no generated `outputs/` artifacts committed.

---

## File Structure

Create:

- `src/services/local_transformers_client.py`: owns local SEA-LION model loading, chat-template prompt execution, token counting, input-budget checks, greedy generation, usage metadata, and teardown.
- `src/kaggle_eval/__init__.py`: exports Kaggle evaluation helpers.
- `src/kaggle_eval/jsonl_io.py`: append/load/complete-ID helpers for resumable JSONL files.
- `src/kaggle_eval/table_preview.py`: structure-aware 1,024-token table preview builder.
- `src/kaggle_eval/selection.py`: deterministic pilot/final ID selection utilities.
- `src/kaggle_eval/runner.py`: sequential zero-shot and POMA run helpers with JSONL checkpointing.
- `src/kaggle_eval/reporting.py`: per-run metrics, paired comparison, bootstrap CI, compliance and error summaries.
- `scripts/run_sea_lion_kaggle_eval.py`: CLI wrapper around `src.kaggle_eval.runner` for local smoke tests and notebook cells.
- `notebooks/kaggle_sea_lion_poma.ipynb`: Kaggle notebook that installs deps, locates repo/data, loads SEA-LION, runs smoke/pilot/final, and displays reports.
- `src/prompts_compact/...`: compact prompt profile mirroring the existing `src/prompts` file tree.
- `tests/services/test_local_transformers_client.py`: mocked local client tests.
- `tests/kaggle_eval/test_jsonl_io.py`: resume and terminal-error completion tests.
- `tests/kaggle_eval/test_table_preview.py`: preview token-limit and row-preservation tests.
- `tests/kaggle_eval/test_selection.py`: deterministic 200-pilot and 543-final selection tests.
- `tests/kaggle_eval/test_reporting.py`: paired metrics/report tests.
- `tests/scripts/test_run_sea_lion_kaggle_eval.py`: CLI config/path tests without loading a model.
- `tests/services/test_prompt_profiles.py`: compact prompt directory selection tests.

Modify:

- `src/config/settings.py`: add prompt-profile, prompt-dir override, local-model, max-input-token, max-new-token, and local quantization settings.
- `src/services/prompt_loader.py`: select prompt directory from settings and expose cache reset for tests.
- `src/services/structured_generation.py`: support local prompt-only mode and robust JSON object extraction.
- `src/contracts/structured_outputs.py`: add `JSON_TEXT_EXTRACT` structured output mode or equivalent enum value for local generation.
- `src/services/llm_client.py`: route `local/...` model ids to `LocalTransformersClient`; preserve existing OpenAI/OpenRouter behavior.
- `src/agents/hint_predictor.py`: accept preview text through the existing prompt variable and keep API stable.
- `src/orchestration/pipeline.py`: pass a preview to HintPredictor when agent hints are enabled; leave specialists and normalization on the full table.
- `baseline/prompts.py`: add compact zero-shot prompt style if the notebook needs a separate baseline prompt name.
- `run_poma.py`: only if required to reuse helpers; prefer keeping notebook runner in `src/kaggle_eval/runner.py`.
- `requirements.txt` or `baselines/requirements.txt`: add optional Kaggle-local dependencies only if the repo already has a suitable requirements surface; otherwise keep notebook install commands explicit.

Do not modify unrelated generated output files or existing dirty worktree changes outside these paths.

---

### Task 1: Config And Prompt Profile Selection

**Files:**
- Modify: `src/config/settings.py`
- Modify: `src/services/prompt_loader.py`
- Create: `tests/services/test_prompt_profiles.py`

**Interfaces:**
- Produces: `Settings.prompt_profile: str`, `Settings.prompts_dir: Path`, `Settings.local_model: LocalModelConfig`, `reset_prompt_cache() -> None`.
- Consumes: existing `load_prompt(name: str, **kwargs: str) -> str`.

- [ ] **Step 1: Write failing tests for default and compact prompt directories**

Add this test file:

```python
from pathlib import Path

import src.config.settings as settings_module
import src.services.prompt_loader as prompt_loader


def _reset_settings(monkeypatch, project_root: Path) -> None:
    monkeypatch.setattr(settings_module, "_settings", None)
    monkeypatch.setenv("POMA_PROJECT_ROOT", str(project_root))
    prompt_loader.reset_prompt_cache()


def test_default_prompt_profile_uses_src_prompts(monkeypatch, tmp_path):
    root = tmp_path
    (root / "src" / "prompts").mkdir(parents=True)
    (root / "src" / "prompts" / "sample.md").write_text("default {x}", encoding="utf-8")
    _reset_settings(monkeypatch, root)

    assert settings_module.get_settings().prompt_profile == "default"
    assert prompt_loader.load_prompt("sample", x="A") == "default A"


def test_compact_prompt_profile_uses_src_prompts_compact(monkeypatch, tmp_path):
    root = tmp_path
    (root / "src" / "prompts_compact").mkdir(parents=True)
    (root / "src" / "prompts_compact" / "sample.md").write_text("compact {x}", encoding="utf-8")
    monkeypatch.setenv("POMA_PROMPT_PROFILE", "compact")
    _reset_settings(monkeypatch, root)

    assert settings_module.get_settings().prompts_dir == root / "src" / "prompts_compact"
    assert prompt_loader.load_prompt("sample", x="B") == "compact B"


def test_prompt_dir_override_wins_over_profile(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    custom = tmp_path / "custom_prompts"
    custom.mkdir(parents=True)
    (custom / "sample.md").write_text("custom {x}", encoding="utf-8")
    monkeypatch.setenv("POMA_PROMPT_PROFILE", "compact")
    monkeypatch.setenv("POMA_PROMPTS_DIR", str(custom))
    _reset_settings(monkeypatch, root)

    assert settings_module.get_settings().prompts_dir == custom
    assert prompt_loader.load_prompt("sample", x="C") == "custom C"
```

- [ ] **Step 2: Run tests and verify they fail for missing config**

Run: `python -m pytest tests/services/test_prompt_profiles.py -v`

Expected: FAIL because `POMA_PROJECT_ROOT`, `POMA_PROMPT_PROFILE`, `POMA_PROMPTS_DIR`, and `reset_prompt_cache()` are not implemented.

- [ ] **Step 3: Add settings fields**

In `src/config/settings.py`, add:

```python
@dataclass(frozen=True)
class LocalModelConfig:
    model_id: str = "aisingapore/Llama-SEA-LION-v3-8B-IT"
    max_model_len: int = 32768
    max_input_tokens: int = 28672
    quantization: str = "nf4"
    max_new_tokens: int = 512
```

Change `Settings.project_root` to read `POMA_PROJECT_ROOT` when set, add `prompt_profile: str = "default"`, and set `prompts_dir` from `POMA_PROMPTS_DIR` when present; otherwise use `src/prompts_compact` when `POMA_PROMPT_PROFILE=compact`, else `src/prompts`.

- [ ] **Step 4: Add prompt-loader cache reset**

In `src/services/prompt_loader.py`, add:

```python
def reset_prompt_cache() -> None:
    _cache.clear()
```

Export remains optional because tests import from the module directly.

- [ ] **Step 5: Run focused tests**

Run: `python -m pytest tests/services/test_prompt_profiles.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src/config/settings.py src/services/prompt_loader.py tests/services/test_prompt_profiles.py
git commit -m "feat: add prompt profile configuration"
```

---

### Task 2: Robust JSON Extraction For Local Prompt-Only Output

**Files:**
- Modify: `src/contracts/structured_outputs.py`
- Modify: `src/services/structured_generation.py`
- Modify: `tests/services/test_structured_generation.py`

**Interfaces:**
- Consumes: `StructuredGenerator.generate(prompt, schema, context)`.
- Produces: local-compatible output mode that appends schema instruction and extracts exactly one JSON object from raw/fenced/text-wrapped output.

- [ ] **Step 1: Add failing tests for local model mode and text-wrapped JSON**

Append these tests to `tests/services/test_structured_generation.py`:

```python
def test_local_sea_lion_uses_json_text_extract_mode():
    assert (
        resolve_output_mode("local/sea-lion-v3-8b-it")
        is StructuredOutputMode.JSON_TEXT_EXTRACT
    )
    assert (
        resolve_output_mode("local/aisingapore/Llama-SEA-LION-v3-8B-IT")
        is StructuredOutputMode.JSON_TEXT_EXTRACT
    )


def test_text_wrapped_single_json_object_is_decoded_without_repair():
    generator, transport = _generator(
        [
            (
                'Here is the answer:\\n{"answer": "yes"}\\nDone.',
                {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            )
        ],
        mode_override=StructuredOutputMode.JSON_TEXT_EXTRACT,
    )

    result = generator.generate("Answer.", SIMPLE_SCHEMA, _context("local/sea-lion-v3-8b-it"))

    assert len(transport.calls) == 1
    assert result.data == {"answer": "yes"}
    assert result.repair_attempted is False


def test_ambiguous_multiple_json_objects_repair_once():
    generator, transport = _generator(
        [
            (
                '{"answer": "first"}\\n{"answer": "second"}',
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            ),
            (
                '{"answer": "repaired"}',
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            ),
        ],
        mode_override=StructuredOutputMode.JSON_TEXT_EXTRACT,
    )

    result = generator.generate("Answer.", SIMPLE_SCHEMA, _context("local/sea-lion-v3-8b-it"))

    assert len(transport.calls) == 2
    assert result.data == {"answer": "repaired"}
    assert "multiple JSON objects" in transport.calls[1][0]
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest tests/services/test_structured_generation.py -v`

Expected: FAIL because `JSON_TEXT_EXTRACT` and extraction behavior are missing.

- [ ] **Step 3: Add enum value**

In `src/contracts/structured_outputs.py`, extend `StructuredOutputMode`:

```python
JSON_TEXT_EXTRACT = "json_text_extract"
```

- [ ] **Step 4: Implement exact-one-object extraction**

In `src/services/structured_generation.py`, add a scanner that walks the raw text, tracks string state, escape state, and balanced braces, and returns one object string only when exactly one complete top-level object exists. Use it inside `_decode_and_validate()` for `JSON_TEXT_EXTRACT` mode. Keep raw JSON and fenced JSON behavior unchanged for existing modes.

Use this public internal helper signature:

```python
def _extract_single_json_object(raw_response: str) -> tuple[str | None, str | None]:
    """Return (json_text, error_message)."""
```

Return `(None, "multiple JSON objects found")` when more than one top-level object is found, and `(None, "no JSON object found")` when none is found.

- [ ] **Step 5: Route local models to extraction mode**

Update `resolve_output_mode()`:

```python
normalized = model.removeprefix("openrouter/")
local_normalized = normalized.removeprefix("local/")
if model.startswith("local/") or model.startswith("local:"):
    return StructuredOutputMode.JSON_TEXT_EXTRACT
```

Accept both `local/sea-lion-v3-8b-it` and `local/aisingapore/Llama-SEA-LION-v3-8B-IT`.

- [ ] **Step 6: Apply schema instruction to local prompt-only mode**

Treat `JSON_TEXT_EXTRACT` like `PROMPT_ONLY` for schema instruction appending and repair prompt construction. It must not send `text_format` to the transport.

- [ ] **Step 7: Run focused tests**

Run: `python -m pytest tests/services/test_structured_generation.py tests/contracts/test_structured_outputs.py -v`

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```powershell
git add src/contracts/structured_outputs.py src/services/structured_generation.py tests/services/test_structured_generation.py
git commit -m "feat: support local json text extraction"
```

---

### Task 3: Local Transformers SEA-LION Client

**Files:**
- Create: `src/services/local_transformers_client.py`
- Modify: `src/services/llm_client.py`
- Create: `tests/services/test_local_transformers_client.py`
- Modify: `tests/services/test_llm_client_structured.py`

**Interfaces:**
- Produces: `LocalTransformersClient.generate_with_usage(prompt: str, *, max_new_tokens: int | None = None) -> tuple[str, dict[str, object]]`.
- Consumes: `LLMClient._generate_raw_text(prompt, text_format)`.

- [ ] **Step 1: Write mocked local client tests**

Create `tests/services/test_local_transformers_client.py`:

```python
from types import SimpleNamespace

import pytest

from src.services.local_transformers_client import ContextOverflowError, LocalTransformersClient


class _FakeTokenizer:
    eos_token_id = 2

    def __call__(self, text, return_tensors=None):
        ids = list(range(len(text.split())))
        return {"input_ids": SimpleNamespace(shape=(1, len(ids)), to=lambda device: SimpleNamespace(shape=(1, len(ids))))}

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        assert messages[0]["role"] == "user"
        return messages[0]["content"] + "\nassistant:"

    def decode(self, ids, skip_special_tokens=True):
        return '{"answer": "ok"}'


class _FakeModel:
    device = "cuda"

    def generate(self, **kwargs):
        return [[0, 1, 2]]


def test_generate_with_usage_counts_tokens_and_calls_model():
    client = LocalTransformersClient(
        tokenizer=_FakeTokenizer(),
        model=_FakeModel(),
        model_id="local/sea-lion-v3-8b-it",
        max_input_tokens=10,
        default_max_new_tokens=4,
    )

    text, usage = client.generate_with_usage("one two")

    assert text == '{"answer": "ok"}'
    assert usage["prompt_tokens"] == 3
    assert usage["completion_tokens"] >= 1
    assert usage["cost_usd"] is None
    assert usage["model"] == "local/sea-lion-v3-8b-it"
    assert usage["quantization"] == "nf4"


def test_context_overflow_raises_before_generation():
    client = LocalTransformersClient(
        tokenizer=_FakeTokenizer(),
        model=_FakeModel(),
        model_id="local/sea-lion-v3-8b-it",
        max_input_tokens=2,
        default_max_new_tokens=4,
    )

    with pytest.raises(ContextOverflowError, match="max_input_tokens=2"):
        client.generate_with_usage("one two three")
```

- [ ] **Step 2: Add failing `LLMClient` routing test**

In `tests/services/test_llm_client_structured.py`, add a test that monkeypatches a fake local client into `src.services.llm_client` and verifies `POMA_LLM_MODEL=local/sea-lion-v3-8b-it` calls local generation and does not pass OpenRouter `text_format`.

- [ ] **Step 3: Run tests and verify failure**

Run: `python -m pytest tests/services/test_local_transformers_client.py tests/services/test_llm_client_structured.py -v`

Expected: FAIL because the module and local routing are missing.

- [ ] **Step 4: Implement `LocalTransformersClient`**

Create `src/services/local_transformers_client.py` with:

```python
class ContextOverflowError(RuntimeError):
    pass


class LocalTransformersClient:
    @classmethod
    def from_pretrained(cls, config: LocalModelConfig) -> "LocalTransformersClient":
        ...

    def generate_with_usage(
        self,
        prompt: str,
        *,
        max_new_tokens: int | None = None,
    ) -> tuple[str, dict[str, object]]:
        ...

    def count_tokens(self, text: str) -> int:
        ...

    def shutdown(self) -> None:
        ...
```

`from_pretrained()` imports `torch`, `BitsAndBytesConfig`, `AutoModelForCausalLM`, and `AutoTokenizer` lazily. Configure:

```python
BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)
```

Use `device_map="auto"`, `trust_remote_code=True`, and `torch_dtype=torch.float16`. Build chat text with `tokenizer.apply_chat_template()` when available, otherwise use the raw prompt. Count input tokens after chat-template formatting. Raise `ContextOverflowError` before `model.generate()` if input tokens exceed `max_input_tokens`.

- [ ] **Step 5: Route local models inside `LLMClient`**

In `src/services/llm_client.py`, add a lazy shared local client and branch in `_generate_raw_text()`:

```python
if self._cfg.model.startswith(("local/", "local:")):
    if text_format is not None:
        raise ValueError("Local Transformers generation does not accept server-side text_format")
    return _get_shared_local_client(self._cfg.local_model).generate_with_usage(
        prompt,
        max_new_tokens=self._cfg.max_tokens,
    )
```

Preserve current `_client.generate_with_usage()` path for non-local models.

- [ ] **Step 6: Run focused tests**

Run: `python -m pytest tests/services/test_local_transformers_client.py tests/services/test_llm_client_structured.py tests/services/test_structured_generation.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add src/services/local_transformers_client.py src/services/llm_client.py tests/services/test_local_transformers_client.py tests/services/test_llm_client_structured.py
git commit -m "feat: add local sea lion llm client"
```

---

### Task 4: Table Preview And HintPredictor Integration

**Files:**
- Create: `src/kaggle_eval/__init__.py`
- Create: `src/kaggle_eval/table_preview.py`
- Modify: `src/orchestration/pipeline.py`
- Create: `tests/kaggle_eval/test_table_preview.py`
- Modify: `tests/agents/test_structured_agents.py`

**Interfaces:**
- Produces: `build_table_preview(table_flattened: str, *, tokenizer: TokenCounter | None = None, max_tokens: int = 1024) -> str`.
- Consumes: `HintPredictorAgent.run(question: str, table_flattened: str)`.

- [ ] **Step 1: Write preview tests**

Create `tests/kaggle_eval/test_table_preview.py`:

```python
from src.kaggle_eval.table_preview import build_table_preview


class _WordTokenizer:
    def encode(self, text):
        return text.split()


def test_short_table_is_returned_unchanged():
    table = "TITLE: Demo\nHEADER: a | b\nrow 1: x | y"
    assert build_table_preview(table, tokenizer=_WordTokenizer(), max_tokens=100) == table


def test_long_preview_keeps_title_header_whole_rows_and_omission_marker():
    rows = "\n".join(f"row {i}: c1={i} | c2=value-{i}" for i in range(1, 31))
    table = "TITLE: Demo\nHEADER: c1 | c2\n" + rows

    preview = build_table_preview(table, tokenizer=_WordTokenizer(), max_tokens=90)

    assert "TITLE: Demo" in preview
    assert "HEADER: c1 | c2" in preview
    assert "row 1:" in preview
    assert "row 30:" in preview
    assert "OMITTED_ROWS" in preview
    assert "\nrow " in preview
    assert len(_WordTokenizer().encode(preview)) <= 90
```

- [ ] **Step 2: Write pipeline integration test**

Add a test to `tests/agents/test_structured_agents.py` or a new pipeline test that monkeypatches `HintPredictorAgent.run`, enables `POMA_USE_AGENT_HINTS=true`, and asserts the value passed to HintPredictor contains the omission marker while the specialist still receives the full table. Use a fake table string with many rows and fake agents so no LLM call occurs.

- [ ] **Step 3: Run tests and verify failure**

Run: `python -m pytest tests/kaggle_eval/test_table_preview.py tests/agents/test_structured_agents.py -v`

Expected: FAIL because preview helper and pipeline hook are missing.

- [ ] **Step 4: Implement preview builder**

In `src/kaggle_eval/table_preview.py`, implement:

```python
class TokenCounter(Protocol):
    def encode(self, text: str) -> list[int] | list[str]:
        ...


def build_table_preview(
    table_flattened: str,
    *,
    tokenizer: TokenCounter | None = None,
    max_tokens: int = 1024,
) -> str:
    ...
```

Split lines, preserve title/header-like lines first, then sample whole rows from start, middle, and end. After each candidate preview, count tokens with `tokenizer.encode(text)` when supplied; otherwise use `text.split()` as a deterministic test fallback. Insert a line like:

```text
[OMITTED_ROWS: 12 rows not shown between sampled sections]
```

If the title/header alone exceed the budget, return the largest line-prefix set that fits and include `[PREVIEW_TRUNCATED_BEFORE_ROWS]`.

- [ ] **Step 5: Pass preview only to HintPredictor**

In `src/orchestration/pipeline.py`, when `settings.use_agent_hints` is true, call:

```python
from src.kaggle_eval.table_preview import build_table_preview

hint_table = build_table_preview(
    request.table_flattened,
    max_tokens=getattr(settings.local_model, "hint_preview_tokens", 1024),
)
active_hints = predictor.run(question=request.question, table_flattened=hint_table)
```

Leave specialist calls unchanged with `request.table_flattened`.

- [ ] **Step 6: Run focused tests**

Run: `python -m pytest tests/kaggle_eval/test_table_preview.py tests/agents/test_structured_agents.py tests/test_run_poma_artifacts.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add src/kaggle_eval/__init__.py src/kaggle_eval/table_preview.py src/orchestration/pipeline.py tests/kaggle_eval/test_table_preview.py tests/agents/test_structured_agents.py
git commit -m "feat: add table preview for agent hints"
```

---

### Task 5: Compact Prompt Profile

**Files:**
- Create: `src/prompts_compact/hint_predictor.md`
- Create: `src/prompts_compact/question_refiner.md`
- Create: `src/prompts_compact/grounded_single_answer.md`
- Create: `src/prompts_compact/answer_normalization.md`
- Create: `src/prompts_compact/specialists/what.md`
- Create: `src/prompts_compact/specialists/who.md`
- Create: `src/prompts_compact/specialists/when.md`
- Create: `src/prompts_compact/specialists/where.md`
- Create: `src/prompts_compact/specialists/yesno.md`
- Create: `src/prompts_compact/specialists/list.md`
- Create: `src/prompts_compact/specialists/why.md`
- Create: `src/prompts_compact/specialists/how.md`
- Create: `src/prompts_compact/specialists/multi_conditions.md`
- Create: `src/prompts_compact/specialists/mathematical_reasoning.md`
- Create: `src/prompts_compact/answer_normalization/what.md`
- Create: `src/prompts_compact/answer_normalization/who.md`
- Create: `src/prompts_compact/answer_normalization/when.md`
- Create: `src/prompts_compact/answer_normalization/where.md`
- Create: `src/prompts_compact/answer_normalization/yesno.md`
- Create: `src/prompts_compact/answer_normalization/list.md`
- Create: `src/prompts_compact/answer_normalization/why.md`
- Create: `src/prompts_compact/answer_normalization/how.md`
- Create: `src/prompts_compact/answer_normalization/multi_conditions.md`
- Create: `src/prompts_compact/answer_normalization/mathematical_reasoning.md`
- Create: `tests/services/test_compact_prompts.py`

**Interfaces:**
- Consumes: unchanged prompt template variables used by agents.
- Produces: complete compact prompt tree selected by `POMA_PROMPT_PROFILE=compact`.

- [ ] **Step 1: Write prompt completeness tests**

Create `tests/services/test_compact_prompts.py`:

```python
from pathlib import Path


REQUIRED = [
    "hint_predictor.md",
    "question_refiner.md",
    "grounded_single_answer.md",
    "answer_normalization.md",
    "specialists/what.md",
    "specialists/who.md",
    "specialists/when.md",
    "specialists/where.md",
    "specialists/yesno.md",
    "specialists/list.md",
    "specialists/why.md",
    "specialists/how.md",
    "specialists/multi_conditions.md",
    "specialists/mathematical_reasoning.md",
    "answer_normalization/what.md",
    "answer_normalization/who.md",
    "answer_normalization/when.md",
    "answer_normalization/where.md",
    "answer_normalization/yesno.md",
    "answer_normalization/list.md",
    "answer_normalization/why.md",
    "answer_normalization/how.md",
    "answer_normalization/multi_conditions.md",
    "answer_normalization/mathematical_reasoning.md",
]


def test_compact_prompt_tree_is_complete():
    root = Path("src/prompts_compact")
    missing = [name for name in REQUIRED if not (root / name).exists()]
    assert missing == []


def test_compact_prompts_are_json_only_and_do_not_ask_for_cot():
    root = Path("src/prompts_compact")
    for path in (root).rglob("*.md"):
        text = path.read_text(encoding="utf-8").lower()
        assert "json" in text
        assert "chain-of-thought" not in text
        assert "step by step" not in text
        assert "giải thích từng bước" not in text


def test_simple_specialists_have_no_examples():
    root = Path("src/prompts_compact/specialists")
    for name in ["what", "who", "when", "where", "yesno", "list"]:
        text = (root / f"{name}.md").read_text(encoding="utf-8").lower()
        assert "example" not in text
        assert "ví dụ" not in text


def test_complex_specialists_have_two_short_examples():
    root = Path("src/prompts_compact/specialists")
    for name in ["why", "how", "multi_conditions", "mathematical_reasoning"]:
        text = (root / f"{name}.md").read_text(encoding="utf-8")
        assert text.count("EXAMPLE ") == 2
        assert "Null" in text
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest tests/services/test_compact_prompts.py -v`

Expected: FAIL because `src/prompts_compact` does not exist.

- [ ] **Step 3: Create compact prompt files**

Create each prompt with the same template variables as its default counterpart. Use this schema text pattern in every specialist:

```text
Return exactly one JSON object:
{"answer": string_or_null, "evidence": ["short table quote"], "confidence": number_0_to_1, "reason": "short reason"}
```

For simple specialists, include rules only. For complex specialists, include exactly:

```text
EXAMPLE 1:
Input: ...
Output: {"answer": "...", "evidence": ["..."], "confidence": 0.8, "reason": "..."}

EXAMPLE 2:
Input: ...
Output: {"answer": null, "evidence": [], "confidence": 0.0, "reason": "Không có đủ bằng chứng trong bảng."}
```

Do not include chain-of-thought instructions. Keep the prompts concise and Vietnamese-friendly.

- [ ] **Step 4: Run prompt tests**

Run: `python -m pytest tests/services/test_compact_prompts.py tests/services/test_prompt_profiles.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/prompts_compact tests/services/test_compact_prompts.py
git commit -m "feat: add compact poma prompt profile"
```

---

### Task 6: Deterministic ID Selection

**Files:**
- Create: `src/kaggle_eval/selection.py`
- Create: `tests/kaggle_eval/test_selection.py`

**Interfaces:**
- Produces: `select_pilot_qas(qas, tables, *, n=200, seed=42) -> list[dict]`, `load_final_543_ids(path: Path | None = None) -> list[str]`.
- Consumes: QAs records with `qa_id`, `table_id`, `hints`; table records rendered through existing preprocessing when table length is needed.

- [ ] **Step 1: Write deterministic selection tests**

Create `tests/kaggle_eval/test_selection.py`:

```python
from src.kaggle_eval.selection import select_pilot_qas, table_length_bucket


def _qa(i, hint, table_id):
    return {"qa_id": str(i), "hints": [hint], "table_id": table_id, "question": f"q{i}", "answer": "a"}


def test_table_length_bucket_boundaries():
    assert table_length_bucket(99) == "short"
    assert table_length_bucket(1000) == "medium"
    assert table_length_bucket(5000) == "long"


def test_select_pilot_qas_is_seeded_and_unique():
    qas = [_qa(i, "What" if i % 2 else "Who", f"t{i % 4}") for i in range(40)]
    table_token_counts = {f"t{i}": i * 1500 for i in range(4)}

    first = select_pilot_qas(qas, table_token_counts=table_token_counts, n=12, seed=42)
    second = select_pilot_qas(qas, table_token_counts=table_token_counts, n=12, seed=42)

    assert [qa["qa_id"] for qa in first] == [qa["qa_id"] for qa in second]
    assert len({qa["qa_id"] for qa in first}) == 12
    assert {"What", "Who"} <= {qa["hints"][0] for qa in first}
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest tests/kaggle_eval/test_selection.py -v`

Expected: FAIL because selection module is missing.

- [ ] **Step 3: Implement selection**

Implement deterministic grouping by `(primary_hint, table_length_bucket)`. Shuffle each group with `random.Random(seed)`, round-robin groups until `n` items are selected, then sort selected items by original dataset order for stable execution. If there are fewer than `n` records, raise `ValueError`.

Use bucket thresholds:

```python
short: token_count < 1000
medium: 1000 <= token_count < 4000
long: token_count >= 4000
```

- [ ] **Step 4: Add final ID source**

Implement `load_final_543_ids(path=None)`. When `path` is provided, load a JSON list or `{"qa_ids": [...]}`. When `path` is not provided, derive the IDs from the existing 543 comparison artifact if present under `outputs/q2_revision/openrouter_google_gemma-3-4b-it/full/reports/poma_vs_zero_shot_543.json`; otherwise raise a message that tells the caller to pass `FINAL_IDS_PATH`.

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/kaggle_eval/test_selection.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src/kaggle_eval/selection.py tests/kaggle_eval/test_selection.py
git commit -m "feat: add deterministic kaggle qa selection"
```

---

### Task 7: JSONL Resume Helpers

**Files:**
- Create: `src/kaggle_eval/jsonl_io.py`
- Create: `tests/kaggle_eval/test_jsonl_io.py`

**Interfaces:**
- Produces: `append_jsonl(path: Path, record: Mapping[str, Any]) -> None`, `load_jsonl(path: Path) -> list[dict[str, Any]]`, `completed_qa_ids(predictions_path: Path, errors_path: Path) -> set[str]`.
- Consumes: runner records with `qa_id`; terminal error records with `terminal: true`.

- [ ] **Step 1: Write resume tests**

Create `tests/kaggle_eval/test_jsonl_io.py`:

```python
from pathlib import Path

from src.kaggle_eval.jsonl_io import append_jsonl, completed_qa_ids, load_jsonl


def test_append_and_load_jsonl(tmp_path):
    path = tmp_path / "predictions.jsonl"
    append_jsonl(path, {"qa_id": "1", "prediction": ["A"]})
    append_jsonl(path, {"qa_id": "2", "prediction": ["B"]})

    assert load_jsonl(path) == [
        {"qa_id": "1", "prediction": ["A"]},
        {"qa_id": "2", "prediction": ["B"]},
    ]


def test_completed_ids_include_predictions_and_terminal_errors(tmp_path):
    predictions = tmp_path / "predictions.jsonl"
    errors = tmp_path / "errors.jsonl"
    append_jsonl(predictions, {"qa_id": "done", "prediction": ["A"]})
    append_jsonl(errors, {"qa_id": "terminal", "terminal": True, "error_type": "context_overflow"})
    append_jsonl(errors, {"qa_id": "retryable", "terminal": False, "error_type": "network"})

    assert completed_qa_ids(predictions, errors) == {"done", "terminal"}
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest tests/kaggle_eval/test_jsonl_io.py -v`

Expected: FAIL because JSONL helpers are missing.

- [ ] **Step 3: Implement JSONL helpers**

Use `json.dumps(record, ensure_ascii=False)` and append newline under a module-level lock. `load_jsonl()` should ignore blank lines and raise `ValueError` with file path and line number for malformed JSON. `completed_qa_ids()` should include all prediction records with a non-empty `qa_id` and error records where `terminal is True`.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/kaggle_eval/test_jsonl_io.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/kaggle_eval/jsonl_io.py tests/kaggle_eval/test_jsonl_io.py
git commit -m "feat: add resumable jsonl helpers"
```

---

### Task 8: Kaggle Runner For Zero-Shot And POMA

**Files:**
- Create: `src/kaggle_eval/runner.py`
- Create: `scripts/run_sea_lion_kaggle_eval.py`
- Create: `tests/scripts/test_run_sea_lion_kaggle_eval.py`
- Modify: `baseline/prompts.py` only if compact zero-shot prompt needs a named style.

**Interfaces:**
- Produces: `RunConfig`, `prepare_run_dirs()`, `run_zero_shot()`, `run_poma()`, and CLI arguments for smoke/pilot/final.
- Consumes: `LocalTransformersClient`, `StructuredGenerator`, `run_pipeline`, `baseline.prompts.build_tableqa_prompt`, `load_dataset_pair`.

- [ ] **Step 1: Write CLI config tests without model load**

Create `tests/scripts/test_run_sea_lion_kaggle_eval.py`:

```python
from pathlib import Path

from scripts.run_sea_lion_kaggle_eval import build_parser, resolve_repo_root


def test_parser_defaults_to_pilot_mode():
    args = build_parser().parse_args(["--repo-root", ".", "--output-root", "out"])

    assert args.phase == "pilot"
    assert args.limit is None
    assert args.model == "local/sea-lion-v3-8b-it"


def test_resolve_repo_root_dataset_mode(tmp_path):
    repo = tmp_path / "POMA"
    (repo / "dataset").mkdir(parents=True)
    (repo / "dataset" / "qas_dev.json").write_text('{"qas":[]}', encoding="utf-8")
    (repo / "dataset" / "qas_test.json").write_text('{"qas":[]}', encoding="utf-8")
    (repo / "dataset" / "table.json").write_text('{"table":[]}', encoding="utf-8")

    assert resolve_repo_root(repo) == repo
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest tests/scripts/test_run_sea_lion_kaggle_eval.py -v`

Expected: FAIL because runner script is missing.

- [ ] **Step 3: Implement `RunConfig`**

In `src/kaggle_eval/runner.py`, define:

```python
@dataclass(frozen=True)
class RunConfig:
    repo_root: Path
    output_root: Path
    phase: Literal["smoke", "pilot", "final"]
    mode: Literal["zero_shot", "poma", "both"]
    model: str = "local/sea-lion-v3-8b-it"
    prompt_profile: str = "compact"
    seed: int = 42
    pilot_n: int = 200
    limit: int | None = None
    final_ids_path: Path | None = None
```

- [ ] **Step 4: Implement run directories**

Create run directories:

```text
{output_root}/sea_lion_v3_8b_it/{phase}/zero_shot/
{output_root}/sea_lion_v3_8b_it/{phase}/poma/
```

Each directory contains `selected_ids.json`, `predictions.jsonl`, `traces.jsonl`, `errors.jsonl`, `metrics.json`, and `comparison.json` as applicable.

- [ ] **Step 5: Implement zero-shot local runner**

Use `baseline.prompts.build_tableqa_prompt()` with `prompt_style="zero_shot"` or a new `sea_lion_zero_shot_compact` style if Task 5 adds one. Use `StructuredGenerator` with schema `baseline_zero_shot.v1` and `CallContext(model=config.model, agent_name="DirectPromptBaseline", prompt_name="zero_shot")`. Append successful records to `predictions.jsonl` and terminal failures to `errors.jsonl`.

- [ ] **Step 6: Implement POMA local runner**

Set environment before importing pipeline-heavy modules:

```python
os.environ["POMA_LLM_MODEL"] = config.model
os.environ["POMA_PROMPT_PROFILE"] = config.prompt_profile
os.environ["POMA_USE_AGENT_HINTS"] = "true"
os.environ["POMA_PARALLEL_WORKERS"] = "1"
```

For each selected QA, call existing `run_poma.process_one()` or `run_pipeline()` with full flattened table. Append prediction and trace separately. Convert `ContextOverflowError` into terminal `errors.jsonl` records with `error_type="context_overflow"`.

- [ ] **Step 7: Implement CLI**

In `scripts/run_sea_lion_kaggle_eval.py`, expose:

```text
--repo-root
--output-root
--phase smoke|pilot|final
--mode zero_shot|poma|both
--limit
--final-ids-path
--model
```

`resolve_repo_root()` validates the three dataset files before model loading.

- [ ] **Step 8: Run focused tests**

Run: `python -m pytest tests/scripts/test_run_sea_lion_kaggle_eval.py tests/kaggle_eval/test_jsonl_io.py tests/kaggle_eval/test_selection.py -v`

Expected: PASS.

- [ ] **Step 9: Commit**

Run:

```powershell
git add src/kaggle_eval/runner.py scripts/run_sea_lion_kaggle_eval.py tests/scripts/test_run_sea_lion_kaggle_eval.py baseline/prompts.py
git commit -m "feat: add sea lion kaggle runner"
```

If `baseline/prompts.py` was not modified, omit it from `git add`.

---

### Task 9: Metrics And Paired Reporting

**Files:**
- Create: `src/kaggle_eval/reporting.py`
- Create: `tests/kaggle_eval/test_reporting.py`

**Interfaces:**
- Produces: `write_run_report(predictions_path, qas_path, output_path, *, tables_path=None) -> dict`, `write_comparison_report(poma_path, zero_path, qas_path, output_path) -> dict`.
- Consumes: `evaluation.run.evaluate_files`, `evaluation.bootstrap.paired_bootstrap_ci`, existing metric sample alignment.

- [ ] **Step 1: Write reporting tests**

Create `tests/kaggle_eval/test_reporting.py`:

```python
import json

from src.kaggle_eval.jsonl_io import append_jsonl
from src.kaggle_eval.reporting import write_comparison_report


def test_write_comparison_report_aligns_same_ids_and_counts_wtl(tmp_path):
    qas = tmp_path / "qas.json"
    qas.write_text(
        json.dumps(
            {
                "qas": [
                    {"qa_id": "1", "answer": "A", "question": "q1", "hints": ["What"]},
                    {"qa_id": "2", "answer": "B", "question": "q2", "hints": ["What"]},
                ]
            }
        ),
        encoding="utf-8",
    )
    poma = tmp_path / "poma.jsonl"
    zero = tmp_path / "zero.jsonl"
    append_jsonl(poma, {"qa_id": "1", "prediction": ["A"]})
    append_jsonl(poma, {"qa_id": "2", "prediction": ["wrong"]})
    append_jsonl(zero, {"qa_id": "1", "prediction": ["wrong"]})
    append_jsonl(zero, {"qa_id": "2", "prediction": ["B"]})

    report = write_comparison_report(poma, zero, qas, tmp_path / "comparison.json")

    assert report["paired"]["count"] == 2
    assert report["win_tie_loss"]["poma_wins"] == 1
    assert report["win_tie_loss"]["zero_wins"] == 1
    assert report["win_tie_loss"]["ties"] == 0
    assert "f1" in report["bootstrap_ci"]
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest tests/kaggle_eval/test_reporting.py -v`

Expected: FAIL because reporting module is missing.

- [ ] **Step 3: Implement single-run report**

Use `evaluate_files()` for EM, F1, ROUGE-1, and METEOR with `candidate_policy="first"` for primary POMA scoring. Add `json_compliance` fields by scanning `schema_valid`, `repair_attempted`, `repair_succeeded`, and error records when supplied.

- [ ] **Step 4: Implement paired report**

Load and align POMA, zero-shot, and QAs by exact same QA IDs. Compute per-sample F1/EM/ROUGE-1/METEOR using existing metric functions, win/tie/loss on F1, and `paired_bootstrap_ci()` for each metric with `samples=10000` and existing default seed.

- [ ] **Step 5: Write JSON outputs**

Write `metrics.json` and `comparison.json` with UTF-8, `ensure_ascii=False`, and indentation. Include input paths and selected ID count.

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/kaggle_eval/test_reporting.py tests/evaluation/test_bootstrap.py tests/evaluation/test_run.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```powershell
git add src/kaggle_eval/reporting.py tests/kaggle_eval/test_reporting.py
git commit -m "feat: add paired sea lion reporting"
```

---

### Task 10: Kaggle Notebook

**Files:**
- Create: `notebooks/kaggle_sea_lion_poma.ipynb`
- Create: `tests/notebooks/test_kaggle_sea_lion_poma_notebook.py`

**Interfaces:**
- Consumes: `scripts/run_sea_lion_kaggle_eval.py`.
- Produces: user-facing Kaggle notebook for smoke, pilot, and optional final run.

- [ ] **Step 1: Write notebook validity test**

Create `tests/notebooks/test_kaggle_sea_lion_poma_notebook.py`:

```python
import json
from pathlib import Path


def test_kaggle_notebook_is_valid_json_and_has_required_config_cells():
    path = Path("notebooks/kaggle_sea_lion_poma.ipynb")
    data = json.loads(path.read_text(encoding="utf-8"))
    sources = "\n".join("".join(cell.get("source", [])) for cell in data["cells"])

    assert data["nbformat"] == 4
    assert "MODEL_ID = \"aisingapore/Llama-SEA-LION-v3-8B-IT\"" in sources
    assert "RUN_FINAL_543 = False" in sources
    assert "POMA_PROMPT_PROFILE" in sources
    assert "run_sea_lion_kaggle_eval.py" in sources
    assert "/kaggle/working" in sources
```

- [ ] **Step 2: Run test and verify failure**

Run: `python -m pytest tests/notebooks/test_kaggle_sea_lion_poma_notebook.py -v`

Expected: FAIL because notebook is missing.

- [ ] **Step 3: Create notebook**

Create a valid nbformat 4 notebook with these cells:

1. Title and experiment assumptions.
2. Dependency install:

```python
%pip install -q "transformers>=4.43" "accelerate>=0.33" "bitsandbytes>=0.43" "jsonschema>=4.0" rouge-score nltk
```

3. Config:

```python
MODEL_ID = "aisingapore/Llama-SEA-LION-v3-8B-IT"
SOURCE_MODE = "dataset"
KAGGLE_REPO_ROOT = "/kaggle/input/poma-repo/POMA"
REPO_URL = "https://github.com/NgDinhKhoi0709/POMA.git"
REVISION = "main"
OUTPUT_ROOT = "/kaggle/working/poma_sea_lion"
RUN_FINAL_543 = False
FINAL_IDS_PATH = None
```

4. Repo setup and dataset-file validation.
5. Environment setup:

```python
import os
os.environ["POMA_LLM_MODEL"] = "local/sea-lion-v3-8b-it"
os.environ["POMA_LOCAL_MODEL_ID"] = MODEL_ID
os.environ["POMA_PROMPT_PROFILE"] = "compact"
os.environ["POMA_USE_AGENT_HINTS"] = "true"
os.environ["POMA_PARALLEL_WORKERS"] = "1"
os.environ["POMA_LOCAL_MAX_MODEL_LEN"] = "32768"
os.environ["POMA_LOCAL_MAX_INPUT_TOKENS"] = "28672"
```

6. Smoke run with `--phase smoke --mode both --limit 5`.
7. Pilot run with `--phase pilot --mode both`.
8. Pilot reporting and display.
9. Final run guarded by:

```python
if RUN_FINAL_543:
    ...
else:
    print("Final 543 run is disabled. Set RUN_FINAL_543 = True after reviewing pilot metrics.")
```

10. Final reporting and output path summary.

- [ ] **Step 4: Validate notebook JSON**

Run: `python -m pytest tests/notebooks/test_kaggle_sea_lion_poma_notebook.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add notebooks/kaggle_sea_lion_poma.ipynb tests/notebooks/test_kaggle_sea_lion_poma_notebook.py
git commit -m "docs: add sea lion kaggle notebook"
```

---

### Task 11: End-To-End Offline Verification

**Files:**
- Modify: none unless tests reveal a defect in files from prior tasks.

**Interfaces:**
- Consumes: all new modules and existing repo tests.
- Produces: verification evidence before handoff.

- [ ] **Step 1: Run focused new test suite**

Run:

```powershell
python -m pytest tests/services/test_prompt_profiles.py tests/services/test_compact_prompts.py tests/services/test_local_transformers_client.py tests/kaggle_eval tests/scripts/test_run_sea_lion_kaggle_eval.py tests/notebooks/test_kaggle_sea_lion_poma_notebook.py -v
```

Expected: PASS.

- [ ] **Step 2: Run relevant existing tests**

Run:

```powershell
python -m pytest tests/services/test_structured_generation.py tests/services/test_llm_client_structured.py tests/agents/test_structured_agents.py tests/test_run_poma_artifacts.py tests/evaluation/test_run.py tests/evaluation/test_bootstrap.py tests/baselines/test_run_baseline_cli.py -v
```

Expected: PASS.

- [ ] **Step 3: Run full suite if time permits**

Run:

```powershell
python -m pytest
```

Expected: PASS. If an unrelated dirty-worktree failure appears, record the failing test name, error summary, and why it is unrelated before handoff.

- [ ] **Step 4: Check git status**

Run:

```powershell
git status --short
```

Expected: only intended source, prompt, test, notebook, and docs changes from these tasks remain uncommitted if the execution mode skips commits; no generated `/outputs/` files are staged.

- [ ] **Step 5: Final handoff**

Report:

- Plan tasks completed.
- Verification commands and results.
- Notebook path.
- Any Kaggle-only verification that could not be run locally because no GPU/model cache is available.

---

## Self-Review

Spec coverage:

- Local SEA-LION runtime is covered by Tasks 1, 2, and 3.
- Compact shared prompts are covered by Task 5.
- HintPredictor table preview is covered by Task 4.
- JSON validation and one-repair policy are covered by Task 2 and Task 3.
- Resume-friendly JSONL outputs are covered by Task 7 and Task 8.
- Pilot and final selection are covered by Task 6 and Task 8.
- Paired metrics and diagnostics are covered by Task 9.
- Kaggle notebook is covered by Task 10.
- Offline verification is covered by Task 11.

Open-blank scan:

- The plan avoids open blanks and gives concrete files, interfaces, commands, and expected outcomes for each task.

Type consistency:

- `LocalTransformersClient.generate_with_usage()` returns the tuple shape expected by `LLMClient._generate_raw_text()`.
- `build_table_preview()` consumes a flattened table string and returns a string, matching `HintPredictorAgent.run()`.
- `RunConfig` fields are the same names used by the script and notebook cells.
- `write_comparison_report()` consumes paths to JSONL prediction files and writes the `comparison.json` expected by run directories.
