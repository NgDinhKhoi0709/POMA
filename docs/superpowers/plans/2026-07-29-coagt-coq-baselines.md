# CoAgt and Chain-of-Query Baselines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vendor the available CoAgt and Chain-of-Query source into POMA, expose both through one CLI, evaluate normalized outputs with POMA, and complete two-sample GPT-4o-mini smoke runs.

**Architecture:** Keep each baseline in its own vendored directory and preserve its prompt and reasoning source. A POMA-owned runner lazily dispatches to exactly one baseline adapter per process, normalizes the run contract, validates CoQ's mandatory base-SQL fallback label, and calls `evaluation.run.evaluate_files` after inference.

**Tech Stack:** Python 3.10+, argparse, OpenAI Python SDK, SQLite/SQLAlchemy, pytest, POMA evaluation modules, PowerShell smoke commands.

## Global Constraints

- The source of record is `D:\.UIT\KLTN\code\baselines`.
- The real smoke model is exactly `openai/gpt-4o-mini`.
- Run exactly two Open-ViTabQA test records per baseline with `max_workers=1`.
- Preserve the available CoAgt and CoQ prompts and reasoning behavior.
- Do not recreate the unpublished CoQ clause-agent modules.
- CoQ must remain labeled `coq_base_sql_fallback` with a non-empty `fallback_reason`.
- Never copy `.env`, secrets, caches, generated outputs, `tmp/*.db`, or prior experiment artifacts.
- `--resume` and `--overwrite` are mutually exclusive.
- All committed runtime paths must be relative to the POMA repository; the external source path may appear only in provenance documentation.
- Use tests with mocked LLM calls before any paid smoke request.

---

## File Map

### Vendored upstream and adapter source

- `baselines/coagt/`: CoAgt source and its existing Open-ViTabQA adapter.
- `baselines/chain_of_query/`: Chain-of-Query source, bundled Chain-of-Table/MAG-SQL dependencies, and its existing Open-ViTabQA adapter.
- `baselines/coagt/PROVENANCE.md`: origin, retained source, exclusions, and local changes.
- `baselines/chain_of_query/PROVENANCE.md`: origin, public repository, fallback limitation, exclusions, and local changes.
- `baselines/README.md`: shared setup and method-fidelity warning.
- `baselines/requirements.txt`: combined dependencies needed by the two Open-ViTabQA adapters.

### POMA-owned orchestration

- `baselines/__init__.py`: marks the baseline integration package.
- `baselines/contracts.py`: run paths, common prediction contract, validation, and JSON/JSONL helpers.
- `baselines/dispatch.py`: lazy one-baseline-per-process adapter dispatch.
- `scripts/run_baseline.py`: public command-line entry point.

### Tests

- `tests/baselines/conftest.py`: minimal Open-ViTabQA fixtures and fake OpenAI responses.
- `tests/baselines/test_vendored_sources.py`: source manifest and forbidden-artifact checks.
- `tests/baselines/test_contracts.py`: common and method-specific output validation.
- `tests/baselines/test_coagt_adapter.py`: CoAgt conversion, model normalization, run finalization, resume, and error behavior.
- `tests/baselines/test_coq_adapter.py`: CoQ conversion, fallback enforcement, finalization, resume, and error behavior.
- `tests/baselines/test_run_baseline_cli.py`: common CLI, path resolution, evaluation bridge, and exit codes.

### Documentation and generated paths

- `README.md`: installation and baseline commands.
- `.gitignore`: baseline smoke outputs and temporary SQLite files.
- `outputs/baselines/<method>/<run-id>/`: generated results, errors, metadata, QA subset, and evaluation report; never committed.

---

### Task 1: Vendor a clean, auditable source snapshot

**Files:**

- Create: `baselines/__init__.py`
- Create: `baselines/README.md`
- Create: `baselines/coagt/**`
- Create: `baselines/coagt/PROVENANCE.md`
- Create: `baselines/chain_of_query/**`
- Create: `baselines/chain_of_query/PROVENANCE.md`
- Create: `baselines/requirements.txt`
- Create: `tests/baselines/test_vendored_sources.py`
- Modify: `.gitignore`

**Interfaces:**

- Consumes: the two external source directories named in Global Constraints.
- Produces: importable vendored roots at `baselines/coagt` and `baselines/chain_of_query`.

- [ ] **Step 1: Write the failing source-manifest test**

```python
# tests/baselines/test_vendored_sources.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_required_vendored_entrypoints_exist() -> None:
    required = [
        "baselines/coagt/agent_approach_open_vitabqa.py",
        "baselines/coagt/convert_open_vitabqa.py",
        "baselines/coagt/utils/agents_prompt_wtq.py",
        "baselines/coagt/utils/spliter_chunk.py",
        "baselines/chain_of_query/run_open_vitabqa.py",
        "baselines/chain_of_query/convert_open_vitabqa.py",
        "baselines/chain_of_query/utils/pipeline.py",
        "baselines/chain_of_query/utils/reasoner.py",
        "baselines/chain_of_query/utils/agents/base_sql_generator.py",
        "baselines/chain_of_query/LICENSE",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    assert missing == []


def test_vendor_tree_contains_no_runtime_artifacts_or_secrets() -> None:
    vendor_root = ROOT / "baselines"
    forbidden_names = {".env", "__pycache__", ".pytest_cache"}
    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in vendor_root.rglob("*")
        if path.name in forbidden_names
        or path.suffix in {".pyc", ".db"}
        or "outputs" in path.parts
        or "tmp" in path.parts
    ]
    assert offenders == []
```

- [ ] **Step 2: Run the test and verify that the vendored paths are absent**

Run:

```powershell
python -m pytest tests/baselines/test_vendored_sources.py -v
```

Expected: FAIL in `test_required_vendored_entrypoints_exist` with the missing
`baselines/coagt` and `baselines/chain_of_query` paths.

- [ ] **Step 3: Copy the clean CoAgt source set**

Copy these files from `D:\.UIT\KLTN\code\baselines\CoAgt` to
`baselines/coagt`, preserving relative paths:

```text
README.md
OPEN_VITABQA_README.md
requirements
agent_approach_open_vitabqa.py
agent_approach_tabfact.py
agent_approach_wtq.py
convert_open_vitabqa.py
make_readable_smoke_json.py
paper_example_tabfact.txt
paper_example_wikitableQA.txt
tabfact_eval.py
wtq_eval.py
utils/agents_prompt_tabfact.py
utils/agents_prompt_wtq.py
utils/spliter_chunk.py
```

Create an empty `baselines/coagt/utils/__init__.py` so tests can identify the
vendored utility boundary.

- [ ] **Step 4: Copy the clean Chain-of-Query source set**

Copy all source and documentation under
`D:\.UIT\KLTN\code\baselines\ChainofQuery` except:

```text
.env
outputs/**
tmp/**
**/__pycache__/**
**/*.pyc
ChainOfQuery_paper.pdf
chain/data.zip
```

Retain the top-level Apache license, `assets/overview.png`, `chain/`,
`magsql/`, all Open-ViTabQA adapter files, `utils/`, and upstream runner
scripts. Create empty package markers where missing:

```text
baselines/chain_of_query/utils/agents/__init__.py
baselines/chain_of_query/utils/sql/__init__.py
```

- [ ] **Step 5: Add provenance and combined dependencies**

Create `baselines/coagt/PROVENANCE.md` containing:

```markdown
# CoAgt provenance

- Local source snapshot: `D:\.UIT\KLTN\code\baselines\CoAgt`
- Imported for: Open-ViTabQA baseline evaluation in POMA
- Preserved behavior: WikiTQ collector prompts, synthesis, answer refinement
- Excluded: `.env`, generated datasets, outputs, caches, and prior results
- POMA-owned changes: callable adapter, model-prefix normalization, normalized
  run contract, safe resume/overwrite handling, and repository-relative paths
```

Create `baselines/chain_of_query/PROVENANCE.md` containing:

```markdown
# Chain-of-Query provenance

- Local source snapshot: `D:\.UIT\KLTN\code\baselines\ChainofQuery`
- Upstream: https://github.com/SongyuanSui/ChainofQuery
- Imported for: Open-ViTabQA baseline evaluation in POMA
- Excluded: `.env`, generated outputs, temporary SQLite databases, caches,
  `ChainOfQuery_paper.pdf`, and `chain/data.zip`
- Fidelity limitation: the public/local snapshot lacks the clause agents
  imported by `utils/pipeline.py`; runs therefore retain and report the
  existing `coq_base_sql_fallback` behavior
- POMA-owned changes: callable adapter, normalized run contract, safe
  resume/overwrite handling, and repository-relative paths
```

Create `baselines/requirements.txt`:

```text
openai
python-dotenv
tqdm
tiktoken
pandas
records
sqlalchemy
requests
recognizers-text-suite
emoji==1.7.0
fuzzywuzzy
```

- [ ] **Step 6: Ignore generated baseline runtime files**

Append to `.gitignore`:

```gitignore
# Vendored baseline runtime artifacts
outputs/baselines/
baselines/**/tmp/
baselines/**/*.db
```

- [ ] **Step 7: Run the source-manifest and repository checks**

Run:

```powershell
python -m pytest tests/baselines/test_vendored_sources.py -v
git status --short
git diff --check
```

Expected: both tests PASS; `git status` shows only intended source,
documentation, test, requirements, and `.gitignore` changes.

- [ ] **Step 8: Commit the source snapshot**

```powershell
git add .gitignore baselines tests/baselines/test_vendored_sources.py
git commit -m "chore: vendor CoAgt and Chain-of-Query sources"
```

---

### Task 2: Define the shared run and prediction contracts

**Files:**

- Create: `baselines/contracts.py`
- Create: `tests/baselines/conftest.py`
- Create: `tests/baselines/test_contracts.py`

**Interfaces:**

- Produces:
  - `RunPaths.create(output_dir: Path, method: str, run_id: str) -> RunPaths`
  - `validate_prediction(record: Mapping[str, Any], method: str) -> None`
  - `validate_run_records(records: Sequence[Mapping[str, Any]], method: str) -> None`
  - `read_jsonl(path: Path) -> list[dict[str, Any]]`
  - `append_jsonl(path: Path, record: Mapping[str, Any]) -> None`
  - `write_json(path: Path, payload: Any) -> None`

- [ ] **Step 1: Add minimal reusable dataset fixtures**

```python
# tests/baselines/conftest.py
import json
from pathlib import Path

import pytest


@pytest.fixture
def open_vitabqa_files(tmp_path: Path) -> tuple[Path, Path]:
    qas = {
        "qas": [
            {
                "qa_id": "q1",
                "table_id": "t1",
                "question": "Ai đứng đầu bảng?",
                "answer": "An",
                "hints": ["who"],
            },
            {
                "qa_id": "q2",
                "table_id": "t1",
                "question": "Có bao nhiêu người?",
                "answer": "2",
                "hints": ["mathematical_reasoning"],
            },
        ]
    }
    tables = {
        "table": [
            {
                "table_id": "t1",
                "table_title": "Xếp hạng",
                "table_dict": {
                    "table_rows": [["Tên", "Hạng"], ["An", "1"], ["Bình", "2"]]
                },
            }
        ]
    }
    qas_path = tmp_path / "qas.json"
    tables_path = tmp_path / "tables.json"
    qas_path.write_text(json.dumps(qas, ensure_ascii=False), encoding="utf-8")
    tables_path.write_text(json.dumps(tables, ensure_ascii=False), encoding="utf-8")
    return qas_path, tables_path
```

- [ ] **Step 2: Write failing contract tests**

```python
# tests/baselines/test_contracts.py
from pathlib import Path

import pytest

from baselines.contracts import RunPaths, validate_prediction


def common_record() -> dict:
    return {
        "qa_id": "q1",
        "table_id": "t1",
        "question": "Ai đứng đầu bảng?",
        "prediction": "An",
        "answer": "An",
        "model": "gpt-4o-mini",
        "method": "coagt",
        "prompt_tokens": 10,
        "completion_tokens": 2,
        "total_tokens": 12,
        "api_calls": 3,
        "cost_usd": 0.000003,
        "latency_s": 0.2,
        "error": None,
        "num_collectors": 1,
        "temperatures": {
            "collector": 0.2,
            "synthesizer": 0.5,
            "refiner": 0.0,
        },
        "max_chunk_tokens": 1000,
    }


def test_run_paths_reject_unsafe_run_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="run-id"):
        RunPaths.create(tmp_path, "coagt", "../escape")


def test_validate_common_coagt_record() -> None:
    validate_prediction(common_record(), "coagt")


def test_validate_coq_requires_fallback_metadata() -> None:
    record = common_record() | {"method": "coq"}
    with pytest.raises(ValueError, match="pipeline_mode"):
        validate_prediction(record, "coq")


def test_validate_coq_rejects_full_pipeline_label() -> None:
    record = common_record() | {
        "method": "coq",
        "pipeline_mode": "full_chainofquery",
        "fallback_reason": "missing agents",
        "valid_sql": True,
        "final_sql": "SELECT 1",
    }
    with pytest.raises(ValueError, match="coq_base_sql_fallback"):
        validate_prediction(record, "coq")
```

- [ ] **Step 3: Run tests and verify the contract module is missing**

Run:

```powershell
python -m pytest tests/baselines/test_contracts.py -v
```

Expected: collection FAILS with `ModuleNotFoundError:
No module named 'baselines.contracts'`.

- [ ] **Step 4: Implement focused contract helpers**

Implement `baselines/contracts.py` with:

```python
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
COMMON_FIELDS = {
    "qa_id", "table_id", "question", "prediction", "answer", "model",
    "method", "prompt_tokens", "completion_tokens", "total_tokens",
    "api_calls", "cost_usd", "latency_s", "error",
}
COAGT_FIELDS = {"num_collectors", "temperatures", "max_chunk_tokens"}


@dataclass(frozen=True)
class RunPaths:
    root: Path
    results_jsonl: Path
    results_json: Path
    errors_jsonl: Path
    qas_subset: Path
    meta_json: Path
    eval_report: Path

    @classmethod
    def create(cls, output_dir: Path, method: str, run_id: str) -> "RunPaths":
        if method not in {"coagt", "coq"}:
            raise ValueError(f"unsupported baseline method: {method}")
        if not SAFE_RUN_ID.fullmatch(run_id):
            raise ValueError(f"invalid run-id: {run_id!r}")
        root = output_dir.resolve() / method / run_id
        return cls(
            root=root,
            results_jsonl=root / "results.jsonl",
            results_json=root / "results.json",
            errors_jsonl=root / "errors.jsonl",
            qas_subset=root / "qas_subset.json",
            meta_json=root / "meta.json",
            eval_report=root / "eval" / "report.json",
        )


def validate_prediction(record: Mapping[str, Any], method: str) -> None:
    missing = sorted(COMMON_FIELDS - record.keys())
    if missing:
        raise ValueError(f"missing prediction fields: {missing}")
    if str(record["method"]).lower() != method:
        raise ValueError(f"method mismatch: {record['method']!r} != {method!r}")
    for field in ("prompt_tokens", "completion_tokens", "total_tokens", "api_calls"):
        if not isinstance(record[field], int) or record[field] < 0:
            raise ValueError(f"{field} must be a non-negative int")
    for field in ("cost_usd", "latency_s"):
        if not isinstance(record[field], (int, float)) or record[field] < 0:
            raise ValueError(f"{field} must be non-negative")
    if method == "coagt":
        missing_coagt = sorted(COAGT_FIELDS - record.keys())
        if missing_coagt:
            raise ValueError(f"missing CoAgt fields: {missing_coagt}")
    elif method == "coq":
        if record.get("pipeline_mode") != "coq_base_sql_fallback":
            raise ValueError("CoQ pipeline_mode must be coq_base_sql_fallback")
        if not str(record.get("fallback_reason") or "").strip():
            raise ValueError("CoQ fallback_reason must be non-empty")
        for field in ("valid_sql", "final_sql"):
            if field not in record:
                raise ValueError(f"missing CoQ field: {field}")


def validate_run_records(records: Sequence[Mapping[str, Any]], method: str) -> None:
    for record in records:
        validate_prediction(record, method)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False) + "\n")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
```

- [ ] **Step 5: Run contract tests**

Run:

```powershell
python -m pytest tests/baselines/test_contracts.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit the shared contract**

```powershell
git add baselines/contracts.py tests/baselines/conftest.py tests/baselines/test_contracts.py
git commit -m "feat: define baseline run contracts"
```

---

### Task 3: Make the CoAgt adapter callable and contract-compliant

**Files:**

- Modify: `baselines/coagt/convert_open_vitabqa.py`
- Modify: `baselines/coagt/agent_approach_open_vitabqa.py`
- Create: `tests/baselines/test_coagt_adapter.py`

**Interfaces:**

- Consumes:
  - `RunPaths`
  - `open_vitabqa_files`
- Produces:
  - `convert_open_vitabqa(qas_path: Path, tables_path: Path, limit: int | None) -> list[dict[str, Any]]`
  - `normalize_openai_model(model: str) -> str`
  - `run_open_vitabqa(*, qas_path: Path, tables_path: Path, run_paths: RunPaths, model: str, limit: int | None, max_workers: int, resume: bool, overwrite: bool) -> dict[str, Any]`

- [ ] **Step 1: Write failing CoAgt adapter tests**

```python
# tests/baselines/test_coagt_adapter.py
from pathlib import Path

from baselines.contracts import RunPaths, read_jsonl
from baselines.coagt.agent_approach_open_vitabqa import (
    normalize_openai_model,
    run_open_vitabqa,
)
from baselines.coagt.convert_open_vitabqa import convert_open_vitabqa


def test_convert_open_vitabqa_for_coagt(open_vitabqa_files) -> None:
    qas_path, tables_path = open_vitabqa_files
    records = convert_open_vitabqa(qas_path, tables_path, limit=1)
    assert records == [
        {
            "ids": "q1",
            "title": "Xếp hạng",
            "statement": "Ai đứng đầu bảng?",
            "table_text": [["Tên", "Hạng"], ["An", "1"], ["Bình", "2"]],
            "answer": ["An"],
            "table_id": "t1",
            "source_split": "test",
            "hints": ["who"],
        }
    ]


def test_normalize_openai_model() -> None:
    assert normalize_openai_model("openai/gpt-4o-mini") == "gpt-4o-mini"


def test_coagt_mock_run_writes_contract_records(
    open_vitabqa_files, tmp_path: Path, monkeypatch
) -> None:
    qas_path, tables_path = open_vitabqa_files
    paths = RunPaths.create(tmp_path, "coagt", "mock")

    def fake_run_sample(record, **kwargs):
        return {
            "qa_id": record["ids"],
            "key": record["ids"],
            "table_id": record["table_id"],
            "question": record["statement"],
            "response": "phân tích",
            "prediction": "An",
            "answer": "An",
            "model": "gpt-4o-mini",
            "method": "coagt",
            "num_collectors": 1,
            "prompt_tokens": 10,
            "completion_tokens": 2,
            "total_tokens": 12,
            "api_calls": 3,
            "cost_usd": 0.000003,
            "latency_s": 0.1,
            "error": None,
            "stage": "coagt_open_vitabqa",
            "temperatures": {
                "collector": 0.2,
                "synthesizer": 0.5,
                "refiner": 0.0,
            },
            "max_chunk_tokens": 1000,
        }

    monkeypatch.setattr(
        "baselines.coagt.agent_approach_open_vitabqa.run_sample",
        fake_run_sample,
    )
    outcome = run_open_vitabqa(
        qas_path=qas_path,
        tables_path=tables_path,
        run_paths=paths,
        model="openai/gpt-4o-mini",
        limit=1,
        max_workers=1,
        resume=False,
        overwrite=False,
    )
    assert outcome["num_records"] == 1
    assert read_jsonl(paths.results_jsonl)[0]["method"] == "coagt"
    assert paths.meta_json.exists()
```

- [ ] **Step 2: Run tests and verify the callable APIs are missing**

Run:

```powershell
python -m pytest tests/baselines/test_coagt_adapter.py -v
```

Expected: collection FAILS because `convert_open_vitabqa`,
`normalize_openai_model`, and `run_open_vitabqa` do not yet expose the required
signatures.

- [ ] **Step 3: Refactor conversion into a pure function**

In `baselines/coagt/convert_open_vitabqa.py`:

- Retain the existing table conversion rules.
- Add the callable signature from Interfaces.
- Preserve `qa_id`, `table_id`, `question`, `answer`, `hints`, table title,
  header, and rows.
- Keep the existing CLI as a thin wrapper over the pure function.
- Raise
  `KeyError(f"Missing table_id={qa['table_id']} for qa_id={qa['qa_id']}")`
  before inference when a QA references an absent table.

- [ ] **Step 4: Refactor the CoAgt runner without changing prompts**

In `baselines/coagt/agent_approach_open_vitabqa.py`:

1. Change baseline utility imports to package-relative imports:

```python
from .utils.agents_prompt_wtq import (
    prompt_agent_follow,
    prompt_agent_synthesis,
    prompt_answer_refiner,
)
from .utils.spliter_chunk import chunk_table
```

2. Add:

```python
def normalize_openai_model(model: str) -> str:
    value = str(model).strip()
    return value.split("/", 1)[1] if value.startswith("openai/") else value
```

3. Measure latency inside `run_sample`.
4. Add `method="coagt"`, `latency_s`, and `error=None` to successful records.
5. Add `run_open_vitabqa(...)` using `RunPaths`, the pure converter, existing
   `run_sample`, existing retry behavior, immediate JSONL writes, and final
   `results.json`, `qas_subset.json`, and `meta.json`.
6. Use POMA root `.env` with `load_dotenv(project_root / ".env",
   override=False)`.
7. Normalize `openai/gpt-4o-mini` before constructing requests.
8. Keep collector/synthesizer/refiner temperatures `0.2/0.5/0.0` and chunk
   size `1000`.
9. Refuse an occupied run unless `resume` or `overwrite` is selected.
10. Delete only the six known generated files from `RunPaths` during
    overwrite.

- [ ] **Step 5: Add resume and failure tests**

Extend `tests/baselines/test_coagt_adapter.py` with:

```python
def test_coagt_resume_skips_result_and_error_ids(
    open_vitabqa_files, tmp_path: Path, monkeypatch
) -> None:
    qas_path, tables_path = open_vitabqa_files
    paths = RunPaths.create(tmp_path, "coagt", "resume")
    paths.results_jsonl.parent.mkdir(parents=True)
    paths.results_jsonl.write_text('{"qa_id":"q1"}\n', encoding="utf-8")
    paths.errors_jsonl.write_text('{"qa_id":"q2","error":"old"}\n', encoding="utf-8")
    called = []
    monkeypatch.setattr(
        "baselines.coagt.agent_approach_open_vitabqa.run_sample",
        lambda record, **kwargs: called.append(record["ids"]),
    )
    outcome = run_open_vitabqa(
        qas_path=qas_path,
        tables_path=tables_path,
        run_paths=paths,
        model="openai/gpt-4o-mini",
        limit=2,
        max_workers=1,
        resume=True,
        overwrite=False,
    )
    assert called == []
    assert outcome["skipped_existing"] == 2
```

- [ ] **Step 6: Run CoAgt adapter tests**

Run:

```powershell
python -m pytest tests/baselines/test_coagt_adapter.py tests/baselines/test_contracts.py -v
```

Expected: all tests PASS and no network call occurs.

- [ ] **Step 7: Commit the CoAgt adapter**

```powershell
git add baselines/coagt tests/baselines/test_coagt_adapter.py
git commit -m "feat: integrate CoAgt Open-ViTabQA adapter"
```

---

### Task 4: Make the CoQ adapter callable and enforce fallback fidelity

**Files:**

- Modify: `baselines/chain_of_query/convert_open_vitabqa.py`
- Modify: `baselines/chain_of_query/run_open_vitabqa.py`
- Create: `tests/baselines/test_coq_adapter.py`

**Interfaces:**

- Consumes:
  - `RunPaths`
  - `validate_prediction`
- Produces:
  - `convert_open_vitabqa(qas_path: Path, tables_path: Path, limit: int | None) -> list[dict[str, Any]]`
  - `normalize_openai_model(model: str) -> str`
  - `require_fallback_mode(record: Mapping[str, Any]) -> None`
  - `run_open_vitabqa(*, qas_path: Path, tables_path: Path, run_paths: RunPaths, model: str, limit: int | None, max_workers: int, resume: bool, overwrite: bool) -> dict[str, Any]`

- [ ] **Step 1: Write failing CoQ conversion and fidelity tests**

```python
# tests/baselines/test_coq_adapter.py
from pathlib import Path

import pytest

from baselines.chain_of_query.convert_open_vitabqa import convert_open_vitabqa
from baselines.chain_of_query.run_open_vitabqa import require_fallback_mode


def test_convert_open_vitabqa_for_coq(open_vitabqa_files) -> None:
    qas_path, tables_path = open_vitabqa_files
    records = convert_open_vitabqa(qas_path, tables_path, limit=1)
    assert records[0]["qa_id"] == "q1"
    assert records[0]["table_id"] == "t1"
    assert records[0]["question"] == "Ai đứng đầu bảng?"
    assert records[0]["answer"] == "An"
    assert records[0]["hints"] == ["who"]
    assert records[0]["table"]["title"] == "Xếp hạng"


def test_require_fallback_mode_rejects_full_chainofquery() -> None:
    with pytest.raises(RuntimeError, match="coq_base_sql_fallback"):
        require_fallback_mode(
            {
                "pipeline_mode": "full_chainofquery",
                "fallback_reason": "",
            }
        )
```

- [ ] **Step 2: Run the tests and verify `require_fallback_mode` is absent**

Run:

```powershell
python -m pytest tests/baselines/test_coq_adapter.py -v
```

Expected: collection FAILS because `require_fallback_mode` is not defined.

- [ ] **Step 3: Package the CoQ adapter without rewriting upstream agents**

Modify imports in `baselines/chain_of_query/run_open_vitabqa.py` so the adapter
can be imported as `baselines.chain_of_query.run_open_vitabqa` while the
vendored CoQ code continues to resolve its own `utils` package. Use one
baseline per process:

```python
BASELINE_ROOT = Path(__file__).resolve().parent
if str(BASELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(BASELINE_ROOT))
```

Do not import CoAgt in the same process. Do not rename or synthesize any module
listed by `_missing_full_pipeline_modules()`.

- [ ] **Step 4: Add explicit fallback enforcement**

Add:

```python
def require_fallback_mode(record: Mapping[str, Any]) -> None:
    if record.get("pipeline_mode") != "coq_base_sql_fallback":
        raise RuntimeError(
            "CoQ integration requires pipeline_mode=coq_base_sql_fallback "
            "for the available source snapshot"
        )
    if not str(record.get("fallback_reason") or "").strip():
        raise RuntimeError("CoQ fallback_reason must be non-empty")
```

Call it for every successful `_run_one` result and before finalizing
`meta.json`. Set:

```python
meta["pipeline_mode"] = "coq_base_sql_fallback"
meta["fallback_reason"] = results[0]["fallback_reason"] if results else (
    "Missing full pipeline modules: " + ", ".join(_missing_full_pipeline_modules())
)
```

- [ ] **Step 5: Normalize the common CoQ output contract**

Keep all current SQL and log fields, and add:

```python
"method": "coq",
"error": None,
```

Successful records go to `results.jsonl`; failed records go to
`errors.jsonl`. The callable runner receives `RunPaths`, writes
`qas_subset.json`, `results.json`, and `meta.json`, and preserves existing
resume behavior.

An occupied run without `resume` or `overwrite` raises
`FileExistsError`. Overwrite removes only the generated files described by
`RunPaths`.

- [ ] **Step 6: Add a mocked contract-compliant CoQ run test**

```python
def test_coq_mock_run_preserves_fallback(
    open_vitabqa_files, tmp_path: Path, monkeypatch
) -> None:
    from baselines.contracts import RunPaths, read_jsonl
    from baselines.chain_of_query import run_open_vitabqa as module

    qas_path, tables_path = open_vitabqa_files
    paths = RunPaths.create(tmp_path, "coq", "mock")

    def fake_run_one(record, **kwargs):
        return {
            "qa_id": record["qa_id"],
            "key": record["qa_id"],
            "table_id": record["table_id"],
            "question": record["question"],
            "response": "An",
            "prediction": "An",
            "answer": record["answer"],
            "model": "gpt-4o-mini",
            "method": "coq",
            "prompt_tokens": 10,
            "completion_tokens": 2,
            "total_tokens": 12,
            "api_calls": 2,
            "cost_usd": 0.000003,
            "latency_s": 0.1,
            "error": None,
            "pipeline_mode": "coq_base_sql_fallback",
            "fallback_reason": "Missing full pipeline modules: column_selector",
            "valid_sql": True,
            "final_sql": 'SELECT "Tên" FROM "Xếp hạng" LIMIT 1',
            "log": {"sqls": []},
        }

    monkeypatch.setattr(module, "_run_one", fake_run_one)
    module.run_open_vitabqa(
        qas_path=qas_path,
        tables_path=tables_path,
        run_paths=paths,
        model="openai/gpt-4o-mini",
        limit=1,
        max_workers=1,
        resume=False,
        overwrite=False,
    )
    record = read_jsonl(paths.results_jsonl)[0]
    assert record["pipeline_mode"] == "coq_base_sql_fallback"
    assert record["fallback_reason"]
```

- [ ] **Step 7: Run CoQ tests**

Run:

```powershell
python -m pytest tests/baselines/test_coq_adapter.py tests/baselines/test_contracts.py -v
```

Expected: all tests PASS without OpenAI requests or temporary databases left
under the repository.

- [ ] **Step 8: Commit the CoQ adapter**

```powershell
git add baselines/chain_of_query tests/baselines/test_coq_adapter.py
git commit -m "feat: integrate Chain-of-Query fallback adapter"
```

---

### Task 5: Add the common CLI and automatic POMA evaluation

**Files:**

- Create: `baselines/dispatch.py`
- Create: `scripts/run_baseline.py`
- Create: `tests/baselines/test_run_baseline_cli.py`

**Interfaces:**

- Consumes:
  - CoAgt and CoQ `run_open_vitabqa(...)`
  - `evaluation.run.evaluate_files(...)`
- Produces:
  - `dispatch_run(method: str, **kwargs) -> dict[str, Any]`
  - `build_parser() -> argparse.ArgumentParser`
  - `main(argv: Sequence[str] | None = None) -> int`

- [ ] **Step 1: Write failing CLI parser tests**

```python
# tests/baselines/test_run_baseline_cli.py
import pytest

from scripts.run_baseline import build_parser


def test_cli_defaults_to_gpt4o_mini_and_one_worker() -> None:
    args = build_parser().parse_args(["coagt", "--limit", "2"])
    assert args.model == "openai/gpt-4o-mini"
    assert args.max_workers == 1


def test_cli_rejects_resume_with_overwrite() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["coq", "--resume", "--overwrite"])
```

- [ ] **Step 2: Run tests and verify the common CLI is absent**

Run:

```powershell
python -m pytest tests/baselines/test_run_baseline_cli.py -v
```

Expected: collection FAILS with `ModuleNotFoundError:
No module named 'scripts.run_baseline'`.

- [ ] **Step 3: Implement lazy dispatch**

Create `baselines/dispatch.py`:

```python
from __future__ import annotations

from typing import Any


def dispatch_run(method: str, **kwargs: Any) -> dict[str, Any]:
    if method == "coagt":
        from baselines.coagt.agent_approach_open_vitabqa import run_open_vitabqa
    elif method == "coq":
        from baselines.chain_of_query.run_open_vitabqa import run_open_vitabqa
    else:
        raise ValueError(f"unsupported baseline: {method}")
    return run_open_vitabqa(**kwargs)
```

Do not import both adapters at module import time; CoQ intentionally retains
its top-level vendored `utils` imports.

- [ ] **Step 4: Implement the CLI parser and safe path resolution**

Create `scripts/run_baseline.py` with:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METRICS = (
    "f1", "em", "rouge1", "meteor", "answerability_f1", "cost"
)
```

Add the positional method choice and common options from the approved design.
Use one mutually exclusive argparse group:

```python
mode = parser.add_mutually_exclusive_group()
mode.add_argument("--resume", action="store_true")
mode.add_argument("--overwrite", action="store_true")
```

Resolve relative `--qas`, `--tables`, and `--output-dir` against
`PROJECT_ROOT`. Reject `--limit <= 0` and `--max-workers <= 0`.

- [ ] **Step 5: Add preflight and evaluation behavior**

In `main()`:

1. Load `PROJECT_ROOT / ".env"` with `override=False`.
2. Fail with exit code `2` when `OPENAI_API_KEY` is missing.
3. Construct `RunPaths`.
4. Call `dispatch_run`.
5. Load and validate successful results.
6. If successful results exist and `--skip-eval` is false, call:

```python
evaluate_files(
    paths.results_jsonl,
    paths.qas_subset,
    tables_path=tables_path,
    output_path=paths.eval_report,
    metrics=list(DEFAULT_METRICS),
    fail_on_metric_error=True,
)
```

7. Return `1` when the adapter reports any selected QA failure; otherwise
   return `0`.
8. Print paths to results, errors, metadata, and evaluation report without
   printing environment values.

- [ ] **Step 6: Add a mocked end-to-end CLI test**

```python
def test_cli_dispatches_and_evaluates(
    open_vitabqa_files, tmp_path, monkeypatch
) -> None:
    from scripts import run_baseline

    qas_path, tables_path = open_vitabqa_files
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_dispatch(method, **kwargs):
        paths = kwargs["run_paths"]
        paths.root.mkdir(parents=True, exist_ok=True)
        paths.results_jsonl.write_text(
            '{"qa_id":"q1","table_id":"t1","question":"Ai đứng đầu bảng?",'
            '"prediction":"An","answer":"An","model":"gpt-4o-mini",'
            f'"method":"{method}","prompt_tokens":10,"completion_tokens":2,'
            '"total_tokens":12,"api_calls":1,"cost_usd":0.000003,'
            '"latency_s":0.1,"error":null,"num_collectors":1,'
            '"temperatures":{"collector":0.2,"synthesizer":0.5,'
            '"refiner":0.0},"max_chunk_tokens":1000}\n',
            encoding="utf-8",
        )
        paths.qas_subset.write_text(
            '{"qas":[{"qa_id":"q1","table_id":"t1",'
            '"question":"Ai đứng đầu bảng?","answer":"An","hints":["who"]}]}',
            encoding="utf-8",
        )
        return {"num_records": 1, "num_errors": 0}

    monkeypatch.setattr(run_baseline, "dispatch_run", fake_dispatch)
    exit_code = run_baseline.main(
        [
            "coagt",
            "--qas", str(qas_path),
            "--tables", str(tables_path),
            "--output-dir", str(tmp_path / "out"),
            "--run-id", "mock",
            "--limit", "1",
        ]
    )
    assert exit_code == 0
    assert (tmp_path / "out/coagt/mock/eval/report.json").exists()
```

- [ ] **Step 7: Run CLI and evaluator tests**

Run:

```powershell
python -m pytest tests/baselines/test_run_baseline_cli.py tests/baselines -v
```

Expected: all baseline tests PASS with no paid request.

- [ ] **Step 8: Commit the common runner**

```powershell
git add baselines/dispatch.py scripts/run_baseline.py tests/baselines/test_run_baseline_cli.py
git commit -m "feat: add unified baseline runner"
```

---

### Task 6: Document setup, fidelity, and reproducible commands

**Files:**

- Modify: `README.md`
- Modify: `baselines/README.md`
- Modify: `baselines/coagt/OPEN_VITABQA_README.md`
- Modify: `baselines/chain_of_query/OPEN_VITABQA_README.md`

**Interfaces:**

- Consumes: the public CLI from Task 5.
- Produces: copy-pasteable install, smoke, resume, overwrite, and evaluation
  guidance.

- [ ] **Step 1: Add a documentation assertion test**

Append to `tests/baselines/test_vendored_sources.py`:

```python
def test_root_readme_documents_both_baseline_smokes() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "scripts/run_baseline.py coagt" in text
    assert "scripts/run_baseline.py coq" in text
    assert "coq_base_sql_fallback" in text
```

- [ ] **Step 2: Run the assertion and verify it fails**

Run:

```powershell
python -m pytest tests/baselines/test_vendored_sources.py::test_root_readme_documents_both_baseline_smokes -v
```

Expected: FAIL because the root README does not yet document the new runner.

- [ ] **Step 3: Add the root Baselines section**

Document:

```powershell
python -m pip install -r baselines/requirements.txt

python scripts/run_baseline.py coagt `
  --model openai/gpt-4o-mini `
  --limit 2 `
  --max-workers 1 `
  --run-id smoke-gpt4o-mini

python scripts/run_baseline.py coq `
  --model openai/gpt-4o-mini `
  --limit 2 `
  --max-workers 1 `
  --run-id smoke-gpt4o-mini
```

Explain generated paths, `--resume`, `--overwrite`, `--skip-eval`, required
`OPENAI_API_KEY`, and the fact that available CoQ code runs
`coq_base_sql_fallback`.

- [ ] **Step 4: Replace external-workspace commands in vendored adapter docs**

Update both `OPEN_VITABQA_README.md` files to use:

- POMA-root paths
- `python scripts/run_baseline.py ...`
- `outputs/baselines/...`
- the POMA evaluator output location

Preserve upstream citations and explicitly separate upstream commands from
POMA adapter commands.

- [ ] **Step 5: Run documentation and diff checks**

Run:

```powershell
python -m pytest tests/baselines/test_vendored_sources.py -v
git diff --check
```

Expected: PASS and no whitespace errors.

- [ ] **Step 6: Commit documentation**

```powershell
git add README.md baselines/README.md baselines/coagt/OPEN_VITABQA_README.md baselines/chain_of_query/OPEN_VITABQA_README.md tests/baselines/test_vendored_sources.py
git commit -m "docs: document CoAgt and CoQ baseline runs"
```

---

### Task 7: Verify tests and perform the two paid smoke runs

**Files:**

- Generate, do not commit:
  - `outputs/baselines/coagt/smoke-gpt4o-mini/**`
  - `outputs/baselines/coq/smoke-gpt4o-mini/**`
- Modify only if verification exposes a defect:
  - the smallest responsible source/test file from Tasks 1-6

**Interfaces:**

- Consumes: completed CLI, adapters, evaluation bridge, POMA `.env`.
- Produces: verified two-sample run artifacts for both methods.

- [ ] **Step 1: Install and validate baseline dependencies**

Run:

```powershell
python -m pip install -r baselines/requirements.txt
python -c "import openai, pandas, records, sqlalchemy, tiktoken, recognizers_suite, fuzzywuzzy; print('baseline dependencies OK')"
```

Expected: the import command prints `baseline dependencies OK`.

- [ ] **Step 2: Run the full mocked test suite**

Run:

```powershell
python -m pytest tests/baselines -v
```

Expected: all tests PASS and no network request occurs.

- [ ] **Step 3: Run regression checks for existing POMA entry points**

Run:

```powershell
python run_poma.py --help
python run_baseline.py --help
python run_eval.py --help
```

Expected: each command exits `0` and displays its existing help.

- [ ] **Step 4: Confirm paid-smoke preconditions without exposing secrets**

Run:

```powershell
python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); print('OPENAI_API_KEY configured' if os.getenv('OPENAI_API_KEY') else 'OPENAI_API_KEY missing')"
```

Expected: `OPENAI_API_KEY configured`. Do not print the key.

- [ ] **Step 5: Run the two-sample CoAgt smoke**

Run:

```powershell
python scripts/run_baseline.py coagt `
  --model openai/gpt-4o-mini `
  --limit 2 `
  --max-workers 1 `
  --run-id smoke-gpt4o-mini `
  --overwrite
```

Expected:

- exit code `0` only if both QA records succeed
- `results.jsonl` contains two valid CoAgt records
- `meta.json` reports `selected_records=2`, `num_records=2`,
  `num_errors=0`
- `eval/report.json` exists

- [ ] **Step 6: Validate the CoAgt smoke artifacts**

Run:

```powershell
python -c "import json, pathlib; p=pathlib.Path('outputs/baselines/coagt/smoke-gpt4o-mini'); rows=[json.loads(x) for x in (p/'results.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]; meta=json.loads((p/'meta.json').read_text(encoding='utf-8')); report=json.loads((p/'eval/report.json').read_text(encoding='utf-8')); assert len(rows)==2; assert all(r['method']=='coagt' for r in rows); assert meta['num_errors']==0; assert len(report['coverage']['evaluated_ids'])==2; print('CoAgt smoke OK')"
```

Expected: `CoAgt smoke OK`.

- [ ] **Step 7: Run the two-sample CoQ smoke**

Run:

```powershell
python scripts/run_baseline.py coq `
  --model openai/gpt-4o-mini `
  --limit 2 `
  --max-workers 1 `
  --run-id smoke-gpt4o-mini `
  --overwrite
```

Expected:

- exit code `0` only if both QA records succeed
- `results.jsonl` contains two valid CoQ fallback records
- `meta.json` reports `pipeline_mode=coq_base_sql_fallback`
- `eval/report.json` exists

- [ ] **Step 8: Validate the CoQ fidelity and evaluation artifacts**

Run:

```powershell
python -c "import json, pathlib; p=pathlib.Path('outputs/baselines/coq/smoke-gpt4o-mini'); rows=[json.loads(x) for x in (p/'results.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]; meta=json.loads((p/'meta.json').read_text(encoding='utf-8')); report=json.loads((p/'eval/report.json').read_text(encoding='utf-8')); assert len(rows)==2; assert all(r['pipeline_mode']=='coq_base_sql_fallback' and r['fallback_reason'] for r in rows); assert meta['pipeline_mode']=='coq_base_sql_fallback'; assert len(report['coverage']['evaluated_ids'])==2; print('CoQ fallback smoke OK')"
```

Expected: `CoQ fallback smoke OK`.

- [ ] **Step 9: Check repository cleanliness and generated-file isolation**

Run:

```powershell
git status --short
git diff --check
git check-ignore outputs/baselines/coagt/smoke-gpt4o-mini/results.jsonl
git check-ignore outputs/baselines/coq/smoke-gpt4o-mini/results.jsonl
```

Expected:

- generated smoke files are ignored
- no `.env`, `.db`, cache, or generated output is staged
- only intentional source/test/documentation fixes, if any, remain

- [ ] **Step 10: Record final evidence for handoff**

Capture in the final handoff:

- pytest command and passed test count
- CoAgt and CoQ smoke exit codes
- exact output directories
- selected/success/error counts
- evaluation coverage count
- CoQ `pipeline_mode` and non-empty fallback reason
- total token and cost fields from each `meta.json`
- `git status --short`

Do not report a baseline as successfully integrated when its real smoke command
returned non-zero or its artifact validation failed.
