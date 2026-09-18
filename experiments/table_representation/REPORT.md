# Table representation for LLM Table QA

**Crawl date:** 2026-09-17  
**Scope:** How a table should be serialized before it is given to an LLM, mapped onto POMA / Open-ViTabQA.  
**Status:** Literature survey plus encoding sandbox. No model scores yet.

POMA currently feeds every specialist the Open-ViTabQA **Flatten V1** string: a rectangular grid after `rowspan`/`colspan` expansion, one logical row per line, cells joined by `|`, header cells marked with a trailing `<header>` tag. The goal of this folder is to treat that string as one method among several, not as a given.

## 1. What we crawled

Papers were opened in a browser on arXiv, the TABVERSE project page, Semantic Scholar, and ACL Anthology, then cross-checked against HTML/PDF text. Screenshots of the main pages are in `screenshots/`. The bibliography with URLs is in `sources.md`.

The crawl concentrated on **prompt serialization** (HTML, Markdown, CSV, JSON, XML, LaTeX, key-value, TAPEX linearization, spreadsheet cell addresses) rather than on new table-specific transformer architectures, because POMA does not fine-tune the backbone.

Two results were treated as primary evidence for format ranking:

1. **Table Meets LLM** (Sui et al., WSDM 2024, arXiv:2305.13062): same Wikipedia-derived tables, seven structural tasks, GPT-3.5 and a GPT-4 subset.
2. **TABVERSE** (Ahsan et al., arXiv:2606.09578): same table *content* rendered as HTML, Markdown, LaTeX, and images; 700 QA pairs; 17 models.

A third line of work, **TQA-Bench** (OpenReview `hxEHr5gJBY`), reports the opposite ranking for *multi-table* relational databases: Markdown beats HTML, and JSON is weakest. That contrast is the main reason not to crown a single format for POMA without a local ablation.

## 2. POMA's current representation

From `preprocessing/representation.py` and `paper/jit-article.tex`:

1. Parse Wikipedia HTML with BeautifulSoup.
2. Expand merged cells onto a rectangular grid (duplicate the source value).
3. Mark `<th>` cells (and majority-header rows) as headers.
4. Emit one line per logical row: `cell <header>|cell <header>|value`.

That is a **row-wise X-separated linearization with an explicit header tag**. It is closest to the **NL + Sep** baseline in Table Meets LLM and to TAPEX's `col: … | … row i: …` family, except Flatten V1 keeps header rows *in place* instead of lifting them into a `col:` prefix, and it repeats merged values instead of emitting `colspan`.

Open-ViTabQA tables are not clean relational frames. The dataset tags `contain_merged_header` and `contain_merged_value`. Hierarchical Wikipedia tables are exactly the case where Markdown and CSV lose structure: they have no `colspan`/`rowspan`. HTML and header-path encodings keep that scope.

## 3. A working taxonomy

Wu, Ritter, and Xu (arXiv:2508.00217) split table input into four families. Lu et al. (arXiv:2402.05121) use a similar split. The encodings in this folder sit in the first family.

| Family | Idea | Typical methods here | Fit for POMA |
|---|---|---|---|
| **Serialization** | Linearize the 2-D grid as text | Flatten V1, Markdown, HTML, CSV, JSON, XML, LaTeX, TAPEX, Markdown-KV | Direct drop-in for current prompts |
| **Schema / program** | Show CREATE TABLE or a DataFrame, query with SQL/Python | Binder, StructGPT, Chain-of-Table operations | Weak on irregular Wikipedia tables; useful later as a specialist |
| **Specialized encoder** | Row/column/tree embeddings inside the model | TAPAS, TaBERT, TUTA, TableFormer | Out of scope: POMA does not train a table encoder |
| **Image / layout** | Render the table and use a VLM | TABVERSE image pipeline, Table-LLaVA | Out of scope for the current text-only pipeline |

Inside serialization there is a second split that matters for Open-ViTabQA:

- **Grid formats** (Markdown, CSV, HTML, LaTeX, Flatten V1) keep row/column alignment.
- **Record formats** (JSON objects, Markdown-KV, NL sentences) repeat the header next to every value.
- **Address formats** (SpreadsheetLLM A1, inverted index, JSON triples, header path) name each cell by coordinates or header path.

Record and address formats cost more tokens but reduce “which column is this value in?” errors on wide or hierarchical tables.

## 4. Paper summaries

Each summary is limited to **how the table is represented**, not the rest of the system.

### 4.1 Table Meets LLM (Sui et al., WSDM 2024)

**arXiv:** [2305.13062](https://arxiv.org/html/2305.13062)  
**Question:** do GPT-3.5/GPT-4 actually parse table *structure*, and which input format helps?

They build SUC: table partition, size detection, merged-cell detection, cell lookup, reverse lookup, column retrieval, row retrieval. Formats compared: **NL + Sep**, **Markdown**, **JSON**, **XML**, **HTML**. They also ablate format explanation, partition marks, role prompts, and whether the question comes before or after the table.

**Verified numbers (Table 2, Acc column, GPT-3.5 / text-davinci-003):**

| Format | Partition | Cell lookup | Reverse lookup | Column retrieval | Row retrieval | Size detection | Merged cell |
|---|---:|---:|---:|---:|---:|---:|---:|
| NL + Sep | 93.00 | 39.67 | 52.00 | 60.67 | 31.00 | 42.00 | 71.33 |
| Markdown | 92.33 | 43.33 | 51.00 | 35.33 | 42.33 | 40.67 | 78.00 |
| JSON | 94.00 | 42.67 | 54.33 | 54.33 | 29.00 | 42.67 | 73.33 |
| XML | 96.00 | 43.33 | 55.00 | 41.33 | 41.00 | 43.67 | 75.00 |
| HTML | **96.67** | **44.00** | 47.33 | **63.33** | 42.00 | **67.00** | 76.67 |

HTML is the only format that is clearly good at **size detection** (67% vs ~42%). That matters for POMA: Flatten V1 does not tell the model how many rows/columns exist.

On downstream table tasks (their Table 5, 1-shot, GPT-3.5):

| Format | TabFact | HybridQA | SQA | FEVEROUS | ToTTo BLEU-4 |
|---|---:|---:|---:|---:|---:|
| NL + Sep | 70.26 | 45.02 | 70.41 | 75.15 | **12.70** |
| Markdown | 68.40 | 45.88 | 66.59 | 71.88 | 8.57 |
| JSON | 68.04 | 42.40 | 70.39 | 73.84 | 8.82 |
| XML | 70.00 | 47.20 | 70.74 | 73.14 | 8.82 |
| HTML | **71.33** | **47.29** | **71.31** | **75.20** | 12.30 |

Their recommended recipe is **HTML + format explanation + role prompt + question after the table**. Self-augmented prompting (ask the model to name critical values/ranges first) added about +2–3 points on TabFact/HybridQA/SQA.

**POMA mapping:** Flatten V1 is NL + Sep plus `<header>`. The paper's closest upgrade path is (a) HTML, or (b) keep Flatten V1 but add a one-line format explanation and table size.

### 4.2 TABVERSE (Ahsan et al., 2026)

**Project page:** [mbzuai-nlp.github.io/TABVERSE](https://mbzuai-nlp.github.io/TABVERSE/)  
**arXiv:** [2606.09578](https://arxiv.org/abs/2606.09578)

Same table content in HTML, Markdown, LaTeX, plus aligned PNG renders. 700 balanced QA pairs from FEVEROUS, HybridQA, TabFact, SQA, WikiTableQuestions. Tasks: QA, SUC (10 probes), structure reconstruction.

Findings taken from the project page (not from a numeric leaderboard table):

- Representation **does** move scores; content-held-fixed is the point of the benchmark.
- **HTML is the safest text format** across QA and SUC.
- Structured text usually beats rendered images, but the gap is model-dependent (Gemma-3 gains +7 to +10 pp from text; some VLMs prefer images).
- Row retrieval (5.0% mean) and cell lookup (9.9%) stay hard in every pipeline.
- LaTeX is a reconstruction bottleneck (usability can drop to 0.77 even for strong models).

**POMA mapping:** a fair POMA ablation should hold the table *content* fixed and only change the serializer, which is exactly what `encodings.py` does. Do not mix Flatten V1 on one subset with Markdown on another.

### 4.3 Singha et al., 2023 (arXiv:2310.10358)

**Title:** *Tabular Representation, Noisy Operators, and Impacts on Table Structure Understanding Tasks in LLMs*

They prompt GPT-3 with eight formats, including HTML, JSON, Markdown, DataMatrix, and **DFLoader** (the pandas `DataFrame` string). They then apply eight noise operators: shuffled/renamed headers, merged columns, transpose, and so on.

Takeaways for POMA:

- Format ranking is **task-specific**. DFLoader/JSON can win fact-finding; HTML can win navigation.
- Merged cells and uninformative sequential headers (exactly Open-ViTabQA noise) hurt some formats more than others. JSON row lookup dropped after a column-merge operator.
- A POMA comparison should include at least one **messy-table slice** (`contain_merged_header` / `contain_merged_value`), not only `normal` tables.

### 4.4 SpreadsheetLLM (Tian, Zhao, Dong et al., 2024)

**arXiv:** [2407.09025](https://arxiv.org/abs/2407.09025)

Vanilla encoding is Markdown-like but every cell carries an **A1 address** (and optionally format). That explodes tokens. **SheetCompressor** then:

1. Keeps heterogeneous “structural anchor” rows/columns and drops distant homogeneous ones.
2. Inverts the grid to `{value: [addresses]}` JSON, dropping empty cells.
3. Aggregates adjacent numeric cells by number-format / type.

They report ~25× compression (96% fewer tokens) and +25.6 pp on GPT-4 spreadsheet table detection versus vanilla encoding. Downstream they use **Chain of Spreadsheet**: detect table region, then QA over the cropped region.

**POMA mapping:** Open-ViTabQA tables are single Wikipedia tables, not huge multi-table sheets, so full SheetCompressor is probably overkill. Two cheap pieces are still useful:

- emit A1 addresses on large tables (`spreadsheet_a1`);
- inverted index for sparse/wide tables (`inverted_index`).

Do not drop “homogeneous” rows on Open-ViTabQA: those rows are often the answer.

### 4.5 TAPEX / OmniTab linearization

TAPEX (Liu et al., ICLR 2022) and OmniTab (Jiang et al., NAACL 2022) flatten a table as:

```text
col: header1 | header2 | header3 row 1: v1 | v2 | v3 row 2: ...
```

This is the most cited *named* linearization in table pretraining. Flatten V1 is similar but keeps header rows in the body with `<header>` tags, which is better when there are **multiple header rows**. TAPEX assumes a single header row. For Open-ViTabQA merged headers, TAPEX needs composed column names (`2024 / Q1`), which `tapex` in this folder does.

### 4.6 TAPAS, TaBERT, TUTA, TableFormer

These are **model** representations, not prompt strings.

- **TAPAS** (Herzig et al., ACL 2020): flatten tokens, then add row-id, column-id, and rank embeddings; predict cell selection + aggregation.
- **TaBERT** (Yin et al., ACL 2020): per-row sequence `column | type | value`, plus vertical attention over a content snapshot of relevant rows.
- **TUTA** (Wang et al., 2020): tree coordinates for hierarchical top/left headers. Directly relevant to Open-ViTabQA merged headers, but it requires a custom encoder.
- **TableFormer** (Yang et al., ACL 2022): drop absolute row/column ids; use relation biases (same row, same column, cell-to-header). Motivates testing order perturbations.

POMA cannot add these embeddings without training. The prompt analogue of TUTA is **header_path**: spell out the header tree in text (`Sales | 2024 / Q1 | 10`).

### 4.7 TableLlama (Zhang et al., NAACL 2024)

Instruction-tunes Llama 2 7B with LongLoRA on TableInstruct. Serialization is ordinary row-wise text; the contribution is **long context + diverse table tasks**, not a new format. For POMA this argues that Qwen3-8B/Gemma may already “know” several formats from pretraining, so a format swap is cheap to try, but long hierarchical tables still need a long context or a preview (POMA already has `build_table_preview` for the hint predictor).

### 4.8 Chain-of-Table (Wang et al., ICLR 2024)

The table is not a static prompt blob. The model emits DataFrame/SQL-like operations (`select_row`, `select_column`, `group_by`, `sort`, `add_column`) and the **updated table** is re-serialized into the next step. This is a representation *policy*: keep intermediate evidence tabular.

POMA already decomposes by question type, not by table operations. A later experiment could give one specialist Chain-of-Table tools while keeping Flatten V1 for the others. It is not a first-line format ablation.

### 4.9 Binder and StructGPT

**Binder** (Cheng et al., 2023) binds Codex to SQL/Python with an `LLM()` API in the program, so the table lives as a database, not as a prompt dump. **StructGPT** (Jiang et al., EMNLP 2023) uses an invoke-linearize-generate loop: an interface extracts a small evidence table, then the LLM sees only that slice.

Both are attractive for large tables, but Open-ViTabQA HTML is messy (merged cells, Vietnamese headers, mixed numeric formats). Building a faithful SQLite view is a project of its own. Keep them as a second-wave experiment, not as the first format bake-off.

### 4.10 Rethinking Tabular Data Understanding (Liu, Wang, Chen, NAACL 2024)

They show LLMs are brittle to row/column permutation and that **textual vs symbolic** reasoning have complementary errors. Mixing both with self-consistency reached 73.6% on WikiTableQuestions. They also propose table-structure **normalization**.

**POMA mapping:** if HTML or Markdown wins, re-run with shuffled rows on `normal` tables. If the gap disappears, the win was spurious order bias (the TableFormer concern). Flatten V1 currently preserves HTML row order, which is usually the Wikipedia reading order.

### 4.11 Industry / blog format bake-offs

The Improving Agents post (11 formats, one large table, no header repetition) ranks **Markdown-KV** first (60.7%) and **pipe-delimited / CSV** last (~41–44%). Token cost of Markdown-KV was about 2.7× CSV. This is not a peer-reviewed benchmark and used one table shape, so treat it as a hypothesis: repeating headers next to values helps on *wide* tables. Open-ViTabQA has both wide month-tables and tall list-tables; Markdown-KV may help the former and waste tokens on the latter.

Lu et al.'s survey concludes that **HTML and NL-with-separators** are the two strongest default families, which matches Table Meets LLM and does *not* match the Improving Agents ranking. Another reason to measure locally.

## 5. What the literature agrees on

1. **Format is not a cosmetic choice.** Holding content fixed, HTML vs Markdown vs JSON vs pipe-separated can move both structural probes and downstream QA by several points.
2. **HTML is the most robust markup for Wikipedia-like tables** in Table Meets LLM and TABVERSE. That is the closest domain to Open-ViTabQA.
3. **Markdown is the usual default** in LLM table papers (TableLlama, many agents) and is more compact. It cannot represent `colspan`/`rowspan`.
4. **JSON as a list of row objects** is convenient for code but often weaker for LLM QA, especially multi-table settings (TQA-Bench).
5. **Merged / hierarchical headers** are a known failure mode. TUTA, HiTab, MULTIHIERTT, SpreadsheetLLM, and Open-ViTabQA all flag them. Flatten V1 duplicates values; it does not name the header *path*.
6. **Row-level indexing is still hard** even with HTML (TABVERSE row retrieval 5%). POMA's evidence strings that quote a Flatten V1 line may be helping here; a format that destroys those copyable lines (pretty JSON) could hurt GSA.
7. **Tell the model the format.** Table Meets LLM's format explanation and “question after the table” are cheap, format-agnostic gains.
8. **No universal winner.** Multi-table SQL-ish tasks prefer Markdown; Wikipedia SUC prefers HTML; fact-finding sometimes prefers DataFrame strings. POMA must measure on Open-ViTabQA, sliced by `table_type`.

## 6. Implications for POMA

| Open-ViTabQA property | Flatten V1 behavior | Risk | Encodings to try |
|---|---|---|---|
| Merged headers | Value copied into every spanned cell; `<header>` on each | Model cannot see that Q1 and Q2 sit under 2024 | `raw_html`, `html`, `header_path`, `latex` |
| Merged values | Same duplication | Inflated row retrieval; duplicated evidence | `raw_html` (keep rowspan), `inverted_index` |
| Vietnamese text | Unchanged | Markup tokens (`<header>`, `|`) mix with Vietnamese | `markdown`, `json_records` (quoted strings) |
| Wide tables | One long pipe line | Header/value misalignment | `markdown_kv`, `json_triples`, `header_path` |
| Tall tables | One line per row | Context overflow (already handled by preview on hint predictor) | keep `flatten_v1` / `csv`; avoid KV |
| Evidence quoting in GSA | Specialists quote Flatten V1 lines | Switching format requires matching evidence format | any new format must be used in **all** stages |
| No SQL schema | Not a database | Binder/StructGPT need a cleaner grid first | optional later |

The production pipeline should stay on Flatten V1 until a paired test on the same questions shows a gain. A new format has to be swapped in `create_representation()` and in every prompt that currently interpolates `{table_flattened}`.

## 7. Recommended local experiment

Run on a **paired** subset, not a new split. Suggested first cut:

- 50 `normal` + 50 `contain_merged_header` + 50 `contain_merged_value` questions from `qas_test.json`.
- Frozen backbone (the current Qwen3-8B POMA or the compact zero-shot baseline).
- One format at a time; no prompt wording changes except a one-line format legend.
- Report EM/F1 overall **and** by `table_type`.
- Also log `n_chars` / approx tokens (the CLI already writes `sizes.json`).

**First four formats (enough to falsify Flatten V1):**

1. `flatten_v1` — control.
2. `html` — literature favorite for Wikipedia tables.
3. `markdown` — compact default in LLM papers.
4. `header_path` — explicit hierarchy for merged headers.

**If HTML wins on merged tables but loses on normal tables**, add `raw_html` (native colspan) vs rebuilt `html` (expanded grid).  
**If Markdown is close and much cheaper**, add `markdown_kv` only on tables with ≥8 columns.  
**Do not** start with Chain-of-Table, Binder, or VLMs until this four-way test is done.

## 8. What this folder implements

`encodings.py` serializes the **same parsed grid** into 16 strings. `run_encode.py` dumps them next to a size table. Tests in `tests/experiments/test_table_representation.py` lock the Flatten V1 header tags, TAPEX prefixes, Markdown grid, JSON records, and composed merged-header paths.

Sample dumps for a compact normal table (`29_4`) and a merged-header table (`37_1`) are under `samples/`. On `29_4`, Flatten V1 is the shortest encoding (251 characters); JSON triples are the longest (1336). On the merged-header table `37_1`, CSV/TAPEX/Markdown are slightly shorter than Flatten V1 because they compose the two header rows into one, while `raw_html` is about 4× Flatten V1 because it still contains Wikipedia link markup.

This is not a claim that any alternative beats Flatten V1 on Open-ViTabQA. It is the minimum setup needed to run that comparison without mixing content, parser, and prompt changes.

A later CPU run of SEA-LION 8B on the **first 50** `qas_test` items (Markdown/prune + few-shot + `table_ops.py`) is logged in `RESULTS.md`: raw EM 0.62 → final EM **0.80**. That run is a cheap-8B recipe, not the four-way Flatten V1 / HTML / Markdown / header-path ablation above.
