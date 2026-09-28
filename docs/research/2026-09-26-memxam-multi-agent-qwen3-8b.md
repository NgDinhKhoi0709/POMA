# MemXam: multi-agent có đối chất cho Table QA tiếng Việt trên Qwen3-8B tự host

Ngày: 2026-09-26. Tài liệu này nối tiếp
[`2026-09-26-multi-agent-tqa-de-xuat.md`](2026-09-26-multi-agent-tqa-de-xuat.md) (khảo sát
multi-agent cho Table QA) và [`enhance_poma/direction-progress.md`](enhance_poma/direction-progress.md)
(D01–D13). Phương pháp của bài báo là **một** hệ multi-agent (MemXam); mọi hệ khác ở đây là
baseline.

> **Trạng thái:** đã xong vòng thực nghiệm trên Qwen3-8B tự host (GPU đã huỷ). Mỗi cấu hình mới
> chỉ chạy **một lần** theo yêu cầu (FS và kNN-SC3 trên dev có 3 lần); con số nào có 1 lần chạy
> thì đọc với sai số giữa các lần chạy ±1,5–2,5 EM (§5.1).

## Tóm tắt

1. **Mục tiêu EM ≥ 80 và BIF ≥ 80 đạt được, nhưng không chắc chắn qua mọi split.**
   - MemXam-SC-KV (v7), phương án tốt nhất **chọn trên dev**: dev 82,41 EM / 80,04 BIF; test
     **80,90 EM / 79,66 BIF** (BIF test hụt 0,34).
   - MemXam-SC (v6): test **82,50 EM / 80,52 BIF**, nhưng dev chỉ 80,00 / 79,44. Chọn v6 vì điểm
     test là chọn trên test, nên không dùng làm kết quả chính.
   - FS cùng phiên: test 71,50 / 73,14; dev trung bình 3 lần 73,33 / 73,73.
   - Khoảng cách với FS trên test: **+9,55 đến +11,00 EM, +6,5 đến +7,4 BIF**, KTC ghép cặp 95%
     không chứa 0.
2. **Nguồn lợi chính là memory cùng bảng, không phải tương tác.** Mọi bảng dev/test đều có câu hỏi
   train; thêm 8–16 cặp hỏi–đáp train cùng bảng vào prompt nâng FS từ ~73 lên ~78–80 EM. Cộng thêm
   nhiều mẫu hoặc nhiều view (self-consistency, vote) lên ~81–82.
3. **Đóng góp riêng của đối chất chưa tách được khỏi 0.** So với bỏ phiếu trên đúng các mẫu tầng
   đầu (ghép cặp trong cùng lần chạy): v6 −1,5 (dev) / +1,0 (test); v7 −0,5 (dev) / +1,0 (test).
   Self-consistency 3 mẫu là baseline rất mạnh và rẻ.
4. **Kết quả âm có đo:** judge LLM (đúng 2/10, 0/6), verifier chấm ứng viên (specificity 0,35),
   Parse-Critic (ghi chú parse làm 1 thắng/4 thua trên câu bị ảnh hưởng), Memory-Curator (−2 EM so
   với Jaccard), memory k = 30, bắt ô tất định.
5. **Trần BIF** (chấm chính gold làm dự đoán) là 86,52 trên subset dev 200 câu và 87,45 trên
   subset test 200 câu (toàn split: 87,48 / 88,97), vì ViNLI chấm thấp các đáp án số/năm ngắn;
   BIF ≥ 80 tương đương EM khoảng 80–83.

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
  200 câu dev (chọn phương pháp; FS và kNN-SC3 chạy 3 lần, các cấu hình mới 1 lần theo yêu cầu)
  và subset 200 câu test (xác nhận, 1 lần).
- Giai đoạn cuối chuyển sang một A100 SXM4 40 GB (Alberta, $0,638/giờ) với cùng image và tham số,
  chỉ nâng `--max-num-seqs` lên 64 (không ảnh hưởng đầu ra). Đo được ~5,8k token prompt/s và
  ~1,2k token sinh/s, tức gấp ~6–7 lần 3090 với giá gấp 2,9 lần (rẻ hơn ~2,3 lần theo token).
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

Chấm chính đáp án gold làm dự đoán cho kết quả EM 100% nhưng **BIF chỉ 87,48 (toàn split dev)
và 88,97 (toàn split test)**; trên đúng hai subset 200 câu dùng trong tài liệu này, trần là
**86,52 (dev) và 87,45 (test)**. Lý do: ViNLI cho P(entailment) rất thấp khi premise và hypothesis đều là một số hay một
năm trơ trọi (vd. `2003`→`2003`: 0,03). Xấp xỉ tuyến tính trên các lần chạy (câu đúng ≈ 0,87, câu
sai ≈ 0,52) ban đầu gợi ý BIF ≥ 80 ứng với EM ~76–79; số đo thực tế sau đó cho thấy cần EM
khoảng **80–83** (ví dụ dev 82,4 EM → 80,0 BIF; test 81,5 EM → 80,1–80,3 BIF). Các con số BIF dưới
đây cần đọc cùng trần này.

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

Bảng trên mô tả bản v3. Các phiên bản sau đó (lý do ở §5):

| Bản | Thay đổi so với bản trước |
|---|---|
| v4 | Không hội tụ sau đối chất → bỏ phiếu {A2, B2, C} với C là phiếu độc lập họ A, thay cho judge |
| v5 (MemXam-3) | Ba solver: Flatten V1, lưới + bằng chứng, **Markdown-KV**; không đồng thuận 3/3 → đối chất một vòng (mỗi solver thấy hai bên kia) → đa số |
| v6 (**MemXam-SC**) | Agent A = kNN k = 16 lấy **3 mẫu** trong một request (self-consistency trong agent), agent B = lưới + bằng chứng; đồng thuận ≥ 3/4 → dừng; tranh chấp → đối chất một vòng giữa lập trường mạnh nhất của mỗi họ → bỏ phiếu trên cả đáp án gốc và đáp án sau đối chất |
| v7 (**MemXam-SC-KV**) | Như v6 nhưng agent B nhìn bảng dạng Markdown-KV (solver đơn lẻ tốt nhất trên dev) |

Đối chứng không tương tác của v6/v7 là **vote 4 mẫu** trên đúng 3 mẫu A + 1 mẫu B của cùng lần
chạy, và **kNN16-SC3** (chỉ 3 mẫu A).

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

### 5.4 Nâng trần: memory lớn hơn, self-consistency, solver thứ ba

| Nhánh (dev 200, 1 lần chạy trừ khi ghi) | EM | BIF | Lệnh gọi/câu | Token prompt/câu | Token sinh/câu |
|---|---:|---:|---:|---:|---:|
| kNN-FS k = 16 | 80,00 | 77,69 | 1 | 2.416 | 802 |
| kNN-FS k = 30 | 78,00 | — | 1 | 2.765 | 809 |
| B với k = 16 | 76,88 | — | 1 | 2.168 | 862 |
| **kNN-SC3** (3 mẫu T = 0,7, 1 request), run 1 / run 2 | **82,00 / 81,50** | **79,39 / 79,44** | 1 | 2.123 | 2.250 |
| Solver Markdown-KV đơn lẻ (v5, 198 câu) | 81,31 | 80,29 | 1 | 2.996 | 705 |
| Vote 3 solver không tương tác (v5, 198 câu) | 79,29 | 78,95 | 3 | 6.873 | 2.288 |
| MemXam-3 (v5, 198 câu) | 80,30 | 79,68 | 3,59 | 9.407 | 2.991 |

Memory k = 16 giúp solver A (+2,5 EM so với k = 8) nhưng không giúp B; k = 30 kém hơn k = 16.
Self-consistency trên kNN-FS là baseline mạnh nhất và rẻ nhất trong nhóm mạnh (3 mẫu dùng chung
một lần prefill). MemXam-3 hơn vote 3 solver cùng tầng đầu +1,0 EM, nhưng chưa vượt SC3 và tốn
gấp 4,4 lần token prompt.

### 5.5 Parse-Critic: LLM tự nhận xét cách parse HTML

Agent nhận HTML gốc đã làm gọn (giữ rowspan/colspan) và chuỗi Flatten V1, liệt kê lỗi parse và
viết ghi chú cấu trúc (không viết lại nội dung ô); ghi chú chỉ được thêm vào prompt solver với
bảng bị đánh giá chưa trung thành. Chạy trên 64 bảng có ô gộp của subset dev. Trên những bảng đã
chạy, agent phát hiện lỗi thật: giá trị rowspan bị lặp sai, ô colspan bị nhân nhiều lần, ghi
chú bị chia đôi. Chạy lần đầu với 4 worker và prompt tới ~20k token đã chiếm hết KV cache của
server dùng chung và làm nghẽn mọi job khác; bản hiện tại giới hạn mỗi phần 12k ký tự.

Kết quả: agent đánh giá 40/72 bảng là parse chưa trung thành. So kNN-FS có ghi chú với kNN-FS
thường trong cùng phiên (200 câu dev): 78,5 so với 80,0 EM (7 thắng / 10 thua). Trên 56 câu thuộc
các bảng có ghi chú: 78,6 so với 83,9 (1 thắng / 4 thua). Trên 144 câu còn lại, prompt giống hệt
nhau mà vẫn có 12 câu khác kết quả, tức nhiễu giữa các lần gọi đã cỡ tác động đo được. Kết luận:
agent phát hiện được lỗi parse, nhưng **đưa ghi chú của nó cho solver không có lợi**, xu hướng âm.

### 5.6 Kết quả chính

Dev 200 câu (một lần chạy, trừ FS và kNN-SC3):

| Nhánh | EM | BIF | Lệnh gọi/câu |
|---|---:|---:|---:|
| FS (TB 3 lần) | 73,33 | 73,73 | 1 |
| kNN-SC3, k = 8 (TB 3 lần) | 81,13 | 79,4 (2 lần) | 1 (3 mẫu) |
| v6: kNN16-SC3 / vote 4 mẫu / **MemXam-SC** | 81,50 / 81,50 / **80,00** | — / 79,14 / **79,44** | 1 / 2 / 2,1 |
| v7: kNN16-SC3 / vote 4 mẫu / **MemXam-SC-KV** | 81,91 / 82,91 / **82,41** | 79,44 / 79,76 / **80,04** | 1 / 2 / 2,2 |

Test 200 câu (subset phân tầng `outputs/d04/qas_test_200.json`, một lần chạy):

| Nhánh | EM | BIF | Lệnh gọi/câu | Token prompt/câu | Token sinh/câu |
|---|---:|---:|---:|---:|---:|
| **FS (baseline)** | **71,50** | **73,14** | 1 | 2.204 | 725 |
| kNN-FS (A, k = 8) | 79,40 | 78,53 | 1 | 2.051 | 656 |
| B (lưới + bằng chứng) | 79,90 | 79,60 | 1 | — | — |
| cascade3 / cascade3b / judge-only | 80,90 / 81,91 / 81,41 | 80,18 / 80,00 / 80,06 | ~2,1 | — | — |
| MemXam v4 / MemXam + judge | 80,90 / 81,91 | 79,55 / 80,02 | 2,26 | 4.408 | 1.574 |
| kNN16-SC3 (run v6 / run v7) | 81,50 / 79,90 | 80,09 / 79,27 | 1 | 2.354 | 1.834 |
| vote 4 mẫu (v6 / v7) | 81,50 / 79,90 | 80,25 / 79,28 | 2 | 4.159–5.353 | 2.483 |
| **MemXam-SC (v6)** | **82,50** | **80,52** | 2,12 | 4.664 | 2.562 |
| **MemXam-SC-KV (v7, chọn trên dev)** | **80,90** | **79,66** | 2,17 | 6.085 | 2.598 |

Các nhánh có 199 câu là do một câu có bảng quá lớn vượt ngữ cảnh 32k ở một view; tính câu đó là
sai thì EM giảm 0,5.

So sánh ghép cặp trên test (KTC 95%): MemXam-SC − FS **+11,00 [+5,50; +16,50]**; MemXam-SC-KV − FS
**+9,55 [+4,02; +15,08]**; MemXam-SC − vote 4 mẫu **+1,00 [−1,00; +3,00]**; MemXam-SC-KV − vote 4
mẫu KV +1,0 (cùng 199 câu).

**Đọc kết quả:**
- Khoảng cách lớn và chắc chắn với FS đến từ memory cùng bảng cộng với nhiều mẫu hoặc nhiều view.
- Hai lần chạy kNN16-SC3 giống hệt cấu hình trên test lệch 1,6 EM (81,5 và 79,9). Mọi chênh lệch
  dưới ~2 điểm giữa các nhánh ở đây nằm trong nhiễu giữa các lần chạy.
- Đối chất so với bỏ phiếu trên cùng mẫu: +1,0 ở cả hai lần test, −1,5 và −0,5 ở hai lần dev. Không
  đủ bằng chứng để nói tương tác có lợi riêng.

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

- **Mỗi cấu hình mới chạy một lần** trên 200 câu dev và 200 câu test; sai số giữa các lần chạy
  (±1,5–2,5 EM) lớn hơn mọi hiệu ứng tương tác đo được. Thiết kế v3→v7 được điều chỉnh sau khi
  xem dev, nên con số dev lạc quan.
- **Test là subset 200 câu**, không phải 992 câu; subset này đã được dùng ở D04/D09 cho mục đích
  khác. Cần một lần chạy test đầy đủ trước khi đưa số vào luận văn.
- Phương án chọn trên dev (v7) **hụt BIF 80 trên test 0,34 điểm**; v6 đạt cả hai ngưỡng trên test
  nhưng không phải phương án chọn trên dev.
- Memory dùng đáp án gold của train trên cùng bảng. Điều này hợp lệ với split của Open-ViTabQA
  (theo câu hỏi), nhưng phải nói rõ trong bài: không áp dụng được cho bảng chưa từng thấy. Tỉ lệ câu
  "sinh đôi" nhỏ (EM-twin chỉ lệch ≤ 0,7 điểm).
- Chỉ một backbone (Qwen3-8B), thinking bật, trần 6000 token sinh; FS bị cắt thinking ở ~2,5% số
  câu, các nhánh có memory ít hơn.

## 8. Việc tiếp theo nếu tiếp tục

1. Chạy test đầy đủ 992 câu cho FS, kNN16-SC3, vote 4 mẫu, MemXam-SC và MemXam-SC-KV (A100
   ~1–1,5 giờ).
2. Lặp ít nhất 3 lần các cặp MemXam–vote trên cùng mẫu để đo đóng góp của đối chất với đủ độ phân
   giải; nếu vẫn ≈ 0 thì đóng khung bài theo hướng "memory + đa dạng mẫu", đối chất là ablation.
3. Thử backbone thứ hai (vd. Qwen3-14B AWQ) để kiểm tra MemXam có tổng quát không.

## 9. Backbone lớn hơn qua OpenRouter (hạng mục của kế hoạch ban đầu)

Kế hoạch ban đầu yêu cầu liệt kê backbone lớn hơn theo giá OpenRouter thật. Hạng mục này **bị thay
bằng hướng tự host Qwen3-8B** theo yêu cầu của người dùng giữa chừng. Lý do: tài khoản OpenRouter
chỉ còn ~$2 credit, và mọi thí nghiệm trên dùng Qwen3-8B tự host. Giá dưới đây lấy từ
`https://openrouter.ai/api/v1/models` ngày **2026-09-26** (USD / 1M token; giá thay đổi thường
xuyên, cần tải lại trước khi dùng):

| Model | Prompt | Sinh | Ngữ cảnh |
|---|---:|---:|---:|
| `qwen/qwen3-8b` (backbone hiện tại) | 0.117 | 0.455 | 131072 |
| `qwen/qwen3-14b` | 0.120 | 0.240 | 131072 |
| `qwen/qwen3-32b` | 0.080 | 0.280 | 131072 |
| `qwen/qwen3-30b-a3b-instruct-2507` | 0.100 | 0.300 | 262144 |
| `qwen/qwen3-235b-a22b-2507` | 0.087 | 0.350 | 262144 |
| `qwen/qwen3-next-80b-a3b-instruct` | 0.100 | 1.100 | 262144 |
| `deepseek/deepseek-v4-flash` | 0.047 | 0.094 | 1048576 |
| `deepseek/deepseek-chat-v3.1` | 0.250 | 0.950 | 163840 |
| `google/gemma-4-31b-it` | 0.090 | 0.340 | 262144 |
| `google/gemma-3-27b-it` | 0.080 | 0.450 | 131072 |
| `openai/gpt-oss-120b` | 0.150 | 0.600 | 131072 |
| `google/gemini-2.5-flash-lite` | 0.100 | 0.400 | 1048576 |
| `meta-llama/llama-4-maverick` | 0.188 | 0.652 | 1048576 |
| `mistralai/mistral-small-3.2-24b-instruct` | 0.094 | 0.250 | 256000 |

Ước lượng chi phí: FS trên 200 câu dùng ~0,44M token prompt và ~0,15M token sinh (§5.6), nên một
lượt FS 200 câu trên các model ~$0,1/$0,35 tốn khoảng $0,1; MemXam-SC tốn khoảng gấp 2 lần prompt
và 3,5 lần token sinh. Giao thức đề xuất nếu tiếp tục: chạy FS và kNN-SC3 trên 2–3 model lớn trước
(rẻ, nhanh), chỉ chạy MemXam-SC trên model nào vượt Qwen3-8B, rồi dùng cùng `score_mas_tqa.py` /
`bif_mas_tqa.py` và so sánh ghép cặp như trên.

## 10. ViNLI 4 nhãn so với 3 nhãn, và PhoBERT tách riêng

Checkpoint BIF của repo là XLM-R Large huấn luyện **4 nhãn** (`0 entailment, 1 contradiction,
2 neutral, 3 other`, notebook `reproductions/vinli/`), trong khi bài báo của dataset dùng mô hình 3
nhãn. `OTHER` trong ViNLI nghĩa là premise và hypothesis không liên quan về sự kiện, chủ thể hay đối
tượng. Đo lại đủ 4 xác suất cho mọi cặp (reference → prediction) đã chấm
(`scripts/bif_label_analysis.py`, `outputs/mas_tqa/eval/bif_label_analysis.json`). Cột `BIF_3~` bỏ
`OTHER` rồi chuẩn hoá lại P(E)/(P(E)+P(C)+P(N)); đây là **xấp xỉ**, không phải mô hình 3 nhãn được
huấn luyện riêng. `BIF_4` tính lại khớp đúng các số BIF đã báo.

| Split | Nhánh | PhoBERT-F1 | P(E), 4 nhãn | P(OTHER) | BIF (4 nhãn) | BIF 3 nhãn (xấp xỉ) |
|---|---|---:|---:|---:|---:|---:|
| dev | gold = dự đoán (trần) | 100,00 | 73,04 | 12,34 | 86,52 | 89,19 |
| dev | FS (3 lần) | 88,12–89,03 | 58,3–59,8 | 24,1–25,5 | 73,23–74,41 | 78,34–79,28 |
| dev | kNN-FS | 91,05 | 61,91 | 21,18 | 76,48 | 80,74 |
| dev | kNN-SC3 (2 lần) | 92,84 / 93,27 | 65,9 / 65,6 | 17,9 / 18,0 | 79,39 / 79,44 | 83,04 / 83,14 |
| dev | MemXam-SC / vote 4 mẫu (v6) | 93,37 / 93,64 | 65,50 / 64,63 | 17,68 / 18,15 | 79,44 / 79,14 | 83,10 / 82,78 |
| dev | MemXam-SC-KV / vote 4 mẫu KV (v7) | 93,66 / 93,64 | 66,42 / 65,89 | 17,07 / 17,39 | 80,04 / 79,76 | 83,55 / 83,31 |
| test | gold = dự đoán (trần) | 100,00 | 74,91 | 11,96 | 87,45 | 89,97 |
| test | FS | 88,04 | 58,23 | 25,24 | 73,14 | 77,88 |
| test | kNN-FS | 91,93 | 65,13 | 19,07 | 78,53 | 82,25 |
| test | kNN16-SC3 | 93,56 | 66,62 | 17,46 | 80,09 | 83,60 |
| test | MemXam v4 | 93,09 | 66,01 | 17,69 | 79,55 | 83,04 |
| test | MemXam-SC / vote 4 mẫu (v6) | 94,33 / 93,81 | 66,70 / 66,69 | 17,01 / 17,11 | 80,52 / 80,25 | 83,89 / 83,66 |
| test | MemXam-SC-KV / vote 4 mẫu KV (v7) | 93,11 / 92,82 | 66,20 / 65,75 | 17,27 / 18,29 | 79,66 / 79,28 | 83,01 / 82,90 |

Nhận xét:
- Mô hình 4 nhãn dồn **~12% xác suất vào `OTHER` ngay cả khi dự đoán trùng hệt gold**. Phần này rơi
  vào các đáp án số/năm trơ trọi, nơi cặp "câu" không có nội dung sự kiện. Với dự đoán sai, `OTHER`
  lên 17–25%.
- Bỏ `OTHER` nâng trần BIF từ 86,5 lên ~89,2 (dev) và từ 87,5 lên ~90,0 (test). Mọi phương pháp tăng
  khoảng 3,4–4,9 điểm BIF; FS tăng nhiều hơn một chút (dự đoán sai của nó dồn nhiều vào `OTHER`), nên
  khoảng cách BIF giữa MemXam và FS co lại ~1 điểm. **Thứ hạng giữa các phương pháp không đổi.**
- Với xấp xỉ 3 nhãn, mọi phương pháp có memory đều vượt BIF 80 trên cả hai subset; nhưng đây là xấp
  xỉ. Để so với số trong bài báo của dataset, cần huấn luyện lại ViNLI 3 nhãn (notebook đã hỗ trợ
  `NUM_LABELS = 3`, bỏ các cặp `OTHER`) rồi chấm lại; khi đó cả hai phần của BIF mới cùng giao thức.
- **PhoBERT-F1 riêng**: FS 88,0–89,0; kNN-FS 91,1–91,9; các ensemble và MemXam 92,8–94,3. Thứ hạng
  theo PhoBERT khớp thứ hạng theo EM.

### 10.1 Chấm lại bằng ViNLI 3 nhãn huấn luyện thật

Checkpoint `checkpoints/vinli-xlmr-large-3label/checkpoint-best` (XLM-R Large, bỏ `OTHER`, Adam 1e-5,
batch 16, 10 epoch, chọn theo dev ở epoch 5; split 18.282 / 2.255 / 2.264): test **81,63 acc / 81,62
macro-F1**, sát mốc paper ViNLI (81,36 / 81,31). Entailment là index 0. Cột `BIF_3` dưới đây dùng
P(entailment) của mô hình này; PhoBERT-F1 giữ nguyên.

| Split | Nhánh | P(E) 3 nhãn | **BIF 3 nhãn** | BIF 4 nhãn |
|---|---|---:|---:|---:|
| dev | gold toàn split (trần) | 48,93 | **74,46** | 87,48 |
| dev | gold dev-200 (trần) | 48,59 | 74,29 | 86,52 |
| dev | FS (3 lần) | 38,1–40,1 | 63,26–64,58 | 73,23–74,41 |
| dev | kNN-SC3 (2 lần) | 43,3 / 43,4 | 68,06 / 68,35 | 79,39 / 79,44 |
| dev | MemXam-SC-KV (v7) | 44,38 | 69,02 | 80,04 |
| test | gold toàn split (trần) | 52,77 | **76,38** | 88,97 |
| test | gold test-200 (trần) | 52,42 | 76,21 | 87,45 |
| test | FS | 40,72 | 64,38 | 73,14 |
| test | kNN16-SC3 / vote 4 mẫu | 47,48 / 47,25 | 70,52 / 70,53 | 80,09 / 80,25 |
| test | **MemXam-SC (v6)** | 47,77 | **71,05** | 80,52 |
| test | MemXam-SC-KV (v7) | 46,50 | 69,80 | 79,66 |

Mô hình 3 nhãn được huấn luyện thật **không** giống xấp xỉ "bỏ `OTHER`" ở §10: với dự đoán trùng hệt
gold, nó chỉ cho P(entailment) ~49–53%, vì các cặp số/năm trơ trọi không còn chỗ trong `OTHER` và bị
đẩy sang `neutral`. Trần BIF 3 nhãn chỉ 74,5 (dev) / 76,4 (test). Thứ hạng phương pháp không đổi;
MemXam-SC đạt 93% trần BIF 3 nhãn trên test-200 (71,05 / 76,21), FS đạt 84%.

**Cần kiểm tra lại với bài báo của dataset:** repo cài BIF với cặp NLI là (đáp án gold → đáp án dự
đoán), không kèm câu hỏi. Nếu bài báo báo cáo BIF lớn hơn ~76 với ViNLI 3 nhãn, thì cách dựng cặp của
họ phải khác (ví dụ ghép câu hỏi để thành câu hoàn chỉnh). Bản PDF của bài báo không có trong repo nên
chưa đối chiếu được.

## 11. Test đầy đủ 992 câu (một lần chạy, A100, 2026-09-27)

Qwen3-8B tự host trên một A100 SXM4 40GB (Vast, $0,601/giờ, ~1,2 giờ, ~$0,6). Cả ba cấu hình chạy
trong cùng một phiên. v7 dùng lại 3 mẫu A của v6 cho các câu v6 đã chạy xong (mẫu độc lập, cùng
prompt), để tiết kiệm GPU; các câu còn lại v7 tự lấy mẫu A.

| Phương pháp | EM | So với FS [KTC 95%] | PhoBERT-F1 | BIF 4 nhãn | BIF 3 nhãn |
|---|---:|---:|---:|---:|---:|
| FS (baseline) | 73,59 | — | 89,33 | 76,36 | 66,83 |
| kNN16-SC3 | 79,23 | +5,65 [+3,53; +7,86] | 92,65 | 80,31 | 69,88 |
| Vote 4 mẫu (v6) | 80,14 | +6,55 [+4,44; +8,77] | 93,08 | 80,78 | 70,24 |
| **MemXam-SC (v6)** | **80,54** | **+6,96 [+4,74; +9,17]** | 93,14 | **80,87** | 70,40 |
| Vote 4 mẫu KV (v7) | 80,28 (989) | +6,57 [+4,45; +8,80] | 93,17 | 81,06 (988) | 70,55 |
| **MemXam-SC-KV (v7, chọn trên dev)** | **81,19** (989; 80,95 nếu tính 3 câu thiếu là sai) | **+7,48 [+5,26; +9,71]** | 93,44 | **81,38** (988) | 70,76 |
| Trần (dự đoán = gold) | 100 | — | 100 | 88,97 | 76,38 |

- v7 thiếu 3 câu vì bảng render sang Markdown-KV vượt ngữ cảnh 32k; EM tính trên 989 câu và báo
  thêm con số khi tính 3 câu đó là sai. BIF của hai nhánh v7 bỏ thêm câu `62_3_178`, nơi output KV
  là JSON hỏng dài 2.843 ký tự làm PhoBERTScore crash (lỗi đã biết của repo); EM vẫn tính câu này
  là sai.
- **Đối chất so với bỏ phiếu trên cùng mẫu (ghép cặp):** v6 +0,40 [−0,60; +1,41]; v7 **+0,91
  [+0,00; +1,82]**. Trên 989 câu, lần đầu tiên hiệu ứng của tương tác có cận dưới chạm 0 — dương
  nhưng nhỏ, chưa vượt ngưỡng có ý nghĩa một cách thuyết phục; cần thêm lần chạy lặp.
- So với trần: MemXam-SC-KV đạt 91,5% trần BIF 4 nhãn và 92,6% trần BIF 3 nhãn; FS đạt 85,8% và
  87,5%.
- Mốc tham chiếu từ bài báo dataset (`docs/Open_ViTabQA.pdf`, checkpoint ViNLI riêng của tác giả):
  Gemini 1.5 Pro 60,80 EM / 0,649 BIF; con người 83,43 EM / 0,781 BIF.

**Tình trạng mục tiêu (đã hạ):** EM ≥ 80 và BIF 4 nhãn ≥ 80 đạt trên test đầy đủ với phương án chọn
trên dev (81,0–81,2 EM, 81,4 BIF). Mục tiêu EM 83–85 chưa đạt (còn thiếu ~2 điểm).

## 12. Phân tích lỗi MemXam-SC-KV trên test đầy đủ

`python scripts/analyze_errors_mas_tqa.py` (989 câu có kết quả; danh sách câu sai ghi ra
`outputs/mas_tqa/eval/errors_memxam_sckv_test.json`). MemXam 81,19, FS 73,71, oracle ứng viên 87,36.

**186 câu sai theo tầng:** 125 câu (67%) không ứng viên nào đúng, tức trần do độ phủ; 61 câu có
ứng viên đúng nhưng bị loại: 20 câu B đúng một mình nhưng A 3/3 đồng nhất nên dừng ở đồng thuận,
15 câu 1/3 mẫu A đúng nhưng hai mẫu A còn lại cùng B sai giống nhau, 26 câu thua sau đối chất.
Đối chất chạy trên 85 câu, đúng 44,7% trong khi oracle trên nhóm đó 75,3%. 31 câu FS đúng mà
MemXam sai.

**Nhóm yếu.** Câu Vì sao 55,6 (thấp hơn FS 63,0), Như thế nào 53,8, đáp án gold ≥8 token 62,2,
tính toán 77,8 (nhiều câu sai nhất: 44), liệt kê/sắp xếp 76,8. Bảng Flatten ≥16k ký tự 56,0
(không lợi so với FS, oracle cũng 56), bảng chỉ có ô gộp giá trị 76,7 (61 câu sai), bảng 40–80
dòng 75,5. Lợi ích phụ thuộc memory: câu có câu train cùng bảng Jaccard ≥0,8 lời +21,7 EM so với
FS, Jaccard <0,5 chỉ khoảng +5; bảng có dưới 10 cặp train chỉ lời +2,0. Với bảng mới hoàn toàn,
phần lợi sẽ giảm mạnh.

**Bản chất 186 câu sai:** 112 sai thật (ô, giá trị, phép tính); 23 đúng nội dung khác định dạng
("2006"/"Năm 2006", "34.4"/"34,4", dấu nháy, "và"/dấu phẩy, bảng gốc viết "Vuơng" còn gold "Vương");
16 Có/Không đúng cực tính khác từ; 17 trả Null; 12 Vì sao/Như thế nào diễn đạt khác; 6 gold Null
(tiền đề sai) nhưng mô hình vẫn trả lời. Sửa Verbalize cho từ Có/Phải/Đúng không khả thi: trên train,
luật hiện tại khớp 90,1% nhãn Có/Không, thêm luật "có phải → Phải" vẫn 90,1%, còn luật lấy từ đa số
của bảng chỉ 70,7%; phần này là nhiễu nhãn, không sửa.

## 13. v8: agent C viết code và luật B phủ quyết (dev đầy đủ, 2026-09-28)

Từ phân tích lỗi §12 thử hai hướng, chọn trên **dev đầy đủ** (991 câu, 983 có kết quả; 8 câu lỗi
HTTP 400, nhiều khả năng do bảng vượt context) rồi mới quyết định chạy test. Tiêu chí đặt trước:
chạy test chỉ khi luật tốt nhất hơn luật v7 với khoảng tin cậy 95% ghép cặp nằm hẳn trên 0.

- **Agent C (Program-of-Thought):** Qwen3-8B (thinking) viết code pandas trên `df` dựng từ
  `table_dict`, kèm 8 cặp hỏi–đáp cùng bảng; code chạy trong tiến trình con có timeout 10 giây,
  giới hạn import, không có `open`/`exec` (`mas_tqa/code_agent.py`).
- **Luật dừng:** tầng đầu (A 3 mẫu, B Markdown-KV, C) chạy một lần; đối chất chạy khi 5 đáp án
  chưa đồng nhất; mọi luật được tính trên cùng các lệnh gọi nên so sánh là ghép cặp
  (`suite_v8`, `scripts/analyze_v8.py`).

| Luật (dev 983 câu, một lần chạy) | EM | Δ so với MemXam-SC-KV [95% CI] | Lệnh gọi/câu |
|---|---:|---:|---:|
| kNN16-SC3 (chỉ A) | 80,47 | −0,61 [−1,73; +0,61] | 1 |
| vote 4 (A×3 + B) | 81,38 | +0,31 [−0,71; +1,32] | 2 |
| MemXam-SC-KV (luật v7) | 81,08 | — | 2,19 |
| **B phủ quyết** (A 3/3 mà B bất đồng → vẫn đối chất) | **81,59** | **+0,51 [−0,10; +1,22]** | 2,31 |
| bỏ phiếu 5 có C, dừng khi ≥4/5 | 81,08 | +0,00 [−0,92; +0,81] | 3,3 |
| C một mình | 58,39 | −22,69 | 1 |

**Agent C không nâng trần.** C chỉ đúng 58,4%; 187/983 câu code lỗi (98 câu không sinh khối code,
45 KeyError do gọi sai tên cột, còn lại ValueError/IndexError khi ép kiểu số). Trên 125 câu mà cả
A lẫn B đều sai, C chỉ cứu 3 câu; trên 800 câu vote 4 đúng, C sai 246. Ngay cả nhóm tính toán C chỉ
đạt 53,6 so với 76,8 của vote 4. Với Qwen3-8B, đọc bảng trực tiếp tốt hơn viết code trên bảng
Wikipedia bẩn (ô gộp, số kiểu Việt, chú thích [10]).

**B phủ quyết có hướng đúng nhưng chưa đủ mạnh.** Luật mở thêm 60 câu đối chất; A đổi lập trường
ở 30 câu; kết quả đúng 29 so với 24 của luật v7, tức +5 câu ròng trên 983 (+0,51 EM), khoảng tin
cậy chạm 0. Không đạt tiêu chí nên **không chạy test**, đã huỷ GPU ngay (chi phí khoảng $1,05).

**Ghi nhận thêm:** trên dev đầy đủ, MemXam-SC-KV chỉ hơn kNN16-SC3 +0,61 EM (CI chạm 0), còn
vote 4 không đối chất đã ngang MemXam. Kết quả này củng cố kết luận §5: phần lợi chính đến từ memory
cùng bảng và self-consistency; đóng góp riêng của đối chất nhỏ, dưới mức phân giải của một lần chạy.

## 14. Sửa từng nhóm câu sai (2026-09-28)

Mọi luật được chọn trên dev (trace v8 dev, 983 câu), rồi áp đúng một lần lên test. Không gọi LLM,
không thuê GPU.

**Định dạng: agent định dạng tất định (`mas_tqa/style.py`).** Đo leave-one-out trên train: người
gán nhãn nhất quán theo bảng ở tiền tố "Năm" cho đáp án năm (đa số toàn cục 85,6% → đa số cùng
bảng 93,0%) và việc kèm đơn vị khi hỏi "bao nhiêu <đơn vị>" (94,0% → 97,0%); gold không bao giờ
giữ ký hiệu chú thích (0 gold, trong khi 90 ô bảng train kết thúc bằng `*`); số ≥1.000 chủ yếu viết
kiểu 1.234.567. Agent sửa theo 5 luật: năm, đơn vị (chỉ khi có câu train cùng bảng hỏi đúng đơn vị
đó), chú thích, hàng nghìn (khi bảng viết kiểu 1.234.567), gộp danh sách lặp. Hai luật bị loại trên
dev: tiền tố hành chính theo ô bảng (sửa 0 / hỏng 2) và dấu thập phân (không đổi câu nào).

| Test (luật chốt trên dev) | EM gốc | + định dạng | Δ [95% CI] | sửa / hỏng | BIF (4 nhãn) gốc → mới |
|---|---:|---:|---:|---:|---:|
| MemXam-SC-KV | 81,19 | **81,90** | +0,71 [+0,10; +1,42] | 10 / 3 | 81,38 → **81,78** |
| vote 4-KV | 80,28 | 81,19 | +0,91 [+0,20; +1,72] | 12 / 3 | |
| kNN16-SC3 | 79,78 | 80,69 | +0,91 [+0,20; +1,72] | 12 / 3 | |
| FS | 73,59 | 74,70 | +1,11 [+0,40; +1,92] | 13 / 2 | 76,36 → 76,89 |

Agent có ích cho mọi phương pháp, kể cả FS, nên khoảng cách MemXam–FS gần như giữ nguyên
(+7,60 → +7,20 EM). Câu bị hỏng là do người gán nhãn không nhất quán ngay trong một bảng.

**Có/Không khác từ (16 câu):** luật Verbalize hiện tại đã tốt nhất trên train (90,1%); là nhiễu nhãn.

**Trả Null / gold Null (17 + 6 câu):** luật "đáp án cuối Null mà có ứng viên khác Null thì lấy
ứng viên đó" trên dev sửa 1, hỏng 3 (−0,20 EM): hai nhóm kéo ngược nhau, không có luật tất định
nào tách được.

**Vì sao / Như thế nào (12 câu):** đáp án diễn đạt tự do; EM không phù hợp, dùng BIF.

**Sai thật (~112 câu):**
- Lỗi tính nhẩm thật chỉ 7 câu trên dev (còn lại: tra sai ô 17, đếm sai 11, xếp hạng 2 trong 37
  câu số–số); agent máy tính có trần khoảng +0,7 EM, chưa đáng làm.
- 65 câu dev sai dù đáp án đúng đã có trong tập ứng viên. Bộ chọn học được (logistic regression,
  đặc trưng: phiếu A, phiếu B, đối chất, trùng ô bảng, độ dài; `scripts/selector_mas_tqa.py`):
  CV 5-fold theo bảng trên dev +0,31 [−0,41; +1,02], không áp lên test. Hệ số cho thấy một phiếu B
  nặng gấp khoảng 2,5 lần một mẫu A, cùng hướng với luật B phủ quyết (§13).
- Thêm backbone < 10B khác làm phiếu phụ: mỗi model chỉ bù 3–7/33 lỗi MemXam trên dev-200; tổ hợp
  tốt nhất +1,0 đến +1,5 EM nhưng được chọn trong hơn 50 tổ hợp trên chính 200 câu đó, nằm trong nhiễu.

**Kết luận.** Phần sửa được mà không cần huấn luyện là định dạng (+0,7 EM, +0,4 BIF, có ý nghĩa
thống kê). Nhóm sai thật cần ứng viên đúng mới; mọi cách không huấn luyện đã thử (agent viết code,
backbone khác, bộ chọn, B phủ quyết) đều dưới mức phân giải của một lần chạy.

## 15. EM mở rộng: tính đúng các cách viết cùng nghĩa (2026-09-28)

`evaluation/lenient.py`, `python scripts/score_lenient.py`. EM gốc giữ nguyên; báo cáo thêm hai mức:

- **yn**: Có = Đúng = Phải; Không = Sai = Không phải (cùng cực tính).
- **format**: thêm đồng nghĩa định dạng: tiền tố "Năm", đơn vị trùng đơn vị trong câu hỏi "bao nhiêu
  <đơn vị>", dấu thập phân (34,4 = 34.4), dấu hàng nghìn (10.400.000 = 10400000), ký hiệu chú thích,
  dấu nháy, tiền tố hành chính ("Thành phố New York" = "New York"), "và" = dấu phẩy, danh sách không
  xét thứ tự trừ khi câu hỏi yêu cầu sắp xếp.

Đã đọc từng cặp chỉ đúng ở mức mở rộng của MemXam (16 yn + 29 format) và FS: tất cả cùng nghĩa.

| Test | n | EM gốc | EM + yn | EM + format | Δ so với FS: gốc / yn / format |
|---|---:|---:|---:|---:|---|
| FS | 992 | 73,59 | 75,00 | 78,73 | — |
| kNN16-SC3 (v7) | 989 | 79,78 | 81,40 | 84,73 | +6,07 / +6,27 / +5,86 |
| vote 4 (v6) | 992 | 80,14 | 81,75 | 84,98 | +6,55 / +6,75 / +6,25 |
| MemXam-SC (v6) | 992 | 80,54 | 82,16 | 85,08 | +6,96 / +7,16 / +6,35 |
| vote 4-KV (v7) | 989 | 80,28 | 81,90 | 85,14 | +6,57 / +6,77 / +6,27 |
| **MemXam-SC-KV (v7)** | 989 | **81,19** | **82,81** | **85,74** | **+7,48 / +7,68 / +6,88** |

Mọi khoảng tin cậy 95% ghép cặp so với FS đều nằm trên +3,3. Mức format thu hẹp khoảng cách
một chút (+7,48 → +6,88) vì FS không có memory cùng bảng nên sai định dạng nhiều hơn; memory giúp
MemXam viết đúng kiểu gold ngay từ đầu. Agent định dạng (§14) chỉ sửa một phần của nhóm này: ở mức
format, có hay không có agent đều ra 85,74 (MemXam) và 78,73 (FS).

## 16. BIF gốc và BIF mở rộng cho mọi phương pháp (test, 988 câu chung)

`python scripts/bif_all.py`. Tập câu chung của mọi file: bỏ 3 câu v7 thiếu và `62_3_178` (PhoBERTScore
crash). BIF mở rộng: câu nào EM mở rộng (§15) tính đúng thì dùng chính gold làm dự đoán, nên điểm câu đó
bằng trần gold-làm-dự-đoán. Mỗi cặp (gold, dự đoán) duy nhất chấm một lần (1.057 cặp), cache ở
`outputs/mas_tqa/eval/bif_pairs_cache.json`. ViNLI 4 nhãn = checkpoint cũ; 3 nhãn = checkpoint huấn luyện
thật (§10.1). Δ là chênh lệch ghép cặp của BIF gốc so với FS.

| Test (988 câu) | PhoBERT | BIF4 gốc | BIF4 + yn | BIF4 + format | BIF3 gốc | BIF3 + yn | BIF3 + format | Δ BIF4 / BIF3 so với FS [95% CI] |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| FS | 89,37 | 76,44 | 76,99 | 78,20 | 66,90 | 67,09 | 67,72 | — |
| FS + định dạng | 89,65 | 76,98 | 77,53 | 78,23 | 67,32 | 67,51 | 67,76 | +0,54 [+0,26; +0,86] / +0,42 [+0,21; +0,67] |
| kNN16-SC3 (v6) | 92,69 | 80,34 | 80,92 | 81,98 | 69,95 | 70,08 | 70,67 | +3,90 [+2,71; +5,17] / +3,05 [+2,06; +4,13] |
| kNN16-SC3 (v7) | 92,87 | 80,68 | 81,25 | 82,31 | 70,23 | 70,36 | 70,95 | +4,23 [+3,03; +5,50] / +3,32 [+2,33; +4,40] |
| vote 4 (v6) | 93,11 | 80,82 | 81,40 | 82,44 | 70,31 | 70,45 | 71,02 | +4,37 [+3,19; +5,66] / +3,40 [+2,39; +4,47] |
| MemXam-SC (v6) | 93,18 | 80,91 | 81,49 | 82,47 | 70,48 | 70,62 | 71,16 | +4,47 [+3,22; +5,76] / +3,57 [+2,54; +4,67] |
| vote 4-KV (v7) | 93,17 | 81,06 | 81,64 | 82,68 | 70,55 | 70,69 | 71,25 | +4,62 [+3,38; +5,90] / +3,65 [+2,60; +4,73] |
| **MemXam-SC-KV (v7)** | 93,44 | **81,38** | **81,96** | **82,92** | **70,76** | **70,90** | **71,40** | **+4,93 [+3,65; +6,23] / +3,85 [+2,77; +4,96]** |
| MemXam-SC-KV + định dạng | 93,64 | 81,78 | 82,36 | 82,94 | 71,14 | 71,28 | 71,42 | +5,33 [+4,02; +6,64] / +4,24 [+3,15; +5,37] |
| Trần (gold làm dự đoán) | 100 | 88,98 | — | — | 76,45 | — | — | |

- Thứ tự các phương pháp giữ nguyên ở mọi cột; MemXam-SC-KV đứng đầu ở cả 6 biến thể BIF.
- BIF mở rộng chỉ tăng 0,5–1,8 điểm (EM mở rộng tăng 4,5 điểm) vì BIF vốn đã cho điểm một phần các
  cách viết cùng nghĩa, và trần của chính BIF thấp (88,98 / 76,45): đổi dự đoán thành gold vẫn không
  đạt 100. MemXam-SC-KV đạt 91,5% trần BIF4 và 92,6% trần BIF3 (gốc); 93,2% / 93,4% (mở rộng).

## 17. Agent M (sinh biểu thức) + agent V (kiểm tra) cho câu tính toán (2026-09-28)

`mas_tqa/math_agent.py`, method `math_mv`, `scripts/analyze_math.py`. Chạy qua OpenRouter (Qwen3-8B,
provider Alibaba, thinking) trên 296 câu dev mà router gán "compute" (không dùng hint; bắt 214/234 câu có
hint tính toán), chi phí khoảng $0,50.

- **M:** đọc bảng Markdown-KV + 8 câu mẫu cùng bảng, chọn loại phép (`tính` / `đếm` / `chọn` /
  `xếp_hạng` / `lookup`), trích ô và viết biểu thức cùng lời giải thích; Python tính tất định (bộ tính
  biểu thức an toàn qua `ast`, chỉ số và phép toán). Câu chỉ cần tra ô thì M bỏ qua.
- **V:** kiểm tra tất định (ô trích phải có trong bảng) và LLM (đúng ô, đủ ô, đúng phép); được sửa lời giải.

**Độ chính xác có điều kiện (dev, 174 câu M trả lời):** M đúng 43,7% (MemXam đúng 80,5% trên cùng câu).
Khi MemXam sai (34 câu) M đúng 6; khi MemXam đúng (140 câu) M sai 70. V xác nhận 107 câu, trong đó M
đúng 67 (MemXam 91); V bác 63 câu, đưa bản sửa 57 câu nhưng chỉ 12 bản sửa đúng.

| Loại M chọn | n | M đúng | MemXam đúng | M đúng mà MemXam sai |
|---|---:|---:|---:|---:|
| đếm | 87 | 52 | 74 | 1 |
| tính | 43 | 24 | 26 | 5 |
| chọn | 41 | 0 | 38 | 0 |
| xếp_hạng | 3 | 0 | 2 | 0 |

`chọn` = 0 do lỗi prompt: M lấy tiêu đề khối "Hàng i" làm nhãn thay vì tên đối tượng. `đếm` sai chủ yếu
vì liệt kê cả hàng không thỏa điều kiện. `tính`, nhóm mà ý tưởng nhắm tới, sửa được 5 lỗi tính nhẩm thật
nhưng làm hỏng 7 câu (phần lớn lệch đơn vị, vd "3" so với gold "3 tháng").

| Luật ghép (dev 983 câu, sau agent định dạng) | EM | Δ [95% CI] | sửa / hỏng |
|---|---:|---:|---:|
| MemXam-SC-KV | 81,99 | — | — |
| thay bằng M khi V xác nhận | 79,55 | −2,44 [−3,56; −1,32] | 5 / 29 |
| thay bằng M+V (kể cả bản sửa của V) | 76,30 | −5,70 [−7,32; −4,17] | 6 / 62 |
| M+V làm 2 phiếu thêm | 82,20 | +0,20 [+0,00; +0,51] | 2 / 0 |
| M+V làm trọng tài khi tranh chấp | 81,28 | −0,71 [−1,63; +0,10] | 6 / 13 |
| chỉ thay khi đáp án M+V trùng một ứng viên sẵn có | 82,40 | +0,41 [−0,10; +1,02] | 6 / 2 |
| chỉ loại `tính`, V xác nhận, giữ đơn vị MemXam | 82,10 | +0,10 [−0,41; +0,61] | 4 / 3 |

**Kết luận.** Không luật nào đạt tiêu chí nên không chạy test. Lỗi của nhóm tính toán nằm ở khâu chọn và
lọc hàng, không ở khâu tính: trên dev chỉ 7 câu là lỗi tính nhẩm thật, và M đọc/lọc hàng kém hơn MemXam
đọc trực tiếp. Bản sửa lỗi nhãn `chọn` chưa chạy lại (credit OpenRouter còn khoảng $0,40); trần của nó
nhỏ vì MemXam đã đúng 38/41 câu loại này.

**PhoBERT-F1 riêng** (cùng 988 câu, lấy từ cache chấm BIF; gốc / + yn / + format; Δ ghép cặp so với FS):
FS 89,37 / 90,17 / 90,95; FS + định dạng 89,65; kNN16-SC3 v7 92,87 (+3,50 [+2,50; +4,53]); vote 4 v6 93,11;
MemXam-SC v6 93,18; vote 4-KV v7 93,17; **MemXam-SC-KV 93,44 / 94,31 / 94,97 (+4,07 [+2,99; +5,17])**;
MemXam-SC-KV + định dạng 93,64.
