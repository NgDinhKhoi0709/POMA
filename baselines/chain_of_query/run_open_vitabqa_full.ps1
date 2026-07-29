param(
    [string]$Model = "openai/gpt-4o-mini",
    [string]$RunId = "open_vitabqa_test_all",
    [int]$MaxWorkers = 1,
    [int]$Limit = 0,
    [switch]$Overwrite,
    [switch]$SkipEval
)

$ErrorActionPreference = "Stop"
$ScriptDir = (Resolve-Path (Split-Path -Parent $MyInvocation.MyCommand.Path)).Path
$WorkspaceRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$QasPath = Join-Path $WorkspaceRoot "Open_ViTabQA\dataset\qas_test.json"
$TablesPath = Join-Path $WorkspaceRoot "Open_ViTabQA\dataset\table.json"
$OutputDir = Join-Path $ScriptDir "outputs"
$RunDir = Join-Path $OutputDir $RunId

Set-Location $ScriptDir

$runArgs = @(
    "run_open_vitabqa.py",
    "--qas", $QasPath,
    "--tables", $TablesPath,
    "--model", $Model,
    "--output-dir", $OutputDir,
    "--run-id", $RunId,
    "--max-workers", "$MaxWorkers",
    "--resume"
)

if ($Limit -gt 0) {
    $runArgs += @("--limit", "$Limit")
}

if ($Overwrite) {
    $runArgs += "--overwrite"
}

python @runArgs

if (-not $SkipEval) {
    $PredPath = Join-Path $RunDir "results.jsonl"
    $SubsetPath = Join-Path $RunDir "qas_subset.json"
    $EvalDir = Join-Path $RunDir "eval"
    $ReportPath = Join-Path $EvalDir "report.json"
    New-Item -ItemType Directory -Force -Path $EvalDir | Out-Null

    Set-Location $WorkspaceRoot
    python -m Open_ViTabQA.cli run-eval `
        --pred $PredPath `
        --qas $SubsetPath `
        --tables $TablesPath `
        --output $ReportPath `
        --metrics f1,em,rouge1,meteor,answerability_f1,rouge1_by_hint,cost

    Set-Location $ScriptDir
}

Write-Host "Run directory: $RunDir"
