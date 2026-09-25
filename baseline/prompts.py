from __future__ import annotations

from typing import Final, Tuple

# Stored in JSONL as prompt_version (stable ids for experiments / analysis).
PROMPT_VERSION_ZERO_SHOT = "v4_zs_minimal_json_vi"
PROMPT_VERSION_COT = "v3_cot_structured_vi"
PROMPT_VERSION_TASK_DECOMPOSITION = "v3_td_structured_vi"
PROMPT_VERSION_FEW_SHOT = "v3_fs_structured_vi"

PROMPT_STYLES: Final[tuple[str, ...]] = (
    "zero_shot",
    "cot",
    "task_decomposition",
    "few_shot",
)

_PROMPT_VERSION_BY_STYLE: dict[str, str] = {
    "zero_shot": PROMPT_VERSION_ZERO_SHOT,
    "cot": PROMPT_VERSION_COT,
    "task_decomposition": PROMPT_VERSION_TASK_DECOMPOSITION,
    "few_shot": PROMPT_VERSION_FEW_SHOT,
}


def resolve_prompt_version(prompt_style: str) -> str:
    s = (prompt_style or "zero_shot").strip().lower()
    if s not in _PROMPT_VERSION_BY_STYLE:
        raise ValueError(f"Unknown prompt_style={prompt_style!r}. Choose from {PROMPT_STYLES}.")
    return _PROMPT_VERSION_BY_STYLE[s]


def _flatten_v1_notes_vi() -> str:
    return (
        "GHI CHÚ ĐỊNH DẠNG TABLE_STR (FLATTEN V1):\n"
        "- Mỗi dòng có dạng: tiêu_đề_hàng|tiêu_đề_cột|giá_trị.\n"
        "- Tiêu đề hàng và tiêu đề cột luôn có hậu tố '<header>'.\n"
        "- Giá trị ô dữ liệu là thành phần thứ ba của mỗi dòng.\n"
    )


def _json_schema_instructions_vi() -> str:
    return (
        "ĐẦU RA (BẮT BUỘC): Một đối tượng JSON hợp lệ duy nhất (có thể bọc trong khối ```json ... ```).\n"
        "Không thêm văn bản ngoài JSON (hoặc ngoài khối ```json).\n"
        "Schema:\n"
        '  {"final_answer": "<một giá trị ngắn gọn; hoặc chuỗi Null khi bảng không đủ thông tin>"}\n'
        "Không xuất reasoning. Không xuất suy luận nội bộ.\n"
        "Tuyệt đối không dùng thẻ <think> hoặc </think>.\n"
        "Quy tắc final_answer (rút gọn, phù hợp đánh giá EM):\n"
        "- Chỉ dựa vào TABLE_STR; không bịa; không lặp nguyên câu hỏi.\n"
        "- Một giá trị ngắn (số, tên, Có/Không, ...); dùng Null (chuỗi) nếu không trả lời được.\n"
        "- Không dùng Markdown trong final_answer.\n"
        "Ví dụ một dòng: "
        '{"final_answer":"42"}\n'
    )


def _cot_schema_instructions_vi() -> str:
    return (
        "ĐẦU RA (BẮT BUỘC): Một đối tượng JSON hợp lệ duy nhất (có thể bọc trong khối ```json ... ```).\n"
        "Không thêm văn bản ngoài JSON (hoặc ngoài khối ```json).\n"
        "Schema:\n"
        '  {"reasoning": "<giải thích ngắn gọn, có thể kiểm tra từ bảng>", '
        '"final_answer": "<một giá trị ngắn gọn; hoặc chuỗi Null khi bảng không đủ thông tin>"}\n'
        "reasoning là lý do ngắn gọn, có thể kiểm tra; chỉ nêu hàng/cột hoặc phép tính cần thiết.\n"
        "Không xuất suy luận riêng tư hoặc từng bước suy nghĩ chi tiết.\n"
        "final_answer chỉ dựa vào TABLE_STR, không dùng Markdown, và dùng Null nếu không trả lời được.\n"
    )


def _task_decomposition_schema_instructions_vi() -> str:
    return (
        "ĐẦU RA (BẮT BUỘC): Một đối tượng JSON hợp lệ duy nhất (có thể bọc trong khối ```json ... ```).\n"
        "Không thêm văn bản ngoài JSON (hoặc ngoài khối ```json).\n"
        "Schema:\n"
        '  {"subproblems": ["<nhiệm vụ ngắn gọn>"], '
        '"reasoning": "<giải thích ngắn gọn, có thể kiểm tra từ bảng>", '
        '"final_answer": "<một giá trị ngắn gọn; hoặc chuỗi Null khi bảng không đủ thông tin>"}\n'
        "subproblems là danh sách các nhiệm vụ ngắn gọn để trả lời câu hỏi.\n"
        "reasoning là lý do ngắn gọn, có thể kiểm tra; chỉ nêu hàng/cột hoặc phép tính cần thiết.\n"
        "Không xuất suy luận riêng tư hoặc từng bước suy nghĩ chi tiết.\n"
        "final_answer chỉ dựa vào TABLE_STR, không dùng Markdown, và dùng Null nếu không trả lời được.\n"
    )


def build_tableqa_prompt_flatten_v1_table_str(
    *,
    question: str,
    table_str: str,
    answer_language: str = "vi",
) -> str:
    """Legacy: zero-shot JSON answer."""
    prompt, _ = build_tableqa_prompt(
        question=question,
        table_str=table_str,
        prompt_style="zero_shot",
        answer_language=answer_language,
    )
    return prompt


def build_tableqa_prompt(
    *,
    question: str,
    table_str: str,
    prompt_style: str = "zero_shot",
    answer_language: str = "vi",
) -> Tuple[str, str]:
    """
    Build TableQA user prompt and return (prompt, prompt_version).
    """
    style = (prompt_style or "zero_shot").strip().lower()
    version = resolve_prompt_version(style)
    ts = str(table_str or "").strip()
    vi = (answer_language or "vi").strip().lower() == "vi"

    if style == "zero_shot":
        return _build_zero_shot(question, ts, vi), version
    if style == "cot":
        return _build_cot(question, ts, vi), version
    if style == "task_decomposition":
        return _build_task_decomposition(question, ts, vi), version
    if style == "few_shot":
        return _build_few_shot(question, ts, vi), version
    raise ValueError(f"Unknown prompt_style={prompt_style!r}. Choose from {PROMPT_STYLES}.")


def _build_zero_shot(question: str, table_str: str, vi: bool) -> str:
    del vi  # Tất cả prompt TableQA dùng tiếng Việt để thống nhất với Open-ViTabQA.
    return (
        "Dựa vào bảng, trả lời câu hỏi. Nếu bảng không đủ thông tin, trả về null. "
        "Trả về đúng một JSON: {\"final_answer\":\"...\"}.\n\n"
        f"BẢNG:\n{table_str}\n\nCÂU HỎI: {question}\n"
    )


def _build_cot(question: str, table_str: str, vi: bool) -> str:
    del vi
    instr = (
        "Bạn là hệ thống hỏi–đáp dựa trên bảng. CHỈ được dùng TABLE_STR.\n"
        "\n"
        + _flatten_v1_notes_vi()
        + "\n"
        + _cot_schema_instructions_vi()
    )

    return f"{instr}\nBẢNG (TABLE_STR):\n{table_str}\n\nCÂU HỎI: {question}\n"


def _build_task_decomposition(question: str, table_str: str, vi: bool) -> str:
    del vi
    instr = (
        "Bạn là hệ thống hỏi–đáp dựa trên bảng. CHỈ được dùng TABLE_STR.\n"
        "\n"
        + _flatten_v1_notes_vi()
        + "\n"
        + _task_decomposition_schema_instructions_vi()
    )

    return f"{instr}\nBẢNG (TABLE_STR):\n{table_str}\n\nCÂU HỎI: {question}\n"


def _few_shot_examples_vi() -> str:
    return (
        "=== VÍ DỤ 1 ===\n"
        "BẢNG (TABLE_STR):\n"
        "Cù Chính Lan <header>|Dân tộc <header>|Kinh\n"
        "Cù Chính Lan <header>|Quê quán <header>|Nghệ An\n"
        "Cù Chính Lan <header>|Năm phong <header>|19/05/1952\n"
        "La Văn Cầu <header>|Dân tộc <header>|Tày\n"
        "La Văn Cầu <header>|Quê quán <header>|Cao Bằng\n"
        "La Văn Cầu <header>|Năm phong <header>|19/05/1952\n"
        "\n"
        "CÂU HỎI: Quê quán của La Văn Cầu là ở đâu?\n"
        'ĐẦU RA: {"final_answer": "Cao Bằng"}\n'
        "\n"
        "=== VÍ DỤ 2 ===\n"
        "BẢNG (TABLE_STR):\n"
        "Cù Chính Lan <header>|Dân tộc <header>|Kinh\n"
        "Cù Chính Lan <header>|Quê quán <header>|Nghệ An\n"
        "La Văn Cầu <header>|Dân tộc <header>|Tày\n"
        "La Văn Cầu <header>|Quê quán <header>|Cao Bằng\n"
        "\n"
        "CÂU HỎI: Có bao nhiêu người thuộc dân tộc Kinh trong số các người được liệt kê ở đây?\n"
        'ĐẦU RA: {"final_answer": "1"}\n'
        "\n"
        "=== VÍ DỤ 3 ===\n"
        "BẢNG (TABLE_STR):\n"
        "Cù Chính Lan <header>|Dân tộc <header>|Kinh\n"
        "Cù Chính Lan <header>|Quê quán <header>|Nghệ An\n"
        "La Văn Cầu <header>|Dân tộc <header>|Tày\n"
        "La Văn Cầu <header>|Quê quán <header>|Cao Bằng\n"
        "\n"
        "CÂU HỎI: Cù Chính Lan thuộc dân tộc Thái đúng không?\n"
        'ĐẦU RA: {"final_answer": "Không"}\n'
        "\n"
        "=== VÍ DỤ 4 ===\n"
        "BẢNG (TABLE_STR):\n"
        "Cù Chính Lan <header>|Dân tộc <header>|Kinh\n"
        "Cù Chính Lan <header>|Quê quán <header>|Nghệ An\n"
        "\n"
        "CÂU HỎI: Tổng thống nước Mỹ năm 2020 là ai?\n"
        'ĐẦU RA: {"final_answer": "Null"}\n'
    )


def _build_few_shot(question: str, table_str: str, vi: bool) -> str:
    del vi
    instr = (
        "Bạn là hệ thống hỏi–đáp dựa trên bảng.\n"
        "Bảng được cung cấp dưới dạng chuỗi Flatten V1 trong TABLE_STR.\n"
        "CHỈ được dùng thông tin trong TABLE_STR để trả lời.\n"
        "\n"
        + _flatten_v1_notes_vi()
        + "\n"
        + _json_schema_instructions_vi()
        + "\n"
        "DƯỚI ĐÂY LÀ CÁC VÍ DỤ MẪU VỀ CÁCH TRẢ LỜI:\n"
        + _few_shot_examples_vi()
        + "\n"
        "BÂY GIỜ ĐẾN LƯỢT BẠN TRẢ LỜI CÂU HỎI THỰC TẾ DỰA TRÊN TABLE_STR SAU ĐÂY.\n"
    )

    return f"{instr}\nBẢNG (TABLE_STR):\n{table_str}\n\nCÂU HỎI: {question}\nĐẦU RA: "


# Backward-compatible alias
PROMPT_VERSION_DIRECT = PROMPT_VERSION_ZERO_SHOT
PROMPT_VERSION_FLATTEN_V1 = PROMPT_VERSION_ZERO_SHOT
