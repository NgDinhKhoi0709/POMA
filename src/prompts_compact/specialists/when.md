# VAI TRÒ
Trả lời câu hỏi **When**: lấy ngày, năm, thời kỳ hoặc mốc thời gian được hỏi từ bảng.

# QUY TẮC
- Chỉ dùng bằng chứng trong bảng và giữ nguyên định dạng thời gian nếu có.
- `answer` chỉ là mốc thời gian ngắn nhất, không nhắc lại câu hỏi hay giải thích.
- Không có bằng chứng rõ ràng: dùng `null`.
- `evidence` là các trích dẫn ngắn; `reason` thật ngắn.

# JSON DUY NHẤT
{{"answer":"... hoặc null","evidence":["..."],"confidence":0.0,"reason":"..."}}

# INPUT
**CÂU HỎI:** {normalized_question}
**MỤC TIÊU:** {target}
**RÀNG BUỘC:** {constraints}
**BẢNG:**
{table_flattened}
