Tính hoặc so sánh số liệu trong bảng. JSON: {{"answer":"... hoặc null","evidence":["..."],"confidence":0.0,"reason":"..."}}.
EXAMPLE 1: đủ số liệu → {{"answer":"2","evidence":["1","1"],"confidence":0.8,"reason":"tổng"}}
EXAMPLE 2: thiếu số liệu → {{"answer":null,"evidence":[],"confidence":0.0,"reason":"thiếu bằng chứng"}}
CÂU HỎI: {normalized_question}
MỤC TIÊU: {target}
RÀNG BUỘC: {constraints}
BẢNG: {table_flattened}
