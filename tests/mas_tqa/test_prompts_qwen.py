from mas_tqa import methods, prompts_qwen
from mas_tqa.client import Usage


def _patch(monkeypatch):
    monkeypatch.setattr(prompts_qwen, "table_str", lambda t: "T|C <header>")
    monkeypatch.setattr(prompts_qwen, "retrieve_same_table", lambda qa, k: [{"question": "Q0?", "answer": "A0"}])
    monkeypatch.setattr(methods, "kv_str", lambda t: "## Hàng 1\nC: v")
    monkeypatch.setattr(prompts_qwen, "tables", lambda: {"t": {"table_title": "Điện Biên_0"}})


def test_messages_put_rules_in_system_and_question_last(monkeypatch):
    _patch(monkeypatch)
    for build in (prompts_qwen.messages_a, prompts_qwen.messages_b):
        msgs = build({"qa_id": "q", "table_id": "t", "question": "Ai là chủ tịch?"})
        assert [m["role"] for m in msgs] == ["system", "user"]
        assert "Null" in msgs[0]["content"] and "<think>" not in msgs[0]["content"]
        user = msgs[1]["content"]
        assert user.index("<bảng>") < user.index("<ví_dụ_cùng_bảng>") < user.index("<câu_hỏi>")
        assert user.rstrip().endswith("}")


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


def test_suite_v10_routes_consensus_and_agent_v(monkeypatch):
    import json

    from mas_tqa import scorer

    _patch(monkeypatch)
    monkeypatch.setattr(scorer, "prefix_flat", lambda qa: "SF\n")
    monkeypatch.setattr(scorer, "prefix_kv", lambda qa: "SK\n")

    def make(a, b):
        class C:
            calls = []

            def chat(self, prompt, **kw):
                assert kw.get("temperature") == 0.6
                if isinstance(prompt, str):
                    self.calls.append("V")
                    lines = prompt.split("CÁC ỨNG VIÊN:\n")[1].split("\nĐẦU RA")[0].splitlines()
                    idx = [ln for ln in lines if ln.startswith("[")]
                    best = next(k for k, ln in enumerate(idx) if ln.endswith("] Y"))
                    return [json.dumps({"scores": [{"id": best, "p": 1}]})], Usage(1, 1, 1)
                if "agent B" in prompt[0]["content"]:
                    self.calls.append("B")
                    return [json.dumps({"evidence": ["Y"], "reason": "r", "final_answer": b})], Usage(1, 1, 1)
                self.calls.append("A")
                return [json.dumps({"reason": "r", "final_answer": x}) for x in a], Usage(1, 1, 1)
        return C()

    qa = {"qa_id": "q", "table_id": "t", "question": "Ai?"}
    c = make(["X", "X", "X"], "X")
    assert methods.suite_v10(c, qa)["memview_q"]["prediction"] == ["X"] and c.calls == ["A", "B"]
    c = make(["X", "X", "X"], "Y")
    out = methods.suite_v10(c, qa)
    assert out["memview_q"]["trace"]["route"] == "agent_v" and out["memview_q"]["prediction"] == ["Y"]
    assert c.calls.count("V") == 2


def test_table_title_is_in_prompt_without_index_suffix(monkeypatch):
    _patch(monkeypatch)
    for build in (prompts_qwen.messages_a, prompts_qwen.messages_b, prompts_qwen.messages_fs):
        user = build({"qa_id": "q", "table_id": "t", "question": "Bảng này của tỉnh nào?"})[1]["content"]
        assert "<tên_bảng>Điện Biên</tên_bảng>" in user and user.index("<tên_bảng>") < user.index("<bảng>")
