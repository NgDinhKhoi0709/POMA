# 04 — Complete experiment log

Unless stated otherwise, all figures below use Qwen3-8B via OpenRouter
(Alibaba provider pinned), `temperature=0`, SHA-256-locked
`evaluation.exact_match`, a **one-answer** policy (`--strict`), and
10.000 paired bootstrap samples.

> **Boundary in the experiment record:** the concatenated-cell parser bug
> was fixed on 2026-09-19. **D01, D02, D04, D09, D10, and D11 used the OLD
> (legacy) parser. D12 and D13 used the FIXED parser.** Results across these
> groups are not directly comparable.

## Overview of completed experiments

The full proposal lists 19 directions (D01–D19,
`docs/research/enhance_poma/2026-09-19-poma-improvement-directions.md`).
**Eight directions were implemented and run in this repository.** D03 and
D05–D08 remain proposals. D13–D19 in the original list were ruled out using
existing evidence. Note that "D13" in the table below names this repository's
header-filtering experiment, not D13 from the original list.

| ID | Direction | n | Parser | EM effect (paired 95% CI) | Conclusion |
|---|---|---:|---|---|---|
| D01 | Fair scorer and provenance | 992 | legacy | POMA−FS: **−1,71** [−3,93; +0,50] | No evidence that POMA outperforms FS |
| D02 | GSA finalizer (one answer) | 992 | legacy | POMA 66,63→68,45; FS 67,34→**70,16** | GSA helps both, but helps FS more |
| D04 | Arithmetic executor (R2 gate) | 200 | legacy | **−1,0** [−2,5; 0,0] for all four readers | **REJECTED** |
| D09 | Eight table representations | 200 | legacy | best **+4,0** [−2,0; +10,0] | No significant winner |
| D10 | H1 — row selection for long tables | 155 | legacy | k=20 **+1,9** [−2,6; +7,1]; tokens −46,6% | Real token savings; EM inconclusive |
| D11 | Simplified POMA v3 (v3lite) | 992 | legacy | **+0,40** [−0,50; +1,31] | No component has a significant effect |
| D12 | Pipe representation | 500 | fixed | `pipe_nohdr` **+2,0** [−1,0; +5,0] | Worth validating; no conclusion yet |
| D13 | LLM header filtering for a compact table | 200 | fixed | **−14,5** [−21,0; −8,0] | **REJECTED: harmful, CI excludes zero** |
| — | Parser-fix A/B | 991 | both | fixed − legacy: **−1,41** [−3,13; +0,30] | Keep the correct parser; do not claim an EM gain |
| — | N1 — run variation | 900 | legacy | **−0,44** (another observation: **+1,7**) | Variation exceeds the measured gains |
| — | Hybrid BM25+PhoBERT retrieval | 476 | — | `hybrid_rrf@3` 92,44 < `bm25@20` 99,16 | **REJECTED** by a predefined rule |
| — | Backbone 2: Gemma-3-4B-IT | 543 | legacy | POMA−ZS: **−12,89** [−17,13; −8,66] | POMA **clearly loses** on a weaker backbone |
| — | Backbone 3: SEA-LION v3 8B IT | 992 | — | ZS 49,50 / FS 49,45 / CoT 47,83 | Run locally (Kaggle/vLLM) |

**Every CI for an improvement direction includes zero except D13, whose
effect is harmful.**

---

## D01 / D02 — Fair scoring and the GSA finalizer (n=992, legacy)

**Method.** Added `run_eval.py --strict` to reject duplicate/missing/extra
IDs, empty answers, and candidate-policy violations, and to record SHA-256
hashes of predictions, QAs, tables, and scorer code. Ran GSA
(`grounded_single_answer.v1`) as a selector emitting one answer for **both**
POMA and Few-shot with the same model, QAs, and scorer.

| System | F1 | EM | R1 | MET | BIF | GSA failure fallbacks |
|---|---:|---:|---:|---:|---:|---:|
| POMA `all` (oracle best-of-K, mean K 3,44, max K 80) | 83,42 | 74,90 | 79,46 | 79,88 | — | — |
| POMA-first | 79,80 | 66,63 | 74,69 | 75,76 | 75,00 | 0 |
| Few-shot raw | 78,63 | 67,34 | 73,46 | 73,55 | 73,83 | 0 |
| POMA + GSA | 81,31 | 68,45 | 77,12 | 78,15 | **76,43** | 2 |
| **Few-shot + GSA** | 81,52 | **70,16** | 76,93 | 77,23 | 76,10 | 3 |

- POMA+GSA − FS+GSA = **−1,71 EM** [−3,93; +0,50]; 53 wins / 70 losses / 869 ties.
- BIF weakly favors POMA by +0,33 (no paired bootstrap for BIF yet).
- GSA cost: POMA $0,4679 / FS $0,4778 (about 1.000 calls each).
- 560/992 POMA predictions have multiple candidates; the old evaluator treated
  them as empty answers while still exiting with code 0.
- **Decision:** close D02. Do not use this test set to select more GSA prompts,
  fallbacks, or variants.

Artifact: `outputs/d01/openrouter_qwen_qwen3-8b/fair_audit.json`.
Code: `scripts/prepare_d01_artifacts.py`, `scripts/audit_d01.py`.

---

## D04 — Arithmetic executor, R2 gate (n=200 stratified subset, legacy) → REJECTED

**Method.** Ported the planner, AST executor, and R2 rule verbatim from RankA.
The rule was fixed **before** API calls. The planner makes one independent
call per question, regardless of reader.

**Results (EM, same n=200 subset):**

| Reader | Original | + R2 |
|---|---:|---:|
| Zero-shot | 64,0 | — |
| CoT | 61,0 | — |
| Few-shot | 69,5 | 68,5 |
| POMA-first | 68,5 | 67,5 |
| POMA + GSA | 70,0 | 69,0 |
| Few-shot + GSA | 71,5 | 70,5 |
| FS + CoT-gate (control) | 69,5 | — |

Across all four readers: **0 wins, 2 losses, 198 ties**, effect
−1,0 [−2,5; 0,0]. BIF fell by exactly 0,3837 points for all four readers.

**Reasons for rejection:**

- Funnel: planner `ok` 110 / `parse_error` 37 / `error` 30 /
  `empty` 14 / `text` 9. Only 15 `ok` questions used an R2 operation;
  4 were excluded due to `compare`, leaving **11 overridden answers**.
- **Every reader already answered all 11 correctly**, including CoT, the
  weakest branch. The executor was correct on 9/11.
- Among 15 calculation questions that FS got wrong, R2 activated on **0/15**.
- Headroom over 992 questions: theoretical maximum **1,8–3,2 EM points**;
  realistic estimate **below about 1 point**.
- For 214 questions with a purely numeric gold answer, FS missed 44:
  **12 formatting only**, 18 wrong values, 14 nonnumeric outputs. Most of
  these are formatter rather than executor problems.
- 31/37 `parse_error` cases came from unbalanced JSON braces. RankA could
  prevent this with GBNF; OpenRouter cannot.

**Limit:** rejection is based on **low expected value**, not a CI that
establishes harm.

---

## D09 — Eight table representations (n=200, legacy)

| Variant | EM | F1 | ROUGE-1 | METEOR | BIF | Mean input tokens |
|---|---:|---:|---:|---:|---:|---:|
| `v1_raw` (control) | 52,50 | 69,86 | 63,10 | 68,14 | 63,81 | 1.436 |
| `v1_clean` | 51,00 | 68,32 | 61,32 | 66,49 | 61,97 | 1.393 |
| `pipe_clean` | 56,00 | 71,58 | 65,85 | 70,13 | **66,02** | 1.387 |
| `pipe_path_clean` | 55,50 | 71,16 | 64,35 | 68,73 | 64,52 | 1.364 |
| `markdown_clean` | 52,50 | 69,76 | 63,35 | 69,14 | 64,14 | 1.527 |
| `markdown_kv_clean` | **56,50** | **73,45** | **68,04** | **72,99** | 65,28 | 2.621 |
| `row_anchor_clean` | 54,00 | 70,87 | 64,39 | 69,32 | 64,61 | 1.618 |
| `json_clean` | 51,00 | 68,71 | 62,07 | 67,30 | 63,06 | 1.507 |

Against `v1_raw`: Markdown-KV +4,0 [−2,0; +10,0];
`pipe_clean` +3,5 [−1,5; +9,0]; JSON −1,5 [−6,5; +3,5].
**All CIs include zero.** Markdown-KV uses 1,9 times as many tokens.

**Three secondary findings matter more than the ranking:**

1. **The prompt has a larger effect than the format.** On the same subset,
   model, and Flatten V1 string, the old `v1_zs` prompt scores **64,0** EM;
   the current `v3_zs_minimal` scores **52,5**. The **−11,5-point** gap
   exceeds every format effect (at most +4).
2. **79% of differences across variants concern answer style rather than
   table reading.** Manual review of 29 differing answers found that 23/29
   only added/removed words or changed wording; just 6/29 changed substance.
3. The safe cleaning layer lost **no answers** on the 200-question subset.
   Across the full 992-question test, one entire-cell answer and three
   substrings were lost, all due to removing quotation marks.

---

## D10 — H1: row selection for long tables (n=155 questions with tables >2.000 tokens, legacy)

The primary objective is **token savings**; higher EM would be a bonus.

| Variant | EM | F1 | ROUGE-1 | METEOR | BIF | API input tokens | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| `v1_raw` (control) | 52,26 | 70,70 | 62,10 | 66,36 | 64,24 | 865.218 | $0,1762 |
| `h1_k20` (primary) | 54,19 | 72,80 | 64,94 | 70,02 | 64,96 | 461.954 (**−46,6%**) | $0,1140 (−35,3%) |
| `h1_k10` (sensitivity) | 52,26 | 72,87 | 65,15 | 70,76 | **65,21** | 390.038 (−54,9%) | $0,1050 (−40,4%) |

- k=20: +1,9 EM [−2,6; +7,1] (9 wins / 6 losses). k=10: 0,0 [−4,5; +4,5].
- Per-call latency fell from 29,3 to 17,4 seconds.
- The design was set **before the run** without model outputs: on train, the
  answer-containing row survived in 250/254 cases at k=20; on dev, 24/25.
- **Caution:** −46,6% applies only to long tables and a single-call zero-shot
  solver. Within multistage POMA over all 992 questions, savings shrink to
  **−6,4%** (see D11).
- 58/155 questions were gated out for aggregation cues, leaving the hardest
  long-table questions untreated.

---

## D11 — POMA v3lite (all 992 test questions, legacy)

Five nested artifacts isolate each component's contribution:

| Variant | Added component | EM | BIF | Versus control |
|---|---|---:|---:|---|
| `control` | POMA-first, original Flatten V1 | 68,35 | 75,33 | — |
| `control_fmt` | + rule-based formatter | 68,55 | 75,50 | +0,20 [−0,30; +0,71] |
| `h1` | + H1 long-table reduction | 68,45 | 75,57 | +0,10 [−0,40; +0,60] |
| `h1_fmt` | + both | 68,65 | 75,75 | +0,30 [−0,40; +1,01] |
| `v3lite` | + answerability gate | 68,75 | **75,97** | +0,40 [−0,50; +1,31] |

Total: **13 wins / 9 losses across 992 questions**. All CIs include zero.

**Three concrete lessons:**

- **H1 is diluted.** It changes the tables for 91/992 questions, but actual
  prompt tokens in the deployed pipeline fall by only **6,4%**
  (6.358.343 → 5.950.649); solver cost falls 2,5%.
- **The formatter barely changes POMA** (AN already produces clean answers).
  Two losses exposed rule bugs, including `format_candidates` dropping the
  `Null` candidate: an answer-selection policy disguised as cleaning.
- **The answerability gate captures almost nothing.** On this run, the ceiling
  is 47 false `Null` answers (4,7 EM points), but the gate gets only +0,10.
  In 16 replacements, **5 correct mistakes, 4 break correct `Null` answers,
  and 7 remain wrong**. The gate adds 159 calls (+16%), but **their cost was
  not recorded**, a measurement gap.

**Key observation:** rerunning the **same control configuration** scores 68,35
versus 66,63 for the older `poma_first.json` artifact: a **+1,7-point** gap,
larger than every effect in the table above (50 wins / 33 losses; only
847/992 answers match verbatim).

---

## D12 — Pipe representation (first 500 test questions, **fixed parser**)

Do not compare with D09 (different parser, questions, and n).

| Variant | EM | F1 | ROUGE-1 | METEOR | BIF | Mean API prompt tokens | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| `v1_raw` | 60,20 | 75,90 | 69,97 | 72,74 | 69,51 | 1.722,5 | $0,2408 |
| `pipe_clean` | 60,20 | 76,50 | 70,14 | 72,80 | 70,24 | 1.635,9 (−5,0%) | $0,2351 |
| `pipe_nohdr` | **62,20** | **77,80** | **71,71** | **74,23** | 70,62 | 1.627,5 (−5,5%) | $0,2349 |
| `pipe_h1` | 60,40 | 76,50 | 70,08 | 72,52 | 70,41 | 1.253,3 (−27,2%) | $0,2099 |
| `nohdr_h1` | 62,60 | — | — | — | **70,89** | 1.233,7 (**−28,4%**) | $0,2076 |

- `pipe_nohdr` − `v1_raw` = +2,0 [−1,0; +5,0]; versus `pipe_clean`,
  +2,0 [−0,6; +4,8]. Both CIs include zero.
- The +3,5 effect of `pipe_clean` in D09 **did not replicate** (parser,
  question subset, and n changed).
- Manual review of 20 differing questions: **9 substantive wins / 2 losses**
  (exploratory two-sided binomial p ≈ 0,065).
- `pipe_h1` changes just 38/500 questions: treat it as a **cost measurement**,
  not an accuracy signal.

---

## D13 — LLM header filtering for a compact table (n=200, fixed parser) → REJECTED

| Variant | EM | F1 | BIF | Total prompt tokens | Cost | Wins/Losses/Ties |
|---|---:|---:|---:|---:|---:|---|
| `v1_raw` (control) | 65,5 | 80,15 | 74,20 | 292.699 | $0,0921 | — |
| `v1_clean` | 67,5 | 82,25 | 73,48 | 293.950 | $0,0936 | 12/8/180 (+2,0 [−2,5; +6,5]) |
| `hdrfilter` | **51,0** | 66,63 | **63,86** | 244.329 | $0,2534 | 9/**38**/153 (**−14,5 [−21,0; −8,0]**) |

BIF paired 95% CI vs `v1_raw`: `v1_clean` −0,44 [−2,96; +2,00]; `hdrfilter`
**−10,10 [−14,09; −6,37]** — BIF agrees with EM that `hdrfilter` is harmful.
BIF scored on 196–199/200 questions per arm (2–4 empty predictions skipped);
computed with `run_eval.py --metrics bif`, checkpoint
`outputs/models/vinli-xlmr-large-4label/vinli-xlmr-large-4label/checkpoint-best`,
`--bif-entailment-id 0`. Artifacts: `outputs/evaluation/bif_new/d13_*.json`.

**This is the project's first intervention with a CI excluding zero, and
the effect is harmful.**

Failure mechanism (analysis of 38 losses):

- The filter keeps an average of **39,8% of columns**.
- **179/200 questions have no selected rows.** Since 77,8% of tables lack a
  left header column, a header-only table provides column names but nothing
  from which the LLM can select rows.
- Only **7/38** losses result from losing the answer cell; **17/38 lose at
  least one condition column** (condition-column retention: 54,7% among losses
  versus 86,5% among ties). The failure is **losing columns needed to locate
  the row**, rather than losing answer columns.
- Solver prompt tokens fall 52,8%, but the filter call generates an average
  of 1.807 completion tokens. **Total tokens rise 75,9%, and cost increases
  2,75-fold.**

A prereun written analysis predicted these outcomes. Details:
`docs/research/enhance_poma/2026-09-20-llm-header-filter-review.md`.

---

## Parser-fix A/B (n=991, two full controls)

| Variant | EM | BIF |
|---|---:|---:|
| `legacy` (old parser) | 67,91 | 75,28 |
| `fixed` (corrected parser) | 66,50 | 74,91 |
| **Difference** | **−1,41 [−3,13; +0,30]** | **−0,37 [−1,30; +0,56]** |

BIF agrees with EM: the parser fix does not change scored quality either
way. Same 991-question artifacts as the EM audit
(`outputs/v3lite/arms_ab_legacy.json` / `arms_ab_fixed.json`).

- Only 72/991 question outcomes differ (29 wins, 43 losses); reversing seven
  outcomes would reverse the sign.
- Among the 325 questions whose tables actually changed: 64,62 → 62,46.
- Wins and losses do **not** arise simply from corrupted tables. Correctly
  splitting cells lets the model choose a smaller span, which sometimes
  matches the gold answer and sometimes does not.
- **Keep the fix because it is faithful to the data; do not claim higher EM.**
- An earlier incorrect fix (`get_text(" ")`, inserting spaces at **every**
  text node) corrupted already correct cells: **−3,41 points, 7 wins /
  21 losses** on 410 questions. The old test missed this because its only
  inline case (`<b>Hà</b> Nội`) already had a space.

---

## N1 — Variation across identical runs (n=900 shared questions)

Ran **the exact same configuration twice** (model, provider, prompt,
cached hints, and parser all identical):

| | EM | BIF |
|---|---:|---:|
| Run 1 | 68,33 | 75,22 |
| Run 2 | 67,89 | 75,09 |
| **Difference** | **−0,44** | **−0,12 [−1,04; +0,78]** |

BIF drift is smaller than EM drift here, but both are non-zero on an
unchanged configuration — the same qualitative point either metric makes.
Artifacts: `outputs/v3lite/drift_run1.json` / `drift_run2.json`.

**98/900 answers (10,9%) changed wording despite no configuration change.**
Together with D11's 68,35 versus 66,63 (a 1,7-point gap), there are now
**two observations of run variation: 0,44 and 1,7 points**. This is not enough
to define a "noise floor of X"; at least three runs are needed.

---

## Hybrid BM25 + PhoBERT retrieval (n=476, no API calls) → REJECTED

The decision rule was **fixed in code before running**: accept hybrid
retrieval only if its `recall@3` matches or exceeds BM25's `recall@20`.

| Ranker | @1 | @2 | @3 | @5 | @10 | @20 |
|---|---:|---:|---:|---:|---:|---:|
| BM25 (current) | 83,8 | **92,4** | **94,5** | **96,2** | **98,1** | 99,2 |
| PhoBERT dense | 80,2 | 87,6 | 89,3 | 91,2 | 95,0 | 96,6 |
| Hybrid normalized sum (alpha=0,5) | **84,9** | 91,2 | 93,3 | 95,2 | 96,8 | 98,3 |
| Hybrid RRF | 83,4 | 90,3 | 92,4 | 94,1 | 96,2 | **100,0** |

**`hybrid_rrf@3` = 92,44 < `bm25@20` = 99,16 → REJECTED.**

- Pure dense retrieval **loses to BM25 at every k**. Table rows are short
  strings containing codes, numbers, and proper names, where exact lexical
  matches help and embeddings blur identities.
- End-to-end upside is already small: BM25 misses 41/784 questions at k=20,
  but **37/41 are aggregation questions already blocked by the cue rule**.
  Even perfect retrieval is worth **under 0,1 EM points**, below observed
  run variation of 0,44–1,7.
- **Limit:** `vinai/phobert-large` is a masked LM, not a sentence embedding
  model. This measurement rules out **direct use of PhoBERT**, not dense
  retrieval in general.
- **Better next step:** lower k. The answer-row BM25 rank has median 0,
  p90 = 2, and p99 = 17; k=20 retains many rows to catch one usually
  ranked in the top three.

---

## Second and third backbones

### Gemma-3-4B-IT via OpenRouter (n=543, incomplete run, legacy)

| System | EM | F1 | ROUGE-1 | METEOR | BIF |
|---|---:|---:|---:|---:|---:|
| POMA-first | 26,70 | 48,98 | 34,41 | 35,14 | 51,06 |
| Zero-shot | **39,59** | **57,31** | **47,07** | **47,83** | **60,95** |
| **Difference (POMA − ZS)** | **−12,89 [−17,13; −8,66]** | −8,33 [−12,04; −4,56] | — | — | **−9,89 [−12,60; −7,14]** |

**The CI excludes zero: POMA clearly loses to the single-call baseline on
this weaker backbone.** BIF agrees, and its own CI also excludes zero. This
is the clearest answer to "Have you tested a second backbone?" However, the
run covers only **543/992 questions**, not the full Q2 matrix. Artifact:
`outputs/q2_revision/openrouter_google_gemma-3-4b-it/full/reports/`.

**BIF note:** one question (`99924_3_130`) was dropped from both arms (542/543
remain) because its Zero-shot prediction is a 1.062-character list that
crashes PhoBERTScore's alignment with an `index out of bounds` error — a
reproducible bug in scoring very long hypotheses, not a data problem. Command:
`run_eval.py --metrics bif --bif-nli-model
outputs/models/vinli-xlmr-large-4label/vinli-xlmr-large-4label/checkpoint-best
--bif-entailment-id 0`, POMA scored with `--candidate-policy first` (matching
the EM protocol), Zero-shot with `single-required`. Artifacts:
`outputs/evaluation/bif_new/gemma_poma.json` / `gemma_zero_shot.json`.

### SEA-LION v3 8B IT (local run on Kaggle, vLLM)

| Variant | n | EM | F1 | ROUGE-1 | METEOR | BIF |
|---|---:|---:|---:|---:|---:|---:|
| Zero-shot (full test) | 992 | 49,50 | 66,09 | 58,72 | 59,93 | 68,24 |
| Few-shot (full test) | 991 | 49,45 | 66,27 | 58,79 | 59,76 | 68,34 |
| CoT (full test) | 991 | 47,83 | 64,46 | 56,79 | 57,73 | 67,20 |
| POMA (stratified 500 subset) | 486 | 43,00 | 60,07 | 50,45 | 50,88 | **59,89** |

**There is no paired POMA-versus-baseline comparison on the same 486-question
subset yet.** Moreover, the three baselines have different n values
(992 / 991 / 991), and the ZS − FS gap is just 0,05 points, or **one
question**, so do not rank ZS against FS for this backbone. Artifact:
`outputs/notebooks/sea_lion_v3_8b_it/`.

**BIF note:** Zero-shot/Few-shot BIF scored on 893/886 of 992/991 questions
(rest have empty predictions, skipped by BIF automatically). CoT dropped one
question (`56_2_116`) for the same PhoBERTScore overlong-hypothesis crash as
the Gemma case above (1.101-character prediction); scored on 897/990. POMA's
59,89 is on the full 486, matched exactly to the EM protocol
(`--candidate-policy first`, `dataset/qas_test_500_stratified.json`) — this is
why it needed the stratified qas file rather than the full test set, unlike
the other three arms. Artifacts: `outputs/evaluation/bif_new/sealion_*.json`.

### Actual Q2 matrix status (avoid rerunning completed work)

| Backbone | Available | Missing |
|---|---|---|
| Qwen3-8B | `full/raw/` (poma + traces + specialists + refiner + normalization), `full/finalized/poma_gsa.json`, `full/reports/` (poma_candidate_max, poma_gsa, poma_diagnostic, baselines_candidate_max) | — (effectively complete) |
| Gemma-3-4B-IT | `full/raw/poma.json` + traces + `zero_shot/`, `full/reports/` (poma_eval_543, poma_vs_zero_shot_543, zero_shot_raw) | **No `finalized/` directory**; few-shot / CoT / TD not run; only 543/992 scored |

Note: `docs/research/Khoi/fix-plan-POMA.md` says there is no
`outputs/q2_revision/`. **That document is outdated**; the full Qwen
branch finished after it was written.

### External baselines: CoAgt and Chain-of-Query

Only **two-question smoke tests** have been run with `openai/gpt-4o-mini`
(`outputs/baselines/coagt/smoke-gpt4o-mini/` and
`coq/smoke-gpt4o-mini/`). **Required warning:** the vendored
Chain-of-Query lacks the clause-agent module. Its adapter always records
`pipeline_mode: "coq_base_sql_fallback"`; **do not report this as a full
Chain-of-Query result.**

## Other completed supporting experiments

- **Fine-tuned a four-label ViNLI XLM-R Large** (`reproductions/vinli/`) for
  BIF. The ViNLI paper (COLING 2022) reports 85,99 accuracy / 86,10 macro-F1.
  **Exact reproduction is blocked because it released no split IDs, seed, or
  training code.** This is a replication-style model and cannot be compared
  directly with their Table 6.
- **Audited 150 dev answers**
  (`outputs/audits/open_vitabqa_dev_answer_audit_150.md`).
- **Ablated POMA without Answer Normalization** on GPT-4o
  (`outputs/poma/ablation/`).
