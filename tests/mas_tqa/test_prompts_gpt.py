import json

from mas_tqa import methods, prompts_gpt
from mas_tqa.client import Usage, VLLMClient


def _patch(monkeypatch):
    monkeypatch.setattr(prompts_gpt, "table_str", lambda t: "T|C <header>")
    monkeypatch.setattr(prompts_gpt, "retrieve_same_table", lambda qa, k: [{"question": "Q0?", "answer": "A0"}])
    monkeypatch.setattr(methods, "kv_str", lambda t: "## Hàng 1\nC: v")
    monkeypatch.setattr(prompts_gpt, "tables", lambda: {"t": {"table_title": "Điện Biên_0"}})


def test_gpt_prompt_asks_for_visible_reason_and_json(monkeypatch):
    _patch(monkeypatch)
    qa = {"qa_id": "q", "table_id": "t", "question": "Ai là chủ tịch?"}
    for build in (prompts_gpt.messages_a, prompts_gpt.messages_b):
        msgs = build(qa)
        assert [m["role"] for m in msgs] == ["system", "user"]
        assert "Không văn bản ngoài JSON" in msgs[0]["content"]
        assert "<think>" not in msgs[0]["content"]
        user = msgs[1]["content"]
        assert user.index("# Bảng") < user.index("# Ví dụ cùng bảng") < user.index("# Câu hỏi")
        assert "Chỉ một JSON" in user
        assert "final_answer" in msgs[0]["content"]


def test_suite_v10_uses_gpt_sampling(monkeypatch):
    _patch(monkeypatch)
    seen = []

    class C:
        model = "azure-4o-mini"

        def chat(self, prompt, **kw):
            seen.append(kw)
            if isinstance(prompt, str):
                return [json.dumps({"scores": [{"id": 0, "p": 1}]})], Usage(1, 1, 1)
            if "agent B" in prompt[0]["content"]:
                return [json.dumps({"evidence": ["Y"], "reason": "r", "final_answer": "X"})], Usage(1, 1, 1)
            assert "agent A" in prompt[0]["content"]
            return [json.dumps({"reason": "r", "final_answer": "X"})] * 3, Usage(1, 1, 1)

    out = methods.suite_v10(C(), {"qa_id": "q", "table_id": "t", "question": "Ai?"})
    assert out["memview_q"]["prediction"] == ["X"]
    assert seen[0]["temperature"] == 0.7 and seen[0]["n"] == 3
    assert seen[0]["response_format"]["type"] == "json_schema"
    assert seen[0]["max_completion_tokens"] == 512 and "top_p" not in seen[0]
    assert seen[1]["temperature"] == 0.0
    assert "evidence" in seen[1]["response_format"]["json_schema"]["schema"]["properties"]


def test_claude_omits_top_p_and_repeats_n(monkeypatch):
    sent = []

    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "{}"}}], "usage": {}}

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.append(json)
        return Resp()

    monkeypatch.setattr("mas_tqa.client.requests.post", fake_post)
    monkeypatch.setenv("VLLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("VLLM_API_KEY", "test")
    client = VLLMClient(model="claude-haiku-4-5")
    texts, usage = client.chat("hi", n=3, temperature=0.7, top_p=1)
    assert len(texts) == 3 and usage.calls == 3
    assert all("top_p" not in body and body["n"] == 1 for body in sent)


def test_openai_client_omits_vllm_fields(monkeypatch):
    sent = {}

    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "{}"}}], "usage": {}}

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.update(json)
        return Resp()

    monkeypatch.setattr("mas_tqa.client.requests.post", fake_post)
    monkeypatch.setenv("VLLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("VLLM_API_KEY", "test")
    client = VLLMClient(model="azure-4o-mini")
    client.chat("hi", top_k=20, min_p=0, response_format={"type": "json_object"}, max_completion_tokens=80)
    assert "chat_template_kwargs" not in sent and "top_k" not in sent and "min_p" not in sent and "max_tokens" not in sent
    assert sent["max_completion_tokens"] == 80 and sent["model"] == "azure-4o-mini"
