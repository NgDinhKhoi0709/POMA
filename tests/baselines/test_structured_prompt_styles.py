import pytest

from baseline.prompts import build_tableqa_prompt


@pytest.mark.parametrize(
    ("prompt_style", "prompt_version", "required_fields", "forbidden_fields"),
    [
        (
            "zero_shot",
            "v4_zs_minimal_json_vi",
            ('"final_answer"',),
            ('"reasoning"', '"subproblems"'),
        ),
        (
            "few_shot",
            "v3_fs_structured_vi",
            ('"final_answer"',),
            ('"reasoning"', '"subproblems"'),
        ),
        (
            "cot",
            "v3_cot_structured_vi",
            ('"reasoning"', '"final_answer"'),
            ('"subproblems"',),
        ),
        (
            "task_decomposition",
            "v3_td_structured_vi",
            ('"subproblems"', '"reasoning"', '"final_answer"'),
            (),
        ),
    ],
)
def test_structured_prompt_styles_request_only_their_contract_fields(
    prompt_style: str,
    prompt_version: str,
    required_fields: tuple[str, ...],
    forbidden_fields: tuple[str, ...],
) -> None:
    """Catch a prompt regression that collapses a style to final-answer-only."""
    prompt, actual_version = build_tableqa_prompt(
        question="Which country is listed?",
        table_str="Country <header>|Name <header>|Guatemala",
        prompt_style=prompt_style,
        answer_language="en",
    )

    assert actual_version == prompt_version
    for field in required_fields:
        assert field in prompt
    for field in forbidden_fields:
        assert field not in prompt


def test_zero_shot_prompt_keeps_minimal_instruction_in_vietnamese() -> None:
    prompt, _ = build_tableqa_prompt(
        question="Thu do la gi?",
        table_str="Quoc gia <header>|Thu do <header>|Ha Noi",
        prompt_style="zero_shot",
    )

    assert prompt == (
        "Dựa vào bảng, trả lời câu hỏi. Nếu bảng không đủ thông tin, trả về null. "
        "Trả về đúng một JSON: {\"final_answer\":\"...\"}.\n\n"
        "BẢNG:\nQuoc gia <header>|Thu do <header>|Ha Noi\n\n"
        "CÂU HỎI: Thu do la gi?\n"
    )
