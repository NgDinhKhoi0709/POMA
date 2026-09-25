# Spec: Kinh nghiệm và điểm yếu của các phương pháp Vietnamese Table QA (ViPanelTR & POMA)

Ngày: 2026-09-18. Phạm vi: đọc ba tài liệu — (1) `MAPR_2026_Khoi.pdf`, bài
**ViPanelTR: A Multi-Agent Framework for Vietnamese Table Question
Answering** đã được **accept tại MAPR2026**; (2) `JIT_Khoi.pdf`, bài **POMA:
A Parallel Multi-Agent Orchestration for Vietnamese Table Question
Answering** hiện đang phản biện tại tạp chí JIT (Q2), trạng thái "*may not
yet meet the requirements*"; (3) `POMA_Ke_hoach_chinh_sua_Q2.docx`, kế
hoạch chỉnh sửa dịch 4 nhận xét của Reviewer 1 thành các đầu việc cụ thể —
rồi rút ra kinh nghiệm chung về cách xử lý bài toán Vietnamese Table QA và
liệt kê rõ điểm yếu của từng phương pháp, đặc biệt là POMA. Tài liệu này
không lặp lại phần phân tích code-level đã có ở
[`2026-09-18-answer-normalization-gsa-score-gap.md`](2026-09-18-answer-normalization-gsa-score-gap.md)
và [`2026-09-17-table-representation-small-lm.md`](2026-09-17-table-representation-small-lm.md);
nó tổng hợp ở tầm phương pháp luận/paper-level và trỏ tới hai tài liệu đó
khi có liên hệ trực tiếp.

## 0. Bối cảnh chung: bài toán và benchmark

Cả hai phương pháp cùng nhắm tới **Open-ViTabQA** (Dao et al., 2025) — 9,911
cặp câu hỏi–đáp án từ 329 bảng Wikipedia tiếng Việt trên 41 domain, chia
theo *table-disjoint split* (7,928 train / 991 dev / 992 test), cùng dùng
đúng 992 câu hỏi test làm bộ đánh giá chính. Đặc điểm khiến bài toán khó:
~55.6% bảng có merged cells, ~59% câu hỏi cần suy luận đa thực thể, ~10% câu
hỏi không có câu trả lời (đáp án vàng là chuỗi literal `Null`). Cả hai bài
đều dùng chung bốn chỉ số EM/F1/ROUGE-1/METEOR và chung phép biểu diễn bảng
**Flatten V1** (mở rộng rowspan/colspan thành lưới logic, join bằng `|`, cell
header có hậu tố `<header>`).

## 1. Hai phương pháp đã thử

### 1.1 ViPanelTR (MAPR2026, đã accept)

Kiến trúc 5-tác nhân cố định vai trò, chạy trên cùng một backbone:
Structuralist (schema/merged cell), Logician (điều kiện/phủ định),
Calculator (số học/đếm/so sánh), Verifier (evidence grounding/abstention),
Synthesizer (tổng hợp). Pipeline có 5 bước: (A) investigation song song bởi
5 role → (B) **early answerability gate**: nếu ≥3/5 role tự đánh giá
unsupported thì trả `Null` ngay, không cần các bước sau → (C) **self-review**
một vòng (mỗi role tự sửa draft của mình) → (D) **peer deliberation** một
vòng (5 role so sánh câu trả lời, consensus rồi mới vote) → (E) **answer
normalization**. Thử trên 3 backbone khớp cặp: Qwen3 8B, LLaMA 3.1 8B,
GPT-4o mini.

Kết quả chính (so với prompt-based cùng backbone, F1): GPT-4o mini
64.57→80.66 (+16.09), Qwen3 8B 62.58→80.06 (+17.48), LLaMA 3.1 8B
56.44→62.23 (+5.79). So với CoAgt/CoQ cùng backbone GPT-4o mini, ViPanelTR
hơn CoAgt +11.79 F1 và hơn CoQ +7.46 F1. Ablation loại bỏ từng giai đoạn
(self-review, peer deliberation) trên Qwen3 8B chỉ làm giảm 0.27–0.56 F1,
nghĩa là phần lớn tín hiệu đã nằm ở investigation ban đầu — nhưng bài không
tách riêng đóng góp của answer normalization theo kiểu ablation on/off như
POMA làm (chỉ có ablation EM cho normalization: +6.55 tới +11.39 điểm EM tuỳ
backbone, xem Table V của MAPR).

### 1.2 POMA (JIT, đang phản biện)

Kiến trúc pipeline tuần tự có định tuyến cứng: (A) **hint predictor** dự
đoán tập nhãn canonical (What/Where/Who/When/Why/How/YesNo/List/
MathematicalReasoning/MultiConditions — đúng 10 nhãn của Open-ViTabQA) → (B)
**question refiner** cấu trúc hoá câu hỏi thành `(q̄, t, c)`, không trả lời →
(C) **router** xác định (deterministic, không gọi LLM) tập specialist cần
chạy → (D) chạy song song các specialist tương ứng (mỗi specialist = 1 role
cố định khớp 1 nhãn) → (E) **answer normalization** hợp nhất output thành
tập biến thể câu trả lời tương đương về nghĩa. Chỉ thử trên **một** backbone:
Qwen3 8B qua OpenRouter.

Kết quả chính so với few-shot cùng backbone: EM 67.14→80.24 (+13.10), F1
78.64→88.23 (+9.59), R1 74.18→86.07 (+11.89), MET 72.30→84.50 (+12.20). Chi
phí: $0.54→$2.06 (3.8×), 5,503,513→19,077,260 token (3.5×), 19,462s→70,674s
(3.6×). Ablation answer normalization (Table 6 của JIT): không có AN = 68.41
EM, có AN = 80.24 EM.

## 2. Kinh nghiệm chung rút ra được (áp dụng cho cả hai phương pháp)

1. **Answer normalization là đòn bẩy điểm số lớn nhất cho Vietnamese Table
   QA, không phải multi-agent reasoning.** Ở POMA, AN đóng góp ~11.83/13.10
   điểm EM (~90% tổng cải thiện so với few-shot); phần hint
   prediction+refiner+specialist+parallel chỉ còn ~1.27 điểm EM. Ở ViPanelTR,
   AN đóng góp +6.55 đến +11.39 điểm EM tuỳ backbone — cùng bậc độ lớn với
   phần lớn cải thiện tổng thể. Điều này khớp với phát hiện code-level đã có
   trong repo
   ([2026-09-18-answer-normalization-gsa-score-gap.md](2026-09-18-answer-normalization-gsa-score-gap.md)):
   phần lớn giá trị đo được từ oracle best-of-K nằm ở việc thử nhiều **hình
   thức bề mặt** cho tới khi trúng đúng hình thức của gold, không phải suy
   luận nội dung tốt hơn. Kinh nghiệm cho các thiết kế sau: **luôn tách riêng
   ablation on/off cho answer normalization và báo cáo tách bạch đóng góp của
   nó**, đừng gộp chung vào "cải thiện nhờ orchestration".
2. **Best-of-K / candidate-variant evaluation cần được áp dụng công bằng cho
   cả hệ thống lẫn baseline.** Nếu chỉ hệ thống đề xuất được hưởng cơ chế sinh
   nhiều biến thể rồi chấm best-match, còn baseline chỉ có một câu trả lời,
   so sánh sẽ thiên vị hệ thống một cách hệ thống — bất kể chất lượng suy
   luận thực sự. Đây là đúng cơ chế mà reviewer JIT chỉ ra ở NX2.2 và cũng là
   đúng cơ chế mà phân tích GSA trong repo đã đo được bằng số cụ thể (K trung
   bình 3.44, K tối đa 80 cho POMA `all`).
3. **Faithful abstention (nhận biết câu hỏi không có câu trả lời) vẫn là bài
   toán chưa giải quyết ở cả hai hệ thống**, dù cách biểu hiện khác nhau:
   ViPanelTR cải thiện F1 lớp Unanswerable ở mọi backbone (23.66→42.11 với
   GPT-4o mini) nhưng điểm tuyệt đối vẫn rất thấp so với lớp Answerable
   (94.54–94.97); POMA thậm chí **thua** chính baseline few-shot ở cả hai lớp
   (xem mục 4). Kết luận chung: pipeline nhiều tác nhân giúp *câu trả lời*
   tốt hơn khi bảng có bằng chứng, nhưng chưa chắc giúp *quyết định có nên
   trả lời hay không* tốt hơn — hai năng lực này cần được đo và tối ưu riêng,
   không suy diễn từ điểm tổng.
4. **Bảng có merged cells vẫn khó hơn bảng thường ở cả hai hệ thống dù đã cải
   thiện đáng kể.** ViPanelTR: F1 trên bảng chuẩn đạt 84.25–85.71 nhưng rơi
   xuống 75–78 trên bảng merged-header/merged-value. POMA: EM đạt 83.51 trên
   bảng normal nhưng chỉ 80.42 (header-merge) và 75.95 (value-merge). Cả hai
   bài đều tự nhận: framework giảm nhẹ khó khăn cấu trúc chứ không loại bỏ
   nó — cần biểu diễn bảng structure-aware hơn là hướng còn để ngỏ ở cả hai.
5. **Chi phí orchestration tăng 3.5–4× cho phần lợi ích tăng dần nhỏ hơn
   nhiều so với answer normalization.** POMA đo trực tiếp điều này (Table 7
   JIT): tăng cost 3.8× và token 3.5× để đổi lấy +13.10 EM, phần lớn trong đó
   đến từ AN chứ không phải orchestration. ViPanelTR không có bảng chi phí
   tương đương trong bản đọc được — đây là khoảng trống nên bổ sung để so
   sánh công bằng giữa hai phương pháp của cùng nhóm tác giả.
6. **Taxonomy đặc thù dataset là rủi ro chung, không riêng POMA.** POMA có 10
   specialist khớp *chính xác* 10 nhãn hint của Open-ViTabQA. ViPanelTR có 5
   role mà chính bài tự mô tả là "*role definitions tied to Open-ViTabQA
   error modes such as merged cells, unsupported questions, Yes/No answers,
   lists, and surface-form variation*" (Related Work, mục c). Cả hai thiết kế
   đều được suy ra từ chính benchmark đang dùng để đánh giá — nghĩa là claim
   "tổng quát cho Table QA" của cả hai bài đều cần một thí nghiệm transfer
   sang dataset khác để được củng cố, không chỉ riêng POMA.
7. **Đơn backbone/đơn dataset/không có kiểm định thống kê là điểm yếu
   phương pháp luận lặp lại ở cả hai bài**, dù ViPanelTR đỡ hơn vì có 3
   backbone (nhưng vẫn 1 dataset, decoding tất định, không báo cáo
   confidence interval); POMA chỉ có 1 backbone + 1 dataset + 1 lần chạy tất
   định (temperature 0.0). Đây là nhóm điểm yếu rẻ nhất để khắc phục (thêm
   backbone, thêm bootstrap CI) nhưng lại là điều kiện gần như bắt buộc để
   thuyết phục reviewer Q2, theo đúng đánh giá trong docx.

## 3. Điểm yếu chi tiết — POMA (theo mức ưu tiên, dựa trên 4 nhận xét của Reviewer 1 JIT)

Trạng thái phản biện: "*the current contributions seem limited and may not
yet meet the requirements for publication*". Bốn nhận xét đều ở mức chung
chung; docx `POMA_Ke_hoach_chinh_sua_Q2` đã dịch thành các vấn đề cụ thể sau,
xếp theo mục trong bản thảo.

| Mục trong bài | Nhận xét | Vấn đề chính | Ưu tiên |
|---|---|---|---|
| Abstract / Contributions (§1, §6) | NX4 | Overclaim "modular multi-agent orchestration" trong khi ablation cho thấy Answer Normalization mới là đòn bẩy chính (~90% cải thiện EM). | Bắt buộc |
| Introduction (§1) | NX1 | Không có research question tường minh; quan hệ problem→solution mờ; chưa biện minh vì sao chọn decomposition-by-type thay vì prompt đơn mạnh hơn/symbolic executor/fine-tuning. | Bắt buộc |
| Problem Formulation & Ablation (§3.1, §5.6) | NX2, NX3 | Cơ chế chấm best-of-K + AN gánh gần hết điểm; kết luận "không có output đúng nào bị AN làm sai" (§5.6) là hệ quả tất yếu của cơ chế best-match, không phải bằng chứng chất lượng AN — chưa rõ baseline có được chấm cùng cơ chế K-biến-thể hay không. | Bắt buộc |
| Method + Appendix (§3.3–3.6) | NX2 | Không có prompt nào trong appendix (chỉ mô tả specialist là "prompt-conditioned module") — hại cả tính thuyết phục lẫn khả năng tái lập; 10 specialist khớp cứng 10 nhãn hint của đúng một dataset. | Bắt buộc |
| Config / Overall Results (§4.3, §5.1) | NX3 | Chỉ một backbone (Qwen3 8B) — với tạp chí Q2, một backbone làm nặng thêm nghi ngờ overfit. | Cao |
| Hint source (§3.3, §5.5) | NX2, NX3 | Không báo cáo precision/recall của hint predictor theo từng nhãn dù router phụ thuộc hoàn toàn vào hint; claim "predicted hints tốt hơn gold hints" (80.24 vs 80.04 EM) được giải thích qua loa, chênh lệch 0.20 EM có thể chỉ là nhiễu. | Cao |
| Parallel specialists (§3.6, §5) | NX2 | "Parallel" chưa được chứng minh có giá trị — không có thống kê trung bình bao nhiêu specialist được kích hoạt mỗi câu hỏi, không có ablation single- vs multi-specialist-routing. | Cao |
| Answerability (§5.3) | NX3 | **POMA thua chính few-shot baseline ở cả hai lớp**: Answerable 96.49 vs 97.38 (few-shot), Unanswerable 51.13 vs 56.64 (few-shot). Ở đúng quyết định cốt lõi (có nên abstain hay không), orchestration không giúp — thậm chí hơi hại. False abstention (bỏ qua 53/946 câu answerable) xảy ra nhiều gấp 4.8 lần hallucination (11/46 câu unanswerable), cho thấy hệ thống thiên về bảo thủ nhưng đánh đổi bằng việc bỏ sót câu trả lời đúng. | Cao |
| Robustness (mục mới) | NX3 | Không có thống kê độ ổn định/significance — chỉ một lần chạy tất định (temperature 0.0). +13 EM chưa được chứng minh là ổn định chứ không phải một lần may. | Nên có |
| Generalization (mục mới) | NX2, NX3 | Chỉ một dataset; vì taxonomy lấy trực tiếp từ Open-ViTabQA, cần một kiểm tra transfer (dù nhỏ) sang benchmark Table QA khác để phản bác nghi ngờ "chỉ chạy được trên đúng dataset đã định nghĩa nhãn". | Nên có |

Ngoài bảng trên, tự bản thân bài JIT cũng thừa nhận hai lỗi phân tích cụ thể
trên câu hỏi Why (R1 giảm từ 69.18 xuống 55.94 so với few-shot):
**routing error** (hint predictor bị phân tâm bởi so sánh số nên route nhầm
sang MathematicalReasoning) và **causal-evidence error** (WhyAgent tái diễn
đạt một fact trong bảng thành "lý do" của chính nó thay vì trả `Null` khi
bảng không có bằng chứng nhân quả thật).

## 4. Điểm yếu chi tiết — ViPanelTR (tự nhận trong bài + suy ra từ số liệu)

ViPanelTR đã được accept, nhưng đọc kỹ số liệu vẫn lộ ra các điểm yếu đáng
ghi nhận cho lần viết tiếp theo hoặc khi so sánh với POMA:

1. **LLaMA 3.1 8B: framework làm giảm điểm ở 7/10 loại câu hỏi.** Theo
   Table II (ROUGE-1 by question type), so với prompt-based cùng backbone:
   Who 63.75→44.39 (**-19.36**), What 68.97→57.83 (-11.14), When 69.06→67.24
   (-1.82), Where 71.33→63.61 (-7.72), How 44.17→23.91 (**-20.26**), Why
   58.26→36.28 (**-21.98**), List 44.52→36.02 (-8.50) — chỉ Yes/No
   (+31.74), Calculate (+12.11), Multi-conditions (+13.74) cải thiện. Nghĩa
   là gain tổng thể +5.79 F1 của backbone này đang che giấu các khoản lỗ khá
   lớn ở phần lớn loại câu hỏi giải thích/factoid; bài không phân tích
   nguyên nhân của việc này (khác với phần phân tích lỗi Why khá kỹ ở POMA).
2. **Faithful abstention còn xa mức trần**, dù cải thiện nhất quán: F1 lớp
   Unanswerable cao nhất chỉ đạt 42.11 (GPT-4o mini), thấp hơn nhiều so với
   Answerable (94.54–94.97). Bài tự kết luận: "*faithful abstention is still
   the main unresolved challenge in Open-ViTabQA*".
3. **Why không ổn định qua các backbone, How vẫn khó với GPT-4o mini** — bài
   tự nêu rõ trong phần "Analysis by Answerability/Question Type" nhưng
   không đi sâu phân tích lỗi theo kiểu POMA (routing error / causal-evidence
   error).
4. **Cùng rủi ro overfit taxonomy như POMA**: 5 role được thiết kế bám sát
   các "error mode" cụ thể của Open-ViTabQA (câu trích ở mục 2.6 phía trên),
   nên claim tổng quát cho Vietnamese Table QA nói chung chưa được kiểm
   chứng bằng dataset thứ hai.
5. **Không có phân tích chi phí/hiệu năng suy luận** (cost, token, latency)
   như POMA có ở Table 5/7 — với một pipeline 5-role × (investigation +
   self-review + peer deliberation), chi phí suy luận nhiều khả năng còn cao
   hơn POMA nhưng không được đo hoặc báo cáo trong bản đọc được.
6. **Cùng thiếu significance/robustness testing**: không thấy bootstrap CI,
   nhiều seed, hay perturbation robustness — cùng nhóm điểm yếu phương pháp
   luận như POMA (mục 2.7).
7. **Bất thường cần kiểm tra trong file PDF**: ở đầu mục "VI. CONCLUSION AND
   FUTURE WORK" (trang 6) có một đoạn ký tự vô nghĩa xen giữa
   ("`c vbmkjhgfrt6/p;lkjhg fde4rfty6uj8ikop[' ':lkjh vfcaswdx-efb.op[;'/m1qww21'`")
   trước câu "*We presented ViPanelTR...*". Đây nhiều khả năng là lỗi paste/gõ
   phím còn sót lại trong file camera-ready đã nộp — nên rà lại bản PDF chính
   thức đã accept tại MAPR2026 trước khi xuất bản cuối cùng, vì tài liệu này
   không tự động sửa các file PDF gốc của bạn.

## 5. Khuyến nghị hành động (áp dụng trực tiếp cho vòng phản hồi JIT, dựa trên docx)

Thứ tự triển khai theo docx `POMA_Ke_hoach_chinh_sua_Q2`, xếp theo chi
phí/tác động (chi phí một lần chạy full POMA chỉ ~$2.06 nên toàn bộ dưới đây
khả thi với ngân sách sinh viên):

1. **Công bằng hoá so sánh** — áp answer normalization lên few-shot/ZS/CoT
   baseline rồi báo cáo lại; đồng thời báo cáo cấu hình single-final-answer
   (không best-of-K) cho cả POMA lẫn baseline; nêu rõ K và cơ chế best-match
   áp dụng cho hệ nào. Đây là thí nghiệm quan trọng nhất — gỡ đồng thời NX2 và
   NX4. Có thể tái sử dụng trực tiếp hạ tầng đã build cho phân tích GSA
   trong repo (`evaluation/io.py:61`, `candidate_policy=first`).
2. **Tổng quát hoá backbone** — thêm ít nhất một backbone ngang tầm (Llama
   3.1 8B, Gemma, hoặc Mistral) để chứng minh method generalize; đây gần như
   là điều kiện cần để được nhận ở Q2, và cũng là dịp áp cùng bộ chỉ số cho
   ViPanelTR để so sánh nhất quán giữa hai bài của cùng nhóm tác giả.
3. **Củng cố method**: báo cáo precision/recall của hint predictor theo
   nhãn; thêm thống kê phân bố số specialist kích hoạt mỗi câu + ablation
   single- vs multi-specialist; đưa toàn văn prompt (hint predictor, refiner,
   vài specialist đại diện) vào Appendix.
4. **Viết lại phần định khung**: thêm 3 research question tường minh vào
   Introduction; taxonomy of failure modes (grounding error; answerability
   error hai chiều; surface-form error) map tới đúng module; đóng khung lại
   contribution để phản ánh đúng những gì controlled analysis chứng minh
   được (không overclaim "khai phá multi-agent"); đóng khung trung thực phần
   answerability đang thua baseline.
5. **Nếu còn thời gian**: bootstrap 95% CI trên 992 mẫu hoặc perturbation
   robustness; transfer test sang một benchmark Table QA khác; cân nhắc một
   evidence-support verifier tối giản để xử lý regression answerability.

## 6. Câu hỏi mở cho hướng nghiên cứu tiếp theo

- Nếu answer normalization đã gánh phần lớn cải thiện, liệu một pipeline
  **đơn-agent + answer normalization mạnh** có đạt gần hiệu năng của
  multi-agent với chi phí thấp hơn nhiều? Đây chính là RQ2 mà docx đề xuất
  đưa vào Introduction, và cũng là câu hỏi có thể trả lời rẻ bằng thí nghiệm
  ở mục 5.1.
- Cả hai phương pháp đều chưa thử **structure-aware representation** (thay
  vì chỉ Flatten V1) cho bảng merged-cell — đây là khoảng trống chung, đã có
  hướng cụ thể (selector BM25/dense không dùng LLM) trong
  [2026-09-17-table-representation-small-lm.md](2026-09-17-table-representation-small-lm.md).
- Faithful abstention nên được đo và tối ưu như một bài toán **classification
  riêng** (không suy diễn từ F1/EM tổng), có thể cần một verifier tách biệt
  khỏi luồng sinh câu trả lời chính — cả ViPanelTR (Verifier role) và POMA
  (early answerability gate/router) đều đã thử một dạng cơ chế này nhưng
  chưa đủ để đóng khoảng cách với baseline đơn giản.
