# Agent "papers" slice: table serialization / representation for zero-shot Vietnamese Table QA

Scope: arXiv/alphaXiv papers NOT in the excluded list (TAP4LLM, TableRAG, PieTa, 2305.13062, TABVERSE, HiTab, AIT-QA, TUTA, DeepTable, STR, ASTRA, OHD, SpreadsheetLLM, RePairTQA, H2Table, TableEval, JTON, RSAT, TABBIE/MATE/TableFormer, ITR).
Tags: [verified] = read in the paper text returned by alphaXiv `answer_pdf_queries` in this session. [inference] = my reasoning, not in a paper.
Venue policy: I only state a venue if the fetched text itself says so. "arXiv preprint (no venue stated in fetched text)" is NOT a claim that it is unpublished.

## 1. Papers checked (opened and read)

| arXiv id | Title (short) | Venue status | Models | Verdict |
|---|---|---|---|---|
| 2310.10358 | Tabular Representation, Noisy Operators... (Singha et al., Microsoft) | Header says "Preprint. Under review", v1 Oct 2023 [verified] | GPT-3 text-davinci-003 only | USEFUL but weak transfer. 8-format comparison (DataFrame code, JSON, CSV, TSV, DataMatrix, Markdown, HTML, HTML-no-space). Structure tasks on flat single-type Kaggle tables, NOT QA. Candidates C1, C2. |
| 2601.08444 | Beyond Linearization: Attributed Table Graphs (TabGR) | arXiv v2, Aug 2026, no venue stated [verified] | GPT-4o-mini, GPT-5-mini, Llama3.3-70B (default), Llama3.1-70B, Llama3.1-8B, Qwen2.5-72B | USEFUL. Only paper found with a same-backbone Markdown/JSON/HTML/LaTeX vs explicit-triple table (Table 6) plus a HiTab hierarchy recipe. Candidate C3. |
| 2312.16702 | Rethinking Tabular Data Understanding with LLMs (Liu, Wang, Chen) | arXiv v1 Dec 2023, no venue stated [verified] | GPT-3.5 only | USEFUL for orientation/transposition (NORM). Candidate C5. Honest null on unperturbed tables. |
| 2501.19378 | TableMaster | "Published as a conference paper at ICLR 2026" [verified from page header] | GPT-4o-mini (main). Page 9 also says Binder/Dater etc. compared on gpt-4o-mini and gpt-3.5-turbo | USEFUL for LLM verbalization (C4) and Table-of-Focus; assumes FLAT tables (Appx B: "we assume all tables are flat"). |
| 2402.12869 | Table-to-Text methods for QA with domain hybrid data (Min et al.) | arXiv v2 Apr 2024, no venue stated [verified] | OPT-1.3B..13B, Llama2-7B/13B/70B, GPT-3.5-turbo | NEGATIVE/weak evidence for row-to-sentence templates (C4b). Setting is RAG/DSFT over a corpus, human/GPT-4 1-5 scores, not EM over a given table. |
| 2406.17961 | NormTab | arXiv v2 Apr 2025, no venue stated [verified] | gpt-3.5-turbo (also gemini-1.5-flash, gpt-4-turbo) | PARTIAL. Value+structure normalization then SQL, not text-reading. Candidate C6 (deterministic parts only). |
| 2404.10150 | TabSQLify | arXiv v1 Apr 2024, no venue stated [verified] | gpt-3.5-turbo | PARTIAL. Sub-table via generated SQL; preprocessing (strip thousand commas, dates to YYYY-MM-DD) and schema-plus-3-rows prompt. Not a zero-shot single-prompt method. |
| 2602.20017 | QUIETT: query-independent table transformation | arXiv v1 Feb 2026, no venue stated [verified] | Gemini-2.0/2.5, DeepSeek-V3.1, Qwen3-80B, GPT-OSS-120B; Table 5 uses LLaMA/Mistral QA models | HEAVY, unclear ablation. 3 LLM calls per table + code execution. Candidate C7 (multi-agent only). |
| 2505.14131 | Texts or Images? (Zhou et al., Bosch) | arXiv v1 May 2025, no venue stated [verified] | Qwen2-7B/72B, Pixtral-12B, Phi-3.5, Mistral-7B, GLM-4-9B, InternLM2.5-7B and their VLMs | REJECTED as a serialization source: compares text vs image, not text formats. Only note: it reports its 3 prompt layouts (pipe, list-of-lists, `[Row i]:` lines) but no per-layout results. |
| 2604.24040 | Robustness of Tabular Retrieval via Representational Stability | "Preprint. Under review." v2 Apr 2026 [verified] | Retrievers only (MPNet, BGE-M3, ReasonIR, SPLADE) | REJECTED: retrieval Recall@1, not QA. One fact, model-dependent: for MPNet on WTQ, R@1 pipe 0.25, tsv 0.25, csv 0.24, html 0.09, json 0.14, xml 0.10, but ReasonIR ranks xml best (0.37) on the same data, so even retrieval rankings flip by encoder. Irrelevant to generative QA. |
| 2508.16265 | M3TQA multilingual multitask table QA | arXiv v1 Aug 2025, no venue stated [verified] | 20 models incl. Qwen3-8B/32B, Llama-3.1-8B | USEFUL only as multilingual baseline evidence (Vietnamese included). No serialization comparison found in returned pages; prompt table format not visible to me. |
| 2411.10541 | Does Prompt Formatting Have Any Impact on LLM Performance? | arXiv v1 Nov 2024, no venue stated [verified] | GPT-3.5/4 only | REJECTED: formats INSTRUCTION templates (plain/Markdown/YAML/JSON), not tables. Only takeaway: no universally best format; GPT-3.5 prefers JSON, GPT-4 Markdown; rankings do not transfer between model series. Do not cite for table serialization. |

### Seen in search snippets only (NOT opened, do not cite for claims)
2609.03395 TabScope, 2608.24082 PARTAB, 2607.11207 ProgramTab, 2605.14465 TABALIGN, 2604.03616 The Format Tax (about structured OUTPUT, not table input), 2604.11970 IndoTabVQA (image VQA), 2402.05121 and 2510.09671 (surveys), 2607.19257 Prompt Design at Scale. None opened.

### Not found
No paper found (via alphaXiv discovery, ~8 queries) that (i) compares table text formats on Vietnamese or any low-resource-language table QA, or (ii) compares formats on merged-cell tables at <=10B with QA metrics. The Vietnamese question therefore stays open. I did not find Sui et al. follow-ups beyond the excluded list.

## 2. Key cross-paper facts (all [verified] unless tagged)

1. Format rankings conflict across papers and are model-specific: Singha (GPT-3) says Markdown is the WORST format (fact-finding overall 67.32, transformation F1 36.11) and DataFrame-code/JSON best; TabGR (Llama3.3-70B, WikiTQ) says HTML 77.3 > LaTeX 76.3 > Markdown 75.5 > JSON 74.2; the excluded TABVERSE says Markdown ~ HTML at 7-8B. Nothing here contradicts "format choice is worth ~1-3 pp at 7-8B end-task QA" [inference from combining with the already-known TABVERSE numbers].
2. Nobody here tests Qwen3-8B on a format comparison. The only Qwen-family sub-10B numbers I read are Qwen2-7B in 2505.14131 (no format ablation) and Qwen3-8B in M3TQA (no format ablation).
3. Explicit row-column-cell binding is the only intervention with a large controlled gain over ALL text formats in one table (TabGR Table 6: +2.8 over best text format HTML), but only at 70B, with extra LLM calls, and with structural-error rate 14.4% vs 19.8% (HTML) judged by GPT-5.3.
4. Thinking mode matters more than representation in M3TQA for Qwen3-8B in Vietnamese: Table 8, Vi column, Qwen3-8B-nothinking 13.97 vs Qwen3-8B-thinking 28.78 (same table content). [verified] This is not a representation result but it bounds how much a serialization tweak can move things.

## 3. CANDIDATE REPRESENTATIONS (not already covered)

Toy table used below (illustrative values, not from any paper):
Quốc gia | Dân số | Diện tích
Việt Nam | 100.000.000 | 331.212
Lào | 7.500.000 | 236.800
Campuchia | 16.900.000 | 181.035

Baseline for comparison (project Flatten V1, approximate): `Quốc gia <header> | Dân số <header> | Diện tích <header>` then `Việt Nam | 100.000.000 | 331.212` per line.

### C1. JSON records keyed by row index (header repeated in every row)
Serialization:
```
{"0": {"Quốc gia": "Việt Nam", "Dân số": "100.000.000", "Diện tích": "331.212"},
 "1": {"Quốc gia": "Lào", "Dân số": "7.500.000", "Diện tích": "236.800"},
 "2": {"Quốc gia": "Campuchia", "Dân số": "16.900.000", "Diện tích": "181.035"}}
```
- Source: 2310.10358 Sec 3.1, Fig 1 and Sec 5.1 (text says each row is on its own line, keyed by row index, with a dict keyed by header names) [verified]. My example is a constructed instance of that description.
- Models: GPT-3 (text-davinci-003) only. No open-weight, no sub-10B, English Kaggle tables, flat tables with one datatype per column, 4097-token limit [verified].
- Reported (fact-finding pass@1, Table 1) [verified]: JSON overall 77.93; NavigationTests 71.43 vs CSV 65.57, TSV 64.43, Markdown 48.71, DFLoader 68.29, HTML 58.83; RowLookup JSON 78.86 vs CSV 78.14. Markdown overall 67.32. Authors' explanation: "orderly structure and repeating navigation elements (specifically headers)".
- Token cost vs pipe baseline: NOT reported. Paper only notes HTML's verbosity: with the 4097 limit HTML fits "up to half as many rows" [verified]. JSON repeats every header per row, so cost scales with rows x columns of header length [inference]; for long Vietnamese headers this is likely >1.5x pipe [inference, unmeasured].
- Merged cells: not tested (flat tables only). Their ColumnMerger noise op hurt JSON transformation but did not hurt row lookup (+2.28, n.s.) [verified]. For spans, duplicate header names collide as JSON keys (e.g. repeated "Năm"); would need suffixing [inference].
- Caution: structure tasks are self-supervised lookups, not QA; the paper itself says whether structure-task performance correlates with QA is future work [verified, Conclusion].

### C2. DataFrame-constructor code snippet (column-oriented, "DFLoader")
Serialization:
```
df = pd.DataFrame({
  'Quốc gia': ['Việt Nam', 'Lào', 'Campuchia'],
  'Dân số': ['100.000.000', '7.500.000', '16.900.000'],
  'Diện tích': ['331.212', '236.800', '181.035']})
```
- Source: 2310.10358 Fig 1 / Table 1 / Table 2 [verified: "DFLoader corresponds to the associated Python code snippet to define the table using the Pandas DataFrame API"]. Example is constructed by me.
- Model: GPT-3 only. Reported: highest overall fact-finding pass@1 79.79 (vs CSV 75.78, JSON 77.93, HTML 71.40, Markdown 67.32) and highest transformation F1 98.55 (Markdown 36.11, TSV 78.55, JSON 94.89) [verified].
- Weaknesses in the same paper [verified, Table 3]: ShuffleRows drops DFLoader NavigationTests by 23.29 and RowLookup by 44.57 (JSON only +0.57 / -6.57). So it is order-sensitive for row indexing. Transposition breaks it (-52.85 column lookup).
- Tokens: not reported. Column-major layout also separates each row's cells, which is the opposite of what a "row lookup + compute across columns" question wants [inference]. Also `df` literal wrapper adds ~20 tokens fixed [inference].
- Merged cells: not applicable; duplicate column names cannot be dict keys [inference].
- Verdict: cheap to test as an arm, but the evidence base is one GPT-3 paper on structure tasks. I would not expect it to beat pipe on Open-ViTabQA without measurement. Its main value is as a contrast that Markdown is not universally safe.

### C3. Row-id + header + cell triples (TabGR "Attributed Table Graph")
Serialization (one triple per cell; TabGR's notation is ⟨r_i, h_j, c_ij⟩):
```
(1, Quốc gia, Việt Nam) (1, Dân số, 100.000.000) (1, Diện tích, 331.212)
(2, Quốc gia, Lào) (2, Dân số, 7.500.000) (2, Diện tích, 236.800)
(3, Quốc gia, Campuchia) (3, Dân số, 16.900.000) (3, Diện tích, 181.035)
```
- Source: 2601.08444 Sec 3.1, Fig 2, Sec 4.2, Table 5, Table 6, Table 4, Appx G, Appx K [verified for the triple concept and numbers; the exact triple text syntax in the prompt is in Appx A, which the tool did not return, so the printed syntax above is my reconstruction from Fig 2/case study "(row2; Shirt Sponsor; )" [verified: case study prints `(row2; Shirt Sponsor; )` with semicolons]).
- Models: Llama3.3-70B (default), Qwen2.5-72B, GPT-4o-mini, Llama3.1-70B, Llama3.1-8B [verified]. Only ONE sub-10B run (Llama3.1-8B, Table 19) and it compares against RoT, not a plain linearization: WikiTQ 64.2 vs RoT 63.7, TabFact 75.2 vs 74.8 [verified]. So at 8B the gain over the strongest baseline is +0.5/+0.4.
- Controlled representation comparison, WikiTQ, Llama3.3-70B (Table 6) [verified]: Markdown 75.5, JSON 74.2, HTML 77.3, LaTeX 76.3, ATG 80.1; structural error rate 21.6 / 23.1 / 19.8 / 20.4 / 14.4 percent (errors labelled by GPT-5.3).
- Ablation (Table 5, full-table mode, Llama3.3-70B) [verified]: full TabGR 80.1; w/o QG-PPR 79.5; w/o semantic relevance 77.6; w/o ATG (linearized CoT) 72.7. CAVEAT: "w/o QG-PPR" still keeps the ATG triples plus an LLM semantic selector (and ~3 LLM calls per question, Table 16), so the triples-only zero-shot effect is not isolated. Table 6's ATG row (80.1) is the full method, not triples alone. Treat +2.8 over HTML as an upper bound for representation alone [inference].
- Token cost vs linearized baseline (Table 4, WikiTQ input tokens per question) [verified]: RoT (linearized) 2,013; TabGR w/o QG-PPR 2,500 (1.24x); full TabGR 4,739 (2.35x). TabFact: 1,520 vs 1,998 (1.31x) vs 3,665 (2.41x). Note these baselines are RoT prompts, not a pipe-joined string; the per-cell triple cost vs a compact pipe line is likely higher (my earlier project measurement put full-cell-path at 2.21x; this paper's 1.24x is for a cheaper triple form) [inference].
- Hierarchical / merged cells (Appx G, HiTab, Qwen2-72B) [verified]: (a) multi-level column headers flattened recursively into one attribute path like `Region-Worker Type-Metric` and embedded in every triple; (b) merged cells in leftmost columns forward-filled so each triple carries the full row hierarchy (e.g. Year-Industry). HiTab 74.3 vs GraphOTTER 72.7; no linearized-text baseline reported on HiTab, so the merged-cell benefit is unmeasured [verified]. RealHiTBench (Table 18, Llama3.3-70B): RoT w/ Markdown 49.20 -> RoT w/ TreeThinker structure 53.12 -> TabGR w/ TreeThinker 54.11 [verified]; the +3.9 is from recovered hierarchy, +1.0 from triples.
- Relevance to Open-ViTabQA: the forward-fill left-column rule equals your span duplication (already measured ~+0.19). Path-flattening of headers overlaps with the already-rejected/weak header-path family (DeepTable/TPE flat at 7-8B). New part is only per-cell (row-id, header, value) binding [inference].
- Verdict: the only candidate with an isolated-ish text-format vs explicit-binding comparison, but at 70B and confounded by extra calls. Cheap approximate arm for 8B: per-row "key=value" lines (see C3b).

### C3b. Per-row key=value lines (cheap variant of C3, header repeated per row) [inference: my design, not a paper's method]
```
Hàng 1: Quốc gia=Việt Nam; Dân số=100.000.000; Diện tích=331.212
Hàng 2: Quốc gia=Lào; Dân số=7.500.000; Diện tích=236.800
Hàng 3: Quốc gia=Campuchia; Dân số=16.900.000; Diện tích=181.035
```
Motivation from the papers: Singha's JSON-wins-navigation finding (C1) and TabGR's per-cell binding (C3) both point to "repeat the header next to each value". No paper tested this exact string at <=10B. Not evidence, a hypothesis to run.

### C4. Table verbalization into prose before answering
C4a. LLM-generated description (TableMaster, ICLR 2026): the table (or its Table-of-Focus) is rewritten by an LM into sequential prose; e.g. for the toy table: "Việt Nam có dân số 100.000.000 người và diện tích 331.212 km2. Lào có ..." (constructed; the paper's real example is a Wikipedia congress table verbalized into paragraphs, Fig 8).
- Source: 2501.19378 Sec 4.3, Table 2 ablation, Fig 8, Table 13 [verified].
- Model: GPT-4o-mini (main). No open sub-10B ablation seen. English WikiTQ/TabFact/FetaQA, HiTab in appendix.
- Reported [verified, Table 2, WikiTQ]: full 78.13; w/o Verbalization 75.78 (-2.35); TabFact 90.12 -> 89.23 (-0.89). Text on page 9 says TabFact impact is "minimal (0.23% drop)", which conflicts with the table's -0.89; I trust the table number and flag the inconsistency. Case study Fig 8: verbalization fixed a distinct-person count (predicted 5 -> correct 4), i.e. helps entity-level counting. Also, w/o Table-of-Focus -1.73, w/o Structure Extraction -3.38 on WikiTQ.
- Cost: one extra LLM call over the sub-table plus the Table-of-Focus SQL/lookup stages; efficiency analysis says WikiTQ table area shrinks ~1:3 [verified]. Not zero-shot single-prompt.
- Merged cells: NOT handled ("we assume all tables are flat", Appx B) [verified]; the paper's own Fig 8 table has repeated rows for the same person.
- For Vietnamese/8B: unknown quality of Qwen3-8B verbalization; risk of hallucinated units (Appx B says verbalization quality is "not optimal") [verified]. Also risk on Yes/No and numeric-compute answers is unmeasured [inference].

C4b. Deterministic row-to-sentence templates (Min et al.): "The following sentences describe [title]. The [AC1] of the [MC] named [row key] is [v]. Its [AC2] is [v]. ..." Example: `Dân số của Quốc gia có tên Việt Nam là 100.000.000. Diện tích của nó là 331.212.`
- Source: 2402.12869 Appx Table 9 (Template 1 relational tables) and Table 2 [verified].
- Models: Llama2-7B/13B/70B, OPT, GPT-3.5; RAG/DSFT over a corpus; scores 0-5 by humans and GPT-4, not EM [verified]. Setting differs from zero-shot QA over a given table.
- Reported (Llama2-7B, RAG, human eval) [verified]: Markdown 3.72, Template 3.44, LLM-based 3.71; GPT-4 eval: Markdown 3.66, Template 3.06, LLM-based 3.59. So template was the worst of four for the 7B reader in RAG. In DSFT Llama2-7B human eval Markdown 2.82 = Template 2.82. RSD (score spread across methods) 2.8-9.0% human, 4.8-16% GPT-4 [verified].
- Length: Table 4 avg generated text length per table: Markdown 998, Template 1259 (+26%), LLM-based 897 (units as printed, unspecified) [verified].
- Verdict: a small negative signal AGAINST template sentences for a 7B reader; not a strong one because of the RAG setting. Do not prioritise.

### C5. Content-aware orientation check + transposition (NORM, Liu et al.)
Method: decide, from the CONTENT of the first row vs the first column, which is the semantic heading; if the first column is, transpose (done by code, not by the LLM) so headers are on top; optionally re-sort rows (dropped in their final run because it changes row-index questions).
Serialization example (stub table, toy): input `Chỉ số | 2019 | 2020 / Dân số | 96 | 97 / Diện tích | 331 | 331` -> after transpose `Năm | Dân số | Diện tích / 2019 | 96 | 331 / 2020 | 97 | 331`.
- Source: 2312.16702 Sec 4.2-4.3, Tables 1-3 [verified].
- Model: GPT-3.5 only, WikiTQ 837 items x 4 variants, zero-shot [verified].
- Reported [verified]: Direct Prompting accuracy original 59.50; transposed 51.14; +NORM on transposed 58.30; on ORIGINAL tables NORM changes 59.50 -> 58.66 (-0.84 abs, reported -1.41% relative), i.e. no gain on normal-orientation tables. Row-shuffled 52.21 -> 58.66. LLM as transposer is unreliable (53.68% accuracy) and as detector fails on transposed tables (32.54%) but a content-aware determinator gets 97.39% / 94.77% [verified].
- Tokens: about 1.0x (only layout changes) [inference].
- Merged cells: not addressed.
- Relevance: consistent with the already-known AIT-QA transposition finding, but this paper adds an honest null: the benefit exists only when the table is oriented "wrong". For Open-ViTabQA only the ~57 stub-column tables are candidates [inference from the project's own shortlist]. Expect zero change on the other 272 tables.

### C6. Deterministic value normalization + explicit row_number column (NormTab / TabSQLify preprocessing)
Steps described [verified]: strip thousand separators (`360,000` -> `360000`), unify dates to YYYY-MM-DD, normalize N/A and blanks to NULL, split ranges like `2010/11` into two columns, drop trailing "total" rows (NormTab structure normalization also detects transposition, 97.0% detection accuracy). Both papers' prompts add a `row_number` column (0-based) and use `col | col` pipe rows [verified from NormTab Fig 1/2 and TabSQLify Fig 3].
Serialization on toy table (Vietnamese numbers use `.` thousands and `,` decimals; the paper never tested this):
```
row_number | Quốc gia | Dân số | Diện tích
0 | Việt Nam | 100000000 | 331212
1 | Lào | 7500000 | 236800
2 | Campuchia | 16900000 | 181035
```
- Sources: 2406.17961 Sec 3.1, Table 4/7; 2404.10150 Sec 3.1, Sec 4.2.
- Models: gpt-3.5-turbo (+ gemini-1.5-flash, gpt-4-turbo in NormTab Table 3) [verified]. Their downstream is SQL generation, so the gain is not a text-reading gain. NormTab WikiTQ 51.30 (SQL original) -> 61.20 (NormTab targeted + SQL), i.e. +9.9; tables improved on 67%, unchanged 24%, worse 9% [verified Table 6/7]. NormTab+TabSQLify 64.7 -> 68.63 [verified Table 5]. No ablation of `row_number` alone.
- Tokens: number normalization shortens digit strings (e.g. `100.000.000` -> `100000000`); `row_number` adds ~2-3 tokens/row [inference, unmeasured].
- Merged cells: no.
- Relevance [inference]: Open-ViTabQA answers are often computed (sum/count/compare). Localized separator normalization (`.`/`,`) is a plausible cheap intervention for a Vietnamese-locale number parsing failure, but NO paper here shows it helps text-reading LLMs, and Vietnamese answers may need the original surface form in the output. Treat as a hypothesis with a measurable check (does normalization change EM on numeric-answer questions only?).

### C7. Query-independent canonical table (QUIETT) - multi-agent only
Adds derived columns (parsed dates, numeric year fields, term_duration), canonical labels, stable row id, and `keep_raw_snapshot` columns; executed by generated pandas code once per table.
- Source: 2602.20017 Sec 2, Sec 5, Tables 4-5, Appx A/B [verified].
- Models: Qwen3-80B, DeepSeek-V3.1, Gemini-2.0/2.5, GPT-OSS-120B. Table 5: Qwen3 transforming, QA by LLaMA/Mistral (sizes not stated in fetched text): WikiTQ 53.67/63.33, HiTab 46.22/51.30 [verified numbers; model sizes unspecified].
- Reported (Table 4, F1, Qwen3-80B column vs CoT on raw table): WikiTQ 58.95 -> 64.20; NQ-Table 61.34 -> 72.60; HiTab 72.97 -> 81.22 [verified]. CAVEAT: the QUIETT row is "QA using the pipeline"; the paper's Fig 2 shows CoT+SQL execution over the transformed table, so it is not a clean representation-only ablation, and CoT+SQL alone on raw is far lower (WikiTQ 51.55). Wins/no-change/loss by table: hierarchical 57/36/7 percent [verified].
- Cost: exactly 3 LLM calls per table for preprocessing, amortized across questions [verified, Appx B].
- Merged cells: hierarchical layouts named as a motivation; operators include `fillna_dynamic` (forward fill) and `combine_columns`; no explicit merged-cell algorithm described [verified].
- Verdict: not a single-prompt representation; consider only as an offline per-table agent. 329 tables x 3 calls is cheap in count, but code execution over Vietnamese text/dates is an extra failure surface [inference].

## 4. What I would rank (evidence-weighted, honest)

1. C3b (per-row key=value / repeated header) as the ONE new text-only arm worth running, because both real signals (Singha JSON navigation +5.9 to +22.7 over CSV/Markdown; TabGR explicit binding lowers structural errors 19.8 -> 14.4) point at "bind header to value locally". Both signals are at GPT-3 / 70B, not at Qwen3-8B; expected gain at 8B is unknown, likely within TABVERSE's 1-3 pp band [inference]. Token cost likely >1.3x pipe [inference].
2. C1 JSON-by-row-index as the comparison arm for #1 (it is the published version of the same idea).
3. C6 numeric normalization as a cheap targeted check on numeric questions.
4. C5 only for the stub-column tables; the paper's own data says no gain elsewhere.
5. C4a/C7 only as an offline multi-call agent, with the flat-table caveat.
Not recommended: C4b row-to-sentence templates (only negative 7B evidence), Markdown-as-improvement (Singha says worst; TabGR says mid-pack; TABVERSE says ~tie).

## 5. Limits of this search
- alphaXiv discovery is semantic and surfaced few 2023-2025 format-comparison papers; several known ones (e.g. Tables-as-Texts-or-Images 2402.12424, Sui et al. follow-ups, Chain-of-Table, Dater) were not opened by me; Chain-of-Table and Dater appear only as baselines inside papers I did read, and I cite no claim from them directly.
- I could not open TabGR Appx A (prompt text), so the exact triple prompt syntax is reconstructed.
- No Vietnamese or Qwen3-8B format ablation exists in what I read; everything above must be re-measured on Open-ViTabQA with McNemar on paired questions.
