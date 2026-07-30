# Gemma-only load throttling design

## Problem

Gemma POMA can receive HTTP 429 responses from the shared DeepInfra upstream
pool. The current POMA batch worker count is one, but specialist execution
inside each QA can issue up to ten concurrent requests. Gemma direct baselines
also default to four concurrent QA workers.

The throttling must apply only to Gemma. Qwen concurrency and experiment
commands must remain unchanged.

## Runtime configuration

Do not add throttling variables to the project `.env`, because those values
would also affect Qwen processes.

In the Gemma-only Anaconda Prompt block, set:

```bat
set "POMA_PARALLEL_WORKERS=1"
set "POMA_LLM_RETRY_DELAY=30"
```

Run Gemma direct baselines with:

```text
--max_workers 1
```

Run Gemma POMA with:

```text
--workers 1
```

Gemma finalizers already default to one worker. They inherit the 30-second
retry delay from the Gemma terminal environment.

## Isolation

The Qwen sections of the runbook retain their existing defaults:

- direct baseline QA workers: four;
- POMA batch workers: one;
- POMA internal specialist limit: ten unless the user explicitly overrides it.

Gemma should run in a separate terminal. Closing that terminal removes the
Gemma-only environment overrides. If the same terminal must later run Qwen,
clear the overrides first:

```bat
set "POMA_PARALLEL_WORKERS="
set "POMA_LLM_RETRY_DELAY="
```

## Failure and resume behavior

Throttling reduces request bursts but cannot eliminate an upstream shared-pool
overload. If all retries still return 429:

1. stop that command;
2. wait before retrying;
3. rerun the same baseline or POMA command;
4. preserve existing JSONL artifacts so completed QAs are skipped.

No provider, model, prompt, schema, dataset, or output path changes are part of
this design.

## Verification

- Run `tests/scripts/test_q2_runbook.py`.
- Run `git diff --check` for the runbook.
- Confirm the Qwen commands do not contain the Gemma throttling flags.
- Confirm the Gemma baseline command contains `--max_workers 1`.
- Confirm the Gemma POMA command contains `--workers 1`.
- Confirm the Gemma setup and cleanup commands scope both environment variables
  to the Gemma terminal.
