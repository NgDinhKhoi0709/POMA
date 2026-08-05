Kết hợp mọi điều kiện từ bảng. JSON: {{"answer":"... hoặc null","evidence":["..."],"confidence":0.0,"reason":"..."}}.
EXAMPLE 1: đủ điều kiện → {{"answer":"A","evidence":["A"],"confidence":0.8,"reason":"khớp"}}
EXAMPLE 2: thiếu điều kiện → {{"answer":null,"evidence":[],"confidence":0.0,"reason":"thiếu bằng chứng"}}
CÂU HỎI: {normalized_question}
MỤC TIÊU: {target}
RÀNG BUỘC: {constraints}
BẢNG: {table_flattened}
