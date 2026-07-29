# CoAgt and Chain-of-Query Baselines Design

## Objective

Vendor the available CoAgt and Chain-of-Query (CoQ) source trees from
`D:\.UIT\KLTN\code\baselines` into POMA, expose both through a consistent
POMA-owned command-line runner, and verify each baseline on two
Open-ViTabQA test questions using `openai/gpt-4o-mini`.

The integration must preserve each baseline's available prompts and reasoning
algorithm. POMA may add adapters, orchestration, validation, output
normalization, and tests, but it must not silently replace or reinterpret the
baseline logic.

## Scope

### Included

- Vendor all source files required to run CoAgt and Chain-of-Query.
- Preserve upstream license, citation, README, prompt, and auxiliary source
  files needed at runtime.
- Preserve the existing Open-ViTabQA adapters as the starting point.
- Add a POMA-owned CLI that runs either baseline with the same dataset,
  model-selection, output, resume, overwrite, and evaluation conventions.
- Normalize prediction records so the existing POMA evaluator can consume
  them.
- Add unit, contract, CLI, resume, overwrite, and smoke coverage.
- Run two real Open-ViTabQA samples per baseline using
  `openai/gpt-4o-mini`.

### Excluded

- Reimplementing unpublished CoQ clause agents.
- Claiming the available CoQ fallback is the full paper implementation.
- Rewriting baseline prompts or reasoning flow around POMA's agent
  abstractions.
- Vendoring `.env` files, credentials, caches, generated output, temporary
  SQLite databases, or old experiment artifacts.
- Running the full Open-ViTabQA test split during initial integration.

## Source Provenance and Fidelity

The source of record for the initial vendor operation is:

- `D:\.UIT\KLTN\code\baselines\CoAgt`
- `D:\.UIT\KLTN\code\baselines\ChainofQuery`

The vendored directories will contain a provenance note identifying the local
source path and, where known, the upstream project URL and commit. Files that
are changed for POMA interoperability will be listed explicitly in that note.

The available Chain-of-Query source does not contain the clause-agent modules
referenced by `utils/pipeline.py`, including `column_selector`, `withas`,
`row_selector`, `aggfunc1`, `aggfunc2`, `order1`, and `order2`. The official
public repository also exposes only `base_sql_generator.py` under
`utils/agents`. Therefore this integration preserves the existing
`coq_base_sql_fallback` behavior. Every CoQ result and run manifest must record:

- `pipeline_mode: "coq_base_sql_fallback"`
- a non-empty `fallback_reason`

The common runner must reject a CoQ result that omits these fields or labels
the run as `full_chainofquery`.

## Repository Layout

```text
POMA/
├── baselines/
│   ├── README.md
│   ├── coagt/
│   │   ├── PROVENANCE.md
│   │   └── ... vendored CoAgt source
│   └── chain_of_query/
│       ├── PROVENANCE.md
│       └── ... vendored Chain-of-Query source
├── scripts/
│   └── run_baseline.py
├── outputs/
│   └── baselines/
│       ├── coagt/
│       └── coq/
└── tests/
    └── baselines/
```

The vendor operation excludes:

- `.env` and other secret-bearing files
- `__pycache__`, `.pytest_cache`, and bytecode
- generated `outputs/` and `run_test/` trees
- Chain-of-Query `tmp/*.db`
- previously converted smoke datasets and generated result files

Small upstream sample inputs that are part of the baseline source distribution
may remain only when a test or documented upstream command requires them.

## Common CLI

The POMA-owned entry point is:

```powershell
python scripts/run_baseline.py <coagt|coq> [options]
```

The common options are:

- `--qas`, default `dataset/qas_test.json`
- `--tables`, default `dataset/table.json`
- `--model`, default `openai/gpt-4o-mini`
- `--limit`, optional positive record limit
- `--max-workers`, default `1`
- `--output-dir`, default `outputs/baselines`
- `--run-id`, optional stable run name
- `--resume`, skip QA IDs already present in result or error JSONL
- `--overwrite`, remove only the explicitly resolved run directory's generated
  files before starting
- `--skip-eval`, disable automatic POMA evaluation

`--resume` and `--overwrite` are mutually exclusive. The runner resolves all
dataset and output paths relative to the POMA repository root, independent of
the caller's current working directory.

The two required smoke commands are:

```powershell
python scripts/run_baseline.py coagt --model openai/gpt-4o-mini --limit 2 --max-workers 1 --run-id smoke-gpt4o-mini
python scripts/run_baseline.py coq --model openai/gpt-4o-mini --limit 2 --max-workers 1 --run-id smoke-gpt4o-mini
```

## Components

### Common runner

`scripts/run_baseline.py` owns argument parsing, repository-relative path
resolution, preflight validation, run-directory naming, adapter dispatch,
post-run contract validation, and optional evaluation.

It invokes baseline adapters through Python functions rather than shelling out.
This makes error propagation, testing, and Windows path handling predictable
while leaving the baseline reasoning functions intact.

### CoAgt adapter

The CoAgt adapter:

1. Reads POMA's QA and table JSON.
2. Converts selected records to the WikiTQ-shaped structures expected by
   CoAgt.
3. Runs the existing collector chain, synthesizer, and answer refiner.
4. Writes successful records immediately to `results.jsonl`.
5. Writes failed records immediately to `errors.jsonl`.
6. Builds `results.json` and `meta.json` at the end.

The existing default temperatures are preserved:

- collector: `0.2`
- synthesizer: `0.5`
- refiner: `0.0`

The existing maximum chunk size remains `1000` tokens.

### Chain-of-Query adapter

The CoQ adapter:

1. Reads POMA's QA and table JSON.
2. Builds the Chain-of-Query table representation and per-sample SQLite
   database.
3. Detects the missing full-pipeline modules.
4. Executes the source's existing base-SQL fallback.
5. Records SQL validity, final SQL, fallback metadata, usage, latency, and
   prediction.
6. Closes and removes per-sample temporary database resources.

No missing clause agent will be synthesized as part of this integration.

### Evaluation bridge

After inference, the common runner invokes POMA's evaluation functions against
the selected QA subset and the normalized prediction JSONL. The default report
includes:

- exact match
- token F1
- ROUGE-1
- METEOR
- answerability F1
- cost

The evaluation report is stored inside the run directory under
`eval/report.json`.

## Output Contract

Each successful prediction record must contain:

- `qa_id: str`
- `table_id: str`
- `question: str`
- `prediction: str`
- `answer: str`
- `model: str`
- `method: str`
- `prompt_tokens: int`
- `completion_tokens: int`
- `total_tokens: int`
- `api_calls: int`
- `cost_usd: float`
- `latency_s: float`
- `error: null`

CoAgt records additionally contain:

- `num_collectors: int`
- stage temperatures
- `max_chunk_tokens: int`

CoQ records additionally contain:

- `pipeline_mode: "coq_base_sql_fallback"`
- `fallback_reason: str`
- `valid_sql: bool`
- `final_sql: str`
- SQL/reasoning log

Each run directory contains:

```text
results.jsonl
results.json
errors.jsonl
qas_subset.json
meta.json
eval/report.json
```

`meta.json` records the method, requested model, backend model, selected and
completed counts, errors, resume statistics, token totals, API call totals,
cost, average latency, source provenance, and pipeline mode.

## Model Access

The smoke run uses `openai/gpt-4o-mini`. The baseline-facing model value is
normalized to `gpt-4o-mini` before calling the OpenAI SDK.

The runner loads POMA's repository-root `.env` without overriding variables
already present in the process environment. It never copies a key into a
baseline directory or writes secrets to output or logs.

Preflight fails before inference when `OPENAI_API_KEY` is absent. Model calls
use each baseline's existing retry behavior. The initial smoke run uses one
worker to limit rate pressure and make failures easier to diagnose.

## Error Handling

- Missing required dependency: fail preflight with the package names and the
  exact installation command.
- Missing API key: fail preflight without making a model request.
- Invalid dataset relationship, including a missing `table_id`: fail before
  inference with the offending QA identifier.
- Individual QA failure: append a structured record to `errors.jsonl`,
  continue remaining samples, and return a non-zero process exit code after
  finalization.
- Contract violation: stop evaluation and return non-zero rather than
  evaluating malformed predictions.
- CoQ mode mismatch: reject the run when its metadata does not explicitly
  match `coq_base_sql_fallback`.
- Existing run data without `--resume` or `--overwrite`: fail without changing
  the run directory.
- Destructive overwrite: delete only known generated files inside the fully
  resolved baseline run directory.

## Testing Strategy

### Unit tests

- Convert representative Open-ViTabQA QA/table fixtures into valid CoAgt
  records.
- Convert the same fixtures into valid CoQ records.
- Reject missing table IDs and malformed table structures.
- Normalize `openai/gpt-4o-mini` to the backend model name.

### Contract tests

- Validate required common fields and field types.
- Validate CoAgt-specific metadata.
- Validate the mandatory CoQ fallback fields.
- Reject a falsely labeled `full_chainofquery` result.

### Runner tests

- Resolve paths correctly when invoked outside the repository root.
- Reject simultaneous `--resume` and `--overwrite`.
- Resume skips IDs found in result or error JSONL.
- Overwrite targets only known files under the selected run directory.
- Mocked LLM calls exercise both CLIs without network cost.
- Successful mocked runs invoke the existing evaluator and produce a report.

### Real smoke verification

Run CoAgt and CoQ on the first two records from `dataset/qas_test.json` with:

- model `openai/gpt-4o-mini`
- `max_workers=1`
- separate run directories

Acceptance requires for each baseline:

- exactly two selected QA IDs represented across results and errors
- no unhandled Python exception
- valid `meta.json`
- evaluator-compatible successful prediction records
- `eval/report.json` when at least one prediction succeeds
- non-zero exit status if any selected QA fails

For CoQ, acceptance also requires every successful result and the run metadata
to identify `coq_base_sql_fallback`.

## Documentation

The root README gains a Baselines section with installation, smoke commands,
full-run examples, output locations, resume behavior, and the CoQ fidelity
limitation.

`baselines/README.md` distinguishes vendored upstream code from POMA-owned
adapters. Each baseline's `PROVENANCE.md` records its origin, license, local
adapter files, and excluded runtime artifacts.

## Completion Criteria

The integration is complete when:

1. A fresh clone contains all non-generated source required by both available
   baselines.
2. Unit and mocked integration tests pass.
3. Both documented two-sample GPT-4o-mini smoke commands finish and produce
   finalized run metadata.
4. Successful predictions are evaluated by POMA without manual conversion.
5. CoQ output is never represented as the unpublished full pipeline.
6. No credential or external absolute path is required in committed runtime
   configuration.
