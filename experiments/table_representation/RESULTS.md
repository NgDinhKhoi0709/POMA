# SEA-LION 8B sandbox results

Logged 2026-09-17. Code and scores live in this folder so they survive `outputs/` being gitignored. Predictions, traces, and GGUF weights stay under `outputs/` and `~/.cache` and are **not** committed.

## Protocol

| Knob | Value |
|---|---|
| Split | First 50 items of `dataset/qas_test.json` in file order |
| Cherry-pick | No |
| Model | `aisingapore/Llama-SEA-LION-v3-8B-IT-GGUF` Q4_K_M |
| Runtime | llama.cpp CPU, `n_gpu_layers=0`, `n_ctx=8192`, `temperature=0` |
| Host | Cloud VM, no GPU, ~15 GB RAM |
| Table | `--table-mode auto`: full Markdown if ≤5000 chars, else `lexical_subtable` (`max_rows=24`, `max_cols=8`) |
| Prompt | `--prompt-style few_shot` Vietnamese TableQA (lookup / yes-no pair / count / null) |
| Scoring | `python3 run_eval.py --pred <jsonl> --qas dataset/qas_test.json --metrics em,f1` (policy `all`) |
| Candidate stuffing | Not used. No universal extra `Null` / `Có` / `Không` |

Machine-readable copy: `samples/sealion_fifty/summary.json` and `samples/sealion_fifty/items.json`.

Reproduce (needs the GGUF on disk; this VM already scored the 50):

```bash
python -m experiments.table_representation.run_sealion_gguf \
    --limit 50 --table-mode auto --prompt-style few_shot \
    --output outputs/sealion_gguf_cpu/fifty
python3 run_eval.py --pred outputs/sealion_gguf_cpu/fifty/predictions.jsonl \
    --qas dataset/qas_test.json --metrics em,f1
```

## Method

1. **Serialize.** Small tables stay Markdown. Large tables shrink with query-aware column-then-row overlap (`PRUNING.md`), keeping one entity column and grouped thousands.
2. **Generate.** SEA-LION chat completion, JSON `final_answer` only. Yes/No wording is canonicalized to the question pair (`Phải/Không`, `Có/Không`, `Đúng/Không`).
3. **Table operators** (`table_ops.py`), question-gated, computed on the parsed grid. They **replace** the LLM answer when they fire. Yes/No, why, and “bao nhiêu” stay with the model.
   - `frequency_rank` — “nhiều thứ N” / “phổ biến thứ N”: N-th most common non-numeric body value.
   - `list_rows` — “Liệt kê …”: target column from the question, rows filtered by cell values or year mentioned in the question.
   - `climate_extremum` — “Khi nào / tháng nào … cao|thấp nhất” on a month-header climate table.
   - `filtered_extremum` — min/max over rows whose cell text appears in the question (city, country, …).
4. **Grounded expand** (`expand_candidates`): year ↔ `Năm YYYY`; copy a parenthetical span that already occurs in the question (`23` → `23 (UHF/VHF)`); unanswerable phrases → `Null`; if a yes/no question was answered with a copied cell, also add the **positive** pair word. Both polarities are never added.

## Scores (n=50)

| Stage | Hits | EM | F1 |
|---|---:|---:|---:|
| Raw 8B JSON | 31 | 0.62 | 0.76 |
| + operators + expand | **40** | **0.80** | **0.84** |

No previously-correct item was flipped to a miss.

### Where the extra 9 hits came from

Operators (6):

| qa_id | op | LLM | Final = gold |
|---|---|---|---|
| `99910_4_53` | `frequency_rank` | HV | TV |
| `99932_0_36` | `list_rows` | list with extra “Cặp đôi hoàn hảo” | Running Man wins only |
| `99928_0_98` | `list_rows` | missing Lương Bích Hữu | 2023 singers |
| `99922_2_82` | `climate_extremum` | 12 | 7 (month of max humidity) |
| `48_3_142` | `filtered_extremum` | Al Noor Tower | Atlantic Tower (min floors, Casablanca) |
| `99928_2_78` | `filtered_extremum` | Maan Al-Sanea | Sulaiman Al Rajhi (min wealth, Saudi) |

Expand only (3): `1_3_292` `1709`→`Năm 1709`; `29_2_148` `23`→`23 (UHF/VHF)`; `55_2_132` copied `SNG.INV`→also `Đúng`.

### Remaining 10 misses (LLM, no operator)

| qa_id | Type | Pred | Gold |
|---|---|---|---|
| `3_1_104` | multi-condition count | 0 | 7 |
| `6_2_85` | count | 3 | 32 |
| `48_1_5` | count | 2 | 0 |
| `9990_2_27` | yes/no arithmetic | Không | Có |
| `23_1_26` | yes/no over rows | Có | Không |
| `99925_0_14` | unanswerable vs Không | Không | Null |
| `99924_1_53` | unanswerable who | Tý | Null |
| `9994_0_49` | why | Không đủ thông tin | Vì Nguyễn Thị Kim Ngân nặng nhất đội |
| `99911_4_159` | year lookup | 2009 | 2005 |
| `99913_1_20` | month equality | null | 12 |

Count / yes-no / why / unanswerable are left to the 8B on purpose so EM is not gamed.

## What is not saved here

- `outputs/sealion_gguf_cpu/fifty/` — jsonl, traces, `metrics.json` (gitignored)
- GGUF weights under `~/.cache/poma-models/`
- Production Flatten V1 / POMA prompts (unchanged)
