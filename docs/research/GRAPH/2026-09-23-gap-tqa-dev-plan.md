# GaP-TQA trên dev: arm và luật quyết định (chốt trước khi gọi API)

Ngày: 2026-09-23. Code: [`gap_tqa/`](../../../gap_tqa/). Hệ tách khỏi POMA: không dùng agent,
orchestration, prompt, GSA hay Hint Predictor của POMA. Chỉ tái dùng hạ tầng chung: parser HTML,
`preprocessing/variants`, `LLMClient`, scorer.

## Thiết lập

- Split: **dev, 991 câu**. Test không chạm cho đến khi chốt hệ.
- Model: `openrouter/qwen/qwen3-8b` (provider Alibaba), `temperature=0`, thinking theo mặc định của provider.
- Reader: prompt riêng, yêu cầu đáp ngắn và chép nguyên văn từ bảng; 2 cặp ví dụ (hỏi, đáp)
  cho mỗi lớp, lấy từ train (seed 7), không kèm bảng.
- Router: luật viết từ câu hỏi train. So với hint gold: 84,1% trên train. Trong các câu router gán
  `lookup` (tra cứu), 4,8% thuộc lớp khác theo nhãn gold.
- Luật phát ô `EMIT_MAX_WORDS = 4` lấy từ train: câu tra cứu có ô gold ≤ 4 từ thì gold là
  nguyên ô ở 84–96% trường hợp.
- Chấm: EM một đáp án bằng scorer của repo (`single-required`, như `--strict`). Bootstrap ghép cặp
  10.000 mẫu so với A1; báo thắng/thua, EM theo lớp gold và theo `table_type`, số lệnh gọi và token.

## Arm (mỗi arm đổi đúng một thứ)

| Arm | Graph |
|---|---|
| A0 | `read_full(v1_raw)` |
| A1 | A0 → `verbalize`. **Đối chứng chính** |
| A2a | như A1, bảng dạng `pipe_nohdr` |
| A2b | như A1, bảng dạng `markdown_kv_clean` |
| A3 | chuỗi hành động người: `read_anchor` (chỉ các hàng neo tìm bằng khớp chữ) → nếu `Null` thì `read_full` → `verbalize` |
| A4 | lớp `lookup`: `locate` (grid, xuất ID ô) → `emit_cell` (ô ≤ 4 từ thì phát nguyên văn; ô dài thì đọc riêng hàng đó; ID hỏng hoặc trùng ô trong câu hỏi thì bỏ qua) → `read_full` nếu chưa có đáp án → `verbalize`. Lớp khác: như A1. Chạy hai bản: route bằng luật (`A4_rule`) và bằng hint gold (`A4_gold`, oracle) |

## Luật quyết định

- **Biểu diễn:** thay `v1_raw` chỉ khi A2x − A1 có cận dưới KTC > 0. Nếu không, và hai arm tương
  đương, chọn arm rẻ hơn.
- **Tổ chức theo chuỗi người (A3):** coi là "thắng" nếu cận dưới KTC > 0. Coi là "tương đương, rẻ
  hơn" nếu KTC nằm trong [−2,5; +2,5] và token ít hơn.
- **GaP-TQA (A4_rule):** chỉ làm tiếp vòng tự học (G3) nếu A4_rule − A1 có cận dưới KTC > 0,
  hoặc điểm ước lượng ≥ +1,5 đi kèm tăng rõ ở lớp `lookup`. `A4_gold − A4_rule` đo phần mất do
  router.
- Chỉnh gì sau khi thấy số dev thì phải chia đôi dev để xác nhận trên nửa còn lại.

## Lưu ý đã biết trước

- Luật Verbalize có dạng được nghĩ ra sau khi xem lỗi trên test (tài liệu 2026-09-22 mục 1.3);
  bảng từ vựng lấy từ train.
- D09/D12 đã quét 8 cách biểu diễn cho reader; A2 chỉ giữ 2 cách tốt nhất ở đó.
- Ngân sách ước khoảng $3.

## Kết quả (dev 991 câu, so ghép cặp với A1)

| Arm | EM | vs A1 (KTC 95%) | Thắng/thua | Lệnh gọi/câu | Prompt token |
|---|---:|---|---:|---:|---:|
| A0 | 69,12 | −1,21 [−2,12; −0,30] | 4/16 | 1,00 | 1,98M |
| A1 | 70,33 | — | — | 1,00 | 1,98M |
| A2a `pipe_nohdr` | 71,95 | +1,61 [−0,30; +3,53] | 54/38 | 1,00 | 1,89M |
| A2b `markdown_kv_clean` | 71,14 | +0,81 [−1,31; +2,93] | 63/55 | 1,00 | 3,31M |
| A3 chuỗi hàng neo, mọi lớp | 70,03 | −0,30 [−2,22; +1,61] | 45/48 | 1,11 | 1,06M |
| A4_rule Locate + phát ô | 68,82 | −1,51 [−3,03; 0,00] | 21/36 | 1,19 | 2,13M |
| A4_gold | 66,30 | −4,04 [−5,95; −2,22] | 24/64 | 1,21 | 2,15M |
| A5_rule (chọn sau khi xem dev) | 73,26 | +2,93 [+0,91; +4,94] | 66/37 | 1,03 | 1,46M |
| A5_gold | 72,96 | +2,62 [+0,61; +4,64] | 67/41 | 1,04 | 1,36M |

Đọc theo luật quyết định:

- **Verbalize** có ý nghĩa thống kê trên dev (A1 − A0). Lớp Yes/No tăng từ 74,4 lên 81,7.
- **Biểu diễn:** không nhánh nào có cận dưới > 0. `pipe_nohdr` cho EM cao nhất và rẻ hơn một chút,
  nên chọn nó theo luật "tương đương thì chọn rẻ hơn".
- **A3** đạt tiêu chí "tương đương, rẻ hơn" (53% token), nhưng hiệu ứng đi ngược nhau theo lớp:
  tra cứu 69,8 → 73,3; liệt kê 78 → 56; tính toán 66,5 → 63,5.
- **A4 không đạt cổng: dừng hướng Locate theo ID + phát nguyên văn.** Ở nhánh phát ô, EM chỉ 68,7
  so với 76,0 của reader trên cùng câu. Nguyên nhân: ô chứa nhiều hơn phần được hỏi
  ("20.1.1981" khi hỏi năm), chọn nhầm cột số, HTML của ô chứa khoá sắp xếp ẩn, và câu có nhiều đáp án.
- **A5** = `pipe_nohdr` + chuỗi hàng neo **chỉ cho lớp `lookup`** + Verbalize. Arm này được chọn
  **sau khi xem dev**, trong khoảng 9 biến thể. Vì vậy mức +2,93 so với A1 là ước lượng lạc quan,
  **không phải hiệu ứng của hệ**.
- **Kiểm tra lại A5 trên 1.000 câu train ngẫu nhiên** (seed 23, bỏ các câu làm ví dụ):
  A5 − A2a = +1,10 [0,00; +2,20], 21 thắng / 10 thua, token −24%. Cận dưới bằng 0, nên theo luật
  đã chốt A5 chỉ là **"tương đương, rẻ hơn"** so với A2a, chưa phải thắng.
  - Bước kiểm tra này **lệch khỏi kế hoạch**: kế hoạch ghi là xác nhận trên nửa dev còn lại,
    nhưng mọi câu dev đã được xem khi chọn A5, nên tôi dùng train.
  - Router được viết từ chính train, nên mẫu này chưa hoàn toàn sạch đối với bước route của A5.
  - A5_gold ≈ A5_rule, tức router không phải điểm nghẽn.

Tóm tắt bằng chứng theo từng thành phần:
- **Verbalize:** đã chốt trước, có ý nghĩa thống kê trên dev.
- **Chuỗi hàng neo chỉ cho `lookup`:** tương đương và rẻ hơn trên câu train mới, xu hướng dương.
- **`pipe_nohdr`:** không có ý nghĩa thống kê, chọn chỉ vì rẻ hơn.
- **Locate + phát ô:** bị cổng đã chốt trước chặn lại.

Chưa có baseline POMA nào chạy trên dev, nên chưa so được GaP-TQA với POMA. Không đặt 73,26 (dev)
cạnh 73,29 của FS+GSA+Verbalize (test).

Ghi chú tái lập: phiên bản đầu của cache có lỗi race. `_load_cache` gán dict rỗng trước khi đọc
xong file, nên luồng khác thấy cache mới nạp một nửa và gọi lại API. Hậu quả là 12 khoá trùng, và
A1 ra 70,23 ở một tiến trình nhưng 70,33 ở tiến trình khác. Đã sửa: nạp dưới lock, bản ghi đầu
tiên thắng. Các báo cáo trên đã dựng lại từ cache sau khi sửa và không phát sinh lời gọi API mới.

Lệnh: `python -m gap_tqa.run --split dev --arms A0 A1 A2a A2b A3 A4 A5 --routers rule gold`;
xác nhận: `python -m gap_tqa.run --split train --sample 1000 --arms A2a A5 --routers rule --baseline A2a`.
Kết quả ở `outputs/gap_tqa/dev/report.json` và `outputs/gap_tqa/train_sample1000/report.json`.

## So với zero-shot và few-shot của repo (dev 991 câu)

Hai baseline được chạy lại trên dev bằng `run_baseline.py --prompt-style zero_shot|few_shot`, cùng
giao thức cũ: Flatten V1, `openrouter/qwen/qwen3-8b`, provider Alibaba. Hệ gốc để so ghép cặp là
FS + Verbalize (`+v` = áp Verbalize tất định lên đáp án đã lưu). So bằng
`scripts/compare_dev_arms.py`.

| Hệ | EM | vs FS+v (KTC 95%) | Thắng/thua | Yes/No | Tra cứu | Prompt token |
|---|---:|---|---:|---:|---:|---:|
| Zero-shot | 62,66 | −9,18 [−12,11; −6,26] | 67/158 | 47,0 | 69,8 | 1,65M |
| Zero-shot + v | 63,27 | −8,58 [−11,50; −5,75] | 67/152 | 50,6 | 69,8 | 1,65M |
| Few-shot | 68,31 | −3,53 [−4,84; −2,32] | 3/38 | 58,5 | 72,9 | 2,40M |
| **Few-shot + v** | **71,85** | — | — | — | — | 2,40M |
| GaP A1 | 70,33 | −1,51 [−3,83; +0,81] | 60/75 | 81,7 | 69,8 | 1,98M |
| GaP A2a | 71,95 | +0,10 [−2,12; +2,32] | 64/63 | 81,7 | 72,5 | 1,89M |
| GaP A5 | 73,26 | +1,41 [−0,71; +3,53] | 69/55 | 81,7 | 75,5 | 1,46M |

- **Hơn rõ zero-shot**; so với few-shot bản gốc thì hơn nhờ Verbalize.
- **So với few-shot + Verbalize, GaP-TQA chưa hơn có ý nghĩa.** A5 cao hơn 1,41 điểm nhưng khoảng
  tin cậy chứa 0. A5 lại là arm được chọn sau khi xem dev, nên con số này còn lạc quan.
- **Lợi thế chắc chắn hiện có là chi phí:** A5 dùng 61% prompt token của few-shot.
- Đối chứng mạnh cần vượt từ nay là **FS + Verbalize**, không phải zero-shot. FS+GSA của POMA vẫn
  chưa chạy trên dev.
