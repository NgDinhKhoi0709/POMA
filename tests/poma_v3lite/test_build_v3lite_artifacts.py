from __future__ import annotations

import pytest

from scripts.build_v3lite_artifacts import SENTINEL, build_arm, candidates_for, index_solver

QA_IDS = ["q1", "q2", "q3"]
TABLE_IDS = {"q1": "t1", "q2": "t2", "q3": "t3"}

SOLVER = index_solver([
    {"arm": "control", "qa_id": "q1", "raw_prediction": ["**Hà Nội**"]},
    {"arm": "control", "qa_id": "q2", "raw_prediction": ["Null"]},
    {"arm": "control", "qa_id": "q3", "raw_prediction": ["Huế"]},
    # H1 only changed q3's table, so only q3 has a treated record.
    {"arm": "v3lite", "qa_id": "q3", "raw_prediction": ["Đà Nẵng"]},
    {"arm": "v3lite", "qa_id": "q1", "raw_prediction": ["ignored"], "error": "boom"},
])
GATE = {"q2": {"qa_id": "q2", "prediction": ["1.200.000"], "changed": True}}


class TestCandidates:
    def test_control_keeps_raw_text(self):
        assert candidates_for("control", "q1", SOLVER, GATE) == (["**Hà Nội**"], "control")

    def test_formatter_arm_cleans_the_same_record(self):
        assert candidates_for("control_fmt", "q1", SOLVER, GATE) == (["Hà Nội"], "control")

    def test_h1_uses_the_treated_record_when_present(self):
        assert candidates_for("h1", "q3", SOLVER, GATE) == (["Đà Nẵng"], "h1")

    def test_h1_splices_control_when_the_table_was_unchanged(self):
        assert candidates_for("h1", "q1", SOLVER, GATE) == (["**Hà Nội**"], "spliced")

    def test_failed_treated_record_is_ignored_and_spliced(self):
        # q1's v3lite record carries an error, so index_solver dropped it.
        assert ("v3lite", "q1") not in SOLVER

    def test_gate_replaces_a_null(self):
        answers, source = candidates_for("v3lite", "q2", SOLVER, GATE)
        assert answers == ["1.200.000"] and source.endswith("+gate")

    def test_ungated_question_falls_back_to_the_formatted_answer(self):
        assert candidates_for("v3lite", "q1", SOLVER, GATE) == (["Hà Nội"], "spliced")


class TestBuildArm:
    def test_covers_every_qa_in_order(self):
        payload = build_arm("control", QA_IDS, TABLE_IDS, SOLVER, GATE)
        assert [p["qa_id"] for p in payload["predictions"]] == QA_IDS
        assert payload["manifest"]["count"] == 3

    def test_each_prediction_has_exactly_one_answer(self):
        payload = build_arm("v3lite", QA_IDS, TABLE_IDS, SOLVER, GATE)
        assert all(len(p["prediction"]) == 1 for p in payload["predictions"])

    def test_null_survives_as_null_when_the_gate_confirms_it(self):
        payload = build_arm("control_fmt", QA_IDS, TABLE_IDS, SOLVER, {})
        assert payload["predictions"][1]["prediction"] == ["Null"]

    def test_empty_answer_becomes_the_sentinel_and_is_listed(self):
        solver = index_solver([
            {"arm": "control", "qa_id": "q1", "raw_prediction": []},
            {"arm": "control", "qa_id": "q2", "raw_prediction": ["x"]},
            {"arm": "control", "qa_id": "q3", "raw_prediction": ["y"]},
        ])
        payload = build_arm("control", QA_IDS, TABLE_IDS, solver, {})
        assert payload["predictions"][0]["prediction"] == [SENTINEL]
        assert payload["manifest"]["missing_or_empty"] == ["q1"]

    def test_sources_are_counted_for_provenance(self):
        payload = build_arm("h1", QA_IDS, TABLE_IDS, SOLVER, GATE)
        assert payload["manifest"]["sources"] == {"spliced": 2, "h1": 1}


def test_index_solver_drops_failed_records():
    rows = [{"arm": "control", "qa_id": "q1", "prediction": ["a"], "error": "x"}]
    assert index_solver(rows) == {}
