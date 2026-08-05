# Repository Guidelines

## Project Structure & Module Organization

POMA is a Python 3.9+ research pipeline for Vietnamese table question answering. Core agents, contracts, orchestration, prompts, and LLM services live in `src/`. Table loading and Flatten V1 conversion belong in `preprocessing/`; scoring code belongs in `evaluation/`. Direct-prompt baselines are in `baseline/`, while externally adapted or vendored systems are under `baselines/`. Use `scripts/` for utility and unified baseline entry points. Tests currently live in `tests/baselines/` and mirror the baseline integration modules. Dataset files are versioned in `dataset/`; generated predictions, traces, and reports go under `outputs/`. Treat `paper/`, `docs/`, and `imgs/` as documentation assets rather than runtime code.

## Build, Test, and Development Commands

Use the existing Conda environment `kltn`; do not create another virtual environment. Activate it, then install any missing documented dependencies:

```powershell
conda activate kltn
python -m pip install openai requests beautifulsoup4 python-dotenv pytest
```

Useful checks and entry points:

- `python -m pytest` runs the full automated test suite.
- `python -m pytest tests/baselines/test_contracts.py` runs one focused test module.
- `python run_poma.py --model qwen3-8b --limit 5 --output outputs/poma/smoke.json` performs a small pipeline smoke run.
- `python run_eval.py --pred <predictions.json> --qas dataset/qas_test.json` evaluates saved predictions.
- `python scripts/run_baseline.py --help` lists unified baseline commands; install `baselines/requirements.txt` first.

## Coding Style & Naming Conventions

Follow PEP 8 with four-space indentation. Use `snake_case` for modules, functions, variables, and CLI flags; use `PascalCase` for classes and dataclasses; use `UPPER_SNAKE_CASE` for constants. Keep public functions typed and prefer small, explicit data contracts in `src/contracts/` or `evaluation/contracts.py`. No repository-wide formatter is configured, so preserve nearby formatting and keep imports grouped as standard library, third-party, then local.

## Testing Guidelines

Tests use `pytest`. Name files `test_<feature>.py`, test functions `test_<behavior>()`, and shared fixtures in `conftest.py`. Add regression tests for contract validation, CLI behavior, adapters, and resource cleanup. Tests should avoid live LLM calls; mock providers and use minimal fixtures. There is no formal coverage threshold, but changed behavior should be exercised.

## Commit & Pull Request Guidelines

History follows Conventional Commit prefixes such as `feat:`, `fix:`, `docs:`, and `chore:`. Keep commits focused and write imperative summaries. Pull requests should explain the change, list verification commands, link relevant issues, and note dataset, prompt, or metric impacts. Include sample output paths or screenshots for changed reports or visualizations. Never commit `.env`, API keys, caches, or generated `outputs/`.
