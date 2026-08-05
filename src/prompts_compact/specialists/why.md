Chỉ suy luận từ bảng. JSON: {{"answer":"... hoặc null","evidence":["..."],"confidence":0.0,"reason":"..."}}.
EXAMPLE 1: có nguyên nhân → {{"answer":"A","evidence":["A"],"confidence":0.8,"reason":"khớp"}}
EXAMPLE 2: thiếu dữ kiện → {{"answer":null,"evidence":[],"confidence":0.0,"reason":"thiếu bằng chứng"}}
CÂU HỎI: {normalized_question}
MỤC TIÊU: {target}
RÀNG BUỘC: {constraints}
BẢNG: {table_flattened}
QUY TẮC ĐẦU RA: `answer` chỉ chứa đáp án ngắn nhất. Không lặp lại, diễn đạt lại CÂU HỎI hoặc viết câu giải thích hoàn chỉnh.
