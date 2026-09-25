# Nhật ký thực hiện các direction của POMA

Cập nhật: 2026-09-20 (bổ sung BIF cho D01/D02/D04/D09/D10/D11; D04 thêm sau D01, D02; D04 đã loại bỏ; D09 sàng lọc trên 200 câu; D10/H1 trên 155 câu bảng dài; D11 chạy bản v3 rút gọn trên toàn bộ 992 câu test; D12 biểu diễn pipe trên 500 câu test đầu). Chỉ ghi các direction đã được triển khai trong repository này; số liệu dưới đây là kiểm tra lại trên artifact đã lưu, không dùng để chọn phương pháp theo tập test.

Danh sách hướng đề xuất đầy đủ: [POMA improvement directions](2026-09-19-poma-improvement-directions.md).

| Direction | Đã làm | Kết quả và trạng thái |
|---|---|---|
| **D01 — Fair scorer and provenance** | Thêm chế độ `run_eval.py --strict` để từ chối ID trùng/thiếu/thừa, câu trả lời rỗng, sai chính sách candidate và lỗi metric; ghi SHA-256 của prediction, QAs, tables và mã scorer. Chuyển artifact cũ sang schema chung mà vẫn giữ hash nguồn; tạo bản một đáp án và audit ghép cặp có manifest, 10.000 bootstrap mẫu. Chạy GSA cho few-shot bằng `openrouter/qwen/qwen3-8b` để có đối chứng cùng finalizer. | **Hoàn thành audit D01 trên 992 câu test.** POMA mới lấy đáp án đầu **66,63% EM**, few-shot gốc **67,34%**; hiệu −0,71 điểm, khoảng tin cậy ghép cặp 95% [−3,33; +1,81]. Sau retry lỗi GSA, dùng cùng finalizer và cùng quy tắc dự phòng: POMA **68,45%**, few-shot **70,16%**; hiệu −1,71 điểm [−3,93; +0,50]. BIF trên đúng hai artifact fallback là **76,43%** cho POMA và **76,10%** cho few-shot (+0,33); BIF chưa có khoảng tin cậy ghép cặp. Không có bằng chứng POMA vượt few-shot trong đối chứng EM này. |
| **D02 — Deployable formatter / GSA** | Chạy GSA làm selector xuất đúng một đáp án cho POMA và Few-shot, cùng model `openrouter/qwen/qwen3-8b`, prompt `grounded_single_answer.v1`, QAs và scorer. Retry riêng các lỗi GSA; dùng fallback đáp án raw đầu chỉ cho các lỗi contract còn lại. | **Chốt bằng GSA.** GSA nâng POMA-first từ **66,63%** lên **68,45% EM**, nhưng Few-shot + GSA đạt **70,16% EM**. BIF tăng 75,00→76,43 cho POMA và 73,83→76,10 cho few-shot. Không tiếp tục tinh chỉnh GSA trên test. Các formatter quy tắc rẻ hơn GSA không triển khai trong D02 này. |
| **D04 — Narrow arithmetic executor (R2)** | Port nguyên văn executor AST, prompt planner, few-shot và serialize bảng của RankA; luật R2 chốt trước khi gọi API: chỉ ghi đè khi `exec_status=ok`, plan có `count/sum/avg/argmax/argmin` và không có `compare`. Planner chạy `openrouter/qwen/qwen3-8b` (cùng provider Alibaba như các baseline, `temperature=0`, tắt thinking theo giao thức RankA), một lần gọi cho mỗi câu, độc lập với reader nên dùng chung cho mọi reader. Không có GBNF trên OpenRouter nên plan được parse sau khi sinh, lỗi ghi `parse_error`, không sửa. Subset 200 câu test phân tầng theo hint (`create_qas_subset.py --size 200 --seed 42`, chốt trước khi chạy). Đối chứng: baseline ZS/CoT/FS/POMA-first/POMA+GSA/FS+GSA cùng model, cắt trên đúng 200 câu; nhánh `FS + CoT-gate` thay đáp án FS bằng đáp án CoT trên đúng các câu executor kích hoạt (kiểm soát "tính toán bằng prompt" cùng cổng, không thêm lệnh gọi). | **Không thấy lợi ích.** Executor chỉ kích hoạt **11/200 câu**, mọi reader đều đã đúng **11/11** câu này; executor đúng 9/11 và làm sai 2 câu. R2 so với reader: FS 69,5→68,5; POMA-first 68,5→67,5; POMA+GSA 70,0→69,0; FS+GSA 71,5→70,5; mỗi cặp **0 thắng, 2 thua, 198 hòa**, hiệu −1,0 điểm [−2,5; 0,0]. Đo headroom trên 992 câu test (không gọi API): lỗi mà một executor có thể sửa **tối đa khoảng 1,8–3,2 điểm EM của FS, thực tế dưới ~1 điểm**, và cổng R2 không chạm tới câu sai nào trong subset (0/15). Trạng thái: **LOẠI BỎ D04**; phần executor của D05 không còn cơ sở, D03 không bị ảnh hưởng. Chi tiết ở mục “Quyết định D04” bên dưới. |
| **D09 — Table representation arms** | Thêm `preprocessing/variants.py` (lớp làm sạch bảng + 6 cách serialize mới) và chạy Qwen3-8B zero-shot (OpenRouter, provider Alibaba, cấu hình của `run_baseline.py`) trên subset 200 câu test cho 8 nhánh: Flatten V1 gốc, V1 đã làm sạch, pipe, pipe + đường dẫn header, Markdown, Markdown-KV, neo hàng/cột, JSON. | **Không nhánh nào thắng Flatten V1 có ý nghĩa thống kê.** EM: V1 gốc 52,5%; Markdown-KV 56,5% (+4,0, KTC 95% [−2,0; +10,0]); pipe 56,0%; pipe + đường dẫn header 55,5%; JSON 51,0%. Làm sạch đơn lẻ: −1,5 [−5,5; +2,5]. Nhánh KV tốn 1,9 lần token đầu vào. Đây là bước sàng lọc trên test, chưa xác nhận; xem mục Ghi nhận của D09. |
| **D10 — Long-table row selection (H1)** | Thêm `preprocessing/reduction.py`: với bảng Flatten V1 > 2.000 token và câu hỏi không có dấu hiệu tổng hợp, giữ header + top-k hàng theo BM25 (cộng hàng chứa ô được nêu trong câu hỏi), thứ tự gốc, kèm dòng ghi chú số hàng; ngược lại giữ bảng nguyên. Chạy Qwen3-8B zero-shot `v3_zs_minimal` trên 155 câu test có bảng > 2.000 token, k=20 (chính) và k=10 (độ nhạy). | **Tiết kiệm token lớn, EM không kém hơn.** k=20: token đầu vào −46,6% và chi phí −35,3% trên 155 câu; EM 52,3 → 54,2 (+1,9, KTC 95% [−2,6; +7,1]); F1 70,7 → 72,8. k=10: token −54,9%, EM 52,3 → 52,3. Chưa xác nhận trên dev. **Chú ý:** con số −46,6% là trên tập con bảng dài với solver zero-shot một lệnh gọi; khi ghép vào POMA nhiều tầng và tính trên cả 992 câu thì chỉ còn −6,4% (xem D11). Xem mục Ghi nhận của D10. |
| **D11 — POMA v3 rút gọn (v3lite)** | Cài `poma_v3lite/` theo sơ đồ v3 đã cắt: H1 rút gọn bảng dài, một solver POMA, formatter quy tắc, và cổng answerability hai bước (chỉ chạy khi đáp án là `Null`). Chạy Qwen3-8B trên **toàn bộ 992 câu test** với hint lấy sẵn từ lần chạy POMA cũ; control POMA chạy mới cùng phiên. Dựng 5 artifact lồng nhau để tách đóng góp từng thành phần. | **Không thành phần nào có ý nghĩa thống kê.** Control 68,35 → v3lite 68,75 EM (+0,40, KTC 95% [−0,50; +1,31]; 13 thắng / 9 thua). Từng bước: formatter +0,20; H1 +0,10; cổng +0,10. Tiết kiệm token thật khi triển khai chỉ 6,4% (không phải 26%), và cổng thêm 16% số lệnh gọi. Cổng có mặt trái: trong 16 lần thay `Null`, chỉ 5 lần cứu đúng, 4 lần phá `Null` đúng. Xem mục Ghi nhận của D11. |
| **D12 — Biểu diễn pipe, 500 câu test đầu** | Thêm `pipe_nohdr` (một dòng lược đồ có nhãn `Cột:` rồi các hàng nối bằng dấu gạch đứng) và cho `reduce_table` chạy trên chuỗi pipe (cổng 2.000 token đo trên chuỗi thật sự gửi). Chạy zero-shot Qwen3-8B, prompt `v3_zs_minimal`, qua OpenRouter trên 500 câu đầu của test với 4 nhánh: `v1_raw` (đối chứng, chạy lại), `pipe_clean`, `pipe_nohdr`, `pipe_h1`. Chấm EM/F1/ROUGE-1/METEOR và BIF. | **Không nhánh nào có ý nghĩa thống kê.** EM: `v1_raw` 60,2; `pipe_clean` 60,2 (+0,0 [−3,0; +3,0], không tái hiện +3,5 của D09); `pipe_nohdr` 62,2 (+2,0 [−1,0; +5,0] so với `v1_raw`); `pipe_h1` 60,4 (+0,2 so với `pipe_clean`, chỉ 38 câu bị đổi). BIF 69,51 / 70,24 / 70,62 / 70,41. `pipe_nohdr` đáng xác nhận: trong các câu khác nhau, nhóm đáp án khác nội dung thắng nhiều hơn thua. Token API thật chỉ giảm 5,0% (pipe) và 27,2% (pipe + H1). Chưa xác nhận trên dev hay full; xem mục Ghi nhận của D12. |
| **D13 — LLM lọc header dựng bảng compact** | Thêm `preprocessing/header_filter.py`: làm sạch lưới, xóa trắng mọi ô không có tag `<header>`, gắn mã `[Hk]`, cho LLM chọn header, rồi dựng bảng compact gồm các cột và hàng của header được chọn. Chạy Qwen3-8B zero-shot trên 200 câu test phủ toàn bộ 76 bảng (trong test) đạt một trong ba tiêu chí cấu trúc, phần còn lại lấp theo phân phối hint. Ba nhánh: `v1_raw` (control), `v1_clean`, `hdrfilter`. | **Âm và có ý nghĩa thống kê — loại bỏ.** EM: control 65,5; `v1_clean` 67,5 (+2,0 [−2,5; +6,5]); `hdrfilter` **51,0 (−14,5, KTC 95% [−21,0; −8,0])**, 9 thắng / 38 thua. Bộ lọc giữ trung bình 39,8% số cột; **179/200 câu không chọn được hàng nào** (bảng không có header cột trái), và trong 21 câu nó cắt hàng thì EM 28,6 so với 52,4. Trong 38 câu thua chỉ 7 câu do mất ô đáp án; **17/38 câu mất ít nhất một cột điều kiện** (tỷ lệ cột điều kiện giữ lại 54,7% ở nhóm thua so với 86,5% ở nhóm hòa), nên cơ chế gây hại là **mất cột định vị hàng**, không phải mất cột đáp án. Prompt solver giảm 52,8% nhưng lệnh gọi lọc sinh trung bình 1.807 completion token, nên **tổng token tăng 75,9%** và chi phí ×2,75. Xem [review và thí nghiệm D13](2026-09-20-llm-header-filter-review.md). |

## Tổng hợp: đã học được gì sau 6 direction

### Quy ước dùng trong tài liệu này

- **Phiên** = một lượt chạy loạt API liên tục tại một thời điểm, với cấu hình cố định (model, provider, prompt, tham số sinh). Hai con số đo ở hai phiên khác nhau không so trực tiếp được, vì chính nhánh đối chứng cũng đổi giữa hai phiên (xem mục dưới).
- **Control** = nhánh đối chứng của một thí nghiệm. Ở D11 là POMA-first trên bảng Flatten V1 nguyên: không H1, không formatter, không cổng.
- **Ghép cặp (paired)** = hai nhánh chạy trên đúng cùng một tập câu hỏi, nên so được từng câu một và bootstrap theo cặp. Mọi khoảng tin cậy trong tài liệu này đều là ghép cặp.
- **Ghép/splice** = lấy đáp án của control cho những câu mà nhánh xử lý có prompt giống hệt control từng byte, thay vì gọi API lại. Chỉ hợp lệ **trong cùng một phiên**.

### Bảng điểm các hiệu ứng đã đo

| Direction | Hiệu ứng đo được (EM; BIF nếu có) | Kết luận |
|---|---|---|
| D01/D02 — GSA làm finalizer | EM POMA so với few-shot: **−1,71** [−3,93; +0,50]; BIF: **+0,33** (không có KTC) | Không có bằng chứng POMA vượt few-shot |
| D04 — Executor số học | EM **−1,0** [−2,5; 0,0] trên 200 câu; BIF **−0,38** ở cả 4 reader | Loại bỏ vì giá trị kỳ vọng thấp |
| D09 — 8 cách biểu diễn bảng | EM cao nhất +4,0 [−2,0; +10,0]; BIF cao nhất `pipe_clean` **+2,21** trên 200 câu | Không nhánh nào thắng Flatten V1 có ý nghĩa |
| D10 — H1 chọn hàng | EM k=20 **+1,9** [−2,6; +7,1]; BIF k=20 **+0,72**, k=10 **+0,97** trên 155 câu bảng dài | Tiết kiệm token thật, EM không kết luận được |
| D11 — v3 rút gọn | EM **+0,40** [−0,50; +1,31]; BIF **+0,64** trên 992 câu | Không thành phần nào có ý nghĩa |

**Mọi khoảng tin cậy đều chứa 0.** Sau 6 direction, chưa có can thiệp nào cải thiện EM một cách có ý nghĩa thống kê.

### Vấn đề lớn nhất: độ nhiễu giữa các lần chạy

Ở D11, chạy lại **đúng cấu hình control** (cùng model, cùng provider, cùng hint lấy sẵn, cùng prompt) cho EM **68,35** trong khi artifact cũ `poma_first.json` là **66,63** — lệch **+1,7 điểm**, với 50 câu thắng, 33 câu thua và 145/992 câu khác chữ.

**Đây là một quan sát đơn lẻ, không phải độ lệch chuẩn đã đo.** Nó chứng minh độ lệch ≥ 1,7 điểm *đã từng xảy ra một lần* giữa hai lần chạy cùng cấu hình; nó **không** xác lập được một "sàn nhiễu". Nhưng chỉ riêng điều đó đã đủ nghiêm trọng: độ lệch này **lớn hơn mọi hiệu ứng trong bảng trên**, kể cả +1,9 của D10 và +0,40 của D11. Chừng nào chưa đo được phân bố này, không kết quả nào trong khoảng ±1 điểm là diễn giải được.

### Headroom so với phần thực sự lấy được

| Cơ chế | Trần lý thuyết | Thực tế lấy được |
|---|---|---|
| Executor số học (D04) | 1,8–3,2 điểm | 0 (cổng không kích hoạt câu nào sai) |
| Cổng answerability (D11) | 4,7 điểm (47 câu Null giả) | +0,1 (thay 16 câu: 5 đúng, 4 phá Null đúng, 7 vẫn sai) |
| Consensus 2 nhánh (chưa làm) | +5,2 điểm | Cần adjudicator đạt ≥ 45,9% trên 224 câu bất đồng để được +3 |

Mẫu lặp lại: **headroom đo được luôn lớn, phần lấy được luôn gần 0.** Lý do chung là cơ chế can thiệp không phân biệt được trường hợp nên sửa với trường hợp không nên sửa — executor kích hoạt đúng những câu reader đã làm đúng; cổng không phân biệt `Null` giả với `Null` thật; adjudicator không có tín hiệu trên 44,2% số câu mà cả hai nhánh cùng sai.

### Đã loại trừ, kèm mức độ bằng chứng

| Hướng | Mức độ | Căn cứ |
|---|---|---|
| Program Agent / executor số học | Giá trị kỳ vọng thấp, **chưa bị bác bỏ bằng KTC** | Trần 1,8–3,2 điểm; 0 thắng / 2 thua trên 200 câu |
| Đổi cách biểu diễn bảng | Không nhánh nào có ý nghĩa | 8 nhánh trên 200 câu, KTC đều chứa 0 |
| Consensus + adjudicator | Loại bằng số học, **chưa chạy thực nghiệm** | Cần x ≥ 32,6% để hòa, ≥ 45,9% để +3; 44,2% câu bất đồng là cả hai cùng sai |
| Generalist trên view thay thế | Loại bằng số đã có | Majority 3 view 55,5% < markdown_kv đơn lẻ 56,5% |
| Nhánh Why riêng | Lỗi phân loại | Why ≠ không trả lời được; n = 23 trên test |

## Ghi nhận của D01 và D02

- File POMA mới có 560/992 câu nhiều candidate. Nếu yêu cầu một đáp án mà không bật `--strict`, evaluator cũ vẫn chấm chúng như đáp án rỗng và trả mã thoát 0. Chế độ mới từ chối kết quả đó trước khi ghi báo cáo.
- Best-of-K đạt **80,24%** trên POMA cũ và **74,90%** trên POMA mới. Hai số này là *oracle diagnostic*, không phải độ chính xác của hệ thống xuất một đáp án. POMA cũ lấy đáp án đầu đạt **67,74%**, khác run POMA mới; hiệu so với few-shot là +0,40 điểm [−2,12; +2,92]. Run POMA mới có đủ **992/992 trace chuyên gia**; các trace ghi `openrouter/qwen/qwen3-8b` và hash nguồn khớp manifest GSA.
- GSA POMA lưu 990 đáp án hợp lệ và 2 lỗi định dạng; cách chấm cũ tính lỗi là sai cho **68,35% EM**. Sau retry, GSA few-shot lưu 989 đáp án hợp lệ và 3 lỗi, chi phí API theo manifest **$0,477802**. Áp cùng quy tắc dự phòng bằng đáp án raw đầu cho 2 và 3 lỗi tương ứng; so sánh GSA ghép cặp có **53 thắng, 70 thua, 869 hòa** cho POMA. Đây là phân tích thăm dò vì quy tắc dự phòng được chốt sau khi thấy lỗi test. Artifact few-shot gốc có **18/992** bản ghi `parse_ok=false` và không có manifest sinh đầy đủ.
- BIF được chấm trên **992/992** đáp án sau fallback: `0,5 * PhoBERTScore F1 + 0,5 * P(entailment)` của ViNLI XLM-R Large bốn nhãn, theo chiều reference → prediction. Đây là metric semantic/NLI phụ trợ, không dùng để thay thế phép kiểm định EM ghép cặp.
- **Quyết định D02:** GSA đã hoàn thành vai trò selector một đáp án và được đóng ở đây. Có thể sửa lỗi schema như một việc bảo trì độc lập, nhưng không dùng test này để chọn thêm prompt, fallback hay biến thể GSA.
- Tất cả điểm D01 dùng cùng tập `dataset/qas_test.json`, cùng mã scorer được băm SHA-256 và cùng chính sách một đáp án. Khoảng tin cậy lấy mẫu theo câu hỏi, chưa gom cụm theo bảng. Đầu ra POMA và few-shot vẫn khác thời điểm sinh và ngân sách suy luận; D01 không suy ra lợi ích nhân quả của kiến trúc nhiều agent.
- **Giới hạn provenance lịch sử:** file raw POMA/few-shot không có manifest sinh đầy đủ; trace POMA lưu `prompt_preview` chứ không lưu nguyên văn mọi prompt. Hash xác nhận chính xác các file hiện có, nhưng không thể khôi phục commit/prompt đầy đủ của lần sinh cũ từ các file đó.
- **Giới hạn thiết kế thử nghiệm:** đây là audit hậu nghiệm trên test đã có, chưa sinh lại toàn bộ dev với run manifest mới và chưa ghép ngân sách token/call. Muốn xác nhận một cải tiến mới, cần chốt phương pháp trên dev trước khi chạy test mới.

Hash của QAs: `e6995557340ab95a75d3fbcc4a9f01c5c5934f4e3cd0849fccb4981f45b24a39`; mã scorer: `6ddd7cf62ff24730908f306b92361b8eb5f4b4a512a06de8aaa7d5dfb8a65432`; trace POMA mới: `571374de1c3ef6a92d067f4405afb4da6c50c786ffea3f61982b51ecf0af26cf`. Hash của từng prediction, manifest model/prompt/settings và bootstrap nằm trong `outputs/d01/openrouter_qwen_qwen3-8b/fair_audit.json`.

Mã tái lập: `scripts/prepare_d01_artifacts.py`, `scripts/audit_d01.py`. Khi chấm riêng từng file một đáp án, dùng `run_eval.py --candidate-policy single-required --strict`; BIF reports ở `outputs/evaluation/bif/` (không đưa vào Git). Báo cáo máy đọc và các artifact dẫn xuất ở `outputs/d01/openrouter_qwen_qwen3-8b/` (không đưa vào Git). Nhật ký này sẽ được nối thêm khi direction khác hoàn tất.

## Ghi nhận của D04

### Cách hoạt động của D04

D04 không thay reader mà thêm một kênh tính toán tất định chỉ can thiệp vào một nhóm phép toán hẹp. Với mỗi câu hỏi:

1. **Reader chạy như cũ** và cho một đáp án (FS, POMA-first, POMA+GSA hoặc FS+GSA; artifact D01/D02 có sẵn).
2. **Planner** (`qwen/qwen3-8b` qua OpenRouter, một lệnh gọi, thinking tắt) nhận bảng đã đánh chỉ số cột/dòng (`[0]=Quận | [1]=Dân số`, dòng `1: ...`), câu hỏi, và 6 ví dụ có sẵn. Nó không trả lời mà xuất JSON `{"plan", "route": "ast"|"text", "ast"}`, trong đó `ast` là cây phép toán trên một DSL nhỏ: `select`, `filter` (`equals/contains/gt/ge/lt/le`), `project`, `argmax/argmin`, `count`, `sum/avg`, `compare`, `const`, `set_union/set_intersect`, `sort`, `take`, `lookup_title`. Planner không thấy đáp án gold hay nhãn hint.
3. **Executor** (`src/table_executor/ast_executor.py`, không dùng model) chạy cây trên `table_rows`. Nó tự đọc số kiểu Việt (`95.664`, `3,5`) và trả một giá trị, hoặc lỗi. Kết quả được gán `ok`, `empty`, `error`, `text` hoặc `parse_error` (JSON hỏng, không được sửa).
4. **Cổng R2** (`r2_override`, chốt nguyên văn từ RankA): chỉ khi trạng thái `ok`, cây có ít nhất một trong `count/sum/avg/argmax/argmin`, và không có `compare`, thì đáp án của reader bị thay bằng giá trị executor (số nguyên bỏ `.0`; số thập phân tối đa 4 chữ số). Mọi trường hợp khác giữ nguyên đáp án reader. `compare` bị loại để không phụ thuộc vào cách scorer coi `Có/Đúng/Phải` là một.
5. Planner độc lập với reader nên một log planner dùng chung cho mọi reader; `scripts/build_d04_arms.py` chỉ áp cổng lên từng artifact reader để tạo nhánh `+R2`. Nhánh đối chứng `FS + CoT-gate` cũng dùng đúng cổng đó nhưng thay bằng đáp án CoT.

Khác RankA duy nhất là bộ giải mã: RankA ép JSON hợp lệ bằng ngữ pháp GBNF của llama.cpp, OpenRouter không có nên plan được parse sau khi sinh.

- **Loại bằng chứng:** thử nghiệm thăm dò trên test, kiểm tra chuyển giao một luật đã chốt từ RankA, không phải chọn phương pháp trên test. Luật R2, prompt planner, few-shot và cách hiển thị bảng được giữ nguyên trước khi gọi API; sau khi thấy kết quả không chỉnh cổng, tập phép toán hay prompt. Hướng D04 gốc yêu cầu chạy trên dev (`docs/research/enhance_poma/2026-09-19-poma-improvement-directions.md`, D04) và D01 ghi rõ phương pháp mới cần chốt trên dev trước khi chạy test; lần chạy này theo yêu cầu dùng subset test 200 câu, nên không dùng để chọn thêm biến thể.
- **Công bằng so sánh:** mọi nhánh dùng `qwen/qwen3-8b` qua OpenRouter, provider Alibaba (mọi 200/200 lệnh gọi planner trả về Alibaba), cùng `qas` con, cùng scorer `exact_match` strict một đáp án qua `scripts/audit_d01.py`. Baseline lấy từ artifact D01/D02 cắt theo ID (đã có sẵn, không sinh lại): reader gốc chạy ở chế độ thinking mặc định của OpenRouter, còn planner tắt thinking theo giao thức RankA. Đây là chênh lệch có chủ ý nhưng cần ghi nhận, vì reader RankA vốn không thinking.
- **Số liệu (EM, n=200, cùng subset):** ZS 64,0; CoT 61,0; FS 69,5; POMA-first 68,5; POMA+GSA 70,0; FS+GSA 71,5; FS+R2 68,5; POMA-first+R2 67,5; POMA+GSA+R2 69,0; FS+GSA+R2 70,5; FS+CoT-gate 69,5. Ở cả bốn reader, R2 cho 0 thắng, 2 thua, 198 hòa, hiệu −1,0 điểm, khoảng tin cậy ghép cặp 95% [−2,5; 0,0] (bootstrap theo câu, chưa gom cụm theo bảng). FS+R2 so với FS+CoT-gate: −1,0 [−2,5; 0,0]. Nhánh `FS + CoT-gate` trùng hoàn toàn với FS (0 thắng, 0 thua, 200 hòa) vì cả hai kênh đã đúng trên mọi câu cổng kích hoạt, nên đối chứng này không đo được gì về tính toán bằng prompt so với tất định; chỉ nói được rằng trên cùng cổng, ghi đè bằng executor gây 2 lỗi còn thay bằng CoT gây 0. POMA-first so với FS: −1,0 [−7,5; +5,5]; POMA+GSA so với FS+GSA: −1,5 [−7,0; +4,0].
- **BIF (n=200, alpha=0,5):** Zero-shot 70,0517; Few-shot 74,1804→73,7967 với R2; POMA-first 74,5034→74,1197; POMA+GSA 75,8777→75,4940; Few-shot+GSA 75,7627→75,3790. Vì vậy R2 giảm đúng **0,3837 điểm BIF** ở cả bốn reader; Few-shot+CoT-gate giữ nguyên 74,1804. CoT không có BIF do BERTScore gặp `device-side assert` trên artifact đó, nên không điền một giá trị không tái lập. BIF chưa có bootstrap ghép cặp.
- **Phễu kích hoạt:** trạng thái planner trên 200 câu là `ok` 110, `parse_error` 37, `error` 30, `empty` 14, `text` 9. Chỉ 15 câu `ok` có phép toán trong R2; 4 câu bị loại vì có `compare`; còn **11 câu** bị ghi đè. Trong 37 `parse_error`, 31 do ngoặc JSON không cân bằng (24 thừa, 7 thiếu): đây là lỗi mà GBNF của RankA ngăn được và OpenRouter không có, nên cổng R2 hẹp hơn nhiều (5,5% số câu, so với ~12% ở RankA).
- **Câu bị ghi đè:** 11 câu gồm 9 `count` và 2 `argmax`. Executor đúng cả 2 `argmax` và 7/9 `count`; 2 câu `count` sai đều trả `0`: `23_1_17` lọc `gt 8.5` trên cột có ô dạng `8.0%`, mà `parse_number` không đọc được đơn vị `%` nên mọi ô bị bỏ qua; `99913_0_4` lọc `equals "Lò Lẹt"` trên cột `Tên (trong sử Việt)` thay vì cột `Ghi chú`. Đây là lỗi planner/filter, không phải lỗi định dạng số. Cả 11 câu này reader đã đúng (ZS/CoT/FS/POMA đều đúng), khác RankA, nơi reader chỉ đúng khoảng 27–29% trên nhóm bị ghi đè. CoT chỉ đạt 61,0 EM chung (nhánh yếu nhất, thấp hơn FS 8,5 điểm) mà vẫn đúng 11/11 trên nhóm này, nên độ mạnh của reader không giải thích được; điều quan sát được là cổng R2 chọn các phép đếm nhỏ tầm thường (đáp án đếm là 2, 2, 7, 2, 2, 1, 2, 3, 7 và hai câu `argmax` tra cứu `Moskva`, `Al Noor Tower`) mà mọi nhánh đều làm đúng. Chênh lệch thinking giữa reader OpenRouter và reader RankA vẫn là một khác biệt giao thức cần ghi nhận, nhưng chưa có thí nghiệm cô lập nên không dùng làm giải thích chính. Đây là mô tả trên 11 câu, không phải kết luận về phân bố toàn tập.
- **Chi phí:** planner 200 câu tốn **$0,0822** (~3,15k token prompt và ~93 token completion mỗi câu, trung bình 2,66 s/câu); 992 câu ước ~$0,41. Tiêu tốn thêm một lệnh gọi mỗi câu chưa cộng vào baseline.
- Hash: subset QAs (`outputs/d04/qas_test_200.json`) `7b0b23a1918c0242e095d5bad74bfdc1b60d5a95d68db606177de3e5bcbf9844`; log planner `c562d02b4df2126fbcc45f9891d49997117f36e2d696140b4d8a08f4cc5e307f`; `src/table_executor/planner.py` `d563efa6061acde9d9d6f8f6aedf016cb186b4d5939b1e49356ed62a4df7ff34`; scorer `6ddd7cf62ff24730908f306b92361b8eb5f4b4a512a06de8aaa7d5dfb8a65432` (trùng D01). Hash artifact từng nhánh và bootstrap trong `outputs/d04/openrouter_qwen_qwen3-8b/d04_audit.json`.
- Mã tái lập: `src/table_executor/` (executor và planner), `scripts/run_d04_planner.py`, `scripts/build_d04_arms.py`, `scripts/analyze_d04.py`, `scripts/measure_d04_headroom.py`, kiểm thử `tests/table_executor/`, `tests/scripts/test_build_d04_arms.py`. Chạy: `create_qas_subset.py --size 200 --seed 42 --output outputs/d04/qas_test_200.json`; `run_d04_planner.py --qas ... --out outputs/d04/openrouter_qwen_qwen3-8b/planner_log.jsonl`; `build_d04_arms.py`; `audit_d01.py` với các `--system/--compare` tương ứng; `analyze_d04.py`. Artifact ở `outputs/d04/` (không đưa vào Git).

### Đo headroom của D04 (không gọi API, 992 câu test)

Chạy bằng `scripts/measure_d04_headroom.py` trên các artifact một đáp án đã có và scorer D01; kết quả ở `outputs/d04/openrouter_qwen_qwen3-8b/d04_headroom.json`. Đây là phân tích hậu nghiệm trên test, chỉ dùng để quyết định ưu tiên, không để chọn tham số.

- **Nhóm "Sử dụng tính toán" (195 câu):** FS sai 63 (EM 67,69), POMA-first sai 63, POMA+GSA sai 64, FS+GSA sai 57. Tính riêng nhóm này, EM gần bằng EM chung, nên hint này không đánh dấu một vùng yếu đặc biệt của reader thinking.
- **Câu có gold là số thuần (214 câu):** FS sai 44, POMA-first sai 55, FS+GSA sai 38. Tách theo kiểu lỗi (FS / POMA-first): cùng giá trị nhưng khác định dạng **12 / 2**, sai giá trị **18 / 22**, không trả về số **14 / 31** (FS: 5 `Null` và 9 văn bản khác; POMA-first: 8 `Null` và 23 văn bản khác, phần văn bản khác chưa phân loại tiếp). Executor chỉ có thể sửa hai nhóm sau; nhóm định dạng thuộc formatter (D02), nhóm `Null` thuộc D08.
- **Trần lý thuyết:** nếu executor sửa được mọi câu sai giá trị và không trả số của FS thì được tối đa (18+14)/992 ≈ 3,2 điểm, hoặc 1,8 điểm nếu chỉ tính sai giá trị. Đây là trần, không phải dự báo. Nhân với độ chính xác có điều kiện của executor RankA (khoảng 51–59%) và với tỉ lệ planner thực sự chạm tới các câu này, ước lượng thô là dưới 1 điểm (suy luận, chưa đo).
- **Độ phủ thực tế trên subset 200 câu:** có 38 câu hint tính toán, FS sai 15, cổng R2 kích hoạt trên 0/15 câu sai này (cả 11 câu kích hoạt đều là câu FS đã đúng). Trong 15 câu sai: 7 bị `parse_error`; ít nhất 6 câu sai vì gold có đơn vị hoặc dấu thập phân kiểu khác (ví dụ gold `2 năm`, `100 tỷ USD`, `138,3` so với đáp án `2`, `100`, `138.3`), không phải lỗi tính; 1 câu `sum` bị lỗi vì ô `29,56ha`. Chỉ khoảng 3–5 câu là lỗi số học mà một planner hoàn hảo có thể sửa, tức tối đa vài điểm phần trăm trên 200 câu, khớp với trần trên.

### Quyết định D04: loại bỏ

**D04 được loại bỏ khỏi danh sách hướng cần làm tiếp.** Lý do, theo thứ tự quan trọng:

1. **Không còn chỗ để sửa.** Trên subset, cả 11 câu R2 ghi đè đều đã được mọi reader làm đúng (kể cả CoT, nhánh yếu nhất), còn 15 câu tính toán FS sai thì cổng không kích hoạt câu nào. Trên 992 câu, trần lý thuyết của executor là khoảng 1,8–3,2 điểm EM cho FS và ước lượng thực tế dưới ~1 điểm (suy luận, chưa đo).
2. **Phần lớn lỗi số không phải lỗi số học.** Với câu có gold là số thuần, FS có 12/44 câu sai chỉ do định dạng và 14/44 không trả về số; chỉ 18/44 là sai giá trị. Lỗi kiểu `2 năm` so với `2`, `138,3` so với `138.3` cần formatter, không cần executor.
3. **Executor có rủi ro làm sai.** Trên cùng cổng nó gây 2 lỗi mới (`%` không parse được; filter sai cột), còn thay bằng CoT gây 0 lỗi. Không nhánh nào tăng EM: 0 thắng, 2 thua, 198 hòa ở cả bốn reader.
4. **Chi phí giao thức.** Thêm một lệnh gọi planner mỗi câu (~$0,0004/câu) và mất khoảng 18% plan do không có GBNF trên OpenRouter; sửa lỗi này chỉ thêm khoảng 5 câu kích hoạt trong 200.

**Giới hạn của quyết định:** kiểm tra trên subset 200 câu test theo yêu cầu, cộng phân tích headroom hậu nghiệm trên 992 câu test; chưa chạy trên dev và chưa chạy 792 câu test còn lại. Đây là loại bỏ theo giá trị kỳ vọng thấp, không phải bác bỏ bằng khoảng tin cậy; hiệu ứng +3 điểm của RankA (reader không thinking) vẫn có thể đúng trong cấu hình của RankA.

**Tác động lên các hướng khác:**
- **D05:** phần executor không còn đóng góp kỳ vọng trên API POMA. D03 (retrieved demonstrations) là hướng độc lập, không bị ảnh hưởng.
- **Mở rộng D02 (formatter đơn vị/định dạng số, kiểm tra `Null` số) không giúp POMA hơn FS.** Formatter là bước hậu xử lý không phụ thuộc kiến trúc, nên áp lên FS thì FS+GSA cũng tăng theo. Dữ liệu D01/D02 ủng hộ nhận định này: FS+GSA đã đạt **70,16%** so với POMA+GSA **68,45%** trên 992 câu, và số câu chỉ sai định dạng trên gold số là FS **12** so với POMA-first **2** (POMA đã có bước chuẩn hoá đáp án), tức formatter mới còn có nhiều chỗ sửa hơn ở FS. Vì vậy nếu mở rộng D02, kỳ vọng FS tăng ít nhất bằng POMA và POMA không có lợi thế kiến trúc riêng. Đây là suy luận từ số liệu hiện có, chưa được đo cho formatter mở rộng.

## Ghi nhận của D09

Tài liệu ứng viên và lý do chọn nhánh: [table-representation-candidates](2026-09-19-table-representation-candidates.md). Đây là **sàng lọc thăm dò trên subset 200 câu test** (`outputs/d04/qas_test_200.json`) với 12 phép so sánh cặp không hiệu chỉnh; chưa chạy dev và chưa chạy các thay đổi cục bộ (banner, chuyển vị bảng stub).

### Cách làm

- **Lớp làm sạch** (`Grid.cleaned`, chốt trước khi gọi API): bỏ dấu trích dẫn trong ô (`[12]`, `[a]`, `[ghi chú n]`, `[cần dẫn nguồn]`), bỏ cột không có giá trị nào, bỏ cột chỉ chứa tên tệp ảnh hoặc đường dẫn, bỏ hàng dữ liệu rỗng; quay về bảng gốc nếu không còn gì. Kiểm tra trước bằng đáp án chuẩn (không dùng đầu ra model, `scripts/check_d09_clean_safety.py`): trên 200 câu subset **không câu nào mất đáp án** (0/80 ô nguyên khối, 0/125 chuỗi con). Trên 992 câu test có 1 câu mất đáp án nguyên ô và 3 câu mất chuỗi con, đều do bỏ dấu trích dẫn. Trên toàn bộ ba tập có 76 cột rỗng, 39 cột chỉ có trích dẫn và 6 cột ảnh.
- **8 nhánh**, cùng một lô, cùng câu hỏi: `v1_raw` (Flatten V1 hiện tại, không làm sạch), `v1_clean` (V1 + làm sạch), `pipe_clean` (bỏ tag `<header>`), `pipe_path_clean` (gộp header nhiều hàng thành `Cha / Con`, đưa banner ra dòng `Chú thích:`), `markdown_clean`, `markdown_kv_clean`, `row_anchor_clean` (`col :` và `row i :`), `json_clean` (`{"columns", "data"}`, không escape ASCII). Nhánh HTML giữ span đã bỏ theo yêu cầu.
- **Giao thức:** giống `run_baseline.py --prompt-style zero_shot` hiện tại: prompt `v3_zs_minimal` (định dạng trung tính, chỉ đổi chuỗi bảng), schema `baseline_zero_shot.v1`, `temperature=0`, `top_p=1`, `max_tokens=10000`, `timeout=60`, model `openrouter/qwen/qwen3-8b` với provider Alibaba, thinking mặc định của provider, 12 luồng. Runner riêng `scripts/run_d09_representation.py` không kế thừa kiểm tra `TABLE_STR:` trong `baseline/run.py:280`: kiểm tra đó luôn thất bại với prompt `BANG:` của `v3_zs_minimal`, nên `run_baseline.py --prompt-style zero_shot` hiện không chạy được.
- Chấm bằng `evaluation.exact_match` đã đóng băng qua `scripts/audit_d01.py` (strict, một đáp án, bootstrap cặp 10.000 mẫu). Chi phí API tổng khoảng $0,73 cho 1.600 lệnh gọi (cộng các lần thử lại).

### Kết quả (200 câu, EM/F1 %, token là trung bình đầu vào mỗi câu)

| Nhánh | EM | F1 | BIF | Token vào | Chi phí (200 câu) |
|---|---:|---:|---:|---:|---:|
| `v1_raw` (control) | 52,5 | 69,9 | 63,81 | 1.436 | $0,086 |
| `v1_clean` | 51,0 | 68,3 | 61,97 | 1.393 | $0,082 |
| `pipe_clean` | 56,0 | 71,6 | **66,02** | 1.387 | $0,083 |
| `pipe_path_clean` | 55,5 | 71,2 | 64,52 | 1.364 | $0,084 |
| `markdown_clean` | 52,5 | 69,8 | 64,14 | 1.527 | $0,088 |
| `markdown_kv_clean` | **56,5** | **73,5** | 65,28 | 2.621 | $0,114 |
| `row_anchor_clean` | 54,0 | 70,9 | 64,61 | 1.618 | $0,089 |
| `json_clean` | 51,0 | 68,7 | 63,06 | 1.507 | $0,089 |

Đủ bốn metric (%, cùng scorer đã khoá; ROUGE-1 là F1; KTC cặp chỉ tính cho EM):

| Nhánh | EM | F1 | ROUGE-1 | METEOR | BIF |
|---|---:|---:|---:|---:|---:|
| `v1_raw` (control) | 52,50 | 69,86 | 63,10 | 68,14 | 63,8080 |
| `v1_clean` | 51,00 | 68,32 | 61,32 | 66,49 | 61,9662 |
| `pipe_clean` | 56,00 | 71,58 | 65,85 | 70,13 | **66,0152** |
| `pipe_path_clean` | 55,50 | 71,16 | 64,35 | 68,73 | 64,5211 |
| `markdown_clean` | 52,50 | 69,76 | 63,35 | 69,14 | 64,1378 |
| `markdown_kv_clean` | **56,50** | **73,45** | **68,04** | **72,99** | 65,2845 |
| `row_anchor_clean` | 54,00 | 70,87 | 64,39 | 69,32 | 64,6052 |
| `json_clean` | 51,00 | 68,71 | 62,07 | 67,30 | 63,0565 |

Hiệu EM theo cặp, KTC 95% (thắng/thua):

- Làm sạch đơn lẻ (`v1_clean − v1_raw`): −1,5 [−5,5; +2,5] (7/10).
- Bỏ tag `<header>` (`pipe_clean − v1_clean`): +5,0 [0,0; +10,0] (18/8). Giả thuyết đáng kiểm tra, nhưng cận dưới đúng bằng 0 và đây là 1 trong 12 phép so sánh.
- Đường dẫn header và banner (`pipe_path_clean − pipe_clean`): −0,5 [−4,5; +3,5].
- Định dạng, so với `pipe_path_clean`: Markdown −3,0 [−8,0; +2,0]; Markdown-KV +1,0 [−4,0; +6,0]; neo hàng/cột −1,5 [−6,5; +3,5]; JSON −4,5 [−9,5; +0,5].
- So với `v1_raw`: Markdown-KV +4,0 [−2,0; +10,0] (22/14); `pipe_clean` +3,5 [−1,5; +9,0]; `pipe_path_clean` +3,0 [−2,0; +8,0]; neo hàng/cột +1,5 [−3,5; +6,5]; Markdown 0,0 [−5,0; +5,0]; JSON −1,5 [−6,5; +3,5].

### Diễn giải và giới hạn

- **Không có bằng chứng để thay Flatten V1.** Mọi khoảng tin cậy so với `v1_raw` đều chứa 0. Thứ hạng giữa các nhánh không đáng tin ở n=200; số câu theo nhóm cấu trúc chỉ 92/56/29/23 nên bảng theo nhóm trong `d09_analysis.json` chủ yếu là nhiễu.
- **Markdown-KV có điểm cao nhất nhưng đắt.** Nó tốn 1,9 lần token đầu vào và chi phí cao hơn 33% cho mức tăng vẫn nằm trong nhiễu; hơn `pipe_path_clean` chỉ +1,0.
- **Prompt chi phối kết quả hơn định dạng.** Cùng subset, cùng model, cùng chuỗi Flatten V1, artifact zero-shot cũ (prompt `v1_zs` dài, có quy tắc ngắn gọn) đạt 64,0% EM, còn prompt hiện tại `v3_zs_minimal` chỉ 52,5%. Ở `v3_zs_minimal` câu trả lời dài (trung bình 6,3–7,7 từ so với 3,0 từ của đáp án chuẩn; 48–59/200 câu dài hơn 8 từ), và EM phạt độ dài. Chênh lệch −11,5 điểm lớn hơn mọi hiệu ứng định dạng đo được (tối đa +4). Cần chọn rõ "baseline cũ" là prompt nào trước khi kết luận thêm.
- **Hai lệnh gọi không có đáp án hợp lệ**, chấm sai bằng đáp án dấu hiệu `[NO_VALID_ANSWER]` ghi trong manifest: `json_clean` câu `99924_3_142` (model trả `null` thay vì chuỗi, thử lại vẫn lỗi) và `markdown_clean` câu `38_1_35` (đáp án rỗng). Mỗi nhánh chịu tối đa 1/200 câu; 8–11 lệnh gọi mỗi nhánh cần sửa schema (`repair_attempted`).
- Đây là dữ liệu test dùng để chọn nhánh, nên nhánh dẫn đầu phải được xác nhận trên dev trước khi coi là kết luận.

### Kiểm tra nhóm "chỉ có header gộp" (pipe_clean thấp hơn V1: 48,28 so với 51,72, n=29)

Chỉ đọc artifact đã lưu, không gọi API. Kết luận: **không tìm thấy nguyên nhân do cấu trúc bảng; đây là nhiễu, và nó chỉ ra một nhiễu lớn hơn nhiều ở phía prompt.**

1. **Chênh lệch là 1 câu, không phải tín hiệu.** 48,28 = 14/29, 51,72 = 15/29. Trong 29 câu chỉ 5 câu khác kết quả (pipe thắng 2, thua 3). Bốc ngẫu nhiên 29 câu từ 200, độ lệch pipe−V1 tệ bằng hoặc hơn −3,4 điểm xảy ra **20,8%** số lần (permutation 20.000 mẫu). Theo bốn nhóm, `pipe_clean − v1_raw` là +2,2 / +5,4 / −3,4 / +13,0; đây là 4 nhóm quan sát rồi mới nhặt nhóm âm, nên không được coi là phát hiện.
2. **Không phải lỗi của định dạng pipe.** Trên đúng nhóm này `pipe_clean` **hơn** `v1_clean` (+10,3; 3 thắng, 0 thua). Phần thấp hơn `v1_raw` đến từ lớp làm sạch: `v1_clean − v1_raw` là 0 thắng, 4 thua (−13,8). Nhưng lớp làm sạch chỉ bỏ chú thích `[6]`, `[84]`, `[1]` và một cột liên kết, không mất nội dung; 4 câu thua đều là đổi kiểu trả lời (2 câu gold `Null`: bảng gốc model trả `null`, bảng sạch model viết một câu giải thích; 1 câu thêm `, tất cả các tập…`; 1 câu đổi danh sách phẩy thành đánh số). `pipe_clean` gộp hai yếu tố (định dạng + làm sạch) nên so thẳng với `v1_raw` bị nhiễm.
3. **Phát hiện chính: phần lớn chênh lệch giữa các nhánh là lệch phong cách trả lời, không phải đọc bảng khác.** Kiểm tay 29 câu `pipe_clean` khác `v1_raw` trên cả 200 câu: **23/29 (79%) là phong cách** (15 thêm/bớt chữ như `tỉnh Ninh Thuận` so với `Ninh Thuận`, 4 câu từ chối không viết `Null`, 4 khác cách viết như `40,0` so với `40.0°c`) và **6/29 (21%) là khác nội dung thật** (`5` so với `20`, `x-34` so với `x-37`, `140` so với `80`, …; trong 6 câu này pipe thắng 4, thua 2). *Ghi chú sửa lỗi:* phép phân loại tự động đầu tiên của tôi báo 100% là cùng nội dung vì bắt nhầm chuỗi con (`5` nằm trong `50`); con số 79/21 là sau khi kiểm tay.
4. **Nguồn của nhiễu phong cách là prompt `v3_zs_minimal`.** Trên 200 câu, đáp án trung bình **7,0 từ** so với gold **3,0** (prompt cũ `v1_zs`: 2,9 từ), và model viết đúng chữ `null` chỉ **4** lần trên 11 câu gold `Null` (`v1_zs`: 10 lần). Giữa hai prompt có 49 câu khác kết quả; 51% là thêm/bớt chữ, 12% là định dạng `Null`.
5. **Điểm dữ liệu chưa giải thích được:** hai artifact zero-shot cùng prompt `v1_zs`, cùng 200 câu cho EM 64,0 (artifact D04) và 67,0 (`q2_revision`, scorer khoá, single-required). Chênh 3 điểm giữa hai lần chạy cùng prompt; chưa rõ do tham số hay do trôi giữa các lần chạy.

**Hệ quả cho thiết kế thí nghiệm:** EM là công cụ kém để so sánh cách biểu diễn bảng khi prompt còn sinh câu trả lời dài. Hiệu ứng biểu diễn thật (khoảng 21% số câu khác nhau, tức vài câu trên 200) nhỏ hơn nhiều so với nhiễu phong cách (79%). Cần cố định phong cách trả lời trước khi so sánh biểu diễn, hoặc dùng thêm thước đo ít nhạy với độ dài.

### Tái lập

- Mã: `preprocessing/variants.py`, `scripts/run_d09_representation.py`, `scripts/check_d09_clean_safety.py`, `scripts/build_d09_artifacts.py`, `scripts/analyze_d09.py`. Kiểm thử: `tests/preprocessing/test_variants.py` (kể cả `v1_raw` khớp `FlattenedTable.to_string()` trên cả 329 bảng) và `tests/scripts/test_build_d09_artifacts.py`.
- Lệnh: `run_d09_representation.py --workers 12 --out outputs/d09/openrouter_qwen_qwen3-8b/records.jsonl`; `build_d09_artifacts.py --score-missing-as-wrong`; `audit_d01.py` với các cặp `--compare` ở trên; `analyze_d09.py`. Artifact ở `outputs/d09/openrouter_qwen_qwen3-8b/` (không đưa vào Git).
- SHA-256: `records.jsonl` c1e994387019b9817774f56e91177e05d01cff2de2d9195f27c559ffae000b84; `variants.py` 4a7cd0724bc3379e6639bd342a010854be03f8c54f0fdd9ed53fa5ebf9cd7b81; `run_d09_representation.py` 9dd42761c751ba048ceac7f65cf389bf653d53fbd6c2ac5a0df57912e56dbac5; QAs con 7b0b23a1918c0242e095d5bad74bfdc1b60d5a95d68db606177de3e5bcbf9844; scorer 6ddd7cf62ff24730908f306b92361b8eb5f4b4a512a06de8aaa7d5dfb8a65432. Cây làm việc chưa commit khi chạy (`working_tree_dirty_at_audit=true`).

## Ghi nhận của D10 (H1: chọn hàng cho bảng dài)

Mục tiêu chính là **tiết kiệm token**; tăng EM/F1 là phần thưởng. Chạy **thăm dò trực tiếp trên test**, theo yêu cầu, chỉ trên 155 câu test có bảng Flatten V1 dài hơn 2.000 token (tokenizer Qwen3, 15,6% tập test). 837 câu còn lại có prompt giống hệt control theo thiết kế nên không chạy. Luật và `k=20` là nhánh chính được chốt trước khi gọi API; `k=10` là độ nhạy. Không chỉnh gì sau khi thấy kết quả.

### Cách hoạt động

- **Điều kiện kích hoạt:** bảng > 2.000 token, **và** câu hỏi không chứa dấu hiệu cần nhiều hàng (`bao nhiêu`, `mấy`, `tổng`, `trung bình`, `số lượng`, `đếm`, `liệt kê`, `sắp xếp`, `thứ tự`, `nhất`, `hơn`, `kém`, `so với`, `chênh lệch`, `cùng`, `giống`, `khác nhau`, `tất cả`, `toàn bộ`, `mỗi`, `những`, `các`, `đầu tiên`, `cuối cùng`, `tăng`, `giảm`). Nếu không, hoặc BM25 không có điểm nào, hoặc giữ lại ≥ 80% số hàng, trả nguyên bảng.
- **Chọn hàng:** BM25 (unigram + bigram, IDF trong chính bảng) giữa câu hỏi và từng hàng; giữ top-k, cộng tối đa k hàng có một ô (≥ 2 ký tự) xuất hiện nguyên vẹn trong câu hỏi. Giữ mọi hàng header, giữ thứ tự gốc, thêm dòng `[Ghi chú: bảng gốc có N hàng dữ liệu; chỉ hiển thị m hàng liên quan đến câu hỏi.]`. Vì Flatten V1 lặp giá trị ô gộp vào từng hàng nên hàng được giữ không mất nhãn nhóm.
- **Thiết kế trước khi chạy (không dùng đầu ra model):** trên train+dev, với câu tra cứu có đáp án là một ô, hàng chứa đáp án còn lại 250/254 (k=20) và 249/256 (k=10) trong train, 24/25 ở cả hai k trong dev; tiết kiệm token khoảng 41–50% trên câu bảng dài.
- **Giao thức** như D09: `v3_zs_minimal`, schema `baseline_zero_shot.v1`, `temperature=0`, `top_p=1`, `max_tokens=10000`, `timeout=60`, `openrouter/qwen/qwen3-8b` (Alibaba), thinking mặc định. Nhánh H1 chỉ gọi model khi chuỗi bảng thật sự thay đổi (k=20: 91/155 câu; k=10: 94/155); các câu khác lấy đáp án của control (cùng prompt). Câu bị chặn: 58 vì dấu hiệu tổng hợp, 6 (k=20) hoặc 3 (k=10) vì giữ ≥ 80% số hàng.

### Kết quả (155 câu test, %)

| Nhánh | EM | F1 | ROUGE-1 | METEOR | BIF | Token đầu vào (API) | Chi phí | Token đầu ra |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `v1_raw` (control) | 52,26 | 70,70 | 62,10 | 66,36 | 64,2366 | 865.218 | $0,1762 | 164.872 |
| `h1_k20` (chính) | 54,19 | 72,80 | 64,94 | 70,02 | 64,9569 | 461.954 (−46,6%) | $0,1140 (−35,3%) | 131.772 |
| `h1_k10` (độ nhạy) | 52,26 | 72,87 | 65,15 | 70,76 | **65,2097** | 390.038 (−54,9%) | $0,1050 (−40,4%) | 130.455 |

- **Tiết kiệm token:** trên chính các câu bị rút gọn, token đầu vào giảm 70,1% (k=20) và 81,4% (k=10). Token của chuỗi bảng (đếm bằng tokenizer Qwen3) giảm 47,9% / 56,6% trên 155 câu; nếu tính trên cả 992 câu test là 26,3% / 31,0% (kế hoạch tính không gọi API).
- **Độ trễ trung bình mỗi lệnh gọi** 29,3 → 17,4 giây (k=20) và 16,3 giây (k=10). Con số này nhiễu vì chạy 12 luồng song song ở các thời điểm khác nhau.
- **EM theo cặp so với control:** k=20 +1,9 [−2,6; +7,1] (thắng 9, thua 6); k=10 0,0 [−4,5; +4,5] (6/6); k=10 so với k=20 −1,9 [−7,1; +3,2]. Trên riêng lát cắt bị rút gọn: k=20 48,4 → 51,6 (n=91); k=10 48,9 → 48,9 (n=94).
- **Quy đổi sang toàn tập test** (giả định 837 câu còn lại không đổi, phép tính co giãn của tôi, không phải phép đo): hiệu EM khoảng +0,3 điểm, khoảng tin cậy khoảng [−0,4; +1,1]; cận dưới nằm trên biên −1 điểm đã đề xuất.
- **Câu thua (k=20, 6 câu):** ba câu chỉ do lời dài hơn quanh đáp án đúng (`Không, ...`, `trường Phúc Kiến`), một câu đáp án rỗng, và hai câu đáp án khác hẳn (`99924_3_125`, `3_2_167`). Tôi chưa kiểm tra từng câu xem hàng bằng chứng có bị bỏ không.

### Giới hạn

- **Thăm dò trên test, 155 câu**, 2 nhánh, không hiệu chỉnh; khoảng tin cậy đều chứa 0. Kết quả chứng minh tiết kiệm token với EM không thấy giảm, không chứng minh EM tăng.
- Câu có bảng dài chiếm 15,6% test, nên tác động lên EM toàn tập nhỏ; lợi ích thực là chi phí (token) và độ trễ.
- **Prompt `v3_zs_minimal` cho câu trả lời dài**, nên nhiều thắng/thua chỉ là chênh lệch độ dài lời đáp; F1, ROUGE-1 và METEOR tăng ổn định hơn EM (F1 +2,1 đến +2,2).
- Các câu có dấu hiệu tổng hợp (58/155) vẫn dùng bảng nguyên, tức là phần bảng dài khó nhất (EM thấp ở nhóm không phải tra cứu) không được giải quyết bởi H1.
- Đáp án rỗng chấm sai bằng đáp án dấu hiệu `[NO_VALID_ANSWER]`: `99924_3_142` (cả ba nhánh), `0_1_150` (k=20), `9997_3_83` (k=10). Một lệnh gọi control (`99924_2_166`) lỗi schema lần đầu, chạy lại trả `null`.
- Đầu ra của một lần chạy 992 câu bị dừng giữa chừng còn trong `records.jsonl` (326 câu control ngoài 155 câu; không dùng); hai file `*_failed_nokey.*` là lần chạy đầu thiếu khoá API.

### Vì sao chọn ngưỡng 2.000 token

Ngưỡng là một con số tròn tôi chọn từ phép đo mô tả trước khi chạy H1; **không được tối ưu hay chỉnh theo kết quả nào**, và các ngưỡng khác (1.000, 4.000) chưa được thử. Các lý do:

- **Nơi độ chính xác bắt đầu tụt.** Trên 992 câu test, EM theo cỡ bảng (Flatten V1, token Qwen3; các mốc chia 500/1.000/2.000/4.000 do tôi đặt): zero-shot cũ khoảng 65–68% với bảng ≤ 2.000 token, rồi 50,5% (2.000–4.000, n=93) và 38,7% (> 4.000, n=62); few-shot 66,7% và 48,4% ở hai mốc đó; POMA-first 69,9% và 61,3%. Bảng ≤ 2.000 token không thấy sụt. Đây là tương quan (bảng dài cũng có nhiều câu tổng hợp hơn), chưa chứng minh bảng dài là nguyên nhân.
- **Nơi có nhiều token nhất.** 155/992 câu test (15,6%) có bảng > 2.000 token nhưng chiếm 54,8% tổng token bảng. Trên dev là 142/991 câu. Bảng này gần p85 của kích thước bảng (p90 khoảng 2.500 trên dev, 3.100 trên test; kiểm tra trước đó ghi p90 ≈ 2.097 bằng tokenizer khác).
- **Nơi giảm hàng có ý nghĩa.** Bảng có ít hàng thì top-k giữ gần hết và H1 tự trả bảng nguyên; với k=20, bảng dưới khoảng 25 hàng hầu như không đổi. Ngưỡng giúp tránh làm thay đổi prompt ở nhóm bảng ngắn có độ chính xác cao, nơi nguy cơ mất bằng chứng chưa được kiểm tra.
- **Tính đơn giản:** một ngưỡng tròn, không có bậc thang hay tham số phụ.

Giới hạn: phép đo EM theo cỡ bảng dùng các kết quả đã có trên chính tập test, nên ngưỡng không hoàn toàn độc lập với test. Ngưỡng cũng chỉ dựa trên phép đo mô tả, không phải trên phép so sánh nhiều ngưỡng. Muốn chọn ngưỡng có cơ sở thì phải so sánh trên train+dev (xem mục bên dưới).

### Có nên bỏ ngưỡng 2.000 token, áp dụng H1 cho mọi bảng?

**Quyết định: không làm ở giai đoạn này.** Ước tính bằng số ký tự của bảng (không gọi API; khớp phép đo token: 27,4% so với 26,3% cho k=20), trên cả 992 câu test:

| Cấu hình | Số câu được rút gọn | Tiết kiệm chuỗi bảng toàn tập |
|---|---:|---:|
| k=20, chỉ bảng > 2k token (đã chạy) | 91 | 27,4% |
| k=20, mọi bảng | 186 | 30,1% |
| k=10, chỉ bảng > 2k token | 94 | 32,7% |
| k=10, mọi bảng | 369 | 40,9% |

- Với k=20, bỏ ngưỡng chỉ thêm khoảng +2,7 điểm phần trăm tiết kiệm, vì bảng ngắn thường dưới khoảng 25 hàng nên H1 giữ từ 80% số hàng và tự trả bảng nguyên (`few_rows`, 339 câu). Muốn tiết kiệm thêm đáng kể phải giảm k xuống 10 (+8 điểm), nhưng trên bảng dài k=10 chỉ bằng control về EM (52,3 so với 54,2 của k=20).
- Bằng chứng độ chính xác hiện chỉ có trên 155 câu bảng dài. Bảng ≤ 2k token có EM cao nhất, chiếm khoảng 45% token bảng (trung vị 925 token), nên rủi ro lớn hơn còn lợi ích tuyệt đối mỗi câu nhỏ hơn.
- Giới hạn chính của tiết kiệm là luật dấu hiệu tổng hợp: 458/992 câu (46%) giữ bảng nguyên, không phải ngưỡng 2k.
- Nếu muốn mở rộng sau này: so ngưỡng (2k, 1k, không ngưỡng) và k (20, 10) trên train+dev, cùng control, không điều chỉnh trên test.

### Tái lập

- Mã: `preprocessing/reduction.py`, `scripts/run_d09_reduction.py` (`--long-only`), `scripts/build_d09_artifacts.py --splice ... --base-arm v1_raw`, kiểm thử `tests/preprocessing/test_reduction.py`. `run_d09_representation.py` được thêm tham số `table_str` sau khi chạy D09 (hành vi cũ không đổi; hash ghi ở D09 là của bản trước).
- Artifact ở `outputs/d09/h1_test/` (không đưa vào Git): `records.jsonl`, `plan.json`, `qas_test_long.json`, `arms/`, `h1_audit.json`. Chấm bằng `audit_d01.py` (strict, một đáp án, bootstrap cặp).
- SHA-256: `records.jsonl` 56fbb306e1312588b32f7adb8c145e58b5c1d09cb696c34fd7c4b6ed7fbaea28; `reduction.py` 945c2be78a399289dacf51801fc572f5db7ad3131fd6716a4e535e20ee5f529c; `run_d09_reduction.py` db35db87647271d39d7581d41bfe112aec483754b1f22453ea88493e4f2110c3; `plan.json` a0aa1355883b6f958513b513831f52f87c41fba5ec7762c19f1d470cd9df7ec7; `qas_test_long.json` d65de98ab466816f96556d6e0fe219e0af33b9473bf57129873f7b1ab14b52b7.

## Ghi nhận của D11 (POMA v3 rút gọn)

Cài đặt bản rút gọn của sơ đồ `poma3.drawio` sau khi cắt Program Agent, Generalist và tầng consensus/adjudicator. Chạy **toàn bộ 992 câu test**, `openrouter/qwen/qwen3-8b` (provider Alibaba). Hint lấy từ `predicted_hints` của lần chạy POMA cũ nên hai nhánh định tuyến giống hệt nhau và không gọi lại HintPredictor.

### Vì sao control phải chạy lại

POMA **không tái lập từng bit**: chạy lại 8 câu bảng ngắn với cùng hint chỉ cho lại 7/8 đáp án cũ. Vì vậy không ghép được với `poma_first.json`; control được chạy mới trong cùng phiên. Trong một phiên thì phép ghép vẫn đúng cho các câu H1 không đổi bảng, vì prompt của chúng giống hệt control từng byte (901/992 câu).

**Control mới đạt 68,35 EM, trong khi `poma_first.json` cũ là 66,63** — lệch +1,7 điểm, lớn hơn mọi hiệu ứng đo được bên dưới. 50 câu thắng, 33 câu thua, và chỉ 847/992 câu có đáp án trùng chữ. Đây là nhiễu giữa các lần chạy cộng với việc dùng hint lấy sẵn. **Không được đặt 68,75 cạnh các số 66,63 / 68,45 / 70,16 đã ghi mà không nói tới độ lệch này.**

### Kết quả (992 câu test, EM/BIF %)

| Nhánh | Thành phần cộng thêm | EM | BIF | So với control |
|---|---|---:|---:|---|
| `control` | POMA-first, Flatten V1 nguyên | 68,35 | 75,3282 | — |
| `control_fmt` | + formatter quy tắc | 68,55 | 75,5038 | EM +0,20 [−0,30; +0,71]; BIF +0,1756 |
| `h1` | + H1 rút gọn bảng dài | 68,45 | 75,5745 | EM +0,10 [−0,40; +0,60]; BIF +0,2463 |
| `h1_fmt` | + cả hai | 68,65 | 75,7501 | EM +0,30 [−0,40; +1,01]; BIF +0,4219 |
| `v3lite` | + cổng answerability | 68,75 | **75,9673** | EM +0,40 [−0,50; +1,31]; BIF +0,6391 |

**Mọi khoảng tin cậy đều chứa 0.** Tổng cộng 13 câu thắng và 9 câu thua trên 992. Kết quả này không chứng minh bản rút gọn hơn control, và cũng không thu hẹp khoảng cách với few-shot + GSA (70,16 ở audit D01).

### Từng thành phần

- **H1 (rút gọn bảng dài).** Đổi bảng của 91/992 câu, tiết kiệm 26,3% token chuỗi bảng và 42,3% token prompt trên chính 91 câu đó. Nhưng **token prompt thật khi triển khai chỉ giảm 6,4%** (6.358.343 → 5.950.649) và chi phí solver giảm 2,5%. Con số −46,6% của D10 là trên tập con bảng dài với solver zero-shot một lệnh gọi; dưới POMA nhiều tầng, phần bảng chiếm tỉ lệ nhỏ hơn trong prompt nên hiệu ứng bị pha loãng. Trên riêng 91 câu bị rút gọn, EM 69,23 → 70,33.
- **Formatter quy tắc.** Đổi 0/301 dự đoán trong lượt kiểm tra sớm và rất ít trên toàn tập: POMA đã có agent AnswerNormalization nên đầu ra vốn sạch. Formatter được thiết kế cho đầu ra thô (few-shot, zero-shot), không cho POMA. Hai câu thua lộ ra hai lỗi quy tắc: (a) luật bỏ trích dẫn `[n]` đã cắt `[2]` khỏi `99913_4_107` mà gold giữ nguyên `[2]`; (b) `format_candidates` bỏ ứng viên `Null` nên khi specialist đầu trả `Null` thì ứng viên thứ hai được đôn lên — đó là **chính sách chọn đáp án trá hình thành làm sạch**, và ở `99955_3_24` nó phá một `Null` đúng.
- **Cổng answerability.** Kích hoạt trên 83/992 câu, 159 lệnh gọi LLM, 0 lỗi. Headroom đo trên chính run này là 47 câu `Null` giả (precision 0,45) tức 4,7 điểm EM. Cổng chỉ lấy được +0,10. Phân tích 16 lần thay `Null`: **5 lần cứu đúng, 4 lần phá `Null` đúng, 7 lần sai vẫn sai** — độ chính xác khi thay là 5/16. Trong 67 lần giữ `Null`, 35 lần gold đúng là `Null`. Cổng không phân biệt được `Null` giả với `Null` thật, mà 45/992 gold là `Null` thật.

### Chi phí

Control 992 câu tốn $1,7158 và 6.358.343 token prompt, trung bình 38,1 giây mỗi câu (16 luồng). Bản v3lite khi triển khai tốn $1,6734 và 5.950.649 token prompt ở tầng solver, **cộng thêm 159 lệnh gọi cổng (+16% số lệnh gọi)** mà tôi **không ghi lại chi phí** — đây là thiếu sót của bộ đo, nên con số tiết kiệm 2,5% ở trên chưa trừ phần này và gần như chắc chắn là âm.

### Giới hạn

- Thăm dò trực tiếp trên test, 5 nhánh, không hiệu chỉnh trên dev. Mọi khoảng tin cậy chứa 0.
- Control dịch +1,7 điểm so với artifact cũ, lớn hơn mọi hiệu ứng đo được. Nếu cần so với few-shot thì phải chạy lại few-shot trong cùng phiên.
- Quy tắc formatter đã chốt trước khi chấm (viết từ quy ước gold của train/dev), nhưng hai lỗi nêu trên chỉ lộ ra sau khi chấm trên test. **Tôi không sửa chúng rồi chấm lại**, vì như vậy là tinh chỉnh trên test; muốn sửa thì phải kiểm trên dev.
- Chi phí của cổng không được ghi lại.
- Một câu lỗi schema (`9994_2_140`, lỗi escape JSON) phải chạy lại mới xong.

### Tái lập

- Mã: `poma_v3lite/` (`formatter.py`, `table_search.py`, `answerability.py`), `scripts/run_v3lite.py`, `scripts/run_v3lite_gate.py`, `scripts/build_v3lite_artifacts.py`, `scripts/analyze_v3lite.py`, kiểm thử `tests/poma_v3lite/` (43 test).
- Artifact ở `outputs/v3lite/` (không đưa vào Git): `records.jsonl`, `gate.jsonl`, `plan.json`, `arms/`, `audit.json`, `analysis.json`. Chấm bằng `audit_d01.py` (strict, một đáp án, bootstrap cặp 10.000 mẫu).
- SHA-256: `records.jsonl` 760fd0c3e87a5cff8669a077932e855f3aa7eb9be42484b4e536ac2148c6bb0a; `gate.jsonl` 65da0cae2ce29a837ee345d0229a70c8a7b85620b08516f9d67db047020cf2d8; `plan.json` d5e942537f1cfab5837ef09ba61b0378077dd65c0ba3842195bf33ca7dfcaf10; `formatter.py` 163d8ac9a3dad4f4927bd6ee9e0a88924734fce2c923dc74226d0913758b3966; `answerability.py` cdf2c8327894aa9e669ec83f1aa727d2b9bb74a83eefc0d70215ed471a6674e0; `table_search.py` 7bffe1f73d6ad2b939437e144c731cf941d291122073189e737207e1121fe0f1; `run_v3lite.py` 8326251c7979e4b46024cd304be018c8cbd0c60105940b88a595d113e0f2c897; `run_v3lite_gate.py` 5fb9f6e5586e65706f4e43af14247c7c278a4eafd912f7ad9f8db84ba08fc3a4; `build_v3lite_artifacts.py` 899f44c7e828ef5b0c8a261255ef5c4c5d03a6c18455172ed3d24eb974baec51.

## Lỗi parser bảng (phát hiện và sửa 2026-09-19; A/B đầy đủ 2026-09-20)

`preprocessing/parser.py:139` gọi `cell.get_text()` **không có dấu phân cách**, nên các đoạn văn bản nằm trong cùng một ô HTML mà cách nhau bởi `<br>` hoặc thẻ khối lồng nhau bị **dính liền không khoảng trắng**.

Ví dụ thật, câu `0_0_8` ("Walter Hallstein thuộc Đảng nào?"):

```
FLATTEN: 1|Walter HallsteinỦy ban Hallstein|1.1.1958|...|Dân chủ Kitô giáoQuốc gia: CDU|
gold: Dân chủ Kitô giáo
pred: Dân chủ Kitô giáoQuốc gia: CDU
```

Model trả lời **đúng theo những gì nó đọc được**; chuỗi bảng mới là thứ hỏng. Kiểm chứng nguyên nhân:

```python
BeautifulSoup("<td>Dân chủ Kitô giáo<br/>Quốc gia: CDU</td>", "html.parser").td.get_text()
# -> 'Dân chủ Kitô giáoQuốc gia: CDU'        (hiện tại)
# get_text(" ", strip=True) -> 'Dân chủ Kitô giáo Quốc gia: CDU'   (đúng)
```

**Phạm vi (đo bằng cách dựng lại toàn bộ chuỗi bảng ở hai chế độ):** **95/329 bảng đổi nội dung, 325/992 câu test bị ảnh hưởng (32,8%).** Chi tiết ở `outputs/v3lite/parser_fix_scope.json`.

**Vì sao nghiêm trọng:** lỗi nằm ở tầng tiền xử lý, **phía trên mọi direction**. D01, D04, D09, D10, D11 đều đọc cùng chuỗi bảng hỏng này. Nó giải thích một phần mẫu "headroom lớn, lấy được gần 0": không tầng nào phía sau sửa được bằng chứng đã hỏng từ đầu vào.

**Bản sửa sai lần đầu, và vì sao nó bị bắt.** Tôi sửa bằng `cell.get_text(" ")`. Cách đó chèn dấu cách giữa **mọi** nút văn bản, kể cả thẻ inline, nên làm hỏng những ô vốn đang đúng:

| gold | parser cũ | `get_text(" ")` |
|---|---|---|
| `Iese/Hãn Ali-Quli/Mustafa Pasha` | đúng | `Iese / Hãn Ali-Quli / Mustafa Pasha` |
| `xã Dĩnh Trì, thành phố Bắc Giang` | đúng | `xã Dĩnh Trì , thành phố Bắc Giang` |
| `12 (UHF/VHF)` | đúng | `12` |

Đo ghép cặp trên 410 câu đã chạy xong của cả hai nhánh: **−3,41 điểm, 7 thắng / 21 thua.** Bộ test lúc đó không bắt được vì ca inline duy nhất tôi viết là `<b>Hà</b> Nội`, vốn đã sẵn dấu cách nên vẫn pass. **Bài học: một test cho nhánh "không được đổi" chỉ có giá trị khi dữ liệu vào thật sự có thể bị đổi.**

**Bản sửa đúng:** chỉ chèn dấu cách ở ranh giới **thẻ khối** (`<br>`, `<p>`, `<div>`, `<li>`, `<tr>`...), giữ nguyên thẻ inline (`<a>`, `<span>`, `<sup>`, `<b>`, `<i>`, `<abbr>`). Cài trong hàm `_cell_text` của `preprocessing/parser.py`.

Biến môi trường `POMA_LEGACY_CELL_TEXT=1` tái lập hành vi cũ; nó tồn tại **chỉ để chạy A/B**, không dùng khi triển khai. Kiểm chứng: kế hoạch H1 ở chế độ legacy cho lại đúng 1.512.630 token như lần chạy D11; bản sửa đúng cho 1.517.395 (bản sửa sai cho 1.519.879 — chính chênh lệch này giúp phát hiện một tiến trình cũ chưa chết đang ghi đè dữ liệu).

Hồi quy: `tests/preprocessing/test_cell_separator.py`, gồm lớp `TestInlineMarkupMustNotBeSplit` lấy trực tiếp từ 5 ca mà bản sửa sai đã làm hỏng.

**Hệ quả:** chuỗi bảng đổi thì **mọi artifact đã lưu mất giá trị đối chứng**. Mọi con số trong các mục D01, D04, D09, D10, D11 ở trên đều đo trên bảng hỏng và phải đọc với lưu ý đó.

### Kết quả A/B của bản sửa parser (992 câu test)

Chạy hai control đầy đủ, chỉ khác nhau ở parser, hint lấy sẵn giống nhau, chấm ghép cặp bằng `audit_d01.py` (bootstrap 10.000 mẫu). Câu `62_3_178` hỏng schema lặp lại ở **cả hai** nhánh nên bị loại khỏi cả hai; còn **991 câu**.

| Nhánh | EM |
|---|---:|
| `legacy` (parser cũ) | 67,91 |
| `fixed` (parser đã sửa) | 66,50 |
| **Hiệu** | **−1,41 [−3,13; +0,30]** |

**Khoảng tin cậy chứa 0 → không kết luận được bản sửa có hại.** Chỉ **72/991 câu** cho kết quả khác nhau (29 thắng, 43 thua); 919 câu còn lại hai nhánh giống hệt. Chỉ cần 7 câu đổi chiều là dấu kết quả đảo ngược.

Trên riêng 325 câu có bảng thực sự đổi: 64,62 → 62,46 (14 thắng, 21 thua).

**Các câu thắng/thua không phải do bảng hỏng mà do chọn span khác nhau.** Ví dụ thắng: gold `Xã Phật Tích, huyện Tiên Du tỉnh Bắc Ninh`, legacy trả `Chùa Phật Tích` (ô bị dính nên không tách được địa chỉ), fixed trả đúng cả địa chỉ; gold `1679 Niên hiệu Vĩnh Trị thứ 4 thời Lê Hy Tông`, legacy chỉ trả `thời Lê Hy Tông`. Ví dụ thua: gold `Bảo tàng Hà Nội`, fixed trả `Hà Nội`; gold `6`, fixed trả `thế kỷ thứ 6`. Tức là tách ô ra đúng khiến model **chọn được phần nhỏ hơn**, đôi khi trùng gold, đôi khi không.

**Kết luận: giữ bản sửa vì nó đúng về mặt dữ liệu, nhưng không tuyên bố nó cải thiện EM.** Bảng bị dính ô là lỗi thật và chuỗi bảng sau khi sửa trung thực hơn; nhưng hiệu ứng lên EM không đo được, và bị át bởi dao động chọn span.

### N1 — Độ nhiễu giữa các lần chạy: đã có phép đo đầu tiên

Chạy **y hệt một cấu hình hai lần** (cùng model, provider, prompt, hint lấy sẵn, cùng parser cũ), trên 900 câu chung:

| | EM |
|---|---:|
| Lần 1 (`records.jsonl`, arm `control`) | 68,33 |
| Lần 2 (`control_legacy.jsonl`) | 67,89 |
| **Chênh** | **−0,44** |

**98/900 câu (10,9%) cho đáp án khác nhau về mặt chữ dù không đổi bất cứ thứ gì.**

Cộng với quan sát cũ (control 68,35 so với artifact `poma_first.json` 66,63, lệch 1,7 điểm), hiện có **hai điểm dữ liệu về độ trôi: 0,44 và 1,7 điểm**. Vẫn chưa đủ để nói "sàn nhiễu là X" — cần ít nhất ba lần chạy để ước lượng khoảng dao động — nhưng đã đủ để kết luận:

> **Mọi hiệu ứng đã đo trong dự án này (D10 +1,9; D11 +0,40; parser −1,41) đều nằm trong hoặc sát vùng trôi của chính phép đo.**

## Ghi nhận của D12 (biểu diễn pipe, 500 câu test đầu)

Thăm dò **trực tiếp trên test**, 500 câu đầu của `dataset/qas_test.json` (đúng thứ tự file, không chọn lọc), theo yêu cầu, để xem kết quả trước khi duyệt chạy full. Zero-shot `openrouter/qwen/qwen3-8b` (provider Alibaba), prompt `v3_zs_minimal`, schema `baseline_zero_shot.v1`, `temperature=0`, `top_p=1`, `max_tokens=10000`, giống D09; chỉ đổi chuỗi bảng. Parser đã sửa (lỗi ô bị dính liền) nên **không so được với số D09** (D09 chạy trên parser cũ, 200 câu).

### Các nhánh

- `v1_raw`: Flatten V1, đối chứng. Chạy lại vì parser đã đổi 95/329 chuỗi bảng.
- `pipe_clean`: lưới đã làm sạch, các hàng nối bằng dấu gạch đứng, bỏ nhãn `<header>`.
- `pipe_nohdr`: lưới đã làm sạch, một dòng lược đồ có nhãn `Cột:` (tiêu đề nhiều hàng nối thành `Cha / Con`, banner đưa lên `Chú thích:`), rồi các hàng dữ liệu. Ô tiêu đề rỗng để trống, không bịa tên cột; bảng có toàn bộ tiêu đề rỗng (25/329) giữ nguyên hàng tiêu đề gốc. **Nhánh này gần `pipe_path_clean` của D09** (khác ở nhãn `Cột:` và hai xử lý trên), không phải một biểu diễn mới hoàn toàn.
- `pipe_h1`: `pipe_clean` cộng H1 (k=20, luật đóng băng của D10) cho bảng dài hơn 2.000 token **tính trên chuỗi pipe**. H1 đổi 38/500 câu (23 bị chặn vì dấu hiệu tổng hợp, 2 vì giữ từ 80% hàng); các câu còn lại lấy đáp án của `pipe_clean` vì prompt giống hệt từng byte. Kiểm trước khi chạy: trong 26 câu bị rút gọn mà gold xuất hiện nguyên văn trong bảng, cả 26 vẫn giữ gold (kiểm bằng chuỗi con, khá lỏng).

### Kết quả (500 câu, %)

| Nhánh | EM | F1 | ROUGE-1 | METEOR | BIF |
|---|---:|---:|---:|---:|---:|
| `v1_raw` | 60,20 | 75,90 | 69,97 | 72,74 | 69,51 |
| `pipe_clean` | 60,20 | 76,50 | 70,14 | 72,80 | 70,24 |
| `pipe_nohdr` | 62,20 | 77,80 | 71,71 | 74,23 | 70,62 |
| `pipe_h1` | 60,40 | 76,50 | 70,08 | 72,52 | 70,41 |

Hiệu ghép cặp, bootstrap 10.000 mẫu (EM theo `audit_d01.py`, BIF theo điểm từng câu):

| Cặp | EM | BIF |
|---|---|---|
| `pipe_clean` − `v1_raw` | +0,00 [−3,00; +3,00] | +0,73 [−1,06; +2,50] |
| `pipe_nohdr` − `v1_raw` | +2,00 [−1,00; +5,00] | +1,10 [−0,71; +2,92] |
| `pipe_nohdr` − `pipe_clean` | +2,00 [−0,60; +4,80] | +0,38 [−1,10; +1,88] |
| `pipe_h1` − `pipe_clean` | +0,20 [−0,40; +0,80] | +0,17 [−0,38; +0,71] |

**Mọi khoảng tin cậy đều chứa 0.** Bỏ 10 câu có sentinel ở ít nhất một nhánh (n=490) cho cùng kết luận (+0,00 / +2,04 / +2,04 / +0,20).

### Cặp câu khác kết quả: phong cách hay nội dung

Phân loại tự động so từng từ (bỏ dấu câu ở hai đầu từ, giữ dấu trong số, có test). Ba nhóm: `null_format` (gold là `Null`), `extra_words` (một đáp án nằm liền mạch trong đáp án kia), `other` (còn lại; gồm cả đáp án khác nội dung lẫn cách viết khác của cùng giá trị nên phải đọc tay). Số thắng/thua của nhánh đứng trước:

| Cặp | Tổng thắng/thua | `null_format` | `extra_words` | `other` |
|---|---|---|---|---|
| `pipe_clean` vs `v1_raw` | 30/30 | 5/3 | 12/16 | 13/11 |
| `pipe_nohdr` vs `v1_raw` | 36/26 | 3/2 | 13/19 | 20/5 |
| `pipe_nohdr` vs `pipe_clean` | 28/18 | 2/3 | 10/11 | 16/4 |
| `pipe_h1` vs `pipe_clean` | 2/1 | 0/0 | 2/0 | 0/1 |

Đọc tay 20 câu `other` của `pipe_nohdr` so với `pipe_clean`: trong 16 câu `pipe_nohdr` đúng, khoảng **9 là khác nội dung thật** (ví dụ `Torre Madrid Nuevo Norte 3` so với `2`, `Pusong Sawi` so với `21`, `2` so với `1`, một câu `pipe_clean` trả `null` oan), 6 là cách viết (`true` so với `Có`, `16.2°C` so với `16.2`, `Bayern` so với `Bavaria`), 1 mơ hồ. Trong 4 câu `pipe_nohdr` sai: 2 khác nội dung, 1 cách viết, 1 là lệnh gọi lỗi bị chấm sentinel. Tức nội dung thật: **9 thắng, 2 thua** (kiểm nhị thức hai phía p≈0,065, thăm dò, chưa hiệu chỉnh cho 4 phép so sánh). Chênh lệch EM +2,0 phần lớn đến từ đây; hai nhóm phong cách gần triệt tiêu nhau.

### Token và chi phí

| Nhánh | Token chuỗi bảng (TB) | Token prompt API (TB) | Chi phí |
|---|---:|---:|---:|
| `v1_raw` | 1.523,8 | 1.722,5 | $0,2408 |
| `pipe_clean` | 1.451,3 (−4,8%) | 1.635,9 (−5,0%) | $0,2351 |
| `pipe_nohdr` | 1.437,3 (−5,7%) | 1.627,5 (−5,5%) | $0,2349 |
| `pipe_h1` | 1.069,5 (−29,8%) | 1.253,3 (−27,2%) | $0,2099 |

Phần tiết kiệm của H1 lớn hơn cả pipe nhưng chỉ tác động lên 38 câu. **Ở n=500, EM của `pipe_h1` không mang tín hiệu về độ chính xác** (chỉ có thể khác `pipe_clean` ở tối đa 38 câu, tức vài câu, thấp hơn độ trôi 0,44–1,7 điểm đã đo); đây là phép đo chi phí.

### Bổ sung: `nohdr_h1` (`pipe_nohdr` cộng H1, 38 câu)

`pipe_h1` được dựng trên `pipe_clean` nên không có dòng `Cột:`. Nhánh `nohdr_h1` chạy H1 (k=20, cùng luật) trên lưới `pipe_nohdr`, nên dòng lược đồ được giữ (32/38 câu bị rút gọn giữ dòng `Cột:`; 6 câu còn lại là bảng mà chính `pipe_nohdr` đầy đủ cũng không có dòng này: 3 bảng không có hàng tiêu đề và 3 bảng bắt đầu bằng `Chú thích:`). H1 chọn đúng **cùng 38 câu** như `pipe_h1`. Chạy 38 lệnh gọi, 0 lỗi, khoảng $0,019; các câu còn lại lấy đáp án `pipe_nohdr`. Records và plan của nhánh này ở file riêng để không đổi hash của artifact 500 câu đã ghi ở trên.

| Nhánh | EM | BIF | Token prompt API | Chi phí |
|---|---:|---:|---:|---:|
| `pipe_nohdr` | 62,20 | 70,62 | 1.627,5 | $0,2349 |
| `nohdr_h1` | 62,60 | 70,89 | 1.233,7 (−28,4% so với `v1_raw`) | $0,2076 |

- Hiệu EM: `nohdr_h1` − `pipe_nohdr` = +0,40 [−0,60; +1,60]; `nohdr_h1` − `pipe_h1` = +2,20 [−0,40; +5,00] (chênh này phần lớn là chênh của `pipe_nohdr` so với `pipe_clean`). Khoảng tin cậy đều chứa 0.
- Trên riêng 38 câu bị đổi: số câu đúng `pipe_clean` 21, `pipe_nohdr` 20, `pipe_h1` 22, `nohdr_h1` 22. BIF trên 38 câu này: 71,09 / 72,10 / 73,29 / 75,64. Token prompt API trên 38 câu: 7.181 → 2.032 (−71,7%).
- `nohdr_h1` khác `pipe_nohdr` về đúng/sai ở 8 câu: 5 thắng, 3 thua. Một câu thắng (`99924_3_120`) chỉ vì `pipe_nohdr` có lệnh gọi lỗi ở câu đó và bị chấm sentinel; loại câu này thì hiệu là +1 câu trên 499. Ba câu thua đều là phong cách trả lời (`Đúng` viết thành `Có`, hai câu thêm mệnh đề sau đáp án). Trong 5 câu thắng chỉ có 1 câu đổi cực yes/no (`59_4_68`), còn lại là cách chọn span (`Vĩnh Lợi` so với `huyện Vĩnh Lợi`) hoặc cứu lệnh gọi lỗi. Chỉ 21/38 đáp án giữ nguyên chữ.

**Đọc như phép đo chi phí, không phải tín hiệu độ chính xác:** nhánh chỉ có thể khác `pipe_nohdr` ở 38 câu, tức tối đa vài câu, thấp hơn độ trôi 0,44–1,7 điểm đã đo. Điều thu được là H1 ghép được với `pipe_nohdr` mà không làm mất dòng lược đồ và cho mức giảm token API lớn nhất (−28,4%); BIF 70,89 là cao nhất trong 5 nhánh, nhưng chênh với `pipe_nohdr` (+0,27) nằm trong nhiễu.

Tái lập: `scripts/run_repr_stage.py --arms nohdr_h1`, artifact `outputs/repr500/records_nohdr_h1.jsonl`, `plan_nohdr_h1.json`, `arms/nohdr_h1.json` (ghép từ `pipe_nohdr`), `audit_nohdr_h1.json`, `bif/nohdr_h1.json`. SHA-256: `records_nohdr_h1.jsonl` 5917294585cfd7ff70d6bfe98785d3758ff1581a204c38dac76697e2fbca2e83; `plan_nohdr_h1.json` e5cd57502513b15b8651d828ab6de6240d2f28864c3274e75b678b0e1af1ddfa.

### Giới hạn

- Đây là 500 câu đầu của test, thăm dò, không hiệu chỉnh, và bốn phép so sánh chưa hiệu chỉnh.
- **Không tái hiện +3,5 EM của `pipe_clean` ở D09**, nhưng cũng không thể nói D09 là nhiễu: parser, tập câu và số câu đều đổi.
- Trước khi chạy tôi ghi tiên nghiệm rằng `pipe_nohdr` sẽ xấp xỉ `pipe_clean` hoặc thấp hơn chút (nó gần `pipe_path_clean`, đạt 55,5 so với 56,0 ở D09). Kết quả cao hơn (+2,0) nên cần nghi ngờ lát cắt 500 câu trước khi gán công cho nhãn `Cột:`.
- Sentinel `[NO_VALID_ANSWER]`: `v1_raw` 5, `pipe_clean` 4, `pipe_nohdr` 6, `pipe_h1` 4. Phần lớn là model trả `final_answer: null` (JSON null thay vì chuỗi) nên schema từ chối; chạy lại vẫn lỗi ở nhiệt độ 0 (cứu được 4/12).
- Ngưỡng 2.000 token của `pipe_h1` đo trên chuỗi pipe nên số câu bị rút gọn khác D10.
- **H1 không xử lý chủ động các hàng tiêu đề/nhãn nằm giữa bảng.** (a) Hàng có quá nửa ô là `<th>` nằm giữa bảng (13/329 bảng, 48/992 câu test, 30 trong 500 câu đầu) bị parser tách khỏi vị trí gốc và dồn lên đầu, ở mọi nhánh kể cả `v1_raw`; H1 coi chúng là tiêu đề, luôn giữ, không xếp hạng, nên không làm hỏng thêm nhưng cũng không khôi phục liên kết giữa nhãn và các hàng bên dưới. (b) Hàng nhãn nhóm không có `<th>` (mọi ô giống nhau) được coi là hàng dữ liệu và bị H1 xếp hạng như hàng thường. Trong 38 câu H1 đổi bảng, 14 câu có hàng nhãn kiểu này, 11 câu bị vứt ít nhất một hàng, và 121 hàng dữ liệu (10 câu) được giữ nhưng mất nhãn nhóm của chúng. Trên 10 câu đó `pipe_clean` và `pipe_h1` cho kết quả giống hệt (4 cùng đúng, 6 cùng sai), nên chưa đo được tổn hại, nhưng n=10 rất nhỏ và 6/10 câu vốn sai ngay cả trên bảng đầy đủ. Hàng nhãn nhóm được nhận diện bằng phép thử gần đúng (mọi ô không rỗng giống nhau), chưa kiểm tay từng bảng.

### Tái lập

- Mã: `preprocessing/variants.py` (`render_pipe_nohdr`), `preprocessing/reduction.py` (tham số `arm`), `scripts/run_repr_stage.py`, `scripts/analyze_repr_stage.py`, `scripts/build_d09_artifacts.py --splice pipe_h1 --base-arm pipe_clean`; chạy bằng interpreter của conda env `kltn`. Kiểm thử `tests/preprocessing/`, `tests/scripts/test_analyze_repr_stage.py`.
- Artifact ở `outputs/repr500/` (không vào Git): `records.jsonl`, `plan.json`, `qas_500.json`, `arms/`, `audit.json`, `bif/`, `analysis.json`.
- BIF: checkpoint `outputs/models/vinli-xlmr-large-4label/vinli-xlmr-large-4label/checkpoint-best`, nhãn entailment = 0 (kiểm bằng 10 cặp thử), tái hiện đúng BIF 63,8080 của `v1_raw` ở D09.
- SHA-256: `records.jsonl` 4bd99338add7eb5f2f69ae8585d3646f5a59e6be81ae0dec6371162a0bc9bfb7; `qas_500.json` 52065e512580a2ae5cd9525d7323ab9f9532d4b03187f4b5c8aaa636c5f40342; `plan.json` 1f2b91c538f0f8f51356ae31a4f14f0f0ae1a295b78fc280a05f306f3aeb5751.

## Hybrid retrieval BM25 + PhoBERT: đã đo, **không nhận**

Không gọi API. Câu hỏi không phải "BM25 có chính xác không" (recall@20 đã là 99,2% trên phần H1 thật sự rút gọn) mà "có giữ ít hàng hơn mà vẫn đủ recall không", vì mỗi hàng bỏ đi là token tiết kiệm được.

**Luật quyết định chốt trong mã trước khi chạy:** chỉ đưa hybrid vào pipeline nếu `recall@3` của hybrid ≥ `recall@20` của BM25.

Lát cắt: train, bảng ≥ 25 hàng sau khi làm sạch, đáp án xuất hiện nguyên văn ở **đúng một** hàng, và **loại câu có dấu hiệu tổng hợp** (H1 không rút gọn các câu đó). n = 476.

| Bộ xếp hạng | @1 | @2 | @3 | @5 | @8 | @10 | @20 |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 (hiện tại) | 83,8 | **92,4** | **94,5** | **96,2** | **97,5** | **98,1** | 99,2 |
| PhoBERT dense | 80,2 | 87,6 | 89,3 | 91,2 | 93,1 | 95,0 | 96,6 |
| Hybrid tổng chuẩn hoá (α=0,5) | **84,9** | 91,2 | 93,3 | 95,2 | 96,2 | 96,8 | 98,3 |
| Hybrid RRF | 83,4 | 90,3 | 92,4 | 94,1 | 95,6 | 96,2 | **100,0** |

**Kết quả: `hybrid_rrf@3` = 92,44 < `bm25@20` = 99,16 → REJECT.**

- **Dense đơn thuần thua BM25 ở mọi k.** Hai hybrid cũng thua BM25 ở mọi k trừ `hybrid_rrf@20` (100,0 so với 99,2) — tức fusion chỉ vớt được vài ca ở k lớn, đúng trục ngược với thứ ta cần.
- **Vì sao:** hàng bảng phần lớn là chuỗi sự kiện ngắn chứa mã, số và tên riêng. Khớp từ vựng chính xác là đúng công cụ cho dạng đó; embedding ngữ nghĩa làm nhoè định danh chính xác. 15 câu BM25 xếp gold trong top 3 bị hybrid đẩy ra: `Kênh tần số 22 (UHF/VHF) chỉ được sử dụng ở tỉnh thành nào?` (BM25 hạng 0 → hybrid hạng 5), `Mô hình nhà thuộc đơn vị quản lý nào?` (0 → 10).
- **Trần lợi ích end-to-end vốn đã nhỏ trước khi đo:** BM25 trượt 41/784 câu ở k=20, nhưng **37/41 là câu tổng hợp mà luật dấu hiệu đã chặn**. Tỉ lệ trượt thực trên phần H1 xử lý dưới 1%, và H1 chỉ chạm 7,6% số câu, nên retrieval hoàn hảo cũng chỉ đáng dưới 0,1 điểm EM — thấp hơn độ trôi 0,44–1,7 điểm.

**Giới hạn của kết luận này:** `vinai/phobert-large` là masked LM, không phải model embedding câu; mean-pooling đầu ra MLM vốn yếu cho retrieval nếu không tinh chỉnh. Phép đo này bác bỏ **PhoBERT dùng trực tiếp**, không bác bỏ dense retrieval nói chung. Một bi-encoder tiếng Việt được huấn luyện cho retrieval có thể khác; trong cache máy hiện không có model nào như vậy. Cũng chưa thử α khác 0,5 hay chỉ nhúng cột liên quan thay vì cả hàng.

### Điều đáng làm thay vào đó: hạ k

Thứ hạng BM25 của hàng chứa đáp án có **trung vị 0, p90 = 2, p99 = 17**, trong khi ta đang giữ **k = 20**. Ta lấy 20 hàng để bắt một hàng gần như luôn nằm trong top 3. Hạ k xuống 5 (recall 96,2%) hoặc 8 (97,5%) cắt thêm khoảng 3/4 số hàng giữ lại, không cần thêm model nào, và chỉ tốn một lần chạy xác nhận EM không sụt.

### Tái lập

`scripts/probe_hybrid_retrieval.py --limit 500 --batch-size 16`, kết quả `outputs/hybrid/probe_train500.json`. Chạy bằng interpreter của conda env `kltn`. Lần chạy đầu với batch 64 chết vì lỗi CUDA nhất thời trên GPU laptop; batch 16 chạy hết. SHA-256 báo cáo: 0d0b43fed88a0a5bd12618ca30624e952901e2ca3dcde5018d48392d4ba1a7b0.

## Hướng đi tiếp theo

Xếp theo thứ tự cái nào mở khoá cái nào. Hai việc đầu là **đo lường**, không phải can thiệp; chúng phải xong trước thì mọi can thiệp sau mới diễn giải được.

### N1 — Đo độ nhiễu giữa các lần chạy (ưu tiên cao nhất)

Chạy **đúng một cấu hình control ba lần**, giống hệt nhau về model, provider, hint lấy sẵn và prompt, rồi báo cáo khoảng dao động EM.

```bash
python scripts/run_v3lite.py --arms control --qas dataset/qas_test.json --out outputs/v3lite/drift_1.jsonl --plan outputs/v3lite/plan.json --hint-predictions outputs/q2_revision/openrouter_qwen_qwen3-8b/full/raw/poma.json --workers 16
```

(lặp với `drift_2.jsonl`, `drift_3.jsonl`, rồi chấm bằng `audit_d01.py`)

- **Chi phí:** khoảng $5 và 3 giờ. **Không cần viết code mới.**
- **Vì sao đây là việc quan trọng nhất:** D11 cho thấy hai lần chạy cùng cấu hình lệch 1,7 điểm. Nếu sàn nhiễu thật sự ở mức đó thì +1,9 của D10 và +0,40 của D11 đều nằm trong nhiễu, và mọi can thiệp tương lai có trần dưới ~2 điểm đều không đáng chạy trên test.
- **Kết quả dùng để làm gì:** đặt ngưỡng "một hiệu ứng phải lớn hơn bao nhiêu mới đáng tin", và quyết định có cần chạy lặp mỗi nhánh hay không.

### N2 — Chạy lại few-shot + GSA trong cùng phiên với control mới

Hiện đang so 68,75 (D11) với 70,16 (audit D01) từ **một phiên khác**, trong khi đã biết có độ lệch giữa các phiên. Đây chính là phép so sánh đầu bài của luận văn — POMA có hơn few-shot không — và ở dạng hiện tại nó **không vững**.

- Chạy few-shot + GSA và control POMA trong cùng phiên, cùng model và provider, rồi chấm ghép cặp.
- Chi phí thấp hơn N1 vì few-shot chỉ một lệnh gọi mỗi câu.

### N3 — Siết điều kiện thay thế của cổng answerability (phụ thuộc N1)

Cổng hiện thay `Null` với độ chính xác 5/16. Ràng buộc đề xuất: **chỉ thay khi bước re-answer trả về ô được trích dẫn khớp nguyên văn một thực thể trong câu hỏi**; các trường hợp khác giữ `Null`.

- **Trần:** 4,7 điểm. **Thực tế dự đoán:** khoảng +1 điểm hoặc thấp hơn.
- **Cảnh báo:** trần thực tế này **nằm ở hoặc dưới mức lệch 1,7 điểm đã quan sát**. Vì vậy N3 chỉ đáng làm nếu N1 cho thấy sàn nhiễu nhỏ hơn đáng kể.
- **Phải kiểm trên dev**, không phải test. Hai lỗi quy tắc của formatter ở D11 (cắt `[2]` khỏi gold, và `format_candidates` đôn ứng viên khi ứng viên đầu là `Null`) cũng thuộc nhóm này: đã biết cách sửa nhưng **cố tình chưa sửa** để không tinh chỉnh trên test.

### Không nên làm tiếp

- **Thêm một tầng nữa vào pipeline.** Bằng chứng qua năm direction nói rằng điểm số không nằm ở tầng biên: D04, D09, D10, D11 đều cộng thêm thành phần và đều không có ý nghĩa thống kê.
- **Thử thêm một cách biểu diễn bảng.** D09 đã quét 8 cách, không cách nào thắng.
- **Xây consensus/adjudicator** khi chưa có grounding thật, vì thành phần cấp grounding (program agent) đã bị đo là kỳ vọng thấp ở D04.

### Tái lập A/B parser

- `POMA_LEGACY_CELL_TEXT=1` cho nhánh legacy, mặc định cho nhánh fixed; `scripts/run_v3lite.py --arms control`.
- Artifact: `outputs/v3lite/control_legacy.jsonl`, `control_fixed.jsonl`, `audit_parser_ab.json`, `parser_fix_scope.json`.
- SHA-256: `control_legacy.jsonl` c58fa14a7127e4a3c821f4c3b2e0d4b1505639e5d7827253f831b86fddaf2fdd; `control_fixed.jsonl` 369105e39ee0b117aa1ea25b051232f43aad082489bbcd8da780ed4982ef1d29; `parser.py` e821553fc42e71b6c7b92eed637fac7974d84a524c915fcab5e4f0dc7bdba2d7.
