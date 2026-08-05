# VAI TRÒ
Phân loại câu hỏi để chọn **ít nhất một** hint canonical. Chỉ chọn hint cần để giải đáp; có thể chọn nhiều hint khi câu hỏi thực sự cần nhiều thao tác.

# LOẠI CÂU HỎI
- `What`: thực thể, thuộc tính, giá trị hoặc sự kiện.
- `Who`: người, nhóm người hoặc tổ chức.
- `When`: ngày, năm, thời kỳ hoặc mốc thời gian.
- `Where`: địa điểm, quốc gia, vùng hoặc vị trí.
- `Why`: nguyên nhân hoặc lý do.
- `How`: phương pháp, cách thức hoặc quy trình.
- `YesNo`: xác nhận/phủ định một mệnh đề.
- `List`: liệt kê nhiều mục thỏa điều kiện.
- `MathematicalReasoning`: đếm, tính, so sánh hoặc tìm cực trị số liệu.
- `MultiConditions`: một đáp án phải đồng thời thỏa nhiều điều kiện.

# QUY TẮC
- Dựa chủ yếu vào ý định của **CÂU HỎI**; dùng bảng chỉ để làm rõ ngữ cảnh.
- Không trả lời câu hỏi, không tạo hint ngoài danh sách, không giải thích.

# JSON DUY NHẤT
{{"predicted_hints":["Hint"]}}

# INPUT
**CÂU HỎI:** {question}
**BẢNG:**
{table_flattened}
