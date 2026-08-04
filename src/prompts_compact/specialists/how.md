Suy luận ngắn từ bảng, không thêm dữ kiện ngoài bảng. Trả đúng một JSON: {{"answer":"... hoặc null","evidence":["trích dẫn ngắn"],"confidence":0.0,"reason":"ngắn"}}.
EXAMPLE 1:
Input: cách thức có trong bảng
Output: {{"answer":"A","evidence":["A"],"confidence":0.8,"reason":"khớp"}}
EXAMPLE 2:
Input: không có cách thức
Output: {{"answer":null,"evidence":[],"confidence":0.0,"reason":"Không có đủ bằng chứng trong bảng."}}
CÂU HỎI: {normalized_question}
MỤC TIÊU: {target}
RÀNG BUỘC: {constraints}
BẢNG: {table_flattened}
