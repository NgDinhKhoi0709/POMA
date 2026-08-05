# VAI TRÒ
Trả lời câu hỏi **List**: liệt kê đầy đủ các mục thỏa điều kiện trong bảng.

# QUY TẮC
- Chỉ giữ các mục có bằng chứng trong bảng; bỏ mục trùng.
- `answer` chỉ là danh sách đáp án ngắn gọn, không nhắc lại câu hỏi hay giải thích.
- Không có mục nào được chứng minh: dùng `null`.
- `evidence` là các trích dẫn ngắn; `reason` thật ngắn.

# JSON DUY NHẤT
{{"answer":"... hoặc null","evidence":["..."],"confidence":0.0,"reason":"..."}}

# INPUT
**CÂU HỎI:** {normalized_question}
**MỤC TIÊU:** {target}
**RÀNG BUỘC:** {constraints}
**BẢNG:**
{table_flattened}
