from mas_tqa import methods, prompts_claude, prompts_gemini, prompts_gpt41


def _patch(monkeypatch, module):
    monkeypatch.setattr("mas_tqa.prompts_layout.table_str", lambda t: "T|C <header>")
    monkeypatch.setattr("mas_tqa.prompts_layout.retrieve_same_table", lambda qa, k: [{"question": "Q0?", "answer": "A0"}])
    monkeypatch.setattr("mas_tqa.prompts_layout.tables", lambda: {"t": {"table_title": "Điện Biên_0"}})
    monkeypatch.setattr(methods, "kv_str", lambda t: "## Hàng 1\nC: v")


def test_gpt41_puts_literal_rules_and_xml_table(monkeypatch):
    _patch(monkeypatch, prompts_gpt41)
    msgs = prompts_gpt41.messages_a({"qa_id": "q", "table_id": "t", "question": "Ai?"})
    assert "# Hướng dẫn" in msgs[0]["content"] and "Không thêm quy tắc khác" in msgs[0]["content"]
    user = msgs[1]["content"]
    assert "<bảng>" in user and user.index("<bảng>") < user.index("<câu_hỏi>") < user.index("<nhắc_lại>")


def test_claude_uses_xml_and_json_object(monkeypatch):
    _patch(monkeypatch, prompts_claude)
    msgs = prompts_claude.messages_a({"qa_id": "q", "table_id": "t", "question": "Ai?"})
    assert "<quy_tắc>" in msgs[0]["content"] and "Bắt đầu ngay bằng dấu {" in msgs[0]["content"]
    assert prompts_claude.FORMATS["A"] == {"type": "json_object"}


def test_gemini_keeps_schema_out_of_the_prompt(monkeypatch):
    _patch(monkeypatch, prompts_gemini)
    msgs = prompts_gemini.messages_a({"qa_id": "q", "table_id": "t", "question": "Ai?"})
    assert "json" not in msgs[0]["content"].lower()
    assert "tiếng Việt" in msgs[0]["content"]
    assert prompts_gemini.SINGLE["extra_body"] == {"reasoning_effort": "none"}
    assert "# Bảng" in msgs[1]["content"] and "<bảng>" not in msgs[1]["content"]


def test_model_line_selects_its_prompt():
    class C:
        def __init__(self, model):
            self.model = model

    assert methods._prompt_pack(C("azure-4.1-mini"))[0].__name__.endswith("prompts_gpt41")
    assert methods._prompt_pack(C("claude-haiku-4-5"))[0].__name__.endswith("prompts_claude")
    assert methods._prompt_pack(C("gemini-2.5-flash-lite"))[0].__name__.endswith("prompts_gemini")
    assert methods._prompt_pack(C("azure-4o-mini"))[0].__name__.endswith("prompts_gpt")
    assert methods._prompt_pack(C("Qwen/Qwen3-8B"))[0].__name__.endswith("prompts_qwen")
