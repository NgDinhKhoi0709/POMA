# Table representation experiments

This folder is an isolated sandbox for comparing **how tables are shown to the LLM**. It does not change the production POMA pipeline, which still serializes every table as Open-ViTabQA **Flatten V1**.

## Why this exists

POMA currently parses HTML, expands merged cells, then emits pipe-separated rows with `<header>` tags. The paper notes that this flattening can hide hierarchical header scope. The literature on LLM table QA shows that the same table content can score several points differently depending on whether it is HTML, Markdown, JSON, TAPEX-style linearization, key-value rows, or a compressed spreadsheet encoding.

This package:

1. Re-serializes the **same parsed Open-ViTabQA grid** into 16 prompt formats.
2. Records a literature report from papers crawled on 2026-09-17.
3. Writes side-by-side samples so a later QA run can swap only the table string.
4. Prunes rows/columns to the question (`PRUNING.md`) so 8B calls send fewer tokens.

## Layout

```text
experiments/table_representation/
  README.md              # this file
  REPORT.md              # literature survey and POMA mapping
  RESULTS.md             # SEA-LION 50-sample protocol, method, EM/F1
  COMPARISON.md          # same-50 vs Qwen/POMA; paper full-test table
  PRUNING.md             # query-aware row/column shrinking
  sources.md             # crawled URLs and access dates
  encodings.py           # serializers
  pruning.py             # lexical sub-table filter
  table_ops.py           # question-gated count/list/min-max tools
  run_encode.py          # CLI to dump encodings
  run_prune.py           # CLI to dump pruned sub-tables
  run_sealion_gguf.py    # CPU GGUF SEA-LION runner + table ops
  screenshots/           # browser captures from the paper crawl
  samples/               # encodings, prune dumps, sealion_fifty scores
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
python -m pytest tests/experiments/test_table_representation.py tests/experiments/test_table_pruning.py tests/experiments/test_table_ops.py tests/experiments/test_run_sealion_gguf.py -q
```

Tests use tiny HTML fixtures and do not call an LLM.

## Query-aware shrinking

To cut prompt tokens, prune rows and columns that do not overlap the question **before** serialization. See `PRUNING.md`.

```bash
python -m experiments.table_representation.run_prune \
  --qa-id 37_1_23 \
  --output experiments/table_representation/samples/pruned \
  --compare
```

`lexical_subtable` is the default for lookup questions (no extra LLM call). Aggregation questions such as “bao nhiêu” keep all rows and only drop columns.

CPU 8B (no GPU): mmap official `Llama-SEA-LION-v3-8B-IT-Q4_K_M.gguf`. First 50 `qas_test` items with few-shot + table operators: **EM 0.80**. Protocol in `RESULTS.md`; comparison with Qwen ZS/FS/POMA in `COMPARISON.md`; per-id log in `samples/sealion_fifty/`.

```bash
python -m experiments.table_representation.run_sealion_gguf --limit 50 --table-mode auto --prompt-style few_shot
```

Raw jsonl/traces stay in gitignored `outputs/`. This folder does not change production Flatten V1.
