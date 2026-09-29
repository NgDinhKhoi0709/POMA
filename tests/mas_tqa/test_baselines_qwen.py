import json

from mas_tqa import methods, prompts_qwen, prompts_fs
from mas_tqa.client import Usage

QA = {"qa_id": "q", "table_id": "t", "question": "Ai?"}


def _patch(monkeypatch):
    monkeypatch.setattr(prompts_qwen, "table_str", lambda t: "T|C <header>")
    monkeypatch.setattr(prompts_qwen, "retrieve_same_table", lambda qa, k: [{"question": "Q0?", "answer": "A0"}])
    monkeypatch.setattr(prompts_qwen, "tables", lambda: {"t": {"table_title": "Điện Biên_0"}})
    monkeypatch.setattr(prompts_fs, "_few_shot_examples_vi", lambda: "CHUNG")
    monkeypatch.setattr(methods, "kv_str", lambda t: "## Hàng 1\nC: v")


def _ans(x):
    return json.dumps({"reason": "r", "final_answer": x})


def test_zero_shot_has_no_examples(monkeypatch):
    _patch(monkeypatch)
    user = prompts_qwen.messages_zs(QA)[1]["content"]
    assert "ví_dụ" not in user and user.startswith("<tên_bảng>") and "<câu_hỏi>" in user


def test_no_memory_prompts_use_generic_examples(monkeypatch):
    _patch(monkeypatch)
    for build in (prompts_qwen.messages_a, prompts_qwen.messages_b):
        user = build(QA, memory=False)[1]["content"]
        assert "<ví_dụ_cùng_bảng>" not in user and "Q0?" not in user and "CHUNG" in user


def test_fs_sc3_majority(monkeypatch):
    _patch(monkeypatch)

    class C:
        def chat(self, prompt, **kw):
            assert kw["n"] == 3 and kw["temperature"] == 0.6
            return [_ans("X"), _ans("Y"), _ans("Y")], Usage(1, 1, 1)

    assert methods.METHODS["fs_qwen_sc3"](C(), QA)["prediction"] == ["Y"]


def test_debate_round_two_sees_other_agents(monkeypatch):
    _patch(monkeypatch)
    seen = []

    class C:
        def chat(self, prompt, **kw):
            if kw.get("n", 1) == 3:
                return [_ans("X"), _ans("Y"), _ans("Y")], Usage(1, 1, 1)
            seen.append(prompt)
            return [_ans("Y")], Usage(1, 1, 1)

    out = methods.mad_debate(C(), QA)
    assert out["prediction"] == ["Y"] and out["usage"].calls == 4 and len(seen) == 3
    first = seen[0]
    assert [m["role"] for m in first] == ["system", "user", "assistant", "user"]
    assert '"X"' in first[2]["content"] and first[3]["content"].count('"Y"') == 2 and '"X"' not in first[3]["content"]


def test_suite_nomem_hides_same_table_examples(monkeypatch):
    from mas_tqa import math_agent, scorer

    _patch(monkeypatch)
    monkeypatch.setattr(scorer, "table_str", lambda t: "T")
    monkeypatch.setattr(math_agent, "demo_block", lambda qa, memory=True: "MEM" if memory else "CHUNG")
    prompts = []

    class C:
        def chat(self, prompt, **kw):
            prompts.append(json.dumps(prompt, ensure_ascii=False))
            if isinstance(prompt, str):
                return [json.dumps({"scores": [{"id": 0, "p": 1}]})], Usage(1, 1, 1)
            if "agent B" in prompt[0]["content"]:
                return [json.dumps({"evidence": [], "reason": "r", "final_answer": "Y"})], Usage(1, 1, 1)
            return [_ans("X")] * 3, Usage(1, 1, 1)

    out = methods.SUITES["suite_v10_nomem"](C(), QA)
    assert set(out) == {"a_only_nm", "vote4_nm", "memview_nm"}
    assert len(prompts) == 4 and not any("Q0?" in p or "MEM" in p for p in prompts)
