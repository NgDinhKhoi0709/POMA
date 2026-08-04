Tính toán hoặc so sánh từ số liệu trong bảng. Trả đúng một JSON: {{"answer":"... hoặc null","evidence":["trích dẫn ngắn"],"confidence":0.0,"reason":"ngắn"}}.
EXAMPLE 1:
Input: số liệu đủ để tính
Output: {{"answer":"2","evidence":["1","1"],"confidence":0.8,"reason":"tổng"}}
EXAMPLE 2:
Input: thiếu số liệu
Output: {{"answer":null,"evidence":[],"confidence":0.0,"reason":"Không có đủ bằng chứng trong bảng."}}
CÂU HỎI: {normalized_question}
MỤC TIÊU: {target}
RÀNG BUỘC: {constraints}
BẢNG: {table_flattened}
