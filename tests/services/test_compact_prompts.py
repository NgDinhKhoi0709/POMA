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
        assert "QUY TẮC ĐẦU RA" in text
        assert "không lặp lại" in text.lower()
