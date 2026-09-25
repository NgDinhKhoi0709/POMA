# 09 — Suggested slide structure

Two versions: **15 slides** for a 15–20 minute progress report and
**25 slides** if the supervisor wants to examine each tested approach.

> **Note — the built deck differs from this plan.** `progress-report.typ` has 16
> numbered slides plus a closing slide. Three deliberate changes: the "Guidance"
> slide listing six decisions was **removed** (those points are now raised verbally
> — see `script-thuyet-trinh.md`); a dedicated **POMA v3lite** slide with the v3lite
> pipeline diagram was **added** after "Three Examples"; and the Data slide dropped
> its "four draft discrepancies" table and its train/dev/test leakage callout,
> keeping one measured-data table with a "why it matters" column (the
> discrepancies and the leakage point are raised verbally instead).
> This file remains the original plan; the deck and the speaker script are the
> current state.

---

## 15-slide version — progress report

| # | Title (short, 1–3 words for the header) | Content | Source |
|---|---|---|---|
| 1 | Title | POMA: Vietnamese Table QA, progress and tested approaches | — |
| 2 | Outline | Four sections: Status · System · Experiments · Plan | — |
| 3 | Task | Open-ViTabQA, <10B without fine-tuning, three challenges (merged headers, multistep questions, `Null`) | [01](01-boi-canh-va-du-lieu.md) |
| 4 | Data | Measured data plus **four draft discrepancies** (4,5%, not 10%; 91% one label; four categories, not three; dev/test tables appear in train) | [01](01-boi-canh-va-du-lieu.md) |
| 5 | System | `imgs/pipeline.png` diagram and seven-stage table | [02](02-he-thong-hien-tai.md) |
| 6 | **80,24 Sequence** | Key slide: 80,24 (oracle) → 67,74 (first) → 66,63/68,45 → FS+GSA **70,16** | [03](03-trang-thai-bai-bao.md) |
| 7 | Attribution | 90% of EM gain comes from Answer Normalization; asymmetric best-of-K scoring; parallel execution cannot change accuracy | [03](03-trang-thai-bai-bao.md) |
| 8 | Experiments | Overview of completed experiments, effects, and CIs | [04](04-nhat-ky-thuc-nghiem.md) |
| 9 | Three Examples | D10 (real token savings) · D11 (v3lite, +0,40) · D13 (−14,5, rejected) | [04](04-nhat-ky-thuc-nghiem.md) |
| 10 | **Run Variation** | 0,44 and 1,7 points across identical runs; 10,9% of answers change wording; most measured effects fall in this range | [07](07-bai-hoc-phuong-phap-luan.md) |
| 11 | Headroom | Ceiling versus captured gain (3,2 → 0; 4,7 → 0,1) and common cause | [05](05-bang-so-lieu-tong-hop.md) §F |
| 12 | Backbone 2 | Gemma-3-4B-IT: POMA 26,70 vs ZS 39,59, CI **excludes zero**, plus SEA-LION | [04](04-nhat-ky-thuc-nghiem.md) |
| 13 | Literature | Prior literature challenges homogeneous multi-agent systems at 8B; our result is **consistent with prior evidence**, not anomalous | [06](06-kien-thuc-nghien-cuu.md) §1 |
| 14 | Plan | N1 → N2 → N3/N4/N5; work to avoid | [08](08-huong-di-tiep-theo.md) |
| 15 | Guidance | Six supervisor decisions: venue, paper framing A/B/C, negative results, budget, ViPanelTR, fine-tuning scope | [08](08-huong-di-tiep-theo.md) |

---

## 25-slide version — ten additional slides

Insert after slide 9 of the 15-slide version:

| Added | Title | Content |
|---|---|---|
| +1 | Table Structure | Only 38/329 tables have header paths differing from flat strings; most "merged headers" are banners or left-column stubs |
| +2 | D01/D02 Detail | Five-row one-answer table, BIF, and GSA costs |
| +3 | D04 | Activation funnel (110 ok → 11 overrides); readers already got all 11 right |
| +4 | D09 | Eight-variant table; prompt effect dominates representation (−11,5 versus at most +4) |
| +5 | D10 | Three-variant table and token/cost figures; −46,6% shrinks to −6,4% within POMA |
| +6 | D11 | Five nested variants; answerability gate correct in 5/16 replacements |
| +7 | D12 | Five variants with the fixed parser; `nohdr_h1` cuts tokens by 28,4% |
| +8 | Parser Bug | Concatenated-cell example; 95/329 tables, 325/992 questions; A/B −1,41; testing lesson |
| +9 | Hybrid Retrieval | Recall@k table, predefined rejection rule, proposal to lower k |
| +10 | Abstention | `Null` confusion matrix; the initial diagnosis was reversed (precision is the bottleneck) |

---

## Three slides to retain even in a shorter deck

1. **80,24 → 70,16 sequence** (slide 6). If the supervisor remembers only
   one slide, it should be this one.
2. **0,44–1,7-point run variation** (slide 10). This addresses why no
   improvement has yet been established.
3. **Experiment overview** (slide 8). It shows the scope of completed work.

---

## Presentation conventions (from `slide/README.md`)

- **Three blocks with consistent meanings:** blue `highlight-block` for
  background/setup; green `result-block` for positive findings; red
  `warning-block` for limitations/cautions. Most findings here are
  **warnings or neutral**. Do not color an effect green if its CI includes zero.
- Keep `=` / `==` headings short (1–3 words). The fixed two-row header
  can wrap over slide content.
- **Typst does not warn about slide overflow.** Compile, count pages, and
  render any edited page to inspect it.
- Every slide results table **needs a metadata line** (n, parser, model,
  run); see [05](05-bang-so-lieu-tong-hop.md).

---

## Likely supervisor questions and where to answer them

| Question | Where to find the answer |
|---|---|
| "Is 80,24 still valid?" | [03](03-trang-thai-bai-bao.md), slide 6: it is an oracle best-of-K figure |
| "Have you tested a second backbone?" | [04](04-nhat-ky-thuc-nghiem.md): yes, Gemma-3-4B-IT (543 questions) and SEA-LION; POMA clearly loses on Gemma |
| "Why has nothing improved?" | [07](07-bai-hoc-phuong-phap-luan.md): 0,44–1,7-point run variation exceeds most effects; apparent headroom has not converted to gains |
| "Are you sure multi-agent does not help?" | [06](06-kien-thuc-nghien-cuu.md) §1: literature on homogeneous 7–8B systems includes a martingale argument |
| "What remains to try?" | [08](08-huong-di-tiep-theo.md): N1–N5 and fine-tuning (outside current scope) |
| "How much was spent on API calls?" | [05](05-bang-so-lieu-tong-hop.md) §E: one full POMA run costs $1,72; individual experiments $0,08–0,73 |
| "Why was the paper rejected?" | [03](03-trang-thai-bai-bao.md): F1–F10, W1–W7, score 4/10, and a possible venue mismatch |
