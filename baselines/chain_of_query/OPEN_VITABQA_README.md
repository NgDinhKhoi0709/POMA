# Chain-of-Query adapter for Open-ViTabQA

This directory contains the vendored Chain-of-Query source and POMA's
Open-ViTabQA adapter.

From the POMA repository root:

```powershell
python -m pip install -r baselines\requirements.txt
python scripts/run_baseline.py coq --model openai/gpt-4o-mini --limit 2 --max-workers 1 --run-id smoke-gpt4o-mini --overwrite
```

`OPENAI_API_KEY` is loaded from the process environment or the repository
`.env`. Results and POMA evaluation metrics are written below
`outputs/baselines/coq/<run-id>/`; use `--resume` to continue a partial run.

## Required interpretation

The available source snapshot lacks the clause-agent modules imported by the
full paper pipeline: `column_selector`, `withas`, `row_selector`, `aggfunc1`,
`aggfunc2`, `order1`, and `order2`. The adapter consequently executes the
upstream base SQL generator and always labels successful records:

```json
{
  "method": "coq",
  "pipeline_mode": "coq_base_sql_fallback",
  "fallback_reason": "Full clause-agent modules are unavailable in the vendored source."
}
```

These outputs are a base-SQL fallback baseline, not full Chain-of-Query
results. The run contract rejects records that omit this disclosure or claim a
full pipeline.
