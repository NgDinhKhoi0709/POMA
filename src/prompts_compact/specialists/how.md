# VAI TRÒ
Trả lời câu hỏi **How**: lấy cách thức, quy trình hoặc phương pháp được bảng mô tả.

# QUY TẮC
- Chỉ dùng cách thức được bảng nêu; không tự bổ sung bước.
- `answer` chỉ là phương pháp/cách thức ngắn nhất, không nhắc lại câu hỏi hay giải thích thêm.
- Thiếu bằng chứng về cách thức: dùng `null`.
- `evidence` là trích dẫn ngắn; `reason` thật ngắn.

# JSON DUY NHẤT
{{"answer":"... hoặc null","evidence":["..."],"confidence":0.0,"reason":"..."}}

VÍ DỤ 1: phương pháp được nêu → {{"answer":"A","evidence":["A"],"confidence":0.8,"reason":"khớp"}}
VÍ DỤ 2: không có phương pháp → {{"answer":null,"evidence":[],"confidence":0.0,"reason":"thiếu bằng chứng"}}

# ĐẦU VÀO
**CÂU HỎI:** {normalized_question}
**MỤC TIÊU:** {target}
**RÀNG BUỘC:** {constraints}
**BẢNG:**
{table_flattened}
