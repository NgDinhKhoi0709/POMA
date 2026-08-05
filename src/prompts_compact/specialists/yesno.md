# VAI TRÒ
Trả lời câu hỏi **YesNo**: kiểm tra mệnh đề trong câu hỏi có được bảng xác nhận hay phủ định.

# QUY TẮC
- Chỉ trả `Có`, `Không` hoặc `null`; không lặp lại câu hỏi và không dùng câu đầy đủ.
- `Có` khi bảng xác nhận mệnh đề; `Không` khi bảng mâu thuẫn mệnh đề.
- Không đủ bằng chứng để kết luận: dùng `null`.
- `evidence` là các trích dẫn ngắn; `reason` thật ngắn.

# JSON DUY NHẤT
{{"answer":"Có, Không hoặc null","evidence":["..."],"confidence":0.0,"reason":"..."}}

# INPUT
**CÂU HỎI:** {normalized_question}
**MỤC TIÊU:** {target}
**RÀNG BUỘC:** {constraints}
**BẢNG:**
{table_flattened}
