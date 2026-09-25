# 08 — Next steps and decisions to discuss

## Ordering principle

The first two tasks concern **measurement**, not interventions. They must
come first so later intervention results can be interpreted.

---

## N1 — Measure variation across runs (highest priority)

Run **one control configuration three times** with identical model,
provider, cached hints, and prompt, then report the EM range.

```bash
python scripts/run_v3lite.py --arms control --qas dataset/qas_test.json \
  --out outputs/v3lite/drift_1.jsonl --plan outputs/v3lite/plan.json \
  --hint-predictions outputs/q2_revision/openrouter_qwen_qwen3-8b/full/raw/poma.json --workers 16
```

- **Cost:** about **$5 and 3 hours**. **No new code required.**
- **Why this comes first:** if the actual noise floor is 1,7 points,
  D10's +1,9, D12's +2,0, and D11's +0,40 all fall within noise.
  **Future test interventions with a ceiling below about 2 points
  would not justify a run.**
- **Use the result to** set a minimum effect worth trusting and decide
  whether each branch needs repeated runs.
- Two of the three needed data points already exist (0,44 and 1,7);
  at least one more run is required.

---

## N2 — Rerun few-shot + GSA alongside a new control

The current comparison places **68,75 (D11)** next to **70,16 (D01 audit)**,
even though these come from **different runs** and run variation is known.
This is the thesis's central comparison (whether POMA beats few-shot),
and it is not robust in its current form.

- Run few-shot + GSA and the POMA control **in the same run**, with the
  same model, provider, and fixed parser, then score the paired results.
- This should cost less than N1 because few-shot uses only one call
  per question.

---

## N3 — Tighten the answerability gate's replacement rule (depends on N1)

The current gate replaces `Null` correctly in 5/16 cases. Proposed
restriction: **replace only if re-answering cites a cell that exactly
matches an entity in the question**; otherwise keep `Null`.

- **Ceiling:** 4,7 points. **Predicted actual gain:** about +1 point
  or less.
- **Caution:** this predicted gain is **at or below the observed
  1,7-point run gap**. N3 is worthwhile **only if N1 finds a
  substantially smaller noise floor**.
- **Validate on dev**, not test.

---

## N4 — Complete the second-backbone matrix (in progress)

| Task | Status |
|---|---|
| Gemma-3-4B-IT, POMA + zero-shot | **543/992 questions**; incomplete run |
| Gemma-3-4B-IT, few-shot / CoT / TD | Not run |
| SEA-LION: paired POMA versus baseline on the **same** 486-question subset | **Missing**; current POMA and baseline figures use different sets |
| `scripts/run_q2_experiments.ps1 -Phase Full` for both backbones | Written and tested (66 commands). **Qwen branch is complete** (raw + GSA finalization + reports); **Gemma has only raw POMA and zero_shot, with no `finalized/`**. See [04](04-nhat-ky-thuc-nghiem.md) |

The current Gemma result (POMA loses to ZS by 12,89 points, CI excludes zero)
is one of the project's few statistically significant results. Completing
the matrix would strengthen the report.

---

## N5 — Lower H1's k (cheap, motivated, not yet run)

The BM25 rank of the answer-containing row has **median 0, p90 = 2,
p99 = 17**, while H1 keeps **k = 20**. Lowering k to 5 (96,2% recall)
or 8 (97,5%) would remove about three quarters of retained rows,
**without adding another model**. It needs one confirmation run to
check that EM does not fall.

---

## N6 — Proposed next system: GaP-TQA (separate follow-up paper)

Source: `docs/research/GRAPH/2026-09-22-graph-as-policy-tqa-proposal.md`;
census script `scripts/census_graph_reach.py` (no API calls).

- **Idea (adapted from GaP, arXiv:2607.05369):** one **frozen typed graph
  per question class**, mixing deterministic nodes (span-aware cell grid,
  structure manifest, Yes/No verbalizer, granularity policy, vote, `Null`
  gate) with Qwen3-8B leaf nodes (locate cell IDs, extract span, judge
  Bool). Graphs are authored and refined **offline** on train (rehearse →
  attribute errors to nodes against gold → one targeted edit → accept or
  reject on dev), then frozen. Test time: 1–3 8B calls per question, no
  agents at runtime.
- **Why not the first draft (per-question typed DAG written by the 8B
  model):** it would repeat D04. Only **3,0%** of test golds are derived
  numbers; only **9,0%** of test questions have ≥ 2 hint labels, so there
  is nothing to split across runtime skill agents.
- **Gold answer types (test, n=992):** single cell 44,0%, Yes/No 19,3%,
  span inside a cell 10,4%, free text 7,1%, number in table 5,1%,
  multiple cells 5,0%, `Null` 4,5%, derived number 3,0%.
- **Free experiment — Yes/No verbalizer node** (lexicon from train: `...đúng
  không?` → `Đúng`, `...phải không?` → `Phải`, else `Có`; negatives →
  `Không`): FS+GSA **70,16 → 73,29 EM (+3,13, paired 95% CI [+1,92;
  +4,33]; 34 wins / 3 losses)**; POMA+GSA 68,45 → 71,77. Measured post hoc
  on test, n=992, legacy parser. The rule reproduces the gold string for
  90,1% of train, 87,6% of dev, and 91,6% of test Yes/No golds, so it is
  not fitted to test. The node relabels stored predictions deterministically, so
  run-to-run drift does not apply. Reproduce with `python scripts/census_graph_reach.py`
  (keys `verbalize_*` in `outputs/graph_census/census.json`). It helps every system, so **the new control is
  FS+GSA+Verbalize = 73,29**.
- **Gates:** G0 confirm on dev (≈ $1); G1 8B cell-ID localization ≥ 70% on
  200 dev questions, with `response_format` JSON schema, or stop; G2
  hand-built graphs for the three largest classes; G3 offline self-learning;
  G4 one-agent versus multi-agent harness; G5 one test run. Total ≈ $12–18.

## Work to avoid next

| Proposal | Reason |
|---|---|
| Add another pipeline stage | D04, D09, D10, and D11 added components without statistically significant gains |
| Try another table representation | D09 tested eight and D12 another four variants; none established a win |
| Build consensus/adjudication | The grounding component (program agent) had low expected value in D04; on 44,2% of disagreements, **both branches are wrong** |
| Build poma2 (specialist-disagreement adjudication) | 88,7% of questions use one specialist, so the gate rarely activates; ceiling +0,71 points |
| Use a same-backbone role council | Failed in literature and related experiments (Δ0,00) |
| Weight by confidence or check cell existence | Confidence AUROC 0,588; evidence AUROC 0,52 — inadequate signals |
| Repeat `empty → Null` | Only 3/117 empty cases have gold `Null`; the rule lost 8,88 points |

---

## Three possible paper framings — supervisor choice needed

### Option A — Conservative revision for resubmission (estimated 5–8 working days)

1. Reconcile figures in Table 6, Fig. 2, evaluator drift, and the
   `Null` count (45 versus 46).
2. On **dev**, run one-answer FS and POMA with the **same formatter and
   AN policy**. Report POMA-first, GSA, and FS+GSA with paired CIs and
   token/call costs.
3. Add a second backbone under the same protocol. Complete hint-predictor
   metrics, errors by question type, the answerability matrix, and
   comparison with ViPanelTR.
4. **Rewrite claims around measured attribution.** Keep `all` only as
   an oracle diagnostic.
5. **Drop** the claim that parallel specialists improve QA unless a
   one-answer, same-finalizer comparison has a CI excluding zero.

### Option B — Balanced methods paper (estimated 2–3 weeks)

Complete A, then add demonstration retrieval and a narrow executor on
**untouched dev data**, with retrieval excluding seen tables. Run an
independent `Null` pilot with a hard-veto control. Freeze the best dev
configuration and evaluate on test **once**. Frame the contribution as a
"training-free, operation-aware Vietnamese Table QA pipeline," without
attributing gains to "multi-agent cooperation."

### Option C — Diagnostic or negative-results paper (best fit to current data)

Reframe the work as a **diagnostic study**:

1. Homogeneous multi-agent orchestration at 8B does not improve Vietnamese
   Table QA, supported by 13 interventions whose CIs all include zero
   and error correlation κ = 0,62.
2. **Much of the apparent gain in this literature comes from answer
   extraction/normalization and asymmetric scoring.** Independently
   reproduce Choi et al.'s finding in another language and task.
3. **Run variation (0,44–1,7 points) exceeds reported effects in this
   range**, a methodological warning for the field.
4. Tooling contribution: a strict scorer with provenance, paired bootstrap,
   preregistered interpretation gate, and reproducible BIF metric.

Suitable venues: language-resource or evaluation conferences/journals
(LRE, TALLIP), or a negative-results track.

---

## Decisions to request from the supervisor

| # | Question | Options or action |
|---|---|---|
| 1 | **Where should it be submitted?** README says KAIS; the filename says JIT, an information systems/management journal that may be a poor topical fit | Confirm actual submission status before revising |
| 2 | **How should the paper be framed?** | A (conservative revision) / B (methods paper) / **C (diagnostic study, closest to the data)** |
| 3 | **Are negative results acceptable?** | If so, C is the strongest and least reviewer-sensitive direction |
| 4 | **What should the API budget prioritize?** | N1 ($5) + N2 to strengthen the main comparison, or new interventions? |
| 5 | **ViPanelTR:** same group and benchmark, not cited in POMA draft | Disclose and distinguish it; avoid duplicate submission |
| 6 | **Can the scope include fine-tuning?** | The project currently requires training-free methods; those avenues are nearly exhausted |
