from __future__ import annotations

from typing import Final, Tuple

# Stored in JSONL as prompt_version (stable ids for experiments / analysis).
PROMPT_VERSION_ZERO_SHOT = "v3_zs_minimal"
PROMPT_VERSION_COT = "v2_cot_structured"
PROMPT_VERSION_TASK_DECOMPOSITION = "v2_td_structured"
PROMPT_VERSION_FEW_SHOT = "v2_fs_structured"

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
        "GHI CHU DINH DANG TABLE_STR (FLATTEN V1):\n"
        "- Moi dong co dang: row_header|column_header|value.\n"
        "- Header hang va header cot luon co hau to '<header>'.\n"
        "- Gia tri o du lieu la thanh phan thu ba cua moi dong.\n"
    )


def _flatten_v1_notes_en() -> str:
    return (
        "TABLE_STR FORMAT (FLATTEN V1):\n"
        "- Each line: row_header|column_header|value.\n"
        "- Row/column headers end with '<header>'.\n"
        "- Cell value is the third field.\n"
    )


def _json_schema_instructions_vi() -> str:
    return (
        "DAU RA (BAT BUOC): Mot JSON hop le duy nhat (co the boc trong khoi ```json ... ```).\n"
        "Khong them van ban ngoai JSON (hoac ngoai khoi ```json).\n"
        "Schema:\n"
        '  {"final_answer": "<mot gia tri ngan gon; hoac chuoi Null khi khong du thong tin trong bang>"}\n'
        "Khong xuat reasoning. Khong xuat suy luan noi bo.\n"
        "Tuyet doi khong dung the <think> hoac </think>.\n"
        "Quy tac final_answer (rut gon, phu hop danh gia EM):\n"
        "- Chi dua TABLE_STR; khong bia; khong lap nguyen cau hoi.\n"
        "- Mot gia tri ngan (so, ten, Co/Khong, ...); dung Null (chuoi) neu khong tra loi duoc.\n"
        "- Khong markdown trong final_answer.\n"
        "Vi du mot dong: "
        '{"final_answer":"42"}\n'
    )


def _json_schema_instructions_en() -> str:
    return (
        "OUTPUT (MANDATORY): Exactly one valid JSON object (may be wrapped in ```json ... ```).\n"
        "No text outside JSON (except optional ```json fence).\n"
        "Schema:\n"
        '  {"final_answer": "<short single value; or Null if insufficient table data>"}\n'
        "Do not return reasoning. Do not reveal internal thinking.\n"
        "Never output <think> or </think>.\n"
        "final_answer rules: table-only; no fabrication; do not repeat the question; no markdown in final_answer.\n"
        "Example: "
        '{"final_answer":"42"}\n'
    )


def _cot_schema_instructions_vi() -> str:
    return (
        "DAU RA (BAT BUOC): Mot JSON hop le duy nhat (co the boc trong khoi ```json ... ```).\n"
        "Khong them van ban ngoai JSON (hoac ngoai khoi ```json).\n"
        "Schema:\n"
        '  {"reasoning": "<giai thich ngan gon, co the kiem tra tu bang>", '
        '"final_answer": "<mot gia tri ngan gon; hoac chuoi Null khi khong du thong tin trong bang>"}\n'
        "reasoning la ly do ngan gon, co the kiem tra; chi neu hang/cot hoac phep tinh can thiet.\n"
        "Khong xuat suy luan rieng tu hoac tung buoc suy nghi chi tiet.\n"
        "final_answer chi dua TABLE_STR, khong markdown, va dung Null neu khong tra loi duoc.\n"
    )


def _cot_schema_instructions_en() -> str:
    return (
        "OUTPUT (MANDATORY): Exactly one valid JSON object (may be wrapped in ```json ... ```).\n"
        "No text outside JSON (except optional ```json fence).\n"
        "Schema:\n"
        '  {"reasoning": "<concise, auditable table-grounded rationale>", '
        '"final_answer": "<short single value; or Null if insufficient table data>"}\n'
        "reasoning is a concise auditable rationale: name only the relevant table facts or calculation.\n"
        "Do not provide private or detailed step-by-step thinking.\n"
        "final_answer is table-only, has no markdown, and is Null if the table is insufficient.\n"
    )


def _task_decomposition_schema_instructions_vi() -> str:
    return (
        "DAU RA (BAT BUOC): Mot JSON hop le duy nhat (co the boc trong khoi ```json ... ```).\n"
        "Khong them van ban ngoai JSON (hoac ngoai khoi ```json).\n"
        "Schema:\n"
        '  {"subproblems": ["<nhiem vu ngan gon>"], '
        '"reasoning": "<giai thich ngan gon, co the kiem tra tu bang>", '
        '"final_answer": "<mot gia tri ngan gon; hoac chuoi Null khi khong du thong tin trong bang>"}\n'
        "subproblems la danh sach cac nhiem vu ngan gon de tra loi cau hoi.\n"
        "reasoning la ly do ngan gon, co the kiem tra; chi neu hang/cot hoac phep tinh can thiet.\n"
        "Khong xuat suy luan rieng tu hoac tung buoc suy nghi chi tiet.\n"
        "final_answer chi dua TABLE_STR, khong markdown, va dung Null neu khong tra loi duoc.\n"
    )


def _task_decomposition_schema_instructions_en() -> str:
    return (
        "OUTPUT (MANDATORY): Exactly one valid JSON object (may be wrapped in ```json ... ```).\n"
        "No text outside JSON (except optional ```json fence).\n"
        "Schema:\n"
        '  {"subproblems": ["<short task>"], '
        '"reasoning": "<concise, auditable table-grounded rationale>", '
        '"final_answer": "<short single value; or Null if insufficient table data>"}\n'
        "subproblems is a list of short tasks needed to answer the question.\n"
        "reasoning is a concise auditable rationale: name only the relevant table facts or calculation.\n"
        "Do not provide private or detailed step-by-step thinking.\n"
        "final_answer is table-only, has no markdown, and is Null if the table is insufficient.\n"
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
    if vi:
        instr = "Dua vao bang, tra loi cau hoi. Neu bang khong du thong tin, tra ve null."
        table_label = "BANG"
        question_label = "CAU HOI"
    else:
        instr = "Answer the question using the table. Return null if the table lacks enough information."
        table_label = "TABLE"
        question_label = "QUESTION"

    return f"{instr}\n\n{table_label}:\n{table_str}\n\n{question_label}: {question}\n"


def _build_cot(question: str, table_str: str, vi: bool) -> str:
    if vi:
        instr = (
            "Ban la he thong hoi-dap dua tren bang. CHI duoc dung TABLE_STR.\n"
            "\n"
            + _flatten_v1_notes_vi()
            + "\n"
            + _cot_schema_instructions_vi()
        )
    else:
        instr = (
            "You are a table QA system. Use ONLY TABLE_STR.\n"
            + _flatten_v1_notes_en()
            + "\n"
            + _cot_schema_instructions_en()
        )

    return f"{instr}\nTABLE_STR:\n{table_str}\n\nQUESTION: {question}\n"


def _build_task_decomposition(question: str, table_str: str, vi: bool) -> str:
    if vi:
        instr = (
            "Ban la he thong hoi-dap dua tren bang. CHI duoc dung TABLE_STR.\n"
            "\n"
            + _flatten_v1_notes_vi()
            + "\n"
            + _task_decomposition_schema_instructions_vi()
        )
    else:
        instr = (
            "Table QA using ONLY TABLE_STR.\n"
            + _flatten_v1_notes_en()
            + "\n"
            + _task_decomposition_schema_instructions_en()
        )

    return f"{instr}\nTABLE_STR:\n{table_str}\n\nQUESTION: {question}\n"


def _few_shot_examples_vi() -> str:
    return (
        "=== VI DU 1 ===\n"
        "TABLE_STR:\n"
        "Cù Chính Lan <header>|Dân tộc <header>|Kinh\n"
        "Cù Chính Lan <header>|Quê quán <header>|Nghệ An\n"
        "Cù Chính Lan <header>|Năm phong <header>|19/05/1952\n"
        "La Văn Cầu <header>|Dân tộc <header>|Tày\n"
        "La Văn Cầu <header>|Quê quán <header>|Cao Bằng\n"
        "La Văn Cầu <header>|Năm phong <header>|19/05/1952\n"
        "\n"
        "QUESTION: Quê quán của La Văn Cầu là ở đâu?\n"
        'OUTPUT: {"final_answer": "Cao Bằng"}\n'
        "\n"
        "=== VI DU 2 ===\n"
        "TABLE_STR:\n"
        "Cù Chính Lan <header>|Dân tộc <header>|Kinh\n"
        "Cù Chính Lan <header>|Quê quán <header>|Nghệ An\n"
        "La Văn Cầu <header>|Dân tộc <header>|Tày\n"
        "La Văn Cầu <header>|Quê quán <header>|Cao Bằng\n"
        "\n"
        "QUESTION: Có bao nhiêu người thuộc dân tộc Kinh trong số các người được liệt kê ở đây?\n"
        'OUTPUT: {"final_answer": "1"}\n'
        "\n"
        "=== VI DU 3 ===\n"
        "TABLE_STR:\n"
        "Cù Chính Lan <header>|Dân tộc <header>|Kinh\n"
        "Cù Chính Lan <header>|Quê quán <header>|Nghệ An\n"
        "La Văn Cầu <header>|Dân tộc <header>|Tày\n"
        "La Văn Cầu <header>|Quê quán <header>|Cao Bằng\n"
        "\n"
        "QUESTION: Cù Chính Lan thuộc dân tộc Thái đúng không?\n"
        'OUTPUT: {"final_answer": "Không"}\n'
        "\n"
        "=== VI DU 4 ===\n"
        "TABLE_STR:\n"
        "Cù Chính Lan <header>|Dân tộc <header>|Kinh\n"
        "Cù Chính Lan <header>|Quê quán <header>|Nghệ An\n"
        "\n"
        "QUESTION: Tổng thống nước Mỹ năm 2020 là ai?\n"
        'OUTPUT: {"final_answer": "Null"}\n'
    )


def _few_shot_examples_en() -> str:
    return (
        "=== EXAMPLE 1 ===\n"
        "TABLE_STR:\n"
        "Cù Chính Lan <header>|Ethnicity <header>|Kinh\n"
        "Cù Chính Lan <header>|Hometown <header>|Nghe An\n"
        "La Văn Cầu <header>|Ethnicity <header>|Tay\n"
        "La Văn Cầu <header>|Hometown <header>|Cao Bang\n"
        "\n"
        "QUESTION: Where is the hometown of La Văn Cầu?\n"
        'OUTPUT: {"final_answer": "Cao Bang"}\n'
        "\n"
        "=== EXAMPLE 2 ===\n"
        "TABLE_STR:\n"
        "Cù Chính Lan <header>|Ethnicity <header>|Kinh\n"
        "Cù Chính Lan <header>|Hometown <header>|Nghe An\n"
        "La Văn Cầu <header>|Ethnicity <header>|Tay\n"
        "La Văn Cầu <header>|Hometown <header>|Cao Bang\n"
        "\n"
        "QUESTION: Is Cù Chính Lan of Tay ethnicity?\n"
        'OUTPUT: {"final_answer": "No"}\n'
        "\n"
        "=== EXAMPLE 3 ===\n"
        "TABLE_STR:\n"
        "Cù Chính Lan <header>|Ethnicity <header>|Kinh\n"
        "Cù Chính Lan <header>|Hometown <header>|Nghe An\n"
        "\n"
        "QUESTION: Who is the US President in 2020?\n"
        'OUTPUT: {"final_answer": "Null"}\n'
    )


def _build_few_shot(question: str, table_str: str, vi: bool) -> str:
    if vi:
        instr = (
            "Ban la he thong hoi-dap dua tren bang.\n"
            "Bang duoc cung cap duoi dang Flatten V1 string trong TABLE_STR.\n"
            "CHI duoc dung thong tin trong TABLE_STR de tra loi.\n"
            "\n"
            + _flatten_v1_notes_vi()
            + "\n"
            + _json_schema_instructions_vi()
            + "\n"
            "DUOI DAY LA CAC VI DU MAU VE CACH TRA LOI (FEW-SHOT EXAMPLES):\n"
            + _few_shot_examples_vi()
            + "\n"
            "BAY GIO DEN LUOT BAN TRA LOI CAU HOI THUC TE DUA TREN TABLE_STR SAU DAY.\n"
        )
    else:
        instr = (
            "You are a table question-answering system.\n"
            "The table is provided as Flatten V1 string in TABLE_STR.\n"
            "Use ONLY TABLE_STR to answer.\n"
            "\n"
            + _flatten_v1_notes_en()
            + "\n"
            + _json_schema_instructions_en()
            + "\n"
            "HERE ARE SOME FEW-SHOT EXAMPLES:\n"
            + _few_shot_examples_en()
            + "\n"
            "NOW IT IS YOUR TURN. ANSWER THE REAL QUESTION BASED ON THE FOLLOWING TABLE_STR.\n"
        )

    return f"{instr}\nTABLE_STR:\n{table_str}\n\nQUESTION: {question}\nOUTPUT: "


# Backward-compatible alias
PROMPT_VERSION_DIRECT = PROMPT_VERSION_ZERO_SHOT
PROMPT_VERSION_FLATTEN_V1 = PROMPT_VERSION_ZERO_SHOT
