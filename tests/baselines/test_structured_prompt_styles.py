import pytest

from baseline.prompts import PROMPT_STYLES, build_tableqa_prompt
from src.contracts import STRUCTURED_SCHEMAS


@pytest.mark.parametrize("prompt_style", PROMPT_STYLES)
def test_prompt_styles_request_only_nullable_final_answer(prompt_style: str) -> None:
    prompt = build_tableqa_prompt(
        question="Quốc gia nào được liệt kê?",
        table_str="Quốc gia <header>|Tên <header>|Guatemala",
        prompt_style=prompt_style,
    )

    assert "Quốc gia <header>|Tên <header>|Guatemala" in prompt
    assert "Quốc gia nào được liệt kê?" in prompt
    assert '"final_answer"' in prompt
    assert "null" in prompt
    assert '"reasoning"' not in prompt
    assert '"subproblems"' not in prompt


def test_baseline_schemas_only_require_nullable_final_answer() -> None:
    expected_properties = {
        "final_answer": {"oneOf": [{"type": "string"}, {"type": "null"}]}
    }
    for prompt_style in PROMPT_STYLES:
        schema = STRUCTURED_SCHEMAS[f"baseline_{prompt_style}.v1"].json_schema
        assert schema["required"] == ["final_answer"]
        assert schema["properties"] == expected_properties


def test_zero_shot_prompt_builder_returns_string() -> None:
    prompt = build_tableqa_prompt(
        question="Thủ đô là gì?",
        table_str="Quốc gia <header>|Thủ đô <header>|Hà Nội",
        prompt_style="zero_shot",
    )

    assert isinstance(prompt, str)
