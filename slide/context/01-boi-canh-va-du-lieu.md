# 01 — Background, task, and data

## Task

Answer Vietnamese questions about semi-structured tables (Vietnamese Table QA)
using the **Open-ViTabQA** benchmark. Tables come from Vietnamese Wikipedia
and may contain multilevel headers and merged cells (`rowspan`/`colspan`).
Questions may require multistep reasoning; unanswerable questions must return
the exact string `Null`. Project constraint: an **open backbone under 10B
parameters, without fine-tuning**. Changes are limited to prompts and the pipeline.

## Data (measured from repository files, not copied from the paper) [MEASURED]

| Measure | Value |
|---|---|
| QA pairs | train 7.928 / dev 991 / test 992 (total 9.911) |
| Source tables | 329 |
| Unanswerable questions (test) | **45/992 = 4,5%** (train 346/7.928 = 4,4%) |
| Table length (tokens) | p50 ≈ **647**, p90 ≈ 2.097, max ≈ 19.284 |
| Tables over 2.000 tokens (test) | 155/992 = 15,6% of questions but **54,8% of all table tokens** |
| Answers copied verbatim from one cell | 42,3% (span-aware recheck: 43,2%) |
| Hint labels per question | 903 questions (91,0%) have one label; 86 have two; 3 have three → mean ≈ 1,10 |

Sources: `docs/research/2026-09-18-multi-agent-small-llm-huong-di.md` §0;
`docs/research/2026-09-18-supporting/structure-encoding-shortlist.md` §0.

## Four data facts that **conflict with the draft** and need correction

| Draft/spec says | Measured result | Implication |
|---|---|---|
| About 10% of questions are unanswerable | **4,5% (45/992)** | Recalculate answerability arguments for a rare 4,5% class |
| Many specialists run "in parallel" | **91% of questions have one hint label → 880/992 (88,7%) call only one specialist** | Parallel execution actually occurs for only about 11% of questions |
| Three `table_type` categories | **Four categories**: normal 461 / merged_value 262 / merged_header 143 / **both 126** | A three-way report either double-counts 126 questions or hides the interaction |
| Trace lists 46 gold `Null` answers | Released file contains **45** | Rebuild Fig. 2 and the answerability confusion matrix |

## What the table structures actually look like [MEASURED]

Analysis of 329 tables with a span-expanding parser
(`structure-encoding-shortlist.md` §0):

| Feature | Tables | Test questions |
|---|---:|---:|
| Full-width banner (colspan = ncols) | 44 | 128 |
| Left header column (matrix layout) | 57 | 153 |
| Truly nested headers (depth ≥ 2) | **28** | **92** |
| `<td>` with colspan | 66 | 197 |
| `<td>` with rowspan | 81 | **252** |
| None of these merge features | 147 | 481 |

- Header depth: **256/329 tables have only one header row**, 60 have two,
  2 have three, and 11 have none.
- Only **38 tables** have a "full header path" different from the flat string,
  affecting just **116 test questions**.
- 77,8% of tables have headers only in the top rows; 22,2% have a left header column.

**Slide takeaway:** "merged header" in Open-ViTabQA **usually does not mean
deeply nested headers**. It is often (a) a title banner duplicated during span
expansion or (b) a matrix layout with labels in the left column. Encoding
`"Revenue > 2023 > Q1"` therefore targets a minority of 116 questions.

## Data leakage across splits [MEASURED]

- **All 296 dev tables and 289 test tables also appear in train**; all 329
  tables have training questions.
- 24/991 dev questions exactly duplicate a train question.

Implication: methods that use train data (fixed few-shot examples, formatting
rules inferred from train, retrieval, learned selectors) must report results
**separately for seen and unseen tables**. Source:
`docs/research/enhance_poma/2026-09-19-poma-improvement-directions.md` §2.2.

## Design implications of these data

1. **Tables are usually small (p50 ≈ 647 tokens).** Methods built to solve
   overlong context (TableRAG, TabSQLify, TableZoomer) address the wrong
   bottleneck for about 90% of this dataset. Only 15,6% of questions have
   tables long enough for meaningful reduction (→ D10).
2. **The `Null` class is rare (4,5%).** Any abstention mechanism must account
   for false abstentions given the roughly 20:1 class imbalance.
3. **91% of questions have one label.** An architecture based on specialist
   disagreement has almost no opportunity to act (→ rejection of poma2; see
   [03](03-trang-thai-bai-bao.md)).
4. **42,3% of answers are entire cells.** Much of the task is locating a cell
   rather than calculating a value.
