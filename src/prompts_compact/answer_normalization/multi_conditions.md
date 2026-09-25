# VAI TRÒ
Chuẩn hóa đáp án **MultiConditions**: mục đã thỏa các điều kiện kết hợp AND/OR.

# QUY TẮC
- Chỉ lấy đáp án từ **ĐÁP ÁN THÔ**; không kiểm tra lại, đổi logic AND/OR hay thêm điều kiện.
- Mỗi phần tử `answers` chỉ là đáp án ngắn nhất, không lặp lại câu hỏi hay giải thích.
- Không tạo đáp án mới từ các ràng buộc.

# JSON DUY NHẤT
{{"answers":["..."]}}

# ĐẦU VÀO
**CÂU HỎI:** {question}
**MỤC TIÊU:** {target}
**ĐÁP ÁN THÔ:** {answer}
