# Grounded Single Answer and Structured Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add repository-wide structured output for POMA-owned LLM calls, a table-grounded single-answer finalizer, symmetric offline finalization, candidate-policy-aware evaluation, and reproducible Q2 experiment analysis.

**Architecture:** A deep `StructuredGenerator` module owns OpenRouter format selection, local JSON Schema validation, one repair attempt, telemetry, and typed failures. POMA agents and direct-prompt baselines declare versioned schemas and share this module; native AN, common AN, and GSA sit behind one finalizer seam and run offline from immutable raw artifacts.

**Tech Stack:** Python 3.9+, dataclasses, `jsonschema`, OpenRouter Responses API, `pytest`, JSON/JSONL, PowerShell runbooks.

## Global Constraints

- Use the existing Conda environment `kltn`; do not create another virtual environment.
- Preserve the existing `AnswerNormalizationAgent` behavior for `AN-native`.
- GSA receives only question, Flatten V1 table, and ordered `{source_name, answer}` candidates.
- GSA never receives gold answers, hints, refiner targets, specialist evidence, confidence, or rationale.
- All POMA-owned LLM calls use structured output; vendored CoAgt and Chain-of-Query protocols remain unchanged.
- Gemma 3 4B uses strict JSON Schema; Qwen3-8B uses JSON-object mode plus the same local validator.
- Structured generation allows exactly one semantic repair attempt and never silently changes model, provider, answer, or denominator.
- New prediction artifacts use `prediction`; readers remain compatible with legacy `predicted_answer`.
- Implementation verification may use fake transports and a user-approved 3-5 item live preflight. Do not launch full 992-instance paid runs as part of implementation.
- Preserve unrelated tracked and untracked user changes.

---

## File Map

### New structured-output files

- `src/contracts/structured_outputs.py`: response-schema registry and structured-generation contracts.
- `src/services/structured_generation.py`: validation, capability policy, repair, and telemetry.
- `tests/contracts/test_structured_outputs.py`: schema registry and domain-validation tests.
- `tests/services/test_structured_generation.py`: transport-mode, validation, repair, and telemetry tests.
- `tests/services/test_openrouter_structured_transport.py`: exact OpenRouter request-body tests.
- `tests/services/test_openai_structured_transport.py`: existing OpenAI-provider compatibility tests.

### New GSA and finalization files

- `src/contracts/finalization.py`: candidate, request, decision, and result contracts.
- `src/agents/grounded_single_answer.py`: GSA prompt invocation and semantic validation.
- `src/prompts/grounded_single_answer.md`: table-grounded synthesis prompt.
- `src/finalization/__init__.py`: public finalization exports.
- `src/finalization/finalizers.py`: native AN, common AN, and GSA adapters.
- `src/finalization/sources.py`: POMA-trace and direct-baseline source adapters.
- `src/finalization/artifacts.py`: fingerprints, manifest creation, JSONL resume, and JSON materialization.
- `scripts/run_finalizer.py`: offline/resumable finalizer CLI.
- `tests/agents/test_grounded_single_answer.py`: GSA contract tests.
- `tests/finalization/test_finalizers.py`: finalizer symmetry tests.
- `tests/finalization/test_sources.py`: source-adapter tests.
- `tests/finalization/test_artifacts.py`: resume and fingerprint tests.
- `tests/finalization/test_run_finalizer_cli.py`: end-to-end fake-LLM CLI tests.

### Modified generation files

- `baseline/llm_client.py`: OpenRouter Responses structured-format and provider-requirement support.
- `src/services/llm_client.py`: use `StructuredGenerator` for JSON calls and expose structured telemetry.
- `src/agents/base_agent.py`: require each JSON agent to declare its response schema.
- `src/agents/hint_predictor.py`: use `hint_predictor.v1`.
- `src/agents/question_refiner.py`: use `question_refiner.v1`.
- `src/agents/specialists/_base_specialist.py`: use `specialist.v1`.
- `src/agents/answer_normalization.py`: use `answer_normalization.v1` without changing native AN semantics.
- `baseline/prompts.py`: versioned per-style structured baseline prompts.
- `baseline/run.py`: schema selection and structured result persistence.
- `baseline/model_output_parse.py`: retain legacy reader only; stop using heuristic parsing in new runs.
- `run_baseline.py`: structured-output options and canonical artifact writing.
- `run_poma.py`: canonical predictions, capability preflight metadata, and trace-safe resume.
- `src/contracts/trace.py`: structured-output telemetry in call traces.
- `README.md`: dependency and new CLI documentation.

### Modified evaluation and analysis files

- `evaluation/io.py`: canonical/legacy candidate loading and candidate-policy application.
- `evaluation/run.py`: candidate-policy enforcement and K statistics.
- `run_eval.py`: `--candidate-policy`.
- `evaluation/bootstrap.py`: paired bootstrap confidence intervals.
- `evaluation/hint_metrics.py`: multilabel hint metrics.
- `evaluation/parallelism.py`: routed-specialist distribution.
- `scripts/run_revision_analysis.py`: one reproducible analysis entry point.
- `scripts/run_q2_experiments.ps1`: explicit preflight and full-matrix command runbook.
- `tests/evaluation/test_io.py`: candidate loading and policies.
- `tests/evaluation/test_run.py`: report and K-statistic tests.
- `tests/evaluation/test_bootstrap.py`: deterministic paired-CI tests.
- `tests/evaluation/test_hint_metrics.py`: exact-set and per-label metric tests.
- `tests/evaluation/test_parallelism.py`: specialist-count tests.
- `tests/scripts/test_revision_analysis.py`: analysis report integration test.

---

### Task 1: Define the Structured-Output Contracts and Schema Registry

**Files:**
- Create: `src/contracts/structured_outputs.py`
- Create: `tests/contracts/test_structured_outputs.py`
- Modify: `src/contracts/__init__.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: standard-library dataclasses and JSON-compatible dictionaries.
- Produces: `ResponseSchema`, `CallContext`, `StructuredOutputMode`, `StructuredResult`, `schema_for_call(name: str) -> ResponseSchema`, and `validate_domain_payload(name: str, data: dict[str, Any]) -> None`.

- [ ] **Step 1: Add `jsonschema` to the documented install command**

Change the README dependency command to include `jsonschema`:

```powershell
python -m pip install openai requests beautifulsoup4 python-dotenv pytest jsonschema
```

- [ ] **Step 2: Write failing registry tests**

Create tests that assert:

```python
def test_schema_registry_contains_every_poma_owned_call():
    assert set(STRUCTURED_SCHEMAS) == {
        "hint_predictor.v1",
        "question_refiner.v1",
        "specialist.v1",
        "answer_normalization.v1",
        "gsa.v1",
        "baseline_zero_shot.v1",
        "baseline_few_shot.v1",
        "baseline_cot.v1",
        "baseline_task_decomposition.v1",
    }


def test_all_schemas_are_closed_objects():
    for response_schema in STRUCTURED_SCHEMAS.values():
        assert response_schema.json_schema["type"] == "object"
        assert response_schema.json_schema["additionalProperties"] is False
```

Add focused tests for required fields and enums, including all four GSA
decisions and the CoT/TD reasoning fields.

- [ ] **Step 3: Run the contract tests and verify RED**

Run:

```powershell
conda run -n kltn python -m pytest tests/contracts/test_structured_outputs.py -q
```

Expected: collection fails because `src.contracts.structured_outputs` does not
exist.

- [ ] **Step 4: Implement immutable contracts and all nine schemas**

Use this public shape:

```python
@dataclass(frozen=True)
class ResponseSchema:
    name: str
    version: str
    json_schema: dict[str, Any]


@dataclass(frozen=True)
class CallContext:
    qa_id: str | None
    agent_name: str
    prompt_name: str
    model: str


class StructuredOutputMode(str, Enum):
    STRICT_JSON_SCHEMA = "strict_json_schema"
    JSON_OBJECT = "json_object"


@dataclass(frozen=True)
class StructuredResult:
    data: dict[str, Any]
    raw_response: str
    schema_name: str
    schema_valid: bool
    repair_attempted: bool
    repair_succeeded: bool
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
```

`schema_valid` records whether the initial generation passed both validation
layers. A successfully repaired result therefore has `schema_valid=False`,
`repair_attempted=True`, and `repair_succeeded=True`; this makes the reported
schema-valid rate informative rather than trivially 100% among successes.

Define schemas with `additionalProperties: false`. Use `oneOf` for nullable
specialist answers and refiner targets. Define GSA `decision` with the exact
enum `selected`, `corrected`, `synthesized`, `null`.

- [ ] **Step 5: Add semantic validators**

Implement validators for invariants not expressible cleanly in the shared JSON
Schema:

```python
def validate_domain_payload(name: str, data: dict[str, Any]) -> None:
    if name == "gsa.v1":
        decision = data["decision"]
        answer = data["final_answer"].strip()
        evidence = data["supporting_evidence"]
        if not answer:
            raise StructuredContractError("gsa final_answer must be non-empty")
        if decision == "null" and answer.lower() != "null":
            raise StructuredContractError("null decision requires final_answer=Null")
        if decision != "null" and not evidence:
            raise StructuredContractError("non-null GSA decisions require evidence")
```

Add equally explicit non-empty-list checks for predicted hints, AN answers, and
task-decomposition subproblems.

- [ ] **Step 6: Run contract tests and full baseline tests**

Run:

```powershell
conda run -n kltn python -m pytest tests/contracts/test_structured_outputs.py tests/baselines -q
```

Expected: PASS.

- [ ] **Step 7: Commit the contract slice**

```powershell
git add README.md src/contracts/__init__.py src/contracts/structured_outputs.py tests/contracts/test_structured_outputs.py
git commit -m "feat: define structured output contracts"
```

---

### Task 2: Add Structured Format Support to the LLM Transports

**Files:**
- Modify: `baseline/llm_client.py`
- Create: `tests/services/test_openrouter_structured_transport.py`
- Create: `tests/services/test_openai_structured_transport.py`

**Interfaces:**
- Consumes: `GenConfig.text_format: dict[str, Any] | None` and `GenConfig.require_parameters: bool`.
- Produces: an OpenRouter `/responses` request with `text.format` and
  `provider.require_parameters`, or an equivalent OpenAI Chat Completions
  `response_format`, plus
  `generate_with_usage(...) -> tuple[str, dict[str, Any]]`, while keeping
  existing text calls backward compatible.

- [ ] **Step 1: Write failing request-body tests**

Mock `requests.post` and assert exact bodies:

```python
def test_openrouter_responses_sends_strict_json_schema(fake_post):
    cfg = GenConfig(
        text_format={
            "type": "json_schema",
            "name": "gsa_v1",
            "strict": True,
            "schema": {"type": "object", "properties": {}},
        },
        require_parameters=True,
    )
    client.generate("openrouter/google/gemma-3-4b-it", "prompt", cfg)
    body = fake_post.call_args.kwargs["json"]
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["provider"]["require_parameters"] is True
```

Add tests for JSON-object mode, merging `provider.only` with
`require_parameters`, and omission for plain-text calls.

Add an OpenAI compatibility test that converts the shared strict format:

```python
{
    "type": "json_schema",
    "name": "hint_predictor_v1",
    "strict": True,
    "schema": {"type": "object", "properties": {}},
}
```

to:

```python
{
    "type": "json_schema",
    "json_schema": {
        "name": "hint_predictor_v1",
        "strict": True,
        "schema": {"type": "object", "properties": {}},
    },
}
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
conda run -n kltn python -m pytest tests/services/test_openrouter_structured_transport.py tests/services/test_openai_structured_transport.py -q
```

Expected: FAIL because `GenConfig` has no `text_format` or
`require_parameters`.

- [ ] **Step 3: Extend `GenConfig`**

Add:

```python
@dataclass
class GenConfig:
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 2048
    timeout: int = 60
    openrouter_provider: Optional[Dict[str, Any]] = None
    text_format: Optional[Dict[str, Any]] = None
    require_parameters: bool = False
```

- [ ] **Step 4: Build the OpenRouter request without mutating caller config**

Inside `_generate_openrouter`, copy provider configuration before merging:

```python
provider = dict(_openrouter_provider_for_model(model_name, cfg.openrouter_provider) or {})
if cfg.require_parameters:
    provider["require_parameters"] = True
if provider:
    body["provider"] = provider
if cfg.text_format is not None:
    body["text"] = {"format": dict(cfg.text_format)}
```

- [ ] **Step 5: Convert the shared format for the existing OpenAI transport**

In `_generate_openai`, pass `response_format` only when
`cfg.text_format is not None`. Convert strict JSON Schema to the Chat
Completions nesting shown in Step 1. Pass JSON-object mode unchanged as
`{"type": "json_object"}`.

- [ ] **Step 6: Run transport and baseline regression tests**

Before running tests, add:

```python
def generate_with_usage(
    self,
    model: str,
    prompt: str,
    config: GenConfig,
    *,
    max_retries: int = 4,
    retry_delay: int = 15,
) -> tuple[str, dict[str, Any]]:
    text = self.generate(
        model,
        prompt,
        config,
        max_retries=max_retries,
        retry_delay=retry_delay,
    )
    usage = dict(getattr(self._thread_local, "last_usage", None) or {})
    usage["cost_usd"] = usage_cost_usd(model, usage)
    return text, usage
```

Test that usage is copied rather than exposing mutable thread-local state.

Run:

```powershell
conda run -n kltn python -m pytest tests/services/test_openrouter_structured_transport.py tests/services/test_openai_structured_transport.py tests/baselines -q
```

Expected: PASS.

- [ ] **Step 7: Commit the transport slice**

```powershell
git add baseline/llm_client.py tests/services/test_openrouter_structured_transport.py tests/services/test_openai_structured_transport.py
git commit -m "feat: support structured response formats"
```

---

### Task 3: Implement the Deep Structured-Generation Module

**Files:**
- Create: `src/services/structured_generation.py`
- Create: `tests/services/test_structured_generation.py`
- Modify: `src/services/__init__.py`

**Interfaces:**
- Consumes: Task 1 contracts and an injected
  `generate_once(prompt: str, text_format: dict[str, Any]) -> tuple[str, dict[str, Any]]`.
- Produces: `StructuredGenerator.generate(prompt, schema, context) -> StructuredResult`.

- [ ] **Step 1: Write failing mode-resolution tests**

Test explicit model mapping:

```python
def test_qwen_uses_json_object_mode():
    assert resolve_output_mode("openrouter/qwen/qwen3-8b") is StructuredOutputMode.JSON_OBJECT


def test_gemma_uses_strict_schema_mode():
    assert resolve_output_mode("openrouter/google/gemma-3-4b-it") is StructuredOutputMode.STRICT_JSON_SCHEMA


def test_existing_openai_model_uses_strict_schema_mode():
    assert resolve_output_mode("openai/gpt-4o-mini") is StructuredOutputMode.STRICT_JSON_SCHEMA
```

Test that unknown OpenRouter models raise `UnsupportedStructuredOutputModel`
unless an explicit override is passed.

- [ ] **Step 2: Write failing validation and repair tests**

Use a fake sequence transport. Assert:

- valid first response makes one call;
- malformed JSON makes exactly two calls;
- schema-invalid JSON makes exactly two calls;
- valid repaired JSON returns `repair_attempted=True`;
- valid repaired JSON returns `schema_valid=False`;
- invalid repair raises `StructuredGenerationError`;
- no third call is made;
- usage and cost sum across both calls.

- [ ] **Step 3: Run focused tests and verify RED**

Run:

```powershell
conda run -n kltn python -m pytest tests/services/test_structured_generation.py -q
```

Expected: FAIL because the module does not exist.

- [ ] **Step 4: Implement capability resolution and text-format builders**

Implement:

```python
def resolve_output_mode(
    model: str,
    override: StructuredOutputMode | None = None,
) -> StructuredOutputMode:
    if override is not None:
        return override
    normalized = model.removeprefix("openrouter/")
    if normalized == "google/gemma-3-4b-it":
        return StructuredOutputMode.STRICT_JSON_SCHEMA
    if normalized in {"qwen/qwen3-8b", "qwen/qwen3-8b-04-28"}:
        return StructuredOutputMode.JSON_OBJECT
    if model.startswith("openai/"):
        return StructuredOutputMode.STRICT_JSON_SCHEMA
    raise UnsupportedStructuredOutputModel(model)
```

For strict mode, build:

```python
{
    "type": "json_schema",
    "name": f"{schema.name.replace('.', '_')}_{schema.version}",
    "strict": True,
    "schema": schema.json_schema,
}
```

For Qwen, build `{"type": "json_object"}` and append a compact serialized
schema instruction to the prompt.

- [ ] **Step 5: Implement decode, local schema validation, and semantic validation**

Use `json.loads`, `jsonschema.Draft202012Validator`, and
`validate_domain_payload`. Format validation errors with JSON paths so repair
prompts identify the exact failure.

- [ ] **Step 6: Implement one non-recursive repair**

The repair prompt must include:

```text
Return one JSON object only.
The previous response failed validation.
Validation errors:
{validation_errors}
Previous response:
{raw_response}
```

Call the same injected transport with the same text format. Validate the repair
directly without entering `generate` recursively.

Normalize each callback's usage dictionary to
`prompt_tokens`, `completion_tokens`, `total_tokens`, and `cost_usd`. Sum the
initial and repair dictionaries into `StructuredResult`.

- [ ] **Step 7: Run module tests**

Run:

```powershell
conda run -n kltn python -m pytest tests/services/test_structured_generation.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit the structured-generation module**

```powershell
git add src/services/__init__.py src/services/structured_generation.py tests/services/test_structured_generation.py
git commit -m "feat: add validated structured generation"
```

---

### Task 4: Migrate POMA Agents to Versioned Structured Schemas

**Files:**
- Modify: `src/services/llm_client.py`
- Modify: `src/agents/base_agent.py`
- Modify: `src/agents/hint_predictor.py`
- Modify: `src/agents/question_refiner.py`
- Modify: `src/agents/specialists/_base_specialist.py`
- Modify: `src/agents/answer_normalization.py`
- Modify: `src/contracts/trace.py`
- Create: `tests/services/test_llm_client_structured.py`
- Create: `tests/agents/test_structured_agents.py`

**Interfaces:**
- Consumes: `StructuredGenerator` and named schemas from Task 1.
- Produces: `LLMClient.generate_structured(...) -> StructuredResult` and
  `BaseAgent.response_schema_name`.

- [ ] **Step 1: Write failing `LLMClient` delegation tests**

Inject a fake low-level client and assert that:

```python
result = client.generate_structured(
    "prompt",
    schema=schema_for_call("hint_predictor.v1"),
    agent_name="HintPredictor",
    prompt_name="hint_predictor",
)
assert result.data == {"predicted_hints": ["What"]}
assert client.get_call_logs()[0]["schema_name"] == "hint_predictor.v1"
```

Also assert schema-valid, repair, mode, token, and cost fields appear in the
call log.

- [ ] **Step 2: Run the client test and verify RED**

Run:

```powershell
conda run -n kltn python -m pytest tests/services/test_llm_client_structured.py -q
```

Expected: FAIL because `generate_structured` is missing.

- [ ] **Step 3: Add schema-aware raw generation to `LLMClient`**

Extend `_generate_raw_text` to accept an optional `text_format`. Construct a
fresh `GenConfig` with `require_parameters=True` for structured calls.
Implement `generate_structured` by constructing a `StructuredGenerator` around
that raw callback.

Keep `generate_text` for genuinely textual calls. Make `generate_json` a
temporary compatibility wrapper that requires a schema argument and delegates
to `generate_structured`; remove heuristic labeled-JSON fallback from new call
paths.

- [ ] **Step 4: Make JSON agents declare schemas**

Add to `BaseAgent`:

```python
response_schema_name: str = ""

def _call_llm_json(self, prompt: str) -> Dict[str, Any]:
    if not self.response_schema_name:
        raise NotImplementedError(f"{self.name} has no response schema")
    result = self._llm.generate_structured(
        prompt,
        schema=schema_for_call(self.response_schema_name),
        agent_name=self.name,
        prompt_name=self.prompt_name,
    )
    return result.data
```

Set exact names on each agent class:

- `HintPredictorAgent`: `hint_predictor.v1`
- `QuestionRefinerAgent`: `question_refiner.v1`
- `BaseSpecialistAgent`: `specialist.v1`
- `AnswerNormalizationAgent`: `answer_normalization.v1`

- [ ] **Step 5: Preserve native AN prompt switching**

Update `_call_llm_json_for_prompt` so it changes only `prompt_name` for logging
and keeps `response_schema_name="answer_normalization.v1"`. Do not change
deterministic variants, prompt selection, answer ordering, or native run-many
semantics.

- [ ] **Step 6: Add agent contract tests with a fake structured LLM**

Test one valid and one invalid payload for each agent family. Assert specialist
evidence/confidence/reason parsing remains unchanged and AN returns the same
ordered variants for deterministic fixtures.

- [ ] **Step 7: Run agent and client tests**

Run:

```powershell
conda run -n kltn python -m pytest tests/services/test_llm_client_structured.py tests/agents/test_structured_agents.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit the POMA migration**

```powershell
git add src/services/llm_client.py src/agents/base_agent.py src/agents/hint_predictor.py src/agents/question_refiner.py src/agents/specialists/_base_specialist.py src/agents/answer_normalization.py src/contracts/trace.py tests/services/test_llm_client_structured.py tests/agents/test_structured_agents.py
git commit -m "refactor: use structured generation in POMA agents"
```

---

### Task 5: Migrate Direct-Prompt Baselines Without Collapsing Prompt Styles

**Files:**
- Modify: `baseline/prompts.py`
- Modify: `baseline/run.py`
- Modify: `baseline/model_output_parse.py`
- Modify: `run_baseline.py`
- Create: `tests/baselines/test_structured_prompt_styles.py`
- Modify: `tests/baselines/test_run_baseline_cli.py`

**Interfaces:**
- Consumes: Task 1 baseline schemas and Task 3 `StructuredGenerator`.
- Produces: canonical baseline records with `prediction`, `structured_output`,
  and style-specific reasoning fields.

- [ ] **Step 1: Write failing prompt-style tests**

Assert:

- zero-shot and few-shot request only `final_answer`;
- CoT requests `reasoning` and `final_answer`;
- task decomposition requests `subproblems`, `reasoning`, and `final_answer`;
- prompt versions change to `v2_zs_structured`, `v2_cot_structured`,
  `v2_td_structured`, and `v2_fs_structured`.

- [ ] **Step 2: Run prompt tests and verify RED**

Run:

```powershell
conda run -n kltn python -m pytest tests/baselines/test_structured_prompt_styles.py -q
```

Expected: FAIL because current CoT and TD prompts suppress reasoning and use v1
versions.

- [ ] **Step 3: Update the four prompt builders**

Keep table/question instructions unchanged. Replace output instructions with
the exact style contract. Do not request hidden chain-of-thought; define
`reasoning` as a concise task rationale suitable for audit.

- [ ] **Step 4: Replace heuristic parsing in new baseline runs**

Map prompt styles to schema names:

```python
SCHEMA_BY_PROMPT_STYLE = {
    "zero_shot": "baseline_zero_shot.v1",
    "few_shot": "baseline_few_shot.v1",
    "cot": "baseline_cot.v1",
    "task_decomposition": "baseline_task_decomposition.v1",
}
```

Call `StructuredGenerator`, persist `prediction=[data["final_answer"]]`, and
provide its raw callback through `LLMZeroShotClient.generate_with_usage`.
Persist optional reasoning/subproblems under `structured_output`. Retain
`parse_reasoning_final_answer` only for loading historical artifacts.

- [ ] **Step 5: Update CLI and artifact tests**

Assert new JSONL records contain:

```python
assert record["prediction"] == ["Guatemala"]
assert "predicted_answer" not in record
assert record["schema_name"] == "baseline_few_shot.v1"
```

Verify skip-existing behavior still keys on `qa_id`.

- [ ] **Step 6: Run baseline tests**

Run:

```powershell
conda run -n kltn python -m pytest tests/baselines -q
```

Expected: PASS.

- [ ] **Step 7: Commit the baseline migration**

```powershell
git add baseline/prompts.py baseline/run.py baseline/model_output_parse.py run_baseline.py tests/baselines/test_structured_prompt_styles.py tests/baselines/test_run_baseline_cli.py
git commit -m "refactor: structure direct baseline outputs"
```

---

### Task 6: Implement the Grounded Single Answer Agent

**Files:**
- Create: `src/contracts/finalization.py`
- Modify: `src/contracts/__init__.py`
- Create: `src/agents/grounded_single_answer.py`
- Modify: `src/agents/__init__.py`
- Create: `src/prompts/grounded_single_answer.md`
- Create: `tests/agents/test_grounded_single_answer.py`

**Interfaces:**
- Consumes: `GroundedAnswerRequest` and schema `gsa.v1`.
- Produces: `GroundedSingleAnswerAgent.run(request) -> GroundedAnswer`.

- [ ] **Step 1: Write failing request-invariant tests**

Cover empty question, empty table, no candidates, preserved ordering, and empty
candidate canonicalization:

```python
def test_empty_candidate_is_canonicalized_not_dropped():
    request = GroundedAnswerRequest(
        question="Câu hỏi?",
        table_flattened="A | B",
        candidates=[AnswerCandidate("What", "")],
    )
    assert request.candidates[0].answer == "Null"
```

- [ ] **Step 2: Write failing result-semantic tests**

Test all four decisions. Include failures for `null` with a non-null answer,
`selected` not matching any normalized candidate, and non-null decisions with
empty evidence.

- [ ] **Step 3: Run GSA tests and verify RED**

Run:

```powershell
conda run -n kltn python -m pytest tests/agents/test_grounded_single_answer.py -q
```

Expected: FAIL because GSA contracts and agent are missing.

- [ ] **Step 4: Implement GSA contracts**

Use frozen dataclasses and this exact public method:

```python
class GroundedSingleAnswerAgent(BaseAgent):
    name = "GroundedSingleAnswer"
    prompt_name = "grounded_single_answer"
    response_schema_name = "gsa.v1"

    def run(self, request: GroundedAnswerRequest) -> GroundedAnswer:
        ...
```

- [ ] **Step 5: Write the GSA prompt**

The prompt must:

- state that only table evidence is authoritative;
- preserve candidate order and source names;
- allow selection, correction, synthesis, or `Null`;
- require concise supporting evidence copied or localized from the table;
- forbid use of gold, external knowledge, markdown, and ungrounded guesses;
- describe the four decision labels.

Serialize candidates as JSON inside the prompt to avoid delimiter ambiguity.

- [ ] **Step 6: Implement output conversion and semantic checks**

After structured validation, canonicalize all null spellings to `Null`. For
`selected`, compare `final_answer` against input candidates with
`evaluation.normalization.normalize_text`.

- [ ] **Step 7: Run GSA tests**

Run:

```powershell
conda run -n kltn python -m pytest tests/agents/test_grounded_single_answer.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit GSA**

```powershell
git add src/contracts/__init__.py src/contracts/finalization.py src/agents/__init__.py src/agents/grounded_single_answer.py src/prompts/grounded_single_answer.md tests/agents/test_grounded_single_answer.py
git commit -m "feat: add grounded single answer agent"
```

---

### Task 7: Add the Three Finalizer Adapters and Symmetric Common AN

**Files:**
- Create: `src/finalization/__init__.py`
- Create: `src/finalization/finalizers.py`
- Create: `tests/finalization/test_finalizers.py`

**Interfaces:**
- Consumes: `FinalizationRequest(question, table_flattened, candidates)` and
  injected AN/GSA agents.
- Produces: `FinalizationResult(prediction, finalizer, trace, usage)`.

- [ ] **Step 1: Write failing finalizer-symmetry tests**

Assert common AN passes only:

```python
normalizer.run_many(
    answers=[candidate.answer for candidate in request.candidates],
    question=request.question,
    target=None,
    specialist_names_by_answer=None,
)
```

Assert native AN receives POMA target/source metadata, GSA receives the table,
and no adapter receives gold.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
conda run -n kltn python -m pytest tests/finalization/test_finalizers.py -q
```

Expected: FAIL because the package does not exist.

- [ ] **Step 3: Define finalizer contracts**

Use:

```python
@dataclass(frozen=True)
class FinalizationRequest:
    qa_id: str
    table_id: str
    question: str
    table_flattened: str
    candidates: list[AnswerCandidate]
    native_target: str | None = None


@dataclass(frozen=True)
class FinalizationResult:
    prediction: list[str]
    finalizer: str
    trace: dict[str, Any]
    usage: dict[str, Any]
```

Only `NativeAnswerNormalizationFinalizer` may consume `native_target` and
source names.

- [ ] **Step 4: Implement the three adapters**

Enforce exactly one prediction for GSA. Preserve AN answer ordering. Add trace
fields that distinguish `an-native`, `an-common`, and `gsa`.

- [ ] **Step 5: Run finalizer and AN regression tests**

Run:

```powershell
conda run -n kltn python -m pytest tests/finalization/test_finalizers.py tests/agents/test_structured_agents.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the finalizer seam**

```powershell
git add src/finalization/__init__.py src/finalization/finalizers.py tests/finalization/test_finalizers.py
git commit -m "feat: add symmetric answer finalizers"
```

---

### Task 8: Build Source Adapters and Reproducible Artifact I/O

**Files:**
- Create: `src/finalization/sources.py`
- Create: `src/finalization/artifacts.py`
- Create: `tests/finalization/test_sources.py`
- Create: `tests/finalization/test_artifacts.py`

**Interfaces:**
- Consumes: POMA specialist-stage artifacts, direct-baseline artifacts, QAs,
  tables, and run configuration.
- Produces: ordered `FinalizationRequest` objects, `RunManifest`, incremental
  JSONL, and materialized JSON.

- [ ] **Step 1: Write failing source-adapter tests**

Create minimal fixtures and assert:

- POMA source names and raw answers come only from `steps.3_specialists`;
- baseline source contains exactly one raw answer;
- gold, hints, target, evidence, confidence, and reason are absent from GSA
  requests;
- missing `qa_id`, table, or raw answer raises a typed input error;
- duplicate IDs are rejected.

- [ ] **Step 2: Write failing artifact tests**

Assert SHA-256 fingerprints are stable, resume skips successful IDs, failed
records remain eligible for explicit retry, mismatched source/config hashes
fail, and materialization sorts by dataset order.

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
conda run -n kltn python -m pytest tests/finalization/test_sources.py tests/finalization/test_artifacts.py -q
```

Expected: FAIL because the modules are missing.

- [ ] **Step 4: Implement source adapters**

Expose:

```python
def load_finalization_requests(
    *,
    source_path: Path,
    source_kind: Literal["poma-specialists", "direct-baseline"],
    qas_path: Path,
    tables_path: Path,
) -> list[FinalizationRequest]:
    ...
```

Use `preprocessing.representation.create_representation(table).to_string()` to
produce the same Flatten V1 table used by generators.

- [ ] **Step 5: Implement manifest and fingerprinting**

`RunManifest` must include source/dataset hashes, git commit, model/provider,
mode, prompt/schema versions, finalizer, generation settings, timestamps,
counts, tokens, and cost. Compute one configuration fingerprint from a
canonical sorted JSON encoding.

- [ ] **Step 6: Implement incremental output**

Append one JSON object per line under a file lock. Never truncate an existing
matching run during resume. Materialize:

```json
{
  "manifest": {},
  "predictions": []
}
```

Every successful record uses `prediction`. Every failed record contains
`qa_id`, `table_id`, and a typed `error`; failures are retained in the official
denominator.

- [ ] **Step 7: Run source/artifact tests**

Run:

```powershell
conda run -n kltn python -m pytest tests/finalization/test_sources.py tests/finalization/test_artifacts.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit artifact I/O**

```powershell
git add src/finalization/sources.py src/finalization/artifacts.py tests/finalization/test_sources.py tests/finalization/test_artifacts.py
git commit -m "feat: add finalization artifact adapters"
```

---

### Task 9: Implement the Offline Finalizer CLI

**Files:**
- Create: `scripts/run_finalizer.py`
- Create: `tests/finalization/test_run_finalizer_cli.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: Tasks 7-8 finalizer and artifact interfaces.
- Produces: the approved `run_finalizer.py` CLI and resumable output.

- [ ] **Step 1: Write failing CLI parser tests**

Test exact accepted values:

```python
assert parser.parse_args([
    "--source", "raw.json",
    "--source-kind", "poma-specialists",
    "--finalizer", "gsa",
    "--qas", "dataset/qas_test.json",
    "--tables", "dataset/table.json",
    "--model", "openrouter/qwen/qwen3-8b",
    "--output", "outputs/q2/gsa.json",
]).finalizer == "gsa"
```

Reject missing tables for GSA, unknown finalizers, and output paths equal to
the source path.

- [ ] **Step 2: Write a fake-LLM end-to-end test**

Run the CLI entry function on two fixture QAs, interrupt after one append,
resume, and assert two unique output records plus a matching manifest.

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
conda run -n kltn python -m pytest tests/finalization/test_run_finalizer_cli.py -q
```

Expected: FAIL because the script is missing.

- [ ] **Step 4: Implement parser and runner**

Support:

- `--source`
- `--source-kind`
- `--finalizer`
- `--qas`
- `--tables`
- `--model`
- `--provider`
- `--output`
- `--resume`
- `--max-workers`
- `--limit`
- `--structured-output-mode`

Do not expose gold answers to finalizers. Print coverage, failure count,
schema-valid rate, repair rate, tokens, cost, and output paths.

- [ ] **Step 5: Document examples**

Add one example each for POMA GSA, baseline GSA, common AN, and native AN. State
that output/source/config fingerprints must match to resume.

- [ ] **Step 6: Run CLI tests**

Run:

```powershell
conda run -n kltn python -m pytest tests/finalization/test_run_finalizer_cli.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit the CLI**

```powershell
git add README.md scripts/run_finalizer.py tests/finalization/test_run_finalizer_cli.py
git commit -m "feat: add offline finalizer runner"
```

---

### Task 10: Fix Canonical Predictions and Trace-Safe POMA Resume

**Files:**
- Modify: `run_poma.py`
- Modify: `src/contracts/trace.py`
- Create: `tests/test_run_poma_artifacts.py`

**Interfaces:**
- Consumes: existing POMA run results and traces.
- Produces: new `prediction` records and merged trace/stage artifacts that
  preserve all prior `qa_id` entries.

- [ ] **Step 1: Write a regression test for the 592/992 trace-loss mechanism**

Build two existing traces and one new trace. Call the incremental/final save
helpers and assert all three IDs remain in both the trace file and each
materialized stage file.

- [ ] **Step 2: Write canonical prediction tests**

Assert `process_one` returns `prediction`, not `predicted_answer`, and summary
helpers read candidates through one compatibility helper.

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
conda run -n kltn python -m pytest tests/test_run_poma_artifacts.py -q
```

Expected: FAIL because `_incremental_save` and final trace writes currently
persist only `new_traces`.

- [ ] **Step 4: Merge existing and new traces on every save**

Use `_merge_trace_lists(current_existing_traces, new_traces)` in incremental,
no-pending, final, and stage-output paths. Preserve newer records by `qa_id`.
Apply the same merge policy to stage records.

- [ ] **Step 5: Centralize candidate compatibility**

Add:

```python
def _record_candidates(record: Mapping[str, Any]) -> list[str]:
    raw = record.get("prediction", record.get("predicted_answer", []))
    ...
```

New POMA writers emit only `prediction`. Readers and historical-stage loading
accept both keys.

- [ ] **Step 6: Run artifact tests**

Run:

```powershell
conda run -n kltn python -m pytest tests/test_run_poma_artifacts.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit the resume fix**

```powershell
git add run_poma.py src/contracts/trace.py tests/test_run_poma_artifacts.py
git commit -m "fix: preserve POMA traces across resume"
```

---

### Task 11: Add Candidate Policies and K Statistics to Evaluation

**Files:**
- Modify: `evaluation/io.py`
- Modify: `evaluation/run.py`
- Modify: `evaluation/exceptions.py`
- Modify: `run_eval.py`
- Create: `tests/evaluation/test_io.py`
- Create: `tests/evaluation/test_run.py`

**Interfaces:**
- Consumes: `candidate_policy: Literal["all", "first", "single-required"]`.
- Produces: policy-validated aligned samples and `candidate_statistics`.

- [ ] **Step 1: Write failing legacy/canonical loader tests**

Assert `extract_candidates` reads, in order:

1. `prediction`
2. legacy `predicted_answer`
3. legacy `predictions`
4. legacy `answer`

Test list and scalar values.

- [ ] **Step 2: Write failing candidate-policy tests**

Assert:

- `all` preserves all candidates;
- `first` keeps one candidate;
- `single-required` accepts K=1;
- `single-required` raises `EvaluationDataError` for K=0 or K>1;
- failed records remain aligned with an empty prediction and score zero rather
  than disappearing.

- [ ] **Step 3: Write failing K-statistic tests**

For K values `[1, 1, 2, 4, 10]`, assert count, mean, median, p95, max, and K=1
proportion. Define p95 using nearest-rank to avoid dependency ambiguity.

- [ ] **Step 4: Run tests and verify RED**

Run:

```powershell
conda run -n kltn python -m pytest tests/evaluation/test_io.py tests/evaluation/test_run.py -q
```

Expected: FAIL because legacy `predicted_answer`, policies, and K statistics
are missing.

- [ ] **Step 5: Implement policy-aware alignment**

Add `candidate_policy` to `align_records` and `evaluate_files`. For failed
records, synthesize `[""]` only for scoring and retain failure metadata in the
report.

- [ ] **Step 6: Add K statistics to the report**

Compute statistics before and after applying the candidate policy. Store under:

```json
{
  "candidate_policy": "all",
  "source_candidate_statistics": {
    "count": 5,
    "mean": 3.6,
    "median": 2,
    "p95": 10,
    "max": 10,
    "k_equals_one_rate": 0.4
  },
  "evaluated_candidate_statistics": {
    "count": 5,
    "mean": 3.6,
    "median": 2,
    "p95": 10,
    "max": 10,
    "k_equals_one_rate": 0.4
  }
}
```

- [ ] **Step 7: Add the CLI flag**

In `run_eval.py`, add:

```python
parser.add_argument(
    "--candidate-policy",
    choices=("all", "first", "single-required"),
    default="all",
)
```

Pass it through to `evaluate_files`.

- [ ] **Step 8: Run evaluation tests and one historical smoke evaluation**

Run:

```powershell
conda run -n kltn python -m pytest tests/evaluation/test_io.py tests/evaluation/test_run.py -q
conda run -n kltn python run_eval.py --pred outputs/poma/qwen/poma_qas_test_qwen3_8b_hp.json --qas dataset/qas_test.json --candidate-policy all
```

Expected: tests PASS; smoke report evaluates 992 IDs and no longer treats
legacy `predicted_answer` as empty.

- [ ] **Step 9: Commit evaluator policies**

```powershell
git add evaluation/io.py evaluation/run.py evaluation/exceptions.py run_eval.py tests/evaluation/test_io.py tests/evaluation/test_run.py
git commit -m "feat: add explicit candidate evaluation policies"
```

---

### Task 12: Add Reproducible Bootstrap, Hint, and Parallelism Analysis

**Files:**
- Create: `evaluation/bootstrap.py`
- Create: `evaluation/hint_metrics.py`
- Create: `evaluation/parallelism.py`
- Create: `scripts/run_revision_analysis.py`
- Create: `tests/evaluation/test_bootstrap.py`
- Create: `tests/evaluation/test_hint_metrics.py`
- Create: `tests/evaluation/test_parallelism.py`
- Create: `tests/scripts/test_revision_analysis.py`

**Interfaces:**
- Consumes: aligned per-QA system scores, QAs, predicted hints, and POMA raw
  traces.
- Produces: one deterministic Q2 analysis JSON report.

- [ ] **Step 1: Write failing paired-bootstrap tests**

Use fixed vectors and assert reproducibility:

```python
result_a = paired_bootstrap_ci(
    system_a=[1.0, 1.0, 0.0, 0.0],
    system_b=[1.0, 0.0, 0.0, 0.0],
    samples=1000,
    seed=20260729,
)
result_b = paired_bootstrap_ci(
    system_a=[1.0, 1.0, 0.0, 0.0],
    system_b=[1.0, 0.0, 0.0, 0.0],
    samples=1000,
    seed=20260729,
)
assert result_a == result_b
```

Reject different ID orderings and unequal sample lengths.

- [ ] **Step 2: Write failing hint-metric tests**

Cover exact-set accuracy, micro/macro P/R/F1, per-label support, and alias
canonicalization through `HINT_ALIASES_TO_CANONICAL`.

- [ ] **Step 3: Write failing parallelism tests**

For routed counts `[1, 1, 2, 3]`, assert the distribution, mean, and
multi-specialist rate. Reject missing router steps rather than silently
shrinking the denominator.

- [ ] **Step 4: Run analysis tests and verify RED**

Run:

```powershell
conda run -n kltn python -m pytest tests/evaluation/test_bootstrap.py tests/evaluation/test_hint_metrics.py tests/evaluation/test_parallelism.py tests/scripts/test_revision_analysis.py -q
```

Expected: FAIL because the modules and script are missing.

- [ ] **Step 5: Implement paired percentile bootstrap**

Use `random.Random(seed)` and sample QA indices with replacement. Return point
estimate, lower/upper 95% percentiles, sample count, and seed. Bootstrap system
scores and paired differences using the same sampled indices.

- [ ] **Step 6: Implement multilabel hint metrics**

Return exact-set accuracy, Jaccard, micro P/R/F1, macro P/R/F1, and per-label
support/P/R/F1 over the complete QAs denominator.

- [ ] **Step 7: Implement parallelism analysis**

Read routed specialist names from `steps.2_router.specialist_names`. Report
count distribution, mean, median, maximum, and rate where K>1. Treat missing
trace IDs as coverage errors.

- [ ] **Step 8: Implement the revision-analysis CLI**

Accept:

- repeated `--system NAME=PATH`;
- `--primary-system`;
- `--baseline-system`;
- `--qas`;
- `--poma-traces`;
- `--bootstrap-samples` defaulting to 10000;
- `--seed` defaulting to 20260729;
- `--output`.

Generate evaluation metrics, paired CIs, hint metrics, parallelism, GSA
decision distribution, schema/repair/failure rates, and cost/latency summaries.
For each system, call `evaluate_files` with
`f1`, `em`, `rouge1`, `meteor`, and `answerability_f1`; never infer
answerability from the aggregate metrics alone.

Write an `interpretation_gate` object for the primary comparison:

```json
{
  "minimum_em_difference": 0.02,
  "observed_em_difference": 0.0,
  "paired_ci_excludes_zero": false,
  "passes_backbone_gate": false
}
```

The script computes these fields mechanically; it does not change the 0.02
threshold or generate publication claims.

- [ ] **Step 9: Run analysis tests**

Run:

```powershell
conda run -n kltn python -m pytest tests/evaluation/test_bootstrap.py tests/evaluation/test_hint_metrics.py tests/evaluation/test_parallelism.py tests/scripts/test_revision_analysis.py -q
```

Expected: PASS.

- [ ] **Step 10: Commit revision analysis**

```powershell
git add evaluation/bootstrap.py evaluation/hint_metrics.py evaluation/parallelism.py scripts/run_revision_analysis.py tests/evaluation/test_bootstrap.py tests/evaluation/test_hint_metrics.py tests/evaluation/test_parallelism.py tests/scripts/test_revision_analysis.py
git commit -m "feat: add Q2 revision analysis"
```

---

### Task 13: Add Capability Preflight and the Symmetric Experiment Runbook

**Files:**
- Create: `scripts/run_q2_experiments.ps1`
- Modify: `README.md`
- Create: `tests/scripts/test_q2_runbook.py`

**Interfaces:**
- Consumes: the POMA, baseline, finalizer, evaluator, and analysis CLIs.
- Produces: explicit dry-run/preflight/full-run commands without launching paid
  work automatically.

- [ ] **Step 1: Write a static runbook test**

Assert the script contains both model IDs, all five generators, AN-common and
GSA for every generator, AN-native for POMA, explicit output paths, and no API
keys.

- [ ] **Step 2: Run the static test and verify RED**

Run:

```powershell
conda run -n kltn python -m pytest tests/scripts/test_q2_runbook.py -q
```

Expected: FAIL because the runbook is missing.

- [ ] **Step 3: Implement safe PowerShell phases**

Use parameters:

```powershell
param(
    [ValidateSet('DryRun','Preflight','Full')]
    [string]$Phase = 'DryRun',
    [int]$PreflightLimit = 5,
    [string]$OutputRoot = 'outputs/q2_revision'
)
```

`DryRun` prints commands only. `Preflight` runs limit 5. `Full` runs 992 only
when the user explicitly selects it.

- [ ] **Step 4: Encode the complete matrix**

For each of:

- `openrouter/qwen/qwen3-8b`
- `openrouter/google/gemma-3-4b-it`

run raw zero-shot, CoT, task decomposition, few-shot, and POMA; then common AN
and GSA for all; native AN for POMA. Use distinct immutable source and
finalizer paths.

- [ ] **Step 5: Add evaluation and analysis commands**

Use `single-required` for raw direct baselines and GSA, `all` for AN, and
`first` only for diagnostic POMA reports. End each backbone phase with
`run_revision_analysis.py --bootstrap-samples 10000 --seed 20260729`.

- [ ] **Step 6: Document the execution gates**

README must state:

- run tests first;
- inspect preflight trace and manifest;
- require 100% schema validity after at most one repair for preflight;
- obtain explicit approval before `-Phase Full`;
- do not mix historical and new artifacts.

- [ ] **Step 7: Run runbook tests**

Run:

```powershell
conda run -n kltn python -m pytest tests/scripts/test_q2_runbook.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit the runbook**

```powershell
git add README.md scripts/run_q2_experiments.ps1 tests/scripts/test_q2_runbook.py
git commit -m "docs: add symmetric Q2 experiment runbook"
```

---

### Task 14: Full Verification and Implementation Handoff

**Files:**
- Modify only files required to fix failures introduced by Tasks 1-13.

**Interfaces:**
- Consumes: all implementation slices.
- Produces: a verified implementation ready for user-approved live preflight.

- [ ] **Step 1: Run the complete test suite**

Run:

```powershell
conda run -n kltn python -m pytest -q
```

Expected: PASS with no live LLM calls.

- [ ] **Step 2: Run CLI help smoke checks**

Run:

```powershell
conda run -n kltn python run_poma.py --help
conda run -n kltn python run_baseline.py --help
conda run -n kltn python scripts/run_finalizer.py --help
conda run -n kltn python run_eval.py --help
conda run -n kltn python scripts/run_revision_analysis.py --help
```

Expected: every command exits 0 and documents its structured-output,
candidate-policy, resume, and output options.

- [ ] **Step 3: Run offline fixture smoke checks**

Run the finalizer and evaluator against test fixtures using the fake transport.
Confirm:

- output uses `prediction`;
- GSA outputs K=1;
- AN outputs K>=1;
- resume produces no duplicates;
- manifest fingerprints are stable;
- failed records remain in coverage.

- [ ] **Step 4: Verify the experiment runbook is non-destructive by default**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_q2_experiments.ps1 -Phase DryRun
```

Expected: commands are printed; no files under `outputs/q2_revision` are
created and no network calls occur.

- [ ] **Step 5: Review the diff for secrets and generated outputs**

Run:

```powershell
git status --short
git diff --check
git diff --stat
```

Confirm `.env`, API keys, caches, and `outputs/` are not staged.

- [ ] **Step 6: Route verification failures back to their owning task**

If verification exposes a defect, return to the task that owns the affected
interface, add a focused regression test there, make the minimal fix, rerun
that task's focused command and the full suite, and commit using that task's
explicit file list. Do not create a catch-all verification commit and do not
use `git add -A`.

- [ ] **Step 7: Stop before paid live runs**

Report test evidence, current commits, and the exact command for:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_q2_experiments.ps1 -Phase Preflight -PreflightLimit 5
```

Request user approval before running the live preflight. Request separate
approval again before `-Phase Full`.
