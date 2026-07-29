# Vendored baselines

This directory contains source snapshots of CoAgt and Chain-of-Query plus
POMA-owned Open-ViTabQA adapters. See each `PROVENANCE.md` for the source and
local modifications. The upstream prompts and reasoning code are retained;
the adapters only bridge the POMA dataset, run contract, and evaluator.

Install the shared dependencies from the repository root:

```powershell
python -m pip install -r baselines\requirements.txt
```

Set `OPENAI_API_KEY` in `.env` or the process environment, then use the unified
runner:

```powershell
python scripts/run_baseline.py coagt --model openai/gpt-4o-mini --limit 2 --max-workers 1 --run-id smoke-gpt4o-mini --overwrite
python scripts/run_baseline.py coq --model openai/gpt-4o-mini --limit 2 --max-workers 1 --run-id smoke-gpt4o-mini --overwrite
```

Defaults are `dataset/qas_test.json`, `dataset/table.json`,
`openai/gpt-4o-mini`, and one worker. Output is written to
`outputs/baselines/<method>/<run-id>/`:

- `results.jsonl` and `results.json`: successful predictions
- `errors.jsonl`: failed samples
- `qas_subset.json`: evaluation references
- `meta.json`: run metadata and counts
- `eval/report.json`: POMA evaluation metrics

Use `--resume` to continue a partially completed run or `--overwrite` to start
the named run again. The two options are mutually exclusive.

## Chain-of-Query limitation

The available Chain-of-Query snapshot does not publish the clause-agent
modules used by the full paper pipeline (`column_selector`, `withas`,
`row_selector`, `aggfunc1`, `aggfunc2`, `order1`, and `order2`). Its adapter
therefore runs the upstream base SQL generator only. Every successful record
is explicitly labeled `pipeline_mode: "coq_base_sql_fallback"` with a non-empty
`fallback_reason`. Do not present these outputs as full Chain-of-Query results.
