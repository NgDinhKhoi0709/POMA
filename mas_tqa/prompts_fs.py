"""Prompt few-shot gốc `v3_fs_structured_vi`, chép nguyên văn từ baseline/prompts.py @ bb42794."""

from __future__ import annotations


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


