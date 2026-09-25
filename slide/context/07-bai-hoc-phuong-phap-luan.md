# 07 — Methodological lessons

These are the **main contributions of the recent work**. The seven lessons
below come from measurements in this repository, rather than literature.

---

## Lesson 1 — Variation across identical runs exceeds measured effects

The **same configuration** (model, provider, prompt, cached hints, parser)
was run twice:

- Run 1: 68,33 EM · Run 2: 67,89 EM → **0,44-point** difference.
- **98/900 answers (10,9%) changed wording with no configuration change.**
- A second observation: new control 68,35 versus old artifact 66,63 →
  **1,7-point** difference.

Compare these with measured intervention effects:

| Intervention | Effect | Within observed variation? |
|---|---:|---|
| D10 H1 k=20 | +1,9 | ✅ |
| D12 `pipe_nohdr` | +2,0 | ✅ (near the boundary) |
| Parser fix | −1,41 | ✅ |
| D11 v3lite | +0,40 | ✅ |
| D04 R2 | −1,0 | ✅ |
| D13 `hdrfilter` | −14,5 | ❌ (far beyond it) |

**Implication:** until this variation is characterized, **effects around
±2 points cannot be interpreted confidently**. This helps explain why no
improvement has been established. It is a finding, not an excuse.

**Caveat:** these are **two individual observations**, not a measured
standard deviation. At least three runs are needed to estimate a range.
That is task N1 in [08](08-huong-di-tiep-theo.md).

---

## Lesson 2 — Headroom is large; captured gain is nearly zero

| Mechanism | Ceiling | Captured |
|---|---|---|
| Arithmetic executor | 1,8–3,2 points | 0 |
| Answerability gate | 4,7 points | +0,1 |
| Disagreement resolver | 0,71 points | +0,30 |
| Perfect retrieval | <0,1 points | — |

**Common cause: the intervention cannot distinguish cases that need a
correction from cases that do not.**

- The executor activates on questions the reader **already answered
  correctly** (11/11), and misses **every measured reader error** (0/15).
- The answerability gate cannot distinguish false from correct `Null`
  predictions: of 16 replacements, 5 correct an error, 4 break a correct
  `Null`, and 7 remain wrong.
- An adjudicator has no useful signal on 44,2% of disagreements where
  **both branches are wrong**.

**Rule:** before implementing an intervention, measure the activation
gate's **conditional accuracy**, not only theoretical headroom.
Headroom counts incorrect answers; the key question is whether the gate
reaches those answers.

---

## Lesson 3 — Prompt effects dominate table representation

On the same 200-question subset, model, and **Flatten V1 string**,
`v1_zs` scores 64,0 EM and `v3_zs_minimal` scores 52,5 EM:
a **−11,5-point** difference.

The entire effect range of eight table representations is only
**−1,5 to +4,0**.

Mechanism: `v3_zs_minimal` generates longer answers (mean **7,0 words**
versus **3,0** in gold answers; `v1_zs` produces 2,9) and outputs the
exact text `null` in only 4/11 cases (`v1_zs`: 10/11). EM penalizes
the extra wording.

**Experimental-design implication:** EM poorly isolates table
representation effects while the prompt still produces verbose answers.
Only about 21% of differing answers reflect substantive representation
effects; 79% are **style variation**. **Stabilize answer style before
comparing representations**, or add metrics less sensitive to length
(F1, BIF).

---

## Lesson 4 — A preprocessing bug affects every downstream stage

Calling `cell.get_text()` without a separator concatenated cell content
in **95/329 tables and affected 325/992 test questions (32,8%)**. The bug
sits **upstream of every direction**: D01, D04, D09, D10, and D11 all
read the same corrupted table strings.

It partly explains the pattern of large headroom and near-zero gain:
**downstream modules cannot restore evidence already damaged at input.**

**A testing lesson:** the first incorrect fix (`get_text(" ")`) damaged
previously correct cells (−3,41 points). The tests **missed it** because
their only inline example (`<b>Hà</b> Nội`) already contained a space
and still passed.

> **A test for a "must remain unchanged" path is useful only if its input
> could actually change.**

---

## Lesson 5 — Oracle scoring is not deployable accuracy

`candidate_policy=all` lets the evaluator pick the candidate that best
matches the gold answer for each question. That is an **unavailable oracle
ceiling** at inference time.

- On one run, best-of-K scores **80,24**, while the first answer scores
  **67,74**: a **12,50-point scoring-policy effect**.
- Among 124 questions "won" by best-of-K, **117 already contain a correct
  answer form in one specialist's variant set**. Yes/no synonyms alone
  account for 49 questions.
- Adding candidates to a best-of-K set **cannot lower its score**.
  Therefore, "no correct answer was made incorrect" follows from the
  scoring rule, not the system design.

**Rule:** report `all` **only as an oracle diagnostic**, always alongside
a one-answer score.

---

## Lesson 6 — Choose methods on dev, not test

Several experiments in the log ran **directly on test** to meet progress
deadlines. This limits the strength of their conclusions:

- D09: 12 **uncorrected** pairwise comparisons on 200 test questions.
- D11 and D12: five and four test variants, respectively, without correction.
- D01: a fallback rule was fixed **after test errors were observed**, so
  its analysis is exploratory.
- D11: two formatter-rule bugs surfaced after scoring and were
  **deliberately not fixed and rescored**, as that would tune on test.

**Rule for the next phase:** use **train for design, dev for selection**,
then **freeze one configuration** for a single test evaluation. Test-set
analysis can justify **rejecting** a design, but cannot justify tuning a
new threshold on that same test set.

An existing enforcement tool,
`scripts/run_revision_analysis.py::interpretation_gate`, requires an EM
gain ≥ 0,02 **and** a paired 95% CI excluding zero.

---

## Lesson 7 — Conventions established for future experiments

| Convention | Implementation |
|---|---|
| **Run** | One continuous API batch with fixed settings. Figures from different runs are **not directly comparable** |
| **Control** | The comparison branch of the experiment, executed **in the same run** |
| **Pairing** | Both branches use exactly the same questions; compare question by question and use 10.000 paired bootstrap samples |
| **Splicing** | Reuse control answers only for questions whose prompt is **byte-for-byte identical**, within the same run |
| **Provenance** | SHA-256 of predictions, QAs, tables, scorer code, and each data-generation script |
| **Preregistration** | Fix activation rules and main parameters **in code before API calls** (done for D04 R2, D10 k=20, hybrid retrieval) |
| **Sentinel** | Score calls with no valid answer as `[NO_VALID_ANSWER]` and record them in the manifest rather than silently dropping them |
