# Faithful structure encoding for Open-ViTabQA — ranked shortlist

## 0. Measured facts about YOUR data (I ran this, not from papers)

Parsed all 329 `table_html` with a span-expanding grid parser; cross-tabbed against `qas_test.json` (992 Q).

**`table_type` is MULTI-LABEL, not 3-way.** Test-question strata:
`normal 461 | merged_value 262 | merged_header 143 | BOTH 126`.
A 3-way report either double-counts 126 questions or hides the interaction. Report 4 strata as primary plus a collapsed 3-way view for comparability.

**Unverified:** I could not locate **ViPanelTR** in any public source (two searches). Its F1 84.25–85.71 vs 75–78 figures are user-supplied and its stratification convention is unknown. POMA is verifiable (repo + paper: Qwen3-8B, 80.24 EM / 88.23 F1 on the test split, Flatten V1 confirmed) but its 83.51/80.42/75.95 split convention is not stated in what I could reach. **Confirm whether both systems used a 3-way or 4-way split before comparing your numbers to theirs** — if they used 3-way, their 'merged_header' and 'merged_value' cells each silently include the 126 'both' questions, and their reported gap is not the gap you will measure.

**Structural taxonomy** (tables / test questions):

| feature | tables | questions | normal | m_header | m_value | both |
|---|---|---|---|---|---|---|
| A full-width banner row (colspan == ncols) | 44 | 128 | 0 | 59 | 11 | 58 |
| B left stub `<th>` column (matrix layout) | 57 | 153 | 7 | 50 | 38 | 58 |
| C genuine nested colspan header groups (depth≥2) | **28** | **92** | 0 | 64 | 0 | 28 |
| D `<td>` colspan | 66 | 197 | 0 | 0 | 99 | 98 |
| D `<td>` rowspan | 81 | **252** | 0 | 0 | 196 | 56 |
| E `<th>` rowspan | 37 | 111 | 0 | 67 | 0 | 44 |
| no merge feature | 147 | 481 | 454 | 27 | 0 | 0 |

Header depth: 256 tables have 1 header row, **60 have 2, only 2 have 3**, 11 have 0.
**Only 38 tables are ones where a fully-qualified header path differs at all from the flat string** (C or E). This is the single most important finding: *"merged header" in Open-ViTabQA is mostly NOT deep nesting.* It is (a) full-width caption banners repeated N times by span expansion, and (b) left stub-header matrix layouts. A `"Doanh thu > 2023 > Quý 1"` encoding is aimed at a **116-question minority on test** (union of C and E).

**Slice sizes across all splits** (needed for the ablations in §3 — test alone is too small to resolve a 5-pt shift). Total 9,911 pairs: train 7,928 / dev 991 / test 992. C∪E feature (where a header path differs from flat): **train 866 + dev 113 = 979**, test 116. Other slices, train+dev: A banner 998, B stub 1,377, C nested 759, D td_rowspan 2,236, D td_colspan 1,621, E th_rowspan 958. 4-way strata over all splits: normal 4,717 / merged_value 2,671 / merged_header 1,426 / both 1,097. These methods are prompt-only with no training, so **using train+dev for the feature-restricted slices leaks nothing** — keep test for headline numbers.

**Measured token cost** (o200k_base proxy; Qwen3 BPE will differ somewhat on Vietnamese diacritics — treat ratios, not absolutes):

| encoding | median | mean | p90 | max | ×E0 | normal | m_hdr | m_val | both |
|---|---|---|---|---|---|---|---|---|---|
| RAW_HTML | 3958 | 8369 | 17571 | 94629 | 5.74× | 8903 | 4981 | 11470 | 3809 |
| **E0 Flatten V1** | 876 | 1457 | 3001 | 17633 | 1.00× | 1052 | 1234 | 2353 | 1328 |
| E1 flat + span-dedupe | 810 | 1330 | 2845 | 14081 | **0.91×** | 1052 | 1159 | 2039 | 1066 |
| E2 attribute-stripped HTML | 1236 | 2015 | 4477 | 15893 | 1.38× | 1813 | 1883 | 2764 | 1346 |
| E3 relational (qualified cols) | 828 | 1427 | 3006 | 17635 | 0.98× | 1055 | 1143 | 2350 | 1190 |
| E4 fully-qualified cell paths | 2061 | 3218 | 7042 | 33689 | **2.21×** | 2599 | 3307 | 4343 | 3048 |

Raw HTML is not viable at the tail (94k tokens, Wikipedia `style`/`srcset`/`href` junk). Span duplication: median ratio 1.03, but 50 tables >1.3, worst `99911_1` at **9.27×** (a colspan=14 banner repeated 14× per row).

**Oracle answer-presence — corrected.** My first pass used substring containment over the whole serialization; that is near-vacuous for ranking encodings (none of them drop text, so all scored 62.1% ±0.6) and it inflates the ceiling, because a gold answer of `"7"` matches any 7 anywhere. Re-measured as **whole-cell match** (is the normalized gold answer exactly some cell's text?):

| | overall | normal | merged_header | merged_value | both |
|---|---|---|---|---|---|
| answer is a table cell | **43.2%** | 46.4% | 46.9% | **32.8%** | 49.2% |
| same, answers ≥3 chars (n=825) | 42.9% | 46.5% | 47.2% | **33.6%** | 43.0% |

The ordering reverses versus the substring version (`both` was 73.8%, an artifact of span duplication creating spurious matches). **The real extractive ceiling is ~43%, and `merged_value` is the worst stratum at 32.8%** — consistent with it being the `td_rowspan`-heavy slice (252 test questions). The other ~57% is computation, Yes/No, aggregation and list answers: hints show 199 "Sử dụng tính toán", 155 Yes/No, 175 cross-cell combination, 56 list/sort. **Cap your expected encoding gain accordingly** — and note that no encoding comparison can be made on this metric, only the ceiling.

---

## 1. Method cards

### Sui et al., "Table Meets LLM" — the paper you named

| field | value |
|---|---|
| Method + link | SUC benchmark + self-augmented prompting — https://arxiv.org/abs/2305.13062 |
| Venue + year | **WSDM 2024** (peer reviewed) |
| Model sizes tested | **GPT-3.5 (text-davinci-003) and GPT-4 ONLY.** Verified from §5.1: "we evaluate the performance on GPT-3.5 and GPT-4... we utilize text-davinci-003 in all experiments." **Zero open-weight models. Zero sub-10B. Do not transfer its format ranking to Qwen3-8B.** |
| Fine-tuning? | Prompt-only |
| Gain on hierarchical/merged | Not a hierarchical benchmark — "we mainly focus on flat relational tables". BUT it has a **Merged Cell Detection** SUC task: GPT-3.5 — Markdown **78.00** > HTML 76.67 > XML 75.00 > JSON 73.33 > NL+Sep 71.33. So on the one merged-cell-specific task, **HTML is not the winner.** Headline "HTML +6.76% over NL+Sep" is the 7-task average. Downstream (GPT-3.5): HTML best on TabFact 71.33, HybridQA 47.29, SQA 71.31. |
| Token delta | Not reported |
| ≥2 datasets? multilingual? | 5 datasets (TabFact, HybridQA, SQA, Feverous, ToTTo). **English only.** |

Transferable finding independent of size: **self-augmented prompting** ("identify critical values and ranges") gave the largest gain of any prompt manipulation (TabFact +2.31, ToTTo BLEU-4 17.24→22.92). Also: 0-shot drops 30.4 pp vs 1-shot on structure tasks. Also: partition marks and format explanations *hurt* Cell Lookup.

### TABVERSE — the format comparison that DOES include sub-10B models

| field | value |
|---|---|
| Method + link | Cross-format controlled benchmark — https://arxiv.org/abs/2606.09578 |
| Venue + year | **arXiv preprint, unreviewed** (Jun 2026; 4 votes / 21 views). MBZUAI + SUTD. |
| Model sizes tested | **Qwen2.5-7B-Instruct, TableGPT2-7B, Qwen3-VL-8B, Gemma-3-12B/27B, InternVL3.5-14B/30B, Ministral-3-14B, LLaVA-1.6-7B/13B, SmolVLM2-2.2B, GPT-5.2, Gemini-3-Flash.** This is the one with real coverage at your size class. |
| Fine-tuning? | Prompt-only, zero-shot, greedy |
| Gain on hierarchical/merged | Not stratified by merged cells. |
| Token delta | Not reported |
| ≥2 datasets? | 5 sources (FEVEROUS, HybridQA, TabFact, SQA, WTQ), 700 balanced. English. |

**This is your "does not transfer" evidence, with numbers.** QA EM on text input:

| model | HTML | LaTeX | Markdown | winner |
|---|---|---|---|---|
| Qwen2.5-7B-Instruct | 44.57 | 42.71 | **45.43** | Markdown |
| TableGPT2-7B | **44.43** | 41.57 | 42.14 | HTML |
| Qwen3-VL-8B | **53.43** | 52.14 | 53.29 | HTML (tie) |
| Gemma-3-27B | **53.43** | 51.29 | 53.14 | HTML (tie) |
| GPT-5.2 | 57.43 | 57.29 | **58.00** | Markdown |
| Gemini-3-Flash | **65.71** | 65.00 | 65.43 | HTML |

Spread at 7–8B is ≤2.9 pp and the ranking **flips between two 7B models**. Contrast with the *structure* subtasks (SUC, LLM-text pipeline) where HTML wins decisively at 7B: Qwen2.5-7B table-partition HTML 16.7 vs Markdown 5.9; cell-lookup 25.4 vs 8.1. **Interpretation for you: format choice buys ~1–3 pp on end-task QA at 8B and is model-specific, but HTML-like explicit tagging buys 10–20 pp on structure-*probing*. That argues for a structure-tagged view as a separate agent, not as a global format swap.** Also: Qwen3-VL-**8B** beats Qwen3-**30B**-A3B under strict EM; "scaling alone does not guarantee better table understanding."

### HiTab — the reference hierarchical benchmark

| field | value |
|---|---|
| Method + link | Dataset + hierarchy-aware logical form — https://arxiv.org/abs/2108.06712 |
| Venue + year | **ACL 2022** (peer reviewed) |
| Model sizes tested | BERT-base (NSM/MAPO), TaPas-base, BART, T5. **Pre-LLM. No decoder LLM baselines in the original paper.** |
| Fine-tuning? | All fine-tuned / weakly supervised |
| Gain on hierarchical | MAPO original logical form 29.2 → **hierarchy-aware logical form 40.7** test EA (+11.5). Partial supervision: MML 45.1. TaPas 38.9. Level-wise accuracy (sum of left+top header levels): 42.9 / 50.0 / 44.7 / 40.5 / **14.1** for levels 2/3/4/5/>5. NLG BLEU by depth: 31.7 / 26.5 / 21.3 for depth 2/3/4+. |
| Token delta | n/a |
| ≥2 datasets? multilingual? | Single dataset, 3,597 tables, 10,672 Q. **English only.** |

**The directly relevant detail:** HiTab's TaPas baseline preprocesses hierarchical tables exactly like your Flatten V1 — "we unmerge the cells spanning many rows/columns on left/top headers and **duplicate the contents into unmerged cells**. The first top header row is specified as column names." So Flatten V1 == the acknowledged-weak HiTab baseline. Their alternative is NOT a different text serialization; it is a **region-selection logical form** (`filter_tree h`, `filter_level l`) operating on an extracted left/top tree. Also: "We also experimented with other serialization methods, such as **header-data pairing** or template-based method, yet **none reported superiority over the simple concatenation**" (§4.2.3, NLG). That is a *negative* result on path-style serialization at BERT/BART scale — worth citing honestly.

Hierarchy extraction: heuristics from **merged cells + indentation + formulas**, 94% accurate on 100 sampled tables. Your `table_html` gives you merges directly.

### AIT-QA — hierarchy normalization as a preprocessor, with a stratified split

| field | value |
|---|---|
| Method + link | Dataset + table transformations — https://arxiv.org/abs/2106.12944 |
| Venue + year | **NAACL 2022 Industry Track** (peer reviewed) |
| Model sizes tested | TaBERT, TaPas, RCI — all BERT-base/large. **No LLMs.** |
| Fine-tuning? | Pretrained on WikiSQL, zero-shot onto AIT-QA; transformations are **preprocessing** |
| Gain on hierarchical | **CORRECTED ATTRIBUTION — read §4.3 carefully.** Header flattening is a *base* transformation applied to **all three** conditions: "Base transformations are **first** performed... Header hierarchies as flat headers — flattening by concatenating parent header text with children text" + "Row headers as Table cells in a new column." The Base row (RCI 40.58) **already has** concatenated parent>child headers. The only variable across Base 40.58 / all-transpose 48.54 / **partial-transpose 51.84** is **transposition**. So AIT-QA gives **zero isolated evidence for header-path concatenation**, and the **+11.3 pp belongs entirely to transposition.** Model-dependence: TaBERT 33.20→33.98 (+0.8); **TaPas 49.32 → 46.80 — transposition HURTS TaPas.** |
| Token delta | Not reported |
| ≥2 datasets? multilingual? | Single dataset, 116 tables / 515 Q, **lookup questions only**. English. |
| **Stratified split (this is the template for your ablation)** | Row-header-hierarchy vs not: RCI 45.89 vs 54.20; TaPas 47.26 vs 50.39; TaBERT 21.92 vs 38.75. **Average drop 13 pp** — same shape as your POMA 83.51/75.95. |

Key transferable insight: **transposition** gave RCI +11 pp, larger than header flattening alone, because "row headers contain more information than column headers." 57 of your 329 tables are left-stub matrix layouts where this applies.

### TUTA — can its coordinates be emitted as text?

| field | value |
|---|---|
| Method + link | Bi-dimensional coordinate tree + tree attention — https://arxiv.org/abs/2010.12537 |
| Venue + year | **KDD 2021** (peer reviewed) |
| Model sizes tested | BERT-scale encoder, pretrained on 57.9M tables |
| Fine-tuning? | **Full pretraining + fine-tuning. Architecture change (attention mask + position embeddings). Not prompt-reusable as a model.** |
| Gain on hierarchical | Cell Type Classification avg macro-F1: TUTA **88.1** vs TAPAS 82.2, TaBERT 75.3, RNN 84.3. Table Type Classification macro-F1 87.6 vs TaBERT 83.6, TAPAS 80.0. **Neither task is QA.** Ablation: tree position embeddings +2.7 over tree-attention-only. |
| Token delta | n/a |
| ≥2 datasets? | 5 datasets (WebSheet, DeEx, SAUS, CIUS, WCC). English-filtered pretraining. |

**Answer to your question "can their coordinate notion be emitted as TEXT?"** — Partially, and this is the reusable part: the *bi-dimensional coordinate tree* itself is a preprocessor, not a model. Each cell gets `(top_path, left_path)` e.g. left `<2,1>`, top `<2,0>`; flat tables degenerate to Cartesian row/col. Their tree-extraction heuristics (merged cells for top header, indentation for left header, formulas) run on `table_html` with no learning. What is NOT reusable is the mechanism: TUTA's gain comes from **attention-distance masking** (ablation: TUTA-base w/o tree attention 79.9 → TA-distance-2 85.3, a +5.4 jump), and you cannot emit an attention mask as prompt text. TAPAS row/column/rank embeddings are the same story — rank embedding (numeric rank within a column) *is* emittable as text and nobody has tested that for a decoder LLM; that is a genuinely open, cheap experiment.

**Corroborating evidence that the text form is the weak half:** DeepTable (below) implements exactly this split and finds the attention-bias half works and the path half does not.

### DeepTable — tree path encoding tested at 7–8B, with a negative result

| field | value |
|---|---|
| Method + link | Structural Attention Bias + Tree Path Encoding — https://arxiv.org/abs/2609.07707 |
| Venue + year | **arXiv preprint, unreviewed** (Sep 2026; 0 votes / 7 views), NYCU Taiwan |
| Model sizes tested | **DeepSeek-LLM-7B-Chat, Llama-3-8B-Instruct, Qwen2.5-7B-Instruct.** Exactly your class. |
| Fine-tuning? | **LoRA (TableLoRA) + attention patch. Higher cost class. Not prompt-only.** |
| Gain on hierarchical | HiTab, over TableLoRA baseline: SAB-only +5.11 / +15.45 / +2.98. **TPE-only (the path encoding): −1.11 (DeepSeek), −0.04 (Qwen2.5), +13.27 (Llama-3).** Averaged over 3 backbones: SAB +7.85, TPE **+4.04**, both +7.42. Depth-stratified on HiTab top-header depth 1/2/3, TPE delta: +0.14/+1.11/+0.41 (DeepSeek) and +0.28/−0.59/+1.31 (Qwen2.5) — the paper's own words: **"TPE remains nearly flat"** while SAB's gain *grows* with depth. |
| Token delta | Not the mechanism (embeddings, not prompt text) |
| ≥2 datasets? | HiTab, WikiTQ, FeTaQA, TabFact. English. |

**Read this as a warning, not a recipe.** The closest published analogue to "emit the header path" (as a learned embedding) is the component that does *not* work at 7–8B; the component that works is an architecture change you cannot do in a prompt. Also note HiTab arithmetic accuracy is **0.0** for `div` and `sum` across all variants — echoes your 199 computation questions.

Useful baseline numbers for context: TableLoRA HiTab accuracy Qwen2.5-7B **62.38**, Llama-3-8B 58.56, DeepSeek-7B 46.94.

### Semantic Triplet Restoration (STR) — the closest thing to your "structure agent view"

| field | value |
|---|---|
| Method + link | `⟨item_path, feature_path, value⟩` triplets — https://arxiv.org/abs/2605.31550 |
| Venue + year | **arXiv preprint, unreviewed** (May 2026; 2 votes / 3 views). Low-visibility; treat claims as unreplicated. |
| Model sizes tested | GLM-4.5-Air, LongCat-Flash-Lite, **Qwen3-0.6B**. No 7–8B dense model. |
| Fine-tuning? | **Prompt-only** representation (an upstream visual parser is fine-tuned but is not needed for you — you already have HTML) |
| Gain on hierarchical | TableEval-test F1: HTML 86.06 → Full Triplet 86.23 → TripletQL 88.49. WTQ acc: HTML 37.43 → **46.59**. TableBench Numerical Reasoning: HTML 31.49 → **60.71**; sub-tasks Time-based +46.8, Counting +42.0, Aggregation +32.9. **Scale trend (their headline): GLM-4.5-Air +1.64, LongCat-Lite +3.54, Qwen3-0.6B +5.10 (+11.0% rel) — "the smaller the model, the larger the gain."** |
| Token delta | **−14% (Full Triplet) / −32% (routed) vs HTML.** Consistent with my measurement: their baseline is HTML (5.74× my flat); against a compact pipe-joined flat string a path encoding is **+121%**, not a saving. State this explicitly in your thesis or you will misquote them. |
| ≥2 datasets? multilingual? | 4 benchmarks, **Chinese + English** — the only multilingual evidence in the shortlist. |

**Honest negatives you must carry over:** STR *regresses* on TableBench DataAnalysis (HTML 27.67 → 13.56) and FactChecking (78.12 → 77.08). Open-ViTabQA has **155 Yes/No** questions — that is exactly the FactChecking shape.

### ASTRA — semantic tree, and the only sub-10B open-weight ablation of a tree view

| field | value |
|---|---|
| Method + link | AdaSTR semantic tree + dual-mode reasoning — https://arxiv.org/abs/2604.08999 |
| Venue + year | **arXiv preprint, unreviewed** (Apr 2026; 3 votes / 47 views). Zhejiang Univ. |
| Model sizes tested | DeepSeek-V3, GPT-4o, o3 main; **Appendix I.2: Qwen2.5-7B, Llama3.1-8B, Qwen3-8B (thinking + no-thinking).** |
| Fine-tuning? | **Training-free.** Tree construction is itself LLM calls (extra cost). |
| Gain on hierarchical | Main (DeepSeek-V3): AIT-QA 78.5→91.6, HiTab 82.0→90.1, SSTQA 63.2→81.9. **Sub-10B, SSTQA, representation-only ("Direct Prompt Raw Table" → "Direct Prompt Semantic Tree"): Qwen2.5-7B 46.60→49.74 (+3.14); Llama3.1-8B 35.99→37.43 (+1.44); Qwen3-8B no-think 52.75→60.86 (+8.11); Qwen3-8B think 54.97→64.92 (+9.95).** |
| Token delta | Not reported; tree construction adds 29–94 s/table offline, amortized over queries |
| ≥2 datasets? | AIT-QA, HiTab, SSTQA. English. |

**The single most actionable warning in this whole shortlist:** ASTRA's *symbolic* branch on **Llama3.1-8B collapses to 10.47%** (vs 40.45 textual), and on Qwen3-8B removing the self-correction loop costs **−12.67** vs **−1.57** on DeepSeek-V3. Their conclusion: "purely symbolic signals without sufficient linguistic grounding may be difficult to interpret reliably" for smaller models. **A structure-agent that emits a code/coordinate-heavy view is exactly the thing that breaks at 8B.** Whatever structure view you build must stay natural-language-shaped.

### Orthogonal Hierarchical Decomposition (OHD)

| field | value |
|---|---|
| Method + link | Orthogonal row/column tree induction + dual-path lineage — https://arxiv.org/abs/2602.01969 |
| Venue + year | **Claims ICML 2026 (PMLR 306); arXiv v2 Jun 2026. Treat as preprint — I could not verify the acceptance.** |
| Model sizes tested | **Qwen2-72B, Qwen2.5-72B, DeepSeek-V3, TableLLaMA-7B. No sub-10B general model.** |
| Fine-tuning? | Prompt-only, but uses an **LLM as a per-edge semantic arbitrator** — an extra LLM call per candidate header pair. Cost class is well above one pass. |
| Gain on hierarchical | Claimed HiTab EM: Qwen2-72B raw 16.48 → 60.16; Qwen2.5-72B 14.14 → 66.92; DeepSeek-V3 15.85 → 67.74. **Be skeptical: a raw-markdown HiTab EM of 15.85 for DeepSeek-V3 is implausibly low** — ASTRA reports DeepSeek-V3 at 82.0 on HiTab with textual serialization. The two preprints disagree by ~66 points on the same baseline. Do not cite either baseline as fact. |
| Token delta | Not measured, but they report an **honest negative**: with TableLLaMA-7B on full HiTab, OHD EM 63.62 **trails** vanilla 64.71 "due to context truncation caused by the token overhead of explicit structural decomposition." |
| ≥2 datasets? | AIT-QA + HiTab. English/Chinese examples. |

That negative is the most useful thing in the paper for you: **at 7B, path-expansion token overhead can cancel the structural gain.** My measurement says E4 is 2.21× — same mechanism.

### SpreadsheetLLM — verified model sizes, and what it actually shows about 8B

| field | value |
|---|---|
| Method + link | SheetCompressor (structural anchors + inverted index + format aggregation) — https://arxiv.org/abs/2407.09025 |
| Venue + year | Microsoft; arXiv v2 Apr 2025 (NAACL 2025 findings-track lineage; **the arXiv version does not state a venue — I did not verify acceptance**) |
| Model sizes tested | **GPT-4, GPT-3.5, Llama2-7B-chat, Llama3-8B-Instruct, Mistral-7B-v0.2, Phi-3-mini.** Open models via **LoRA fine-tuning**, 8×A100. |
| Fine-tuning? | Both. **Critical: in-context learning with open sub-10B models is catastrophic — Llama3 0.027, Mistral 0.036, Phi3 0.034, Llama2 0.041 F1 on table detection. All structural gains for sub-10B came only after fine-tuning** (Llama3 0.471 → 0.719 with compression). |
| Gain on hierarchical | Task is table *detection*, not hierarchical-header QA. GPT-4 ICL 0.154 → 0.410 compressed. Spreadsheet QA: **GPT-4 only**, 0.466 → 0.743 (compress + CoS + FT). |
| Token delta | **25× compression** (1.55M → 62k tokens on test set); 96% cost reduction. Ablation: removing aggregation *raises* F1 (0.759→0.789) — the format abstraction hurts accuracy, it only buys tokens. |
| ≥2 datasets? | One detection benchmark + one self-built 307-item QA set. **English only** ("spreadsheets containing non-ASCII characters were excluded"). |

Relevance to you is limited: your tables are dense, not sparse; structural anchors target empty-cell sparsity you don't have. The reusable bit is **inverted-index translation** (merge identical cell texts into one entry with an address range) — lossless, and it is the principled version of my E1 dedupe for your colspan-banner pathology.

### Same Content, Different Representations

| field | value |
|---|---|
| Method + link | RePairTQA controlled study — https://arxiv.org/abs/2509.22983 |
| Venue + year | **ICLR 2026** (stated on the paper; peer reviewed) |
| Model sizes tested | GPT-4o, Gemini-2.5-flash/Pro, **Qwen3-235B**, plus NL2SQL/hybrid systems. **No sub-10B.** |
| Fine-tuning? | Prompt-only |
| Gain on hierarchical | Not about merged cells — structured vs semi-structured (verbalized) representation. NL2SQL drops 30–45 pp on semi-structured; LLMs drop 3.5 pp; hybrids <5 pp. |
| Token delta | Not reported |
| ≥2 datasets? | BIRD, MMQA, TableEval. English. |

Use it for one claim only: **representation is a first-order effect, and symbolic/relational pipelines are the most brittle to representation shift.** That is an argument *against* betting everything on a relational-normalization agent for messy Wikipedia tables.

### Also-rans, cited and moved past
- **H2Table** (hierarchical hypergraph, https://arxiv.org/abs/2609.01216) — arXiv preprint, unreviewed; not read in depth.
- **TableEval** (https://arxiv.org/abs/2506.03949) — multilingual (zh/en), multi-structured benchmark; the *evaluation* venue STR uses. Worth citing as the multilingual precedent for your Vietnamese framing.
- **JTON** (https://arxiv.org/abs/2604.05865) — token-efficient JSON superset; token-budget, out of your scope.
- **RSAT** (https://arxiv.org/abs/2605.00199) — trains SLMs 1–8B for cell-level attribution; fine-tuning class.
- **TABBIE / MATE / TableFormer** — all architecture-level (row/col encoders, sparse attention patterns, attention-logit biases). None emit anything as prompt text. TableFormer's mechanism is what DeepTable's SAB reimplements via LoRA. Skip unless you go to fine-tuning.

---

## 2. Cross-cutting verdicts

1. **The format-comparison literature is GPT-shaped and does not transfer.** Sui et al. = GPT-3.5/4 only. Same Content = ≥235B only. SpreadsheetLLM's QA = GPT-4 only. The only sub-10B format comparison is TABVERSE (unreviewed), and it shows the HTML/Markdown ranking **flips between two different 7B models** with a ≤3 pp spread. Write this in your thesis.
2. **Structure-*probing* accuracy and end-task QA accuracy respond differently to format.** TABVERSE: at 7B, HTML beats Markdown by 10–20 pp on cell-lookup/partition but loses by 0.9 pp on QA EM. This is the strongest argument in the literature for your heterogeneous-agent thesis: a structure-tagged view helps *locating*, a fluent view helps *answering*.
3. **Path/coordinate encodings are the weakest-evidenced family at your scale — and there is no peer-reviewed isolated positive result for them at all.** HiTab explicitly reports header-data pairing gave no superiority over plain concatenation; DeepTable's TPE ≈ 0 at 7B and stays flat as header depth grows; OHD's TableLLaMA-7B run *trails* vanilla on token overhead; and AIT-QA, once read correctly, isolates **nothing** for header concatenation. The only positive is STR — unreviewed, 3 views, a 0.6B model, an HTML baseline rather than a compact flat one, and a documented regression on fact-checking.
4. **Transposition is the best-evidenced single intervention in this entire shortlist.** +11.3 pp for RCI on AIT-QA, peer reviewed, isolated, and it costs zero extra tokens. It is also *model-dependent* (helps RCI +11.3, hurts TaPas −2.5) — which makes it a strong heterogeneous-agent candidate, since a view that helps one reader and hurts another is by construction a different view.
5. **Natural-language shape matters more than structural fidelity at 8B.** ASTRA's symbolic branch collapses on Llama3.1-8B (10.47). SpreadsheetLLM's compressed encodings are unusable in ICL for all four sub-10B models. Every encoding you propose should read like prose-adjacent text, not like coordinates.
6. **Your bottleneck may not be encoding at all.** The whole-cell extractive ceiling is **43%**, and the worst stratum (merged_value, 32.8%) is worst for a reason encoding alone cannot fix — many of its answers are computed, not looked up. Cap your expected gain accordingly.

---

## 3. Ranked top-3 to try

**Statistical design that applies to all three.** Test alone (992 Q) cannot resolve a 5-point shift on a feature slice — at n=116 and EM≈0.6, 5 points is ~6 questions, inside binomial noise; DeepTable's own decoding audit showed a measured gap moving 2.49 → 1.50 from a sampling/greedy switch alone. So: **(a)** run the feature-restricted slices on **train+dev** (C∪E = 979 questions instead of 116; these are prompt-only methods, nothing leaks), keeping test for the headline 4-way numbers; **(b)** compare encodings with **McNemar on discordant pairs**, not independent proportions — same questions, two encodings, so the paired test roughly halves the n you need; **(c)** fix greedy decoding and say so.

### #1 — Span-faithful flat + banner hoist ("Flatten V2") — the mandatory control

*Rationale:* it targets the pathologies that actually dominate your data (banners 44 tables, `td_rowspan` 81 tables), it is the only candidate **cheaper** than the baseline, and without it any later gain you credit to a structural encoding is partly just de-duplication.

**Transformation on `table_html`:** parse to a span-aware grid. At each span origin emit `text <header> [span r{R} c{C}]`; at continuation cells emit a single `^` instead of repeating the text. Hoist any row whose single cell has `colspan == ncols` out of the grid into a `# Chú thích bảng:` line — 44 tables, and it kills the 9.27× duplication on `99911_1`. SpreadsheetLLM's inverted-index translation is the principled lossless version of the same idea, and it was their only module with no accuracy cost.

**As a heterogeneous agent view:** weak by design. Its job is to be the control.

**Ablation:** EM/F1 × {normal, merged_header, merged_value, both} for E0 vs E1-dedupe vs E1+banner-hoist. Plus the A-banner slice (998 train+dev Q) and the D-rowspan slice (2,236 Q), where the transformation actually changes the string. McNemar per slice.

**Cost:** 0.91× tokens → **~$1.8/run**; 3 arms ≈ **$5.5**.

### #2 — Stub-table transposition — best-evidenced intervention, and a genuinely heterogeneous view

*Rationale:* after correcting the AIT-QA attribution, this is the **only peer-reviewed, isolated, double-digit gain** on hierarchical-header tables anywhere in this shortlist (+11.3 pp, RCI). It costs zero extra tokens. And its model-dependence (helps RCI, hurts TaPas) is precisely what you want from a second agent view.

**Transformation on `table_html`:** for the **57 left-stub tables / 1,377 train+dev questions**, apply AIT-QA's partial-transpose rule — transpose when the row headers carry more characters than the column headers — so the descriptive stub labels land where 8B models attend. Your `99913_2` climate table is the canonical case: `Tháng | 1 | 2 … | Năm` across the top with `Cao kỉ lục °C (°F)` down the side is exactly the layout AIT-QA found models read badly.

**As a heterogeneous agent view:** strong and free. Agent A reads the table as-is, Agent B reads the transposed view — same content, orthogonal access path, no token penalty. If AIT-QA's model-dependence carries over, the two agents fail on *different* questions, which is the claim you actually want to make.

**Ablation:** EM/F1 × 4 strata, plus the B-stub slice (1,377 train+dev Q — comfortably powered). Arms: as-is / partial-transpose / all-transpose (AIT-QA's "All T" was *worse* than partial for RCI — replicate that). **Complementarity:** disagreement rate and oracle-of-2 between the as-is agent and the transposed agent, per stratum.

**Cost:** ~1.0× tokens → **~$2/run**; 3 arms ≈ **$6**.

### #3 — Structure-probe sidecar: TUTA-style bi-tree coordinates as a short text manifest

*Rationale:* the direct answer to your research question and the novel slot. TABVERSE shows explicit structural tagging buys **10–20 pp on structure *probing*** at 7B while barely moving QA EM — so deploy it where it is strong, as a locator, not as a global format swap. TUTA's tree-extraction heuristics (merged cells → top tree, indentation → left tree) run on your HTML with no learning; only the attention mechanism is un-portable, and DeepTable confirms the attention half is the half that works.

**Transformation on `table_html`:** keep the flat string unchanged and **append** a compact manifest (~100–300 tokens, versus E4's +121%): table shape and header depth; the list of fully-qualified column paths (`"Doanh thu > 2023 > Quý 1"` — this subsumes the E3 relational view at 0.98× cost); row-header paths for stub tables; a span map (`banner rows: 1`, `spanning cells: r3c2 spans 1×4`); and — the piece nobody has tested for a decoder LLM — **TAPAS-style rank emitted as text** (per numeric column, the argmax/argmin row labels). The structure agent's output is a *cell coordinate or qualified header path*, which the flat agent then resolves.

**As a heterogeneous agent view:** strongest of the three, and the design the evidence supports. Additive and small, so it avoids OHD's TableLLaMA-7B truncation failure; natural-language-shaped, so it avoids ASTRA's Llama-3.1-8B symbolic collapse (10.47 vs 40.45 textual). Keep a hard fallback: invalid coordinate → defer to the flat agent. ASTRA measured the cost of dropping that fallback at **−12.67 on Qwen3-8B** versus −1.57 on DeepSeek-V3.

**Ablation:** arms = flat only / flat+manifest / flat+manifest+structure-agent-as-locator, each EM/F1 × 4 strata, plus the C∪E slice (979 train+dev Q). Report the structure agent's **coordinate precision separately** from end-task EM — TABVERSE shows that is where the signal lives, and it is the metric that can succeed even if EM does not move. This is the arm where complementarity is the primary claim, not a side measurement.

**Cost — repriced.** Arm 3 is **two LLM calls per question**, so ≥2× calls before any token ratio, and STR's own appendix reports output tokens rising **+60.1%** even while input tokens fell 36.9%. Realistic: flat+manifest ~1.15× ≈ **$2.3/run**; the two-call locator arm ≈ **$4–4.5/run**. Three arms ≈ **$9**. Optional E4 full-cell-path falsification arm at 2.21× ≈ **$4.4**.

**Total program (#1+#2+#3) ≈ $20–25**, ≈ $29 with the falsification arm. Fine-tuning (DeepTable/TableLoRA-style SAB, the component that actually works at 7–8B) is the next cost class — DeepTable's own accounting is ~3,041 GPU-hours on 2×L40S across 202 runs — and I would not enter it before the prompt-only arms plateau.

### Demoted, with reasons
- **Header-path relational view as a standalone bet (E3).** Folded into #3's manifest, where it costs ~0 extra. Standalone its prior is weak-to-negative: no peer-reviewed isolated positive exists, HiTab reports an explicit null, DeepTable's TPE is flat at 7B, and it only changes the string for 38 of 329 tables.
- **Full per-cell triplets (E4) as the primary encoding.** 2.21× tokens, 4,343 tok/question on merged_value, and every sub-10B data point (DeepTable TPE ≈ 0, OHD TableLLaMA-7B −1.1, ASTRA symbolic collapse on Llama-3.1-8B) points against it. Run it to falsify, not to win — a clean negative replicating OHD's 7B truncation result is itself a thesis contribution.
