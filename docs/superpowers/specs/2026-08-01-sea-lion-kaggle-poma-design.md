# SEA-LION Kaggle POMA Design

Date: 2026-08-01

## Goal

Build a Kaggle-ready evaluation path for `aisingapore/Llama-SEA-LION-v3-8B-IT`
as a sub-10B independent backbone for Vietnamese table question answering in
POMA, with a compact shared prompt profile and reproducible pilot/final
evaluation.

## Background

The existing Gemma POMA run on the same 543 test IDs underperformed its
zero-shot baseline. The Qwen3-8B run was much stronger, which suggests that
model capability and candidate finalization behavior matter more than POMA
structure alone. The next experiment needs a different under-10B backbone,
not another Qwen-family model, and it needs to run on Kaggle GPU hardware.

SEA-LION v3 8B IT is the selected backbone because it is Llama 3.1 based,
targets Southeast Asian languages including Vietnamese, supports long context,
and stays below 10B parameters. SEA-LION is not assumed to be available through
OpenRouter, so the implementation will run it locally in Kaggle.

## Scope

This work will add:

- A local SEA-LION inference adapter for POMA using `transformers`.
- Compact shared prompts for the POMA agents.
- A table preview mechanism for HintPredictor.
- Strict JSON parsing, validation, repair tracing, and resume-friendly outputs.
- A Kaggle notebook that can run pilot and final evaluations.
- Offline tests for the new deterministic logic.

This work will not add:

- Fine-tuning.
- vLLM serving.
- Automatic prompt tuning on the test set.
- Automatic promotion from pilot to final evaluation.
- Committing generated model outputs under `outputs/`.

## Runtime Design

The Kaggle runtime uses `transformers` plus `bitsandbytes` with 4-bit NF4
quantization. It targets a single T4 GPU and runs sequentially with batch size
one. The model is loaded as `aisingapore/Llama-SEA-LION-v3-8B-IT`.

Generation is deterministic:

- `do_sample=False`.
- No chain-of-thought prompting.
- No temperature parameter when greedy decoding is used.
- Agent-specific `max_new_tokens` limits, typically 128 to 512.
- Context length configured for a 32K-token window.

The implementation should prefer a direct local adapter over a local HTTP
server. The adapter will expose the same conceptual operation the existing
POMA agents need: submit a prompt, receive raw generated text, parse JSON, and
record trace metadata.

## Prompt Profile

The compact prompt profile must be shared across backbones when comparing POMA
variants. Model-specific prompt rewrites are not allowed for the final
comparison unless they are explicitly reported as a separate experiment.

Prompt budgets:

- HintPredictor instruction target: at most about 500 tokens.
- QuestionRefiner instruction target: at most about 500 tokens.
- Simple specialists (`what`, `who`, `when`, `where`, `yesno`, `list`): at most
  about 500 instruction tokens and no few-shot examples.
- Complex specialists (`why`, `how`, `multi_conditions`, `math`): at most about
  900 instruction tokens and exactly two short examples, one answerable and one
  `Null`.
- GroundedSingleAnswer: compact decision prompt with no unnecessary reasoning
  transcript.
- Normalization prompts: compact JSON-only prompts.

All prompts must preserve existing contracts and canonical hint names. They
should ask for concise JSON only and avoid free-form explanations.

## Table Context Policy

HintPredictor receives a table preview instead of the full flattened table.
The preview is capped at 1,024 model tokens and contains:

- Table title or identifier when available.
- All column headers.
- Whole flattened rows sampled from the beginning, middle, and end.
- A clear omitted-row marker with row counts.

Specialist agents and GroundedSingleAnswer receive the full flattened table.
The implementation must check token length before each model call.

Input safety limits:

- Maximum input budget: 28,672 tokens.
- Remaining context budget: reserved for generation and safety margin inside
  the 32K-token context.

If an input exceeds the budget, the run records a `context_overflow` error for
that QA item and checkpoints it. The system must not silently truncate the
evidence table or produce an answer from incomplete table content.

The current table-length measurement using the SEA-LION tokenizer found the
largest flattened table at 17,904 tokens, so the expected compact prompts
should fit the 32K policy for normal specialist calls.

## Structured Output Policy

SEA-LION local generation does not provide server-side JSON schema enforcement,
so structured output is enforced client-side.

The parser accepts:

- A plain JSON object.
- A JSON object wrapped in a Markdown code fence.
- A JSON object preceded or followed by non-JSON text, provided exactly one
  valid object can be extracted.

After parsing, the existing response contract must be validated. If parsing or
contract validation fails, the adapter issues one repair call containing the
validation error and the previous raw output. If the repair also fails, the
agent follows its current safe fallback behavior or records a structured error,
depending on the existing agent contract.

Every call trace records:

- Prompt token count.
- Generated token count when available.
- Raw output.
- Parsed JSON.
- Validation error when present.
- Repair count.
- Latency.
- Model name and quantization mode.

## Evaluation Flow

The notebook supports two phases.

Pilot phase:

- Select 200 deterministic QA items from `dataset/qas_dev.json`.
- Use `seed=42`.
- Stratify by canonical hint type and table length bucket.
- Run zero-shot SEA-LION and POMA SEA-LION on the same QA IDs.
- Produce metrics and diagnostics.

Final phase:

- Use the same 543 test QA IDs used in the Gemma and Qwen comparisons.
- Run only when the notebook variable `RUN_FINAL_543 = True`.
- Keep zero-shot and POMA checkpoints separate.
- Do not automatically start the final run based on pilot metrics.

Metrics:

- Exact Match.
- Token-level F1.
- ROUGE-1.
- METEOR.
- Paired win/tie/loss.
- Paired bootstrap 95% confidence intervals.
- Latency and token usage summaries.
- JSON compliance and repair rates.
- Error summaries by hint type and table length bucket.

Oracle candidate scoring may be produced as secondary analysis when candidate
data is available, but it is not the primary reported POMA result.

## Notebook Design

The notebook is a thin orchestration layer. It should not duplicate the whole
pipeline.

It must support two source modes:

- Kaggle Dataset mode: use a mounted repository directory such as
  `/kaggle/input/poma-repo/POMA`.
- Git mode: clone `REPO_URL` and checkout an explicit `REVISION`.

Before loading the model, the notebook validates that these files exist:

- `dataset/qas_dev.json`
- `dataset/qas_test.json`
- `dataset/table.json`

The notebook includes cells for:

- Installing Kaggle dependencies.
- Selecting repo source mode.
- Loading the model and tokenizer.
- Running a small smoke sample.
- Running the 200-item pilot.
- Evaluating pilot outputs.
- Optionally running the final 543-item test when `RUN_FINAL_543 = True`.
- Evaluating final outputs.
- Showing output paths and compact summary tables.

Output files are written under `/kaggle/working/` by default. Prediction and
trace outputs are append-only JSONL files so interrupted Kaggle sessions can be
resumed by QA ID.

## Resume And Output Design

Each run has a stable run directory containing:

- `selected_ids.json`
- `predictions.jsonl`
- `traces.jsonl`
- `errors.jsonl`
- `metrics.json`
- `comparison.json`

The runner loads completed QA IDs from existing JSONL output and skips them on
resume. A QA item is considered complete only when it has either a final
prediction record or a terminal structured error record.

Zero-shot and POMA runs use separate directories so partial runs do not collide.

## Tests

Tests must avoid live LLM calls. They should cover:

- Table preview construction preserves title, headers, whole rows, and omitted
  count markers while respecting token limits.
- JSON extraction from raw JSON, fenced JSON, and text-wrapped JSON.
- Parser failure on ambiguous or invalid JSON.
- One-repair behavior with a mocked local adapter.
- Resume logic skips completed QA IDs and retains failed terminal records.
- Pilot ID selection is deterministic for `seed=42`.
- CLI or notebook helper configuration resolves Kaggle Dataset mode and Git mode
  paths without loading a model.

## Acceptance Criteria

The implementation is acceptable when:

- Offline tests for new logic pass.
- Existing relevant tests still pass.
- The notebook can be opened as a valid `.ipynb`.
- A user can run a small smoke test on Kaggle by changing only documented config
  variables.
- Pilot and final runs write resumable JSONL outputs.
- Metrics reports can compare zero-shot and POMA on the same selected QA IDs.
- No generated `outputs/` artifacts are committed.

## Known Risks

- SEA-LION may emit malformed JSON more often than API models with strict schema
  support. The repair policy limits retries to keep runtime predictable.
- Kaggle T4 memory can vary by session image and installed package versions.
  NF4 quantization and batch size one are required defaults.
- Prompt compaction can improve cost and context use but may change POMA
  behavior. Results must be reported as the compact prompt profile, not mixed
  with older prompt metrics.
- If the repository is uploaded as a Kaggle Dataset, it must include these new
  modules and prompts. Cloning the public GitHub remote may not include local
  uncommitted changes.
