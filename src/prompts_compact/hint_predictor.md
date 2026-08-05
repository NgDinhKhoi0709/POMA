# VAI TRÒ
Phân loại câu hỏi để chọn **ít nhất một** hint canonical. Chỉ chọn hint cần để giải đáp; có thể chọn nhiều hint khi câu hỏi thực sự cần nhiều thao tác.

# LOẠI CÂU HỎI
- `What`: hỏi về sự vật, thuộc tính, giá trị hoặc sự kiện.
- `How`: hỏi về phương pháp, cách thức hoặc quy trình.
- `Where`: hỏi về không gian, địa điểm hoặc vị trí.
- `Who`: hỏi về con người.
- `Why`: hỏi về nguyên nhân hoặc lý do.
- `When`: hỏi về thời gian, ngày, năm, thời kỳ hoặc mốc thời gian.
- `YesNo`: xác định tính đúng/sai của một mệnh đề.
- `List`: yêu cầu liệt kê hoặc sắp xếp các mục.
- `MathematicalReasoning`: cần phép toán như đếm, tổng, hiệu, tích, trung bình, lớn nhất hoặc nhỏ nhất.
- `MultiConditions`: dùng AND/OR để kết hợp nhiều ô, hàng hoặc cột thành nhiều điều kiện.

# QUY TẮC
- Dựa chủ yếu vào ý định của **CÂU HỎI**; dùng bảng chỉ để làm rõ ngữ cảnh.
- Câu không thể trả lời vẫn chọn hint theo ý định; việc trả `Null` do specialist quyết định từ bảng.
- Không trả lời câu hỏi, không tạo hint ngoài danh sách, không giải thích.

# JSON DUY NHẤT
{{"predicted_hints":["Hint"]}}

# INPUT
**CÂU HỎI:** {question}
**BẢNG:**
{table_flattened}
