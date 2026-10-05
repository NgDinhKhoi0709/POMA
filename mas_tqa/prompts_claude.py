"""Prompt cho dòng Claude, gồm Haiku 4.5.

Claude tách nội dung bằng thẻ XML khi một tin nhắn trộn chỉ dẫn, bảng và ví dụ.
Claude 4 trả lời ngắn và sát chữ; cấm lời dẫn trước JSON vì proxy này không prefill được dấu {.
Lượt thử json_schema strict trên claude-haiku-4-5 trả về {} nên dòng này dùng JSON mode
và nêu đủ khoá trong prompt. Không bật extended thinking: ngân sách đó nuốt token của đáp án.
"""

from __future__ import annotations

from .prompts_layout import messages

_JSON = {"type": "json_object"}
SINGLE = {"temperature": 0.0, "max_tokens": 512, "response_format": _JSON}
SAMPLE = {"temperature": 0.7, "max_tokens": 512, "response_format": _JSON}
FORMATS = {"A": _JSON, "B": _JSON, "V": _JSON}

_RULES = """<quy_tắc>
1. Chỉ dùng tên bảng và các ô trong thẻ bảng. Được so sánh, tính toán, và đọc ký hiệu trong bảng.
2. Không dùng kiến thức ngoài bảng. Khi không đủ thông tin, final_answer là Null.
3. final_answer chép đúng chuỗi của ô. Không thêm chủ ngữ. Không dịch.
4. Câu hỏi Có/Không: một từ, cùng kiểu các ví dụ.
5. Câu hỏi liệt kê: cách nhau bởi dấu phẩy, theo thứ tự trong bảng, trừ khi câu hỏi yêu cầu sắp xếp.
6. Câu hỏi tính toán: phép tính nằm trong reason. final_answer chỉ là kết quả.
</quy_tắc>
<suy_luận>reason tối đa 2 câu tiếng Việt và đứng trước final_answer.</suy_luận>
<đầu_ra>Chỉ một JSON. Bắt đầu ngay bằng dấu {. Không có lời dẫn, không có markdown.</đầu_ra>"""

_SYSTEM_A = (
    "<vai_trò>Bạn là agent A. Trả lời một câu hỏi tiếng Việt từ đúng bảng được đưa.</vai_trò>\n"
    "<định_dạng_bảng>Mỗi dòng là các ô cách nhau bởi dấu |. "
    "Ô có hậu tố header trong dấu &lt; &gt; là tiêu đề. Ô còn lại là giá trị.</định_dạng_bảng>\n"
    + _RULES
    + "\n<ví_dụ_hình_dạng>{\"reason\": \"Ô cột Năm ở hàng 1 là 2012.\", \"final_answer\": \"2012\"}</ví_dụ_hình_dạng>"
)

_SYSTEM_B = (
    "<vai_trò>Bạn là agent B. Trả lời một câu hỏi tiếng Việt từ đúng bảng được đưa. "
    "Chép ô bằng chứng vào evidence trước khi kết luận.</vai_trò>\n"
    "<định_dạng_bảng>Mỗi khối bắt đầu bằng \"## Hàng i\". "
    "Mỗi dòng có dạng \"Tên cột: giá trị\".</định_dạng_bảng>\n"
    + _RULES
    + "\n<ví_dụ_hình_dạng>{\"evidence\": [\"Năm: 2012\"], \"reason\": \"Ô Năm của hàng 1 là 2012.\", "
    "\"final_answer\": \"2012\"}</ví_dụ_hình_dạng>"
)

_OUT_A = "Thiếu thông tin thì final_answer là Null. Chép đúng ô. Bắt đầu bằng dấu {."
_OUT_B = _OUT_A

SCORE_TASK = (
    "Đối chiếu từng ứng viên với bảng. Có thể một ứng viên đúng hoặc tất cả đều sai. "
    "Cho mỗi ứng viên một xác suất đúng. Tổng bằng 1. "
    "Trả về JSON bắt đầu bằng dấu {, đúng khoá scores. Mỗi phần tử có id và p.\n"
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
