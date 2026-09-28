from mas_tqa import style

TRAIN = {"t": [{"qa_id": f"r{i}", "question": "Xây vào năm nào?", "answer": "Năm 2001"} for i in range(3)]
         + [{"qa_id": "u1", "question": "Ông bao nhiêu tuổi?", "answer": "45 tuổi"},
            {"qa_id": "f1", "question": "Nhà có bao nhiêu tầng?", "answer": "30"}]}
QA = {"qa_id": "q", "table_id": "t", "question": "Bà ấy bao nhiêu tuổi?"}


def _patch(monkeypatch, cells="Burundi* | 4.512"):
    monkeypatch.setattr(style, "train_by_table", lambda: TRAIN)
    monkeypatch.setattr(style, "_cells", lambda t: cells)


def test_year_and_unit_follow_same_table_train_style(monkeypatch):
    _patch(monkeypatch)
    assert style.harmonize("2012", {**QA, "question": "Khánh thành khi nào?"}) == "Năm 2012"
    assert style.harmonize("10", QA) == "10 tuổi"
    assert style.harmonize("12", {**QA, "question": "Tháp có bao nhiêu tầng?"}) == "12"


def test_no_evidence_or_proper_noun_keeps_answer(monkeypatch):
    _patch(monkeypatch)
    assert style.harmonize("335", {**QA, "question": "Tháp cao bao nhiêu m?"}) == "335"
    assert style.harmonize("3", {**QA, "question": "Có bao nhiêu Đại hội?"}) == "3"
    assert style.harmonize("Hà Nội", QA) == "Hà Nội"


def test_footnote_thousands_and_duplicate_list(monkeypatch):
    _patch(monkeypatch)
    assert style.harmonize("Burundi*", QA) == "Burundi"
    assert style.harmonize("10400000", {**QA, "question": "Chênh lệch?"}) == "10.400.000"
    assert style.harmonize("24.3, 24.3", {**QA, "question": "Nhiệt độ?"}) == "24.3"
