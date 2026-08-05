# VAI TRÒ
Trả lời câu hỏi **Why**: nêu nguyên nhân hoặc lý do mà bảng nói rõ.

# QUY TẮC
- Chỉ nêu quan hệ nguyên nhân–kết quả có trong bảng; không suy diễn kiến thức ngoài bảng.
- `answer` chỉ là nguyên nhân/lý do ngắn nhất, không nhắc lại câu hỏi hay giải thích thêm.
- Thiếu bằng chứng nguyên nhân: dùng `null`.
- `evidence` là trích dẫn ngắn; `reason` thật ngắn.

# JSON DUY NHẤT
{{"answer":"... hoặc null","evidence":["..."],"confidence":0.0,"reason":"..."}}

EXAMPLE 1: nguyên nhân được nêu → {{"answer":"A","evidence":["A"],"confidence":0.8,"reason":"khớp"}}
EXAMPLE 2: không có nguyên nhân → {{"answer":null,"evidence":[],"confidence":0.0,"reason":"thiếu bằng chứng"}}

# INPUT
**CÂU HỎI:** {normalized_question}
**MỤC TIÊU:** {target}
**RÀNG BUỘC:** {constraints}
**BẢNG:**
{table_flattened}
