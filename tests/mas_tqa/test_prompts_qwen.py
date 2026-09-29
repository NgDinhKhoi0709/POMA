from mas_tqa import methods, prompts_qwen
from mas_tqa.client import Usage


def _patch(monkeypatch):
    monkeypatch.setattr(prompts_qwen, "table_str", lambda t: "T|C <header>")
    monkeypatch.setattr(prompts_qwen, "retrieve_same_table", lambda qa, k: [{"question": "Q0?", "answer": "A0"}])
    monkeypatch.setattr(methods, "kv_str", lambda t: "## Hàng 1\nC: v")


def test_messages_put_rules_in_system_and_question_last(monkeypatch):
    _patch(monkeypatch)
    for build in (prompts_qwen.messages_a, prompts_qwen.messages_b):
        msgs = build({"qa_id": "q", "table_id": "t", "question": "Ai là chủ tịch?"})
        assert [m["role"] for m in msgs] == ["system", "user"]
        assert "Null" in msgs[0]["content"] and "<think>" not in msgs[0]["content"]
        user = msgs[1]["content"]
        assert user.index("<bảng>") < user.index("<ví_dụ_cùng_bảng>") < user.index("<câu_hỏi>")
        assert user.rstrip().endswith("}")


def test_explain_question_gets_null_hint(monkeypatch):
    _patch(monkeypatch)
    msgs = prompts_qwen.messages_a({"qa_id": "q", "table_id": "t", "question": "Vì sao X bị huỷ?"})
    assert "hỏi lý do/cách thức" in msgs[1]["content"]
    msgs = prompts_qwen.messages_a({"qa_id": "q", "table_id": "t", "question": "Ai là chủ tịch?"})
    assert "hỏi lý do/cách thức" not in msgs[1]["content"]


def test_agent_uses_qwen_sampling(monkeypatch):
    _patch(monkeypatch)
    seen = {}

    class C:
        def chat(self, prompt, **kw):
            seen.update(kw, messages=prompt)
            return ['{"reason": "r", "final_answer": "X"}'] * kw["n"], Usage(1, 1, 1)

    out = methods.METHODS["a_qwen_sc3"](C(), {"qa_id": "q", "table_id": "t", "question": "Ai?"})
    assert out["prediction"] == ["X"]
    assert (seen["temperature"], seen["top_p"], seen["top_k"], seen["min_p"], seen["max_tokens"]) == (0.6, 0.95, 20, 0.0, None)
    assert isinstance(seen["messages"], list)
