# MemXam: multi-agent có đối chất cho Table QA tiếng Việt trên Qwen3-8B tự host

Ngày: 2026-09-26. Tài liệu này nối tiếp
[`2026-09-26-multi-agent-tqa-de-xuat.md`](2026-09-26-multi-agent-tqa-de-xuat.md) (khảo sát
multi-agent cho Table QA) và [`enhance_poma/direction-progress.md`](enhance_poma/direction-progress.md)
(D01–D13). Phương pháp của bài báo là **một** hệ multi-agent (MemXam); mọi hệ khác ở đây là
baseline.

> **Trạng thái:** đang chạy. Các mục có dấu ⏳ sẽ được điền khi đủ 3 lần chạy trên dev và lần
> chạy test duy nhất.

## Tóm tắt

⏳

## 1. Hạ tầng: Qwen3-8B tự host

- Backbone: `Qwen/Qwen3-8B`, bf16 (không lượng tử hoá), vLLM `vllm/vllm-openai:latest`,
  `--max-model-len 32768 --gpu-memory-utilization 0.90 --max-num-seqs 10`, một RTX 3090 24 GB
  thuê trên Vast.ai (host Taiwan). Host đầu tiên (Trung Quốc) treo khi pull image từ Docker Hub
  nên đã bị huỷ.
- Mọi lệnh gọi dùng `temperature=0` (trừ các mẫu self-consistency/phiếu thứ ba: `0.7`,
  `top_p=0.95`), thinking bật (Qwen3 mặc định), `max_tokens=6000`. Khối `<think>` bị bỏ trước khi
  parse JSON; thinking bị cắt (không có `</think>`) được coi là không có đáp án.
- Thông lượng đo được: ~200 token sinh/s và ~700–800 token prompt/s cho toàn server. KV cache chỉ
  ~5 GB (~34k token), nên chỉ ~7–8 chuỗi thinking chạy song song. Vì vậy thí nghiệm dùng subset
  200 câu dev (chọn phương pháp, 3 lần chạy) và subset 200 câu test (xác nhận, 1 lần).
- Mọi baseline được **chạy lại trong cùng phiên trên cùng endpoint**; không so với artifact
  OpenRouter cũ.
- Mã: `mas_tqa/` (client, dữ liệu, prompt, phương pháp), `scripts/run_mas_tqa.py`,
  `scripts/score_mas_tqa.py`, `scripts/bif_mas_tqa.py`, `scripts/analyze_memxam.py`; kiểm thử
  `tests/mas_tqa/`. Endpoint mặc định của pipeline POMA cũng đổi được qua
  `POMA_OPENROUTER_API_BASE`.

## 2. Hai quan sát định hình thiết kế

### 2.1 Mọi bảng dev/test đều có câu hỏi train

296/296 bảng dev và 289/289 bảng test xuất hiện trong train (split theo câu hỏi, không theo
bảng); trung vị 29 câu train mỗi bảng dev. Đây là một bộ nhớ hợp lệ về **cách viết đáp án của
chính bảng đó**. Rò rỉ trực tiếp nhỏ: 47/991 câu dev có câu train cùng bảng với Jaccard token
≥ 0,8, trong đó 16 câu cùng đáp án (1,6%). Mọi bảng kết quả báo thêm EM khi bỏ các câu "sinh
đôi" này (cột `EM-twin`).

### 2.2 Trần BIF

Chấm chính đáp án gold làm dự đoán cho kết quả EM 100% nhưng **BIF chỉ 87,48 (dev) và 88,97
(test)**. Lý do: ViNLI cho P(entailment) rất thấp khi premise và hypothesis đều là một số hay một
năm trơ trọi (vd. `2003`→`2003`: 0,03). Xấp xỉ tuyến tính trên các lần chạy (câu đúng ≈ 0,87, câu
sai ≈ 0,52) cho thấy **BIF ≥ 80 tương đương EM khoảng 76–79**. Các con số BIF dưới đây cần đọc
cùng trần này.

## 3. MemXam

| Vai | Hiện thực | Loại |
|---|---|---|
| **Memory** | k = 8 cặp (câu hỏi → đáp án gold) train trên chính bảng đó, gần câu hỏi nhất theo Jaccard token | tất định |
| **Solver A** | Flatten V1 + memory, thinking, xuất `final_answer` (= baseline kNN-FS) | LLM |
| **Solver B** | Bảng dạng lưới (`pipe_path_clean`) + memory, thinking, xuất `evidence` (ô bảng) trước rồi `final_answer` | LLM, khác họ prompt và cách nhìn bảng |
| **Kiểm tra** | Loại đáp án rỗng/không parse được, và đáp án không phải Có/Không cho câu Có/Không (router GaP-TQA: precision 98,8%, recall 99,5% trên train) | tất định |
| **Đối chất** | Khi A, B hợp lệ và khác nhau: mỗi solver thấy đáp án + ô bằng chứng của bên kia, giữ hoặc đổi, **một vòng** | LLM, tương tác |
| **Judge** | Nếu vẫn bất đồng: chọn một trong hai đáp án (không được viết đáp án mới) | LLM |

Mọi vai của cùng một solver dùng chung tiền tố prompt `[hướng dẫn + bảng + memory]`, chỉ khác
phần đuôi, để vLLM tái dùng prefix cache.

Theo định nghĩa của tài liệu 2026-09-26 (§1), MemXam là **multi-agent**: hai solver đọc và phản
hồi output của nhau. Các ablation bên dưới cô lập đúng phần đóng góp của tương tác.

## 4. Baseline và ablation (cùng tầng đầu)

Trong mỗi lần chạy, A và B được gọi một lần và dùng chung cho mọi nhánh dưới đây, nên các so sánh
MemXam–ablation là ghép cặp trên cùng đáp án tầng đầu.

| Nhánh | Mô tả | Vai trò |
|---|---|---|
| FS | Prompt few-shot gốc `v3_fs_structured_vi` (4 ví dụ tự dựng), thinking | **baseline chính** |
| kNN-FS | Solver A một mình | cô lập đóng góp của memory |
| B (evid) | Solver B một mình | baseline một lệnh gọi mạnh nhất |
| cascade3 | Như MemXam đến bước kiểm tra; bất đồng thì thêm một phiếu họ A (T = 0,7), đa số | vote không tương tác |
| cascade3b | Như trên, phiếu thứ ba họ B | vote không tương tác |
| judge-only | Bất đồng thì judge chọn thẳng giữa A và B | bỏ đối chất |
| kNN-SC3 | 3 mẫu kNN-FS (T = 0,7), đa số | self-consistency cùng ngân sách |

## 5. Kết quả

### 5.1 Dev 200 câu, bản v2 (chưa có bước kiểm tra), 1 lần chạy

| Nhánh | EM | BIF |
|---|---:|---:|
| FS | 75,0 | 74,41 |
| kNN-FS | 77,0 | 76,46 |
| B (evid) | 79,0 | 78,55 |
| cascade3 | 80,0 | 78,51 |
| MemXam v2 | 81,0 | 79,41 |

MemXam v2 − FS: +6,0 EM [+2,0; +10,1]. Trên 36 câu bất đồng, đối chất sửa 11 và phá 3 so với chỉ
dùng A; nhánh judge đúng 2/10. Đọc từng câu bất đồng cho ra ba lỗi hệ thống: (1) đáp án rỗng do
parse lỗi được coi là một ứng viên và có lúc được judge chọn; (2) đáp án sai loại cho câu Có/Không
kéo solver đúng đổi theo; (3) đối chất đôi khi làm đáp án dài hơn (`Tài chính` → `Bộ Tài chính`).
Bản v3 thêm vai **Kiểm tra** để sửa (1) và (2), và một câu hướng dẫn giữ cách viết theo memory
cho (3). Đây là thay đổi sau khi xem dev, nên kết luận cuối dựa vào lần chạy test.

FS dao động giữa các lần chạy cùng cấu hình: 75,0 / 72,5 / 72,5 EM (BIF 74,41 / 73,23 / 73,54).
Ngay cả solver nhiệt độ 0 cũng không tất định: thinking dài phân nhánh theo batch của vLLM, nên
A và B ở hai lần chạy khác nhau cho kết quả lệch 2–4 điểm. Mọi so sánh giữa hai lần chạy phải
đọc với sai số này; so sánh **trong cùng một lần chạy** (MemXam với ablation, cùng A và B) thì
sạch hơn nhiều.

### 5.2 Từ v3 đến v4: judge là mắt xích yếu

v3 (thêm Kiểm tra) chạy được 118–120 câu trước khi thay bằng v4. Trên hai lần chạy v2 và v3,
nhánh judge đúng 2/10 và 0/6 câu, trong khi phiếu bầu với một phiếu thứ ba độc lập (cascade3) sửa
6/phá 0 và 5/phá 1. Judge không thiên vị vị trí (chọn [0] và [1] xấp xỉ nhau) mà đơn giản là chọn
kém; có một ca hai solver **đổi chéo** đáp án cho nhau sau đối chất. Tính lại offline từ trace
(phiếu C của cascade3 độc lập với đối chất nên dùng lại được), "đối chất rồi bỏ phiếu {A2, B2, C}"
đạt 81,0 (v2, 200 câu) và 78,81 (v3, 118 câu), bằng hoặc hơn cả đối chất + judge (81,0 / 76,27) lẫn
cascade3 (80,0 / 78,81). v4 lấy thiết kế này; judge giữ lại làm ablation `memxam_judge`.

### 5.3 Dev 200 câu, v4, lần chạy 1

| Nhánh | EM | BIF | Lệnh gọi/câu |
|---|---:|---:|---:|
| FS (TB 3 lần) | 73,33 | 73,73 | 1 |
| kNN-FS (A) | 77,50 | 76,48 | 1 |
| B (evid) | 79,00 | 78,22 | 1 |
| cascade3 | 80,50 | 78,51 | 2,12 |
| cascade3b | 80,50 | 78,43 | 2,12 |
| judge-only | 81,00 | 78,92 | 2,12 |
| **MemXam v4** | **80,00** | **78,67** | 2,29 |
| MemXam + judge | 79,00 | 78,21 | 2,29 |

Oracle {A, B} = 83,5. A và B đồng ý 165/200 câu (EM 87,9 trên nhóm này). Trên 35 câu bất đồng: chỉ
B đúng 12, chỉ A đúng 9, cả hai sai 13. MemXam sửa 9/phá 4 so với chỉ dùng A; cascade3 sửa 6/phá 0.

**Đọc kết quả:** mọi ensemble trên cùng A, B nằm trong khoảng 79–81, chênh nhau dưới mức phân
giải của 200 câu. Phần lớn khoảng cách với FS (+6 đến +7 EM, +5 BIF) đến từ **memory cùng bảng**
và **solver thứ hai khác họ prompt**; phần đóng góp riêng của tương tác (đối chất) **chưa tách
được** khỏi bỏ phiếu ở cùng số lệnh gọi. BIF dưới 80 vì trần BIF của subset dev này chỉ 87,5.

### 5.4 Nâng trần: memory lớn hơn và solver thứ ba ⏳

### 5.3 Test 200 câu, 1 lần chạy ⏳

## 6. Các ý đã thử và loại

- **Verifier agent chấm từng ứng viên** (thay cho bỏ phiếu) trên pool 5 lời giải độc lập đã lưu
  (3 mẫu kNN-SC3, B, A k=16). Trên 48 câu dev có bất đồng (101 ứng viên), verifier gần như chấp
  nhận mọi đáp án: recall 0,91, specificity 0,35, precision 0,41. EM: vote 83,0 → verifier 82,5
  (sửa 0, phá 1). Oracle của nhóm này 33/48, vote đúng 26/48. Kết quả âm có đo độ chính xác có
  điều kiện: model 8B tự kiểm định không phân biệt được đáp án đúng/sai trong đúng những câu khó.
- **Bỏ phiếu thuần** trên pool càng lớn thì bão hoà quanh 82–83 (SC3 82,4; SC3 + B + A16 + B16
  82,9), dù oracle toàn pool là 86,9.

- **Bắt đáp án về đúng ô bảng** (tất định): trên dự đoán FS và kNN-FS, 0 câu sửa, 7 câu phá; gold
  thường là phần con của ô (`207 m` so với ô `207 m (679 ft)`).
- **Tắt thinking**: FS rơi còn ~55 EM (n = 41); kNN-FS không thinking ~62–64.
- **Bộ chọn Có/Phải/Đúng/Sai học từ train**: 87,6% trên câu Có/Không dev, bằng đúng Verbalize
  hiện có; phần còn lại là nhiễu gán nhãn.
- **Solver B không thinking** (bản v1): yếu hơn A, và trong đối chất đã kéo A đúng sang đáp án
  sai; thay bằng B thinking.

## 7. Giới hạn

⏳
