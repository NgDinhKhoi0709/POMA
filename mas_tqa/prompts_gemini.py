"""Prompt cho dòng Gemini 2.5, gồm Flash-Lite.

Gemini 2.5 suy nghĩ nội bộ trước khi trả lời, và token suy nghĩ trừ vào max_completion_tokens,
nên JSON bị cắt nếu không tắt thinking. Schema nằm ở response_format; prompt không chép lại
khung JSON (Google khuyến nghị không lặp schema trong lời nhắc). Mô tả trường nằm trong schema.
Flash-Lite cần chỉ dẫn ngắn và một câu khoá ngôn ngữ tiếng Việt.
"""

from __future__ import annotations

from .prompts_gpt import FORMATS
from .prompts_layout import messages

_THINKING_OFF = {"reasoning_effort": "none"}
SINGLE = {"temperature": 0.0, "max_completion_tokens": 1024, "extra_body": _THINKING_OFF}
SAMPLE = {"temperature": 0.7, "max_completion_tokens": 1024, "extra_body": _THINKING_OFF}

_SYSTEM_A = (
    "Bạn là agent A. Trả lời một câu hỏi tiếng Việt chỉ từ bảng Wikipedia dạng Flatten V1. "
    "Mỗi dòng là các ô cách nhau bởi dấu |. Ô có hậu tố \"<header>\" là tiêu đề.\n"
    "Chỉ dùng tên bảng và các ô. Được so sánh, tính toán, đọc ký hiệu trong bảng. "
    "Không dùng kiến thức ngoài. Không đủ thông tin thì final_answer là Null. "
    "final_answer chép đúng chuỗi ô, không thêm chủ ngữ, không dịch. "
    "Có/Không là một từ cùng kiểu các ví dụ. Liệt kê cách nhau bởi dấu phẩy, theo thứ tự trong bảng. "
    "Phép tính nằm trong reason; final_answer chỉ là kết quả. "
    "reason tối đa 2 câu tiếng Việt."
)

_SYSTEM_B = (
    "Bạn là agent B. Trả lời một câu hỏi tiếng Việt chỉ từ bảng dạng Markdown-KV. "
    "Mỗi khối bắt đầu bằng \"## Hàng i\". Mỗi dòng có dạng \"Tên cột: giá trị\". "
    "Chép các ô đã dùng vào evidence.\n"
    "Chỉ dùng tên bảng và các ô. Không dùng kiến thức ngoài. Không đủ thông tin thì final_answer là Null. "
    "final_answer chép đúng chuỗi ô, không dịch. reason tối đa 2 câu tiếng Việt."
)

_OUT_A = "Trả lời bằng tiếng Việt. Chỉ dùng bảng này. Thiếu thông tin thì final_answer là Null."
_OUT_B = _OUT_A

SCORE_TASK = (
    "Đối chiếu từng ứng viên với bảng. Có thể một ứng viên đúng hoặc tất cả đều sai. "
    "Cho mỗi id một xác suất p. Các p cộng lại bằng 1. Viết bằng tiếng Việt nếu có chữ.\n"
)


def messages_a(qa: dict, k: int = 16, memory: bool = True) -> list[dict]:
    return messages(_SYSTEM_A, qa, k, memory, _OUT_A, table="flat", wrap="markdown")


def messages_b(qa: dict, k: int = 8, memory: bool = True) -> list[dict]:
    return messages(_SYSTEM_B, qa, k, memory, _OUT_B, table="kv", wrap="markdown")


def messages_fs(qa: dict, examples: bool = True) -> list[dict]:
    system = _SYSTEM_A.replace("Bạn là agent A.", "Bạn là hệ thống hỏi đáp trên bảng.")
    return messages(system, qa, 0, False, _OUT_A, table="flat", wrap="markdown", force_generic=examples, skip_examples=not examples)


def messages_zs(qa: dict) -> list[dict]:
    return messages_fs(qa, examples=False)
