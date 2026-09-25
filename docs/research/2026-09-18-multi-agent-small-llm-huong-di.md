# Hướng đi cho Table QA trên Open-ViTabQA với LLM dưới 10B: multi-agent nào thực sự có bằng chứng

Ngày: 2026-09-18. Phạm vi: tra cứu bên ngoài (arXiv/alphaXiv, Consensus, blog kỹ
thuật, leaderboard SEA-HELM, OpenRouter API) cộng với **đo trực tiếp trên
`qas_test.json` và `table.json`** của Open-ViTabQA, để trả lời một câu hỏi: với
backbone mở dưới 10B, dạng multi-agent nào cho Table QA tiếng Việt là có bằng
chứng, và thí nghiệm nào chứng minh được điều đó. Tài liệu này nối tiếp
[`2026-09-18-vietnamese-table-qa-methods-spec.md`](2026-09-18-vietnamese-table-qa-methods-spec.md)
(kinh nghiệm và điểm yếu của ViPanelTR/POMA),
[`2026-09-18-answer-normalization-gsa-score-gap.md`](2026-09-18-answer-normalization-gsa-score-gap.md)
(phân tích code-level của AN/GSA) và
[`2026-09-17-table-representation-small-lm.md`](2026-09-17-table-representation-small-lm.md)
(biểu diễn/rút gọn bảng). Năm báo cáo chi tiết theo từng mảng nằm trong thư mục
[`2026-09-18-supporting/`](2026-09-18-supporting/).

## Tóm tắt

Kết quả trung tâm: **multi-agent kiểu nhiều persona trên cùng một backbone dưới
10B không thể hoạt động, và lý do đã được chứng minh chứ không phải suy đoán.**
Ablation 0.27–0.56 F1 của ViPanelTR và ~1.27 EM của POMA không phải là kết quả
đáng thất vọng — chúng là *kết quả được dự đoán trước* bởi một định lý đã công bố.

Ba hệ quả kéo theo, mỗi hệ quả đổi cách đọc một phần của bản thảo JIT:

1. Phần đóng góp của orchestration (1.27 EM) **nằm dưới ngưỡng phân giải** của
   bộ test 992 câu. Điều này vừa biến nó thành một kết quả âm hợp lệ, vừa
   **vô hiệu hoá** kết luận ở §5.3 rằng orchestration làm hại answerability.
2. Answer normalization không phải "mẹo bề mặt" mà **chính là hàm tổng hợp**
   của bất kỳ cơ chế bỏ phiếu nào trên không gian đáp án tự do. Đây là cách
   đóng khung trung thực cho NX4 mà không phải thừa nhận contribution là rỗng.
3. Chẩn đoán về abstention trong spec bị **đảo ngược**: POMA phát `Null` quá
   nhiều chứ không phải quá ít, nên thêm verifier/abstain-vote là đi sai hướng.

Ba trục còn sống, xếp theo độ mạnh bằng chứng: **bỏ phiếu thay vì thảo luận**;
**dị thể về góc nhìn hoặc về backbone** (có cổng kiểm tra trước); và **kênh cấu
trúc/thực thi như một *bộ định vị*, không phải một persona**.

## 0. Số liệu đo trực tiếp trên dataset — ràng buộc mọi hướng đi

Các số dưới đây đo từ file gốc trong repo Open-ViTabQA, không lấy từ paper.
Chúng mâu thuẫn với vài con số đang dùng trong bản thảo, nên phải sửa trước.

| Đại lượng | Bản thảo/spec ghi | **Đo thật** |
|---|---|---|
| Câu hỏi unanswerable (test) | ~10% | **45/992 = 4.5%** (train 346/7.928 = 4.4%) |
| Số nhãn hint mỗi câu | ngụ ý "parallel" | **903 câu (91.0%) chỉ 1 nhãn**; 86 câu 2 nhãn; 3 câu 3 nhãn → **trung bình ~1.10** |
| Kích thước bảng | — | p50 ≈ **647 token**, p90 ≈ 2.097, max ≈ 19.284 |
| Đáp án là bản sao nguyên một ô | — | **42.3%** (đo lại độc lập bằng grid span-aware: 43.2%) |
| Phân tầng `table_type` (test) | 3 chiều | **4 chiều**: normal 461 / merged_value 262 / merged_header 143 / **cả hai 126** |

Bốn hệ quả trực tiếp:

- **`table_type` là đa nhãn.** Báo cáo 3 chiều thì hoặc đếm trùng 126 câu, hoặc
  che mất tương tác. Cả ViPanelTR (84.25 vs 75–78 F1) lẫn POMA (83.51/80.42/75.95
  EM) đều không nói rõ dùng quy ước nào — nếu là 3 chiều thì ô merged_header và
  merged_value của cả hai bài đều âm thầm chứa 126 câu "cả hai". **Phải xác định
  quy ước trước khi so sánh hai bài với nhau.**
- **Bảng rất nhỏ.** Với p50 ≈ 647 token, các phương pháp giải bài toán "context
  length" (TableRAG, TabSQLify, TableZoomer, DataFactory) đang giải sai bài toán
  cho ~90% dữ liệu này. Khuyến nghị selector BM25 trong
  [tài liệu biểu diễn bảng](2026-09-17-table-representation-small-lm.md) chỉ cần
  cho phần đuôi phân phối.
- **"Parallel specialists" hầu như không song song.** Router của POMA gần như
  luôn kích hoạt đúng một specialist. Đây chính là thống kê mà reviewer đòi ở
  NX2, và nó không ủng hộ chữ "Parallel" trong tiêu đề bài.
- **Trần extractive ~43%.** Phần còn lại là tính toán, Yes/No, tổng hợp đa ô,
  liệt kê. Lợi ích kỳ vọng của một kênh SQL/PoT bị chặn trên bởi con số này, và
  tầng merged_value còn tệ nhất (32.8%). Trong 195 câu "Sử dụng tính toán", có
  48.2% đáp án **đã có sẵn** trong bảng, tức không cần số học thật.

Một chênh lệch nhỏ cần ghi nhận: đếm chính xác chỉ có **45** đáp án `Null` (duy
nhất một biến thể chuỗi, không có `null`/`NULL`/rỗng), trong khi bản thảo POMA
ghi 46. Tài liệu này dùng 45.

## 1. Cơ chế: vì sao nhiều persona trên một backbone 8B không thể hoạt động

[Choi, Zhu & Li, *Debate or Vote: Which Yields Better Decisions in Multi-Agent
LLMs?*, NeurIPS 2025](https://arxiv.org/abs/2508.17536) chạy đúng lớp backbone
của chúng ta và giữ cố định ensemble (Majority Voting được định nghĩa là debate
với T=0 trên cùng N=5 agent), chỉ thay đổi số vòng tương tác:

| Backbone | Single agent | Debate tốt nhất | **Majority Voting** |
|---|---:|---:|---:|
| Qwen2.5-7B-Instruct (TB 7 benchmark) | 0.7205 | 0.7377 | **0.7691** |
| Llama3.1-8B-Instruct | 0.6203 | 0.6990 | **0.7242** |
| Qwen2.5-7B, riêng nhóm số học | — | 0.8400 | **0.9900** |

Kèm chứng minh (Theorem 2): dưới mô hình niềm tin Dirichlet-Compound-Multinomial,
debate tạo ra một **martingale** trên niềm tin của từng agent vào đáp án đúng —
`E[p_{i,t} | α_{t-1}] = p_{i,t-1}`. Nguyên văn: *"debate itself does not
systematically improve or degrade an agent's belief on average."* Xác nhận thực
nghiệm: độ chính xác trung bình của agent phẳng qua cả 5 vòng.

Một số liệu nữa liên quan trực tiếp tới thành phần GSA: **judge/aggregator tập
trung còn có hại** trên Llama — 0.6094 → 0.6053 → **0.5670** ở T=2/3/5, tức
*thấp hơn cả single agent*.

Ở 8B, phương sai của martingale không trung tính mà **bất lợi**, vì model nhỏ sau
RLHF rất theo đám đông. [Bertalanič & Fortuna](https://arxiv.org/abs/2605.00914)
chạy N=10 agent đồng nhất trên Qwen2.5-7B / Llama-3.1-8B / Ministral-3-8B — đúng
cấu hình POMA — và đo: **sycophancy tới 85.5%**, tỉ lệ lật đúng→sai tới 70.0%,
**oracle gap 32.3 pp** (đáp án đúng có trong pool nhưng bị plurality vote loại).
Consensus tăng lên 90.1% trong khi độ chính xác giảm. Đáng chú ý nhất là
**nhóm đối chứng nhiễu**: tiêm rationale *không liên quan* cho ra 63.2% trên
GSM-Hard, cao hơn cả debate (58.8%) — nghĩa là phần lợi ích quy cho "thảo luận"
có thể tái tạo được bằng việc prompt lại, không phải bằng cộng tác.

[Zhang et al.](https://arxiv.org/abs/2502.08788) chuẩn hoá 5 framework MAD về
~6 lượt gọi trên 9 benchmark × 4 model (có Llama3.1-8B): **không framework nào
đạt tỉ lệ thắng >20% so với CoT thường** theo ANOVA ở p<0.05; Multi-Persona đạt
0%. Nguyên văn: *"In most cases when SC can be applied, SC achieves the highest
performance, defeating CoT, not to mention MAD methods."*

Còn [Huang et al., ICLR 2024](https://arxiv.org/abs/2310.01798) — bài thường bị
trích sai — thực ra **chỉ giới hạn ở self-correction *nội tại*** và bản thân bài
ủng hộ phản hồi từ bên ngoài. Model nhỏ nhất họ thử là Llama-2-70B, nên "8B không
tự sửa được" là ngoại suy, tuy là ngoại suy đơn điệu (GPT-4-Turbo 91.5→90.0;
Llama-2-70B 62.0→**36.5**). Số dùng được cho chúng ta là Table 7, so ở cùng ngân
sách: **MAD 83.0 vs self-consistency 88.2** với 9 phản hồi.

**Kết luận mục này.** ViPanelTR và POMA đều là cấu hình agent đồng nhất, cùng
backbone, cùng chuỗi Flatten V1. Năm nghiên cứu độc lập ở 7–8B đều kết luận cấu
hình đó tốt nhất là ngang, thường là thua, so với lấy mẫu cùng model K lần rồi
vote. Ablation nhỏ của hai bài là **sự triệt tiêu** giữa phần debate sửa đúng và
phần debate làm hỏng — [nghiên cứu của AWS](https://arxiv.org/abs/2605.09618)
phân rã cụ thể trên Llama/MuSiQue: debate đúng riêng ở 13.7% câu và **làm hỏng
một đáp án vốn đúng ở 12.3%** câu.

## 2. Ngưỡng phân giải: bộ test 992 câu không đo được hiệu ứng đang bàn

Với n=992 và độ chính xác ≈67%, sai số chuẩn một nhánh là **1.49 pp**. So sánh
hai nhánh như hai tỉ lệ độc lập, hiệu ứng nhỏ nhất phát hiện được ở power 80%,
α=0.05 hai phía là `(1.96+0.84)·√2·1.49 ≈` **5.9 pp**.

| Đại lượng | Giá trị | Có đo được không? |
|---|---:|---|
| Tổng cải thiện POMA vs few-shot | +13.10 EM | Có (≫ 5.9 pp) |
| Phần orchestration (sau khi trừ AN) | **+1.27 EM** | **Không** |
| Ablation self-review / peer deliberation (ViPanelTR) | 0.27–0.56 F1 | **Không** |

Với lớp Unanswerable còn nặng hơn: n=45 cho sai số chuẩn tối đa 7.45 pp, tức
**CI 95% rộng ±14.6 pp**. Chênh lệch POMA 51.13 vs few-shot 56.64 là **5.51 pp**
— nằm sâu trong nhiễu. Nghĩa là khẳng định ở §5.3 rằng orchestration làm hại
answerability **không được dữ liệu ủng hộ**; nó cũng không bị bác bỏ, đơn giản là
chưa đo được.

Hai việc bắt buộc từ đây. Thứ nhất, **mọi ablation phải ghép cặp** — cùng câu
hỏi, cùng seed, McNemar exact hoặc paired bootstrap theo item; với tỉ lệ bất đồng
d thì MDE ≈ `2.8·√(d/n)`, ở d=0.15 là 3.4 pp, ở d=0.08 là 2.5 pp. Để phân giải
1.27 điểm cần d dưới ~2%, điều mà không một thay đổi kiến trúc đắt gấp 3.5× nào
tạo ra. Thứ hai, với các lát cắt theo đặc trưng cấu trúc, **kéo mẫu từ
train+dev** — pipeline là prompt-only nên không rò rỉ gì: lát C∪E có **979 câu**
ở train+dev thay vì 116 ở test.

Phát biểu "phần cải thiện nhờ orchestration nằm dưới ngưỡng phân giải của phép
đánh giá" là một kết quả âm hợp lệ, trích dẫn được, và **mạnh hơn một kết quả
dương yếu**.

## 3. Answer normalization là hàm tổng hợp, không phải mẹo

Toàn bộ bằng chứng self-consistency ở mục 1 đến từ **không gian đáp án nhỏ**.
Chen et al. tự giới hạn phạm vi ở *"tasks with a fairly small number of possible
responses (e.g., multiple-choice questions) that support a majority vote"*, còn
Li et al. phải thay exact-match voting bằng tương đồng BLEU cho sinh mở.

Table QA tiếng Việt có không gian đáp án tự do. **Hai đáp án đúng ở hai hình thức
bề mặt khác nhau không bỏ phiếu chung được** — chúng chỉ gộp *qua normalizer*.
Vậy lợi ích của self-consistency không độc lập với normalization mà là **một hàm
của nó**. Đây chính là lý giải cơ chế cho việc AN đáng 11.83 EM ở POMA, và nó cho
phép đóng khung lại contribution mà không phải thừa nhận là rỗng.

Có tiền lệ ngoài để trích: Appendix F của Choi et al. đo cùng một model cho
**0.8713 hoặc 0.6620** trên GSM8K *chỉ tuỳ theo bộ trích xuất đáp án*, và kết
luận rằng lựa chọn extractor *"can significantly affect measured performance —
sometimes even reversing conclusions."* Cùng hiện tượng, đã được công bố ở một
venue hạng nhất.

Cảnh báo kèm theo khi đọc số của người khác: Weaver dùng **REM (Relaxed Exact
Match)** — để một LLM chuẩn hoá prediction về định dạng gold *rồi mới* exact
match (gold "17 years", pred "17" → tự thêm đơn vị → tính là đúng). TableLLM chấm
WikiTQ 89.10 bằng DeepSeek-V3 cho điểm 1–10 với ngưỡng 7. **Không con số nào
trong hai bài đó so sánh được với EM thô.**

## 4. Abstention: chẩn đoán trong spec bị đảo ngược

Tái dựng ma trận nhầm lẫn lớp `Null` của POMA từ các số đã có (946 answerable,
46 unanswerable, 53 false abstention, 11 hallucination — tổng 992 khớp):

| | dự đoán `Null` | dự đoán có đáp án |
|---|---:|---:|
| **gold `Null`** (46) | TP = 35 | FN = 11 |
| **gold answerable** (946) | FP = 53 | TN = 893 |

→ **precision 39.8%, recall 76.1%, F1 52.2%** (khớp 51.13 báo cáo; chênh lệch
1.1 điểm phù hợp với partial credit của char-F1, nên tái dựng là đúng). Dùng con
số gold thật 45 thay vì 46 thì ra P 39.1% / R 75.6% / F1 51.5% — kết luận không đổi.

**Hệ thống phát `Null` 88 lần trong khi gold chỉ 45–46, tức bội số ~1.9×. Nút
thắt là precision (39.8%), không phải recall (76.1%).** Con số "4.8×" trong spec
là tỉ lệ *đếm thô* dưới mất cân bằng 20:1, không phải tỉ lệ *chi phí*; chuẩn hoá
lại thì false abstention là 5.6% còn hallucination là 23.9%.

Giết false positive là nước đi **duy nhất nâng được cả hai F1 cùng lúc**:

| Số FP loại bỏ (trên 53) | Null-F1 |
|---:|---:|
| 10 | 56.5 |
| 20 | 61.4 |
| 30 | 67.3 |
| 53 (toàn bộ) | **86.4** |

Điều này đảo ngược phản xạ tự nhiên là "thêm một verifier để abstain mạnh hơn".
Hai bằng chứng độc lập nói thẳng rằng làm vậy sẽ hại:

- [GRAB-RAG](https://arxiv.org/abs/2608.22228) chạy **đúng lớp model của chúng
  ta** (Phi-4-mini 3.8B, Llama-3.1-8B, Qwen2.5-7B): thêm verifier kiểm tra xung
  đột phía generator giảm câu trả lời sai xuống 13.3% **nhưng đẩy False Abstention
  Cost lên 49.8%** — bỏ mất gần nửa số câu vốn trả lời được. Cổng "≥3/5 role vote
  unsupported" của ViPanelTR **là cùng một hình dạng**.
- [Slobodkin et al.](https://arxiv.org/abs/2310.11877) định lượng đánh đổi của
  chỉ thị abstention: thêm hint nâng unanswerable-F1 tới +80 điểm nhưng **tốn
  −8.3 F1 / −7.1 EM trên câu answerable**. Nếu prompt của POMA (nhiều vai, mỗi
  vai có thể mang một câu "trả `Null` nếu không chắc") nhấn hint mạnh hơn
  few-shot, **riêng điều đó có thể giải thích toàn bộ 53 FP**.

Một phát hiện ngược lại của GRAB-RAG thì đáng mừng: khi bằng chứng **đơn giản là
thiếu**, các model này abstain rất đáng tin (≤1% trả lời sai). `Null` của
Open-ViTabQA nhiều khả năng thuộc loại thiếu-bằng-chứng, nên tỉ lệ miss 24% của
POMA có vẻ là **lỗi orchestration chứ không phải giới hạn năng lực model** —
nhất quán với việc few-shot thắng POMA ở lớp này.

Hai cổng triển khai đã kiểm chứng live trên OpenRouter: `qwen/qwen3-8b` trả
**`logprobs: false`** và **không phơi `structured_outputs`** (chỉ có
`response_format`). Mọi phương pháp cần xác suất token — semantic entropy liên
tục, sequence log-prob, P(True) đã hiệu chỉnh — **chết trên backbone chính** trừ
khi tự host bằng vLLM (tự host cho cả logprobs lẫn hidden states). Semantic
entropy còn có vấn đề thứ hai: nó đọc trục *correctness*, mà trên trục
*answerability* một nghiên cứu 2B–14B chỉ đo được AUROC 0.54–0.67. Đúng bài, sai
trục — dùng nó làm chẩn đoán trên tập 53 FP, không làm cổng quyết định.

## 5. Ba trục còn sống, kèm thí nghiệm chứng minh

Xếp theo độ mạnh bằng chứng. Chi phí tính theo giá OpenRouter live: Qwen3-8B
khoảng **$0.19–0.30 cho cả 992 câu** một lượt — ngân sách **không phải ràng
buộc**, nên chọn theo khoa học chứ không theo giá.

### Thí nghiệm #0 — miễn phí, làm trước tất cả

Diff độ mạnh của chỉ thị abstention giữa prompt POMA và prompt few-shot. Không
tốn một lượt gọi LLM nào, mất khoảng một giờ, và theo Slobodkin có thể giải thích
trọn vẹn khoảng cách 53 FP. Kèm theo: trích ma trận nhầm lẫn `Null` của chính
few-shot baseline từ file prediction có sẵn — F1 56.64 của nó đến từ precision
tốt hơn hay recall tốt hơn sẽ quyết định toàn bộ hướng sửa.

### Trục 1 (bằng chứng mạnh nhất) — thay thảo luận bằng bỏ phiếu, và *đo* K

Bỏ toàn bộ self-review/peer-deliberation, thay bằng self-consistency ở cùng ngân
sách token, với K được dò chứ không giả định. [Li et al. (TMLR 2024)](https://arxiv.org/abs/2402.05120)
cho thấy lợi ích ensemble **tăng khi model yếu đi và bài toán khó lên**
(Llama2-13B +69% tương đối trên GSM8K, +200% trên MATH, so với +16%/+34% của
GPT-3.5) — chúng ta đang ở đúng vùng ensemble trả giá nhất. Chen et al. chứng
minh đường cong theo K **không đơn điệu** và cho thủ tục ước lượng K* từ ~100
mẫu dev.

**Ablation.** Quét K ∈ {1,3,5,10} **bắt chéo với hai mức mạnh của normalizer**.
Đây là tương tác không tìm thấy trong tài liệu nào, và nó chính là cách biến mục
3 thành một đóng góp đo được: nếu đường cong SC phẳng dưới normalizer yếu và dốc
dưới normalizer mạnh, bạn đã chứng minh normalizer là hàm tổng hợp. Báo cáo delta
ghép cặp, CI bootstrap 95% theo item, p của McNemar, số bất đồng (b, c), **và
tổng token sinh ra**. Thêm hai nhánh đối chứng mà hầu hết bài MAD bỏ qua: **đối
chứng nhiễu** của Bertalanič và **đối chứng extractor** của Choi. Chi phí: K=10
≈ $3, K=5 ≈ $1.50.

### Trục 2 — dị thể, nhưng phải qua cổng đo tương quan lỗi trước

Đây là kết quả dương duy nhất trong toàn bộ tài liệu MAD: Zhang et al. gọi
**model heterogeneity** là *"a universal antidote"*, cải thiện SoM **+6.4%** và
EoT **+8.2%**, và cơ chế nằm gần như trọn vẹn ở các câu mà model này giải được
còn model kia thì không. Framework *đơn giản* hưởng lợi **nhiều hơn** framework
phức tạp — trực tiếp ủng hộ việc rút gọn POMA thay vì làm phức tạp thêm.

**Cảnh báo phải nêu:** mọi kết quả heterogeneity đã công bố đều là **cross-tier**
(Zhang ghép gpt-4o-mini với Llama-**70B**). **Không có bằng chứng decorrelation ở
cùng cỡ 8B.** Nên trước khi xây ensemble, chạy một phép đo rẻ: hai backbone trên
cùng 992 câu, tính tỉ lệ bất đồng và **oracle-of-2**. Nếu oracle-of-2 không vượt
max(A,B) đủ nhiều thì trục này chết và bạn đã tiết kiệm được cả tháng.

Hai dạng dị thể, theo thứ tự rủi ro:

**(a) Dị thể *miễn phí* về góc nhìn — chuyển vị bảng stub.** Sau khi sửa lại quy
kết của [AIT-QA](https://arxiv.org/abs/2106.12944), đây là **can thiệp đơn lẻ có
bằng chứng tốt nhất** trong toàn bộ khảo sát: **+11.3 pp** (RCI 40.58 → 51.84),
peer-reviewed, được cô lập, **không tốn thêm token**. Lưu ý quan trọng: phần
"flatten header" là *base transformation* áp cho cả ba điều kiện, nên +11.3 pp
**thuộc về chuyển vị**, không phải về nối chuỗi header — AIT-QA không cung cấp
bằng chứng cô lập nào cho header-path. Và nó **phụ thuộc model** (giúp RCI, *hại*
TaPas 49.32 → 46.80) — đúng tính chất cần có ở một view thứ hai. Dữ liệu của
chúng ta có **57 bảng stub / 1.377 câu train+dev** để đo.

**(b) Dị thể về backbone.** Theo SEA-HELM (dữ liệu 2026-09-18, 58 model, có CI
95%), cột tiếng Việt:

| Model | VI (95% CI) |
|---|---|
| Qwen 3.5 9B | 71.93 [70.42, 73.42] |
| **Qwen3-8B** (đang dùng) | 68.17 [66.54, 69.80] |
| Gemma 4 E4B (8B total / 4.5B effective) | 67.14 [65.36, 68.99] |
| SEA-LION v3 (Gemma2) 9B | 63.82 |
| Llama-3.1-8B | 44.63 [42.62, 46.66] |
| **SEA-LION v4 8B** (Apertus) | **39.96** |

**SEA-LION 8B không nên vào shortlist** — model dense sub-10B duy nhất của dòng
v4 đạt VI 39.96, *thua cả Llama-3.1-8B*; base Apertus-8B ở 34.46 nên nhãn "SEA"
gần như không mua được gì. Các dòng v4.5/v4.8 hiện tại là 27B–120B, vượt ràng
buộc. **SeaLLMs v3 cũng loại**: tokenizer trùng byte-for-byte với Qwen3-8B
(vocab 151.643) vì là dẫn xuất Qwen2 — không thể biện hộ là một backbone khác.
Các model Việt chuyên biệt (PhoGPT-4B, Vistral-7B, VinaLLaMA, Arcee-VyLinh) đều
cũ hoặc là dẫn xuất Qwen, không có mặt trên SEA-HELM lẫn OpenRouter.

Khuyến nghị: **`google/gemma-4-E4B-it`** — Apache-2.0, 128k context, khác lab,
khác corpus, khác tokenizer (262k vs 151k), khác kiến trúc, mà **CI tiếng Việt
chồng lấn với Qwen3-8B**. Đây là lý do **Llama-3.1-8B là lựa chọn sai** dù hiển
nhiên: ở VI 44.63, mọi chênh lệch sẽ quy về model chứ không phải pipeline. Còn
Qwen3.5-9B chỉ là *version control*, không phải *generalization control* —
reviewer đòi generalization sẽ không chấp nhận thêm một con Qwen. Hai việc phải
thông trước: máy hiện tại là Windows 11 Home (vLLM cần WSL2 + GPU NVIDIA) và
`transformers 4.57.1` chưa load được config Gemma-4.

Giao thức công bằng bắt buộc: cùng chuỗi bảng đã cache, **tắt thinking ở cả hai**
cho bảng headline (Qwen3-8B vẫn là checkpoint hybrid nên `enable_thinking` là một
confound thật), **dùng chung một bộ sampling param cố định** thay vì "khuyến
nghị" của từng hãng, cùng một evaluator với một phép chuẩn hoá tiếng Việt, và
**báo cáo tỉ lệ parse-failure theo từng backbone như một số hạng nhất**.

### Trục 3 — kênh cấu trúc/thực thi như một *bộ định vị*, không phải một persona

Đây là chỗ đặt "heterogeneous evidence", nhưng phải đặt đúng hình dạng. Bằng
chứng ủng hộ:

- [TAT-LLM](https://arxiv.org/abs/2401.13223) ablate bỏ External Executor (code
  **tất định**, 0 lượt gọi LLM): **7B mất −16.66 / −17.80 / −16.54 EM** trên
  FinQA / TAT-QA / TAT-DQA, trong khi **70B chỉ mất −6.71 / −4.81 / −4.81**. Giá
  trị của việc đưa tính toán ra khỏi đầu LLM **giảm đơn điệu theo scale** — bằng
  chứng sạch nhất rằng hướng này đáng giá nhất đúng ở ràng buộc <10B. Có thể lấy
  nguyên Algorithm 1 làm post-processor cho *bất kỳ* agent nào, không cần train:
  equation hợp lệ → `eval`; chứa `#` → đếm; chứa `>`/`<` → `eval`; `N.A.` → quay
  về span đã trích.
- [TABVERSE](https://arxiv.org/abs/2606.09578) (có Qwen2.5-7B, TableGPT2-7B,
  Qwen3-VL-8B) cho thấy format chỉ đáng ~1–3 pp trên QA EM ở 8B **và thứ hạng
  HTML/Markdown lật giữa hai model 7B khác nhau** — nhưng gắn thẻ cấu trúc tường
  minh đáng **10–20 pp trên các tác vụ *dò* cấu trúc** (Qwen2.5-7B table-partition:
  HTML 16.7 vs Markdown 5.9; cell-lookup 25.4 vs 8.1). Đây là luận cứ mạnh nhất
  cho thiết kế: **một view gắn thẻ cấu trúc giúp *định vị*, một view trôi chảy
  giúp *trả lời*.**
- [ASTRA](https://arxiv.org/abs/2604.08999) đo riêng ở sub-10B: chỉ đổi biểu diễn
  (Raw Table → Semantic Tree) cho Qwen3-8B non-thinking **52.75 → 60.86 (+8.11)**,
  thinking 54.97 → 64.92 (+9.95); Qwen2.5-7B +3.14; Llama3.1-8B +1.44.

Nhưng **ba cảnh báo độc lập chống lại việc dùng SQL thô làm một agent** trên
53.5% bảng merged của chúng ta:

1. [Mix Self-Consistency](https://arxiv.org/abs/2312.16702): khi chuyển vị bảng,
   **PyAgent sụp 55.91 → 12.45 (−77.73%)** trong khi Direct Prompting chỉ
   −14.05%. Suy luận symbolic mong manh với biến đổi cấu trúc gấp ~5 lần đọc text.
2. Weaver đo **tỉ lệ lỗi SQL 42.5%** ở GPT-4o-mini so với 15.0% ở GPT-4o, quy
   thẳng cho *"smaller model size"*.
3. Nhánh symbolic của ASTRA trên **Llama3.1-8B sụp còn 10.47%** (so với 40.45 của
   nhánh textual); bỏ vòng self-correction tốn **−12.67** trên Qwen3-8B. Kết luận
   của họ: tín hiệu thuần symbolic *"may be difficult to interpret reliably"* với
   model nhỏ.

Cộng thêm một cảnh báo về thiết kế từ [RSAT](https://arxiv.org/abs/2605.00199)
(Qwen2.5 1.5B/3B/7B, Llama-3 1B/3B/8B): **attribution hậu kiểm sụp đổ ở model
<8B** — chỉ 12.7% thành công định dạng trung bình, 0.4% với Qwen-3B, và *tệ hơn*
khi tăng scale trong cùng họ (Llama-8B 4.0%); lỗi là xuất rỗng hoặc không phải
JSON ở 76–100% số lần. **Tuyệt đối không thiết kế một agent thứ hai kiểu "giờ hãy
trích dẫn bằng chứng của bạn"** — citation phải được phát ra *trong* lượt trả lời.

**Thiết kế được bằng chứng ủng hộ**, do đó: giữ chuỗi phẳng nguyên vẹn và **nối
thêm một manifest cấu trúc ngắn** (~100–300 token, so với +121% của mã hoá
full-path): hình dạng bảng và độ sâu header; đường dẫn cột đầy đủ; đường dẫn
row-header cho bảng stub; bản đồ span; và — chưa ai thử cho decoder LLM — **rank
kiểu TAPAS dưới dạng text** (mỗi cột số, nhãn hàng argmax/argmin). Agent cấu trúc
xuất ra **một toạ độ ô hoặc một đường dẫn header**, agent phẳng mới phân giải.
Giữ hình dạng ngôn ngữ tự nhiên, **không** nặng code/toạ độ. Bắt buộc có fallback
cứng: toạ độ không hợp lệ → nhường cho agent phẳng.

**Và một đối chứng bắt buộc chạy trước:** "Flatten V2" — flat trung thực với span
(ở ô gốc ghi `[span rR cC]`, ở ô tiếp nối ghi `^` thay vì lặp lại chữ) cộng với
việc nhấc các hàng banner `colspan == ncols` lên thành dòng chú thích. Đây là
phương án **rẻ hơn** baseline (0.91× token) và xử lý đúng bệnh chính: 44 bảng có
banner, tệ nhất lặp **9.27×**. Không có đối chứng này thì mọi cải thiện về sau có
một phần chỉ là khử trùng lặp.

**Ablation cho cả trục:** EM/F1 theo **4 tầng** `table_type`, cộng lát cắt đặc
trưng lấy từ train+dev (C∪E 979 câu, stub 1.377 câu, banner 998 câu, td_rowspan
2.236 câu), McNemar theo từng lát. Báo cáo **độ chính xác toạ độ của agent cấu
trúc tách riêng** khỏi EM cuối — theo TABVERSE đó là chỗ tín hiệu nằm, và nó có
thể thành công ngay cả khi EM không nhúc nhích. Chi phí toàn chương trình ≈ $20–25.

## 6. Những mâu thuẫn đã phát hiện, ghi lại thay vì trích bừa

- **HiTab tự báo một kết quả âm quan trọng.** Baseline TaPas của
  [HiTab (ACL 2022)](https://arxiv.org/abs/2108.06712) tiền xử lý *đúng như*
  Flatten V1: *"we unmerge the cells spanning many rows/columns… and duplicate
  the contents into unmerged cells."* Tức **Flatten V1 chính là baseline mà HiTab
  thừa nhận là yếu**. Nhưng cách sửa của họ không phải một serialization khác mà
  là một *logical form* chọn vùng, và họ ghi rõ: *"We also experimented with other
  serialization methods, such as header-data pairing or template-based method, yet
  none reported superiority over the simple concatenation."*
- **Họ mã hoá đường dẫn/toạ độ là nhóm có bằng chứng yếu nhất ở quy mô của chúng
  ta** — không tồn tại một kết quả dương nào vừa được cô lập vừa peer-reviewed.
  [DeepTable](https://arxiv.org/abs/2609.07707) (DeepSeek-7B, Llama-3-8B,
  Qwen2.5-7B) đo riêng Tree Path Encoding: **−1.11 / +13.27 / −0.04**, và tự nhận
  *"TPE remains nearly flat"* theo độ sâu, trong khi thành phần *thực sự* hoạt
  động (Structural Attention Bias, +7.85 trung bình) là thay đổi kiến trúc **không
  thể đưa vào prompt**. [OHD](https://arxiv.org/abs/2602.01969) với TableLLaMA-7B
  còn *thua* vanilla (63.62 vs 64.71) vì token overhead.
- **Hai preprint lệch nhau ~66 điểm trên cùng một baseline.** OHD báo DeepSeek-V3
  đạt 15.85 EM trên HiTab với markdown thô, ASTRA báo 82.0 với serialization
  textual. **Không trích baseline của bài nào làm sự thật.**
- **Không tìm thấy ViPanelTR ở nguồn công khai nào.** Các số 84.25–85.71 vs 75–78
  F1 là do người dùng cung cấp và quy ước phân tầng không rõ. Kết hợp với vấn đề
  3-chiều vs 4-chiều ở mục 0, **không nên so trực tiếp con số của hai bài như thể
  chúng cùng thang đo** cho tới khi xác nhận quy ước.
- **Chain-of-Table ghi backbone là "Llama-2-17B-chat"** — không tồn tại model nào
  như vậy, và Appendix C không ghi kích thước. Không suy đoán.
- Cần **kiểm chứng số IM-TQA của Chain-of-Query** trước khi dùng nó làm bằng
  chứng cho merged cell, vì IM-TQA là proxy công khai gần nhất với điều kiện của
  chúng ta.

## 7. Điều không tồn tại — và đó là khoảng trống có thể claim

**Không một phương pháp nào trong toàn bộ họ program-aided/decomposition đánh giá
câu hỏi unanswerable.** WikiTQ, TabFact, FeTaQA, HiTab, FinQA, TAT-QA, IM-TQA,
TableBench đều không có lớp này. Cách các hệ thống xử lý **kết quả SQL rỗng** rất
thống nhất: ProTrix từ chối viết SQL (chỉ case study); TableMaster có "information
sufficiency check" nhưng dùng để *mở rộng* context; ProgramTab thử lại 5 lần rồi
im lặng bỏ cuộc; TabSQLify vá bằng column-selection; Chain-of-Query quay về query
hợp lệ cuối; TableLLM **loại bỏ** các truy vấn Spider trả null khỏi dữ liệu
huấn luyện.

Tất cả đều coi kết quả rỗng là **lỗi cần vá**. Coi nó là **một lá phiếu abstain**
là tín hiệu có căn cứ thực thi — không do LLM sinh ra — mà một agent đọc-text về
mặt cấu trúc *không thể* tạo ra. Theo những gì kiểm chứng được, điều này chưa
được công bố trong họ này.

Về độ lớn kỳ vọng, phải dùng con số thật: **45** câu `Null`, không phải ~99. Đưa
recall abstention lên thêm ~60% phần còn thiếu tương ứng khoảng **+2.7 EM** — vẫn
gấp đôi toàn bộ phần orchestration (1.27 EM), nhưng vẫn **dưới ngưỡng 5.9 pp**
của phép kiểm không ghép cặp, nên bắt buộc đo bằng McNemar ghép cặp và báo cáo
**cả Unanswerable-F1 lẫn Answerable-F1** để bắt được hồi quy over-abstention.

Và khoảng trống thứ hai, lớn hơn: **mọi phương pháp được khảo sát trong cả năm
mảng đều chỉ đánh giá trên tiếng Anh.** Weaver và H-STAR ghi rõ English-only
trong phần Limitations; số còn lại đơn giản là không thử. TableEval (zh/en) là
tiền lệ đa ngữ duy nhất tìm được. Mọi khẳng định chuyển giao trong tài liệu này
là **giả thuyết cần kiểm chứng, không phải kết quả**.

## 8. Thứ tự triển khai đề xuất

| # | Việc | Chi phí | Gỡ được gì |
|---|---|---|---|
| 0 | Diff chỉ thị abstention POMA vs few-shot; trích ma trận `Null` của baseline | **$0** | Có thể giải thích trọn 53 FP |
| 1 | Sửa số: 4.5% chứ không 10%; gold `Null` = 45; 4 tầng `table_type`; hint TB 1.10 | **$0** | NX2 (thống kê specialist), tính chính xác |
| 2 | Chuyển mọi ablation sang ghép cặp + McNemar + bootstrap CI; nêu rõ MDE 5.9 pp | **$0** | NX3 (robustness); biến 1.27 EM thành kết quả âm hợp lệ |
| 3 | Quét K × hai mức normalizer, kèm đối chứng nhiễu và đối chứng extractor | ~$5 | NX2 + NX4 cùng lúc; đóng khung lại AN đúng bản chất |
| 4 | "Flatten V2" span-faithful + nhấc banner (đối chứng bắt buộc) | ~$5,5 | Cô lập phần cải thiện thật của biểu diễn |
| 5 | Chuyển vị bảng stub; đo tỉ lệ bất đồng + oracle-of-2 | ~$6 | Dị thể miễn phí, bằng chứng peer-reviewed tốt nhất |
| 6 | Cổng decorrelation Qwen3-8B × Gemma-4-E4B, rồi mới ensemble | ~$1 cho cổng | NX3 (đa backbone) + trục dị thể |
| 7 | Manifest cấu trúc làm bộ định vị + fallback cứng | ~$9 | Merged cells; phần novel của luận văn |
| 8 | Kết quả SQL rỗng làm lá phiếu abstain | ~$4 | Khoảng trống chưa công bố ở mục 7 |

Các mục 0–2 không tốn tiền, không tốn lượt gọi LLM, và gỡ được ba trong bốn nhận
xét của Reviewer 1. **Nên làm hết trước khi chạy bất kỳ thí nghiệm nào.**
