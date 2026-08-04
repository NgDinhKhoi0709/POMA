from src.kaggle_eval.jsonl_io import append_jsonl, completed_qa_ids, load_jsonl


def test_append_and_load_jsonl(tmp_path):
    path = tmp_path / "predictions.jsonl"
    append_jsonl(path, {"qa_id": "1", "prediction": ["A"]})
    append_jsonl(path, {"qa_id": "2", "prediction": ["B"]})
    assert load_jsonl(path) == [
        {"qa_id": "1", "prediction": ["A"]},
        {"qa_id": "2", "prediction": ["B"]},
    ]


def test_completed_ids_include_predictions_and_terminal_errors(tmp_path):
    predictions = tmp_path / "predictions.jsonl"
    errors = tmp_path / "errors.jsonl"
    append_jsonl(predictions, {"qa_id": "done", "prediction": ["A"]})
    append_jsonl(errors, {"qa_id": "terminal", "terminal": True, "error_type": "context_overflow"})
    append_jsonl(errors, {"qa_id": "retryable", "terminal": False, "error_type": "network"})
    assert completed_qa_ids(predictions, errors) == {"done", "terminal"}
