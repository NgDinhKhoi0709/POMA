"""Prompt cho dòng GPT-4.1 (azure-4.1, azure-4.1-mini).

Theo GPT-4.1 Prompting Guide: model tuân thủ chỉ dẫn sát nghĩa hơn GPT-4o, không tự suy ra ý.
Khung system là Vai trò, Hướng dẫn, Các bước suy luận, Định dạng, Ví dụ. Bảng dài bọc XML
(định dạng tài liệu dài được khuyến nghị). Ba ràng buộc dễ bị bỏ lặp lại sau câu hỏi.
Không dùng lời nhắc agentic kiểu "cứ làm đến khi xong": đây là một lượt hỏi đáp, không phải vòng công cụ.
"""

from __future__ import annotations

from .prompts_gpt import FORMATS, GPT_SAMPLE, GPT_SINGLE  # noqa: F401
from .prompts_layout import examples_block, messages, title_block

_RULES = """# Hướng dẫn
Làm đúng các mục sau. Không thêm quy tắc khác.
1. Chỉ dùng tên bảng và các ô trong bảng được đưa. Được so sánh, tính toán, và đọc ký hiệu ngay trong bảng.
2. Không dùng kiến thức ngoài bảng. Khi bảng không đủ thông tin, final_answer là đúng chuỗi Null.
3. final_answer chép đúng chuỗi của ô: cùng chữ, cùng số, đơn vị và tiền tố. Không thêm chủ ngữ. Không dịch chữ trong ô.
4. Câu hỏi Có/Không: đúng một từ, cùng kiểu các ví dụ (Có, Không, Đúng, Sai, Phải, Không phải).
5. Câu hỏi liệt kê: các phần tử cách nhau bởi dấu phẩy, theo thứ tự trong bảng, trừ khi câu hỏi yêu cầu sắp xếp.
6. Câu hỏi tính toán: phép tính nằm trong reason. final_answer chỉ là kết quả, đúng kiểu số của bảng.

# Các bước suy luận
reason là kế hoạch ngắn: nêu ô đã dùng, rồi phép tính nếu có. Tối đa 2 câu tiếng Việt. Viết reason trước final_answer.

# Định dạng đầu ra
Một JSON object đúng schema. Không có văn bản ngoài JSON."""

_FINAL = (
    "Chỉ dùng bảng trong tin nhắn này. "
    "Nếu bảng không đủ thông tin, final_answer là Null. "
    "final_answer chép đúng kiểu ô, không dịch."
)

_SYSTEM_A = (
    "# Vai trò và mục tiêu\n"
    "Bạn là agent A. Mục tiêu duy nhất của lượt này: trả lời một câu hỏi tiếng Việt từ đúng bảng được đưa.\n\n"
    "# Định dạng bảng\n"
    "Bảng nằm trong thẻ bảng. Mỗi dòng là các ô cách nhau bởi dấu |. "
    "Ô có hậu tố \"<header>\" là tiêu đề cột hoặc tiêu đề hàng. Ô còn lại là giá trị.\n\n"
    + _RULES
    + "\n\n# Ví dụ hình dạng\n"
    '{"reason": "Ô cột Năm ở hàng 1 là 2012.", "final_answer": "2012"}'
)

_SYSTEM_B = (
    "# Vai trò và mục tiêu\n"
    "Bạn là agent B. Mục tiêu duy nhất của lượt này: trả lời một câu hỏi tiếng Việt từ đúng bảng được đưa, "
    "và chép ô bằng chứng trước khi kết luận.\n\n"
    "# Định dạng bảng\n"
    "Bảng nằm trong thẻ bảng. Mỗi khối bắt đầu bằng \"## Hàng i\". "
    "Mỗi dòng trong khối có dạng \"Tên cột: giá trị\".\n\n"
    + _RULES
    + "\n\n# Ví dụ hình dạng\n"
    '{"evidence": ["Năm: 2012"], "reason": "Ô Năm của hàng 1 là 2012.", "final_answer": "2012"}'
)

_OUT_A = _FINAL
_OUT_B = _FINAL

SCORE_TASK = (
    "Đối chiếu từng ứng viên với bảng. Có thể một ứng viên đúng, hoặc tất cả đều sai. "
    "Mỗi ứng viên nhận một xác suất đúng. Các xác suất cộng lại bằng 1. "
    "Ứng viên đúng phải khớp ô và cùng cách viết với các đáp án mẫu. "
    "Điểm nằm trong JSON đúng schema, không có văn bản ngoài JSON.\n"
)


def messages_a(qa: dict, k: int = 16, memory: bool = True) -> list[dict]:
    return messages(_SYSTEM_A, qa, k, memory, _OUT_A, table="flat")


def messages_b(qa: dict, k: int = 8, memory: bool = True) -> list[dict]:
    return messages(_SYSTEM_B, qa, k, memory, _OUT_B, table="kv")


def messages_fs(qa: dict, examples: bool = True) -> list[dict]:
    system = _SYSTEM_A.replace("Bạn là agent A.", "Bạn là hệ thống hỏi đáp trên bảng.")
    return messages(system, qa, 0, False, _OUT_A, table="flat", force_generic=examples, skip_examples=not examples)


def messages_zs(qa: dict) -> list[dict]:
    return messages_fs(qa, examples=False)
