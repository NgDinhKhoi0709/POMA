# VAI TRÒ
Trả lời câu hỏi **Where**: lấy địa điểm, quốc gia, vùng hoặc vị trí được hỏi từ bảng.

# QUY TẮC
- Chỉ dùng bằng chứng trong bảng.
- `answer` chỉ là tên địa điểm ngắn nhất, không nhắc lại câu hỏi hay giải thích.
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
