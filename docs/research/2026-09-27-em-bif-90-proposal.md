# Mục tiêu EM/BIF ≥ 90 với model < 10B và multi-agent: đánh giá khả thi và đề xuất

Ngày: 2026-09-27. Nối tiếp [`2026-09-26-memxam-multi-agent-qwen3-8b.md`](2026-09-26-memxam-multi-agent-qwen3-8b.md)
(kết quả hiện tại: MemXam-SC 82,5 EM / 80,5 BIF trên test-200, Qwen3-8B, chỉ prompt) và bản khảo
sát [`2026-09-26-multi-agent-tqa-de-xuat.md`](2026-09-26-multi-agent-tqa-de-xuat.md).
Ràng buộc: backbone < 10B tham số, phương pháp là multi-agent.

## Tóm tắt

1. **BIF ≥ 90 không đạt được với metric hiện tại, bất kể phương pháp.** Chấm chính gold làm dự
   đoán (EM 100%) chỉ cho BIF 86,52 (dev-200), 87,45 (test-200), 87,48 (dev đủ), 88,97 (test đủ),
   vì ViNLI 4 nhãn đẩy ~12% xác suất vào `OTHER` ngay cả với cặp trùng hệt. Xấp xỉ bỏ `OTHER` (3
   nhãn) nâng trần lên ~89,2 / 90,0: vẫn cần EM gần 100% mới chạm 90.
2. **EM ≥ 90 nằm sát trần nhất quán của chính dataset.** 34 nhóm câu hỏi trùng hệt nhau trên cùng
   bảng chỉ có 31 nhóm cùng gold (91,2%). Câu Có/Không (19,6% dev): dù biết đúng cực tính, từ
   `Có/Đúng/Phải/Không` chỉ đoán được 87,6% (≈ 2,4 điểm EM không lấy lại được). Oracle của mọi ứng
   viên hiện có trên dev là 86,9.
3. **Chỉ prompt thì đã bão hoà ở ~82–83 EM** (vote trên nhiều mẫu/view; judge và verifier zero-shot
   không giúp). Bằng chứng duy nhất cho bước nhảy lớn ở < 10B trong literature là **huấn luyện**:
   Table-R1 (Qwen2.5-7B, RLVR) WTQ 54,8 → 79,8; Mixture-of-Minds (Qwen3-8B, GRPO từng vai) 47,4 →
   57,4; MATATA (Phi-3-mini 3,8B) FinQA 47,1 → 70,1. Kết quả của ta cũng cùng chiều: phần lớn lợi ích
   đến từ việc khớp phong cách đáp án của người gán nhãn (bộ nhớ cùng bảng), điều mà huấn luyện làm
   trực tiếp hơn.
4. **Đề xuất: MemXam-T** — multi-agent có **vai được huấn luyện**: 2 solver LoRA (khác backbone
   hoặc khác view) học từ train với bộ nhớ cùng bảng, một **verifier được huấn luyện** trên ứng
   viên sinh ra từ train để thay cho bỏ phiếu, và vòng phản hồi verifier → solver khi mọi ứng viên bị
   loại. Mục tiêu thực tế: **EM ~86–88 trên test đủ 992 câu**, BIF ~83 (4 nhãn) / ~86 (3 nhãn).
5. **Đề nghị sửa mục tiêu** thành EM ≥ 87 và BIF chuẩn hoá theo trần (BIF / BIF-trần) ≥ 0,95, báo cả
   BIF 4 nhãn và 3 nhãn. Cần GVHD đồng ý việc fine-tune (quyết định #6 trong các tài liệu trước).

## 1. Vì sao 90 không phải mục tiêu khả thi

### 1.1 BIF

BIF = 0,5 × PhoBERTScore-F1 + 0,5 × P(entailment của ViNLI), reference → prediction. Với dự đoán trùng
gold, PhoBERT = 1,0 nhưng P(entailment) chỉ trung bình 0,73–0,75, thấp nhất ở đáp án số/năm (0,46).

| Tập | Trần BIF 4 nhãn (EM = 100%) | Trần xấp xỉ 3 nhãn |
|---|---:|---:|
| dev-200 | 86,52 | 89,19 |
| test-200 | 87,45 | 89,97 |
| dev đủ 991 | 87,48 | — |
| test đủ 992 | 88,97 | — |

Không có cách hợp lệ nào đưa BIF lên 90 với checkpoint hiện tại. Cách duy nhất là "làm đẹp metric"
(vd. viết đáp án thành câu `Năm 2003` để NLI chấm cao hơn), nhưng làm vậy mất EM và không phản ánh
chất lượng thật, nên **không đề xuất**. Việc cần làm là huấn luyện ViNLI 3 nhãn như bài báo của
dataset (notebook `notebooks/vinli-coling-2022.ipynb`, `NUM_LABELS = 3`), đo lại trần, rồi báo BIF
kèm trần tương ứng.

### 1.2 EM

- **Tự nhất quán của nhãn:** 31/34 nhóm câu hỏi trùng hệt trên cùng bảng có cùng gold (91,2%; n
  nhỏ, chỉ là ước lượng thô). Nếu tỉ lệ bất nhất ~9% này đúng cho cả tập thì trần EM thực tế nằm
  quanh 90–91.
- **Chọn từ Có/Không:** 87,6% với luật Verbalize; theo phong cách từng bảng còn thấp hơn (84,0%), tức
  đây là nhiễu chứ không phải quy ước theo bảng. Loại câu này mất ≈ 2,4 điểm EM gần như chắc chắn.
- **Oracle ứng viên hiện có:** 86,9 trên dev-200 (5 lời giải độc lập); vote đạt 82,9.

Ước lượng này ngụ ý: kể cả hệ hoàn hảo về đọc bảng cũng khó vượt ~90–91 EM; một hệ < 10B thực tế
nên nhắm 86–88.

## 2. Vì sao prompt đã bão hoà

Từ tài liệu 2026-09-26: FS 71,5 → bộ nhớ cùng bảng 79,4 → nhiều mẫu/view + vote 81,5 → đối chất
82,5 (test-200). Đối chất so với vote trên cùng mẫu: trung bình 4 lần đo = 0. Judge LLM đúng 2/10 và
0/6; verifier zero-shot có specificity 0,35; Memory-Curator và Parse-Critic không giúp. Nghĩa là thêm
vai LLM không huấn luyện không còn chỗ để lấy thêm điểm; khoảng trống oracle–vote (~4 điểm) chỉ lấy
được bằng một bộ chọn **đã học** tín hiệu đúng/sai.

## 3. Đề xuất: MemXam-T (multi-agent có vai huấn luyện)

| Vai | Hiện thực | Dữ liệu huấn luyện | Loại |
|---|---|---|---|
| Memory | Truy hồi Jaccard k = 8–16 câu train cùng bảng (giữ nguyên, đã chứng minh hiệu quả) | — | tất định |
| **Solver A** | Qwen3-8B + LoRA, view Flatten V1, không thinking sau SFT (đầu ra ngắn, nhanh) | 7.928 câu train, bộ nhớ **leave-one-out** (loại chính câu đó và các câu Jaccard ≥ 0,8) | LLM đã SFT |
| **Solver B** | Khác backbone < 10B (vd. Llama-3.1-8B hoặc SEA-LION v3 8B) hoặc cùng Qwen3-8B nhưng view Markdown-KV + bằng chứng | như trên | LLM đã SFT |
| **Verifier** | Qwen3-8B + LoRA chấm (câu hỏi, bảng, bộ nhớ, ứng viên) → P(đúng) | Ứng viên do Solver A/B sinh trên train (K = 8 mẫu/câu, fold chéo để tránh học thuộc), nhãn = EM với gold | LLM đã SFT (hoặc cross-encoder PhoBERT làm nhánh rẻ) |
| Kiểm tra | Luật loại đáp án rỗng/sai loại (giữ nguyên) | — | tất định |
| Phản hồi | Nếu verifier loại mọi ứng viên: gửi nhận xét của verifier về solver để sinh lại một lần | — | tương tác |

Luồng: A, B sinh K mẫu → Kiểm tra → Verifier chấm từng ứng viên khác nhau → chọn ứng viên điểm
cao nhất (hoà thì theo số phiếu) → nếu mọi điểm < ngưỡng thì một vòng phản hồi verifier → solver.
Tương tác thật nằm ở vòng generator ↔ verifier (kiểu MALT: generator / verifier / refiner được huấn
luyện riêng), và được ablation bằng cách thay verifier bằng vote cùng mẫu.

Vì sao kỳ vọng vượt được mức hiện tại:
- SFT với bộ nhớ cùng bảng dạy trực tiếp cách viết đáp án của người gán nhãn (nguồn lỗi lớn nhất của
  FS), và cho phép tắt thinking (giảm ~10 lần token sinh, bớt lỗi cắt thinking).
- Verifier đã học có tín hiệu thật về đúng/sai, nhắm vào khoảng trống oracle–vote ~4 điểm; MATA
  dùng bộ chọn nhỏ đã train và báo cáo lợi rõ ở 3–8B.
- Hai backbone khác nhau làm lỗi ít tương quan hơn (phân tích 2026-09-26 §4.2: thêm backbone khác mở
  thêm +4,3 điểm trần oracle).

## 4. Kế hoạch thực nghiệm và cổng quyết định

| Bước | Việc | Cổng để đi tiếp | Chi phí ước tính |
|---|---|---|---|
| 0 | Huấn luyện ViNLI 3 nhãn; đo trần BIF; chuẩn bị test đủ 992 câu, ≥ 3 lần chạy, KTC ghép cặp | — | Kaggle (miễn phí) |
| 1 | SFT Solver A (QLoRA r = 16, 2–3 epoch, bộ nhớ leave-one-out) | dev-200 ≥ kNN-SC3 + 3 EM (≥ ~85) | A100 ~2–4 giờ (~$1,5–3) |
| 2 | SFT Solver B (backbone thứ hai hoặc view KV) | tương quan lỗi A–B thấp hơn cặp prompt-only; oracle {A,B} ≥ 90 | ~$1,5–3 |
| 3 | Sinh K = 8 mẫu trên train (fold chéo), huấn luyện Verifier | trên fold giữ lại: specificity ≥ 0,8 tại recall ≥ 0,9; dev: verifier − vote ≥ +2 EM | ~$2–4 |
| 4 | Vòng phản hồi verifier → solver | sửa/phá ≥ 3:1 trên câu bị kích hoạt | nhỏ |
| 5 | Test đủ 992 câu, 3 lần chạy: FS, kNN-SC3, vote cùng mẫu, MemXam-T, ablation từng vai | — | ~$2 |
| (6) | GRPO với phần thưởng EM cho Solver A (kiểu Table-R1) nếu bước 1 chưa đạt cổng | +2 EM so với SFT | ~$5–10 |

Tổng cỡ $10–20 thuê A100 (giá Vast ~$0,60/giờ quan sát được ngày 2026-09-27), hoặc chậm hơn nhưng
miễn phí trên Kaggle 2×T4 cho SFT/QLoRA.

## 5. Rủi ro

- **Rò rỉ:** bộ nhớ lấy từ train, và SFT cũng học trên train. Phải dùng bộ nhớ leave-one-out khi
  huấn luyện, loại câu "sinh đôi" (Jaccard ≥ 0,8), và báo EM-twin như hiện tại.
- **Học thuộc nhiễu nhãn:** SFT có thể khớp cả những gold không nhất quán; theo dõi dev, dừng sớm.
- **Verifier học lối tắt** (vd. ưa đáp án ngắn): kiểm tra theo loại câu hỏi và báo độ chính xác có
  điều kiện (sửa/phá) như bài học Headroom.
- **Phạm vi áp dụng:** cả bộ nhớ lẫn SFT dựa vào việc bảng test có câu hỏi train; phải nói rõ không
  tổng quát sang bảng chưa từng thấy.
- **Chính sách:** fine-tune cần GVHD cho phép (quyết định #6 trong các tài liệu trước).

## 6. Nếu không được fine-tune

Chỉ còn các đòn bẩy prompt, vốn đã bão hoà: kỳ vọng tối đa ~83–84 EM (vd. thêm backbone < 10B khác
vào pool rồi vote, tăng số mẫu SC). Khi đó nên đổi mục tiêu thành EM ≥ 83 và BIF ≥ 80 (4 nhãn), và
đóng khung đóng góp là bộ nhớ cùng bảng cộng đa dạng mẫu/view.

## 7. Cập nhật: người dùng không muốn huấn luyện model

Các phép đo bổ sung (2026-09-27), đều không huấn luyện:

- **Backbone < 10B mới hơn không giúp.** `qwen/qwen3.5-9b` qua OpenRouter (provider Venice, không
  ghim), dev-200: FS 64,0 và kNN16-FS 74,4 EM, so với Qwen3-8B 73,3 (TB 3 lần) và 80,0. Chi phí $0,28.
- **Trần của bước chọn khi không huấn luyện:** oracle của pool ứng viên MemXam-SC (3 mẫu A + B + đáp án
  sau đối chất) là 86,5 / 86,9 (dev v6 / v7) và 86,0 / 86,4 (test v6 / v7). Kể cả bộ chọn hoàn hảo
  cũng chỉ đạt ~86–87 EM, nên **EM 90 không đạt được nếu không huấn luyện**.
- **Bộ chọn tất định ưu tiên đáp án khớp nguyên văn một ô bảng** (cộng w vào số phiếu), tính offline
  trên pool đã lưu:

  | Pool | Vote | w = 0,5 | w = 1,5 |
  |---|---:|---:|---:|
  | dev v6 | 81,5 | 81,5 | 81,0 |
  | dev v7 | 82,9 | 83,4 | 83,4 |
  | test v6 | 81,5 | 82,0 | 82,5 |
  | test v7 | 79,9 | 80,4 | 81,9 |

  Cùng chiều nhưng nhỏ (+0 đến +2), cỡ nhiễu giữa các lần chạy; nếu dùng thì chốt w = 0,5 trước khi
  chạy test mới.

Mục tiêu thực tế trong ràng buộc (< 10B, multi-agent, không huấn luyện): **EM ~83–85, BIF ~81 (4
nhãn) / ~85 (3 nhãn, xấp xỉ)**. Hướng đi: giữ MemXam-SC, tăng đa dạng ứng viên từ cùng backbone
(ba view Flatten / lưới / Markdown-KV, mỗi view có memory và lấy mẫu) để nâng oracle, chọn bằng vote
cộng ưu tiên khớp ô; tuỳ chọn một bộ chọn logistic regression nhỏ trên đặc trưng (không huấn luyện
LLM; pilot cũ trong repo cho +0,4 đến +1,4 so với vote).

### 7.1 Ngôn ngữ prompt và ghi chú định dạng bảng

Qwen3-8B qua OpenRouter (provider Alibaba ghim qua `VLLM_EXTRA_BODY`), dev-200, ba arm chạy cùng
phiên, so ghép cặp với kNN16-FS tiếng Việt gốc (82,0 EM):

| Prompt | EM | Hiệu [KTC 95%] | Thắng/thua |
|---|---:|---:|---:|
| Tiếng Anh, dịch sát + "Write final_answer in Vietnamese, in exactly the same style as the example answers below" (bảng, câu hỏi, đáp án mẫu giữ tiếng Việt) | 79,29 (198 câu) | −2,53 [−6,06; +0,51] | 3/8 |
| Tiếng Việt, sửa ghi chú định dạng | 80,00 | −2,00 [−6,00; +1,50] | 5/9 |

Ghi chú định dạng gốc (có từ prompt baseline `v3_fs_structured_vi`) mô tả Flatten V1 là bộ ba
`tiêu_đề_hàng|tiêu_đề_cột|giá_trị`, nhưng 143/145 bảng của subset dev thực tế là lưới (dòng đầu là
tên cột có `<header>`, mỗi dòng sau là một hàng; 43 bảng có ô đầu hàng mang `<header>`). Sửa ghi chú
cho đúng không cải thiện. Bản tiếng Anh vẫn trả lời bằng tiếng Việt; phần thua chủ yếu là lệch cách
viết so với đáp án mẫu. Kết luận: giữ prompt tiếng Việt gốc.
