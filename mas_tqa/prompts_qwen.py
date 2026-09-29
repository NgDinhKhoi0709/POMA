"""Prompt cho agent A/B viết theo Best Practices của Qwen3-8B (model card chính thức, Hugging Face).

- Thinking mode: temperature 0.6, top_p 0.95, top_k 20, min_p 0; KHÔNG greedy (dễ lặp vô hạn).
- Độ dài đầu ra đủ lớn (khuyến nghị 32.768): để vLLM tự dùng phần ngữ cảnh còn lại (max_tokens=None).
- Chuẩn hoá đầu ra: yêu cầu đáp án nằm trong một trường JSON cố định (như ví dụ "answer": "C" của Qwen).
- Không cấm suy luận: model tự suy nghĩ trong <think>, prompt chỉ quy định phần trả lời cuối.
Quy tắc cố định để ở system message (dùng chung mọi câu → tận dụng prefix cache); dữ liệu dài (bảng, câu mẫu)
đặt trước, câu hỏi và yêu cầu định dạng đặt cuối user message.
"""

from __future__ import annotations

import re

from .data import retrieve_same_table, table_str, tables

QWEN_THINKING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "min_p": 0.0, "max_tokens": None}

_RULES = """<quy_tắc>
1. Chỉ dựa vào thông tin trong bảng và tên bảng. Được suy luận từ các thông tin đó (so sánh, tính toán, suy ra từ tên bảng, ký hiệu hay ngữ cảnh của bảng); không dùng kiến thức bên ngoài bảng.
2. Chỉ kết luận khi bảng có đủ thông tin để trả lời. Nếu không đủ thông tin (kể cả khi câu hỏi hỏi lý do hoặc cách thức mà bảng không ghi, hoặc câu hỏi giả định một điều không đúng với bảng), final_answer là "Null".
3. Đáp án ngắn gọn, viết đúng phong cách các ví dụ cùng bảng: chép nguyên văn giá trị ô, giữ cùng kiểu viết số, đơn vị, tiền tố (ví dụ "Năm 2012" hay "2012") như ví dụ; không thêm chủ ngữ hay diễn giải.
4. Câu hỏi Có/Không: trả lời đúng một từ, dùng cùng từ mà các ví dụ cùng bảng dùng (Có/Không, Đúng/Sai, Phải/Không phải).
5. Câu hỏi liệt kê: các phần tử cách nhau bởi dấu phẩy, theo thứ tự xuất hiện trong bảng trừ khi câu hỏi yêu cầu sắp xếp.
6. Câu hỏi tính toán: tính cẩn thận từ các ô liên quan; đáp án là con số cuối cùng, viết theo kiểu số của bảng.
</quy_tắc>"""

_SYSTEM_A = (
    "Bạn là agent A trong một hệ nhiều agent trả lời câu hỏi tiếng Việt trên bảng Wikipedia. "
    "Bạn đọc bảng ở định dạng Flatten V1.\n\n"
    "<định_dạng_bảng>\nMỗi dòng của bảng là các ô cách nhau bởi dấu |. Ô có hậu tố \"<header>\" là tiêu đề "
    "(tiêu đề cột ở dòng đầu, hoặc tiêu đề hàng ở đầu dòng); các ô còn lại là giá trị.\n</định_dạng_bảng>\n\n"
    + _RULES
)

_SYSTEM_B = (
    "Bạn là agent B trong một hệ nhiều agent trả lời câu hỏi tiếng Việt trên bảng Wikipedia. "
    "Bạn đọc bảng ở định dạng Markdown-KV và phải chỉ ra bằng chứng trước khi kết luận.\n\n"
    "<định_dạng_bảng>\nBảng được viết thành từng khối \"## Hàng i\"; mỗi dòng trong khối có dạng "
    "\"Tên cột: giá trị\".\n</định_dạng_bảng>\n\n"
    + _RULES
)

_OUT_A = ('Trả lời bằng đúng một đối tượng JSON, không kèm văn bản nào khác:\n'
          '{"reason": "<tối đa 2 câu: dùng hàng/cột/ô nào và suy ra đáp án thế nào>", "final_answer": "<đáp án hoặc Null>"}')
_OUT_B = ('Trả lời bằng đúng một đối tượng JSON, không kèm văn bản nào khác:\n'
          '{"evidence": ["<chép nguyên văn các ô dùng để trả lời>"], "reason": "<tối đa 2 câu>", '
          '"final_answer": "<đáp án hoặc Null>"}')


def _title(qa: dict) -> str:
    """Tên trang Wikipedia chứa bảng (bỏ hậu tố số thứ tự bảng "_0")."""
    name = re.sub(r"_\d+$", "", str(tables()[qa["table_id"]].get("table_title") or "")).strip()
    return f"<tên_bảng>{name}</tên_bảng>\n" if name else ""


def _examples(qa: dict, k: int, memory: bool = True) -> str:
    """memory=False (ablation): thay câu mẫu cùng bảng bằng ví dụ chung của prompt few-shot gốc."""
    if not memory:
        from .prompts_fs import _few_shot_examples_vi

        return f"<ví_dụ_chung>\n{_few_shot_examples_vi().strip()}\n</ví_dụ_chung>"
    rows = "\n".join(f"CÂU HỎI: {d['question']}\nĐÁP ÁN: {d['answer']}" for d in retrieve_same_table(qa, k))
    return f"<ví_dụ_cùng_bảng>\n{rows}\n</ví_dụ_cùng_bảng>"


def _question(qa: dict, out: str) -> str:
    return f"<câu_hỏi>\n{qa['question']}\n</câu_hỏi>\n\n{out}"


def messages_a(qa: dict, k: int = 16, memory: bool = True) -> list[dict]:
    user = f"{_title(qa)}<bảng>\n{table_str(qa['table_id'])}\n</bảng>\n\n{_examples(qa, k, memory)}\n\n{_question(qa, _OUT_A)}"
    return [{"role": "system", "content": _SYSTEM_A}, {"role": "user", "content": user}]


def messages_b(qa: dict, k: int = 8, memory: bool = True) -> list[dict]:
    from .methods import kv_str

    user = f"{_title(qa)}<bảng>\n{kv_str(qa['table_id'])}\n</bảng>\n\n{_examples(qa, k, memory)}\n\n{_question(qa, _OUT_B)}"
    return [{"role": "system", "content": _SYSTEM_B}, {"role": "user", "content": user}]


def messages_fs(qa: dict, examples: bool = True) -> list[dict]:
    """Baseline few-shot cùng khung prompt với agent A (system, bảng Flatten V1, định dạng đầu ra, tham số lấy mẫu),
    chỉ thay câu mẫu cùng bảng bằng các ví dụ chung của prompt few-shot gốc: so sánh đo đúng tác dụng của memory
    cùng bảng và phần multi-agent. examples=False: zero-shot."""
    demos = f"{_examples(qa, 0, memory=False)}\n\n" if examples else ""
    user = f"{demos}{_title(qa)}<bảng>\n{table_str(qa['table_id'])}\n</bảng>\n\n{_question(qa, _OUT_A)}"
    return [{"role": "system", "content": _SYSTEM_A.replace("Bạn là agent A trong một hệ nhiều agent", "Bạn là hệ thống")},
            {"role": "user", "content": user}]


def messages_zs(qa: dict) -> list[dict]:
    return messages_fs(qa, examples=False)
