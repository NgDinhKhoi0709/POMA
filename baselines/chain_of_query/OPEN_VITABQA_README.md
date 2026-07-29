# ChainofQuery on Open_ViTabQA

This directory contains the upstream ChainofQuery repository plus a local Open_ViTabQA adapter.

## Upstream

- Repository: https://github.com/SongyuanSui/ChainofQuery.git
- Pinned smoke commit: `f8102c30155ef24e99a883e8f31611286fdb4d90`
- Local path: `baselines/ChainofQuery`

## Local adapter files

- `convert_open_vitabqa.py`: converts `Open_ViTabQA/dataset/qas_test.json` and `table.json` to ChainofQuery-shaped records.
- `run_open_vitabqa.py`: runs the upstream Chain-of-Query pipeline and writes evaluator-compatible `results.json`/`results.jsonl`.
- `run_open_vitabqa_full.ps1`: full-run PowerShell script with resume enabled by default.
- `.env.example`: documents the required `OPENAI_API_KEY`.

## Dependencies

The upstream `requirements.txt` omits a few imported packages. For this workspace smoke run, install:

```powershell
python -m pip install -r baselines\ChainofQuery\requirements.txt records sqlalchemy tiktoken requests recognizers-text-suite emoji==1.7.0 fuzzywuzzy
```

The upstream repository at the pinned commit does not include the full clause-agent modules imported by `utils.pipeline` (`column_selector`, `withas`, `row_selector`, and related files). The local runner therefore marks smoke outputs with `pipeline_mode: "coq_base_sql_fallback"` and uses the upstream `utils/agents/base_sql_generator.py` path. Full Chain-of-Query comparison requires obtaining those missing upstream agent files or replacing the fallback with an equivalent clause-agent implementation.

## Conversion smoke

```powershell
python baselines\ChainofQuery\convert_open_vitabqa.py `
  --qas Open_ViTabQA\dataset\qas_test.json `
  --tables Open_ViTabQA\dataset\table.json `
  --output run_test\ChainofQuery\data\open_vitabqa_test.json `
  --limit 3
```

## Inference smoke

```powershell
python baselines\ChainofQuery\run_open_vitabqa.py `
  --qas Open_ViTabQA\dataset\qas_test.json `
  --tables Open_ViTabQA\dataset\table.json `
  --model openai/gpt-4o-mini `
  --output-dir run_test\ChainofQuery `
  --run-id smoke-gpt4o-mini `
  --limit 3 `
  --max-workers 1 `
  --resume
```

Expected output:

- `run_test/ChainofQuery/smoke-gpt4o-mini/input_open_vitabqa.json`
- `run_test/ChainofQuery/smoke-gpt4o-mini/qas_subset.json`
- `run_test/ChainofQuery/smoke-gpt4o-mini/results.json`
- `run_test/ChainofQuery/smoke-gpt4o-mini/results.jsonl`
- `run_test/ChainofQuery/smoke-gpt4o-mini/meta.json`

## Evaluation smoke

```powershell
python -m Open_ViTabQA.cli run-eval `
  --pred run_test\ChainofQuery\smoke-gpt4o-mini\results.jsonl `
  --qas run_test\ChainofQuery\smoke-gpt4o-mini\qas_subset.json `
  --tables Open_ViTabQA\dataset\table.json `
  --output run_test\ChainofQuery\smoke-gpt4o-mini\eval\report.json `
  --metrics f1,em,rouge1,meteor,answerability_f1,rouge1_by_hint,cost
```

## Output contract

Each result record includes:

- `qa_id`
- `key`
- `table_id`
- `source_split`
- `question`
- `response`
- `prediction`
- `answer`
- `model`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `api_calls`
- `cost_usd`
- `stage`
- `method`
- `pipeline_mode`
- `fallback_reason`
- `valid_sql`
- `final_sql`
- `latency_s`
- `error`

Token/cost fields follow the CoAgt Open_ViTabQA adapter format. Pricing defaults to `gpt-4o-mini` OpenAI rates:

- input: `$0.15 / 1M tokens`
- output: `$0.60 / 1M tokens`

Override with `OPENAI_INPUT_USD_PER_1M` and `OPENAI_OUTPUT_USD_PER_1M` when running a different pricing table.

## Resume behavior

`run_open_vitabqa.py` supports CoAgt-style resume:

- `results.jsonl` is appended after each successful QA.
- `errors.jsonl` is appended for failed QA records.
- `--resume` skips `qa_id`s already present in either JSONL file.
- `--overwrite` deletes prior result/error/meta files before running.
- `results.json` and `meta.json` are regenerated from `results.jsonl` at the end of every run.

Resume metadata is written to `meta.json`: `selected_records`, `pending_records`, `existing_done_ids`, `skipped_existing`, and `skipped_duplicate_input`.

## Full run

Use the provided script. It saves outputs inside `baselines/ChainofQuery/outputs/<run-id>/` and enables resume by default.

```powershell
baselines\ChainofQuery\run_open_vitabqa_full.ps1 -MaxWorkers 3
```

Useful variants:

```powershell
# Resume or continue the default full run
baselines\ChainofQuery\run_open_vitabqa_full.ps1 -MaxWorkers 3

# Fresh full run
baselines\ChainofQuery\run_open_vitabqa_full.ps1 -MaxWorkers 3 -Overwrite

# Development slice
baselines\ChainofQuery\run_open_vitabqa_full.ps1 -RunId open_vitabqa_test_50 -Limit 50 -MaxWorkers 3

# Skip evaluation after inference
baselines\ChainofQuery\run_open_vitabqa_full.ps1 -MaxWorkers 3 -SkipEval
```

`-MaxWorkers N` controls how many questions are processed concurrently. Start with `3`; reduce it if the API rate limit is hit.
