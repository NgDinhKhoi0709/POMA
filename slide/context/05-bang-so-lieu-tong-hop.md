# 05 — Results matrix with metadata

This file **introduces no new figures**. It reorganizes the results in
[04](04-nhat-ky-thuc-nghiem.md) with enough metadata to identify valid
comparisons. Use it when building slide tables.

## Rule: direct comparison requires all six fields to match

`split + n` · `parser` · `scorer + candidate policy` ·
`model/provider` · `prompt` · `run`

If a field is missing or differs, mark the slide **"not directly comparable."**

---

## A. One-answer results on all 992 test questions — main thesis comparison

Shared settings: `dataset/qas_test.json`, n=992; **legacy** parser;
`exact_match` scorer hash `6ddd7cf6…`; one-answer policy (`--strict`);
`openrouter/qwen/qwen3-8b` (Alibaba).

| System | EM | F1 | BIF | Source artifact / generation run | Direct comparison? |
|---|---:|---:|---:|---|---|
| POMA-first | 66,63 | 79,80 | 75,00 | `q2_revision/.../full/raw/poma.json` (Q2 run) | ✅ with POMA+GSA |
| Few-shot raw | 67,34 | 78,63 | 73,83 | `outputs/baseline/qwen/full_few_shot/`: **historical artifact, `source_manifest = None`, generation run unknown** | ⚠️ generated at a different time from POMA-first |
| POMA + GSA | 68,45 | 81,31 | 76,43 | New GSA run, D01 | ✅ same run as FS+GSA |
| **Few-shot + GSA** | **70,16** | 81,52 | 76,10 | New GSA run, D01 | ✅ same run as POMA+GSA |
| Zero-shot raw | 63,10 | 76,14 | 70,02 | `outputs/baseline/qwen/`: **historical artifact** | ⚠️ run unknown |
| Task decomposition raw | 59,98 | 74,01 | 68,68 | `outputs/baseline/qwen/`: **historical artifact** | ⚠️ run unknown |
| CoT raw | 59,48 | 74,01 | 69,26 (n=990) | `outputs/baseline/qwen/`: **historical artifact** | ⚠️ run unknown |
| POMA `all` (oracle) | 74,90 | 83,42 | — | Same raw data as POMA-first | ⚠️ **oracle, not a deployable system** |
| POMA control (D11) | 68,35 | — | 75,33 | **D11 run** | ❌ **+1,7 versus 66,63 despite identical settings** |
| v3lite (D11) | 68,75 | — | 75,97 | D11 run | ✅ with D11 control; ❌ not with 70,16 |

**Key comparison:** POMA+GSA − FS+GSA = **−1,71 EM points**, paired 95% CI
[−3,93; +0,50], 53 wins / 70 losses / 869 ties. **This is the strongest
comparison in the table:** both GSA branches were rerun together in D01 on
the same QAs. The same pair on BIF: **+0,33 points, paired 95% CI [−0,98;
+1,63]** — BIF points the other way but its interval also includes zero, so
BIF does not resolve what EM leaves open. Computed from
`outputs/evaluation/bif/poma_gsa_fallback_details.json` /
`few_shot_gsa_fallback_details.json` (already on disk from an earlier run),
paired bootstrap via `evaluation.bootstrap.paired_bootstrap_ci`.

**Provenance caveat (explain if asked):** the `raw` rows come from older
stored baseline files **without full generation manifests**. The original
few-shot artifact also has **18/992 records with `parse_ok=false`**. Thus
POMA-first versus Few-shot raw (−0,71) is weaker than the comparison of the
two GSA branches. Source: `outputs/d01/.../fair_audit.json`, field
`systems/few-shot-raw/source_manifest = None`.

**BIF exclusions in this table.** `CoT raw`'s BIF drops 2/992 questions
(`17_4_238`, `17_4_219`): their stored prediction is literal API-error text
("ERROR: Generation failed…"), not an answer — a data defect in this historical
artifact, not a scorer bug. Separately, the Gemma and SEA-LION backbone
comparisons (see [04](04-nhat-ky-thuc-nghiem.md)) each drop one question to a
**real** BIF scorer bug: a very long genuine list-style answer (1,000+
characters) crashes PhoBERTScore's alignment with an `index out of bounds`
error, on both CPU and CUDA. Do not conflate the two causes.

**Small differences from the README table:** ZS F1 is 76,14 here versus
76,16 there; ZS EM 63,10 versus 62,40; FS EM 67,34 versus 67,14. These
are **not typos**. They reflect **evaluator drift**: identical artifacts
scored by different scorer versions. Always identify the scorer when
placing the tables together.

**Required slide warning:** do not place v3lite's 68,75 next to 66,63 /
68,45 / 70,16 without mentioning the 1,7-point difference between runs.

---

## B. Subset results — compare only within each group

| Group | n | Parser | Subset | Variants and EM |
|---|---:|---|---|---|
| **D04** | 200 | legacy | Stratified by hint, seed 42 | ZS 64,0 · CoT 61,0 · FS 69,5 · POMA-first 68,5 · POMA+GSA 70,0 · FS+GSA 71,5 |
| **D09** | 200 | legacy | Same subset as D04 | v1_raw 52,5 · v1_clean 51,0 · pipe 56,0 · pipe_path 55,5 · md 52,5 · md_kv 56,5 · row_anchor 54,0 · json 51,0 |
| **D10** | 155 | legacy | Questions with tables >2.000 tokens | v1_raw 52,26 · h1_k20 54,19 · h1_k10 52,26 |
| **D12** | 500 | **fixed** | First 500 test questions | v1_raw 60,20 · pipe_clean 60,20 · pipe_nohdr 62,20 · pipe_h1 60,40 · nohdr_h1 62,60 |
| **D13** | 200 | **fixed** | Covers 76 tables with structural features | v1_raw 65,5 · v1_clean 67,5 · hdrfilter 51,0 |

**Do not compare across these groups.** For example, "pipe scores 56,0 in
D09 and 60,20 in D12" compares different parsers, question sets, and n values.

On the **same 200-question D04/D09 subset**, with the same Flatten V1
string and model:

- old `v1_zs` prompt: **64,0** EM;
- current `v3_zs_minimal` prompt: **52,5** EM.

→ **The prompt gap (−11,5 points) exceeds the entire range of table-format
effects (at most +4,0).** It also explains why D09 and D12/D13 have
different baselines.

---

## C. Across backbones — compare only within a backbone

| Backbone | Infrastructure | n | ZS | FS | CoT | POMA |
|---|---|---:|---:|---:|---:|---:|
| Qwen3-8B | OpenRouter (Alibaba) | 992 | 63,10 | 67,34 | 59,48 | 66,63 (first) / 68,45 (+GSA) |
| Gemma-3-4B-IT | OpenRouter | 543 (incomplete) | **39,59** | — | — | **26,70** (first) |
| SEA-LION v3 8B IT | Kaggle + vLLM (local) | 992 / 991 | 49,50 | 49,45 | 47,83 | 43,00 (n=486, different subset) |

**Read comparisons within each row, not between backbone rows.** Key points:

- On **Qwen3-8B**, POMA is similar to or slightly below the strongest baseline.
- On **Gemma-3-4B-IT**, POMA **loses to zero-shot by 12,89 points**; CI
  [−17,13; −8,66] excludes zero.
- On **SEA-LION**, the three baselines score around 48–50, while POMA scores
  43,0 on another subset. **No paired comparison exists**, so no conclusion
  follows yet.

General pattern: **any benefit from POMA depends on the backbone and disappears
or reverses with a weaker one.** ViPanelTR also observes this.

---

## D. "Published" versus "audited" results — for one slide

| Source | POMA EM | Few-shot EM | Scoring | Note |
|---|---:|---:|---|---|
| Draft / README | **80,24** | 67,14 | POMA best-of-K, baseline one answer | **Asymmetric** |
| Audit of old run | 67,74 | 67,34 | One answer for both | +0,40 [−2,12; +3,02] |
| Audit of new run (raw) | 66,63 | 67,34 | One answer for both | −0,71 [−3,33; +1,81] |
| Audit of new run (same GSA) | 68,45 | **70,16** | One answer and same finalizer for both | **−1,71 [−3,93; +0,50]** |

---

## E. Cost and tokens — where positive results do exist

| Measurement | Value | Scope |
|---|---|---|
| One full POMA run (992 questions) | **$1,7158**, 6.358.343 prompt tokens, mean 38,1 s/question (16 workers) | D11 control |
| Deployed v3lite | $1,6734, 5.950.649 prompt tokens **(−6,4%)** | But **159 additional gate calls (+16%) were not costed** |
| H1 k=20 on long-table questions only | Input tokens **−46,6%**, cost −35,3%, latency 29,3 → 17,4 s | n=155 |
| H1 across all 992 POMA questions | **Only −6,4%** | Savings diluted |
| `nohdr_h1` (pipe + H1) | API prompt tokens **−28,4%** versus `v1_raw` | n=500, D12 |
| GSA | +1 call/question, $0,468–0,478 for 992 questions | D01/D02 |
| D04 planner | +1 call/question, $0,0822 for 200 questions (estimated $0,41 for 992) | D04 |
| D13 `hdrfilter` | **Total tokens +75,9%; cost 2,75 times higher** | D13 |

**The cost result is the only clearly positive result so far:** reducing
long tables preserves EM and genuinely cuts tokens for affected questions.
Within multistage POMA, however, savings shrink to 6,4%.

---

## F. Theoretical headroom versus captured gain

| Mechanism | Theoretical ceiling | Captured gain |
|---|---|---|
| Arithmetic executor (D04) | 1,8–3,2 points | **0** (gate missed every wrong answer) |
| Answerability gate (D11) | 4,7 points (47 false `Null` answers) | **+0,1** (16 replacements: 5 corrections, 4 correct `Null` answers broken, 7 still wrong) |
| Specialist-disagreement resolver | +0,71 points | +0,30 observed |
| Two-branch consensus (not built) | +5,2 points | Adjudicator must be ≥45,9% accurate on 224 disagreements to gain +3 |
| Perfect H1 retrieval | <0,1 points | — |

**Recurring pattern:** measured headroom is large, but captured gain is near
zero. The mechanisms cannot reliably identify **when an answer needs fixing**.
