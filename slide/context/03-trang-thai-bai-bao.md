# 03 — Paper status: published figures versus audited results

## Results currently shown in the README and draft

Open-ViTabQA test, Qwen3-8B, percentages. Sources: `README.md` and the
`JIT_Khoi.pdf` draft.

| System | EM | F1 | R1 | MET |
|---|---:|---:|---:|---:|
| Qwen3 8B zero-shot | 62,40 | 76,16 | 69,06 | 67,52 |
| Qwen3 8B task decomposition | 59,38 | 74,01 | 65,99 | 64,15 |
| Qwen3 8B chain-of-thought | 59,17 | 74,03 | 66,55 | 64,45 |
| Qwen3 8B few-shot | 67,14 | 78,64 | 74,18 | 72,30 |
| **POMA (Qwen3 8B)** | **80,24** | **88,23** | **86,07** | **84,50** |

## Audited result sequence — the most important slide

```
80,24  POMA best-of-K (ORACLE, older run, n=992)
  ↓ −12,50  [95% CI 10,48–14,62]  ← scoring policy alone
67,74  POMA first answer (same run)
       versus Few-shot 67,34 → +0,40 [−2,12; +3,02]  ← not significant

(new Qwen run, n=992, same scorer, one-answer policy)
74,90  POMA `all` (ORACLE best-of-K, mean K 3,44, maximum K 80)
66,63  POMA-first
67,34  Few-shot raw
68,45  POMA + GSA
70,16  Few-shot + GSA  ← single-call baseline OUTPERFORMS POMA
       POMA+GSA − FS+GSA = −1,71 points [−3,93; +0,50]; 53 wins / 70 losses / 869 ties
```

Sources: `docs/research/Khoi/review-POMA-Boost-v2-architecture.md` §1;
`outputs/q2_revision/qwen_baseline_comparison_candidate_max.md`.

**Short explanation:** most of the 80,24 − 67,14 gap comes from (a) asymmetric
best-of-K scoring and (b) answer normalization, both of which can also be
applied to the baseline, rather than from multi-agent orchestration.

## Technical review of the draft: F1–F10 (overall score 4/10, reject)

Source: `docs/research/Khoi/review-POMA-JIT.md`.

| # | Finding | Severity |
|---|---|---|
| **F1** | Ablation attributes the gain to **Answer Normalization**, not orchestration: FS 67,14 → POMA without AN 68,41 → POMA 80,24, so **90% of the EM gain comes from AN**, which can also be applied to the baseline | Fatal to current framing |
| **F2** | "No correct answer was made incorrect" follows from best-of-K scoring, not the design | Definition |
| **F3** | A candidate set can contain both `Null` and a real answer, hedging both answerability outcomes | Weakens contribution |
| **F4** | "Parallel" cannot affect accuracy (no cross-talk, T=0); latency is the only possible benefit and has not been measured | Weakens contribution |
| **F5** | Consolidation is undefined; the `confidence` field is unused | Rewrite |
| **F6** | The description of AN ("does not generate new reasoning") conflicts with the implementation (LLM calls for free text) | Rewrite |
| **F7** | The paper's own baselines undermine its premise: TD 59,38 and CoT 59,17 both score **below** ZS 62,40 | Contradiction |
| **F8** | The paper promises better answerability, but POMA **loses** to FS in both classes (96,49 vs 97,38 and 51,13 vs 56,64); it adds 18 false abstentions while preventing only 2 hallucinations | Fatal to motivation |
| **F9** | "Predicted hints outperform gold hints" is confounded by candidate-set size (+0,20 EM = 2 questions, but +70% tokens) | Weakens claim |
| **F10** | "Insufficient budget for another backbone" contradicts Table 7 (one POMA run costs **$2,06**) | Remove claim |

### Two unresolved arithmetic inconsistencies

1. **Table 6 versus §5.6.** §5.6 says AN flips 177/992 questions (17,84%) from
   wrong to correct with none flipped back. Without AN, EM should therefore be
   80,24 − 17,84 = **62,40**, not 68,41. Also, **68,41% is not k/992**
   (678/992 = 68,35%; 679/992 = 68,45%). If 62,40 is correct, POMA without AN
   scores **4,7 points below few-shot**.
2. **Evaluator drift.** Re-evaluating old artifacts with the current evaluator
   changes FS 67,14 → 67,34; ZS 62,40 → 63,10; and the Fig. 2 Null-F1
   values 51,13/56,64 → 52,24/59,20.

## Trace diagnostics (logs available for 592–992 questions) [MEASURED]

| Question | Result | Implication |
|---|---|---|
| Specialists per question | 880 questions use one specialist (88,7%), 112 use two, 0 use three; mean 1,113 | Disagreement adjudication (poma2) almost never activates |
| Disagreement after canonicalization | 8/64 questions with two specialists, about 1,4% of all questions | — |
| Perfect resolver ceiling | +0,30 points observed, upper bound +0,71 | The whole disagreement branch is worth at most 0,7 EM |
| Errors invisible to the gate | 92,9% (171 wrong single-specialist answers + 11 jointly wrong answers) | — |
| Confidence | 77,9% exactly 1,0; AUROC 0,588 (non-Null) | No signal for weighting |
| Evidence grounding | 88,5% of wrong answers still cite a real cell; AUROC 0,52 | A "does this cell exist?" verifier is ineffective |
| Error correlation: POMA vs FS | Both wrong on 240/992, **2,30 times** the independent expectation; κ = 0,62 | Same-backbone errors are strongly correlated, limiting ensemble value |
| Unconditional vote across five branches | 67,64 < POMA-first 67,74 | Simple voting does not help |

**Decision: do not build poma2.** Source:
`docs/research/Khoi/review-POMA-Boost-v2-architecture.md` §0–§3.

## Journal issue — supervisor decision needed

- The draft filename is `JIT_Khoi.pdf`, and `paper/jit-article.tex` uses
  Taylor & Francis's `interact.cls`. This suggests **Journal of Information
  Technology**, an **information systems/management** journal rather than an
  NLP/AI venue. If so, the editor's four general comments may concern the
  **management contribution** rather than the technical work.
- The repository `README.md`, however, says the paper is under review at
  **Knowledge and Information Systems (KAIS, Springer, Q2 AI/data systems)**,
  which fits better.
- **Confirm the actual submission status** before investing in revisions,
  and avoid duplicate submissions.
- **ViPanelTR (MAPR 2026)**, by the same group, uses the same benchmark and
  backbone and compares with CoAgt/CoQ, but **the POMA draft does not cite it**.
  Disclose and distinguish the two works.

Sources: `docs/research/Khoi/journal-selection-POMA.md`,
`review-POMA-JIT.md` Part D.

## Existing repository support for most requested revisions

`docs/research/Khoi/fix-plan-POMA.md` maps review requests to code already
written and tested: applying AN to baselines
(`CommonAnswerNormalizationFinalizer`), one-answer scoring
(`CandidatePolicy`), bootstrap CIs, hint-predictor metrics, parallelism
statistics, the second backbone wired in `scripts/run_q2_experiments.ps1`,
and a preregistered interpretation gate. The remaining work is mainly
**running experiments and writing**, rather than coding.
