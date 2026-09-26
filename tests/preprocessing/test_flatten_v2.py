"""Flatten V2: Flatten V1 minus columns that are empty in every body row; citations are kept."""

from preprocessing.variants import render_flatten_v2

HTML = (
    "<table>"
    "<tr><th>Tên</th><th>Hình</th><th>Diện tích</th><th>Nguồn</th></tr>"
    '<tr><td>Hà Nội<sup class="reference">[1]</sup></td><td><img src="a.png"/></td><td>3</td><td>[2]</td></tr>'
    "<tr><td>Huế</td><td></td><td>5</td><td></td></tr>"
    "</table>"
)


def test_only_originally_empty_columns_are_dropped():
    assert render_flatten_v2({"table_html": HTML}).splitlines() == [
        "Tên <header>|Diện tích <header>|Nguồn <header>",
        "Hà Nội[1]|3|[2]",
        "Huế|5|",
    ]
