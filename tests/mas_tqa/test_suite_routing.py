import pytest

from mas_tqa import methods
from mas_tqa.client import Usage

QA = {"qa_id": "q1", "table_id": "t1", "question": "Ai là chủ tịch?", "answer": "X"}
YN_QA = {"qa_id": "q2", "table_id": "t1", "question": "X là chủ tịch đúng không?", "answer": "Đúng"}


class FakeClient:
    """Trả lời theo loại prompt: A (kNN-FS), B (lưới), đối chất, judge."""

    def __init__(self, a, b, rebut_a=None, rebut_b=None, judge=0, third="Z"):
        self.a, self.b, self.ra, self.rb, self.judge, self.third = a, b, rebut_a, rebut_b, judge, third
        self.calls = []

    def chat(self, prompt, **kw):
        grid = prompt.startswith(methods._GRID_HEADER)
        if "trọng tài" in prompt:
            kind, text = "judge", f'{{"choice": {self.judge}}}'
        elif "chuyên gia kia" in prompt:
            kind = "rebut_b" if grid else "rebut_a"
            ans = self.rb if grid else self.ra
            text = f'{{"decision": "giu", "evidence": [], "final_answer": "{ans}"}}'
        elif kw.get("temperature"):
            kind, text = "third", f'{{"evidence": [], "final_answer": "{self.third}"}}'
        else:
            kind = "B" if grid else "A"
            text = f'{{"evidence": [], "final_answer": "{self.b if grid else self.a}"}}'
        self.calls.append(kind)
        return [text], Usage(1, 10, 1)


@pytest.fixture(autouse=True)
def _no_data(monkeypatch):
    monkeypatch.setattr(methods, "flat_prefix", lambda qa: "FLAT\n")
    monkeypatch.setattr(methods, "grid_prefix", lambda qa: methods._GRID_HEADER + "GRID\n")
    monkeypatch.setattr(methods, "knn_prompt", lambda qa: "FLAT\nQ")
    monkeypatch.setattr(methods, "evid_prompt", lambda qa: methods._GRID_HEADER + "GRID\nQ")


def test_agreement_stops_after_two_calls():
    c = FakeClient("X", "x")
    out = methods.suite(c, QA)
    assert out["memxam"]["prediction"] == ["X"] and out["memxam"]["trace"]["route"] == "agree"
    assert c.calls == ["A", "B"]


def test_validator_drops_empty_answer_without_debate():
    c = FakeClient("X", "")
    out = methods.suite(c, QA)
    assert out["memxam"]["prediction"] == ["X"] and out["memxam"]["trace"]["route"] == "validator"
    assert c.calls == ["A", "B"]


def test_validator_drops_non_yes_no_answer_for_yes_no_question():
    c = FakeClient("c. 794", "Đúng")
    out = methods.suite(c, YN_QA)
    assert out["memxam"]["prediction"] == ["Đúng"]
    assert out["cascade3"]["prediction"] == ["Đúng"]


def test_cross_examination_converges():
    c = FakeClient("X", "Y", rebut_a="Y", rebut_b="Y")
    out = methods.suite(c, QA)
    assert out["memxam"]["prediction"] == ["Y"] and out["memxam"]["trace"]["route"] == "converged"


def test_invalid_rebuttal_keeps_original_answer():
    c = FakeClient("X", "Y", rebut_a="", rebut_b="Y", third="Y")
    out = methods.suite(c, QA)
    assert out["memxam"]["trace"]["A2"] == "X"
    assert out["memxam"]["prediction"] == ["Y"] and out["memxam"]["trace"]["route"] == "vote"


def test_no_convergence_votes_with_third_solver_and_ties_go_to_a2():
    c = FakeClient("X", "Y", rebut_a="X", rebut_b="Y", third="Z")
    out = methods.suite(c, QA)
    assert out["memxam"]["prediction"] == ["X"]
    c = FakeClient("X", "Y", rebut_a="X", rebut_b="Y", third="Y")
    assert methods.suite(c, QA)["memxam"]["prediction"] == ["Y"]


def test_judge_ablation_never_returns_new_answer():
    c = FakeClient("X", "Y", rebut_a="X", rebut_b="Y", judge=7)
    out = methods.suite(c, QA)
    assert out["memxam_judge"]["prediction"][0] in {"X", "Y"}


def test_malformed_json_still_yields_final_answer():
    from mas_tqa.client import final_answer
    assert final_answer('{"evidence": ["a", ""]}, "final_answer": "Có"') == "Có"


class Fake3:
    """Solver theo view (flat / lưới / kv); lượt đối chất trả `revised[view]`."""

    def __init__(self, first, revised):
        self.first, self.revised, self.calls = first, revised, []

    def chat(self, prompt, **kw):
        view = 2 if prompt.startswith("KV") else 1 if prompt.startswith(methods._GRID_HEADER) else 0
        rebut = "chưa thống nhất" in prompt
        self.calls.append(("R" if rebut else "S", view))
        ans = (self.revised if rebut else self.first)[view]
        return [f'{{"evidence": [], "final_answer": "{ans}"}}'], Usage(1, 10, 1)


@pytest.fixture
def _v5(monkeypatch):
    monkeypatch.setattr(methods, "kv_prefix", lambda qa, k=8: "KV\n")
    monkeypatch.setattr(methods, "flat_prefix", lambda qa, k=8: "FLAT\n")
    monkeypatch.setattr(methods, "grid_prefix", lambda qa, k=8: methods._GRID_HEADER + "GRID\n")


def test_suite3_unanimous_stops_after_three_calls(_v5):
    c = Fake3(["X", "x", "X"], ["?", "?", "?"])
    out = methods.suite3(c, QA)
    assert out["memxam3"]["prediction"] == ["X"] and len(c.calls) == 3


def test_suite3_debate_then_majority(_v5):
    c = Fake3(["X", "Y", "Z"], ["Y", "Y", "Z"])
    out = methods.suite3(c, QA)
    assert out["vote3"]["prediction"] == ["X"]  # không có đa số → lấy A
    assert out["memxam3"]["prediction"] == ["Y"] and len(c.calls) == 6


class FakeSC:
    def __init__(self, a_samples, b, ra="?", rb="?"):
        self.a, self.b, self.ra, self.rb, self.calls = a_samples, b, ra, rb, []

    def chat(self, prompt, **kw):
        grid = prompt.startswith(methods._GRID_HEADER)
        if "chuyên gia kia" in prompt:
            self.calls.append("R")
            ans = [self.rb if grid else self.ra]
        else:
            self.calls.append("S")
            ans = [self.b] if grid else self.a[: kw.get("n", 1)]
        return [f'{{"evidence": [], "final_answer": "{x}"}}' for x in ans], Usage(1, 10, 1)


def test_suite_sc_consensus_stops_early():
    c = FakeSC(["X", "X", "Y"], "X")
    out = methods.suite_sc(c, QA)
    assert out["memxam_sc"]["prediction"] == ["X"] and c.calls == ["S", "S"]


def test_suite_sc_contested_debates_then_votes():
    c = FakeSC(["X", "X", "Y"], "Y", ra="Y", rb="Y")
    out = methods.suite_sc(c, QA)
    assert out["vote4"]["prediction"] == ["X"]
    assert out["memxam_sc"]["prediction"] == ["Y"] and c.calls.count("R") == 2
