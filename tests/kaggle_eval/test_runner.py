from pathlib import Path

from src.kaggle_eval.runner import RunConfig, _dataset_paths, baseline_prediction


def test_baseline_prediction_reads_final_answer_from_schema_payload():
    assert baseline_prediction({"final_answer": "42"}) == ["42"]


def test_baseline_prediction_preserves_json_null_as_no_candidate():
    assert baseline_prediction({"final_answer": None}) == []


def test_full_test_phase_uses_complete_test_dataset(tmp_path: Path) -> None:
    config = RunConfig(
        repo_root=tmp_path,
        output_root=tmp_path / "out",
        phase="test",
        mode="zero_shot",
    )

    qas_path, tables_path = _dataset_paths(config)

    assert qas_path == tmp_path / "dataset" / "qas_test.json"
    assert tables_path == tmp_path / "dataset" / "table.json"
