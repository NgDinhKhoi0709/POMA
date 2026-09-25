# 02 — Current system

## POMA architecture (running version, `run_poma.py`)

Inference pipeline with **no backbone fine-tuning**. Diagram: `imgs/pipeline.png`.

| Stage | Module | Function | LLM call? |
|---|---|---|---|
| 1. Preprocessing | `preprocessing/parser.py`, `representation.py` | Parse HTML into a logical grid (resolve `rowspan`/`colspan`), normalize Unicode, serialize as **Flatten V1** (one row per line, `\|` separators, `<header>` tags on header cells) | No |
| 2. Hint predictor | `src/agents/hint_predictor.py` | Assign one or more standard reasoning labels to each question | Yes |
| 3. Question refiner | `src/agents/question_refiner.py` | Rewrite the question with an explicit target and constraints | Yes |
| 4. Router | `src/agents/router.py` | **Deterministic 1:1** mapping from hint to specialist | No |
| 5. Specialists (parallel) | `src/agents/specialists/*.py` | Ten prompts by question type: `What, Where, Who, When, Why, How, YesNo, List, MathematicalReasoning, MultiConditions`. Each returns an answer, evidence, confidence, and rationale | Yes (one call per agent) |
| 6. Answer Normalization | `src/agents/answer_normalization.py` | Merge candidates and generate **Vietnamese variants** for booleans, numbers, dates, lists, rankings, and `Null` | **Hybrid**: regex for numbers/dates/booleans/lists; LLM for free text |
| 7. Finalizer (optional) | `src/agents/grounded_single_answer.py`, `src/finalization/` | GSA selects, edits, or synthesizes **exactly one** table-grounded answer | Yes |

**Three points to make when presenting the architecture:**

1. **The router is a 1:1 lookup table.** Thus `Â` is simply `Ĥ` with a
   different label. "Deterministic routing" makes no new decision; the real
   decision lies in the hint predictor, whose **accuracy has never been reported**.
2. **Parallel execution cannot affect accuracy:** specialists do not see each
   other's outputs, and decoding uses `temperature=0`. Parallel and sequential
   execution produce the same answers. The only possible benefit is latency,
   which has not been measured against sequential execution (review F4).
3. **Parallel execution happens for only about 11% of questions:** 880/992
   questions invoke just one specialist.

## POMA v3lite — simplified version implemented and run (`poma_v3lite/`)

Built from the `poma3.drawio` diagram after **removing** the Program Agent,
Generalist, and consensus/adjudicator layer (see D11 in [04](04-nhat-ky-thuc-nghiem.md)
and [03](03-trang-thai-bai-bao.md) for the reasons).

| Component | File | Mechanism |
|---|---|---|
| H1 — reduce long tables | `poma_v3lite/table_search.py`, `preprocessing/reduction.py` | For tables over 2.000 tokens **and** questions without aggregation cues, keep headers plus the top-k BM25 rows (k=20), preserve original row order, and add a note with the original row count |
| Solver | Reuses a POMA specialist | One solver rather than a set of specialists |
| Rule-based formatter | `poma_v3lite/formatter.py` | Normalize answers using rules inferred from train/dev gold conventions (no LLM call) |
| Answerability gate | `poma_v3lite/answerability.py` | Trigger only for a `Null` answer: check again and re-answer |

## Implemented table representations (`preprocessing/variants.py`)

`v1_raw` (original Flatten V1) · `v1_clean` · `pipe_clean` ·
`pipe_path_clean` · `pipe_nohdr` · `markdown_clean` ·
`markdown_kv_clean` · `row_anchor_clean` · `json_clean` ·
`hdrfilter` (`preprocessing/header_filter.py`).
`Grid.cleaned()` removes `[12]`-style citations, empty columns, columns
containing only images/links, and empty body rows.

## Deterministic computation channel (`src/table_executor/`)

`planner.py` generates JSON `{plan, route, ast}` in a small DSL
(`select, filter, project, argmax/argmin, count, sum/avg, compare, sort,
take, lookup_title`). `ast_executor.py` executes the tree over `table_rows`
and parses Vietnamese-style numbers (`95.664`, `3,5`). The **R2** gate
overrides an answer only when `exec_status=ok`, the plan uses
`count/sum/avg/argmax/argmin`, and it has no `compare`.
**Measured and rejected** (D04).

## Evaluation infrastructure (`evaluation/`, `run_eval.py`) — currently the repository's strongest component

| Component | File | Function |
|---|---|---|
| Primary metrics | `exact_match.py`, `f1.py`, `rouge1.py`, `meteor.py` | EM, F1, ROUGE-1, METEOR |
| Candidate policy | `io.py::CandidatePolicy` | `all` (oracle best-of-K), `first`, or `single-required` |
| Strict mode | `run_eval.py --strict` | Reject duplicate/missing/extra IDs, empty answers, and policy violations; record SHA-256 of predictions, QAs, tables, and scorer code |
| Confidence intervals | `bootstrap.py::paired_bootstrap_ci` | 10.000 paired bootstrap samples with a fixed seed, matched by `qa_id` |
| Diagnostics | `answerability_f1.py`, `hint_metrics.py`, `metrics_by_table_type.py`, `parallelism.py`, `cost.py` | Answerability, hint predictor P/R/F1, table-type breakdown, specialists per question, cost |
| Semantic metric | `bif_score.py`, `bertscore.py` | **BIF** = `0,5 × PhoBERTScore F1 (PhoBERT-large, layer 17) + 0,5 × P(entailment)` from four-label ViNLI XLM-R Large, reference → prediction |
| Interpretation gate | `scripts/run_revision_analysis.py::interpretation_gate` | Require an EM increase ≥ 0,02 **and** a paired 95% CI excluding zero |

The ViNLI checkpoint for BIF was fine-tuned in-house:
`reproductions/vinli/ViNLI_COLING_2022_Kaggle.ipynb`. Results are in
`outputs/models/vinli-xlmr-large-4label/`; entailment label = 0
(checked on ten example pairs).

## Backbones and runtime

| Channel | Model | Runtime |
|---|---|---|
| Main API | `openrouter/qwen/qwen3-8b` (Alibaba provider pinned) | OpenRouter |
| Second backbone (API) | `openrouter/google/gemma-3-4b-it` | OpenRouter |
| Local backbone | SEA-LION v3 8B IT | Kaggle, vLLM (`src/services/local_vllm_client.py`, `local_transformers_client.py`) |
| External baselines | CoAgt, Chain-of-Query | `baselines/`, `scripts/run_baseline.py` |

The client supports rotation across multiple API keys, JSON-schema structured
output (`src/contracts/structured_outputs.py`), and two prompt profiles
(full `src/prompts/` and shorter `src/prompts_compact/`).

## Parser bug found and fixed (2026-09-19) — affects all older results

`preprocessing/parser.py` called `cell.get_text()` **without a separator**.
Text separated by `<br>` or block tags inside the same HTML cell was therefore
**concatenated without spaces**.

```
FLATTEN: ...|Dân chủ Kitô giáoQuốc gia: CDU|      gold: Dân chủ Kitô giáo
```

- **Scope: content changed in 95/329 tables, affecting 325/992 test questions
  (32,8%).**
- Correct fix: insert spaces only at **block-tag boundaries**
  (`<br>, <p>, <div>, <li>, <tr>`), leaving inline tags
  (`<a>, <span>, <sup>, <b>, <i>`) intact. Regression test:
  `tests/preprocessing/test_cell_separator.py`.
- `POMA_LEGACY_CELL_TEXT=1` reproduces the old behavior for A/B runs only.
- **Implication: D01/D02/D04/D09/D10/D11 artifacts were measured using
  corrupted tables.** See [04](04-nhat-ky-thuc-nghiem.md).
