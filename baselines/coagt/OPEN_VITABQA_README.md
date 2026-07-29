# Open_ViTabQA Adapter for CoAgt

This adapter keeps the original CoAgt WikiTQ prompts in `utils/agents_prompt_wtq.py` unchanged.
Only the Open_ViTabQA data format, model, temperatures, and chunk size are adapted.

```powershell
python convert_open_vitabqa.py --split mixed --count 5 --output dataset_wtq/open_vitabqa_smoke_5.jsonl --refs-output outputs/open_vitabqa_smoke_5_refs.json
python agent_approach_open_vitabqa.py --input dataset_wtq/open_vitabqa_smoke_5.jsonl --output outputs/open_vitabqa_smoke_5_predictions.jsonl --overwrite
python -m Open_ViTabQA.cli run-eval --qas baselines/CoAgt/outputs/open_vitabqa_smoke_5_refs.json --pred baselines/CoAgt/outputs/open_vitabqa_smoke_5_predictions.jsonl --tables Open_ViTabQA/dataset/table.json --metrics f1,em,rouge1,meteor,answerability_f1,cost --output baselines/CoAgt/outputs/open_vitabqa_smoke_5_eval.json
python make_readable_smoke_json.py --output outputs/open_vitabqa_smoke_5_readable.json
```

Defaults:

- Model: `gpt-4o-mini`
- Collector temperature: `0.2`
- Synthesizer temperature: `0.5`
- Refiner temperature: `0.5` (same as CoAgt WikiTQ script)
- Max token split: `1000`

Run the first 50 questions of `qas_test`:

```powershell
cd baselines/CoAgt
.\run_open_vitabqa_test_limit50.ps1 -MaxWorkers 3
```

The runner also supports limiting an already converted JSONL:

```powershell
python agent_approach_open_vitabqa.py --input dataset_wtq/open_vitabqa_test_50.jsonl --limit 50 --max-workers 3 --resume
```

Results are appended to the prediction JSONL as soon as each question finishes. With `--resume`, already completed `qa_id`s in the prediction/error JSONL files are skipped. Use `-Overwrite` on the PowerShell script only when you want a fresh run.
