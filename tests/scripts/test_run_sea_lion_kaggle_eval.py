from scripts.run_sea_lion_kaggle_eval import build_parser, resolve_repo_root

def test_parser_defaults_to_pilot_mode():
    args = build_parser().parse_args(["--repo-root", ".", "--output-root", "out"])
    assert args.phase == "pilot"
    assert args.limit is None
    assert args.model == "local/sea-lion-v3-8b-it"

def test_resolve_repo_root_dataset_mode(tmp_path):
    repo = tmp_path / "POMA"
    (repo / "dataset").mkdir(parents=True)
    for name in ("qas_dev.json", "qas_test.json", "table.json"):
        (repo / "dataset" / name).write_text("{}", encoding="utf-8")
    assert resolve_repo_root(repo) == repo
