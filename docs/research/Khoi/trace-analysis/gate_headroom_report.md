# POMA-Boost v2: can a disagreement gate help? Offline evidence from existing POMA outputs

Everything here was computed offline from the files in `poma_repo/outputs` and `poma_repo/dataset`. No LLM or API calls were made. Correctness is always the repo's own `evaluation.exact_match.score_sample`, as the code currently stands in the repo. Numbers labelled **ESTIMATE** involve extrapolation or a modelling choice. Every other number is **MEASURED**.

Scripts and JSON are in `analysis/`: `common.py`, `q1_integrity.py`, `build_instances.py`, `analysis.py`, `q8_q11.py`, `refine.py`, `q1_extra.py`. The consolidated JSON is `gate_headroom_results.json`, and the per-instance table is `instances_with_cats.json`.

## TL;DR

1. **Per-specialist outputs exist for only 592 of 992 questions (hp run).** They are the contiguous tail, positions 400–991 of the main output order. The other 400 have only the final candidate set.
2. **Table 6 "w/o AN" (68.41) was computed on those 592 questions, with Qwen3-8B.** It is not a 992-question number and it does not come from the gpt-4o-mini ablation files. 68.41 = 405/592 exactly; no integer k gives k/992 = 68.41%. With the current evaluator, raw best-of-K on the 592 is 404/592 = 68.24. Meanwhile "with AN" (80.24) is on 992. On the same 592 questions the ablation is **68.24 → 79.56**. **177 / 17.84% cannot be reproduced**: the 592 traces show 67 wrong→right flips and 0 right→wrong. 177 equals 796 − 619, which is paper POMA EM minus paper ZS EM (80.24 − 62.40).
3. **The gate has almost nothing to act on.**
   - 88.7% of questions route to exactly one specialist.
   - Among traced 2-specialist questions, only 8 of 64 disagree after canonicalization. That is 1.35% of traced questions, and an ESTIMATED ≈1.4% of 992.
   - 92.9% of best-of-K errors are invisible to the gate: 171 single-specialist wrong plus 11 agree-and-wrong, out of 196.
   - A perfect resolver of specialist disagreements adds **+3 questions (+0.30 EM)** to single-answer POMA on the traced subset. The ceiling across all 992 is ≤ +7 (+0.71).
4. **Best-of-K accounts for 12.50 EM points (124 questions).** Single-answer POMA (first candidate) scores **67.74**, statistically indistinguishable from FS at 67.34 (paired difference +0.40, 95% CI [−2.12, 3.02]). 117 of the 124 best-of-K-only wins are the correct surface form inside one specialist's variant set, 49 of them yes/no synonyms. Only ≤7 involve a second specialist or a hedge.
5. **Answerability errors are almost all unanimous.** All 46 gold-Null questions were routed to a single specialist. A hedge (mixed Null/non-Null) trigger would see 8 of 64 answerability errors (12.5%) and 0 of 11 hallucinations.
6. **Neither confidence nor evidence grounding makes a usable verifier.** 77.9% of confidences are exactly 1.0 (AUROC 0.59–0.66), and in 5 of 8 disagreements both specialists report the same confidence. Evidence cites real table cells in 91.8% of non-null outputs whether right or wrong (AUROC 0.52). All traced hallucinations cite fully grounded cells.
7. **Cross-method disagreement is where the headroom is.** Gating on POMA-first ≠ FS (fires on 217 of 992) and taking a 5-way vote gives **69.86** single-string (+2.12). A question-cue yes/no formatter learned on train gives **71.27** (+3.53, ESTIMATE). The oracle over {POMA-first, FS, ZS, CoT, TD} is 79.64.

---

## Q1. Data integrity

### Instance counts

| File | Records |
|---|---:|
| `poma/qwen/poma_qas_test_qwen3_8b_hp.json` (dict: predictions/evaluation/stats) | 992 |
| `poma/qwen/poma_qas_test_qwen3_8b_no_hp.json` | 992 |
| `poma/qwen/*_hp_traces.json`, `specialists/`, `refiner/`, `normalization/` (hp) | **592** each, same ids |
| same four files for no_hp | **621** each |
| `poma/ablation/..._gpt4o_hp_without_answer_normalization.json` | 395 (597 skipped: "missing stage 3") |
| `poma/ablation/..._gpt4o_no_hp_without_answer_normalization.json` | 983 (9 skipped) |
| `poma/hint_predictor/qas_test.json` | 992 |
| `baseline/qwen/full_{zs,cot,td,few_shot}/qwen3-8b.json(l)` | 992 each |

- **No file holds per-specialist outputs for all 992 questions.**
- The hp traces are exactly main-output positions 400–991, and the no_hp traces are positions 371–991. Both look like the tail of a resumed run.
- For those 592 questions, the traces' `normalized_answers` equal the main file's `predicted_answer`.
- `router.specialist_names == predicted_hints` on all 592, so the number of specialists is known for all 992 from `predicted_hints`.
- The traced and untraced subsets have similar profiles: gold-Null 24/592 vs 22/400, and similar hint mix. List is 6.8% vs 4.0% and Why is 2.2% vs 3.5%.

### Which model produced the ablation files

The ablation files are **gpt-4o-mini**. A least-squares fit of `cost_usd` on the token counts gives exactly $0.150/M prompt and $0.600/M completion. The same fit on the Qwen3-8B files gives $0.050/M and $0.400/M.

### EM under the current repo evaluator

| System | EM | Stored/paper EM | Note |
|---|---:|---:|---|
| POMA hp best-of-K | **80.24** (796/992) | 80.24 | Paper value reproduced. F1 88.25 (paper 88.23), R1 84.48 (86.07), MET 85.17 (84.50) |
| POMA no_hp best-of-K | 80.34 | 80.24 stored / 80.04 paper | Three different values |
| FS / ZS / CoT / TD | 67.34 / 63.10 / 59.48 / 59.98 | 67.14 / 62.40 / 59.17 / 59.38 | Stored per-sample scores come from an older evaluator (list order-sensitive, no trailing-'.' strip) |
| gpt-4o-mini ablation, hp | 57.97 on 395 (229) | — | 23.08% if the 597 missing count as wrong |
| gpt-4o-mini ablation, no_hp | 59.92 on 983 (589) | 59.61 stored | 59.38% over 992 |

**Qwen3-8B without AN** (hp traced 592, raw `3_specialists[*].answer`):

| Setting (592 subset) | EM | F1 | R1 | MET |
|---|---:|---:|---:|---:|
| (a) best-of-K over raw specialist answers | **68.24** (404) | 81.37 | 76.56 | 77.47 |
| (b) first specialist, single answer | 67.74 (401) | 81.05 | 76.17 | 77.12 |
| with AN, best-of-K, same 592 | 79.56 (471) | 87.96 | 84.44 | 84.98 |
| with AN, first candidate, same 592 | 67.74 (401) | 81.04 | 76.20 | 77.13 |
| Paper Table 6 "w/o AN" | 68.41 (= 405/592) | 81.31 | 78.98 | 75.60 |

The no_hp traced subset (621) behaves the same way: raw best-of-K 68.60, with AN 79.23, 66 flips, 0 right→wrong.

### Verdict on the 68.41 vs 62.40 contradiction

**MEASURED:**
- Table 6 "w/o AN" is the Qwen3-8B raw specialist best-of-K on the 592 traced questions. The residual 1-question difference, and the R1/MET differences, go in the same direction as the evaluator drift seen on the main file.
- It was paired with the 992-question 80.24, so the table compares two different populations.
- The "177 flips / 17.84%" cannot come from the traces. They show 67 flips on 592.

**ESTIMATE:**
- On the traced subset, first-candidate correctness equals raw-first correctness on 590 of 592 questions. The untraced first-candidate EM is 271/400 = 67.75%.
- Extrapolating, w/o-AN on 992 ≈ 68.25%, and AN flips on 992 ≈ 112–119.
- Getting 62.40 would require the untraced 400 to score 53.75% raw, while their first-candidate EM is 67.75%.
- So the reviewer's "implied 62.40" does not hold for Qwen w/o-AN. It only equals ZS EM.

## Q2. Specialists per question

| Routing | 1 | 2 | 3 | Single share | Mean |
|---|---:|---:|---:|---:|---:|
| hp (predicted hints), all 992 | 880 | 112 | 0 | **88.71%** | 1.113 |
| hp, traced 592 | 528 | 64 | 0 | 89.19% | 1.108 |
| gold hints (no_hp routing), all 992 | 911 | 78 | 3 | 91.83% | 1.085 |

For 88.7% of questions "disagreement" is undefined, because only one specialist runs.

## Q3. Disagreement among the 64 traced 2-specialist questions

| Agreement level | Disagree | % of 64 |
|---|---:|---:|
| L0 raw string differs | 10 | 15.6 |
| L1 repo `normalize_text` differs (NFC, lowercase, whitespace collapse, trailing '.') | 10 | 15.6 |
| L2 `canon_equal`: L1 plus order-free multiset of list items (repo `parse_list_items`), Null==Null | 8 | 12.5 |
| L3 repo AN deterministic variant sets (booleans, numbers, units, dates, rank, context strip) intersect under L2 | 8 | 12.5 |
| **L4 recorded per-specialist AN variant sets (incl. LLM variants and Null forcing) intersect under L2** | **8** | **12.5** |

- Only 2 of the 10 raw disagreements are surface-only: list order ("Lombardia, Lazio, Sicilia" vs "Lazio, Lombardia, Sicilia") and delimiter (","/";").
- Raw hedges (mixed Null/non-Null): 2.
- Gate firing rate: 8 of 592 traced = **1.35%**. Across 992 it is at least 14, because 6 more untraced 2-specialist questions have mixed candidate sets. An ESTIMATE of ≈14 (1.4%) follows from 8/64 × 112.
- no_hp robustness (52 traced multi-specialist questions, gold routing): 10 disagree at L4, 5 have at least one specialist correct, and 7 agree while wrong.

## Q4. Gate headroom (MEASURED; all 992)

**Per-specialist correctness** is best-of-K within that specialist's own AN variant set.
- Single-specialist questions: the recorded set is used, because it equals the specialist's set.
- 2-specialist questions: the recorded AN LLM responses are replayed through the deterministic AN rules. An emulation of the older list-variant rule is needed (see caveats).
  - 585 of 592 recorded sets reproduce exactly, and union correctness is identical on 592 of 592.
  - For multi-specialist questions, 63 of 64 reproduce exactly.

**Agreement** uses L4.

| Category | n | % of 992 | Best-of-K errors (196) | % of best-of-K errors | First-candidate errors (320) | % of first-cand. errors |
|---|---:|---:|---:|---:|---:|---:|
| single & correct (first variant) | 603 | 60.79 | 0 | 0 | 0 | 0 |
| single & correct only via a non-first variant | 106 | 10.69 | 0 | 0 | 106 | 33.12 |
| **single & wrong** | **171** | 17.24 | 171 | **87.24** | 171 | 53.44 |
| agree & correct (all correct) | 45 | 4.54 | 0 | 0 | 6 | 1.88 |
| **agree & wrong** | **11** | 1.11 | 11 | **5.61** | 11 | 3.44 |
| disagree & ≥1 correct (recoverable) | 4 | 0.40 | 0 | 0 | 3 | 0.94 |
| disagree & none correct | 4 | 0.40 | 4 | 2.04 | 4 | 1.25 |
| untraced 2-specialist, best-of-K correct | 38 | 3.83 | 0 | 0 | 9 | 2.81 |
| untraced 2-specialist, best-of-K wrong (no candidate correct) | 10 | 1.01 | 10 | 5.10 | 10 | 3.12 |

There were no "agree & only one correct" cases.

The traced-only version (592, fully observed) shows the same shape:
- single wrong: 106 (87.6% of 121 best-of-K errors)
- agree & wrong: 11 (9.1%)
- disagree & none correct: 4 (3.3%)
- disagree & recoverable: 4, of which 3 have a wrong first candidate

**Upper bounds:**
- Any selector over existing candidates is capped at best-of-K, **80.24**. Under best-of-K scoring, a perfect resolver recovers **0** errors: every recoverable disagreement is already counted as correct.
- Single-string scoring:
  - first candidate: 67.74 (672)
  - with a perfect specialist resolver on traced disagreements: **675 (68.04%)**, a gain of 3
  - adding the ceiling from untraced 2-specialist questions (1 likely-second-specialist hit plus 3 hedged sets whose first candidate is Null) raises the bound to ≤ **679 (68.45%)**
- Errors invisible to a disagreement gate:
  - of best-of-K errors: 182/196 (**92.9%**), rising to 192/196 (98.0%) if the untraced wrong ones are counted, which no selector can fix
  - of first-candidate errors (320):
    - 182 (56.9%) are invisible and wrong in content
    - 106 + 6 = 112 (35.0%) are surface-form choices inside one agreed answer, which a disagreement gate also cannot see
    - 9 are untraced 2-specialist questions with a correct candidate somewhere in the set; at most 4 of them are cross-specialist
    - the rest: 3 disagree & recoverable, 4 disagree & none correct, 10 untraced & wrong

## Q5. Single-answer EM and best-of-K inflation

- Best-of-K 80.24 vs first candidate **67.74**. Inflation is **12.50 points** (124 questions); paired bootstrap 95% CI [10.48, 14.62].
- Candidate set size K: mean 3.65, median 2, p95 15, max 70, K=1 for 33.1%. The largest sets come from list delimiter × adjacent-swap permutations: K = 5n.
- Single-answer policies on the traced 592 all give **401/592 (67.74)**:
  - first specialist raw
  - first specialist's first AN variant
  - majority over specialists (with ≤2 specialists this reduces to ties broken by order)
  - maximum confidence

  Best-of-K on the same 592 gives 471.
- **Where the 124 best-of-K-only wins come from**, classified by provenance:

| Source | Count |
|---|---:|
| Deterministic AN variant of the first candidate | 106 |
| … boolean synonyms (Có/Đúng/Phải, Không/Sai/Không phải) | 49 |
| … numbers and units | 28 |
| … dates | 16 |
| … text (context strip, spacing, rank) | 12 |
| … list | 1 |
| LLM-normalizer variant only | 10 |
| List space-joined variant | 1 |
| Second specialist (traced) | 3 |
| Untraced, not derivable from the first candidate (likely second specialist) | 1 |
| Hedged set, first candidate Null, a later non-Null candidate correct | 3 |

- ESTIMATE: a yes/no formatter keyed on question cue and polarity, learned on `qas_train.json`, picks the gold word for 177 of 191 test booleans when given the true polarity. Applied to POMA's first candidate it lifts single-answer EM to **71.27** (+3.53).

## Q6. Null / answerability (46 gold-Null, 946 answerable)

| Rule | False abstentions | Hallucinations |
|---|---:|---:|
| Candidate set contains Null (paper; repo `prediction_is_unanswerable`) | **53** | **11** |
| Literal "Null" only | 53 | 11 |
| Single answer (first candidate) | 50 | 11 |
| Stored per-sample answerability in the hp file | 53 | 11 |

- The reviewer's figure of 12 hallucinations is not reproducible under any of these rules.
- 8 candidate sets contain both Null and non-Null. All 8 are gold-answerable questions; 2 are traced and 6 untraced. 4 of the 8 are EM-correct through their non-Null candidate, so the same question counts both as EM-correct and as a false abstention.

**False abstentions under the set rule (53):**
- single-specialist Null: 39
- 2-specialist unanimous Null: 6
- mixed (hedge): 8
- All 40 Null outputs from traced false abstentions were emitted by the specialists themselves; none were forced by the AN Why/How rules.

**Hallucinations (11):** all 11 are single-specialist non-Null. **All 46 gold-Null questions were routed to a single specialist.**

**What a hedge-only trigger would see:**
- 8 of 64 answerability errors (**12.5%**) under the set rule, and 5 of 61 (8.2%) under the single-answer rule
- 0 of 11 hallucinations
- 87.5% of answerability errors are unanimous

A "prefer the first non-Null candidate when the set is mixed" rule raises correct answers among the 8 mixed sets from 1 to 4 (+3).

## Q7. Confidence

- There are 656 traced specialist outputs. Confidence is exactly 1.0 for **77.9%** and ≥ 0.9 for 93.45%. Values: 1.0 ×511, 0.95 ×94, 0.5 ×14, 0.0 ×13, 0.15 ×9, 0.9 ×7, others ≤ 3.
- AUROC of confidence for predicting specialist correctness:
  - against AN best-of-K correctness: 0.663
  - against first-variant or raw correctness: 0.591
  - non-Null outputs only: 0.588
  - The higher values are mostly driven by low confidence on Null outputs.
- Accuracy by confidence bucket: 1.0 → 85.3% (n=511); [0.9, 1.0) → 61.8% (102); < 0.7 → 40.0% (40).
- In the 8 disagreement cases: first specialist 1/8 correct, max-confidence 1/8 (confidences tied in 5 of 8), oracle 4/8. For comparison, FS is correct in 5/8 of them, ZS 5/8, TD 5/8, CoT 3/8.

## Q8. Evidence grounding (flattened table rebuilt with the repo's `create_representation`)

- **The evidence is not quoted text.** Only 0.38% of 1,596 evidence items are literal substrings of the flattened table. Items are formatted as "row-key | column-header | value" triplets.
- **At cell level, almost every part is a real cell.** 97.36% of the parts (split on "|", `<header>` removed) exactly match a table cell. 91.78% of 596 non-Null outputs have every part matching exactly.
- **Grounding does not predict correctness.**
  - AUROC 0.517 (exact fraction) and 0.526 (substring).
  - Fully grounded outputs are 83.7% correct, not fully grounded ones 77.6% (n=49). The base rate is 83.2%.
  - "Answer appears in table": AUROC 0.570.
  - Wrong answerable outputs are fully grounded 88.5% of the time; correct ones 92.3%.
- **It does not work as a Null-checker either.**
  - All 4 traced hallucinated outputs on gold-Null questions cite fully grounded cells.
  - The rule "force Null if evidence is not fully grounded" flags 49 outputs: 0 gold-Null and 38 correct answers, which would become false abstentions.
  - False-abstention Null outputs cite evidence in 39 of 40 cases (33 fully grounded). Correct Null outputs cite grounded evidence in 13 of 20. AUROC 0.66.
- A free deterministic grounding check therefore cannot serve as a verifier: the failures are in reasoning over real cells, not fabricated cells.

## Q9. Heterogeneous voters (all single-string unless noted; current evaluator)

| System | Single string | + same deterministic AN variants (best-of-K) |
|---|---:|---:|
| POMA (first candidate) | 67.74 | 78.33 |
| FS | 67.34 | 75.81 |
| ZS | 63.10 | 68.45 |
| CoT | 59.48 | 65.83 |
| TD | 59.98 | 66.53 |
| POMA best-of-K (AN incl. LLM variants) | 80.24 | — |

**Paired bootstrap** (repo `paired_bootstrap_ci`, 10k resamples):

| Comparison | Difference | 95% CI |
|---|---:|---|
| POMA best-of-K − FS | +12.90 | [10.08, 15.83] |
| POMA-first − FS | **+0.40** | [−2.12, 3.02] |
| POMA-first+det − FS+det | +2.52 | [0.10, 4.94] |
| POMA best-of-K − FS+det | +4.44 | [2.12, 6.75] |

**2×2 tables:**
- POMA-first vs FS: both right 588, only POMA 84, only FS 80, both wrong **240** (104.5 expected under independence, 2.30×). Cohen's κ 0.623, φ 0.623.
- POMA best-of-K vs FS: 622 / 174 / 46 / 150 (64.0 expected, 2.34×), κ 0.439.
- Pairwise κ on correctness ranges from 0.49 to 0.75. The highest are CoT~TD 0.751 and ZS~CoT 0.728.

**Oracle (at least one correct):**
- {POMA-first, FS, ZS, CoT, TD}: 79.64
- {POMA best-of-K + four baselines}: 87.50
- POMA-first + FS: 75.81
- all five with deterministic variants: 87.10
- POMA-first is wrong but some baseline is right on 118 questions; for POMA best-of-K the figure is 72.

**Votes:** clusters are formed where deterministic variant sets intersect; the representative answer is POMA's if it is in the winning cluster; ties go to the cluster with the earliest member in the order POMA, FS, ZS, CoT, TD.

| Vote | EM | Change vs POMA-first |
|---|---:|---:|
| 5-way vote, single string | 67.64 | −0.10 |
| 5-way vote, det-K | 75.91 | — |
| Gate on POMA-first ≠ FS (fires on 217) → 5-way vote | **69.86** | +2.12 |
| Same gate, keeping POMA's full set when POMA wins, best-of-K | 80.44 | +0.20 vs 80.24 |
| Gate on specialist disagreement (8) → vote over 2 specialists + 4 baselines | 68.15 | +0.41 |
| POMA-first Null → FS | 68.65 | +0.91 |

Baselines have no AN, so both scorings are shown.

## Q10. By gold question type (multi-label; an instance counts under each of its hints)

| Type | n | Best-of-K EM | First EM | FS EM | 2-spec | single wrong | agree & wrong | disagree ≥1 correct | disagree none | untraced 2-spec wrong | surface-only (best-of-K ok, first wrong) | gold Null |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Why | 27 | 44.44 | 40.74 | 55.56 | 1 | 14 | 0 | 0 | 0 | 1 | 1 | 17 |
| MathematicalReasoning | 195 | 81.03 | 64.62 | 67.69 | 28 | 31 | 2 | 1 | 1 | 3 | 32 | 0 |
| List | 56 | 69.64 | 66.07 | 50.00 | 6 | 13 | 2 | 0 | 1 | 1 | 2 | 1 |
| MultiConditions | 174 | 79.31 | 69.54 | 73.56 | 51 | 28 | 3 | 2 | 2 | 3 | 17 | 0 |
| YesNo | 155 | 89.68 | 59.35 | 58.06 | 22 | 15 | 1 | 0 | 0 | 0 | 47 | 1 |
| What | 183 | 81.42 | 74.86 | 71.58 | 11 | 29 | 3 | 1 | 1 | 1 | 12 | 1 |
| When | 120 | 85.00 | 71.67 | 69.17 | 6 | 16 | 0 | 0 | 0 | 2 | 16 | 5 |
| Where | 99 | 78.79 | 74.75 | 77.78 | 7 | 17 | 2 | 1 | 0 | 2 | 4 | 5 |
| Who | 54 | 74.07 | 68.52 | 68.52 | 10 | 13 | 1 | 1 | 0 | 0 | 3 | 9 |
| How | 13 | 46.15 | 46.15 | 38.46 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 8 |

- **Why:** 14 of 15 errors are single-specialist; none is recoverable by the gate. FS beats POMA here (55.56 vs 44.44).
- **MathematicalReasoning:** 33 of 37 errors are invisible. Its large best-of-K gap (32 questions) is surface form, mainly number and unit variants.
- **List:** 15 of 17 errors are invisible and 0 are recoverable.
- **MultiConditions:** 31 of 36 errors are invisible and 2 are recoverable.
- **YesNo:** 47 surface-only wins; single-answer POMA (59.35) is on par with FS (58.06).

## Q11. Hint predictor and tokens

**Hint predictor** (repo `evaluate_hint_metrics`, main hp run's `predicted_hints` vs gold):
- Exact-set accuracy 65.02%, Jaccard 0.711, micro P/R/F1 0.714 / 0.732 / 0.723, macro F1 0.721.
- Per label (P / R):

| Label | Precision | Recall |
|---|---:|---:|
| MultiConditions | 0.61 | **0.40** |
| MathematicalReasoning | **0.60** | 0.94 |
| What | 0.68 | 0.61 |
| How | 1.00 | **0.31** |
| Why | 1.00 | 0.70 |
| YesNo | 0.77 | 0.86 |
| List | 0.80 | 0.80 |
| When | 0.88 | 0.85 |
| Where | 0.74 | 0.83 |
| Who | 0.87 | 0.74 |

- Top confusions: MultiConditions→YesNo 28, What→MathReasoning 25, MultiConditions→MathReasoning 19, MultiConditions+YesNo→YesNo 15.
- `outputs/poma/hint_predictor/qas_test.json` is a **different run**. Its hint sets match the main run on 549 of 992, and its exact-set accuracy is 50.1%.

**Specialists and tokens:**
- Mean specialists per question: 1.113 with predicted hints vs 1.085 with gold hints, so routing adds +2.6% specialist calls.
- Total tokens rise **+70.12%** (19,077,260 vs 11,213,901): prompt +79.68%, completion +34.25%.
- ESTIMATE, from a regression that uses ZS prompt tokens as a proxy for table size: extra prompt tokens per question ≈ 2,530 constant (hint-predictor instructions) + 1.09 × table size (≈ 4,760 at the mean) ≈ 7,290, against an observed 7,113. Only ≈ 146 per question come from extra specialists. **The +70% is the hint-predictor call reading the full table, not extra routing.**
- Paired per-question change in total tokens: +7,764 when both runs route to one specialist (n=827); +15,253 when hp routes to 2 and gold to 1 (n=84).

**Accuracy with predicted vs gold hints:** under the current evaluator, predicted hints do not beat gold hints. Best-of-K is 80.24 (hp) vs 80.34 (no_hp); first candidate is 67.74 vs 68.35. The paper reports 80.24 vs 80.04.

---

## What this implies for POMA-Boost v2

1. **An intra-POMA "Disagree?" gate is close to a no-op on this backbone.** MEASURED: it fires on about 1.4% of questions. Under single-answer scoring its ceiling is +0.3 to +0.7 EM; under best-of-K it is 0. The planned row/column verifier and tie-breaker would run about 14 times on the test set.
2. **Switching to single-answer scoring costs about 12.5 EM up front.** MEASURED: 80.24 → 67.74, which equals FS. Most of that is surface-form choice inside one answer, not specialist conflict.
   - The cheapest recoverable part is a deterministic formatter. ESTIMATE: the yes/no formatter alone gives 71.27.
   - Number, date and unit formatters are plausible next steps (44 questions); not estimated here.
3. **A hedge trigger for answerability sees 12.5% of answerability errors and no hallucinations.** An answerability checker has to run unconditionally, at least on single-specialist Null or non-Null outputs, and needs a signal other than evidence grounding and self-confidence. Both are measured to be uninformative.
4. **To keep a gate, trigger it on cross-method disagreement, for example POMA-first vs FS** (MEASURED: fires on 21.9%, +2.12 EM single-string with a simple 5-way vote, oracle 79.64). Errors are strongly correlated (κ 0.62; 2.3× more both-wrong than independence predicts), so returns are bounded.

## Caveats

- **Per-specialist data covers only 592 of 992 hp questions**, a contiguous tail. For the 352 untraced single-specialist questions the candidate set is the specialist's set, so they are fully measured. For the 48 untraced 2-specialist questions, agree/disagree is unknown except for the 6 mixed Null/non-Null sets. Their best-of-K and first-candidate correctness is known and bounded in the tables.
- **The repo code is not the code that produced the outputs.**
  - (a) `_BOOLEAN_TRUE_VARIANTS` is mojibake on disk (`"CĂ³","ÄĂºng","Pháº£i"`), as is one unit alias. I patched them in memory only.
  - (b) The current `_list_variants` returns `[answer]`, but the recorded run added 5 delimiters × adjacent swaps. I emulated this.
  - Reconstruction: 585/592 exact, 592/592 same correctness, 63/64 exact for multi-specialist questions.
- **Evaluator drift.** The current repo evaluator differs from the one that produced the stored per-sample scores and the paper's baseline, R1 and MET numbers. It uses order-insensitive lists, strips a trailing ".", and whitespace handling differs. All my EMs use the current evaluator. POMA's 80.24 matches because of +2/−2 offsetting per-sample differences, while ZS is 63.10 here vs 62.40 in the paper.
- **Canonicalization choices are mine.** `canon_equal` does not use hints; clustering relies on the repo AN deterministic rules. Correctness never uses them; it is always the repo evaluator against gold.
- **Tiny samples.** Only 8 disagreement cases and 4 traced hallucinated outputs, so any rate computed on them is very noisy.
- **Test-set rules.** The vote and gate rules were fixed before being run, not tuned, but they are evaluated on test. The yes/no formatter was learned on train only.
- **Confidence AUROC mixes in Null outputs;** the non-Null-only value (0.588) is also reported.
- **Unresolved figures.** The reviewer's "12 hallucinations" and the paper's no_hp 80.04 could not be reproduced from the released files; I did not guess their source.
