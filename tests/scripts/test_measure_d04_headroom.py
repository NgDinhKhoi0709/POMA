"""D04 headroom split must separate format-only errors from value errors."""

from scripts.measure_d04_headroom import numeric_error_split


def test_numeric_error_split_categories():
    qas = [{"qa_id": k, "answer": a} for k, a in
           {"a": "138,3", "b": "7", "c": "5", "d": "3", "e": "Hà Nội"}.items()]
    answers = {k: {"prediction": [v]} for k, v in
               {"a": "138.3", "b": "10", "c": "Null", "d": "3", "e": "x"}.items()}
    ok = {"a": False, "b": False, "c": False, "d": True, "e": False}
    assert numeric_error_split(qas, answers, ok) == {
        "wrong": 3,
        "same_number_different_format": 1,
        "wrong_value": 1,
        "no_numeric_prediction": 1,
    }
