# Fix Plan: POMA — code-grounded, priority-ranked

**Based on:** inspection of `github.com/NgDinhKhoi0709/POMA` (source, tests, `paper/jit-article.tex`, `paper/jit-appendix.tex`, `scripts/run_q2_experiments.ps1`, `docs/Q2_EXPERIMENT_RUNBOOK.md`), against the weaknesses in `review-POMA-JIT.md`.
**Date:** 2026-09-17

---

## Headline finding: the repo is far ahead of the paper

`paper/jit-article.tex` in the repo is substantively identical to the submitted PDF — same "68.41" w/o-AN number, same budget-excuse sentence, no RQs, no second backbone, no bootstrap CI, no hint accuracy. But the **codebase already contains, tested, a complete engineered answer to almost every "must-fix" item** in the review and in the author's own revision plan. It just hasn't been run or written up.

| What the paper/plan needs | Code that already does it |
|---|---|
| Apply AN to baselines, symmetric comparison | `src/finalization/finalizers.py::CommonAnswerNormalizationFinalizer` ("an-common") — runs the *same* `AnswerNormalizationAgent` on any raw baseline answer |
| Single-answer (non best-of-K) comparison | `src/agents/grounded_single_answer.py` + `GroundedSingleAnswerFinalizer` ("gsa") — an LLM judge selects **one** table-grounded answer, contract-validated |
| Report K and the scoring policy | `evaluation/io.py::CandidatePolicy` (`all`/`first`/`single-required`) + `evaluation/run.py::candidate_statistics` (mean/median/p95/max K, `k_equals_one_rate`) |
| Second backbone | `scripts/run_q2_experiments.ps1` already wires **Qwen3-8B and Gemma-3-4B-IT** through the identical matrix |
| Bootstrap CI / stability | `evaluation/bootstrap.py::paired_bootstrap_ci` + `paired_answerability_bootstrap_ci`, 10,000 resamples, fixed seed, paired by qa_id |
| Hint-predictor precision/recall per label | `evaluation/hint_metrics.py::evaluate_hint_metrics` — micro/macro P/R/F1, exact-set accuracy, Jaccard |
| Specialists-per-question / parallelism stats | `evaluation/parallelism.py::analyze_parallelism` — distribution, mean, median, `multi_specialist_rate` |
| Full prompts in appendix | Already **written** in `paper/jit-appendix.tex`, just commented out (`% Commented out ... as it may not be needed`) |
| A pre-registered "does this actually work" gate | `scripts/run_revision_analysis.py::interpretation_gate` — requires EM gain ≥0.02 **and** the paired 95% CI to exclude 0 |

It's genuinely tested: `tests/scripts/test_q2_runbook.py` asserts the dry-run emits exactly **66 commands** in the correct shape (8 baseline runs, 2 POMA runs, 22 finalizer calls, 32 evaluations, 2 revision analyses), with the candidate-policy locked per artifact type. `docs/Q2_EXPERIMENT_RUNBOOK.md` records "222 passed" as of 2026-07-30.

**What is not run yet:** there is no `outputs/q2_revision/` in the repo — the Full phase (992 questions × 2 backbones × {raw, AN-common, GSA, AN-native}) has never been executed. The gap between reject and accept is now mostly an **execution-and-writing gap**, not a coding gap.

### Two review findings corrected by reading the code
- **AN is a hybrid, not purely deterministic.** For `number/date/boolean/list` answers it's regex-only (no LLM); for free text it calls an LLM. §3.7's "not to introduce new reasoning" is defensible for most traffic, not all — needs one clarifying sentence, not a rewrite.
- **The best-of-K asymmetry is sharper than "unclear," it's confirmed.** `src/finalization/sources.py::_baseline_candidates` asserts a raw baseline record contains exactly one string. `evaluation/exact_match.py`: `value = 1.0 if any(exact_text_match(candidate, ...) for candidate in candidates) else 0.0`. So Table 2's ZS/CoT/FS numbers are genuinely single-candidate scored, while POMA is scored best-of-K — exact, not speculative.

---

## Ranked fix plan with reviewer-facing score impact

Baseline: **4/10, reject** (see `review-POMA-JIT.md`). Deltas are cumulative and approximate.

### Tier 1 — run the existing runbook, write up what it produces (this is the ballgame)

**1. Execute `run_q2_experiments.ps1 -Phase Full` for both backbones, then §7's two extra symmetric comparisons, then export the CSV.**
- Status: 100% built and tested, 0% run.
- Remaining work: `Preflight` (5 questions) → `Full` (992×2 backbones). Budget: ~$15–25 total, per the paper's own $2.06/POMA-run cost figure.
- **Why this is the whole review** — three possible outcomes:
  - POMA-AN-common beats FS-AN-common **and** POMA-GSA beats FS-GSA, both backbones, CI excludes 0 → the orchestration claim survives a fair test. Soundness 2→3, Contribution 2→3, **Overall 4→7 (accept-track)**.
  - POMA wins on Qwen but the margin shrinks/reverses on Gemma (matches what ViPanelTR already found — backbone-dependent gains) → narrow the claim to "helps on some backbones, primarily via normalization." **Overall 4→6 (weak-accept-track)**, contingent on the abstract rewrite (#4).
  - POMA loses to FS-AN-common under fair scoring → this *is* the RQ2 finding the plan already anticipated ("surface-form normalization matters more than orchestration"). Doesn't raise *this* paper's score, but is a legitimate reframed paper.
- Priority: **1 (blocking everything else)**.

**2. Reconcile Table 6 / §5.6's "68.41 EM w/o AN, 177 flips, 17.84%" against 992 questions** (678/992=68.35%, 679/992=68.45% — 68.41% is not k/992).
- Status: unresolved in both PDF and repo's `jit-article.tex`.
- Remaining work: cheap — trace which script produced Table 6 and re-derive it, or drop it in favor of the new symmetric tables from #1.
- Score impact: removes a soundness landmine — **~+0.5 on Soundness**.
- Priority: **1**, alongside #1.

**3. Run `evaluation/hint_metrics.py` and `evaluation/parallelism.py` over the existing Qwen traces** (`outputs/poma/qwen/poma_qas_test_qwen3_8b_hp_traces.json` already exists — no new LLM call needed).
- Status: fully built; input data already on disk.
- Remaining work: near-zero — run two functions, paste the JSON into two small tables.
- Score impact: directly answers "hint accuracy not reported" / "parallel not shown to matter." **+0.5–1.0 on Presentation/Contribution**, essentially free.
- Priority: **1 — do this first, before spending any API budget.**

**4. Rewrite abstract/contributions/§1 to match whatever Tier-1 actually shows**, using the RQ1–RQ3 framing from the revision plan.
- Status: not started; no code produces prose.
- Score impact: without this, a favorable Tier-1 result doesn't fix the review — the framing problem (F1) is independent of the numbers. **+1 on top of #1's result**, a day of writing.
- Priority: **1**, sequenced right after #1's results land.

### Tier 2 — cheap, code-supported, materially strengthens but doesn't gate accept

**5. Uncomment `paper/jit-appendix.tex`'s prompts section; cite it from the main text.**
- Status: fully written in Vietnamese-prompt form already, just behind `%`. Confirm the `PromptListing` LaTeX environment is defined (check `interact.cls`/preamble; if not, a five-line macro).
- Score impact: +0.3–0.5 Presentation, essentially free.
- Priority: **2**, same pass as #1's writing.

**6. Cite ViPanelTR (MAPR 2026) and PanelTR; add the differentiation paragraph.** *(Pure literature work, not covered by any code.)*
- Also resolve while here: the two papers report a **22-EM different** Qwen3-8B zero-shot number on the identical test split (62.40 in POMA vs. 40.46 in MAPR). Decide which protocol is canonical.
- Score impact: this is a **redundant-publication risk**, not just a novelty ding — an uncited overlapping paper from the same authors, same benchmark, same backbone, same CoAgt/CoQ comparisons can trigger a desk-level integrity question independent of technical merit. **Treat as blocking, not optional.**
- Priority: **1, in parallel with the engineering** — needs a human decision, not compute.

**7. State explicitly, in prose, which of ZS/CoT/FS/POMA get AN and which scoring policy each uses.**
- Status: the runbook's own policy comment is essentially the paragraph the paper needs, translated to prose.
- Priority: **2** (rolled into #1/#4's writing pass).

### Tier 3 — not built, correctly deprioritized

**8. Cross-dataset transfer test.** `docs/Q2_EXPERIMENT_RUNBOOK.md` states outright there is no CLI for this yet and it is explicitly not required for this revision. Matches the "redesign, next-paper" classification — don't promise it now.

**9. Evidence-support verifier for answerability.** Same story — not built, not required. The honest move (per the plan) is to discuss the regression, not build a verifier under deadline pressure.

Priority: **3 (skip for this revision; leave as future work, which the paper already does).**

---

## Execution order (mirrors the runbook's own §10)

1. Run `pytest` + `-Phase DryRun` (sanity, ~5 min, no network calls).
2. Run `-Phase Preflight` on both backbones (5 questions — catches integration bugs before spending real budget).
3. Full Qwen matrix: 4 baselines + POMA, each through raw/AN-common/GSA.
4. Full Gemma matrix, same shape (needs the documented throttling: `POMA_PARALLEL_WORKERS=1`, `POMA_LLM_RETRY_DELAY=30`, `--max_workers 1`).
5. The three paired revision analyses (AN-native-vs-GSA, AN-common-vs-AN-common, GSA-vs-GSA) + CSV export.
6. **Only after seeing those numbers**, write §1 RQs, rewrite abstract/contributions, reconcile Table 6, uncomment the appendix, and resolve the MAPR overlap.
7. Leave cross-dataset transfer and the verifier as future work.

---

## Bottom-line score prediction

If steps 1–6 land with POMA still ahead under GSA and AN-common on at least one backbone with a CI excluding zero, and the MAPR overlap is resolved by citation and differentiation rather than left silent: **6–7/10** on resubmission.

If the gain is Qwen-only or reverses under fair scoring: **5–6/10** with a reframed contribution — still a defensible, honest paper, just not the one currently drafted.

---

*See `review-POMA-JIT.md` for the full finding-by-finding review this plan is fixing, and `journal-selection-POMA.md` for whether the current target venue is even the right one to spend this effort on.*
