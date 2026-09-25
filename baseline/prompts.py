from __future__ import annotations

from typing import Final

PROMPT_STYLES: Final[tuple[str, ...]] = (
    "zero_shot",
    "cot",
    "task_decomposition",
    "few_shot",
)

ZERO_SHOT_PROMPT = """Chỉ dùng TABLE_STR để trả lời QUESTION.

TABLE_STR:
{table_str}

QUESTION: {question}

Chỉ trả về một JSON: {{"final_answer": "<câu trả lời ngắn>"}}. Nếu bảng không đủ thông tin: {{"final_answer": null}}. Không thêm nội dung khác.
"""

COT_PROMPT = """Chỉ dùng TABLE_STR để trả lời QUESTION. Xác định hàng, cột và phép tính cần thiết trước khi trả lời nhưng không xuất suy luận.

TABLE_STR:
{table_str}

QUESTION: {question}

Chỉ trả về một JSON: {{"final_answer": "<câu trả lời ngắn>"}}. Nếu bảng không đủ thông tin: {{"final_answer": null}}. Không thêm nội dung khác.
"""

TASK_DECOMPOSITION_PROMPT = """Chỉ dùng TABLE_STR để trả lời QUESTION. Tự chia câu hỏi thành các bước cần thiết nhưng không xuất các bước.

TABLE_STR:
{table_str}

QUESTION: {question}

Chỉ trả về một JSON: {{"final_answer": "<câu trả lời ngắn>"}}. Nếu bảng không đủ thông tin: {{"final_answer": null}}. Không thêm nội dung khác.
"""

FEW_SHOT_PROMPT = """Chỉ dùng TABLE_STR để trả lời QUESTION.

Ví dụ:
TABLE_STR:
Người <header>|Quê quán <header>|An|Hà Nội
QUESTION: Quê quán của An ở đâu?
OUTPUT: {{"final_answer": "Hà Nội"}}

TABLE_STR:
Người <header>|Quê quán <header>|An|Hà Nội
QUESTION: Tuổi của An là bao nhiêu?
OUTPUT: {{"final_answer": null}}

TABLE_STR:
{table_str}

QUESTION: {question}

Chỉ trả về một JSON: {{"final_answer": "<câu trả lời ngắn>"}}. Nếu bảng không đủ thông tin: {{"final_answer": null}}. Không thêm nội dung khác.
"""

_TEMPLATE_BY_STYLE: dict[str, str] = {
    "zero_shot": ZERO_SHOT_PROMPT,
    "cot": COT_PROMPT,
    "task_decomposition": TASK_DECOMPOSITION_PROMPT,
    "few_shot": FEW_SHOT_PROMPT,
}


def build_tableqa_prompt_flatten_v1_table_str(
    *,
    question: str,
    table_str: str,
    answer_language: str = "vi",
) -> str:
    """Legacy zero-shot prompt builder."""
    return build_tableqa_prompt(
        question=question,
        table_str=table_str,
        prompt_style="zero_shot",
    )


def build_tableqa_prompt(
    *,
    question: str,
    table_str: str,
    prompt_style: str = "zero_shot",
    answer_language: str = "vi",
) -> str:
    """Build a TableQA user prompt."""
    style = (prompt_style or "zero_shot").strip().lower()
    template = _TEMPLATE_BY_STYLE.get(style)
    if template is None:
        raise ValueError(f"Unknown prompt_style={prompt_style!r}. Choose from {PROMPT_STYLES}.")
    return template.format(
        question=question,
        table_str=str(table_str or "").strip(),
    )
