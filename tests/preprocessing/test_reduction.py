"""H1 row selection: what is kept, and every condition that must return the full table."""

from preprocessing.reduction import reduce_table, select_rows
from preprocessing.variants import Grid, render_v1

ROWS = [(f"Đội {i}", f"Thành phố {chr(65 + i)}", str(1000 + i)) for i in range(30)]
HTML = (
    "<table><tr><th>Đội</th><th>Nơi</th><th>Số</th></tr>"
    + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in ROWS)
    + "</table>"
)
TABLE = {"table_id": "t", "table_html": HTML}
LONG = lambda text: 5000  # noqa: E731
SHORT = lambda text: 100  # noqa: E731


def test_short_tables_are_returned_in_full():
    result = reduce_table(TABLE, "Đội 7 ở thành phố nào", k=5, token_count=SHORT)
    assert (result.reduced, result.reason) == (False, "short_table")
    assert result.text == render_v1(Grid.from_table_data(TABLE))


def test_aggregation_cues_keep_the_whole_table():
    for question in ("Có bao nhiêu đội ở thành phố A", "Đội nào có số cao nhất", "Tổng số của đội 3 và đội 4"):
        assert reduce_table(TABLE, question, k=5, token_count=LONG).reason == "aggregation_cue", question


def test_reduction_keeps_header_matching_rows_in_original_order_and_a_note():
    result = reduce_table(TABLE, "Đội 7 thuộc thành phố nào", k=3, token_count=LONG)
    assert result.reduced and result.rows_total == 30
    lines = result.text.split("\n")
    assert lines[0] == "Đội <header>|Nơi <header>|Số <header>"
    assert "Đội 7|Thành phố H|1007" in lines
    body = [line for line in lines[1:-1]]
    assert len(body) == result.rows_kept <= 6
    assert body == sorted(body, key=lambda line: int(line.split("|")[2]))
    assert lines[-1] == "[Ghi chú: bảng gốc có 30 hàng dữ liệu; chỉ hiển thị %d hàng liên quan đến câu hỏi.]" % result.rows_kept


def test_a_row_naming_an_entity_is_kept_even_when_it_ranks_below_top_k():
    body = [list(row) for row in ROWS]
    kept = select_rows(body, "Thành phố H là quê của đội nào", 1)
    assert 7 in kept


def test_no_lexical_overlap_falls_back_to_the_full_table():
    result = reduce_table(TABLE, "zzz qqq xxx", k=3, token_count=LONG)
    assert (result.reduced, result.reason) == (False, "no_lexical_signal")


def test_keeping_most_of_the_table_is_not_a_reduction():
    result = reduce_table(TABLE, "Đội 7 thuộc thành phố nào", k=28, token_count=LONG)
    assert (result.reduced, result.reason) == (False, "few_rows")


# --- reduction on a compact serializer (pipe arms) -------------------------------------------------------


def test_default_arm_is_still_flatten_v1():
    assert reduce_table(TABLE, "Đội 7", k=3, token_count=LONG).text == reduce_table(
        TABLE, "Đội 7", k=3, token_count=LONG, arm="v1_raw"
    ).text


def test_pipe_arm_returns_exactly_the_pipe_string_when_nothing_is_reduced():
    from preprocessing.variants import render_table

    result = reduce_table(TABLE, "Đội 7 thuộc thành phố nào", k=3, token_count=SHORT, arm="pipe_clean")
    assert not result.reduced
    assert result.text == render_table(TABLE, "pipe_clean")  # byte-identical, so splicing from the control is valid
    assert "<header>" not in result.text


def test_pipe_arm_reduction_has_no_header_tag_and_keeps_the_header_row():
    result = reduce_table(TABLE, "Đội 7 thuộc thành phố nào", k=3, token_count=LONG, arm="pipe_clean")
    lines = result.text.split("\n")
    assert result.reduced and "<header>" not in result.text
    assert lines[0] == "Đội|Nơi|Số"
    assert "Đội 7|Thành phố H|1007" in lines
    assert lines[-1].startswith("[Ghi chú: bảng gốc có 30 hàng dữ liệu")


def test_gate_is_measured_on_the_string_that_is_sent():
    seen = []

    def count(text):
        seen.append(text)
        return 100

    reduce_table(TABLE, "Đội 7", k=3, token_count=count, arm="pipe_clean")
    assert seen and all("<header>" not in text for text in seen)


def test_pipe_nohdr_arm_reduces_under_the_labelled_schema_line():
    result = reduce_table(TABLE, "Đội 7 thuộc thành phố nào", k=3, token_count=LONG, arm="pipe_nohdr")
    lines = result.text.split("\n")
    assert result.reduced and lines[0] == "Cột: Đội|Nơi|Số"
    assert "Đội 7|Thành phố H|1007" in lines


def test_reduction_ranks_on_the_cleaned_body():
    html = (
        "<table><tr><th>Tên</th><th>Số</th><th>Nguồn</th></tr>"
        + "".join(f"<tr><td>Mục {i}</td><td>{i}</td><td></td></tr>" for i in range(30))
        + "</table>"
    )
    result = reduce_table({"table_id": "c", "table_html": html}, "Mục 7", k=3, token_count=LONG, arm="pipe_clean")
    assert result.reduced and result.text.split("\n")[0] == "Tên|Số"  # the empty column was dropped first
