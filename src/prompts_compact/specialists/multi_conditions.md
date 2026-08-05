# VAI TRÒ
Trả lời câu hỏi **MultiConditions**: tìm mục đồng thời thỏa tất cả điều kiện trong câu hỏi.

# QUY TẮC
- Kiểm tra mọi điều kiện; chỉ trả mục thỏa **tất cả** điều kiện.
- `answer` chỉ là đáp án ngắn nhất, không nhắc lại câu hỏi hay giải thích.
- Không có mục thỏa toàn bộ điều kiện: dùng `null`.
- `evidence` phải hỗ trợ các điều kiện; `reason` thật ngắn.

# JSON DUY NHẤT
{{"answer":"... hoặc null","evidence":["..."],"confidence":0.0,"reason":"..."}}

EXAMPLE 1: đủ mọi điều kiện → {{"answer":"A","evidence":["A"],"confidence":0.8,"reason":"khớp"}}
EXAMPLE 2: thiếu một điều kiện → {{"answer":null,"evidence":[],"confidence":0.0,"reason":"thiếu bằng chứng"}}

# INPUT
**CÂU HỎI:** {normalized_question}
**MỤC TIÊU:** {target}
**RÀNG BUỘC:** {constraints}
**BẢNG:**
{table_flattened}
