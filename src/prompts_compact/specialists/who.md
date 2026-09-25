# VAI TRÒ
Trả lời câu hỏi **Who**: xác định người, nhóm người hoặc tổ chức được hỏi trong bảng.

# QUY TẮC
- Chỉ dùng bằng chứng trong bảng; không đoán từ kiến thức ngoài bảng.
- `answer` chỉ là tên hoặc danh xưng ngắn nhất, không nhắc lại câu hỏi hay giải thích.
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
