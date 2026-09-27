import pytest

from mas_tqa import code_agent, methods
from mas_tqa.client import Usage

QA = {"qa_id": "q1", "table_id": "t1", "question": "Ai là chủ tịch?", "answer": "X"}


class FakeV8:
    """A: 3 mẫu; B: Markdown-KV; C: code (đáp án = biến answer); đối chất theo đuôi prompt."""

    def __init__(self, a, b, c, rebut_a=None, rebut_b=None):
        self.a, self.b, self.c, self.ra, self.rb = a, b, c, rebut_a, rebut_b
        self.calls = []

    def chat(self, prompt, **kw):
        kv = prompt.startswith(methods._KV_HEADER)
        if "chuyên gia kia" in prompt:
            kind, ans = ("rebut_b", self.rb) if kv else ("rebut_a", self.ra)
            texts = [f'{{"decision": "giu", "evidence": [], "final_answer": "{ans}"}}']
        elif prompt.startswith(methods._CODE_HEADER):
            kind, texts = "C", [f"```python\nanswer = {self.c!r}\n```"]
        elif kv:
            kind, texts = "B", [f'{{"evidence": ["ô"], "final_answer": "{self.b}"}}']
        else:
            kind, texts = "A", [f'{{"final_answer": "{x}"}}' for x in self.a]
        self.calls.append(kind)
        return texts, Usage(1, 10, 1)


@pytest.fixture(autouse=True)
def _no_data(monkeypatch):
    monkeypatch.setattr(methods, "flat_prefix", lambda qa, k=8: "FLAT\n")
    monkeypatch.setattr(methods, "kv_prefix", lambda qa, k=8: methods._KV_HEADER + "KV\n")
    monkeypatch.setattr(methods, "code_prompt", lambda qa, k=8: methods._CODE_HEADER + "Q")
    monkeypatch.setattr(code_agent, "table_rows", lambda t: [["Tên"], ["X"]])


def test_all_agree_no_debate():
    c = FakeV8(["X", "X", "X"], "X", "X")
    out = methods.suite_v8(c, QA)
    assert c.calls == ["A", "B", "C"]
    assert all(out[m]["prediction"] == ["X"] for m in ("memxam_sckv", "memxam_veto", "memxam_c5", "code_c"))


def test_b_veto_triggers_debate_only_for_veto_rule():
    c = FakeV8(["X", "X", "X"], "Y", "Y", rebut_a="Y", rebut_b="Y")
    out = methods.suite_v8(c, QA)
    assert out["memxam_sckv"]["prediction"] == ["X"] and out["memxam_sckv"]["trace"]["route"] == "consensus"
    # Veto: vote trên [Y, Y, X, X, X, Y] → hoà 3–3, về A2 = Y.
    assert out["memxam_veto"]["prediction"] == ["Y"] and out["memxam_veto"]["trace"]["route"] == "debate"
    # C5: X có 3/5 < 4 → đối chất; vote trên [Y, Y, X, X, X, Y, Y] → Y.
    assert out["memxam_c5"]["prediction"] == ["Y"]
    assert c.calls.count("rebut_a") == 1 and c.calls.count("rebut_b") == 1


def test_code_failure_is_dropped_by_validator(monkeypatch):
    monkeypatch.setattr(code_agent, "run_code", lambda rows, code: (None, "timeout"))
    c = FakeV8(["X", "X", "X"], "X", "Z")
    out = methods.suite_v8(c, QA)
    assert out["code_c"]["prediction"] == ["Null"] and out["code_c"]["trace"]["error"] == "timeout"
    assert out["memxam_c5"]["prediction"] == ["X"] and "rebut_a" not in c.calls


def test_c_dissent_debates_with_c_answer_when_b_agrees():
    c = FakeV8(["X", "X", "W"], "X", "Z", rebut_a="X", rebut_b="X")
    out = methods.suite_v8(c, QA)
    tr = out["memxam_c5"]["trace"]
    assert tr["A_pos"] == "X" and tr["B_pos"] == "W"  # ưu tiên ứng viên còn lại của pool v7
    assert out["memxam_sckv"]["prediction"] == ["X"] and out["memxam_c5"]["prediction"] == ["X"]


def test_no_c_mode_skips_code_call_and_keeps_veto(monkeypatch):
    monkeypatch.setenv("MAS_V8_NO_C", "1")
    c = FakeV8(["X", "X", "X"], "Y", "unused", rebut_a="Y", rebut_b="Y")
    out = methods.suite_v8(c, QA)
    assert "C" not in c.calls
    assert out["memxam_veto"]["prediction"] == ["Y"] and out["memxam_sckv"]["prediction"] == ["X"]
