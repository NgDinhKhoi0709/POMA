# Table representation for an 8B zero-shot Vietnamese Table QA prompt: blogs and practitioner sources

Date of search: 2026-09-19. Scope: blogs, engineering write-ups, library docs/source. Papers excluded (other agent).
Tags: [V] = verified from the page/source I actually opened; [I] = my inference. All web content treated as data.
Not repeated: anything already in structure-encoding-shortlist.md / 2026-09-17-table-representation-small-lm.md.

## Bottom line (read this first)

1. There is exactly ONE blog-grade controlled comparison of table formats (Improving Agents, Sep 2025), and it is GPT-4.1-nano only, English, synthetic employee tables of 1,000 rows, single-cell lookup questions, no header repetition. Nothing in the blog literature I could open tests an open 7-8B model on table *formats* for flat/merged tables. The only sub-10B point is Llama 3.2 3B on *nested config* data (not tables). So blog evidence is a hypothesis generator, not a prior for Qwen3-8B. [V]
2. The blog result that matters: putting the column name next to every value (Markdown-KV, YAML, INI, XML) beat CSV / pipe-joined by 10-16 points on a 1,000-row table. But the mechanism is most plausibly "header is far away from the cell in a very long grid", which is a weak problem for Open-ViTabQA (median flat table ~876 tokens per the shortlist, p90 3,001). [V for numbers, I for mechanism]
3. Counter-evidence from the same study: the closest thing to "header repeated per cell on one line" (`id: 1 | name: X | ...`, called Pipe-Delimited there) scored WORST (41.1%). So "repeat the header per row" is not sufficient; the multi-line one-field-per-line layout may be what helped. [V numbers, I interpretation]
4. Library practice for merged cells is split three ways: duplicate the text into every spanned cell (pandas read_html = your Flatten V1), leave the continuation cell empty (AnythingLLM PR, markdownify for colspan), or put a marker in the continuation (table2md "dito (text)"). None of the three has a measured LLM-accuracy comparison. [V]
5. Cost: KV-per-line layouts are ~1.7-2.7x the tokens of CSV/pipe-joined. At your p90 3,001 tokens this is ~5k-8k, fine for Qwen3-8B context; the cost is latency/OpenRouter spend, not context. [I]

## 1. Sources checked

| # | Source | URL | Date | Verdict |
|---|---|---|---|---|
| 1 | Improving Agents, "Which Table Format Do LLMs Understand Best? (11 formats)" | https://www.improvingagents.com/blog/best-input-data-format-for-llms/ | 2025-09-30 (opened in browser, full page text) | RELEVANT, the key blog. GPT-4.1-nano only, n=1000 questions/format. Full numbers in section 2. |
| 2 | Improving Agents, "Which Nested Data Format Do LLMs Understand Best?" | https://www.improvingagents.com/blog/best-nested-data-format/ | 2025-10-14 (WebFetch summary) | PARTIAL. Nested Terraform-like config, not tables. GPT-5 Nano / Llama 3.2 3B Instruct / Gemini 2.5 Flash Lite, 1,000 questions per format per model. Only source with a sub-10B model, but different data type. |
| 3 | Improving Agents, "TOON Benchmarks" | https://www.improvingagents.com/blog/toon-benchmarks/ | 2025-10-28 (WebFetch) | LOW. TOON (header-once CSV-like) 47.5% vs CSV 44.3% (n.s.) vs Markdown-table 51.9% on the same GPT-4.1-nano test; authors "failed to find circumstances where TOON was the best-performing format". Not useful for merged-header tables. |
| 4 | toon-format/toon Discussion #285, community expanded benchmark | https://github.com/toon-format/toon/discussions/285 | undated in fetch (community post, unreviewed) | LOW-MED. 34 models via Bedrock incl. Ministral 3B, Llama 3.x, Gemma 3 27B, Nemotron Nano 9B (no param counts given). YAML 83.0 > JSON pretty 81.0 > JSON compact 79.6 > TOON 77.4 > CSV 69.7 (flat only). Small models show 10-15 pp gaps concentrated on filtering. Self-selected, not controlled. |
| 5 | TOON official benchmarks | https://toonformat.dev/guide/benchmarks | 2025 (v4.1.1) | IRRELEVANT for us: format author's own benchmark, closed-weight models only (haiku-4.5, gemini flash, gpt-5.4-nano, grok), 244 questions; TOON 63.1 vs CSV 62.2 vs JSON 60.3 on flat data. |
| 6 | GIGAZINE write-up | https://gigazine.net/gsc_news/en/20251007-ai-table-format/ | 2025-10-07 | Secondary copy of #1. Says "GPT-4.1 mini"; the primary page says GPT-4.1-nano. Trust the primary. |
| 7 | anup.io "Data in CSV Format Isn't Always the Best for LLMs" | https://www.anup.io/data-in-csv-format-isnt-always-the-best-for-llms/ | 2025-10-07 | Secondary retelling of #1; no models/n stated. Ignore. |
| 8 | idir.ai "I Made a Mistake About TOON" | https://www.idir.ai/en/blog/i-made-a-mistake-about-toon-and-heres-the-data-that-proved-me-wrong | seen only in search snippet | Re-cites #1 (not opened). Ignore. |
| 9 | Towards Data Science, "Retrieve One Row from a Table, Not the Whole Table: Row-Level Chunks for RAG" | https://towardsdatascience.com/retrieve-one-row-from-a-table-not-the-whole-table-row-level-chunks-for-rag/ | 2026-08-21 (direct fetch and browser both failed; content obtained via a third-party reader proxy, r.jina.ai) | PARTIAL. Recommends each body row as `col: val \| col: val \| ...` "so the column names travel with the values". Retrieval only, character-count savings, no model, no n, no accuracy. Its format is the one that scored worst in #1 for QA. |
| 10 | dev.to (Encephos), "How to stop LLMs from hallucinating on complex HTML tables" | https://dev.to/encephos/how-to-stop-llms-from-hallucinating-on-complex-html-tables-python-2e0k | 2026-07-29 | RELEVANT for merged-cell mechanics only. `table2md` grid solver fills spanned cells with a prefix such as "dito (Spanned Header)". No benchmarks, no models; anecdotal. |
| 11 | AnythingLLM PR #6388 "give a merged table cell the columns it covers" | https://github.com/Mintplex-Labs/anything-llm/pull/6388 | merged 2026-09-17 | RELEVANT (mechanics). Lays out a browser-style grid; colspan padded with empty `\|`, rowspan continuation cell left empty. Clamps colspan to 1..1000. 48/48 unit tests, no LLM evaluation. |
| 12 | markdownify source (`convert_td`/`convert_th`/`convert_tr`) | https://raw.githubusercontent.com/matthewwithanm/python-markdownify/develop/markdownify/__init__.py | read 2026-09-19 | RELEVANT (mechanics). colspan: text followed by `' \|' * colspan` (clamped 1-1000, empty cells after); rowspan: not handled at all, so later rows misalign. |
| 13 | pandas `read_html` source (`_expand_colspan_rowspan`) | https://raw.githubusercontent.com/pandas-dev/pandas/main/pandas/io/html.py | read 2026-09-19 | RELEVANT (mechanics). Docstring: cell contents "copied to subsequent cells". Identical policy to your Flatten V1. |
| 14 | Docling docs "Advanced chunking & serialization" + issues docling #1853 (2025-06-25) and docling-core #722 (2026-08-18) | https://docling-project.github.io/docling/_generated/examples/advanced_chunking_and_serialization/ ; https://github.com/docling-project/docling/issues/1853 ; https://github.com/docling-project/docling-core/issues/722 | see left | RELEVANT. Default `TripletTableSerializer` emits `row_header, col_header = value.` sentences; `MarkdownTableSerializer` hardcodes grid row 0 as the only header and demotes stacked header rows to data (known bug). No accuracy evaluation in docs. |
| 15 | websiteaiscore "The Token Tax: HTML Tables Break AI Rankings" | https://websiteaiscore.com/blog/markdown-vs-html-tables-rag-optimization | 2025-12-24 | LOW. Assertions only (HTML 3-5x tokens; 3x3 table ~180 vs ~45 tokens), no experiment. Advises "repeat the data in each cell" for merged cells, matching Flatten V1. |
| 16 | "Notation Matters" (Kutschka and Geiger) | https://arxiv.org/abs/2605.29676 | 2026-05-28 | IRRELEVANT: it is a paper, and concerns JSON vs TOON/TRON in agentic tool calls, five 7-8B open models but no tables. |
| 17 | Sebastian Raschka, Ahead of AI archive (magazine.sebastianraschka.com) | https://magazine.sebastianraschka.com/archive | 2026-09-19 (browser text of archive listing, ~30 posts visible) | NOTHING on table serialization. Archive is LLM architecture / training / reasoning / multimodal posts. Substack site search and the JSON archive API did not return usable results (HTTP 400 / no filter applied), so I cannot rule out an unlisted mention; a web search restricted to his domains found no table-format post. His older post on deep learning for tabular data (sebastianraschka.com/blog/2022/deep-learning-for-tabular-data.html) is about NN architectures, not prompts. |
| 18 | Hugging Face blog / docs (table QA) | search only: https://huggingface.co/tasks/table-question-answering | n/a | Nothing on prompt serialization; TAPAS/TableLLM pages. Irrelevant. |
| 19 | Lilian Weng, Eugene Yan, Simon Willison, Hamel Husain | search only | n/a | Searched for table-format content; found none (Willison posts are about CLI/`files-to-prompt`). I did not read their archives exhaustively. |
| 20 | Microsoft Learn / Azure AI Document Intelligence RAG docs | https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/retrieval-augmented-generation?view=doc-intel-4.0.0 | search snippets only | Recommend Markdown output from Layout model and separate chunks for tables; no comparative evidence. Not opened in full. |
| 21 | LangChain CSVLoader docs | https://python.langchain.com/v0.2/docs/how_to/document_loader_csv/ | search snippet | Confirms default per-row document = `column: value` on separate lines (i.e. Markdown-KV-like without headings). Convention, not evidence. |
| 22 | Unstructured docs "table-to-html" | https://docs.unstructured.io/concepts/enriching/table-to-html | fetched 2026-09-19 | Promotes HTML (`text_as_html`) as canonical; no numbers; merged-cell handling not documented on that page. |
| 23 | LlamaIndex (PandasQueryEngine, LlamaParse tweet) | search snippets | n/a | Pandas engine prints `str(df)` (whitespace-aligned, `to_string`-like) for the LLM; LlamaParse claims better markdown table reconstruction (tweet, no numbers). Not opened. Irrelevant to zero-shot serialization. |
| 24 | Medium posts (Jani benchmark; ESTretyakov; SoftServe; Towards AI chunking) | various | n/a | Could not open (403 / empty). Snippets only; the Jani numbers (Llama-3.1-8B markdown 57.0, Qwen2.5-7B 62.2) look like they derive from a paper (arXiv 2603.15402), so leave to the papers agent. |
| 25 | OpenAI cookbook / Anthropic docs / Cohere / Google docs on table input | search only | n/a | No official guidance with evidence found. Only generic advice ("Markdown beats CSV", XML tags for sections). |

## 2. The one hard blog experiment (source #1), verbatim numbers [V]

Setup [V]: GPT-4.1-nano (parameter count undisclosed), 1,000 synthetic employee records x 8 attributes (id, name, age, city, department, salary, years_experience, project_count), 1,000 randomized single-field lookup questions ("What is Alice W204's salary?"), 11 formats, 95% CI half-width about +/-3.1 pts. No header repetition ("we didn't do that here"). Authors state limitations: one model, one data pattern, straightforward tables only, lookups only, "particularly for CSV, HTML and markdown table formats" they expect repeated headers/smaller tables to do better.

| Format | Accuracy | 95% CI | Tokens | x CSV tokens |
|---|---|---|---|---|
| Markdown-KV | 60.7% | 57.6-63.7 | 52,104 | 2.67 |
| XML | 56.0% | 52.9-59.0 | 76,114 | 3.90 |
| INI | 55.7% | 52.6-58.8 | 48,100 | 2.46 |
| YAML | 54.7% | 51.6-57.8 | 55,395 | 2.84 |
| HTML | 53.6% | 50.5-56.7 | 75,204 | 3.85 |
| JSON | 52.3% | 49.2-55.4 | 66,396 | 3.40 |
| Markdown table | 51.9% | 48.8-55.0 | 25,140 | 1.29 |
| Natural language | 49.6% | 46.5-52.7 | 43,411 | 2.22 |
| JSONL | 45.0% | 41.9-48.1 | 54,407 | 2.79 |
| CSV | 44.3% | 41.2-47.4 | 19,524 | 1.00 |
| "Pipe-delimited" (`k: v \| k: v \| ...`) | 41.1% | 38.1-44.2 | 43,098 | 2.21 |

My reading [I]: (a) Markdown-KV vs CSV/pipe/JSONL is outside the CIs; Markdown-KV vs XML/INI/YAML/HTML/JSON is roughly at or inside the CI edge, so only "KV-per-line beats CSV/pipe" is solid, not the fine ranking. (b) HTML 53.6 vs Markdown table 51.9 is well inside noise. (c) Because the pipe row with keys did worst while the same information one-field-per-line did best, line structure (one cell per line, its own name in front) rather than "header repeated" is the plausible driver. (d) The 1,000-row scale is the confound; the authors themselves say to expect smaller tables to close the gap.

Nested-data follow-up (#2) [V]: GPT-5 Nano YAML 62.1 > Markdown 54.3 > JSON 50.3 > XML 44.4; Llama 3.2 3B JSON 52.7 > XML 50.7 > YAML 49.1 > Markdown 48.0; Gemini 2.5 Flash Lite YAML 51.9 > Markdown 48.2 > JSON 43.1 > XML 33.8. Model-specific ranking again (a 3B open model prefers JSON; two closed models prefer YAML). Markdown was 34% fewer tokens than JSON, 10% fewer than YAML (GPT-5 Nano). Consistent with the shortlist's TABVERSE point that rankings flip across models.

## 3. Candidate representations not already in the two docs

Illustrative tiny table used throughout (3 rows, already rectangular). Baseline Flatten V1:

```
Quốc gia <header>|Dân số <header>|Diện tích <header>
Việt Nam|100 triệu|331.212 km²
Lào|7,5 triệu|236.800 km²
Thái Lan|66 triệu|513.120 km²
```

Token ratios below: I measured this 3-row example with the o200k_base proxy tokenizer against Flatten V1 = 57 tokens [I: proxy, Qwen3 BPE differs on Vietnamese diacritics; ratios only]. They do not shrink with more rows (keys repeat per row) whereas Flatten V1's header amortizes, so long tables approach the "x CSV" ratios in section 2 divided by about 1.15 [I].

### C1. Markdown-KV record blocks (best format in source #1)
```
## Hàng 1
Quốc gia: Việt Nam
Dân số: 100 triệu
Diện tích: 331.212 km²

## Hàng 2
Quốc gia: Lào
Dân số: 7,5 triệu
Diện tích: 236.800 km²
```
(The blog fences each record in triple backticks; my measurement: 98 tokens without fences = 1.72x, 110 with fences = 1.93x.)
- Source: https://www.improvingagents.com/blog/best-input-data-format-for-llms/ (2025-09-30).
- Models: GPT-4.1-nano only, n=1000 questions, 1,000-row table. [V]
- Delta: 60.7% vs CSV 44.3% (+16.4), vs Markdown table 51.9% (+8.8), vs JSON 52.3% (+8.4), vs pipe-with-keys 41.1% (+19.6). [V]
- Token cost: source measured 52,104 vs CSV 19,524 = 2.67x; vs Markdown table 2.07x. My 3-row measurement 1.72x vs Flatten V1. [V for source, I for ours]
- Merged cells [I]: works naturally on an expanded rectangular grid since each record is self-contained; a rowspan value is simply repeated in every record it covers (duplicates cost 1 line each). A full-width colspan banner would become the same key repeated N times per record: hoist banner rows out first (matches the shortlist's Flatten V2 banner hoist), else the 9.27x pathology (`99911_1`) gets worse in this format. Header-group nesting can be embedded in the key (`Dân số > 2023`) at no structural cost, but that is the E3/E4 path family and has weak evidence per the shortlist.
- Caveats: no evidence at 7-8B; unclear whether the gain survives on ~10-50-row tables; lookup-only questions. The only sub-10B nearby signal (Llama 3.2 3B, nested data) preferred JSON over Markdown/YAML, i.e. not KV.

### C2. INI sections (per-row `[section]`, `key = value`)
```
[hang_1]
Quốc gia = Việt Nam
Dân số = 100 triệu
Diện tích = 331.212 km²
```
- Source: same blog. GPT-4.1-nano; 55.7% (+11.4 vs CSV); 48,100 tokens (2.46x CSV); 3-row measurement 95 tokens = 1.67x. [V/I]
- Merged: same as C1. Adds nothing over C1 except slightly fewer tokens per record in the blog (48,100 vs 52,104, -7.7%) at -5.0 pts (inside CI). Treat as a C1 variant, not a separate arm.

### C3. YAML list of records
```
rows:
  - Quốc gia: "Việt Nam"
    Dân số: "100 triệu"
    Diện tích: "331.212 km²"
```
- Source: same blog: 54.7% (+10.4 vs CSV), 55,395 tokens (2.84x). Nested-data blog: YAML best for GPT-5 Nano (62.1) and Gemini 2.5 Flash Lite (51.9) but 3rd of 4 for Llama 3.2 3B (49.1 vs JSON 52.7). TOON discussion #285 (34 models, community): YAML top at 83.0 vs JSON 81.0 vs CSV 69.7. [V]
- Merged [I]: same as C1; YAML quoting adds tokens and Vietnamese values containing `:` or `,` need quotes. 3-row measurement 96 tokens = 1.68x.
- Verdict: dominated by C1 for Vietnamese tables (quoting hazards, no accuracy edge), but it is the format with the broadest (still weak) cross-model support in blogs.

### C4. Header-repeated one-line row ("inline KV", a.k.a. pipe with keys)
```
Quốc gia: Việt Nam | Dân số: 100 triệu | Diện tích: 331.212 km²
Quốc gia: Lào | Dân số: 7,5 triệu | Diện tích: 236.800 km²
```
- Sources: worst format in #1 (41.1%, -3.2 vs CSV, 43,098 tokens = 2.21x); recommended for retrieval chunks by the TDS article (#9, no accuracy data). 3-row measurement: 80 tokens = 1.40x. [V/I]
- This is the closest cousin of Flatten V1 (same line layout, same `|` separators, header attached to every cell). Recorded mainly as a warning: header repetition on the same line is not what the top blog format does, and it did worst. Worth ONE cheap arm only if you want to test "header adjacent to every cell" without changing line structure, but the prior is negative. [I]
- Merged: same expanded grid; every spanned value carries its own key.

### C5. Natural-language sentence per row (template)
```
Việt Nam có dân số 100 triệu và diện tích 331.212 km².
Lào có dân số 7,5 triệu và diện tích 236.800 km².
```
- Source: same blog; the blog's NL was a one-sentence-per-record with all attributes: 49.6% (+5.3 vs CSV), 43,411 tokens (2.22x). Per-row NL template with the first column as subject is my Vietnamese adaptation; my 3-row measure 58 tokens = 1.02x (short because it drops keys' repetition and uses connective words instead). [V for blog, I for adaptation]
- Merged [I]: fragile. A template needs a subject column and reliable header semantics; banner rows, multi-level headers, and Yes/No or list-answer questions (155 + 56 in test per shortlist) don't map to a fixed sentence. Not competitive at 49.6 vs KV 60.7 in the source. Also NL adds hallucination surface for rewriting numbers/units.

### C6. Row-header-anchored triplets (Docling `TripletTableSerializer`)
```
Việt Nam, Dân số = 100 triệu. Việt Nam, Diện tích = 331.212 km². Lào, Dân số = 7,5 triệu. Lào, Diện tích = 236.800 km².
```
- Source: Docling docs and issue #1853 (2025-06-25), https://github.com/docling-project/docling/issues/1853 and the advanced_chunking example. Format is `row_header, column_header = value.` (see the verbatim complaint `a, column_b = b. column_c = c. d, column_b = e. column_c = f.`). No accuracy evaluation exists in the docs; it was designed for embeddings/chunk text, and users complain rows fuse into one block. [V]
- Token cost [I]: 3-row measure 80 tokens = 1.40x. Cost grows with columns because the row name repeats per cell.
- Merged [I]: it is the only serializer here that treats the FIRST column as the row identity, so it matches the 57 left-stub tables (shortlist section B) directly, but it is undefined for rowspan stubs unless the expanded stub value is repeated (which the grid already does). The `<th>` stub column would map to `row_header`. This is related to but distinct from the shortlist's STR triplets (`item_path, feature_path, value`): this is the flat 2-level version with no path expansion and no evidence at any model size. Caution per shortlist ASTRA note: code-like `=`/`.` syntax might read symbolic to an 8B; keep it sentence-like if tried.

### C7. Header repetition every N rows (control, not a new format)
```
Quốc gia <header>|Dân số <header>|Diện tích <header>
Việt Nam|100 triệu|331.212 km²
... (N rows)
Quốc gia <header>|Dân số <header>|Diện tích <header>
```
- Source: the Improving Agents blog explicitly recommends repeating headers "every 100 records" for CSV/HTML/Markdown tables, but they did NOT test it and only say they "would expect" higher accuracy. [V that it is untested] Docling chunker also has `repeat_table_header` and open issue #2975 confirming headers are lost in sibling chunks otherwise. [V from search snippet only]
- Relevance [I]: only matters for tables longer than ~50-100 rows; p90 flat length is 3,001 tokens (shortlist), so it will affect a small tail. Cheap (+1 line per N rows). Weakest priority.
- Merged: header rows are unaffected; multi-row headers must be repeated as a block.

### C8. Continuation-cell policy for spans (the merged-cell part specifically)
Options seen in real libraries, shown on a 2-row rowspan of "Việt Nam" and a 2-column colspan header "Dân số" over "2020 | 2021":

```
Duplicate (pandas read_html, HiTab-TaPas baseline = your Flatten V1):
  Việt Nam|97|98
  Việt Nam|24|25
Empty continuation (AnythingLLM PR #6388, markdownify for colspan):
  Việt Nam|97|98
          |24|25          # rowspan continuation left blank
Marker + text ("dito", table2md via dev.to #10):
  Việt Nam|97|98
  dito (Việt Nam)|24|25
Caret marker (already in shortlist Flatten V2):
  Việt Nam|97|98
  ^|24|25
```
- Evidence: none of the four has an LLM evaluation in any source I opened [V]. The Improving Agents blog did not test merged cells (it says "would be interesting"). websiteaiscore (#15) merely asserts "repeat the data in each cell" is safest.
- [I] Empty continuation is the riskiest for a zero-shot 8B (a blank cell can read as a missing value, and the rowspan label is what questions in the `merged_value` stratum refer to); markdownify additionally breaks rowspan alignment. Duplicate is your current best-supported default; `dito (X)` is the only NEW variant vs the shortlist (it keeps the text visible like duplication, yet tells the model it is a span continuation). It costs about +2 tokens per continuation cell. Cheap A/B: duplicate vs `dito (X)`/`(nt. X)` on the D-rowspan slice.
- Note for Vietnamese: a marker word would be Vietnamese ("như trên", "(gộp)") rather than Indonesian "dito"; keep it short.

## 4. What I would carry into the project [I]

- Best-supported blog signal, translated: test C1 (Markdown-KV) as one arm against Flatten V1 with header repetition equalized; hoist banners first; expect 1.7x tokens. Treat any win as model-specific and report McNemar on the merged strata. Use train+dev for slices per the shortlist.
- Do NOT expect the GPT-4.1-nano ranking to transfer: nano-scale lookup on a 1,000-row grid, no repetition of headers, lookup questions only. Your tables are ~50x shorter and ~57% of questions need computation/Yes-No/lists.
- The pipe-with-keys result (C4) is a cautionary counterpoint to any "just attach headers to every cell in the current layout" idea.
- The closest sub-10B blog data (Llama 3.2 3B) picked JSON on nested data, so at 8B keep an arm with JSON-records or the model's own preferred format if time permits, but JSON is 3.4x tokens.
- Sebastian Raschka's magazine has no relevant content that I could find; do not cite it.

## 5. Not verified / could not open
- TDS article opened only through a third-party reader proxy; author not named there.
- Medium posts (403/empty), Microsoft Learn pages (snippets only), LlamaIndex docs (snippets only), HF blog (nothing relevant), Lilian Weng/Eugene Yan/Hamel Husain/Simon Willison (no table-format content found; archives not exhaustively read).
- Improving Agents nested-data numbers and TOON post came via WebFetch summaries, not page text; the main table-format post was read in full via the browser.
- I did not run any model or API call; the token ratios are from a proxy tokenizer on a 3-row toy table.
