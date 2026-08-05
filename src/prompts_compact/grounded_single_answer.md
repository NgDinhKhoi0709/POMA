# VAI TRÒ
Chọn một đáp án duy nhất được bảng hỗ trợ từ các ứng viên.

# QUY TẮC
- Chỉ chọn đáp án có bằng chứng rõ ràng trong bảng.
- `answer` chỉ là đáp án ngắn nhất, không lặp lại câu hỏi hay giải thích.
- Không có ứng viên được chứng minh: dùng `null`.
- `evidence` là trích dẫn ngắn; `reason` thật ngắn.

# JSON DUY NHẤT
{{"answer":"... hoặc null","evidence":["..."],"confidence":0.0,"reason":"..."}}

# INPUT
**CÂU HỎI:** {question}
**BẢNG:**
{table_flattened}
**ỨNG VIÊN:** {candidates}
