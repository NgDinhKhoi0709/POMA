# VAI TRÒ
Trả lời câu hỏi **MultiConditions**: tìm mục bằng cách kết hợp nhiều ô, hàng hoặc cột theo các điều kiện trong câu hỏi.

# QUY TẮC
- Giữ đúng logic của câu hỏi: với AND, mục phải thỏa mọi vế; với OR, mục chỉ cần thỏa ít nhất một vế.
- Có thể kết hợp điều kiện trên nhiều ô, hàng và cột; không đổi AND thành OR hoặc ngược lại.
- `answer` chỉ là đáp án ngắn nhất, không nhắc lại câu hỏi hay giải thích.
- Không có mục thỏa logic truy vấn: dùng `null`.
- `evidence` phải hỗ trợ các điều kiện; `reason` thật ngắn.

# JSON DUY NHẤT
{{"answer":"... hoặc null","evidence":["..."],"confidence":0.0,"reason":"..."}}

EXAMPLE 1: thỏa điều kiện AND → {{"answer":"A","evidence":["A"],"confidence":0.8,"reason":"khớp"}}
EXAMPLE 2: không thỏa logic truy vấn → {{"answer":null,"evidence":[],"confidence":0.0,"reason":"thiếu bằng chứng"}}

# INPUT
**CÂU HỎI:** {normalized_question}
**MỤC TIÊU:** {target}
**RÀNG BUỘC:** {constraints}
**BẢNG:**
{table_flattened}
