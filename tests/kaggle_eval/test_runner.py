from src.kaggle_eval.runner import baseline_prediction


def test_baseline_prediction_reads_final_answer_from_schema_payload():
    assert baseline_prediction({"final_answer": "42"}) == ["42"]
