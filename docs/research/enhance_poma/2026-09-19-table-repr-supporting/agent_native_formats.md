# Native table input formats of open-weight LLMs, and tokenizer cost (for zero-shot Open-ViTabQA, Qwen3-8B)

Date checked: 2026-09-19. Tags: [verified from source] = read in the paper text / model card / repo raw file this session; [measured] = I ran the local cached tokenizer; [inference] = my reasoning, no source states it.
All fetched text was treated as data. Repo not modified. No API calls made. Local tokenizers were used offline (cached files only, no weights).

## Headline finding
TableLlama's HiTab prompt (primary source: arXiv 2311.09206 appendix) duplicates a merged cell into every spanned column, e.g. `[SEP] | department of defense | department of defense | department of defense | ...`. This is published precedent that the project's Flatten V1 merge handling (duplicate into each spanned position) matches what a table specialist was trained on [verified from source]. No source shows a zero-shot advantage for any "native" format for Qwen3/SeaLLM/SEA-LION [verified absence in sources checked].

---------------------------------------------------------------------------------------------------

## 1. Sources checked and verdict

| Source | Opened? | What it gives | Verdict |
|---|---|---|---|
| TableGPT2 paper, arXiv 2411.02059 (preprint; 7B and 72B, Qwen2.5-based; CPT 86B tokens) + HF card `tablegpt/TableGPT2-7B` (raw README) + `tablegpt-agent` repo | yes | Training used MANY serializations (html, xml, df.markdown(), df.to_string(), json, custom; >20 table-info combinations). Released model card documents ONE inference format: `df.head(5).to_string(index=False)` inside a code-generation prompt | Best-documented "native" format, but it is a code-gen / pandas prompt, not a short-answer table prompt |
| TableLLM, arXiv 2403.19318 (CodeLlama-7B/13B) + HF card RUCKBReasoning/TableLLM-13b | yes | Spreadsheet scenario: CSV header + first rows, model writes Python. Document scenario: table as CSV inside a fenced block with `[Table Text]` description | CSV native; both prompt templates are verbatim on the card |
| StructLM, arXiv 2402.16671 (COLM 2024; 7B/13B/34B, Llama2/CodeLlama base) | yes (full text) | UnifiedSKG-style linearization `col : | h1 | h2 row 1 : | a | b ...` inside Llama-2 `[INST] <<SYS>>` template | Native = `col :/row i :` |
| TableLlama / TableInstruct, arXiv 2311.09206 (Llama-2-7B + LongLoRA, 2.6M instances) + HF dataset card `osunlp/TableInstruct` | yes | `[TLE] caption... [TAB] col: | h | h [SEP] row 1: | ... [SEP]` inside Alpaca template. Hierarchical/merged headers are DUPLICATED per spanned cell in the HiTab prompt | Native = `[TAB]`/`[SEP]`; duplication of merged cells is exactly what the project's Flatten V1 does |
| TableBench, arXiv 2408.09174 (AAAI 2025 header) + HF dataset `Multilingual-Multimodal-NLP/TableBench` (first ~3.5 KB of TableBench_DP.jsonl) | yes | Prompt: "Read the table below in JSON format: [TABLE] {'columns': [...], 'data': [[...]]}" then question. Evaluates 30+ models 7B-110B incl. Qwen1.5/Qwen2, and TableLLM-finetunes (7-8B) | Native (evaluation) = JSON columns/data, python-repr style |
| Table-R1, arXiv 2505.23621 (EMNLP 2025 main per ACL Anthology URL from search; Qwen2.5-7B backbones, SFT and RLVR "Zero") | yes (PDF text + GitHub repo + HF eval dataset rows) | Prompt template appendix: `Table Title: {table_title}` / `Table Content: {table_repr (markdown / html)}` / `Question:` + JSON answer format. Mapping of dataset -> markdown or html NOT stated in the paper text I extracted. Follow-up: GitHub `Table-R1/Table-R1` only downloads prebuilt HF datasets (data/table-r1-eval.py = `load_dataset('Table-R1/Table-R1-Eval-Dataset')`), so I sampled the HF datasets-server: the first 4000 rows (all data_source = WTQ, of 50,863 total) render the table as MARKDOWN with a `| --- |` separator row and zero `<table` HTML [verified from dataset rows]. Rows for HiTab/other sources were not reachable (HTTP 429), so their markup remains unverified | Markdown for WTQ (verified, 4000 rows); other datasets unverified |
| Qwen2.5 technical report, arXiv 2412.15115 | yes (grep) | States Qwen2.5 has "better support for structured input and output (e.g., tables and JSON)" and a "structured data understanding" SFT set: tabular QA, fact verification, error correction, structural understanding; format NOT stated | No format disclosed |
| Qwen3 technical report, arXiv 2505.09388 | yes (grep "table/markdown/tabular/structured data") | Only architecture/benchmark "Table N" hits. No statement about table training data or table format | Nothing usable. Absence of evidence, not evidence of absence |
| SeaLLMs-v3, arXiv 2407.19672 + HF card SeaLLMs-v3-7B-Chat | yes | Built on Qwen2 (7B). SFT data includes "table-related tasks" (one phrase, no format, no share). Card has no table text | Format unknown |
| SEA-LION cards (raw READMEs of Llama-SEA-LION-v3-8B-IT, Gemma-SEA-LION-v3-9B-IT, Apertus-SEA-LION-v4-8B-IT; a fetch of Qwen-SEA-LION-v4-8B-VL returned nothing, so not checked) | yes (grep table/tabular/markdown/json) | No table-related statement | Format unknown |
| Llama / Mistral / Gemma model cards | NOT checked in depth | -- | Not found. Only inferred from TableBench/ToRR that they were evaluated with generic prompts |
| Table-GPT, arXiv 2310.09263 (fine-tuned GPT-3.5, size not public) | yes | Markdown table format used for tuning; format ablation Markdown/CSV/JSON (Table 5) | see section 3 |
| ToRR "Mighty ToRR", arXiv 2502.19412 | yes (grep + sections 3.3, 5) | 14 zero-shot LLMs, 7 serializers incl. "Indexed Row Major" (`col : Name | Age | Sex row 1 : ...`), HTML, JSON, CSV, Markdown, DataFrame | see section 3 |
| Deng and Mihalcea, "Towards Better Understanding Table Instruction Tuning", arXiv 2501.14717 | yes (appendix grep) | Documents the eval-time table formats used for tuned models (Markdown for FeTaQA/HiTab/TATQA/ToTTo from Zhang et al. 2024a; `|` for TabMWP; HTML for WikiTQ/InfoTabs) | Format varies per dataset; no matched/mismatched ablation |

Name collisions to avoid: two different papers are called "Table-R1" (2505.23621 inference-time scaling, has Table-R1-Zero, used here; 2505.12415 region-based RL, not used), and two different things are called "TableLLM" (RUCKBReasoning CodeLlama models, 2403.19318; and the Qwen2/Llama3-finetuned baselines in TableBench, 2408.09174).

Not opened / could not verify: publication venues for Table-GPT, TableLlama, ToRR, Deng and Mihalcea; Table-R1 markup for datasets other than WTQ; whether TableGPT2's semantic encoder is present in the open weights (the card says text input in df.head() form). I did not open the browser pane (not needed).

---------------------------------------------------------------------------------------------------

## 2. Table: model -> native table format -> source

Model sizes / n are given where read. "Tuned on" means table data was in SFT; "eval" means benchmark harness format.

| Model (size, base) | Native / documented table format, example | Source |
|---|---|---|
| TableGPT2-7B / 72B (Qwen2.5; preprint) | Inference: `df.head(5).to_string(index=False)` wrapped in a prompt. Verbatim-style: `Given access to several pandas dataframes, write the Python code to answer the user's question.` `/*` `"{var_name}.head(5).to_string(index=False)" as follows:` `{df_info}` `*/` `Question: {user_question}`. Example rendered: a whitespace-aligned table, header line then rows. Training: randomised html / xml / df.markdown() / df.to_string() / json / custom, >20 combinations with schema + field descriptions + value enumerations [verified from source] | Paper section 5.3 "diverse table serialization input formats" https://arxiv.org/abs/2411.02059 ; card README raw https://huggingface.co/tablegpt/TableGPT2-7B/raw/main/README.md (line: "tabular data structured as text in the format of a df.head() result") |
| TableLLM-7B/13B (CodeLlama-7B/13B-Instruct; preprint) | Code path: `[INST]Below are the first few lines of a CSV file. You need to write a Python program to solve the provided question.` `Header and first few lines of CSV file:` `{csv_data}` `Question: {question}[/INST]`, csv_data e.g. `Sex,Length,Diameter,...` newline `M,0.455,0.365,...`. Text path: `### [Table Text]` `{table_descriptions}` `### [Table]` fenced ``` `{table_in_csv}` ``` `### [Question]` `{question}` `### [Solution]` [verified from source] | https://huggingface.co/RUCKBReasoning/TableLLM-13b/raw/main/README.md ; paper Fig. 15-16 https://arxiv.org/abs/2403.19318. Text-answer training used tables under 500 tokens (WikiTQ, FeTaQA, TAT-QA) |
| StructLM-7B/13B/34B (Llama2 / CodeLlama; COLM 2024) | `[INST] <<SYS>> You are an AI assistant that specializes in analyzing and reasoning over structured information... <</SYS>> {instruction} {input} [/INST]` where input holds the linearized table, e.g. `col : |3/31/2007 |3/31/2008 |3/31/2009 ... row 1 : abiomed inc |100 |96.19 ... row 2 : nasdaq composite index |100 |94.11 ...` (verbatim from paper Appendix E; note `|` glued to the following cell, no space before it) [verified from source] | https://arxiv.org/abs/2402.16671 Appendix D-E |
| TableLlama-7B (Llama-2-7B + LongLoRA, 8K ctx; 2.6M instances; preprint) | Alpaca template `### Instruction: ... ### Input: [TLE] The table caption is ... [TAB] col: | stat | player | team | total | [SEP] row 1: | Wins | Masaichi Kaneda | ... [SEP] row 2: ... ### Question: ... ### Response:`. HiTab (hierarchical) variant, verbatim: `[TAB] | agency | 2015 | 2016 | 2017 | 2018 | [SEP] | department of defense | department of defense | department of defense | ... [SEP] | rdt&e | 61513.5 | ...` (the merged "department of defense" cell is repeated in every spanned column) [verified from source] | https://arxiv.org/abs/2311.09206 Appendix; card https://huggingface.co/datasets/osunlp/TableInstruct |
| TableBench eval harness (used for 30+ models: Qwen1.5/2 7B-110B, Llama2/3/3.1, Mistral-7B, StructLM, TableLLM-FT) | `Read the table below in JSON format:` `[TABLE]` `{'columns': ['season', 'tropical lows', ...], 'data': [['1990 - 91', 10, 10, 7, 'marian'], ...]}` then `Let's get start!` `Question: ...`; DP/TCoT/SCoT/PoT variants. Verbatim from the first record of TableBench_DP.jsonl [verified from source]. Tables in benchmark average 16.7 rows x 6.7 cols [verified] | https://huggingface.co/datasets/Multilingual-Multimodal-NLP/TableBench ; paper https://arxiv.org/abs/2408.09174 |
| Table-R1-SFT / Table-R1-Zero (Qwen2.5-7B-Instruct and others; EMNLP 2025 main) | `Instruction: This is a short-answer table QA task. Answer the question based on the provided table.` `Table` `Table Title: {table_title}` `Table Content: {table_repr (markdown / html)}` `Question: {question}` `Answer Format: ... ```json {"answer": ["answer1", ...]} ```` [verified from source]. Which datasets use which markup: not stated in extracted text | https://arxiv.org/pdf/2505.23621 Appendix prompts |
| Table-GPT (fine-tuned GPT-3.5) | Markdown serialization; authors argue GPT "tends to generate tables in the Markdown format", "likely because GPT is pre-trained on lots of GitHub code" (their conjecture) [verified as their statement] | https://arxiv.org/abs/2310.09263 section 5.4 |
| Qwen2.5 (0.5B-72B) | "Structured Data Understanding" SFT set incl. tabular QA; formats not disclosed | https://arxiv.org/abs/2412.15115 |
| Qwen3 (incl. 8B) | Nothing stated about tables | https://arxiv.org/abs/2505.09388 |
| SeaLLMs-v3-7B-Chat (Qwen2) | "table-related tasks" in SFT; formats not disclosed | https://arxiv.org/abs/2407.19672 |
| SEA-LION v3/v4 8-9B | Nothing stated | HF cards |

Two observations across the table [inference, from the rows above]:
1. There is no single native format. Table specialists were trained on one of: CSV/pandas text (TableLLM, TableGPT2), `col:/row i:` (StructLM, TableLlama, Table-GPT-style markdown aside), JSON (TableBench harness), Markdown/HTML (Table-R1). The only model that deliberately randomised formats (TableGPT2) did so on purpose, which suggests its authors did not trust a single format.
2. Qwen3-8B (the project's main model) has no published native table format. Any "match the model's training format" argument for Qwen3 rests on guesswork; the only concrete Qwen-adjacent fact is that Table-R1 and TableBench harness (which include Qwen models) both use markdown/html or JSON, i.e. standard formats rather than `|`-joined-with-`<header>` tags.

---------------------------------------------------------------------------------------------------

## 3. Does matching the training format help (zero-shot, no finetune)?

Verdict: NO direct evidence found. No paper I opened runs a zero-shot instruct model (Qwen2.5/Qwen3/SeaLLM/SEA-LION) with a matched vs mismatched table format, because instruct models have no declared table training format. The nearby evidence is weak and mixed:

1. Table-GPT (GPT-3.5 fine-tuned on Markdown tables; size unknown; arXiv 2310.09263) [verified from source]: at test time Markdown 0.705 overall (seen 0.739 / unseen 0.663), CSV 0.687, JSON 0.672. "the Markdown format on average performs better than other formats, although the gap is not too significant". This is the only matched-vs-mismatched-ish result (train=Markdown), gap 1.8 to 3.3 points overall, unseen-task gap 0.1 (CSV) to 4.2 (JSON). No untuned-model control, so it cannot separate "training match" from "Markdown just works". Authors' explanation (pretraining on GitHub Markdown) is a conjecture.
2. ToRR (14 zero-shot LLMs incl. Llama-3.1-8B/70B/405B, Mistral-7B, Mixtral, Qwen2-72B, GPT-4o, Claude, Gemini, DeepSeek-V3; arXiv 2502.19412) [verified from source]: "no serializer consistently outperforms others"; per-model weak preferences, max difference 0.06 overall performance across serializers; format perturbations have no consistent effect; but single-format model rankings are unreliable. Implication: for a zero-shot instruct model, format changes move scores by a few points, and per-model best format is not predictable. n per dataset not extracted; preprint status unverified.
3. TableBench (arXiv 2408.09174) [verified from source]: StructLM shows "strong table understanding capabilities but exhibit weaker instruction-following" and the authors hypothesise ("may be attributed to") a mismatch between StructLM's tuning instruction format and theirs. StructLM-7B scores 17.06 / 25.21 / 8.30 (TCoT / SCoT / PoT overall) versus Qwen2-7B 22.77 / 22.26 / 0.60 on the same JSON-table prompts. This is about instruction/answer format brittleness of specialists, a hypothesis not an ablation, and it points to a RISK of specialised formats rather than a benefit.
4. StructLM's own Limitations paragraph [verified] warns its models may have "unnecessary specificity towards the conventions within our train set" and that formatting diversity should be increased. TableGPT2's >20 randomised formats is the corresponding mitigation [verified]. Both imply that matching brittle-specialist formats matters for the specialists themselves, not for a general instruct model.
5. Deng and Mihalcea [verified]: tuned models were evaluated per dataset with Markdown (FeTaQA, HiTab, TATQA, ToTTo), `|` (TabMWP) or HTML (WikiTQ, InfoTabs), with no ablation on format.

Bottom line for the project [inference]: because Qwen3-8B/SeaLLM/SEA-LION are general instruct models with undisclosed table data, "match native format" is not an evidence-backed lever. A format change is expected to move EM by a few points at most (ToRR's 0.06 ceiling per model, Table-GPT's ~2-3), and can be tested with a cheap 3-4 arm ablation on your 500-sample stratified run. The interaction with merged-cell handling and token cost is a more important design driver than "nativeness".

---------------------------------------------------------------------------------------------------

## 4. Tokenizer cost (measured locally, offline, no downloads)

Method: `AutoTokenizer.from_pretrained(..., local_files_only=True)` for cached Qwen/Qwen3-8B, SeaLLMs/SeaLLMs-v3-7B-Chat, aisingapore/Apertus-SEA-LION-v4-8B-IT, aisingapore/Llama-SEA-LION-v3-8B-IT; `add_special_tokens=False`, text only. Script: `scratchpad/tokcost.py` and `tok2.py`. Only a 3-row and a 12-row synthetic Vietnamese table; cost ratios are indicative, not dataset-wide. The dataset-level cost should be re-measured on the real 329 tables before committing.

Identity note [measured]: Qwen3-8B and SeaLLMs-v3-7B have byte-identical `vocab.json` and `merges.txt` (md5 equal), so all counts are identical. Apertus-SEA-LION-v4 is within about 2 tokens; Llama-SEA-LION-v3 uses a different (cheaper: about 0.65-0.7x of the Qwen count on this content) vocabulary.

### 4a. Vietnamese with diacritics on Qwen3 [measured]
- Sample 24-word Vietnamese question: 30 tokens (1.25 tokens/word) vs 19-word English question: 21 tokens (1.11 tokens/word). NFC and NFD give the same count (30) on Qwen3; on Apertus-SEA-LION-v4 NFD explodes 34 -> 106 and on Llama-SEA-LION-v3 30 -> 80 (so normalise to NFC before serialising for those models).
- Stripping diacritics INCREASES tokens (30 -> 38 on Qwen3): the tokenizer has learned Vietnamese diacritic forms; do not strip.
- Typical splits: `Việt Nam` -> `Vi`,`ệt`,` Nam` (3); `Quốc gia` -> `Qu`,`ốc`,` gia` (3); `Dân số` -> `D`,`ân`,` số` (3); `Thành phố Hồ Chí Minh` (6). Hyphenated transliterations are costly: `Cam-pu-chia` 5, `Xin-ga-po` 5.
- Whether a word begins with a space matters: `|Việt Nam|` = 5 tokens (`|`,`Vi`,`ệt`,` Nam`,`|`) but `| Việt Nam |` = 4 (`|`,` Việt`,` Nam`,` |`) because ` Việt` is a single token. So spaces around `|` are almost cost-neutral (net +0% tiny table, +6% 12-row table on Qwen3) and change first-word tokenisation.
- Numbers are the dominant fixed cost: digits are tokenised ONE PER TOKEN plus each separator (`98.186.856` = 10 tokens, `331.212` = 7), so 30-50% of a numeric table's tokens are independent of the delimiter choice.

### 4b. Delimiters and markup on Qwen3 [measured]
- `|` = 1 token; ` |` = 1; tab = 1 (fused with the next char: `a\tb` -> `a`,`\tb`); `,` = 1 (`,b` fused).
- Baseline tag ` <header>` = 3 tokens (` <`,`header`,`>`) per header cell; `**bold**` markers cost 2 per cell total; `[SEP]` = 3; `| --- | --- |` row = 5 tokens for 2 columns (about 2 per column) plus newline.
- HTML `<td>` = 2, `</td>` = 3, `<th>` = 2, `</th>` = 3, `<tr>` = 2, `</tr>` = 3: 5 tokens of overhead per cell, ` rowspan="2"` = 4 more.
- JSON: repeated keys cost every row (`"Quốc gia": "Việt Nam"` = 10 tokens vs 3 for the value+space); `ensure_ascii=True` (Python default) turns diacritics into `\uXXXX` escapes and costs about 2.4-2.6x baseline, so NEVER json.dumps a Vietnamese table without `ensure_ascii=False`.

### 4c. Cost vs project baseline (Flatten V1: `Header <header>|...` then `a|b|c` rows), Qwen3-8B [measured]

| Format | 3x3 table (baseline 84 tok) | 12-row table (baseline 316 tok) |
|---|---|---|
| Flatten V1 (pipe, ` <header>` tags) | 1.00x | 1.00x |
| pipe, no header tag | 0.93x | 0.98x |
| pipe with spaces around `|` | 1.00x | 1.06x |
| TSV | 0.90x | 0.97x |
| CSV | 0.92x | 0.98x |
| df.to_string(index=False) (TableGPT2) | 0.98x | (not run) |
| Markdown with `| --- |` row | 1.11x | 1.11x |
| Markdown without separator row | 1.02x | 1.09x |
| JSON `{'columns':...,'data':...}` (TableBench) | 1.17x | 1.13x |
| StructLM `col : | ... row 1 : | ...` | 1.14x | 1.21x |
| TableLlama `[TAB] col: ... [SEP] row 1: ...` | 1.33x | 1.38x |
| key:value lines | 1.26x | 1.46x |
| HTML `<th>/<td>` | 1.74x | 1.65x |
| JSON list of records (ensure_ascii=False) | 1.46x | 1.64x |
| JSON list of records (ascii-escaped) | 2.42x | 2.62x |

Same ordering on SeaLLMs-v3 (identical vocab), Apertus-SEA-LION-v4, and Llama-SEA-LION-v3 (HTML 2.0x, JSON records 2.0x, StructLM 1.3x there).

The current Flatten V1 is already near the cheap end. Its only avoidable overhead is the 3-token `<header>` tag per header cell.

Open-ViTabQA relevance [inference from measurements]: cost matters little except for HTML/JSON-records; 8B-context is not the binding constraint for tables of this size (the project's measured table sizes are in structure-encoding-shortlist section 0, not re-derived here).

---------------------------------------------------------------------------------------------------

## 5. Candidate representations implied by this evidence

Tiny example table (3 columns, plain, no merges) and one merged-header variant. Token counts [measured] on Qwen3-8B vocabulary; ratios vs Flatten V1 on the same table.

Plain table used (cell values are illustrative placeholders I typed for tokenizer tests, not sourced statistics): header `Quốc gia | Dân số | Diện tích`; rows `Việt Nam | 98.186.856 | 331.212`, `Thái Lan | 71.801.279 | 513.120`, `Lào | 7.529.475 | 236.800`.

Merged-header table used (for merge behaviour): `Quốc gia` spans 2 header rows, `Dân số` spans 2 columns over `2019`,`2020`; data rows `Việt Nam | 96.208.984 | 97.338.579`, `Thái Lan | 69.625.582 | 69.799.978`. Flatten V1 (baseline) = 89 tokens.

### C0. Baseline, Flatten V1 (control) [measured: 84 tokens plain / 89 merged]
```
Quốc gia <header>|Dân số <header>|Diện tích <header>
Việt Nam|98.186.856|331.212
Thái Lan|71.801.279|513.120
Lào|7.529.475|236.800
```
Merged: duplicates into every spanned position:
```
Quốc gia <header>|Dân số <header>|Dân số <header>
Quốc gia <header>|2019 <header>|2020 <header>
Việt Nam|96.208.984|97.338.579
```
Native to nobody [verified: no model card uses `<header>` tags; the closest precedent is TableLlama duplicating merged cells]. Keep as control.

### C1. Markdown pipe table (Table-R1 "markdown", Table-GPT, ToRR) [measured 1.11x tokens]
```
| Quốc gia | Dân số | Diện tích |
| --- | --- | --- |
| Việt Nam | 98.186.856 | 331.212 |
| Thái Lan | 71.801.279 | 513.120 |
| Lào | 7.529.475 | 236.800 |
```
Merged: no native span syntax; use the same duplication (`| Quốc gia | Dân số | Dân số |` then `| Quốc gia | 2019 | 2020 |`), 1.02x on the merged example, but markdown's single `---` separator implies exactly one header row, so a 2-row header sits awkwardly in the body [inference]. Evidence for: Table-R1 template lists it, Table-GPT reports it best of 3 (gap 2-3 pts on a GPT-3.5 tune), ToRR includes it (no consistent winner). Cost: 1.09-1.11x.

### C2. TableBench-style JSON columns/data (Qwen-family harness format) [measured 1.17x plain / 1.13x on 12 rows]
```
{'columns': ['Quốc gia', 'Dân số', 'Diện tích'], 'data': [['Việt Nam', '98.186.856', '331.212'], ['Thái Lan', '71.801.279', '513.120'], ['Lào', '7.529.475', '236.800']]}
```
Merged: cannot represent 2 header rows; must collapse headers to a single path label (`Dân số 2019`, `Dân số 2020`, `Quốc gia`) and lose the hierarchy, or nest under a header path [inference]. Evidence: TableBench used it for 30+ models incl. Qwen; strict JSON header vs data mapping avoids column misalignment at 1.13-1.17x. Do not use keys-per-row JSON (1.46-1.64x, 2.4x with ascii escaping).

### C3. StructLM/TableLlama-style `col : | ... row i : | ...` [measured 1.14x (StructLM) to 1.33x (TableLlama with [SEP])]
```
col : | Quốc gia | Dân số | Diện tích row 1 : | Việt Nam | 98.186.856 | 331.212 row 2 : | Thái Lan | 71.801.279 | 513.120 row 3 : | Lào | 7.529.475 | 236.800
```
(row-per-line variant: put each `row i :` on its own line.) Merged: duplicate per spanned cell, as TableLlama does in its HiTab prompt [verified from source]. Rationale: it is the ONLY format with explicit `col`/`row N` anchors, which helps rank/position questions ("row 3") [inference]; nativeness benefits only StructLM/TableLlama, not Qwen3 [verified: no such training disclosed]. Include as a cheap ablation, not as the expected winner.

### C4. df.to_string(index=False) (TableGPT2 documented) [measured 0.98x plain]
```
Quốc gia     Dân số Diện tích
Việt Nam 98.186.856   331.212
Thái Lan 71.801.279   513.120
     Lào  7.529.475   236.800
```
(actual pandas output from a local run; columns right-aligned with space padding). Merged: no support; requires collapsed headers. Poorly suited to multi-word Vietnamese cells (whitespace is an ambiguous delimiter), and TableGPT2's own prompt is a pandas-code prompt [verified], so I would not use it for a zero-shot short-answer task; listed for completeness. Cost-neutral.

### C5. HTML with rowspan/colspan (retains merges natively; WikiTQ/InfoTabs eval format in Deng and Mihalcea; Table-R1 "html") [measured 1.5x-1.74x]
```
<table><tr><th>Quốc gia</th><th>Dân số</th><th>Diện tích</th></tr><tr><td>Việt Nam</td><td>98.186.856</td><td>331.212</td></tr>...</table>
```
Merged, exact: `<th rowspan="2">Quốc gia</th><th colspan="2">Dân số</th>` then `<th>2019</th><th>2020</th>`: 136 tokens vs 89 (1.53x). Only format here that carries the source structure without duplication and without inventing anything; cost premium is the tag overhead (5 tokens/cell) [measured]. The evidence that models read HTML tables well comes from other agents' comparison papers, not this slice.

### C6. Header-path flatten + plain pipe (no tag) [measured 0.84x on merged example, 0.93x plain] [inference for accuracy effect]
```
Quốc gia|Dân số / 2019|Dân số / 2020
Việt Nam|96.208.984|97.338.579
Thái Lan|69.625.582|69.799.978
```
Merged: parent labels folded into leaf header (`Dân số / 2019`), removes both the `<header>` tag cost and the duplicate header row. No source I opened validates this for small LMs directly (structure-encoding-shortlist.md already ranks span-faithful/path variants; this slice contributes only the cost figure and the note that the ` / ` and ` | ` splits are cheap on Qwen3). Rank/edge cases (rowspan in body cells) not handled.

Expected tokens vs baseline (Qwen3, 12-row plain table): TSV/CSV 0.97-0.98x [measured]; C6 about 0.98x on plain tables [inference from the no-tag pipe_plain run; C6 itself was measured only on the 3x3 (0.93x) and the merged example (0.84x)]; C1 1.11x; C2 1.13x; C3 1.21x (StructLM) to 1.38x (TableLlama); C5 1.65x.

### Recommendation for the ablation, given the evidence [inference]
- Because no source shows format matching helps a general instruct model and the format effect size is a few points (ToRR max 0.06, Table-GPT 2-3 points), run a small ablation on the existing 500-sample run: C0 (control), C1 Markdown, C5 HTML span-faithful (semantic winner if merges matter), C3 col/row-anchor. C2/C4 are lower priority. C6 is the cheapest variant to A/B against C0 to isolate the `<header>` tag cost.
- Normalise all Vietnamese to NFC before prompting (matters for SEA-LION vocabularies, no effect on Qwen3).
- Never serialize Vietnamese JSON with ensure_ascii=True.
- If context limits or cost matter, avoid HTML on the largest tables; use spans only where the table actually has merges (Open-ViTabQA merges are frequent but not universal, see shortlist section 0).

---------------------------------------------------------------------------------------------------

## 6. Caveats
- Nearly all specialist models are 7-13B Llama/CodeLlama/Qwen2.5 fine-tunes evaluated on English (or Chinese for TableGPT2) tables; no Vietnamese evidence anywhere in this slice.
- Table-GPT numbers are for a fine-tuned proprietary GPT-3.5 and are 2023 results; do not transfer the effect size to Qwen3-8B.
- ToRR's "no serializer wins" is aggregated over models and datasets; the model-specific effect (up to 0.06) is not broken down by Qwen3 (Qwen3 not evaluated; Qwen2-72B is).
- Token-cost figures come from two synthetic tables; digit-per-token behaviour makes real numeric tables less sensitive to delimiter choice than my ratios suggest.
- `Sea-Lion` in the task text was ambiguous; I measured Apertus-SEA-LION-v4-8B and Llama-SEA-LION-v3-8B; other SEA-LION cached models (Gemma v3-9B, Gemma v4.5-E2B) were not measured.
