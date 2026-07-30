import pytest

from baseline.prompts import build_tableqa_prompt


@pytest.mark.parametrize(
    ("prompt_style", "prompt_version", "required_fields", "forbidden_fields"),
    [
        (
            "zero_shot",
            "v2_zs_structured",
            ('"final_answer"',),
            ('"reasoning"', '"subproblems"'),
        ),
        (
            "few_shot",
            "v2_fs_structured",
            ('"final_answer"',),
            ('"reasoning"', '"subproblems"'),
        ),
        (
            "cot",
            "v2_cot_structured",
            ('"reasoning"', '"final_answer"'),
            ('"subproblems"',),
        ),
        (
            "task_decomposition",
            "v2_td_structured",
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
