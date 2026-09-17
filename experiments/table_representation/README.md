# Table representation experiments

This folder is an isolated sandbox for comparing **how tables are shown to the LLM**. It does not change the production POMA pipeline, which still serializes every table as Open-ViTabQA **Flatten V1**.

## Why this exists

POMA currently parses HTML, expands merged cells, then emits pipe-separated rows with `<header>` tags. The paper notes that this flattening can hide hierarchical header scope. The literature on LLM table QA shows that the same table content can score several points differently depending on whether it is HTML, Markdown, JSON, TAPEX-style linearization, key-value rows, or a compressed spreadsheet encoding.

This package:

1. Re-serializes the **same parsed Open-ViTabQA grid** into 16 prompt formats.
2. Records a literature report from papers crawled on 2026-09-17.
3. Writes side-by-side samples so a later QA run can swap only the table string.

## Layout

```text
experiments/table_representation/
  README.md              # this file
  REPORT.md              # literature survey and POMA mapping
  sources.md             # crawled URLs and access dates
  encodings.py           # serializers
  run_encode.py          # CLI to dump encodings
  screenshots/           # browser captures from the paper crawl
  samples/               # example encodings from Open-ViTabQA tables
```

## Encode one table

From the repository root:

```bash
python -m experiments.table_representation.run_encode \
  --table-id 29_4 \
  --output experiments/table_representation/samples \
  --compare
```

Repeat `--table-id` for more tables, or pass `--limit 5` to encode the first five records. Restrict methods with `--methods flatten_v1,markdown,html,header_path`.

## Methods

| Method | What it emits | Main source |
|---|---|---|
| `flatten_v1` | Production POMA string: `cell <header>\|value` | Open-ViTabQA / POMA |
| `markdown` | GitHub-style pipe table | Table Meets LLM; TABVERSE |
| `html` | Rebuilt `<table>` after merge expansion | Sui et al. 2024; TABVERSE |
| `raw_html` | Original `table_html` with `rowspan`/`colspan` | Dataset native format |
| `csv` | Header + comma-separated rows | Sui et al. 2024 |
| `json_records` | List of row objects | Singha et al. 2023 |
| `json_triples` | `{row, column, value}` cells | TabRAG-style paths |
| `markdown_kv` | Per-row key/value list | Improving Agents Markdown-KV |
| `tapex` | `col: ... row i: ...` | TAPEX / OmniTab |
| `nl_sentences` | `column is value` sentences | TableGPT / Table-BERT |
| `xml` | Nested `<row><cell>` markup | Table Meets LLM |
| `latex` | `tabular` environment | TABVERSE |
| `spreadsheet_a1` | `A1,value\|B1,value` rows | SpreadsheetLLM vanilla |
| `inverted_index` | Value → address list JSON | SpreadsheetLLM SheetCompressor |
| `header_path` | `row \| header path \| value` | Hierarchical / HiTab style |
| `df_loader` | Pandas-like aligned text | Singha et al. 2023 |

## Tests

```bash
python -m pytest tests/experiments/test_table_representation.py -q
```

Tests use tiny HTML fixtures and do not call an LLM.

## What this folder does not do

It does not run POMA, does not call a model, and does not claim a winner. Use `REPORT.md` to choose a small comparison set, then pass the dumped strings into an existing baseline or POMA prompt in a later experiment.
