from src.kaggle_eval.table_preview import build_table_preview


class _WordTokenizer:
    def encode(self, text):
        return text.split()


def test_short_table_is_returned_unchanged():
    table = "TITLE: Demo\nHEADER: a | b\nrow 1: x | y"

    assert build_table_preview(table, tokenizer=_WordTokenizer(), max_tokens=100) == table


def test_long_preview_keeps_title_header_whole_rows_and_omission_marker():
    rows = "\n".join(f"row {i}: c1={i} | c2=value-{i}" for i in range(1, 31))
    table = "TITLE: Demo\nHEADER: c1 | c2\n" + rows

    preview = build_table_preview(table, tokenizer=_WordTokenizer(), max_tokens=90)

    assert "TITLE: Demo" in preview
    assert "HEADER: c1 | c2" in preview
    assert "row 1:" in preview
    assert "row 30:" in preview
    assert "OMITTED_ROWS" in preview
    assert "\nrow " in preview
    assert len(_WordTokenizer().encode(preview)) <= 90
