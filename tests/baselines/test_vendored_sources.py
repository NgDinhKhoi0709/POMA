from pathlib import Path
import subprocess


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
    forbidden_names = {".env", "__pycache__", ".pytest_cache"}
    tracked = subprocess.run(
        ["git", "ls-files", "baselines"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    offenders = [
        value
        for value in tracked
        for path in [Path(value)]
        if path.name in forbidden_names
        or path.suffix in {".pyc", ".db"}
        or "outputs" in path.parts
        or "tmp" in path.parts
    ]
    assert offenders == []


def test_readmes_document_unified_runner_and_coq_fallback() -> None:
    readmes = [
        ROOT / "README.md",
        ROOT / "baselines" / "README.md",
        ROOT / "baselines" / "coagt" / "OPEN_VITABQA_README.md",
        ROOT / "baselines" / "chain_of_query" / "OPEN_VITABQA_README.md",
    ]
    for readme in readmes:
        text = readme.read_text(encoding="utf-8")
        assert "scripts/run_baseline.py" in text

    coq_docs = "\n".join(
        readme.read_text(encoding="utf-8") for readme in readmes
    )
    assert "coq_base_sql_fallback" in coq_docs
