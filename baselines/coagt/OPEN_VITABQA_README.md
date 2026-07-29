# CoAgt adapter for Open-ViTabQA

This adapter retains the vendored CoAgt WikiTQ prompts and reasoning stages,
while converting POMA's Open-ViTabQA records to the expected input shape.

From the POMA repository root:

```powershell
python -m pip install -r baselines\requirements.txt
python scripts/run_baseline.py coagt --model openai/gpt-4o-mini --limit 2 --max-workers 1 --run-id smoke-gpt4o-mini --overwrite
```

`OPENAI_API_KEY` is loaded from the process environment or the repository
`.env`. The CoAgt defaults preserve the source configuration:

- collector temperature: `0.2`
- synthesizer temperature: `0.5`
- refiner temperature: `0.5`
- maximum chunk size: `1000` tokens

Results and POMA evaluation metrics are written below
`outputs/baselines/coagt/<run-id>/`. Use `--resume` to continue a partial run.
The output contract records the collector count, stage temperatures, token
usage, estimated API cost, latency, and any error.
