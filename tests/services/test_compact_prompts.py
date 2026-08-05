from pathlib import Path


REQUIRED = [
    "hint_predictor.md", "question_refiner.md", "grounded_single_answer.md",
    "answer_normalization.md", "specialists/what.md", "specialists/who.md",
    "specialists/when.md", "specialists/where.md", "specialists/yesno.md",
    "specialists/list.md", "specialists/why.md", "specialists/how.md",
    "specialists/multi_conditions.md", "specialists/mathematical_reasoning.md",
    "answer_normalization/what.md", "answer_normalization/who.md",
    "answer_normalization/when.md", "answer_normalization/where.md",
    "answer_normalization/yesno.md", "answer_normalization/list.md",
    "answer_normalization/why.md", "answer_normalization/how.md",
    "answer_normalization/multi_conditions.md",
    "answer_normalization/mathematical_reasoning.md",
]


def test_compact_prompt_tree_is_complete():
    root = Path("src/prompts_compact")
    assert [name for name in REQUIRED if not (root / name).exists()] == []


def test_compact_prompts_are_json_only_and_do_not_ask_for_cot():
    for path in Path("src/prompts_compact").rglob("*.md"):
        text = path.read_text(encoding="utf-8").lower()
        assert "json" in text
        assert "chain-of-thought" not in text
        assert "step by step" not in text


def test_simple_specialists_have_no_examples():
    root = Path("src/prompts_compact/specialists")
    for name in ["what", "who", "when", "where", "yesno", "list"]:
        assert "example" not in (root / f"{name}.md").read_text(encoding="utf-8").lower()


def test_complex_specialists_have_two_short_examples():
    root = Path("src/prompts_compact/specialists")
    for name in ["why", "how", "multi_conditions", "mathematical_reasoning"]:
        text = (root / f"{name}.md").read_text(encoding="utf-8")
        assert text.count("EXAMPLE ") == 2
        assert "null" in text


def test_answer_prompts_require_minimal_non_restated_answers():
    paths = [
        Path("src/prompts_compact/answer_normalization.md"),
        Path("src/prompts_compact/grounded_single_answer.md"),
        *Path("src/prompts_compact/specialists").glob("*.md"),
        *Path("src/prompts_compact/answer_normalization").glob("*.md"),
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "# QUY TẮC" in text
        lowered = text.lower()
        assert "không lặp lại" in lowered or "không nhắc lại" in lowered


def test_specialist_and_normalization_prompts_have_clear_structured_sections():
    paths = [
        *Path("src/prompts_compact/specialists").glob("*.md"),
        *Path("src/prompts_compact/answer_normalization").glob("*.md"),
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "# VAI TRÒ" in text
        assert "# QUY TẮC" in text
        assert "# JSON DUY NHẤT" in text
        assert "# INPUT" in text


def test_hint_predictor_documents_every_canonical_hint_and_refiner_contract():
    hint_text = Path("src/prompts_compact/hint_predictor.md").read_text(
        encoding="utf-8"
    )
    for hint in [
        "What",
        "Where",
        "Who",
        "When",
        "Why",
        "How",
        "YesNo",
        "List",
        "MathematicalReasoning",
        "MultiConditions",
    ]:
        assert f"`{hint}`" in hint_text

    refiner_text = Path("src/prompts_compact/question_refiner.md").read_text(
        encoding="utf-8"
    )
    for field in ["normalized_question", "target", "constraints"]:
        assert f"`{field}`" in refiner_text


def test_compact_prompts_preserve_open_vitabqa_addition_semantics():
    root = Path("src/prompts_compact")
    hint_text = (root / "hint_predictor.md").read_text(encoding="utf-8")
    assert "tính đúng/sai" in hint_text
    assert "liệt kê hoặc sắp xếp" in hint_text
    assert "tổng, hiệu, tích, trung bình, lớn nhất hoặc nhỏ nhất" in hint_text
    assert "AND/OR" in hint_text
    assert "không thể trả lời" in hint_text

    multi_text = (root / "specialists/multi_conditions.md").read_text(
        encoding="utf-8"
    )
    assert "với AND" in multi_text
    assert "với OR" in multi_text

    list_text = (root / "specialists/list.md").read_text(encoding="utf-8")
    assert "thứ tự/sắp xếp" in list_text
