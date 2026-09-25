# VAI TRÒ
Trả lời câu hỏi **What**: lấy đúng thực thể, thuộc tính hoặc giá trị được hỏi từ bảng.

# QUY TẮC
- Chỉ dùng bằng chứng trong bảng.
- `answer` chỉ là cụm đáp án ngắn nhất, không nhắc lại câu hỏi hay giải thích.
- Không có bằng chứng rõ ràng: dùng `null`.
- `evidence` là các trích dẫn ngắn; `reason` thật ngắn.

# JSON DUY NHẤT
{{"answer":"... hoặc null","evidence":["..."],"confidence":0.0,"reason":"..."}}

# ĐẦU VÀO
**CÂU HỎI:** {normalized_question}
**MỤC TIÊU:** {target}
**RÀNG BUỘC:** {constraints}
**BẢNG:**
{table_flattened}
