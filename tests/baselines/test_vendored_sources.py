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
