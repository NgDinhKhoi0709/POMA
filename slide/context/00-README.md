# Source material for the POMA supervisor progress presentation (Vietnamese Table QA)

Updated: 2026-09-20. These documents are **source material for slides**, not the
slides themselves. Every figure below comes from artifacts and documents in the
repository and includes a source path. Do not add new figures or estimates unless
explicitly marked.

## Reading order

| File | Contents | Slides |
|---|---|---|
| [01-boi-canh-va-du-lieu.md](01-boi-canh-va-du-lieu.md) | Task, measured Open-ViTabQA properties, figures that conflict with the draft | Problem, Data |
| [02-he-thong-hien-tai.md](02-he-thong-hien-tai.md) | Running POMA architecture, v3lite, evaluation infrastructure | Method, System |
| [03-trang-thai-bai-bao.md](03-trang-thai-bai-bao.md) | Published versus audited results, review F1–F10/W1–W7, journal issue | Current status, Why revise |
| [04-nhat-ky-thuc-nghiem.md](04-nhat-ky-thuc-nghiem.md) | All completed experiments (D01–D13, parser, drift, second backbone) | Approaches tested |
| [05-bang-so-lieu-tong-hop.md](05-bang-so-lieu-tong-hop.md) | Results matrix with comparison metadata | Results tables |
| [06-kien-thuc-nghien-cuu.md](06-kien-thuc-nghien-cuu.md) | Literature on multi-agent models under 10B, table representation, program-aided reasoning, and abstention | Related work, Motivation |
| [07-bai-hoc-phuong-phap-luan.md](07-bai-hoc-phuong-phap-luan.md) | Measurement lessons: run variation, illusory headroom, prompt effects | Discussion, Lessons |
| [08-huong-di-tiep-theo.md](08-huong-di-tiep-theo.md) | N1/N2/N3, work to avoid, three possible paper directions | Plan |
| [09-goi-y-cau-truc-slide.md](09-goi-y-cau-truc-slide.md) | Slide-by-slide outline for 15- and 25-slide versions | Build the deck |

## Five points to state accurately from the start

1. **The paper's 80,24 EM is best-of-K (oracle), not the accuracy of a system
   that emits one answer.** On the same run, the first answer scores only
   **67,74**. The 12,50-point gap comes from scoring, not reasoning.
   Source: `docs/research/Khoi/review-POMA-Boost-v2-architecture.md` §1.
2. **Under a fair comparison (one answer per system, same GSA finalizer), POMA
   does not outperform few-shot.** POMA+GSA scores 68,45 versus Few-shot+GSA
   70,16; difference −1,71 points, paired 95% CI [−3,93; +0,50].
   Source: `outputs/q2_revision/qwen_baseline_comparison_candidate_max.md`.
3. **The proposal lists 19 directions (D01–D19); eight were implemented and
   run** (D01, D02, D04, D09, D10, D11, D12, D13). None significantly improves
   EM. D13 is the only direction with a CI excluding zero, and its effect is
   **harmful** (−14,5 points).
4. **The most important methodological finding is variation of 0,44 and 1,7
   EM points across identical runs** (10,9% of answers change wording with no
   configuration change). Every measured effect (+1,9; +0,40; +2,0; −1,41)
   falls within or near that range.
5. **On the second backbone, POMA clearly loses to a single-call baseline.**
   Gemma-3-4B-IT (n=543): POMA-first 26,70 versus zero-shot 39,59 EM,
   difference −12,89 [−17,13; −8,66].

## How to state the conclusion

Accurate: *"No fair comparison (same run, one answer, same finalizer) has shown
POMA outperforming few-shot; all confidence intervals include zero; several
claims in the draft could not be reproduced."*

Avoid: *"POMA does not work."* The data do not support that stronger conclusion.

## Rule for comparing figures (important for slide tables)

Two figures may be compared directly only when **all six attributes match**:
dataset and n, parser version (legacy/fixed), scorer and candidate policy,
model and provider, prompt, and **run**. If any attribute differs or is
unknown, label the figures "not directly comparable." See [05](05-bang-so-lieu-tong-hop.md)
and [07](07-bai-hoc-phuong-phap-luan.md) for the rationale.

**Do not mix results from the RankA repository into POMA tables.** The +2,46 /
+3,04 / +4,63 figures mentioned in research notes come from another repository,
on the **dev** split, with scorer N1 (which treats `Có/Đúng/Phải` as equivalent).
They motivate transfer hypotheses; they are not POMA results.

## Evidence labels (retain on slides)

| Label | Meaning |
|---|---|
| **[MEASURED]** | Calculated directly from repository data, predictions, or logs |
| **[INFERENCE]** | Proposal, transfer hypothesis, or estimate without an isolated experiment |
| **[LITERATURE]** | Result from an external paper read in full |
| **[EXPLORATORY]** | Analysis or decision made **after** inspecting test data |
