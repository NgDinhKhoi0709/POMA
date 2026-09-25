# D13 — LLM lọc header để dựng bảng compact

Ngày: 2026-09-20. Trạng thái: **đã chạy trên 200 câu; kết quả âm và có ý nghĩa thống kê**. Tài liệu này đánh giá ý tưởng và chốt điều kiện
để nó đáng chạy, dựa trên số đo lại từ artifact đã có (`outputs/v3lite/control_fixed.jsonl`,
992 câu test, Qwen3-8B) và thống kê 329 bảng trong `dataset/table.json`.

## Ý tưởng được đề xuất

1. Sau Flatten V1, làm sạch chú thích / link; xem bảng như ma trận, bỏ dòng/cột rỗng (trừ header).
2. Dựng một "bản header-only": xóa hết giá trị của mọi ô **không** mang tag `<header>`.
3. Đưa bản đó + câu hỏi cho LLM, LLM chọn các header cần thiết.
4. Dựng bảng compact gồm các **cột và dòng** của những header được chọn, rồi mới giải.

## Kết quả thực nghiệm (200 câu, Qwen3-8B zero-shot)

Xem mục "Thí nghiệm" ở cuối tài liệu. Tóm tắt: `hdrfilter` **51,0 EM** so với control `v1_raw`
**65,5 EM**, hiệu **−14,5 điểm, KTC 95% ghép cặp [−21,0; −8,0]**, 9 thắng / 38 thua / 153 hòa.
Tổng token **tăng 75,9%** và chi phí tăng 2,75 lần. Đây là can thiệp đầu tiên trong dự án có khoảng
tin cậy **không chứa 0** — theo chiều có hại. Phần phân tích dưới đây viết trước khi chạy; mọi dự
đoán của nó đều được xác nhận.

## Kết luận ngắn (viết trước khi chạy)

Bước 1 **đã có sẵn** trong repo và đã được đo là không có lợi. Bước 2–4 trên thực tế chỉ là một
**bộ lọc cột** chứ không phải lọc cả dòng lẫn cột, vì 77,8% bảng không có ô header nào ngoài các
dòng header trên cùng. Headroom EM của trục cột là **khoảng 0,5–0,9 điểm**, tức **nhỏ hơn mức
nhiễu 1,7 điểm giữa hai lần chạy cùng cấu hình** đã ghi nhận ở D11. Trục dòng không có headroom.
Nếu làm, phải đóng khung là đóng góp về **hiệu quả token có ràng buộc recall**, không phải đóng
góp về độ chính xác, và phải có baseline không gọi LLM (BM25 chọn cột) để chứng minh lệnh gọi
thêm là xứng đáng.

## Bằng chứng

### 1. Bước 1 đã tồn tại và đã được đo

`preprocessing/variants.py::Grid.cleaned()` đã bỏ citation `[1]`, cột rỗng, cột chỉ chứa
ảnh/link, và dòng body rỗng. D09 đo riêng lớp làm sạch này: **−1,5 EM, KTC 95% [−5,5; +2,5]**.
Không có gì mới để lấy ở bước 1.

### 2. Bản header-only không chọn được dòng

Thống kê 329 bảng (`Grid.from_table_data`):

| Đặc điểm | Số bảng | Tỷ lệ |
|---|---|---|
| Chỉ có header ở các dòng trên cùng | 256 | 77,8% |
| Có ô header nằm trong dòng body (header cột trái) | 73 | 22,2% |
| Header nhiều dòng (`n_head > 1`) | 69 | 21,0% |

Với 77,8% bảng, bản header-only chỉ còn lại tên cột: LLM không có thông tin nào để chọn **dòng**.
Bước 4 khi đó giữ lại toàn bộ dòng, và toàn bộ ý tưởng suy biến thành lọc cột. Chỉ với 22,2%
bảng có header cột trái thì cột 0 mới đóng vai trò khóa dòng — và ngay cả khi đó, mỗi dòng chỉ
còn một chuỗi tên, tức là bài toán retrieval theo tên thực thể, thứ mà BM25 trong
`preprocessing/reduction.py` đã làm không tốn lệnh gọi.

### 3. Trục dòng không có headroom; trục cột có một chút

EM đo lại trên `outputs/v3lite/control_fixed.jsonl`, **chỉ lấy candidate đầu** (best-of-K là
oracle, không phải độ chính xác hệ thống). Toàn tập: **66,4 EM**, khớp với `poma_first` 66,63
trong D01.

| Số cột | n | EM (SE) | | Số dòng | n | EM (SE) |
|---|---|---|---|---|---|---|
| ≤ 4 | 67 | 76,1 (5,2) | | ≤ 15 | 406 | 65,5 (2,4) |
| 5–7 | 696 | 65,5 (1,8) | | 16–40 | 403 | 67,7 (2,3) |
| 8–11 | 116 | 70,7 (4,2) | | 41–80 | 98 | 61,2 (4,9) |
| ≥ 12 | 113 | 61,9 (4,6) | | > 80 | 85 | **70,6** (4,9) |

Trục dòng **không đơn điệu và không có xu hướng**: nhóm bảng dài nhất (> 80 dòng) lại có EM cao
nhất. Đây là bằng chứng độc lập cho kết luận D10/D11 — cắt dòng không mua được độ chính xác.

Trục cột có một hố ở nhóm ≥ 12 cột (61,9 so với 66,4 toàn tập), nhưng **cũng không đơn điệu**
(nhóm 8–11 cột đạt 70,7, cao hơn nhóm 5–7 cột). Non-monotonic là dấu hiệu chiều rộng không phải
nguyên nhân nhân quả. Nếu vẫn lấy hố này làm mục tiêu: 113 câu nâng từ 61,9 lên mức toàn tập
66,4 cho **+0,51 điểm EM**; nâng lên 70 cho **+0,92 điểm**. Cả hai đều dưới độ lệch 1,7 điểm mà
D11 quan sát được khi chạy lại đúng cấu hình control.

Giả thuyết "nhóm ≥ 12 cột toàn câu cần nhiều cột" **bị bác bỏ**: tỷ lệ câu mang hint tính
toán / kết hợp ô / liệt kê là 40,7% trong nhóm ≥ 12 cột và 40,9% trên toàn tập — cùng một hỗn
hợp. Hố EM đó không giải thích được bằng loại câu hỏi.

### 4. Hàm mất mát bất đối xứng ở mức 8,6% prompt

Trong chính artifact trên, bảng chiếm **trung vị 8,6%** tổng prompt token (trung bình 10,9%, tối
đa 56,2%) — ví dụ một bảng 776 ký tự trong prompt 4.519 token. Nghĩa là:

- Bỏ nhầm một cột cần thiết: mất câu trả lời, **không cứu lại được**.
- Giữ thừa một cột: tốn vài phần trăm của 8,6%, gần như **miễn phí**.

Độ "mạnh tay" tối ưu của bộ lọc vì thế bị đẩy về gần 0. Lập luận này đến từ hình dạng của hàm
mất mát, không phụ thuộc vào con số EM nào ở trên. Thêm vào đó, 40,9% câu test cần suy luận đa
cột (tính toán, đa điều kiện, liệt kê), nên bộ lọc phải giữ nhiều cột cho gần một nửa số câu.

Trần lý thuyết của tiết kiệm token, đo bằng **bộ lọc cột oracle** (chỉ giữ cột chứa đáp án +
cột 0), trên 419 câu có đáp án nằm nguyên văn trong một ô: giảm **trung vị 78,1%** ký tự bảng.
Nhưng vì bảng chỉ là 8,6% prompt, mức đó quy ra chưa tới 7% prompt token, và đó là oracle chỉ
giữ đúng cột đáp án — chưa tính các cột điều kiện.

### 5. Đây là lần thứ bảy của cùng một khuôn mẫu

`direction-progress.md` đã ghi: "headroom đo được luôn lớn, phần lấy được luôn gần 0", vì cơ chế
can thiệp không phân biệt được trường hợp nên sửa với trường hợp không nên sửa. Bộ lọc header có
đúng hình dạng đó: nó không biết khi nào mình đang bỏ cột vô hại và khi nào đang bỏ cột chứa đáp
án. Cổng answerability của D11 thêm 16% lệnh gọi để đổi lấy +0,1 EM; một lệnh gọi lọc cho mỗi câu
là chi phí cùng bậc.

## Nếu vẫn làm: thiết kế nên sửa gì

1. **Gọi đúng tên: bộ lọc cột (column pruning), không phải lọc header.** Bỏ hẳn kỳ vọng chọn dòng
   từ bản header-only; nếu cần chọn dòng thì dùng BM25 sẵn có ở `reduction.py`.
2. **Đừng gửi ma trận đã bị xóa giá trị.** Nó vẫn tốn một dòng `|||||` cho mỗi hàng và thêm nhiễu.
   Gửi **danh sách lược đồ**: `Grid._split()` trong `variants.py` đã dựng sẵn một khóa cho mỗi cột
   (header nhiều tầng nối thành `Cha / Con`), cộng thêm giá trị cột 0 cho 22,2% bảng có header cột
   trái. Cùng thông tin, ít token hơn nhiều lần. Kèm 1–2 giá trị mẫu mỗi cột thì LLM chọn tốt hơn
   hẳn so với chỉ có tên cột (tên cột tiếng Việt thường viết tắt hoặc mơ hồ).
3. **Chốt luật an toàn trước khi chạy**, giống `AGGREGATION_CUES`: luôn giữ cột 0 và các cột header
   cột trái; luôn giữ toàn bộ cột khi bảng ≤ 8 cột (chiếm ~77% bảng, không đáng lọc); không lọc khi
   hint là tính toán / đa điều kiện / liệt kê trừ khi LLM chọn ≥ 3 cột.
4. **Đo recall trước, đo EM sau.** Chỉ số quyết định là: đáp án vàng và các cột điều kiện có còn
   trong bảng compact không. Nếu recall < ~98% thì dừng, không cần chạy EM.
5. **Baseline bắt buộc: chọn cột bằng BM25, không gọi LLM.** Nếu bộ lọc LLM không thắng baseline
   miễn phí này, lệnh gọi thêm không xứng đáng.
6. **Chốt trên dev, không chốt trên test**, và đo sàn nhiễu trước (chạy lại cùng cấu hình 3 lần)
   — vì mọi hiệu ứng kỳ vọng ở đây nhỏ hơn 1,7 điểm.

## Thí nghiệm

### Thiết kế

200 câu test (`outputs/d13/qas_d13_200.json`, seed 42). Mỗi bảng đạt một trong ba tiêu chí cấu
trúc và có mặt trong test đóng góp đúng một câu (**76 bảng**); 124 câu còn lại lấp theo phân phối
hint của full test. Tổng cộng 99/200 câu nằm trên bảng cấu trúc khó.

Tiêu chí tính trên lưới HTML gốc (trước khi parser kéo hàng header lên đầu): `clusters` = số thành
phần liên thông 4 hướng của ô `<th>`; `mid_header` = có hàng đa số `<th>` xuất hiện sau một hàng
body; `merged` = số ô có `rowspan`/`colspan` > 1. Số ô gộp tái lập **chính xác** bảng của tác giả
(73 bảng có ≥ 5, 183 bảng có ≥ 1); hai tiêu chí còn lại cho 17 và 14 thay vì 12 và 10, nên tập dùng
ở đây là **tập bao** của tập tác giả. 8 bảng đạt tiêu chí nhưng không có câu hỏi nào trong test:
`0_2, 25_3, 25_4, 48_2, 4_4, 58_2, 59_2, 8_1`.

Ba nhánh, cùng model `openrouter/qwen/qwen3-8b`, cùng prompt zero-shot `v4_zs_minimal_json_vi`,
cùng schema và `GenConfig` như D09 (temperature 0, top_p 1, max_tokens 10000). Chỉ chuỗi bảng khác
nhau. Control chạy mới trong cùng phiên, không ghép từ artifact cũ.

| Nhánh | Bảng đưa cho solver |
|---|---|
| `v1_raw` | Flatten V1 nguyên (control) |
| `v1_clean` | Flatten V1 sau `Grid.cleaned` (tách riêng lớp làm sạch) |
| `hdrfilter` | Bảng compact từ header do LLM chọn (thêm một lệnh gọi lọc) |

**Sửa prompt một lần trước khi chạy chính thức.** Prompt lọc đầu tiên chỉ yêu cầu chọn cột chứa
dữ liệu cần đọc/so sánh/tính toán. Trên smoke test 3 câu, LLM chọn đúng cột đáp án nhưng bỏ cột
chứa tên thực thể nên solver không dò được hàng (0/3 đúng, control 3/3). Prompt được sửa để bắt
buộc chọn thêm cột dùng xác định hàng, rồi mới chạy 200 câu. Ba câu smoke đó **nằm trong** subset
200, nên đây là một lần điều chỉnh không tiền đăng ký — nhưng nó đẩy kết quả về phía **có lợi** cho
ý tưởng, vì prompt chưa sửa còn tệ hơn.

17/600 lệnh gọi solver trả `{"final_answer": null}`, bị schema chuỗi từ chối (8 `hdrfilter`,
5 `v1_raw`, 4 `v1_clean`). Chúng được chấm là đáp án `Null` theo **cùng một luật trên cả ba nhánh**.

### Kết quả

| Nhánh | EM | F1 | Hiệu so với control (KTC 95%) | Thắng/Thua/Hòa | Token tổng | Chi phí |
|---|---|---|---|---|---|---|
| `v1_raw` | **65,5** | 80,15 | — | — | 419.914 | $0,0921 |
| `v1_clean` | **67,5** | 82,25 | +2,0 [−2,5; +6,5] | 12 / 8 / 180 | 424.162 | $0,0936 |
| `hdrfilter` | **51,0** | 66,63 | **−14,5 [−21,0; −8,0]** | 9 / 38 / 153 | 738.451 | $0,2534 |

Lớp làm sạch một mình vẫn không có ý nghĩa thống kê, đúng như D09. Bộ lọc header làm **mất 14,5
điểm EM** với khoảng tin cậy không chứa 0.

### Bộ lọc đã làm gì

| Chỉ số | Giá trị |
|---|---|
| Tỷ lệ cột giữ lại (trung bình) | 39,8% (trung vị 40,0%) |
| Tỷ lệ hàng giữ lại (trung bình) | 92,6% |
| Số câu LLM thực sự chọn được hàng | **21/200** |
| Fallback `all_rows` (không chọn được hàng nào) | **179/200** |
| Không chọn gì / mã không hợp lệ | 2 / 2 |
| Ô chứa đáp án vàng bị loại | 16 câu |
| EM trên 16 câu đó | 12,5 (control 56,25) |
| EM trên 21 câu có chọn hàng | 28,6 (control 52,4) |

**Dự đoán "bản header-only không chọn được dòng" được xác nhận:** 179/200 câu rơi vào fallback
`all_rows`. Trong 21 câu bộ lọc thực sự cắt hàng, EM là 28,6 so với 52,4 của control; n = 21 nên
sai số chuẩn khoảng 10 điểm — đây là **gợi ý mạnh** rằng cắt hàng gây hại, chưa phải một phép đo
chắc chắn.

### Cơ chế gây hại: mất cột điều kiện, không phải mất cột đáp án

Trong 38 câu thua, chỉ **7** câu do loại nhầm ô chứa đáp án. Để giải thích phần còn lại, đo thêm
**cột điều kiện**: cột chứa một ô body có nội dung xuất hiện nguyên văn trong câu hỏi (cùng luật
khớp cụm mà `preprocessing/reduction.py` dùng để nhận diện hàng được nêu tên).

| Nhóm | n | Không tìm được ô điều kiện | Giữ đủ mọi cột điều kiện | **Mất ít nhất một cột điều kiện** | Tỷ lệ cột điều kiện giữ lại |
|---|---|---|---|---|---|
| Thắng | 9 | 2 | 6 | 1 | 85,7% |
| **Thua** | 38 | 6 | 15 | **17** | **54,7%** |
| Hòa | 153 | 37 | 92 | 24 | 86,5% |

Trong 14 câu thua mà ô đáp án vẫn còn trong bảng compact, **9 câu mất cột điều kiện**, 3 câu giữ
đủ, 2 câu không tìm được ô điều kiện. Vậy cơ chế gây hại chính **không phải** loại nhầm cột đáp án
mà là **loại mất cột dùng để định vị hàng**: mô hình vẫn nhìn thấy cột chứa câu trả lời nhưng không
còn cách nào biết hàng nào là hàng đúng. Đây chính là hàm mất mát bất đối xứng nêu ở mục 4: bộ lọc
giữ 39,8% số cột, và phần bị bỏ mang thông tin định vị.

### Token: tiết kiệm ở solver, mất nhiều hơn ở bộ lọc

| Khoản | `hdrfilter` | `v1_raw` |
|---|---|---|
| Prompt token của solver | 138.012 (**−52,8%**) | 292.699 |
| Prompt token của lệnh gọi lọc | 106.317 | 0 |
| Completion token | 494.122 | 127.215 |
| **Tổng** | **738.451 (+75,9%)** | 419.914 |
| Chi phí | $0,2534 (**×2,75**) | $0,0921 |

Bảng compact đúng là cắt hơn một nửa prompt của solver. Nhưng lệnh gọi lọc sinh trung bình **1.807
completion token** mỗi câu (Qwen3 suy nghĩ trước khi trả JSON), gấp gần ba lần completion của chính
solver. Tiết kiệm ở tầng dưới bị nuốt nhiều lần bởi tầng trên.

Lưu ý khi đọc con số −52,8%: solver ở đây dùng prompt zero-shot tối giản, nên bảng chiếm phần lớn
prompt. Trong POMA nhiều tầng, bảng chỉ chiếm trung vị 8,6% prompt (mục 4 ở trên), nên phần tiết
kiệm triển khai thực tế sẽ nhỏ hơn nhiều, còn chi phí lệnh gọi lọc thì giữ nguyên.

### Chia theo loại bảng

| Nhóm | n | `v1_raw` | `v1_clean` | `hdrfilter` |
|---|---|---|---|---|
| Bảng đạt tiêu chí cấu trúc | 99 | 66,67 | 64,65 | 48,48 |
| Bảng còn lại | 101 | 64,36 | 70,30 | 53,47 |

Bộ lọc không cứu được nhóm bảng cấu trúc khó; nó mất nhiều điểm hơn ở chính nhóm đó (−18,2 so với
−10,9).

### Kết luận của thí nghiệm

Loại bỏ `hdrfilter` ở dạng này. Đây là direction đầu tiên trong dự án có khoảng tin cậy không chứa
0, và nó nằm ở phía có hại. Nếu muốn tiếp tục trục cột, ba điều kiện phải đổi: (1) gửi danh sách
lược đồ kèm giá trị mẫu thay vì ma trận bị xóa trắng, (2) bắt buộc giữ cột khóa và chỉ lọc khi bảng
đủ rộng, (3) tắt suy nghĩ của mô hình ở lệnh gọi lọc, vì 1.807 completion token mỗi câu đã tự xóa
hết phần tiết kiệm. Baseline miễn phí cần vượt qua vẫn là chọn cột bằng BM25, chưa chạy.

## Tái lập

Phần phân tích trước thí nghiệm tính từ `dataset/table.json`, `dataset/qas_test.json` và
`outputs/v3lite/control_fixed.jsonl` bằng `preprocessing.variants.Grid` và
`evaluation.normalization.exact_text_match`, chấm chỉ candidate đầu tiên.

Thí nghiệm: `scripts/build_d13_subset.py` (subset và manifest), `scripts/run_d13_header_filter.py`
(ba nhánh, JSONL nối tiếp được), `scripts/analyze_d13.py` (EM/F1, bootstrap ghép cặp 10.000 mẫu,
chẩn đoán bộ lọc), `scripts/analyze_d13_conditions.py` (cột điều kiện). Cơ chế lọc ở `preprocessing/header_filter.py`, schema `header_filter.v1` ở
`src/contracts/structured_outputs.py`. Artifact: `outputs/d13/records.jsonl`, `outputs/d13/report.json`,
`outputs/table_structure_stats.json`.

Giới hạn: một phiên chạy duy nhất, 200 câu, một model, solver zero-shot một lệnh gọi. Hiệu −14,5
điểm lớn hơn nhiều lần độ lệch giữa các phiên đã quan sát (1,7 điểm), nên kết luận không phụ thuộc
vào sàn nhiễu; nhưng các con số tuyệt đối thì có.
