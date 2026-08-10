param(
    [string]$Model = 'openrouter/qwen/qwen3-8b',
    [string]$OutputDir = 'outputs/baseline',
    [string]$RunId = 'zero-shot-500-stratified',
    [int]$MaxWorkers = 4
)

$ErrorActionPreference = 'Stop'

if ($MaxWorkers -le 0) {
    throw 'MaxWorkers must be positive.'
}

# This committed subset contains 500 seed-20260810 samples selected
# proportionally from dataset/qas_test.json by normalized hint signature.
& python run_baseline.py `
    --qas dataset/qas_test_500_stratified.json `
    --tables dataset/table.json `
    --models $Model `
    --prompt-style zero_shot `
    --limit 500 `
    --max_workers $MaxWorkers `
    --output_dir $OutputDir `
    --id $RunId

if ($LASTEXITCODE -ne 0) {
    throw "Zero-shot run failed with exit code $LASTEXITCODE."
}
