# Journal Selection: is "JIT" the right venue for POMA?

**Date:** 2026-09-17

---

## Short answer

Probably not — and this may explain the vague, generic tone of the four editor comments better than a pure quality problem does.

---

## Why I think JIT is the wrong venue

The manuscript text itself doesn't print the target journal name anywhere I could extract (Taylor & Francis "interact" drafts typically don't), but two things point at a specific journal:

- The file is literally named `JIT_Khoi.pdf`.
- `paper/jit-article.tex` in the repo uses Taylor & Francis's `interact.cls`, and T&F's ***Journal of Information Technology*** runs on the route code `rjit20` on tandfonline.com — matching "JIT" exactly.

If that's the target, its own aims-and-scope says:

> "focused on new research addressing information, management, and communications technologies **as applied to the digital worlds of business, government and non-governmental enterprises**... designed to be read by researchers... in the fields of **Information Systems, Management and Information Science**... as well as senior business and IT executives."

That is a management/IS-strategy journal — digital transformation, IT governance, organizational adoption, theory-building case studies. It is historically a top-tier IS venue (ABS 4*/FT50-class), not a computational-NLP or AI-systems methods venue.

**This matters for how to read the rejection.** A paper about multi-agent LLM orchestration on a QA benchmark has essentially no topical fit here, regardless of execution quality. The four comments —

> "clearer articulation ... of the research purpose and problem statement"
> "the proposed solution ... does not appear sufficiently convincing"
> "lacks robust and persuasive experimental validation"
> "the current contributions seem limited"

— read like a reviewer evaluating *managerial/theoretical* contribution and finding none, rather than a reviewer engaging with the specific technical weaknesses catalogued in `review-POMA-JIT.md` (the AN/best-of-K scoring, single backbone, etc.). Those comments are exactly what an IS-strategy reviewer writes about a systems paper that doesn't attempt an organizational or managerial framing — not necessarily what an NLP/AI reviewer writes about a paper with a real evidence problem.

**Practical implication:** if JIT is confirmed as the actual venue, I would not spend the Tier-1 engineering effort in `fix-plan-POMA.md` trying to satisfy *this* journal's reviewer — a technically perfect version of this paper still isn't the kind of paper JIT publishes. The fixes are still worth doing (they're needed for any credible venue), but the target should change first.

---

## A contradiction worth resolving first

The repository's own `README.md` citation block says something different from either "JIT" or the assumption above:

> "The manuscript has been submitted to *Knowledge and Information Systems* and is currently under review."

*Knowledge and Information Systems* (KAIS, Springer) is a Q2 AI/data-systems journal — a much more sensible fit than a T&F IS-strategy journal. Either:
- the README is stale and JIT is current, or
- you've already pivoted to KAIS and the `.docx` revision plan / file naming just hasn't caught up.

**Resolve this before anything else** — it determines which reviewer comments (the four shown here, or a different KAIS decision) are the ones actually being addressed, and whether the interact.cls / T&F formatting is even still needed.

---

## If not JIT: ranked alternatives

Ranked by topical fit for a Vietnamese-language, benchmark-driven, multi-agent LLM systems paper — not just by quartile.

### 1. ACM Transactions on Asian and Low-Resource Language Information Processing (TALLIP) — top pick
- Q2 (SJR, 2024), ACM-published, SJR ≈ 0.503, h-index 31.
- Scope is explicitly computation over Asian and low-resource languages — Vietnamese Table QA is squarely in scope, and "low-resource" is a genuine selling point here rather than an afterthought needing justification.

### 2. Knowledge and Information Systems (KAIS, Springer)
- Q2, general data/AI-systems audience used to benchmark-and-ablation-style empirical papers.
- Also what the repo's own README already claims as the current target — worth confirming and possibly just proceeding with this one.

### 3. Knowledge-Based Systems (Elsevier)
- Q1 — higher bar and more competitive than the others on this list, but this is the exact journal that published the Open-ViTabQA benchmark paper (Dao et al., 2025) that POMA builds on. A methodologically strengthened follow-up has a natural editorial thread there.

### 4. Language Resources and Evaluation (Springer)
- Q2. Good fit **if** the paper leans into the evaluation/diagnostic contribution (the AN-vs-orchestration attribution finding, hint-accuracy analysis, answerability breakdown) rather than the orchestration-method framing — i.e., pairs naturally with the "RQ2" reframing discussed in `review-POMA-JIT.md` Part E.

### 5. Expert Systems with Applications (Elsevier)
- Q1, high-volume, broad applied-AI audience. A common "safe" option for groups like this one; mentioned as a fallback rather than a first choice, since its scope is broader than the specific low-resource/NLP contribution here.

---

## What doesn't change regardless of venue

The technical fixes in `fix-plan-POMA.md` (fair AN-on-baseline comparison, single-answer scoring, second backbone, bootstrap CI, hint accuracy, the MAPR/ViPanelTR citation) are necessary for **any** credible venue on this list. A better-fit journal gets you a reviewer who engages with those numbers instead of bouncing the paper on scope — it doesn't waive the numbers themselves.

---

*See `review-POMA-JIT.md` for the full technical review and `fix-plan-POMA.md` for the code-grounded, priority-ranked execution plan.*
