Kết hợp mọi điều kiện và chỉ dùng bằng chứng trong bảng. Trả đúng một JSON: {{"answer":"... hoặc null","evidence":["trích dẫn ngắn"],"confidence":0.0,"reason":"ngắn"}}.
EXAMPLE 1:
Input: hai điều kiện có bằng chứng
Output: {{"answer":"A","evidence":["A"],"confidence":0.8,"reason":"khớp"}}
EXAMPLE 2:
Input: thiếu một điều kiện
Output: {{"answer":null,"evidence":[],"confidence":0.0,"reason":"Không có đủ bằng chứng trong bảng."}}
CÂU HỎI: {normalized_question}
MỤC TIÊU: {target}
RÀNG BUỘC: {constraints}
BẢNG: {table_flattened}
