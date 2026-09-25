"""Regression tests for the cell-text separator fix in ``HTMLTableParser``.

A cell whose HTML holds several blocks used to be read with ``get_text()``, gluing the blocks
together with nothing between them. The corruption reached every table representation, and the model
was then scored wrong for faithfully quoting the cell it had been shown. The real case that exposed
it is test question ``0_0_8``: the flattened cell read ``Dân chủ Kitô giáoQuốc gia: CDU`` while the
gold answer was ``Dân chủ Kitô giáo``.
"""

from __future__ import annotations

import importlib

import pytest

from preprocessing.parser import HTMLTableParser


def cells(html: str) -> list[str]:
    parsed = HTMLTableParser().parse(f"<table><tr>{html}</tr></table>")
    row = (parsed.headers + parsed.rows)[0]
    return [str(cell.value) for cell in row]


class TestBlocksInsideOneCell:
    def test_br_becomes_a_space(self):
        assert cells("<td>Dân chủ Kitô giáo<br/>Quốc gia: CDU</td>") == ["Dân chủ Kitô giáo Quốc gia: CDU"]

    def test_nested_divs_become_a_space(self):
        assert cells("<td><div>Walter Hallstein</div><div>Ủy ban Hallstein</div></td>") == [
            "Walter Hallstein Ủy ban Hallstein"
        ]

    def test_paragraphs_become_a_space(self):
        assert cells("<td><p>Hà Nội</p><p>Việt Nam</p></td>") == ["Hà Nội Việt Nam"]

    def test_list_items_become_a_space(self):
        assert cells("<td><ul><li>Hà Nội</li><li>Huế</li></ul></td>") == ["Hà Nội Huế"]

    def test_header_cells_get_the_same_treatment(self):
        assert cells("<th>Dân số<br/>(2019)</th>") == ["Dân số (2019)"]


class TestNoRegressionOnOrdinaryCells:
    @pytest.mark.parametrize(
        "html,expected",
        [
            ("<td>Hà Nội</td>", "Hà Nội"),
            ("<td>  Hà   Nội  </td>", "Hà Nội"),
            ("<td>8.000.000</td>", "8.000.000"),
            ("<td></td>", ""),
            ("<td><b>Hà</b> Nội</td>", "Hà Nội"),
        ],
    )
    def test_plain_cells_are_unchanged(self, html, expected):
        assert cells(html) == [expected]


class TestInlineMarkupMustNotBeSplit:
    """The first attempt used ``get_text(" ")`` and split these too; it lost 21 test questions.

    Each case below is taken from a question that regression broke, so they are the tests that
    would have caught it before the A/B run was paid for.
    """

    def test_links_around_a_slash_stay_joined(self):
        assert cells("<td>Iese/<a>Hãn Ali-Quli</a>/<a>Mustafa Pasha</a></td>") == [
            "Iese/Hãn Ali-Quli/Mustafa Pasha"
        ]

    def test_punctuation_in_its_own_span_stays_attached(self):
        assert cells("<td>xã Dĩnh Trì<span>,</span> thành phố Bắc Giang</td>") == [
            "xã Dĩnh Trì, thành phố Bắc Giang"
        ]

    def test_superscript_footnote_stays_attached(self):
        assert cells("<td>Hà Nội<sup>[1]</sup></td>") == ["Hà Nội[1]"]

    def test_parenthetical_with_a_slash_is_untouched(self):
        assert cells("<td>12 (<abbr>UHF</abbr>/<abbr>VHF</abbr>)</td>") == ["12 (UHF/VHF)"]

    def test_emphasis_inside_a_word_stays_joined(self):
        assert cells("<td>Bắc<i>Giang</i></td>") == ["BắcGiang"]

    def test_several_cells_stay_separate(self):
        assert cells("<td>Hà Nội</td><td>Huế</td>") == ["Hà Nội", "Huế"]


def test_legacy_env_var_restores_the_old_behaviour(monkeypatch):
    """The A/B switch must still reproduce pre-fix strings, or the comparison run is meaningless."""
    import preprocessing.parser as parser

    monkeypatch.setenv("POMA_LEGACY_CELL_TEXT", "1")
    reloaded = importlib.reload(parser)
    try:
        parsed = reloaded.HTMLTableParser().parse(
            "<table><tr><td>Dân chủ Kitô giáo<br/>Quốc gia: CDU</td></tr></table>"
        )
        assert str((parsed.headers + parsed.rows)[0][0].value) == "Dân chủ Kitô giáoQuốc gia: CDU"
    finally:
        monkeypatch.delenv("POMA_LEGACY_CELL_TEXT", raising=False)
        importlib.reload(parser)
