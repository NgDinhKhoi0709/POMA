# Ứng viên biểu diễn bảng cho Open-ViTabQA (D09)

Ngày: 2026-09-19. Trạng thái: **đã chạy sàng lọc trên 200 câu; kết quả ở [direction-progress](direction-progress.md#ghi-nhận-của-d09)**. Bản đã chạy khác kế hoạch dưới đây ở hai điểm theo yêu cầu: bỏ nhánh HTML (A7) và thêm lớp làm sạch bảng cho mọi nhánh trừ control `v1_raw`, kèm nhánh `v1_clean` để tách riêng ảnh hưởng của làm sạch. Phần còn lại của tài liệu là kế hoạch ban đầu, liệt kê các cách biểu diễn có thể áp dụng, kèm chi phí token đo trên bảng thật và thiết kế thí nghiệm đề xuất. Đây là hướng D09 (alternative table view) trong [danh sách direction](2026-09-19-poma-improvement-directions.md).

Báo cáo gốc của ba agent tìm tài liệu và script đo token nằm ở [2026-09-19-table-repr-supporting/](2026-09-19-table-repr-supporting/). Các nguồn đã được phủ trước đó không nhắc lại ở đây: [structure-encoding-shortlist](../2026-09-18-supporting/structure-encoding-shortlist.md) và [table-representation-small-lm](../2026-09-17-table-representation-small-lm.md).

## 1. Kết luận ngắn

1. **Không có bằng chứng nào cho Qwen3-8B hoặc cho tiếng Việt.** Không tìm thấy nghiên cứu nào so sánh định dạng bảng trên tiếng Việt, và cũng không có nghiên cứu nào đo Qwen3-8B khi đổi định dạng. Báo cáo Qwen3, Qwen2.5, SeaLLM-v3 và SEA-LION không công bố định dạng bảng nào. Vì vậy mọi kết quả bên dưới phải được đo lại, không thể suy ra từ literature.
2. **Kích thước hiệu ứng kỳ vọng nhỏ.** ToRR (14 model chạy zero-shot) báo chênh lệch tối đa 0,06 giữa các serializer cho một model, và Table-GPT báo khoảng 2–3 điểm. TABVERSE, đã có trong shortlist cũ, báo khoảng 1–3 điểm ở 7–8B và thứ hạng đảo chiều giữa hai model 7B.
3. **Tín hiệu mạnh nhất từ blog là đặt tên cột cạnh từng giá trị, mỗi trường một dòng (Markdown-KV).** Trên GPT-4.1-nano, Markdown-KV đạt 60,7% so với CSV 44,3%, nhưng bảng có 1.000 hàng, câu hỏi chỉ tra cứu ô và chỉ một model. Cùng thí nghiệm đó cho thấy cách "lặp header trên cùng dòng" (`k: v | k: v`) là cách tệ nhất (41,1%).
4. **Flatten V1 có tiền lệ về merged cell.** TableLlama lặp nội dung ô gộp vào mọi cột bị gộp trong prompt HiTab, giống hệt cách Flatten V1 xử lý. Span dedup đã đo gần bằng 0 (+0,19) và bị loại ở D17.
5. **Đề xuất:** chạy 8 nhánh (7 cách mới và 1 nhánh control) ở mục 4 trên subset 200 câu, dùng như bước **sàng lọc**. Với n=200, chỉ phát hiện được chênh lệch từ khoảng 5 điểm trở lên (mục 5), nên nhánh dẫn đầu phải được xác nhận lại trên tập lớn hơn trước khi coi là kết luận.

## 2. Hiện trạng cần giữ nguyên

- Flatten V1: mỗi hàng một dòng, ô ngăn cách bằng `|`, ô header có hậu tố ` <header>`, ô gộp được lặp vào mọi vị trí bị gộp ([representation.py](../../../preprocessing/representation.py)).
- Prompt zero-shot hiện tại chỉ có chuỗi bảng và câu hỏi, không có `table_title`/`table_domain` ([baseline/prompts.py](../../../baseline/prompts.py), `_build_zero_shot`). Thí nghiệm mới chỉ đổi chuỗi bảng, giữ nguyên prompt, schema đầu ra, model, nhà cung cấp và scorer.
- Trần trích xuất nguyên ô chỉ khoảng 43% (shortlist cũ): phần còn lại là tính toán, Yes/No, liệt kê. Biểu diễn không sửa được lỗi số học, nên mức tăng kỳ vọng vốn bị chặn.

## 3. Bằng chứng mới, tóm lược

| Nguồn | Model, cỡ mẫu | Điều rút ra | Độ tin cậy |
|---|---|---|---|
| [Improving Agents, 11 định dạng](https://www.improvingagents.com/blog/best-input-data-format-for-llms/) (2025-09-30) | GPT-4.1-nano; 1.000 câu tra cứu trên bảng 1.000 hàng | Markdown-KV 60,7% > XML 56,0 > INI 55,7 > YAML 54,7 > HTML 53,6 > JSON 52,3 > Markdown table 51,9 > NL 49,6 > JSONL 45,0 > CSV 44,3 > `k: v \| k: v` 41,1. Khoảng tin cậy khoảng ±3 điểm, nên chỉ kết luận được "KV mỗi dòng > CSV/pipe". Token gấp 2,67 lần CSV | Trung bình: đã đọc toàn trang; một model, dữ liệu tổng hợp, chỉ tra cứu |
| [Singha et al., 2310.10358](https://arxiv.org/abs/2310.10358) | GPT-3 (text-davinci-003) | Markdown tệ nhất (67,32) so với DataFrame-code 79,79 và JSON 77,93 trên tác vụ cấu trúc, không phải QA | Thấp cho chúng ta: model cũ, không phải QA; xếp hạng ngược với blog |
| [TabGR, 2601.08444](https://arxiv.org/abs/2601.08444) | Llama3.3-70B (WikiTQ); duy nhất một lần chạy 8B | HTML 77,3 > LaTeX 76,3 > Markdown 75,5 > JSON 74,2; liên kết tường minh hàng-header-giá trị đạt 80,1 nhưng cần thêm lệnh gọi LLM và không tách được riêng phần biểu diễn. Ở 8B chỉ hơn baseline mạnh nhất +0,5 | Thấp cho zero-shot 8B |
| [Table-GPT, 2310.09263](https://arxiv.org/abs/2310.09263) | GPT-3.5 tinh chỉnh trên Markdown | Markdown 0,705, CSV 0,687, JSON 0,672; tác giả gọi khoảng cách là "không đáng kể" | Thấp: không có đối chứng không tinh chỉnh |
| [ToRR, 2502.19412](https://arxiv.org/abs/2502.19412) | 14 model zero-shot (Llama-3.1-8B, Mistral-7B, Qwen2-72B, ...) | Không serializer nào thắng nhất quán; chênh lệch tối đa 0,06 mỗi model | Trung bình; chưa xác minh venue |
| [Liu et al., 2312.16702](https://arxiv.org/abs/2312.16702) | GPT-3.5, WikiTQ | Chuyển vị chỉ giúp khi bảng bị đặt sai hướng (51,14 → 58,30); trên bảng gốc giảm nhẹ (59,50 → 58,66) | Thấp: một model |
| [TableLlama, 2311.09206](https://arxiv.org/abs/2311.09206) | Llama-2-7B tinh chỉnh | Prompt HiTab lặp ô gộp vào từng cột bị gộp | Tiền lệ cho Flatten V1, không phải bằng chứng hiệu năng |
| [M3TQA, 2508.16265](https://arxiv.org/abs/2508.16265) | Qwen3-8B, có tiếng Việt | Qwen3-8B tiếng Việt: 13,97 khi tắt thinking so với 28,78 khi bật | Chỉ để tham chiếu: không phải kết quả về định dạng |

Định dạng gốc của các model chuyên bảng (đã kiểm chứng từ nguồn): TableGPT2 dùng `df.head(5).to_string(index=False)` khi suy luận và nhiều định dạng ngẫu nhiên khi huấn luyện; TableLLM dùng CSV; StructLM dùng `col : | ... row 1 : | ...`; TableBench dùng JSON `{'columns', 'data'}`; Table-R1 dùng Markdown (đã xác minh trên 4.000 dòng WTQ). Không có nguồn nào cho thấy một model instruct tổng quát hưởng lợi khi định dạng lúc chạy khớp định dạng huấn luyện.

## 4. Các nhánh đề xuất (Tier A, chạy trên subset 200 câu)

Token đo bằng tokenizer Qwen3-8B cục bộ trên 200 câu (138 bảng), tỉ lệ so với Flatten V1 theo tổng token. Chuỗi mẫu từ bảng `99922_0` (2 hàng header, ô gộp) và `3_1` nằm trong script đo.

| ID | Nhánh | Mô tả | ×V1 | Token/bảng: trung vị / p90 / max | Vì sao thử |
|---|---|---|---|---|---|
| A0 | Flatten V1 (control) | Hiện tại | 1,00 | 872 / 2.547 / 19.133 | Chạy lại cùng lô để cùng giao thức |
| A1 | Pipe không tag | Như V1 nhưng bỏ ` <header>` | 0,98 | 859 / 2.536 / 19.120 | Tách riêng chi phí và tác dụng của tag `<header>` (3 token mỗi ô header) |
| A2 | Pipe + đường dẫn header | Bỏ tag, gộp nhiều hàng header thành `Cha / Con`, đưa banner ra dòng `Chú thích:` | 0,97 | 838 / 2.536 / 19.120 | Đối chứng sạch cho A3–A6: cùng tiền xử lý, chỉ khác định dạng |
| A3 | Markdown table | `\| a \| b \|` + dòng `---` | 1,09 | 972 / 2.836 / 19.585 | Định dạng phổ biến nhất; Table-R1, Table-GPT dùng |
| A4 | Markdown-KV | Khối `## Hàng i`, mỗi ô một dòng `Tên cột: giá trị` | 1,94 | 1.642 / 5.226 / 22.877 | Tín hiệu mạnh nhất của blog; đắt nhất |
| A5 | Neo hàng/cột | `col : \| ...` rồi `row i : \| ...` (kiểu StructLM/TableLlama) | 1,17 | 1.069 / 3.041 / 19.955 | Neo số hàng, hữu ích cho câu hỏi thứ hạng và vị trí |
| A6 | JSON cột/dữ liệu | `{"columns": [...], "data": [[...]]}`, `ensure_ascii=False` | 1,13 | 1.033 / 3.070 / 19.804 | Định dạng của TableBench (có model Qwen) |
| A7 | HTML giữ span | `<th rowspan colspan>` chỉ ở ô gốc, không lặp ô gộp | 1,51 | 1.215 / 4.247 / 17.377 | Nhánh duy nhất giữ cấu trúc gộp mà không lặp dữ liệu |

Lưu ý khi đọc kết quả:

- **Nhiễu do tiền xử lý chung.** A2–A6 đều gộp header nhiều hàng, đưa banner ra ngoài và chuẩn hoá NFC (bắt buộc với Markdown-KV, nếu không banner bị lặp ở mọi khối). A0 và A1 không làm vậy, và A7 giữ nguyên hàng header. So A0 với A3–A6 sẽ trộn ảnh hưởng của định dạng với ảnh hưởng của tiền xử lý; **so với A2 mới tách được riêng định dạng**.
- A4 tốn gần gấp đôi token: khoảng 500 nghìn token cho 200 câu so với 258 nghìn của A0.
- Không bao giờ `json.dumps` tiếng Việt với `ensure_ascii=True`: chi phí tăng 2,4–2,6 lần (đo bởi agent).
- Có 11 bảng không có hàng header; các nhánh dùng khoá cột sẽ đặt tên `Cột j`.

### Không đề xuất chạy, kèm lý do

| Cách | Lý do loại |
|---|---|
| `k: v \| k: v` một dòng, `Hàng i: k=v; ...` | Là nhánh tệ nhất trong thí nghiệm blog (41,1%). Có mâu thuẫn giữa các agent: agent bài báo xếp `Hàng i: k=v` là ứng viên số 1, còn blog lại thấy dạng một dòng thua dạng nhiều dòng. Chỉ thêm nếu bạn muốn |
| JSON mỗi hàng một khoá (records) | 1,46–1,64 lần token (2,4–2,6 lần nếu escape ASCII); ý tưởng "tên cột cạnh giá trị" đã được A4 phủ |
| YAML, INI, XML | Bị Markdown-KV áp đảo trong blog; YAML cần quote khi giá trị chứa `:` hoặc `,` |
| Câu văn theo mẫu mỗi hàng | Tín hiệu âm ở 7B (Min et al., 2402.12869: mẫu là cách tệ nhất trong RAG); dễ hỏng với bảng banner, header nhiều tầng, câu Yes/No |
| DataFrame-code, `df.to_string` | Column-major, nhạy thứ tự hàng (giảm 23–45 điểm khi xáo hàng trong Singha); khoảng trắng mơ hồ với ô nhiều từ |
| TOON, Docling triplet | TOON không thắng ở đâu trong benchmark của chính tác giả; Docling triplet không có đánh giá độ chính xác nào |
| Verbalization bằng LLM, TableMaster, QUIETT, TableRAG, PieTa | Cần nhiều lệnh gọi LLM; không còn là prompt zero-shot đơn (TableMaster còn giả định bảng phẳng). Phần chọn hàng/cột đã ở D10 |

## 5. Vì sao chưa nên kết luận từ 200 câu

**Độ phủ theo cấu trúc trên subset** (phát hiện bằng script bs4 riêng, ước lượng thô; nhãn `table_type` trong `dataset/table.json`): normal 92, chỉ merged_value 56, chỉ merged_header 29, cả hai 23. Số câu có đặc điểm cấu trúc (một câu có thể có nhiều đặc điểm): banner một ô chiếm toàn hàng khoảng 44, td rowspan 49, td colspan 37, ô header có colspan trong hàng nhiều ô 27, th rowspan 17, cột stub `<th>` ở đầu hàng 26; 91 câu thuộc bảng không có đặc điểm gộp nào. Số 44 của banner cao hơn con số 128/992 của shortlist cũ một cách không tỉ lệ, vì định nghĩa của tôi lỏng hơn; dùng chúng để so cỡ, không để trích dẫn.

Hệ quả:

- **Nhánh A0–A7 đều đổi chuỗi của mọi bảng**, nên cả 200 câu đều có tác động và Tier A phù hợp với subset 200.
- Các thay đổi chỉ chạm một phần bảng (chuyển vị bảng stub, đưa banner ra ngoài, dấu nối tiếp ô gộp) chỉ ảnh hưởng khoảng 26–44 câu trong 200. Với cỡ này không phân biệt được hiệu ứng vài điểm với nhiễu, nên nên chạy các thay đổi đó trên lát cắt train+dev (prompt-only, không rò rỉ), theo đúng thiết kế trong shortlist cũ.
- **Ngưỡng phát hiện.** Với so sánh cặp trên 200 câu, khi hai nhánh bất đồng khoảng 30 câu, sai số chuẩn của hiệu xấp xỉ 2,7 điểm, khoảng tin cậy 95% khoảng ±5 điểm. Đây là ước tính thô của tôi, chưa tính trên dữ liệu thật. Hiệu ứng kỳ vọng 1–3 điểm sẽ không hiện ra.
- **Chọn nhánh cao nhất trong 8 nhánh trên test là thiên lệch lạc quan.** Cách D04 đã làm (khoá luật trước khi gọi API, không chỉnh sau) áp dụng ở đây; nhánh dẫn đầu cần được kiểm lại trên dev (991 câu) trước khi thay Flatten V1.

## 6. Thiết kế thí nghiệm đề xuất

1. **Giao thức:** giữ nguyên prompt zero-shot, schema JSON đầu ra, model `qwen/qwen3-8b` qua OpenRouter (pin provider `alibaba`), decoding và scorer đã khoá. Chỉ thay chuỗi bảng. Chạy lại A0 cùng lô với các nhánh mới, không dùng lại `zero_shot.json` cũ, để không bị lệch cấu hình.
2. **Thinking:** baseline zero-shot cũ chạy với thinking bật mặc định của model. Đề xuất giữ bật cho mọi nhánh để cùng giao thức; M3TQA cho thấy thinking ảnh hưởng nhiều hơn biểu diễn ở tiếng Việt.
3. **Đo:** EM và F1 theo scorer đã khoá, kiểm định cặp (paired bootstrap của `audit_d01.py`), tách theo 4 nhóm `table_type`, kèm token đầu vào, độ trễ, tỉ lệ đầu ra sai định dạng, và số câu mỗi nhánh thắng/thua A0 và A2.
4. **Chi phí:** 8 nhánh × 200 = 1.600 lệnh gọi; tổng token bảng khoảng 2,5 triệu (bảng ở mục 4). Theo tỉ lệ giá đo từ log planner D04 (khoảng $0,13 mỗi triệu token cả vào lẫn ra) thì phần đầu vào dưới $0,5; phần đầu ra của thinking chưa đo. Ước tính thô: vài USD, chưa kiểm chứng. Tôi sẽ chạy thử 10 câu trước để đo chi phí thật.
5. **Triển khai (chưa làm):** module serializer mới trong `preprocessing/` cho A1–A7, runner theo mẫu `scripts/run_d04_planner.py` (resumable JSONL, worker song song), artifact một đáp án theo schema D01 rồi đưa qua `audit_d01.py --strict`, kèm test cho từng serializer. Script trong [thư mục supporting](2026-09-19-table-repr-supporting/repr_probe.py) chỉ là bản nháp để đo token, không phải mã dùng cho thực nghiệm.

## 7. Cần bạn quyết định

1. Chốt danh sách nhánh A0–A7, hoặc bớt/thêm (ví dụ thêm `Hàng i: k=v; ...`, hoặc bỏ A7 vì đắt và dễ vượt ngân sách token).
2. Thinking bật (đề xuất) hay tắt cho cả lô.
3. Chỉ sàng lọc trên subset 200 câu test như bạn yêu cầu, hay đồng ý xác nhận nhánh dẫn đầu thêm trên dev.
4. Có chạy Tier B (banner hoist, chuyển vị bảng stub, dấu nối tiếp ô gộp, chuẩn hoá số) trên lát cắt train+dev như một thí nghiệm riêng hay bỏ qua.

## 8. Giới hạn của tài liệu

- Các tỉ lệ token chỉ dùng cho việc lập kế hoạch; đo trên 138 bảng của subset, tokenizer Qwen3-8B, không tính lệnh và prompt.
- Không tìm thấy nội dung liên quan trong archive của Sebastian Raschka (agent chỉ đọc danh mục bài, không chạy được tìm kiếm trong site). Hugging Face, Lilian Weng, Eugene Yan, Simon Willison, Hamel Husain và tài liệu của OpenAI/Anthropic/Cohere không có so sánh định dạng có số liệu. Các trang Medium không mở được.
- Nhiều bài báo chỉ đọc phần kết quả qua alphaXiv; nhiều bài chưa rõ venue nên coi là preprint. Chi tiết và danh sách chưa mở nằm trong báo cáo gốc từng agent.
- Cả ba agent đều không gọi API OpenRouter; repo chỉ được thêm tài liệu, không sửa mã.
