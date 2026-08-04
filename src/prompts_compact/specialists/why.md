Suy luận ngắn từ bảng, không thêm dữ kiện ngoài bảng. Trả đúng một JSON: {{"answer":"... hoặc null","evidence":["trích dẫn ngắn"],"confidence":0.0,"reason":"ngắn"}}.
EXAMPLE 1:
Input: nguyên nhân có trong bảng
Output: {{"answer":"A","evidence":["A"],"confidence":0.8,"reason":"khớp"}}
EXAMPLE 2:
Input: không có nguyên nhân
Output: {{"answer":null,"evidence":[],"confidence":0.0,"reason":"Không có đủ bằng chứng trong bảng."}}
CÂU HỎI: {normalized_question}
MỤC TIÊU: {target}
RÀNG BUỘC: {constraints}
BẢNG: {table_flattened}
