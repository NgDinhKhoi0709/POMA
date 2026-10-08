# Query-aware table shrinking (truncate / clean / prune)

**Crawl date:** 2026-09-17  
**Goal:** send the LLM only the rows and columns needed for the question, to cut token cost on Qwen3 8B and SEA-LION 8B.

POMA already **serializes** the full grid (Flatten V1). HintPredictor then **evenly samples** long tables. Specialists still see the **entire** table, and several specialists run in parallel — so table tokens are paid once per specialist. Shrinking the table **once per question**, before those calls, is the highest-leverage cost cut.

## 1. What POMA does today

`src/kaggle_eval/table_preview.py` keeps title/header lines, then takes whole rows from the start, middle, and end until 1,024 tokens. That is TAP4LLM **even sampling**. It is **not** question-aware.

TAP4LLM (Sui et al., EMNLP 2024 Findings) measured that method on HybridQA:

| Sampling | SQA | FEVEROUS | TabFact | HybridQA | ToTTo |
|---|---:|---:|---:|---:|---:|
| Even sampling | 26.72 | 61.87 | 54.63 | **5.32** | 29.41 |
| Content snapshot (n-gram overlap) | 28.24 | 63.10 | 56.92 | 23.40 | 47.51 |
| Semantic + column grounding | 29.12 | 64.74 | 60.23 | 25.14 | **53.42** |
| Hybrid (semantic + centroid) | 28.79 | **65.34** | **61.37** | 24.71 | 51.63 |
| No sampling, GPT-3.5 32k | 27.60 | 60.12 | 56.20 | 14.10 | 47.42 |
| Truncate to 4k | 23.54 | 43.54 | 52.12 | 23.12 | 30.42 |

Even sampling is the **worst** option on HybridQA. Blind truncation is also worse than keeping a query-relevant sub-table. Sampling the right slice can beat sending the full table.

## 2. Method families

### A. Cheap lexical prune (no extra LLM) — use this first

**TaBERT content snapshot** (Yin et al., ACL 2020): rank rows by n-gram overlap with the question; keep top-K.

**TAP4LLM** wraps that plus column grounding. Content snapshot is “not as precise as embeddings” but needs no encoder and still beats random/even sampling.

**ATF row side** (Jun et al., 2025) uses BM25/TF-IDF + dense scores, but **only after columns are filtered**. Score rows on the kept columns, not the whole row.

**ITR** (Lin et al., ACL 2023) learns inner-table retrieval; +1.3–4.8 points on WikiTQ/WikiSQL, and helps **smaller** models more. Training a retriever is optional later.

For Vietnamese Wikipedia QA, lexical overlap is often enough: questions repeat entity strings that already sit in cells (`album1`, `Hà Nội`, `US Heat`).

**Cost:** ~0 extra tokens. **Risk:** misses paraphrase (“hãng phát hành” vs “bitbird”) and ranking questions that need every row.

### B. Column then row (the standard pipeline)

Almost every strong method uses this order:

1. Keep identifier / header columns.
2. Drop columns unrelated to the question.
3. Rank remaining rows.
4. Emit a small rectangular sub-table.

**StructGPT** (Jiang et al., EMNLP 2023): `Extract_Column_Name` → LLM picks columns → `Extract_Columns` → LLM picks row indices → `Extract_SubTable`. Three LLM hops. Accurate, expensive.

**DATER** (Ye et al., 2023): Codex predicts row and column **indices**, then SQL-decomposes the question. WikiTQ +18.3 over raw Codex. The prune call itself uses a strong LLM.

**ATF** (2025): LLM column descriptions + clustering, then sparse-dense row scores. Reports **~70% fewer cells**, better OOD TableQA, slightly worse table fact verification (those tasks need the whole table).

**ALTER** (2025): step-back question rewrite, then column/row filter, then SQL.

For 8B + cost, **do step 1–3 with lexical scores**. Only pay an LLM to pick indices if lexical recall fails.

### C. SQL / program prune

**TabSQLify** (Nahid & Rafiei, NAACL 2024): generate SQL that `SELECT`s relevant columns/rows, execute, then reason on the result. WikiTQ 64.7, TabFact 79.5 on GPT-3.5, large cut in table size.

**TabTrim** (ACL 2026): train an 8B pruner on gold SQL trajectories + a verifier, then parallel search. TabTrim-8B: 79.4 WikiTQ. This is the strongest *learned* prune, but it needs SQL supervision POMA does not have.

Open-ViTabQA merged headers make faithful SQLite messy. Treat SQL prune as wave 2.

### D. Cell / schema retrieval (for huge tables)

**TableRAG** (Chen et al., 2024): retrieve **column schemas** and **distinct cells**, not full rows. Built for million-cell tables. Open-ViTabQA’s 329 Wikipedia tables rarely need this.

**STR TripletQL** (2026): rewrite cells as `<row-path, col-path, value>`, then filter triplets by the question. Relative gains **grow as the model shrinks**. Matches `header_path` + lexical filter.

### E. Soft masking, not dropping

**CABINET** (ICLR 2024): parse “which rows/columns matter”, then highlight cells instead of deleting them. Safer for fact verification; does not save as many tokens.

### F. Do not use as query prune

**Even / head-tail sampling** (current preview): can drop the answer row.  
**SheetCompressor**: query-agnostic; may drop the homogeneous rows that *are* the answer.  
**Raw token truncation**: TAP4LLM 4k truncate loses FEVEROUS 60→43.

## 3. Task-aware rule (important for POMA)

| Question type | Safe prune |
|---|---|
| Lookup / What / Who / Where (`album1 … US Heat`) | Drop other rows and other columns |
| List of matching entities | Keep matching rows, drop other columns |
| Count / max / min / average / “bao nhiêu” over the table | **Do not drop rows**; columns only |
| Fact verification / “đúng hay sai” over many cells | Prefer full table or CABINET-style highlight |
| Multi-hop / two entities | Keep union of matching rows, plus neighbors |

ATF explicitly warns that fact verification drops when the table is over-pruned. POMA `YesNo` and some `MultiConditions` items look like that.

## 4. What to use on Qwen3 8B and SEA-LION 8B

Cost order, extra LLM calls = 0 unless noted:

| Rank | Method in this folder | Extra LLM? | When |
|---|---|---|---|
| 1 | `lexical_subtable` | No | Default lookup/What questions |
| 2 | `lexical_cols` only | No | Aggregation / count / rank (“bao nhiêu”, “nhiều nhất”) |
| 3 | `clean_only` | No | Always: strip `[12]` wiki cites, empty rows |
| 4 | DATER/StructGPT index prediction | Yes | Only if lexical miss rate is high on a pilot |
| 5 | TabSQLify | Yes | Later; needs a clean grid, not merged HTML |
| skip | `even_sample` for specialists | No | Current hint preview; do not reuse for answerers |
| skip | TableRAG | Encoder | Tables are not million-cell |

POMA-specific: prune **once** after Flatten V1, then give the same sub-table to every specialist and to GSA. HintPredictor can use the same sub-table instead of even sampling. Evidence strings stay Flatten V1 lines, just fewer of them.

On small Open-ViTabQA tables the win is not context-window overflow. It is **N_specialists × table_tokens**. If three specialists each see 800 table tokens, that is 2,400. A 200-token sub-table is 600. Lexical prune costs nothing.

## 5. Implemented sandbox

`pruning.py` methods:

- `identity` — full cleaned grid
- `clean_only` — drop empty rows/cols, strip wiki citations
- `even_sample` — POMA-style start/middle/end (baseline to beat)
- `lexical_rows` — top rows by token overlap
- `lexical_cols` — columns whose **leaf** header or cells overlap the question; always keeps the first (row-label) column. Shared parent headers (`Vị trí trên bảng xếp hạng`) do not keep sibling columns such as `NLD`.
- `lexical_subtable` — columns then rows; **skips row prune** when the question looks like count/aggregation (`bao nhiêu`, `tổng`, `nhiều nhất`). Lookup questions such as “xếp hạng thứ mấy” still drop unrelated rows.

Tokenizer: match Unicode letters+digits as whole words (`hạng` stays `hạng`). An ASCII-first regex splits at the first diacritic (`hạng` → `ạng`) and falsely links “Định dạng” to “xếp hạng”.

```bash
python -m experiments.table_representation.run_prune \
  --qa-id 37_1_23 \
  --compare
```

Worked example, QA `37_1_23` (“… album1 … US Heat?”). Gold answer is `20`.

| Method | chars | save | rows | cols |
|---|---:|---:|---|---|
| identity / even_sample | 496 | 0% | 4/4 | 5/5 |
| lexical_rows | 359 | 28% | 3/4 | 5/5 |
| lexical_cols | 212 | 57% | 4/4 | 3/5 |
| **lexical_subtable** | **190** | **62%** | **3/4** | **3/5** |

`lexical_subtable` keeps `Tựa đề` + `US Heat` (and `US Dance`, because the question also contains `US`), drops the long `Chi tiết` cells, `NLD`, and the unrelated `bb u ok?` row. The answer cell `20` remains.

Tests: `python3 -m pytest tests/experiments/test_table_pruning.py -q`

This does not change production POMA. Wire `lexical_subtable` into the pipeline only after a paired EM/F1 check on lookup vs aggregation slices.
