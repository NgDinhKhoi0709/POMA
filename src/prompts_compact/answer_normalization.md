# VAI TRÒ
Chuẩn hóa câu trả lời thô thành đáp án có thể đối chiếu với đáp án tham chiếu.

# QUY TẮC
- Chỉ chuẩn hóa nội dung có trong **ĐÁP ÁN**; không tự trả lời lại từ câu hỏi.
- Mỗi phần tử `answers` chỉ là một đáp án ngắn nhất, không lặp lại câu hỏi hay giải thích.
- Giữ tên riêng, số, ngày và cách viết có trong đáp án thô khi hợp lệ.
- Không có đáp án hợp lệ: trả `{{"answers":["Null"]}}`.

# JSON DUY NHẤT
{{"answers":["..."]}}

# ĐẦU VÀO
**CÂU HỎI:** {question}
**MỤC TIÊU:** {target}
**ĐÁP ÁN THÔ:** {answer}
