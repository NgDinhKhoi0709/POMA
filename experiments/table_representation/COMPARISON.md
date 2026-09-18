# Comparison: sandbox SEA-LION vs methods already run

Two different splits. Do not mix them.

1. **First 50 of `qas_test.json` (file order)** — the SEA-LION CPU experiment. Qwen / POMA numbers here are the same 50 ids, rescored from saved `outputs/` with this repo’s `evaluation/`.
2. **Full Open-ViTabQA test (992)** — paper table, plus a rescore of the prediction files still on disk.

SEA-LION was **not** run on the full 992. GPT-4o POMA dumps are incomplete; they are listed last.

Machine copy: `samples/sealion_fifty/comparison.json`.

## 1. Same 50 questions as the SEA-LION run

Rescored 2026-09-18. Candidate policy `all`. Metrics are **percent**. Hits are EM count / 50.

| System | Table | EM | F1 | R1 | MET | Hits |
|---|---|---:|---:|---:|---:|---:|
| POMA Qwen3-8B (predicted hints) | Flatten V1 | 84.00 | 89.14 | 86.88 | 88.38 | 42 |
| POMA Qwen3-8B (no hint predictor) | Flatten V1 | 84.00 | 89.49 | 87.29 | 89.32 | 42 |
| **SEA-LION 8B Q4 CPU + table_ops** | Markdown / prune | **80.00** | **83.70** | **80.00** | **80.00** | **40** |
| Qwen3-8B few-shot | Flatten V1 | 74.00 | 80.69 | 78.00 | 77.92 | 37 |
| Qwen3-8B zero-shot | Flatten V1 | 70.00 | 75.49 | 72.10 | 71.53 | 35 |
| Qwen3-8B task-decomposition | Flatten V1 | 66.00 | 74.42 | 69.00 | 68.04 | 33 |
| Qwen3-8B chain-of-thought | Flatten V1 | 64.00 | 70.77 | 68.48 | 68.20 | 32 |
| SEA-LION 8B Q4 CPU few-shot (LLM only) | Markdown / prune | 62.00 | 76.14 | 68.81 | 68.23 | 31 |

These 50 ids are **not** a stratified sample. Qwen3-8B here is OpenRouter, full Flatten V1, temperature 0. SEA-LION is local llama.cpp Q4_K_M CPU, shorter tables, then `table_ops.py`. POMA still emits multiple surface candidates; SEA-LION+ops does not stuff yes/no/`Null`.

On this slice: operators lift SEA-LION from 62% to 80% EM, above Qwen few-shot (74%) and below POMA (84%).

Partial GPT-4o dumps on this slice (missing ids, no answer normalization): +HP 12/50 scored, EM 41.67; no-HP 41/50 scored, EM 58.54. Not comparable.

## 2. Full test (992) — paper vs files in `outputs/`

Paper numbers are copied from `paper/jit-article.tex` Table `overall-results` (percent). Starred rows are Open-ViTabQA reference systems, not rerun here. Local column = this repo `evaluation/` on the saved json/jsonl.

| System | Paper EM | Paper F1 | Local EM | Local F1 | Local n |
|---|---:|---:|---:|---:|---:|
| Llama 2* | 6.00 | 4.20 | — | — | — |
| Llama 3.1* | 34.30 | 34.20 | — | — | — |
| Mistral 7B v0.3* | 35.00 | 34.90 | — | — | — |
| Mistral Nemo 2407* | 35.60 | 35.50 | — | — | — |
| Gemini 2.0 Flash Exp.* | 60.20 | 60.50 | — | — | — |
| Gemini 1.5 Pro* | 60.80 | 59.80 | — | — | — |
| TAPAS-Large* | 31.44 | 31.56 | — | — | — |
| ViT5-Large* | 45.13 | 45.22 | — | — | — |
| KorWikiTQ* | 46.00 | 46.00 | — | — | — |
| CoAgt (reimpl.) | 32.36 | 68.87 | — | — | no dump in `outputs/` |
| CoQ (reimpl.) | 57.86 | 73.20 | — | — | no dump in `outputs/` |
| Qwen3 8B CoT | 59.17 | 74.03 | 59.48 | 74.01 | 992 |
| Qwen3 8B TD | 59.38 | 74.01 | 59.98 | 74.01 | 992 |
| Qwen3 8B ZS | 62.40 | 76.16 | 63.10 | 76.14 | 992 |
| Qwen3 8B FS | 67.14 | 78.64 | 67.34 | 78.63 | 992 |
| POMA Qwen3 8B | 80.24 | 88.23 | 80.24 | 88.25 | 992 (`…_hp.json`) |
| POMA Qwen3 8B no HP | — | — | 80.34 | 87.91 | 992 |
| SEA-LION 8B + table_ops | — | — | — | — | not run on 992 |

Small paper vs local gaps on the Qwen baselines are rescoring / file-version drift, not a new training run.

## 3. SEA-LION pilots on this VM (not 50)

| Run | n | EM | F1 | Notes |
|---|---:|---:|---:|---|
| `ten` zero-shot + lexical_subtable | 10 | 40.00 | 48.41 | first 10 ids; entity-column prune not yet |
| `ten_v2` few-shot + auto markdown | 10 | 50.00 | 60.91 | same 10 ids |
| `fifty` LLM only | 50 | 62.00 | 76.14 | first 50 |
| `fifty` + table_ops + expand | 50 | 80.00 | 83.70 | first 50; see `RESULTS.md` |

## Prediction files (gitignored)

| Method | Path |
|---|---|
| Qwen ZS / TD / CoT / FS | `outputs/baseline/qwen/full_{zs,td,cot,few_shot}/qwen3-8b.jsonl` |
| POMA Qwen +HP / no HP | `outputs/poma/qwen/poma_qas_test_qwen3_8b_{hp,no_hp}.json` |
| SEA-LION 50 | `outputs/sealion_gguf_cpu/fifty/predictions.jsonl` |
