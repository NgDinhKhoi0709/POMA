param(
    [ValidateSet('DryRun','Preflight','Full')]
    [string]$Phase = 'DryRun',
    [int]$PreflightLimit = 5,
    [string]$OutputRoot = 'outputs/q2_revision'
)

$ErrorActionPreference = 'Stop'

# Evaluation policy: raw direct baselines and GSA use --candidate-policy single-required;
# Answer Normalization uses --candidate-policy all; diagnostic POMA reports use
# --candidate-policy first. Backbone analysis always uses --bootstrap-samples 10000
# and --seed 20260729.

$models = @(
    [PSCustomObject]@{
        Id = 'openrouter/qwen/qwen3-8b'
        Slug = 'openrouter_qwen_qwen3-8b'
    },
    [PSCustomObject]@{
        Id = 'openrouter/google/gemma-3-4b-it'
        Slug = 'openrouter_google_gemma-3-4b-it'
    }
)

$directGenerators = @(
    [PSCustomObject]@{ Name = 'zero_shot'; PromptStyle = 'zero_shot' },
    [PSCustomObject]@{ Name = 'cot'; PromptStyle = 'cot' },
    [PSCustomObject]@{ Name = 'task_decomposition'; PromptStyle = 'task_decomposition' },
    [PSCustomObject]@{ Name = 'few_shot'; PromptStyle = 'few_shot' }
)

function Invoke-RunbookCommand {
    param([string[]]$Command)

    $display = ($Command | ForEach-Object {
        "'{0}'" -f ($_ -replace "'", "''")
    }) -join ' '
    Write-Host $display

    if ($Phase -eq 'DryRun') {
        return
    }

    & $Command[0] @($Command[1..($Command.Count - 1)])
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $display"
    }
}

function Assert-ImmutablePaths {
    param(
        [string]$Source,
        [string]$Output
    )

    if ($Source -eq $Output) {
        throw "Finalizer source and output must be distinct: $Source"
    }
}

if ($PreflightLimit -le 0) {
    throw 'PreflightLimit must be positive.'
}

$datasetQas = 'dataset/qas_test.json'
$tables = 'dataset/table.json'
$limit = 992
$qas = $datasetQas

if ($Phase -eq 'Preflight') {
    $limit = $PreflightLimit
    $qas = Join-Path $OutputRoot 'preflight/qas_limit_5.json'
}

if ($Phase -ne 'DryRun') {
    New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
}

if ($Phase -eq 'Preflight') {
    Invoke-RunbookCommand @(
        'python', 'scripts/create_qas_subset.py',
        '--input', $datasetQas,
        '--output', $qas,
        '--size', [string]$limit,
        '--seed', '20260729'
    )
}

foreach ($model in $models) {
    $backboneRoot = Join-Path $OutputRoot $model.Slug
    $rawRoot = Join-Path $backboneRoot 'raw'
    $finalRoot = Join-Path $backboneRoot 'finalized'
    $reportsRoot = Join-Path $backboneRoot 'reports'

    foreach ($generator in $directGenerators) {
        $rawDirectory = Join-Path $rawRoot $generator.Name
        $rawSource = Join-Path $rawDirectory "$($model.Slug).jsonl"
        $anCommon = Join-Path $finalRoot "$($generator.Name)_an-common.json"
        $gsa = Join-Path $finalRoot "$($generator.Name)_gsa.json"

        Invoke-RunbookCommand @(
            'python', 'run_baseline.py',
            '--qas', $qas,
            '--tables', $tables,
            '--models', $model.Id,
            '--prompt-style', $generator.PromptStyle,
            '--limit', [string]$limit,
            '--output_dir', $rawRoot,
            '--id', $generator.Name,
            '--no-eval'
        )

        Invoke-RunbookCommand @(
            'python', 'run_eval.py',
            '--qas', $qas,
            '--pred', $rawSource,
            '--output', (Join-Path $reportsRoot "$($generator.Name)_raw.json"),
            '--candidate-policy', 'single-required',
            '--fail-on-metric-error'
        )

        Assert-ImmutablePaths -Source $rawSource -Output $anCommon
        Invoke-RunbookCommand @(
            'python', 'scripts/run_finalizer.py',
            '--source', $rawSource,
            '--source-kind', 'direct-baseline',
            '--finalizer', 'an-common',
            '--qas', $qas,
            '--tables', $tables,
            '--model', $model.Id,
            '--provider', 'openrouter',
            '--output', $anCommon,
            '--limit', [string]$limit
        )

        Invoke-RunbookCommand @(
            'python', 'run_eval.py',
            '--qas', $qas,
            '--pred', $anCommon,
            '--output', (Join-Path $reportsRoot "$($generator.Name)_an-common.json"),
            '--candidate-policy', 'all',
            '--fail-on-metric-error'
        )

        Assert-ImmutablePaths -Source $rawSource -Output $gsa
        Invoke-RunbookCommand @(
            'python', 'scripts/run_finalizer.py',
            '--source', $rawSource,
            '--source-kind', 'direct-baseline',
            '--finalizer', 'gsa',
            '--qas', $qas,
            '--tables', $tables,
            '--model', $model.Id,
            '--provider', 'openrouter',
            '--output', $gsa,
            '--limit', [string]$limit
        )

        Invoke-RunbookCommand @(
            'python', 'run_eval.py',
            '--qas', $qas,
            '--pred', $gsa,
            '--output', (Join-Path $reportsRoot "$($generator.Name)_gsa.json"),
            '--candidate-policy', 'single-required',
            '--fail-on-metric-error'
        )
    }

    $pomaRaw = Join-Path $rawRoot 'poma.json'
    $pomaTraces = Join-Path $rawRoot 'poma_traces.json'
    $pomaAnCommon = Join-Path $finalRoot 'poma_an-common.json'
    $pomaAnNative = Join-Path $finalRoot 'poma_an-native.json'
    $pomaGsa = Join-Path $finalRoot 'poma_gsa.json'

    Invoke-RunbookCommand @(
        'python', 'run_poma.py',
        '--qas', $qas,
        '--tables', $tables,
        '--model', $model.Id,
        '--limit', [string]$limit,
        '--output', $pomaRaw,
        '--no-eval'
    )

    Invoke-RunbookCommand @(
        'python', 'run_eval.py',
        '--qas', $qas,
        '--pred', $pomaRaw,
        '--output', (Join-Path $reportsRoot 'poma_diagnostic.json'),
        '--candidate-policy', 'first',
        '--fail-on-metric-error'
    )

    foreach ($finalizer in @(
        [PSCustomObject]@{ Name = 'an-common'; Output = $pomaAnCommon },
        [PSCustomObject]@{ Name = 'an-native'; Output = $pomaAnNative },
        [PSCustomObject]@{ Name = 'gsa'; Output = $pomaGsa }
    )) {
        Assert-ImmutablePaths -Source $pomaTraces -Output $finalizer.Output
        Invoke-RunbookCommand @(
            'python', 'scripts/run_finalizer.py',
            '--source', $pomaTraces,
            '--source-kind', 'poma-specialists',
            '--finalizer', $finalizer.Name,
            '--qas', $qas,
            '--tables', $tables,
            '--model', $model.Id,
            '--provider', 'openrouter',
            '--output', $finalizer.Output,
            '--limit', [string]$limit
        )

        $candidatePolicy = if ($finalizer.Name -eq 'gsa') {
            'single-required'
        } else {
            'all'
        }
        Invoke-RunbookCommand @(
            'python', 'run_eval.py',
            '--qas', $qas,
            '--pred', $finalizer.Output,
            '--output', (Join-Path $reportsRoot "poma_$($finalizer.Name).json"),
            '--candidate-policy', $candidatePolicy,
            '--fail-on-metric-error'
        )
    }

    Invoke-RunbookCommand @(
        'python', 'scripts/run_revision_analysis.py',
        '--system', "poma-an-native=$pomaAnNative",
        '--system', "few-shot-gsa=$(Join-Path $finalRoot 'few_shot_gsa.json')",
        '--primary-system', 'poma-an-native',
        '--baseline-system', 'few-shot-gsa',
        '--qas', $qas,
        '--poma-traces', $pomaTraces,
        '--bootstrap-samples', '10000',
        '--seed', '20260729',
        '--output', (Join-Path $reportsRoot 'revision_analysis.json')
    )
}
