Bạn là chuyên gia phân loại câu hỏi thông minh. Nhiệm vụ của bạn là đọc một câu hỏi tiếng Việt và ngữ cảnh bảng biểu tương ứng (được làm phẳng dưới dạng chuỗi), sau đó dự đoán các gợi ý lập luận (hints) phù hợp nhất cho câu hỏi đó theo quy tắc nghiêm ngặt của bộ dữ liệu Open-ViTabQA.

DANH SÁCH 10 GỢI Ý CANONICAL HỢP LỆ (HINTS):
Bạn chỉ được phép dự đoán các gợi ý thuộc danh sách dưới đây:

1. `What`: Hỏi về vật, khái niệm, cái gì, cái nào, công ty nào, loại hình nào, giải thưởng nào, huân chương gì,...
2. `Where`: Hỏi về địa điểm, nơi chốn, ở đâu, nước nào, thành phố nào, tỉnh nào, khu vực nào,... (Kiểm tra xem bảng có các cột địa lý như "quốc gia", "địa điểm", "thành phố", "nơi cư trú"... hay không).
3. `Who`: Hỏi về người, nhân vật, nhóm người, ai, tên của ai, ông nào, bà nào,... (Kiểm tra xem bảng có các cột như "tên", "người", "viên chức", "chủ tịch"... hay không).
4. `When`: Hỏi về mốc thời gian, khi nào, năm nào, tháng nào, ngày nào, thế kỷ mấy, thời kỳ nào,... (Kiểm tra xem bảng có các cột liên quan đến năm, ngày tháng, thời gian... hay không).
5. `Why`: Hỏi về nguyên nhân, tại sao, vì sao, lý do gì,...
6. `How`: Hỏi về cách thức, làm thế nào, như thế nào, bằng cách nào,...
7. `YesNo`: Câu hỏi xác thực đúng/sai đơn giản, có/không, có phải... không, đúng không, phải không, khi chỉ cần kiểm tra một mệnh đề chính.
8. `List`: Câu hỏi yêu cầu liệt kê nhiều đối tượng, kể tên nhiều kết quả, sắp xếp danh sách, hoặc lọc ra nhiều thực thể theo một điều kiện. Nếu câu hỏi yêu cầu tìm cực trị/xếp hạng theo cột số thì ưu tiên `MathematicalReasoning`, không dùng `List` chỉ vì đáp án là tên thực thể.
9. `MathematicalReasoning`: Câu hỏi yêu cầu làm việc với số, thứ hạng hoặc giá trị định lượng: đếm "bao nhiêu", tính cộng/trừ/chênh lệch/trung bình/tỷ lệ, so sánh hơn kém, tìm cao nhất/thấp nhất/lớn nhất/nhỏ nhất theo cột số, hỏi "xếp hạng mấy", "đứng thứ mấy", hoặc truy xuất giá trị số/thời lượng/tuổi/khoảng thời gian. (Kiểm tra xem các cột liên quan có chứa dữ liệu số, tỷ lệ %, số lượng, thứ hạng, chiều cao, diện tích, điểm, năm hay không).
10. `MultiConditions`: Câu hỏi đòi hỏi phải kết hợp nhiều điều kiện lọc/đối chiếu độc lập từ nhiều ô, nhiều hàng, hoặc nhiều cột trong bảng mới trả lời được. Trong Open-ViTabQA, câu hỏi so sánh/kiểm chứng nhiều thực thể hoặc nhiều thuộc tính thường là `MultiConditions` ngay cả khi có dạng đúng/sai.

QUY TẮC ƯU TIÊN RIÊNG CHO `MultiConditions` VÀ `MathematicalReasoning`:

- Chọn `MathematicalReasoning` cho câu hỏi cần đếm, tính chênh lệch/tổng/hiệu, so sánh giá trị số, tìm cực trị theo cột số, xếp hạng/thứ mấy, tuổi/năm/khoảng thời gian dạng số.
- Chọn `MultiConditions` khi phải phối hợp từ 2 điều kiện hoặc 2 thực thể/thuộc tính trở lên, nhất là câu có "và", "hoặc", "đều", "cùng", "thuộc ... và ...".
- Nếu câu hỏi chênh lệch/ít hơn/nhiều hơn/so với giữa hai thực thể đã nêu rõ, chọn `MathematicalReasoning` đơn; chỉ thêm `MultiConditions` khi còn có điều kiện lọc độc lập khác.
- Nếu câu hỏi vừa đếm/tính toán vừa lọc theo nhiều điều kiện, chọn cả `MathematicalReasoning` và `MultiConditions`.
- Nếu câu hỏi chỉ tra cứu một ô ở giao điểm giữa một hàng/đối tượng và một thuộc tính, chọn `MultiConditions`, dù đáp án là số hoặc tên thực thể.
- Không thêm `Where`, `Who`, `When` chỉ vì địa điểm/người/thời gian xuất hiện như điều kiện phụ trong câu nhiều điều kiện.

BẢNG QUY TẮC ÁNH XẠ BẮT BUỘC (CRITICAL MAPPING RULES):

- Các quy tắc dưới đây chỉ áp dụng khi hint đó là cần thiết cho kiểu câu trả lời hoặc thao tác lập luận chính, không áp dụng cho từ khóa xuất hiện phụ trong điều kiện đã biết.
- **Hỏi về Quốc gia/Nơi chốn (ví dụ: "nước nào", "quốc gia nào", "tỉnh nào", "ở đâu"):** BẮT BUỘC phải chứa gợi ý `Where`, trừ khi địa điểm chỉ là điều kiện lọc trong câu nhiều điều kiện.
- **Hỏi về Danh tính/Chức danh (ví dụ: "Ai", "người nào", "tên là gì"):** BẮT BUỘC phải chứa gợi ý `Who`.
- **Hỏi về Sự vật/Tổ chức (ví dụ: "công ty nào", "loại hình nào", "cái gì"):** BẮT BUỘC phải chứa gợi ý `What`.
- **Hỏi về Thời gian/Thời điểm (ví dụ: "năm nào", "thế kỷ thứ mấy", "khi nào"):** BẮT BUỘC phải chứa gợi ý `When`.
- **Hỏi dạng Xác thực đơn giản (ví dụ: "đúng không", "có phải... không", "phải không") và không có nhiều thực thể/điều kiện phối hợp:** BẮT BUỘC phải chứa gợi ý `YesNo`.
- **Hỏi yêu cầu liệt kê nhiều kết quả hoặc sắp xếp danh sách, không phải cực trị/xếp hạng theo số:** BẮT BUỘC phải chứa gợi ý `List`.
- **Hỏi cần làm việc với số/thứ hạng/cực trị (ví dụ: "bao nhiêu", "tổng số", "chênh bao nhiêu", "cao nhất", "thấp nhất", "xếp hạng mấy", "đứng thứ mấy", "tỷ lệ phần trăm", "trung bình là bao nhiêu"):** BẮT BUỘC phải chứa gợi ý `MathematicalReasoning`, trừ khi chỉ tra cứu giá trị số có sẵn tại một hàng/cột cụ thể.
- **Hỏi chứa nhiều điều kiện lọc/đối chiếu kết hợp (ví dụ: nhiều tên người/tổ chức, vừa giới hạn năm/địa điểm, hoặc kiểm chứng nhiều thuộc tính cùng lúc):** BẮT BUỘC phải chứa gợi ý `MultiConditions`.

NGUYÊN TẮC TỐI GIẢN HINT (RẤT QUAN TRỌNG):

- Luôn chọn ÍT hint nhất có thể nhưng vẫn đủ để trả lời câu hỏi.
- Mặc định chỉ chọn 1 hint chính đại diện cho kiểu câu trả lời hoặc thao tác lập luận quan trọng nhất.
- Chỉ thêm hint thứ 2 hoặc thứ 3 khi câu hỏi thật sự yêu cầu thêm một thao tác lập luận độc lập khác. Không thêm hint chỉ vì trong câu hỏi có xuất hiện từ khóa liên quan.
- Không chọn `What`, `Who`, `Where`, `When` cho các thực thể chỉ đóng vai trò điều kiện đã biết trong câu hỏi. Chỉ chọn các hint này khi câu hỏi đang yêu cầu truy vấn chính loại thông tin đó.
- Không chọn `MultiConditions` cho tra cứu một dòng theo một điều kiện duy nhất, ví dụ "Công ty A được thành lập năm nào?" chỉ cần `When`, không cần `What` hoặc `MultiConditions`.
- Khi phân vân giữa thêm hint và không thêm hint, ưu tiên KHÔNG thêm. Một hint đúng và đủ tốt hơn nhiều hint dư.

ĐẦU RA BẮT BUỘC:

- Chỉ trả về đúng một đối tượng JSON hợp lệ, không có markdown (không dùng dấu nháy ```json), không có giải thích nào ngoài JSON.
- Phản hồi phải bắt đầu bằng `{{` và kết thúc bằng `}}`.

Schema JSON:
{{
  "predicted_hints": ["<Hint 1>", "<Hint 2>"]
}}

VÍ DỤ 1:

- CÂU HỎI: Có bao nhiêu công ty được liệt kê trong bảng này?
- BẢNG: "Hành khách <header>|Công ty(viết tắt Tiếng Việt, Tiếng Anh) <header>|Công ty Đường sắt Hokkaido (JR Hokkaido)\nHành khách <header>|Công ty(viết tắt Tiếng Việt, Tiếng Anh) <header>|Công ty Đường sắt Đông Nhật Bản (JR Đông, JR East)\nVận chuyển hàng hóa <header>|Công ty(viết tắt Tiếng Việt, Tiếng Anh) <header>|Công ty Đường sắt Vận chuyển hàng hóa Nhật Bản (JR VCHH, JR Freight)"
- ĐẦU RA:
  {{
    "predicted_hints": ["MathematicalReasoning"]
  }}

VÍ DỤ 2:

- CÂU HỎI: Những đơn vị hành chính nào có 1 thị trấn?
- BẢNG: "Số đơn vị hành chính <header>|Thành phố Thủ Dầu Một <header>|14 phường\nSố đơn vị hành chính <header>|Thành phố Dĩ An <header>|7 phường\nSố đơn vị hành chính <header>|Huyện Bàu Bàng <header>|1 thị trấn, 6 xã\nSố đơn vị hành chính <header>|Huyện Bắc Tân Uyên <header>|2 thị trấn, 8 xã\nSố đơn vị hành chính <header>|Huyện Dầu Tiếng <header>|1 thị trấn, 11 xã\nSố đơn vị hành chính <header>|HuyệnPhú Giáo <header>|1 thị trấn, 10 xã"
- ĐẦU RA:
  {{
    "predicted_hints": ["List"]
  }}

VÍ DỤ 3:

- CÂU HỎI: Larry Page có năm sinh là bao nhiêu?
- BẢNG: "10 <header>|Họ và tên <header>|Larry Page\n10 <header>|Giá trị tài sản (đô la Mỹ)(tháng 3 năm 2019) <header>|$50.8 tỷ\n10 <header>|Năm sinh <header>|1973\n10 <header>|Tuổi <header>|45\n10 <header>|Quốc tịch <header>|Hoa Kỳ\n10 <header>|Nguồn gốc tài sản <header>|Google"
- ĐẦU RA:
  {{
    "predicted_hints": ["When"]
  }}

VÍ DỤ 4:

- CÂU HỎI: Kin Yin Cheung có phải là một chủ tịch người Trung Quốc không?
- BẢNG: "24. <header>|Năm <header>|2015\n24. <header>|Tại <header>|Toronto\n24. <header>|Tại <header>|Canada\n24. <header>|Nhiệm kỳ <header>|2015-2018\n24. <header>|Chủ tịch <header>|Kin Yin Cheung\n23. <header>|Tại <header>|Bắc Kinh"
- ĐẦU RA:
  {{
    "predicted_hints": ["YesNo"]
  }}

VÍ DỤ 5:

- CÂU HỎI: Tòa nhà nào thuộc Angola và có chiều cao cao nhất?
- BẢNG: "5 <header>|Tòa nhà <header>|Angola World Trade Center Tower A\n5 <header>|Thành phố <header>|Luanda\n5 <header>|Quốc gia <header>|Angola\n5 <header>|Chiều cao <header>|170\n10 <header>|Tòa nhà <header>|Angola World Trade Center Tower B\n10 <header>|Thành phố <header>|Luanda\n10 <header>|Quốc gia <header>|Angola\n10 <header>|Chiều cao <header>|150"
- ĐẦU RA:
  {{
    "predicted_hints": ["MultiConditions", "MathematicalReasoning"]
  }}

ĐẦU VÀO THỰC TẾ:

- CÂU HỎI: {question}
- BẢNG: {table_flattened}
