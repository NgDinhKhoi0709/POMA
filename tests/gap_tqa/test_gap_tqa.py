from gap_tqa import nodes
from gap_tqa.graphs import State, run_graph
from gap_tqa.router import gold_class, route
from gap_tqa.table import Table

HTML = (
    "<table><tr><th rowspan='2'>Tỉnh</th><th colspan='2'>Dân số</th></tr>"
    "<tr><th>2019</th><th>2024</th></tr>"
    "<tr><td>Đà Nẵng</td><td>1.134</td><td>1.245</td></tr>"
    "<tr><td>Huế</td><td>1.128</td><td>1.160</td></tr></table>"
)
TABLE = Table.of({"table_id": "t", "table_html": HTML, "table_title": "Dân số"})


def fake_llm(replies):
    calls = []

    def llm(prompt, tag):
        calls.append(tag)
        return replies[tag].pop(0), 10, True

    return llm, calls


def test_router_classes():
    assert route("Huế có dân số trên 1 triệu người đúng không?") == "yesno"
    assert route("Tỉnh nào có dân số cao nhất?") == "compute"
    assert route("Dân số Đà Nẵng năm 2024 là gì?") == "lookup"
    assert gold_class(["Câu hỏi Yes/No", "Sử dụng tính toán"]) == "yesno"


def test_verbalize_follows_question_tail():
    assert nodes.verbalize("A lớn hơn B, đúng không?", "Có") == "Đúng"
    assert nodes.verbalize("A lớn hơn B phải không?", "có") == "Phải"
    assert nodes.verbalize("A có lớn hơn B không?", "Không") == "Không"
    assert nodes.verbalize("A là gì?", "1.245") == "1.245"


def test_render_keeps_headers_and_selected_rows_only():
    text = TABLE.render("pipe_nohdr", keep_rows={1})
    assert "Huế" in text and "Đà Nẵng" not in text and "2024" in text


def test_lookup_graph_emits_short_cell(monkeypatch):
    llm, calls = fake_llm({"locate": ["r0c2"]})
    monkeypatch.setattr(nodes, "llm", llm)
    s = run_graph("A4", "lookup", State("Dân số Đà Nẵng năm 2024 là bao nhiêu?", TABLE, ""))
    assert s.answer == "1.245" and calls == ["locate"]


def test_lookup_graph_falls_back_to_reader_on_bad_id(monkeypatch):
    llm, calls = fake_llm({"locate": ["r9c9"], "read": ["1.245"]})
    monkeypatch.setattr(nodes, "llm", llm)
    s = run_graph("A4", "lookup", State("Dân số Đà Nẵng năm 2024?", TABLE, ""))
    assert s.answer == "1.245" and calls == ["locate", "read"]


def test_human_chain_expands_when_anchor_view_says_null(monkeypatch):
    llm, calls = fake_llm({"read": ["Null", "1.160"]})
    monkeypatch.setattr(nodes, "llm", llm)
    s = run_graph("A3", "lookup", State("Dân số Huế năm 2024?", TABLE, ""))
    assert s.answer == "1.160" and calls == ["read", "read"] and "anchor1" in s.trace[0]
