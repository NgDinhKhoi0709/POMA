"""D09 artifact builder: last successful record wins, missing questions are never filled."""

import json

from scripts.build_d09_artifacts import SENTINEL, build_arm, load_records, splice_records


def _line(**row):
    return json.dumps(row, ensure_ascii=False)


def test_failed_attempts_are_ignored_and_a_later_success_wins(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text("\n".join([
        _line(arm="a", qa_id="1", table_id="t", error="Timeout"),
        _line(arm="a", qa_id="1", table_id="t", prediction=["x"]),
        _line(arm="a", qa_id="1", table_id="t", prediction=["y"]),
        _line(arm="b", qa_id="1", table_id="t", error="Timeout"),
    ]) + "\n", encoding="utf-8")
    records = load_records(path)
    assert records["a"]["1"]["prediction"] == ["y"]
    assert "b" not in records


def test_build_arm_keeps_subset_order_and_reports_missing_ids():
    records = {
        "2": {"table_id": "t2", "prediction": ["b"]},
        "1": {"table_id": "t1", "prediction": [3]},
    }
    predictions, missing = build_arm(records, ["1", "2", "3"])
    assert [p["qa_id"] for p in predictions] == ["1", "2"]
    assert predictions[0] == {"qa_id": "1", "table_id": "t1", "prediction": ["3"]}
    assert missing == ["3"]


def test_missing_questions_get_a_sentinel_only_when_table_ids_are_given():
    records = {"1": {"table_id": "t1", "prediction": ["a"]}}
    predictions, missing = build_arm(records, ["1", "2"], table_ids={"1": "t1", "2": "t2"})
    assert missing == ["2"]
    assert predictions[1] == {"qa_id": "2", "table_id": "t2", "prediction": [SENTINEL]}


def test_an_empty_model_answer_counts_as_missing():
    records = {"1": {"table_id": "t1", "prediction": ["  "]}}
    predictions, missing = build_arm(records, ["1"], table_ids={"1": "t1"})
    assert missing == ["1"]
    assert predictions == [{"qa_id": "1", "table_id": "t1", "prediction": [SENTINEL]}]


def test_splice_takes_base_answers_only_for_questions_the_partial_arm_lacks():
    base = {"1": {"prediction": ["a"]}, "2": {"prediction": ["b"]}, "3": {"prediction": ["c"]}}
    partial = {"2": {"prediction": ["B"]}}
    merged, spliced = splice_records(base, partial)
    assert spliced == ["1", "3"]
    assert {k: v["prediction"][0] for k, v in merged.items()} == {"1": "a", "2": "B", "3": "c"}
