# 06 — Research findings gathered so far

Five areas were reviewed (detailed notes in
`docs/research/2026-09-18-supporting/`). Each section states the finding,
primary evidence, and **implication for POMA**.

---

## 1. Multi-agent systems with models under 10B — the most relevant area

**Finding:** multi-persona systems sharing one backbone under 10B perform
poorly. This has been shown in the literature; it is not merely speculation.

| Source | Setup | Result |
|---|---|---|
| Choi, Zhu & Li (NeurIPS 2025) | Homogeneous agents sharing one backbone, Qwen2.5-7B-Instruct and Llama3.1-8B-Instruct — **POMA's setting** | Majority voting **matches or beats every debate topology**, with a martingale proof that debate cannot increase expected correctness |
| Bertalanič & Fortuna (2026) | N=10 homogeneous 7–8B agents (Qwen2.5-7B, Llama-3.1-8B, Ministral-3-8B) | Debate **loses** to isolated self-correction while using **2,1–3,4 times as many tokens** |
| Huang et al. (ICLR 2024), Table 7 | GSM8K, matched budgets | MAD @ 9 responses = **83,0** versus self-consistency @ 9 = **88,2**, a 5,2-point deficit |
| Huang et al. | Llama-2-70B intrinsic self-correction | 62,0 → 43,5 → 36,5 (smaller models fare worse; GPT-4-Turbo: 91,5 → 88,0 → 90,0) |

**Implication for POMA:** the 1,27 EM orchestration ablation result is
**consistent with prior predictions**, not an unusual failure. It lies
within the published effect range for homogeneous deliberation at 8B.

**Possible thesis contribution:** Choi et al., Appendix F, Table 9, report
single-agent GSM8K = **0,8713** using their answer extractor, but only
**0,6620** with Du et al.'s extractor on the **same model**. They note
that answer extraction can materially affect measured performance and
sometimes reverse the conclusion. **POMA's 11,83/13,10 EM attributable to
Answer Normalization independently reproduces this phenomenon for Vietnamese
Table QA.** This is the strongest publishable claim and has a precedent to cite.

**Additional engineering sources:** Cognition's "Don't build multi-agents"
(2025) recommends a linear single-threaded agent. Anthropic's "Building
effective agents" calls a fixed sequence a **workflow** and reserves
**agent** for tasks with an unpredictable number of steps; it reports that
multi-agent systems use **about 15 times as many tokens** as chat.
Open-ViTabQA follows fixed steps (serialize table → classify → answer →
check), suggesting a **workflow** framing. These three sources help answer
a reviewer asking why not to add more agents.

---

## 2. Table representation and reduction for LMs under 10B

**Current recommendation:** retain **Flatten V1**, add local row/column
selection **without LLM calls**, and set an explicit token budget. BM25 or
n-grams are cheapest. Try an LM selector only if an ablation shows missing
evidence recall for multiconstraint questions.

| Method | Useful idea | Warning from the paper |
|---|---|---|
| **TAP4LLM** | Sampler → augmenter → packer → solver; content snapshots and semantic sampling | Full setup uses **4,7–8,4 LLM calls per question**, so it is not a cheap baseline |
| **TableRAG** | Budgeted schema and (column, cell) indexing; send only top-K evidence | If all values differ, relevant evidence may still be dropped |
| **ITR / PieTa** | Precedents for row, column, and mixed-subtable selection | Require a **trained retriever**; independent row/column selection may miss dependencies across rows |

**Implemented rule:** a selector may return only `row_ids`/`column_ids`
and scores, **not rewrite table content**. Always include headers, title,
and rows with exact number/entity matches; fall back to full Flatten V1
if there is no hit.

**Where our data challenge the literature's emphasis:** at p50 ≈ 647 tokens,
overlong context is the wrong bottleneck for about 90% of this dataset.
D10 therefore focuses on the 15,6% of questions with long tables.

---

## 3. Program-aided reasoning and decomposition

| Source | Key result |
|---|---|
| **TAT-LLM** (2401.13223) | Removing the External Executor (deterministic code, zero LLM calls) costs **7B models 16,5–17,8 EM**, but **70B models only 4,8–6,7**. The value of external calculation falls with model scale. This is strong evidence for program-aided work under a 10B limit |
| **Mixture-of-Minds** (Meta, 2510.20176), no training, TableBench | LLaMA-3.1-8B: 15,42 → 14,58 (**no improvement**); Qwen3-8B: 41,98 → 47,38 (**+5,4**). Same workflow and size class, opposite outcomes: backbones are not interchangeable |
| **TableMaster** (ICLR 2026), Table 11, WikiTQ | Symbolic is **not** always more accurate: gpt-4o textual 83,98 versus symbolic 74,63; **only the weakest model** (gpt-3.5-turbo) benefits from symbolic execution |
| **Weaver**, Table 6 | gpt-4o-mini SQL error rate **42,5%** versus 15,0% for gpt-4o, attributed to smaller model size |

**Implication for POMA:** literature supports a narrow executor for small
models, but **D04 on this dataset produced 0 wins / 2 losses**. The gate
mostly reached simple counts that the reader already solved. The mechanism
may be sound in general, but it has poor coverage here.

---

## 4. Abstention (the `Null` decision)

**The initial brief diagnosed the problem in the wrong direction.**
Reconstructing POMA's `Null` confusion matrix (946 answerable,
46 unanswerable, 53 false abstentions, 11 hallucinations):

| | Predicted `Null` | Predicted answer |
|---|---:|---:|
| **Gold `Null`** (46) | TP = 35 | FN = 11 |
| **Gold answerable** (946) | FP = 53 | TN = 893 |

→ **Null precision 39,8% · recall 76,1% · F1 52,2%**
(the paper reports 51,13).

**Diagnosis:** the system emits `Null` **too often in absolute terms**
(88 predictions versus 46 gold, **1,9 times as many**). **Precision** is
therefore the bottleneck, not recall. Recall is already 76,1%, with little
room to gain and much to lose.

**Implication:** another verifier or abstention vote would target recall
where it is already adequate. Improve **`Null` precision** instead.
D11 tested that direction (its gate runs only for `Null`) and gained
just +0,10.

**Warning from literature/RankA:** an unconstrained Skeptic reported
"insufficient information" on 130/300 questions; the rule
`empty_selection → Null` lost 8,88 points. **An empty retrieval result
must never be treated as proof of `Null`.**

---

## 5. Encoding table structure

Measurements on all 329 tables (see [01](01-boi-canh-va-du-lieu.md)):

- **`table_type` is multi-label with four categories**, not three.
  Neither ViPanelTR nor POMA specifies the convention clearly. **Resolve it
  before comparing the papers**: with three categories, both papers'
  `merged_header` and `merged_value` counts silently contain 126 "both"
  questions.
- Only **38/329 tables** have full header paths different from flat strings:
  just 116 test questions. `Parent / Child` encoding targets a minority.
- **Train+dev slice sizes** are large enough for structure ablations, without
  leakage from training a model because these methods only change prompts:
  C∪E 866 + 113 = 979 questions; banner 998; stub 1.377;
  `td_rowspan` 2.236; `td_colspan` 1.621.
  → **Run structure ablations here rather than on the 992 test questions.**
- **ViPanelTR was not found in public sources** in two searches. Its
  F1 figures of 84,25–85,71 were supplied by the authors, and its
  stratification convention is unknown.

---

## 6. Second backbone

- The shortlist draws on the Vietnamese SEA-HELM leaderboard. This is a
  **secondary source**, not a Table QA result, so it is not primary evidence.
- Selected and run: **Gemma-3-4B-IT** (API) and **SEA-LION v3 8B IT**
  (local, Kaggle/vLLM).
- Cross-backbone comparison requires the **same frozen prompt, identical
  table bytes, formatter, scorer, and thinking mode**. Report error
  complementarity **before** building an ensemble.
- Qwen3 thinking mode is **not specified in the draft** and may change EM
  substantially. A reviewer asked about it directly.

---

## 7. Semantic BIF metric and ViNLI

- BIF = `0,5 × PhoBERTScore F1 (PhoBERT-large, layer 17) + 0,5 ×
  P(entailment)`, reference → prediction, following Open-ViTabQA.
- A four-label ViNLI model was needed, so **XLM-R Large was fine-tuned
  in-house** on Kaggle (`reproductions/vinli/`). The ViNLI paper (COLING
  2022) reports **85,99 accuracy / 86,10 macro-F1** on four labels and
  81,36 / 81,31 without `OTHER`.
- **In-house fine-tuning result** (`checkpoints/results.zip` →
  `vinli-xlmr-large-4label/run.json`): XLM-R Large, four labels, Adam,
  lr 1e-5, batch 16, 10 epochs, max length 128, seed 42; best dev epoch 3.
  Split sizes 24.376 / 3.009 / 2.991 match the paper. **Dev: 85,24 accuracy
  / 85,18 macro-F1. Test: 85,42 accuracy / 85,49 macro-F1**, versus the
  paper's 85,99 / 86,10 (−0,57 / −0,61). Per-label test F1: entailment
  83,61, contradiction 79,89, neutral 80,27, other 98,20. The training data
  came from a **third-party Hugging Face mirror**
  (`presencesw/vinli_4_label`), not an author release (`provenance.json`
  warns about this).
- **Exact reproduction is blocked by data and provenance, not code:** the
  paper gives split **sizes**, but no split IDs, seed, schema, checkpoint,
  or training code; the group's official dataset page currently **does
  not list ViNLI**. This is a **replication-style** model and cannot be
  compared directly with their Table 6.
- BIF is a **secondary metric**, not a replacement for paired EM tests.
  Most experiments still **lack paired BIF bootstrap intervals**.
