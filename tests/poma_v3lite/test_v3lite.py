from __future__ import annotations

import pytest

from poma_v3lite.answerability import run_gate
from poma_v3lite.formatter import format_answer, format_candidates
from poma_v3lite.table_search import render_rows, search_rows

TABLE = {
    "table_html": (
        "<table><tr><th>Tỉnh</th><th>Dân số</th></tr>"
        "<tr><td>Hà Nội</td><td>8.000.000</td></tr>"
        "<tr><td>Đà Nẵng</td><td>1.200.000</td></tr>"
        "<tr><td>Cần Thơ</td><td>1.300.000</td></tr></table>"
    )
}


class TestFormatter:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("**Hà Nội**", "Hà Nội"),
            ("`8.000.000`", "8.000.000"),
            ('"Đà Nẵng"', "Đà Nẵng"),
            ("“Cần Thơ”", "Cần Thơ"),
            ("Đáp án là: Hà Nội", "Hà Nội"),
            ("Câu trả lời: 42", "42"),
            ("Hà Nội[1]", "Hà Nội"),
            ("  Hà   Nội  ", "Hà Nội"),
            ("Có.", "Có"),
            ("Có,", "Có"),
        ],
    )
    def test_removes_formatting_noise(self, raw, expected):
        assert format_answer(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "  ", "Null", "none", "N/A"])
    def test_nullish_becomes_null(self, raw):
        assert format_answer(raw) == "Null"

    def test_keeps_decimal_and_thousands_separators_untouched(self):
        # Gold uses both "." and "," as the decimal mark, so no rewrite is safe.
        assert format_answer("138.3") == "138.3"
        assert format_answer("138,3") == "138,3"
        assert format_answer("1.400.012") == "1.400.012"

    def test_keeps_units_untouched(self):
        assert format_answer("2 năm") == "2 năm"

    def test_does_not_strip_an_internal_apostrophe(self):
        assert format_answer("Xã Ea H'leo") == "Xã Ea H'leo"

    def test_candidates_drop_nulls_and_dedupe_preserving_order(self):
        assert format_candidates(["**Hà Nội**", "Null", "Hà Nội", "Đà Nẵng"]) == ["Hà Nội", "Đà Nẵng"]


class TestTableSearch:
    def test_finds_row_by_diacritic_insensitive_name(self):
        assert search_rows(TABLE, ["da nang"]) == [2]

    def test_ranks_by_coverage_and_returns_table_order(self):
        assert search_rows(TABLE, ["Hà Nội", "Cần Thơ"]) == [1, 3]

    def test_returns_empty_when_nothing_matches(self):
        assert search_rows(TABLE, ["Sơn La"]) == []

    def test_render_keeps_header_and_selected_rows_only(self):
        rendered = render_rows(TABLE, [2])
        assert rendered.splitlines() == ["Tỉnh <header> | Dân số <header>", "Đà Nẵng | 1.200.000"]


class TestGate:
    def test_does_not_fire_on_a_real_answer(self):
        def boom(*_args):
            raise AssertionError("must not call the model")

        result = run_gate("Dân số Hà Nội?", TABLE, "8.000.000", generate_json=boom)
        assert (result.fired, result.answer) == (False, "8.000.000")

    def test_recovers_a_false_null(self):
        calls = []

        def fake(prompt, _schema, step):
            calls.append(step)
            if step == "IdentifyMissingEvidence":
                return {"needed_evidence": ["Đà Nẵng"]}
            assert "Đà Nẵng | 1.200.000" in prompt
            return {"answerable": True, "final_answer": "**1.200.000**"}

        result = run_gate("Dân số Đà Nẵng?", TABLE, "Null", generate_json=fake)
        assert (result.answer, result.changed, result.calls) == ("1.200.000", True, 2)
        assert calls == ["IdentifyMissingEvidence", "ReAnswerOrConfirmNull"]

    def test_confirms_a_true_null(self):
        def fake(_prompt, _schema, step):
            if step == "IdentifyMissingEvidence":
                return {"needed_evidence": ["Hà Nội"]}
            return {"answerable": False, "final_answer": "Null"}

        result = run_gate("GDP Hà Nội?", TABLE, "Null", generate_json=fake)
        assert (result.answer, result.changed, result.fired) == ("Null", False, True)

    def test_keeps_null_when_no_row_matches(self):
        def fake(_prompt, _schema, step):
            assert step == "IdentifyMissingEvidence"
            return {"needed_evidence": ["Sơn La"]}

        result = run_gate("Dân số Sơn La?", TABLE, "Null", generate_json=fake)
        assert (result.answer, result.rows_found, result.calls) == ("Null", 0, 1)

    def test_keeps_null_when_the_model_errors(self):
        def fake(*_args):
            raise RuntimeError("timeout")

        result = run_gate("Dân số Đà Nẵng?", TABLE, "Null", generate_json=fake)
        assert result.answer == "Null" and result.error.startswith("RuntimeError")

    def test_empty_answer_is_treated_as_null_and_gated(self):
        def fake(_prompt, _schema, step):
            if step == "IdentifyMissingEvidence":
                return {"needed_evidence": ["Cần Thơ"]}
            return {"answerable": True, "final_answer": "1.300.000"}

        assert run_gate("Dân số Cần Thơ?", TABLE, "", generate_json=fake).answer == "1.300.000"
