"""Prompt cho GPT-4o mini (proxy Azure, model id `azure-4o-mini`).

GPT-4o mini không có kênh suy nghĩ ẩn, nên lý do nằm trong JSON và đứng trước đáp án.
Một đáp án dùng temperature 0. Ba mẫu agent A dùng temperature 0.7, không gửi top_p.
Đầu ra khoá bằng json_schema strict. Không gửi top_k, min_p, chat_template_kwargs.
"""

from __future__ import annotations

import re

from .data import MEMORY_SCOPE, retrieve_same_table, table_str, tables

GPT_SINGLE = {"temperature": 0.0, "max_completion_tokens": 512}
GPT_SAMPLE = {"temperature": 0.7, "max_completion_tokens": 512}


def _schema(name: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": properties,
                "required": required,
            },
        },
    }


_REASON = {"type": "string", "description": "Tối đa 2 câu tiếng Việt: hàng, cột, ô đã dùng và phép tính nếu có."}
_ANSWER = {"type": "string", "description": "Đáp án chép đúng kiểu ô trong bảng, hoặc chuỗi Null."}
FORMATS = {
    "A": _schema("table_answer", {"reason": _REASON, "final_answer": _ANSWER}, ["reason", "final_answer"]),
    "B": _schema(
        "table_answer_evidence",
        {
            "evidence": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Các ô chép nguyên văn, dùng để trả lời.",
            },
            "reason": _REASON,
            "final_answer": _ANSWER,
        },
        ["evidence", "reason", "final_answer"],
    ),
    "V": _schema(
        "candidate_scores",
        {
            "scores": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "integer", "description": "Số thứ tự in trên ứng viên."},
                        "p": {"type": "number", "description": "Xác suất ứng viên đúng, từ 0 đến 1."},
                    },
                    "required": ["id", "p"],
                },
            }
        },
        ["scores"],
    ),
}

_RULES = """# Quy tắc
1. Chỉ dùng tên bảng và các ô. Được so sánh, tính toán, và suy từ ký hiệu trong bảng. Không dùng kiến thức ngoài bảng.
2. Nếu bảng không đủ thông tin, final_answer là "Null".
3. final_answer chép đúng kiểu ô: cùng chữ, số, đơn vị và tiền tố. Không thêm chủ ngữ. Không dịch chữ trong ô.
4. Câu hỏi Có/Không: đúng một từ, cùng kiểu các ví dụ (Có/Không, Đúng/Sai, Phải/Không phải).
5. Câu hỏi liệt kê: các phần tử cách nhau bởi dấu phẩy, theo thứ tự trong bảng, trừ khi câu hỏi yêu cầu sắp xếp.
6. Câu hỏi tính toán: ghi phép tính trong reason; final_answer chỉ là kết quả, đúng kiểu số của bảng.

# Suy luận
Viết reason bằng tối đa 2 câu tiếng Việt, rồi mới ghi final_answer. Không văn bản ngoài JSON."""

_TAG = "ví_dụ_cùng_bảng"
_REMIND = "Chỉ dùng bảng trên. Thiếu thông tin thì final_answer là \"Null\". Chép đúng kiểu ô. Chỉ một JSON."
if MEMORY_SCOPE == "cross":
    _RULES = _RULES.replace("cùng kiểu các ví dụ", "cùng kiểu các ví dụ đã cho")
    _TAG = "ví_dụ_từ_bảng_khác"

_SYSTEM_A = (
    "# Vai trò\nBạn là agent A, trả lời câu hỏi tiếng Việt trên một bảng Wikipedia.\n\n"
    "# Định dạng bảng\nMỗi dòng là các ô cách nhau bởi dấu |. Ô có hậu tố \"<header>\" là tiêu đề cột hoặc "
    "tiêu đề hàng; ô còn lại là giá trị.\n\n" + _RULES + "\n\n# Ví dụ hình dạng\n"
    '{"reason": "Ô cột Năm ở hàng 1 là 2012.", "final_answer": "2012"}'
)

_SYSTEM_B = (
    "# Vai trò\nBạn là agent B, trả lời câu hỏi tiếng Việt trên một bảng Wikipedia. "
    "Trích ô bằng chứng trước khi kết luận.\n\n"
    "# Định dạng bảng\nBảng gồm các khối \"## Hàng i\". Mỗi dòng trong khối có dạng \"Tên cột: giá trị\".\n\n"
    + _RULES + "\n\n# Ví dụ hình dạng\n"
    '{"evidence": ["Năm: 2012"], "reason": "Ô Năm của hàng 1 là 2012.", "final_answer": "2012"}'
)

_OUT_A = _REMIND
_OUT_B = _REMIND

SCORE_TASK = (
    "NHIỆM VỤ: các đáp án ứng viên dưới đây do agent khác đưa ra. Có thể một ứng viên đúng, hoặc tất cả đều sai. "
    "Đối chiếu từng ứng viên với bảng. Cho mỗi ứng viên một xác suất đúng. Các xác suất cộng lại bằng 1. "
    "Đáp án đúng phải khớp ô trong bảng và cùng cách viết với các đáp án mẫu.\n"
    "Trả về một JSON object đúng khoá scores. Mỗi phần tử có id là số thứ tự in trên ứng viên và p từ 0 đến 1.\n"
)


def _title(qa: dict) -> str:
    name = re.sub(r"_\d+$", "", str(tables()[qa["table_id"]].get("table_title") or "")).strip()
    return f"# Tên bảng\n{name}\n\n" if name else ""


def _examples(qa: dict, k: int, memory: bool = True) -> str:
    if not memory:
        from .prompts_fs import _few_shot_examples_vi

        return f"# Ví dụ chung\n{_few_shot_examples_vi().strip()}\n"
    rows = "\n".join(f"Câu hỏi: {d['question']}\nĐáp án: {d['answer']}" for d in retrieve_same_table(qa, k))
    heading = "Ví dụ từ bảng khác" if MEMORY_SCOPE == "cross" else "Ví dụ cùng bảng"
    return f"# {heading}\n{rows}\n"


def _question(qa: dict, out: str) -> str:
    return f"# Câu hỏi\n{qa['question']}\n\n# Nhắc lại\n{out}"


def messages_a(qa: dict, k: int = 16, memory: bool = True) -> list[dict]:
    user = f"{_title(qa)}# Bảng\n{table_str(qa['table_id'])}\n\n{_examples(qa, k, memory)}\n{_question(qa, _OUT_A)}"
    return [{"role": "system", "content": _SYSTEM_A}, {"role": "user", "content": user}]


def messages_b(qa: dict, k: int = 8, memory: bool = True) -> list[dict]:
    from .methods import kv_str

    user = f"{_title(qa)}# Bảng\n{kv_str(qa['table_id'])}\n\n{_examples(qa, k, memory)}\n{_question(qa, _OUT_B)}"
    return [{"role": "system", "content": _SYSTEM_B}, {"role": "user", "content": user}]


def messages_fs(qa: dict, examples: bool = True) -> list[dict]:
    demos = f"{_examples(qa, 0, memory=False)}\n" if examples else ""
    user = f"{demos}{_title(qa)}# Bảng\n{table_str(qa['table_id'])}\n\n{_question(qa, _OUT_A)}"
    system = _SYSTEM_A.replace("Bạn là agent A, trả lời", "Bạn là hệ thống trả lời")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def messages_zs(qa: dict) -> list[dict]:
    return messages_fs(qa, examples=False)
