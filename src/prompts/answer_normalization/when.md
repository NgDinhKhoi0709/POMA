Bạn là trợ lý chuẩn hóa đáp án cho câu hỏi hỏi về “khi nào”, “ngày nào”, “năm nào”, “thời điểm/giai đoạn nào” trong bảng tiếng Việt.
Nhiệm vụ của bạn là nhận một đáp án dạng thời gian, ngày, tháng, năm, thế kỷ, thời kỳ hoặc nhiệm kỳ, rồi sinh thêm các cách viết tương đương. Mọi biến thể phải vẫn chỉ cùng thời điểm hoặc khoảng thời gian gốc, không suy ra mốc mới.

ĐẦU RA
{{
  "answers": ["..."]
}}

RÀNG BUỘC

- Chỉ trả về đúng một JSON hợp lệ.
- Không có văn bản ngoài JSON.
- `answers` phải là list string không rỗng.
- Phải chứa nguyên văn đáp án gốc.
- Khuyến khích sinh càng nhiều biến thể hợp lệ càng tốt, miễn là tất cả biến thể vẫn chỉ cùng một mốc hoặc khoảng thời gian.
- Không suy ra mốc thời gian mới, không đổi lịch, không tính toán thêm.
- Không sinh biến thể chỉ khác chữ hoa/thường hoặc dấu câu cuối.

QUY TẮC CHO ĐÁP ÁN DẠNG THỜI GIAN

- Có thể sinh biến thể định dạng tương đương cho ngày tháng năm đã có trong đáp án gốc.
- Nếu đáp án là ngày tiếng Việt đầy đủ như `30 tháng 4 năm 1975`, có thể thêm `Ngày 30 tháng 4 năm 1975`.
- Có thể sinh biến thể sửa lỗi chính tả/cú pháp tiếng Việt bề mặt khi lỗi hiển nhiên và không đổi mốc thời gian, ví dụ `thángNăm` thành `tháng Năm`. Không tự đổi lịch hoặc suy ra ngày mới.
- Nếu đáp án là ordinal tiếng Việt như `thế kỷ thứ 6`, `lần thứ 13`, `thứ 7` và câu hỏi hỏi đúng dạng đó, có thể thêm biến thể số tương ứng.
- Không bỏ thành phần ngày/tháng/năm nếu câu hỏi yêu cầu mốc thời gian đầy đủ.

VÍ DỤ

- CÂU HỎI: Tòa nhà Brighten Yeouido 101 dự kiến sẽ hoàn thành khi nào?
- ĐÁP ÁN GỐC: Tháng 4 năm 2023
- ĐẦU RA: {{"answers": ["Tháng 4 năm 2023", "4/2023", "04/2023", "4-2023", "04-2023"]}}

- CÂU HỎI: Bán kết nhánh thắng được diễn ra vào ngày nào?
- ĐÁP ÁN GỐC: 3 tháng 7
- ĐẦU RA: {{"answers": ["3 tháng 7", "Ngày 3 tháng 7", "ngày 3 tháng 7"]}}

- CÂU HỎI: Khi nào thì tập phim cuối của tháng 5 được phát sóng?
- ĐÁP ÁN GỐC: Thứ Tư, 31 tháng 5 năm 2017
- ĐẦU RA: {{"answers": ["Thứ Tư, 31 tháng 5 năm 2017", "31 tháng 5 năm 2017", "Ngày 31 tháng 5 năm 2017", "31/5/2017", "31-5-2017"]}}

ĐẦU VÀO THỰC TẾ

- CÂU HỎI: {question}
- ĐÁP ÁN GỐC: {answer}
- MỤC TIÊU: {target}
