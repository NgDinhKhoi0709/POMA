"""Agent C chuyên phát hiện câu không trả lời được (Null) cho câu hỏi giải thích ("vì sao", "như thế nào").

Trên train, 56% câu giải thích có gold Null (các loại câu khác ~2%): bảng Wikipedia hiếm khi ghi lý do,
và nhiều câu có tiền đề sai. Agent chỉ quyết định "bảng có ghi rõ lý do/cách thức được hỏi không".
Cũng định nghĩa ghi chú EXPLAIN_NOTE thêm vào đuôi prompt của A và B cho câu giải thích.
"""

from __future__ import annotations

from .client import Usage, VLLMClient, parse_json

EXPLAIN_NOTE = (
    "LƯU Ý: câu hỏi này hỏi lý do hoặc cách thức. Chỉ trả lời khi bảng ghi rõ lý do/cách thức đó. Nếu bảng "
    "không ghi, hoặc điều câu hỏi giả định không đúng với bảng (ví dụ \"vì sao X mà không phải Y\" trong khi bảng "
    "không nói gì về lý do), final_answer là \"Null\". Khi trả lời, chép sát phần giải thích có trong bảng.\n"
)

_TASK = (
    "NHIỆM VỤ: KHÔNG trả lời câu hỏi. Chỉ xác định bảng có thật sự chứa thông tin trả lời câu hỏi dưới đây hay "
    "không. Câu hỏi hỏi lý do hoặc cách thức; chỉ coi là trả lời được khi bảng ghi rõ lý do/cách thức đó (một ô "
    "hoặc cột giải thích, mô tả, ghi chú). Coi là KHÔNG trả lời được khi: bảng chỉ có số liệu mà không nêu lý do; "
    "lý do phải tự suy đoán ngoài bảng; hoặc điều câu hỏi giả định không đúng với bảng.\n"
    "ĐẦU RA: đúng một JSON {\"answerable\": true | false, \"evidence\": \"<chép ô bảng chứa lý do nếu có, "
    "rỗng nếu không>\", \"reason\": \"<một câu giải thích quyết định>\"}.\n"
)


def detect(client: VLLMClient, qa: dict, prefix: str) -> tuple[bool | None, dict, Usage]:
    t, u = client.chat(prefix + _TASK + f"\nCÂU HỎI: {qa['question']}\nĐẦU RA: ")
    obj = parse_json(t[0]) or {}
    ans = obj.get("answerable")
    if isinstance(ans, str):
        ans = {"true": True, "false": False}.get(ans.strip().lower())
    return (ans if isinstance(ans, bool) else None), {k: str(obj.get(k, ""))[:300] for k in ("evidence", "reason")}, u
