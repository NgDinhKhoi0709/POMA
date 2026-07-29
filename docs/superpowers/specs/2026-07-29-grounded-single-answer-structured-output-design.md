# Grounded Single Answer and Structured Output Design

Date: 2026-07-29

## 1. Purpose

This design supports the Q2 revision experiments for POMA. It has two linked
goals:

1. Add a table-grounded finalizer that returns exactly one answer.
2. Enforce structured, validated outputs for every POMA-owned LLM call.

The design preserves the existing variant-producing Answer Normalization (AN)
so the paper can distinguish native best-of-K evaluation from fair
single-answer evaluation.

The paper will let the controlled results determine its framing. If POMA does
not retain a meaningful advantage after symmetric finalization, the revised
paper will attribute the gains to normalization or grounded final verification
rather than overclaiming orchestration.

## 2. Scope

Structured output is mandatory for:

- all agents under `src/`;
- the new Grounded Single Answer agent;
- POMA-owned zero-shot, few-shot, chain-of-thought, and task-decomposition
  baselines under `baseline/`;
- structured-output repair calls.

Vendored CoAgt and Chain-of-Query protocols are not changed. Their outputs may
be validated at the POMA adapter seam without changing the upstream method.

The existing Conda environment `kltn` remains the development environment.

## 3. Architecture

### 3.1 Structured generation module

Create a deep module at `src/services/structured_generation.py`:

```python
class StructuredGenerator:
    def generate(
        self,
        *,
        prompt: str,
        schema: ResponseSchema,
        context: CallContext,
    ) -> StructuredResult:
        ...
```

The interface exposes only the prompt, response schema, and call metadata. The
implementation owns:

- OpenRouter request formatting;
- model capability resolution;
- strict JSON Schema versus JSON-object mode;
- local JSON Schema validation;
- one semantic repair attempt;
- token and cost accounting;
- schema and repair telemetry;
- typed failures.

`BaseAgent`, direct-prompt baselines, and GSA call this same module. Callers do
not implement independent JSON parsing or repair.

### 3.2 Schema registry

Define versioned schemas in `src/contracts/structured_outputs.py`:

- `hint_predictor.v1`
- `question_refiner.v1`
- `specialist.v1`
- `answer_normalization.v1`
- `gsa.v1`
- `baseline_zero_shot.v1`
- `baseline_few_shot.v1`
- `baseline_cot.v1`
- `baseline_task_decomposition.v1`

JSON Schema is the single structural source of truth. Parsed dictionaries are
then converted to typed domain contracts, where semantic invariants are
checked.

### 3.3 Finalizer seam

Provide one internal finalizer interface:

```python
finalize(request: FinalizationRequest) -> FinalizationResult
```

Three adapters satisfy it:

- `NativeAnswerNormalizationFinalizer`
- `CommonAnswerNormalizationFinalizer`
- `GroundedSingleAnswerFinalizer`

The existing native AN behavior is preserved. Common AN omits POMA-only target,
hint, and specialist metadata so the same postprocessor is applied to all
generators. GSA is implemented in
`src/agents/grounded_single_answer.py`.

The data flow is:

```text
POMA specialists -- raw candidates -+-> AN-native -> K answers
                                    +-> AN-common -> K answers
                                    `-> GSA       -> 1 answer

Direct baseline --- raw candidate --+-> AN-common -> K answers
                                    `-> GSA       -> 1 answer
```

GSA consumes raw generator answers, not AN-expanded variants. It is an
alternative finalizer rather than a stage after AN.

## 4. Contracts and invariants

### 4.1 Structured generation

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

### 4.2 GSA request

```python
@dataclass(frozen=True)
class AnswerCandidate:
    source_name: str
    answer: str


@dataclass(frozen=True)
class GroundedAnswerRequest:
    question: str
    table_flattened: str
    candidates: list[AnswerCandidate]
```

The request must satisfy these invariants:

- question and table are non-empty;
- at least one candidate is present;
- candidate ordering is preserved;
- no gold answer, hint, refiner target, specialist evidence, confidence, or
  rationale is passed;
- an empty candidate answer is canonicalized to `Null`, not silently dropped.

POMA supplies one or more raw specialist candidates. Each direct baseline
supplies one candidate.

### 4.3 GSA result

```python
class GroundedDecision(str, Enum):
    SELECTED = "selected"
    CORRECTED = "corrected"
    SYNTHESIZED = "synthesized"
    NULL = "null"


@dataclass(frozen=True)
class GroundedAnswer:
    final_answer: str
    decision: GroundedDecision
    supporting_evidence: list[str]
    reason: str
```

The result must satisfy these invariants:

- `final_answer` is a non-empty string;
- every abstention representation is canonicalized to `Null`;
- `decision=null` requires `final_answer="Null"`;
- `selected` requires a normalized match to an input candidate;
- `corrected` retains the candidate's semantic value while correcting its
  representation;
- `synthesized` denotes a semantically new answer;
- every non-null result contains at least one supporting evidence string.

GSA may synthesize a new answer or decide `Null` after reading the table. It is
therefore described in the paper as grounded answer synthesis/verification, not
as surface normalization.

## 5. Structured-output capability policy

Two transport modes are supported:

```python
class StructuredOutputMode(str, Enum):
    STRICT_JSON_SCHEMA = "strict_json_schema"
    JSON_OBJECT = "json_object"
```

For the approved experiments:

- `google/gemma-3-4b-it` uses strict JSON Schema.
- `qwen/qwen3-8b` uses JSON-object mode followed by the same local validator.

The OpenRouter `/responses` request uses:

- `text.format={type:"json_schema", name, strict, schema}` for strict mode;
- `text.format={type:"json_object"}` for JSON-object mode;
- `provider.require_parameters=true`;
- non-streaming generation;
- temperature 0.

The implementation does not silently change model or provider. A startup
preflight may query model metadata, but the resolved mode is fixed for the run
and recorded in its manifest. There is no per-request capability lookup.

Use the `jsonschema` package for local structural validation. Domain contract
construction performs a second semantic validation pass. Strict provider
enforcement never replaces local validation.

For JSON-object mode, the prompt loader appends compact schema instructions.
Strict mode does not duplicate the full schema as prose.

## 6. Repair and error handling

The generation sequence is:

```text
generate
-> JSON decode
-> JSON Schema validation
-> domain invariant validation
-> on failure: one same-model, same-schema repair call
-> validate repaired result
```

The repair call is marked `repair_attempt=True` and cannot recursively trigger
another repair.

Provider and network retries remain separate from semantic repair. If the
single repair fails, the module raises a typed error and the runner writes a
failed record. It does not choose the first candidate, invent `Null`, or switch
models.

Errors and traces must not contain API keys. Large prompt/table dumps are only
written to an explicitly configured diagnostic artifact.

## 7. Direct baseline schemas

Structured output preserves the behavioral distinction among prompt styles:

```json
{"final_answer": "..."}
```

is used for zero-shot and few-shot.

```json
{"reasoning": "...", "final_answer": "..."}
```

is used for chain-of-thought.

```json
{
  "subproblems": ["..."],
  "reasoning": "...",
  "final_answer": "..."
}
```

is used for task decomposition.

Only `final_answer` is evaluated. Reasoning and subproblems are retained for
audit.

## 8. Offline finalizer runner

Provide a unified entry point:

```powershell
python scripts/run_finalizer.py `
  --source <raw-output-or-trace.json> `
  --source-kind poma-specialists|direct-baseline `
  --finalizer an-native|an-common|gsa `
  --qas dataset/qas_test.json `
  --tables dataset/table.json `
  --model <model-id> `
  --output <path> `
  --resume
```

Source adapters only translate artifact formats. They do not contain
finalization behavior.

The runner:

- loads the question and Flatten V1 table by ID;
- preserves the source artifact;
- writes incremental JSONL;
- resumes by `qa_id`;
- materializes a readable JSON artifact after completion;
- rejects resume when the source hash or configuration fingerprint differs.

The POMA trace writer must preserve prior trace records during resume. Current
historical Qwen traces contain only 592 of 992 instances, so they are suitable
for regression and smoke tests only.

## 9. Artifact contract

All new output uses `prediction` as the canonical key:

```json
{
  "qa_id": "...",
  "table_id": "...",
  "prediction": ["..."],
  "finalizer": "gsa",
  "finalizer_trace": {
    "decision": "selected",
    "supporting_evidence": ["..."],
    "reason": "...",
    "structured_output": {}
  },
  "usage": {}
}
```

Loaders continue accepting legacy `predicted_answer`, but new writers do not
emit it.

Each run manifest records:

- dataset and source-artifact hashes;
- git commit;
- model and provider;
- resolved structured-output mode;
- prompt and schema versions;
- finalizer and complete generation configuration;
- temperature and token limits;
- success, error, schema-valid, and repair counts;
- elapsed time, tokens, and cost.

## 10. Evaluator changes

Add candidate policies:

```powershell
python run_eval.py ... --candidate-policy all
python run_eval.py ... --candidate-policy first
python run_eval.py ... --candidate-policy single-required
```

- `all` performs best-of-K evaluation and is used for AN.
- `first` is a diagnostic only.
- `single-required` rejects records whose candidate count is not exactly one
  and is used for GSA and raw direct baselines.

The evaluator accepts both `prediction` and legacy `predicted_answer`. It also
reports mean, median, p95, maximum K, and the proportion with K=1.

## 11. Testing

Tests avoid live LLM calls and use fake transport adapters.

### 11.1 Structured generation

Test:

- request translation for both output modes;
- `require_parameters=true`;
- valid and invalid JSON;
- schema and semantic validation;
- exactly one repair;
- typed failure after failed repair;
- no model/provider fallback;
- usage aggregation across generation and repair;
- secret-safe error logging.

### 11.2 Schemas and agents

For every schema, test valid fixtures, missing fields, incorrect types, extra
properties, and invalid enums. Verify that direct baselines preserve their
reasoning fields and that domain contracts retain existing behavior.

### 11.3 GSA

Test request validation, all four decisions, decision/result invariants,
evidence requirements, abstention canonicalization, and exactly one prediction.

### 11.4 Runner and evaluator

Test both source adapters, non-overwrite behavior, incremental output, resume,
fingerprint mismatch, output ordering, legacy candidate loading, all candidate
policies, K statistics, and reproduction of a known historical fixture.

## 12. Verification gates

Before full experiments:

- `python -m pytest` passes;
- fake-LLM offline smoke tests pass;
- each backbone passes a live 3-5 instance preflight;
- all preflight records are schema-valid after at most one repair;
- at least one trace for each observed GSA decision is inspected;
- the run manifest contains the capability and configuration fingerprint.

For paper results:

- every system/configuration contains exactly 992 unique IDs;
- failed samples remain in the denominator;
- every GSA record contains exactly one answer;
- schema-valid, repair, and failure rates are reported;
- both backbones use the same experimental matrix.

## 13. Experimental matrix

Backbones:

- Qwen3-8B
- Gemma-3-4B

Generators:

- zero-shot
- chain-of-thought
- task decomposition
- few-shot
- POMA

For each generator, evaluate:

- raw output;
- common AN with best-of-K policy;
- GSA with single-required policy.

POMA additionally evaluates native AN to reproduce and analyze the original
system.

The primary comparison within each backbone is:

```text
POMA + GSA versus the strongest direct baseline + GSA
```

Exact Match is the primary metric. F1, ROUGE-1, and METEOR are secondary
metrics.

Required analyses:

- paired bootstrap 95% confidence intervals using 10,000 resamples;
- a recorded bootstrap seed;
- confidence intervals for systems and paired differences;
- answerability confusion and per-class F1;
- K distribution and best-of-K minus first-candidate gap;
- GSA decision distribution;
- schema-valid, repair, and failure rates;
- hint exact-set accuracy and micro, macro, and per-label precision/recall/F1;
- specialists-per-question distribution and actual parallel rate;
- latency, token, and cost summaries.

## 14. Precommitted interpretation

- If POMA+GSA exceeds the strongest direct baseline+GSA by at least 2 EM and
  the paired confidence interval excludes zero on both backbones, the paper may
  claim evidence of generalizable orchestration value.
- If this condition holds on only one backbone, the effect is described as
  model-dependent.
- If it holds on neither backbone, the paper is reframed around normalization,
  grounded final verification, and controlled source-of-gain analysis.
- If common AN improves strongly but GSA does not, candidate multiplicity and
  best-of-K evaluation are identified as the main gain.
- If GSA improves all generators similarly, grounded final verification rather
  than orchestration is identified as the main gain.
- Answerability regressions are reported directly.
- Thresholds are not changed after observing results.

## 15. Execution policy

All official Qwen results are rerun on all 992 instances after the new
structured-output implementation is frozen. Historical outputs are not mixed
with new outputs. Gemma runs the full symmetric matrix.

Implementation begins only after this design is approved and converted into a
detailed implementation plan.
