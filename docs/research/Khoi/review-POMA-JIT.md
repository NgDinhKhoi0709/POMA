# Review: POMA (Parallel Multi-Agent Orchestration for Vietnamese Table QA)

**Reviewed for:** journal submission (informally referred to as "JIT" — see `journal-selection-POMA.md` for a scope-fit concern about this venue)
**Materials used:** `JIT_Khoi.pdf` (submitted manuscript), `POMA_Ke_hoach_chinh_sua_Q2.docx` (author's own revision plan), editor/reviewer comment screenshot, `MAPR_2026_Khoi.pdf` (ViPanelTR — same authors, same benchmark, reference paper)
**Date:** 2026-09-17

---

## Bottom line

The editor's four comments are vague, but they almost certainly come from one problem. The paper credits its gain to "multi-agent orchestration." Its own numbers put most of that gain in an answer-normalization step that any baseline could also use. The scoring also lets POMA choose the best of K candidates, while nothing says the baselines got the same chance. On top of that there are two internal arithmetic contradictions and one self-refuting sentence about budget. Adding experiments won't fix this on its own — the paper's claim has to change.

---

## Part A · Argument pass

### Load-bearing claim
Splitting Vietnamese Table QA by question type into specialist agents, run in parallel, beats a single prompt on the same backbone, and the split itself causes the gain.

### Chain trace
| # | Link | Status |
|---|---|---|
| 1 | Direct prompting fails because one call handles grounding, reasoning, answerability and formatting (§1) | **assumed**: no error taxonomy of the baseline's actual failures |
| 2 | The LLM hint predictor gives useful type labels (§3.3) | **assumed**: hint accuracy against gold labels is never reported |
| 3 | The router maps hints to specialists (§3.5) | proved, and trivial: ρ is a 1:1 lookup, so Â is just Ĥ relabeled |
| 4 | Specialists reason better than one prompt (§3.6) | **assumed**: w/o-AN vs FS is +1.27 EM (Tab. 6 vs Tab. 2), and even that number is contradicted by §5.6 (see W2) |
| 5 | Running them in parallel adds value | **assumed, and ruled out by construction** (see F4) |
| 6 | The normalizer turns outputs into matching surface forms (§3.7) | measured: +11.83 EM |
| 7 | The metric rises | measured, but under best-of-K candidate scoring (§3.1) that nothing says applies to the baselines |

### Findings

**F1 · The ablation places the gain in answer normalization, not orchestration.** *(Class 2, fatal to the framing)*
| | EM | F1 | R1 | MET |
|---|---|---|---|---|
| FS (Tab. 2) | 67.14 | 78.64 | 74.18 | 72.30 |
| POMA w/o AN (Tab. 6) | 68.41 | 81.31 | 78.98 | 75.60 |
| POMA (Tab. 6) | 80.24 | 88.23 | 86.07 | 84.50 |
| **Share of gain from AN** | **90%** | 72% | 60% | 73% |

Even if every number is correct, the abstract's closing claim about "the value of modular multi-agent orchestration" doesn't follow. AN is orthogonal to multi-agent design and would work on FS output just as well. *Remedy: new experiment (AN applied to ZS/CoT/FS) plus a rewrite of the claim.*

**F2 · "No correct output became incorrect" (§5.6) follows from the scoring, not from the design.** *(B3 definitional, weakens the contribution)*
§3.1 says the evaluator picks the best-matching candidate from the set, and §5.6 says the raw answer stays in that set. Adding candidates to a best-of-K set can never lower the score. *Remedy: writing (state K and who gets set scoring) plus a new experiment (single-answer scoring for every system).*

**F3 · The multi-candidate set can hedge on answerability.** *(Class 2, weakens the contribution)*
§5.3 says a prediction counts as Unanswerable "if the normalized candidate set contains Null" — so a set can hold both Null and a real answer, which under best-match EM is scored correct whichever way the gold label goes. *Remedy: writing (report how many sets contain both Null and non-Null) plus a new experiment.*

**F4 · "Parallel" in the title has no effect on accuracy by construction.** *(Class 1, weakens the contribution)*
Specialists don't see each other's outputs (§3.6), decoding is at temperature 0. Running them in parallel or sequentially gives identical answers; the only possible benefit is latency, and that is never measured against a sequential baseline. *Remedy: writing (retitle or add a latency ablation).*

**F5 · Consolidation is stated but never defined, and the confidence field goes unused.** *(C3/C4, weakens the contribution)*
Each specialist returns (answer, evidence, confidence, reason) but no equation or table uses confidence or evidence, and Future Work proposes "confidence-aware specialist selection" — confirming nothing uses it today. *Remedy: writing.*

**F6 · The normalizer's description doesn't fully match its implementation.** *(C2, cosmetic to moderate)*
§3.7 describes deterministic string cleanup "not to introduce new reasoning." §5.7 lists AN among the LLM calls. *Remedy: writing (clarify: it's a hybrid — deterministic for number/date/boolean/list, LLM-based for free text).*

**F7 · The paper's own baselines contradict the decomposition premise.** *(B2 self-refutation, weakens the contribution)*
TD (59.38 EM) and CoT (59.17) both score **below** ZS (62.40) in Tab. 2. Adding decomposition or reasoning to a single call hurts, undiscussed. *Remedy: writing, or make it a finding in its own right.*

**F8 · The motivation promises better answerability, and POMA does worse than its baseline on it.** *(Class 2, weakens the contribution)*
POMA scores below FS on **both** answerability classes (Fig. 2: 96.49 vs 97.38 and 51.13 vs 56.64). Working back from the reported F1 scores:

| | False abstentions | Hallucinated answers | Unanswerable correct |
|---|---|---|---|
| FS | 35 | 14 | 32 / 46 |
| POMA | 53 | **12** (text says 11) | 34 / 46 |

The orchestration adds 18 false abstentions and removes only 2 hallucinations. *Remedy: writing.*

**F9 · The "predicted hints beat gold hints" conclusion is confounded by candidate-set size.** *(Class 2, weakens the contribution)*
Tab. 5: predicted hints give +0.20 EM (2 questions out of 992) but +7.9k tokens per instance (+70%) — too much for one hint-prediction call, likely because predicted hints trigger more specialists, i.e. a bigger K under best-of-K. *Remedy: new experiment (report hints per instance for both settings) plus softer wording.*

**F10 · The budget excuse contradicts Table 7.** *(Class 1, weakens the contribution)*
§4.2 limits the study to one backbone for budget reasons; Table 7 puts a full POMA test run at **$2.06**. *Remedy: new experiment (cheap) — delete the sentence regardless.*

**A3 prior-art tiers**
- **Anticipated (grounded):** ViPanelTR (MAPR 2026), same authors, same benchmark and backbone, same CoAgt/CoQ comparisons, role-specialized parallel agents plus answer normalization. POMA doesn't cite it.
- **Adjacent:** PanelTR (Ma, 2025, cited in MAPR [17]) — multi-agent panel for table reasoning, left out of POMA's related work.
- **Query (not a finding, unverified):** question-type-conditioned prompt routing / mixture-of-prompts routing for QA generally.

### What a hostile AC reads
A 10-way question classifier feeds a lookup table of 10 prompts. The outputs go through an LLM formatter and are scored best-of-K against a baseline scored on one answer. When the formatter is removed, the multi-agent system is either about 1 EM above few-shot or about 5 EM below it, depending on which section you believe. The system is also worse than few-shot on both answerability classes and runs on a single backbone the paper claims it couldn't afford to expand, despite pricing that expansion at two dollars.

### Handoff
- `assumed_links`: 1 (no error taxonomy), 2 (hint accuracy), 4 (specialists vs FS with AN held fixed), 5 (parallel)
- `suspect_baselines`: FS/ZS/CoT/TD (scoring and AN not stated); CoAgt/CoQ (backbone not stated)
- `queued_class_3`: EM 68.41 vs the 177-flip count; 11 vs 12 hallucinations; Tab. 4 counts; the ZS gap with MAPR

---

## Part B · Full review (journal-style, NeurIPS-form scoring adapted)

### Summary
POMA is a training-free, prompt-based pipeline for Vietnamese Table QA on Open-ViTabQA. An LLM predicts one or more of 10 dataset question-type hints; a fixed map sends each hint to a type-specific specialist prompt; specialists run in parallel; an answer-normalization stage emits a set of surface variants scored best-match. On the 992-question test split with Qwen3-8B, POMA reports 80.24 EM against 67.14 for few-shot prompting.

### Strengths
- **S1.** The paper states its own weak results openly: the Why-question drop with two worked error cases (§5.2), answerability losses (§5.3), and a 3.8× cost increase (§5.7).
- **S2.** Controlled vs. cross-study comparisons are kept separate throughout; the paper repeatedly declines to claim superiority over Gemini (§5.1).
- **S3.** ZS/TD/CoT/FS share one generation wrapper and decoding setup (§4.3).
- **S4.** Tab. 6 isolates answer normalization — publishing it, even though it undercuts the framing, is to the authors' credit.
- **S5.** Code is released.

### Weaknesses (by severity)
1. **W1 · The headline attribution isn't supported** (see F1, F7). *Fix:* apply the same AN to ZS/CoT/FS, score every system with single-answer EM, reframe the contribution.
2. **W2 · Tab. 6 vs §5.6 arithmetic contradiction.** §5.6 says AN flips 177/992 (17.84%) from wrong to right and none from right to wrong; then w/o-AN EM should be 80.24 − 17.84 = **62.40**, not 68.41. Also 68.41% is not achievable as k/992 (678/992 = 68.35%, 679/992 = 68.45%). If 62.40 is correct, POMA without AN sits **4.7 EM below few-shot** and the orchestration story collapses. *Fix:* reconcile; state whether "177" counts instances or specialist outputs, and whether the w/o-AN denominator/pooling differs from plain accuracy.
3. **W3 · The scoring protocol isn't specified symmetrically** (see F2, F3). *Fix:* state K and its distribution; score baselines the same way; add a compute-matched baseline (FS × k, or self-consistency, which the paper cites but doesn't run).
4. **W4 · Worse answerability than its own baseline, unacknowledged** (see F8). Also 12 hallucinations, not 11 (4.4×, not 4.8×).
5. **W5 · One backbone, one dataset, one deterministic run, no CIs.** The +0.20 EM hint claim is 2 questions. OpenRouter at temperature 0 isn't guaranteed deterministic (requests can route to different providers). The budget sentence contradicts Tab. 7 (F10).
6. **W6 · Missing design rationale for the novel parts.** "Deterministic routing" is a 1:1 lookup whose real decision (hint prediction) is never accuracy-checked; "parallel" can't affect accuracy (F4); consolidation is undefined (F5); AN's description doesn't match its implementation (F6); no prompts anywhere in the paper.
7. **W7 · Undisclosed overlap with the same group's other paper** — see Part D.

**Minor.** Tab. 4 row counts (461+269+388=1,118) exceed 992 — clarify overlap. Tab. 5 column header says "Original," text says "Dataset." Several sentences start lowercase. Qwen3 thinking-mode on/off is unstated and can materially change EM.

### Questions (answers that would change my score)
1. Is the w/o-AN EM 68.41 or 62.40?
2. Are ZS/CoT/FS scored on one string or a candidate set, and do they pass through the same "output parsing" wrapper?
3. What are mean/max K? How many POMA sets contain both Null and a non-Null answer?
4. How many specialists activate per question with predicted vs. gold hints?
5. Which backbone did CoAgt/CoQ use?
6. Was Qwen3 thinking mode enabled?

**A result I'd accept:** with AN applied to FS and single-answer scoring for all systems, POMA stays ahead by a margin outside a bootstrap CI.

### Limitations
Cost, Why-questions, and answerability are discussed; the dataset-taxonomy dependence, the scoring asymmetry, and the single-backbone threat to validity are not.

### Scores
- Soundness: **2/4** — scoring asymmetry, the W2 contradiction, an attribution the paper's own ablation doesn't support.
- Presentation: **3/4** — clear writing; missing prompts and consolidation rule; minor table issues.
- Contribution: **2/4** — capped by F1 (fatal to the framing).
- Overall: **4/10** (Reject; journal equivalent: reject, resubmission encouraged).
- Confidence: **4/5** — arithmetic checked, no access to code/outputs at review time (see Addendum below — code was subsequently inspected).

**Justification.** If W1 and W2 resolve against the paper, a headline claim fails. A rebuttal showing POMA beats FS+AN under single-answer scoring on two or more backbones would put the paper around 6.

---

## Part C · How the editor's four comments map to the paper

| Editor comment | What it most likely points to |
|---|---|
| Purpose and problem statement unclear | Link 1 is only asserted; answerability motivation contradicts §5.3 (F8); TD/CoT < ZS undercuts the premise (F7) |
| Solution not convincing, rationale thin | Routing is a lookup, "parallel" does nothing for accuracy, consolidation undefined, AN description ≠ implementation (F4–F6); no prompts |
| Validation not robust | Scoring asymmetry (W3), W2 contradiction, one backbone, no CIs, compute-mismatched baseline |
| Contributions limited | F1, plus undisclosed overlap with ViPanelTR (Part D) |

---

## Part D · Findings that depend on the MAPR (ViPanelTR) paper

1. **The zero-shot baseline differs by 22 EM between the two papers.** Same group, same backbone (Qwen3-8B), same test set: zero-shot scores **62.40 EM / 76.16 F1** in POMA (Tab. 2) vs. **40.46 EM / 62.58 F1** in MAPR (Tab. I). POMA's own zero-shot baseline (62.40) nearly matches ViPanelTR's full system (64.72).
2. **CoAgt and CoQ numbers are identical in both papers.** MAPR states these are GPT-4o-mini runs; POMA reports them next to a Qwen3-8B system without naming the backbone.
3. **POMA doesn't cite ViPanelTR**, despite overlapping benchmark, comparisons, grant number (C2026-26-10), and design (role-specialized parallel agents + answer normalization). A journal can treat an uncited overlapping paper as redundant publication.
4. **ViPanelTR already has what POMA lacks:** three backbones, a phase ablation, and an answerability gate that improves unanswerable-class F1 over its own baseline.
5. *(Not a review point, but fix before camera-ready either way)*: MAPR's conclusion has a line of keyboard mash before "We presented ViPanelTR."

---

## Part E · Audit of the author's own revision plan (`POMA_Ke_hoach_chinh_sua_Q2.docx`)

**Correct, and worth keeping:** AN carries the gain (§2.1); best-of-K is unfair and the "zero regression" claim is tautological (§2.2); add RQs; include prompts; report hint accuracy; the predicted>gold hint claim may be noise; add a second backbone; bootstrap CIs; the answerability regression.

**What it misses, ranked by impact:**
1. The W2 Tab. 6 vs §5.6 contradiction — the plan takes 68.41 at face value; if 62.40 is right, "+1.3 EM from orchestration" becomes −4.7.
2. Overlap with ViPanelTR and the undisclosed CoAgt/CoQ backbone — not mentioned at all.
3. The 22-EM zero-shot gap between the two papers — decide which protocol is canonical before running anything new.
4. TD/CoT < ZS (F7) — free evidence for the plan's own surface-form story.
5. Null-and-answer hedging inside candidate sets (F3).
6. "Parallel" can't change accuracy (F4) — the plan's single-vs-multi-specialist ablation tests multiple specialists, not parallel *execution*; retitle or measure latency instead.
7. Confidence field unused, consolidation rule undefined (F5); AN is partly an LLM call (F6).
8. The budget sentence contradicts Tab. 7 — delete regardless of other changes.
9. A compute-matched baseline (FS × k, self-consistency) — "AN on baselines" alone doesn't equalize the 3.5× token budget.
10. Counting errors: 12 hallucinations not 11; Tab. 4 counts sum to 1,118.

**One correction to the plan:** temperature 0 through OpenRouter is not guaranteed deterministic across providers — pin a provider or report run-to-run variation.

---

## If I were you: fix list

### Must fix before resubmission — `writing`
- Reconcile Tab. 6 with §5.6 (the 177-flip arithmetic).
- State K, the scoring rule, and whether baselines get the same treatment.
- Cite ViPanelTR and PanelTR; add a differentiation paragraph.
- Name the CoAgt/CoQ backbone.
- Delete the budget sentence.
- Define the consolidation rule; say what confidence is used for, or drop the field.
- Correct 11→12 and 4.8×→4.4×.
- Rewrite the abstract/contributions around the actual attribution result.

### Must fix — `new experiment` (each ≲ $5 at the paper's own per-run cost)
- AN applied to ZS/CoT/FS.
- Single-answer EM for every system.
- FS sampled k times at POMA's token budget.
- A second (ideally third) backbone.
- Hint precision/recall per label.
- Specialists per question, both hint sources.

### Should fix if time permits
- Bootstrap CIs.
- Count of candidate sets containing both Null and an answer.
- Sequential-vs-parallel latency, or retitle to drop "Parallel."
- Full prompts in an appendix.
- Explain TD/CoT < ZS.
- Fix the Tab. 4 counts.

### Rebuttal prep
- **"Contribution is small."** Present the controlled attribution breakdown itself as the contribution, with POMA as the vehicle — don't defend "orchestration" as the source of the gain.
- **"Tailored to one dataset's taxonomy."** Can't be fully fixed without a second dataset (redesign, next-paper). State it as a scoped design choice; show hint-predictor errors degrade gracefully.
- **Answerability regression.** A verifier is a redesign; say plainly ViPanelTR's gate already handles this and combining the two is future work.

**Predicted reviewer reaction if resubmitted with only the plan's changes:** scores around 4–5. Main objection: POMA+AN doesn't clearly beat FS+AN under fair scoring, or — if a reviewer finds MAPR — redundant publication.

---

*See `fix-plan-POMA.md` for what the codebase already implements toward these fixes (more than the paper reflects) and a priority-ranked execution plan, and `journal-selection-POMA.md` for a venue-fit concern separate from all of the above.*
