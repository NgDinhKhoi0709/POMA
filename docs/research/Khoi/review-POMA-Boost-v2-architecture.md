# Review kiến trúc POMA-Boost v2 và đề xuất thay thế POMA v3

Sơ đồ được review là `poma2.drawio`. Sơ đồ đề xuất là `poma3.drawio`.

Ngày: 2026-09-18

Tôi chạy 6 agent song song, mỗi agent một việc:
1. Phân tích offline output có sẵn trong repo, không gọi API, tốn $0. Kết quả nằm trong `trace-analysis/`.
2. Kiểm tra 23 paper mà poma2 trích, xem có thật không và có được dùng đúng không.
3. Tìm nguồn diversity cho table QA (text vs program, nhiều view bảng, nhiều model khác nhau).
4. Tìm phương pháp answerability và cascade/escalation.
5. Kiểm tra novelty và overlap, kể cả bài của Son et al.
6. Đọc blog (Raschka, Willison, Anthropic engineering, Weng, Hamel, Eugene Yan, Wolfe, HF, Google Research và vài nơi khác).

Ký hiệu [ĐO] là số đo trực tiếp từ output của repo bằng evaluator của chính repo. [ƯỚC] là ước lượng hoặc suy luận. Agent đã mở trang abs của mọi arXiv ID trong file này.

---

## 0. Kết luận ngắn

poma2 hợp lý trên giấy nhưng dữ liệu không ủng hộ nó. **Không nên xây poma2 như đang vẽ.**

Mỗi box trong poma2 sinh ra để trả lời một finding của review (F4, F5, F2/F3, F8). Nhưng cả kiến trúc đứng trên một tiền đề chưa ai kiểm tra, rằng các specialist của POMA bất đồng với nhau theo cách có ích. Output thật trong repo cho thấy điều ngược lại.

- 88,7% câu hỏi chỉ route tới đúng 1 specialist (880/992) [ĐO]. Với các câu này gate "Disagree?" không có gì để so, nên luôn trả "agree".
- Ở các câu có 2 specialist, gate chỉ bật ở khoảng 1,4% tổng số câu [ĐO trên 592 câu có trace, ƯỚC cho 992].
- Một resolver hoàn hảo cho mọi bất đồng chỉ cộng +0,3 EM khi chấm single-answer, trần là +0,7 [ĐO].
- Gate không nhìn thấy 92,9% lỗi (182/196). Đó là những câu chỉ có một specialist và nó sai, hoặc các specialist đồng thuận nhưng cùng sai [ĐO].
- Trường confidence bão hòa. 77,9% giá trị bằng đúng 1,0, AUROC chỉ 0,59–0,66 [ĐO]. Không có gì để calibrate hay đánh trọng số.
- Trường evidence không phân biệt được đúng sai. Câu trả lời sai vẫn trích cell có thật trong 88,5% trường hợp, AUROC 0,52 [ĐO].
- Cả 46 câu gold-Null đều chỉ có 1 specialist. Nhánh "hedge" chỉ thấy 8/64 lỗi answerability và không thấy hallucination nào trong 11 cái [ĐO].

Thêm nữa, 3 thành phần dùng sai paper mà chúng trích (LofreeCP, S\*, OW/ISP), và 2 thành phần khác phải mô tả lại (MARGIN, COMPETE). Chi tiết ở §2.

Theo tôi, nên giữ những ý tốt của poma2: aggregation bất đối xứng, escalation có điều kiện, tách hai trục correctness và answerability, và xuất một đáp án duy nhất. Phần phải đổi là nguồn diversity. Nó phải đến từ các agent suy luận theo những cách khác nhau, gồm một text specialist, một program agent chạy pandas trên máy, và một generalist đọc bảng ở view khác. Mười role prompt chạy cùng backbone ở T=0 không tự sinh ra diversity. Answerability cần một agent riêng, chạy trên mọi dự đoán Null. Answer Normalization cần tách đôi, canonicalizer đặt trước gate và formatter đặt cuối cùng.

Kiến trúc đề xuất nằm ở §4, file sơ đồ là `poma3.drawio.xml` và `poma3.drawio.png`.

Trace analysis còn giải được mâu thuẫn ở Table 6 (68,41 vs 62,40) và phát hiện evaluator drift. Hai chuyện này buộc paper hiện tại phải sửa số liệu dù chọn kiến trúc nào (§7). Vài kết luận trong `review-POMA-JIT.md` cũ cũng phải đính chính (§8).

---

## 1. Số đo từ output có sẵn trong repo

Nguồn là `trace-analysis/gate_headroom_report.md`. Repo chỉ lưu output riêng của từng specialist cho 592/992 câu (bản hp), còn số specialist của mỗi câu thì biết đủ cho 992 câu.

| Câu hỏi | Kết quả | Hệ quả cho poma2 |
|---|---|---|
| Số specialist mỗi câu | 1 specialist ở 880 câu (88,7%), 2 ở 112 câu, 3 ở 0 câu. Trung bình 1,113 | "Parallel" chỉ thật sự chạy ở 11% số câu. F4 còn nặng hơn review cũ nghĩ |
| Tỉ lệ bất đồng sau canonicalize | 8/64 câu có 2 specialist, tức khoảng 1,4% tổng số câu | Gate gần như không bao giờ bật |
| Trần của resolver hoàn hảo (single-answer) | 67,74 → 68,04 (+0,30). Trần trên 992 câu là +0,71 | Cả nhánh disagree đóng góp nhiều nhất 0,3–0,7 EM |
| Lỗi gate không thấy | 92,9% lỗi best-of-K (171 câu single-specialist sai, 11 câu đồng thuận nhưng sai) | Gate không chạm tới phần lớn lỗi |
| Best-of-K thổi phồng EM | 80,24 (best-of-K) vs 67,74 (đáp án đầu tiên), chênh 12,50 [CI 10,48–14,62] | Trong 124 câu "thắng nhờ best-of-K", 117 câu có đáp án đúng dạng nằm sẵn trong tập biến thể của một specialist. Riêng từ đồng nghĩa yes/no chiếm 49 câu |
| POMA single-answer vs FS | 67,74 vs 67,34, chênh +0,40 [−2,12; +3,02], không có ý nghĩa thống kê | Chấm công bằng thì orchestration hiện tại ngang few-shot |
| Cùng áp biến thể AN tất định | POMA 78,33 vs FS 75,81, chênh +2,52 [0,10; 4,94] | Còn chút lợi thế, nhưng nhỏ và sát biên |
| Confidence | 77,9% bằng 1,0; 93,5% từ 0,9 trở lên; AUROC 0,59–0,66 | MARGIN và OW không có tín hiệu để dùng |
| Evidence grounding | 91,8% output non-Null chỉ trích cell có thật, dù đúng hay sai; AUROC 0,52 | Verifier kiểu "evidence có trong bảng không" vô dụng |
| Answerability trên dữ liệu hiện tại | POMA 53 false abstention, 11 hallucination, Null-F1 52,24. FS 42 và 9, Null-F1 59,20 | FS tốt hơn POMA ở cả hai hướng lỗi |
| Nhánh hedge thấy được gì | 8/64 lỗi answerability (12,5%), 0/11 hallucination | Tách hai trục mà chỉ chạy trên hedge thì bỏ sót gần hết F8 |
| Tương quan lỗi POMA vs FS | Cả hai cùng sai 240 câu, nếu độc lập thì chỉ khoảng 104,5 (gấp 2,30 lần); κ = 0,62 | Cùng backbone thì lỗi tương quan mạnh, kể cả giữa hai phương pháp khác nhau |
| Voter khác phương pháp | Chỉ vote khi POMA-first ≠ FS (bật ở 217 câu) được 69,86 (+2,12). Oracle single-answer của {POMA, FS, ZS, CoT, TD} là 79,64 | Dư địa nằm ở bất đồng giữa các phương pháp, không nằm giữa các role |
| Formatter yes/no học từ tập train | 71,27 (+3,53) [ƯỚC] | Chỗ rẻ nhất để lấy lại điểm là format, không phải xung đột giữa specialist |
| Theo loại câu | Why: POMA-first 40,7 vs FS 55,6. Math: 64,6 vs 67,7. List: 66,1 vs 50,0. YesNo: best-of-K 89,7 nhưng first chỉ 59,4 | Specialist giúp được List. Why và Math tệ hơn FS khi chấm single-answer |
| Hint predictor | Đúng nguyên tập 65,0%, micro-F1 0,723. Recall MultiConditions 0,40, How 0,31 | Đầu vào của router chất lượng trung bình |
| Vì sao predicted hint tốn thêm 70% token | Số specialist chỉ tăng 2,6%. Phần +70% đến từ việc hint predictor đọc toàn bộ bảng | Đính chính F9 của review cũ (§8) |

Một lưu ý về phương pháp. Mọi phân tích ở trên chạy trên tập test. Chừng đó đủ để bác bỏ poma2, nhưng mọi quyết định thiết kế và ngưỡng cho kiến trúc mới phải làm lại trên tập dev (chạy POMA trên dev tốn khoảng $2). Không làm vậy thì paper dính lỗi tune trên test.

---

## 2. Review từng thành phần của poma2

| Thành phần | Vấn đề | Bằng chứng | Quyết định |
|---|---|---|---|
| Aggregator, gọi LLM ở mọi câu | Ở nhánh agree nó không làm gì mà vẫn tốn khoảng 992 call, mỗi call chứa toàn bộ output và bảng. Việc so đáp án làm tất định được | Gate bật ở khoảng 1,4% số câu | Bỏ LLM. So khớp tất định trên canonical key, chỉ gọi LLM ở nhánh bất đồng |
| Gate "Disagree?" trên specialist | 88,7% câu chỉ có 1 specialist, và lỗi tương quan vì cùng backbone, cùng view, cùng T=0. Chính plan trích Nine Judges (9 judge chỉ bằng khoảng 2 phiếu hiệu dụng) rồi lại xây lõi trên bất đồng giữa các judge đó | §1 | Giữ gate, đổi nguồn voter thành text specialist, program agent và generalist |
| Answer Normalization đặt sau gate | Gate so chuỗi thô, nên nó coi khác biệt bề mặt là bất đồng, trong khi đó đúng là thứ AN sinh ra để sửa | Trong trace, 2/10 bất đồng thô chỉ là thứ tự list hoặc dấu phân cách | Tách AN. Canonicalizer tất định đặt trước gate, formatter đặt cuối |
| Row/Col Verifier (DRE, Table-Critic) | DRE trên Qwen3-8B chỉ sửa được 1,1–1,8 pp, kể cả khi critic nhìn thấy ground truth, và critic tốt nhất là bản 4B đã fine-tune. Chưa ai thử Table-Critic ở model từ 8B trở xuống | Agent 2 | Thay bằng kiểm tra bằng cách chạy chương trình |
| Tie-breaker "discriminating query" (S\*) | S\* bắt buộc chạy code để sinh input phân biệt. Không chạy code thì nó chỉ còn là baseline "LLM judge" trong ablation của S\* (55,6 vs 57,5) | Agent 2 | Giữ ý của S\* nhưng làm cho đúng. Sinh chương trình phân biệt hai đáp án, chạy trên DataFrame, để LLM quyết sau khi đọc kết quả in ra |
| Correctness Check (COMPETE) | Paper viết cho lỗ hổng kiến thức tham số (closed-book). Đặt một passage giả cạnh bảng thì chỉ đo được model dễ bị lung lay tới đâu, và model 8B bám context sẽ đổi ý quá nhiều. Trên Mistral-7B nó ngang baseline self-consistency (0,640 vs 0,641) | Agent 2, 4 | Bỏ |
| Answerability Check (LofreeCP) | Dùng sai. LofreeCP là conformal prediction cho correctness, tạo tập dự đoán chứa gold với xác suất ít nhất 1−α. Nó không có khái niệm unanswerable, cần khoảng 30 mẫu mỗi câu và 50% dữ liệu có nhãn để calibrate. Tập {Null, x} chính là hedge best-of-K quay lại | Agent 2, 4 | Bỏ, thay bằng Identify-then-Verify cộng dò bảng tất định (§4) |
| Chỉ kích hoạt hai trục khi có hedge | Không thấy false abstention khi mọi specialist cùng nói Null (45/53), và không thấy hallucination nào (11/11) | §1 | Kích hoạt trên mọi dự đoán Null (khoảng 9% số câu), trên câu Why, và trên các cờ hallucination có precision cao |
| Weighted Consolidation (OW/ISP) | ISP cần một không gian nhãn cố định dùng chung cho mọi câu, không hợp với đáp án tự do tiếng Việt. OW cần độ chính xác của từng agent và giả định các agent độc lập có điều kiện. Theo Nine Judges, weighting chỉ đóng được tối đa 11% khoảng cách Condorcet, kể cả khi có gold label. Trong sơ đồ nó còn thừa. Nhánh agree không có gì để cân, còn nhánh disagree thì tie-breaker đã quyết xong | Agent 2 và logic sơ đồ | Bỏ. Nếu cần thì dùng luật theo loại câu, tức numeric/list/multi-condition tin program, lookup/why tin text |
| Confidence Calibration (MARGIN) | "Không cần train" thì đúng, "không cần nhãn" thì sai, vì MARGIN cần biết đúng sai của mọi dự đoán. Confidence của Qwen3-8B đã bão hòa ở 1,0 | Agent 2 và §1 | Bỏ |
| Final Answer (single) | Đúng hướng, bỏ được best-of-K | Không có | Giữ |

---

## 3. Lỗi logic và trình bày trong chính sơ đồ poma2

Về luồng xử lý có năm lỗi.
1. Nhánh hedge đi thẳng vào Answer Normalization, bỏ qua Weighted Consolidation, nên không rõ AN nhận candidate nào.
2. Không có nhánh thất bại. Sơ đồ không nói gì về trường hợp verifier không tìm được candidate nào grounded, hay tie-breaker không phân xử được.
3. Nhánh agree vẫn đi qua Weighted Consolidation dù chẳng có gì để cân.
4. Question Refiner của v1 biến mất khỏi sơ đồ mà không có lời giải thích. Table Context cũng không nối tới Hint Prediction hay Verifier, dù cả hai đều cần bảng.
5. Không thành phần nào xử lý hai failure mode của câu Why mà chính paper đã nêu, là route nhầm sang Math và coi một fact là nguyên nhân của chính nó.

Về trình bày có sáu lỗi.
1. Mũi tên Specialist 1 → … → Specialist N đọc như một chuỗi tuần tự. Đó đúng là pattern CoAgt mà paper tự phân biệt với mình. Muốn thể hiện song song thì vẽ fan-out/fan-in và không nối các specialist với nhau, như poma3 đã làm.
2. Nhiều cạnh có đầu mút lơ lửng (`e3`, `e6`, `e7` không gắn vào source hay target), kéo box là gãy.
3. Khung các stage lệch nhau, y lúc 25 lúc 30, chiều cao lúc 370 lúc 430.
4. Hình thoi quyết định tô màu hồng, trùng màu output của Final Answer.
5. Caption viết "consolidates…, calibrates confidence…", ngược với thứ tự thực tế. Caption nằm trong hình thì dùng cho slide hoặc draft được, còn vào paper thì nên chuyển sang `\caption{}`.
6. Chữ "Boost" không đúng. Cơ chế này không phải boosting vì không có bước đánh lại trọng số tuần tự trên mẫu khó. BoT dùng chữ boosting như một ẩn dụ, và reviewer ML dễ bắt lỗi chữ này. Gọi là selective verification hoặc cascade thì chính xác hơn.

---

## 4. Kiến trúc đề xuất POMA v3

File sơ đồ là `poma3.drawio.xml` và `poma3.drawio.png`.

Tôi gợi ý giữ acronym và đổi nghĩa thành *Parallel Orchestration of Mixed-reasoning Agents*. Ở v3 chữ "Parallel" mới đúng, vì 3 solver luôn chạy song song chứ không chỉ ở 11% số câu như v1.

```
Stage 1  Input Preparation
  Question ─► Question Analyzer (1 call: hints · structured query · answer type)
  Table    ─► Table Views (no LLM: Flatten V1 text · header-path records · pandas DataFrame)
Stage 2  Heterogeneous Solvers, chạy song song, mù, T=0
  S  Routed Specialist(s)   text reasoning, route theo hint (giữ nguyên POMA v1)
  P  Program Agent          viết pandas, chạy trên CPU, tối đa 2 vòng sửa theo traceback
  G  Generalist Agent       few-shot trên một view bảng khác (header-path records)
  └► Answer Canonicalizer (no LLM) → canonical keys (yes/no, số, ngày, list không thứ tự)
Stage 3  Consensus & Verification
  Agree? (no LLM)
   ├─ agree ─────────────────────────────────────────────► Formatter
   ├─ disagree ─► Execution-grounded Adjudicator
   │              (sinh chương trình phân biệt, chạy, LLM quyết dựa trên kết quả in ra;
   │               không phân xử được thì numeric/list/multi-cond theo P, lookup/why theo text)  ► Formatter
   └─ có Null bất kỳ hoặc câu Why ─► Answerability Agent (chỉ thành phần này được xuất Null)
                 Identify missing evidence → Search table (no LLM) → re-answer có trích cell, hoặc confirm Null
                 + kiểm quan hệ nhân quả cho Why (EXPLICIT / CO-OCCURRING / NONE)          ► Formatter
Stage 4  Output
  Answer Formatter (theo loại đáp án, xuất một đáp án: chọn từ yes/no theo cách hỏi, định dạng
                    số/ngày học từ train; chỉ free-text mới dùng LLM) ─► Final Answer
  Dev-split Calibration: luật formatter, ngưỡng gate, ngưỡng Null (khai báo rõ trong paper)
```

### 4.1. Lý do của từng mảnh

| Mảnh | Lý do | Bằng chứng |
|---|---|---|
| Program Agent (P) | Đây là nguồn diversity duy nhất đã được đo trên bảng ở cùng ngân sách, và lỗi của nó khác loại. Text sai vì đọc nhầm bảng, code sai vì lỗi lập trình | Mix-SC (2312.16702, NAACL'24) trộn text và Python được 73,06, so với 66,39 khi chỉ dùng text ×10 và 61,39 khi chỉ dùng Python ×10. FlexTaF-Vote (2408.08841) nâng Llama3-8B trên WikiTQ từ 49,1 lên 55,7. Đội hạng 2/100 ở SemEval-25 Task 8 dùng đúng quy trình lọc đáp án invalid, vote, rồi mới gọi arbiter khi không đồng thuận. Chính paper POMA đã đề xuất "deterministic symbolic tools for counting and ranking" ở Future Work |
| Generalist (G) trên view khác | Voter đối chứng, đồng thời chính là baseline FS trong ablation | Vote khi POMA ≠ FS cho +2,12 EM [ĐO]. MFA (2604.12491) thấy bất đồng giữa các định dạng bảng mang thông tin ngang self-consistency |
| Gate kiểu MoT (text vs program) | Tiền lệ trực tiếp cho việc escalate dựa trên CoT và PoT có cho cùng đáp án hay không | MoT cascades (2310.03094, ICLR'24) ngang GPT-4-CoT-SC với khoảng 40% chi phí, và verifier LLM viết bằng prompt thua answer consistency |
| Adjudicator có chạy code | Tự sửa lỗi mà không có feedback bên ngoài thì kết quả tệ đi. Có feedback từ việc chạy code thì kết quả tốt lên | 2406.01297, 2310.01798; ablation của S\*; blog Weng (5/2025); bài harness design của Anthropic (3/2026) cho thấy judge cùng model chấm quá dễ dãi |
| Answerability Agent riêng, chạy trên mọi Null | Open-ViTabQA chấm Null như một đáp án, nên một bước kiểm correctness mà lùi về Null chỉ có thể làm hại. Dư địa nằm ở false abstention. Sửa hết 53 thì Null-F1 lên khoảng 0,85, còn sửa hết 11–12 hallucination chỉ lên khoảng 0,63 | Identify-then-Verify (2512.06476, EACL'26 Findings) với Llama-3.1-8B gần bằng GPT-4o. Sufficient Context (2411.06037, ICLR'25). Two Axes (2607.08456) tách hai trục, nhưng trong paper đó các tín hiệu answerability lấy qua API đều yếu (AUROC 0,54–0,66), nên v3 kiểm bằng căn cứ trong bảng chứ không để model tự đánh giá |
| Formatter một đáp án | Toàn bộ lợi thế của best-of-K là format. Học luật chọn từ yes/no theo cách hỏi từ tập train là hợp lệ và rẻ | Khoảng +3,53 EM single-answer [ƯỚC]. Breunig (1/2025) khuyên chuẩn hóa tất định trước, chỉ đưa phần mơ hồ cho LLM |

### 4.2. Kế thừa, thay đổi và loại bỏ

Từ v1, v3 giữ hint predictor, router, 10 specialist prompt (giờ đóng vai voter S), Flatten V1 và phần tất định của AN. Từ poma2, v3 giữ aggregation bất đối xứng (một chỗ nhìn mọi output), escalation có điều kiện, việc tách hai trục và single answer.

Phần thêm mới gồm Program Agent, Generalist trên view khác, adjudicator có chạy code, Answerability Agent (Identify-then-Verify, dò bảng, kiểm nhân quả cho Why), formatter học từ train và calibration trên dev.

Phần bỏ đi gồm Aggregator-LLM ở mọi câu, OW/ISP, MARGIN, COMPETE, LofreeCP, trigger chỉ-hedge, S\* không chạy code và LLM row/col critic.

### 4.3. Chi phí [ƯỚC]

v1 tốn khoảng 4,1 call mỗi câu (hint, refiner, 1,11 specialist, AN), trung bình 19,2k token. Riêng hint predictor đọc cả bảng đã chiếm khoảng 7k token trong số đó.

v3 gồm các call sau:
- Analyzer 1 call. Có thể ablate bản chỉ đọc câu hỏi và dòng header để tiết kiệm khoảng 7k token.
- S 1,11 call. P 1 call cộng tối đa 2 lần sửa, và chỉ nhận schema với vài dòng mẫu nên ít token.
- G 1 call.
- Adjudicator 1–2 call ở khoảng 20–30% số câu. Tỉ lệ bất đồng POMA-FS đo được là 22%.
- Answerability 1–2 call ở khoảng 10–15% số câu.

Cộng lại khoảng 1,2–1,5 lần token của v1, vẫn dưới $5 cho một lượt test trên Qwen3-8B. Vì v3 dùng nhiều token hơn, mọi so sánh phải có baseline cân compute, tức FS self-consistency @k với cùng tổng token.

### 4.4. Rủi ro đã biết của v3

- Program agent ở cỡ 8B có thể giòn. ReAcTable chỉ đạt 2,5% trên Llama3.1-8B. Bảng merged-cell và cách viết số kiểu Việt ("1.234.567", "3,5") dễ làm code chạy sai. Cách giảm rủi ro là tiền xử lý tất định: ghép header thành path "L1 › L2", đặt alias cột c0…cn, parse số kiểu Việt, và dùng pandas thay SQLite vì `lower()` và `LIKE` của SQLite chỉ xử lý ASCII.
- Có mức phạt cho ngôn ngữ không phải tiếng Anh. MultiSpider mất 6%, MULTITAT mất 19%.
- Gate sẽ bật nhiều hơn, nên precision của adjudicator quyết định kết quả. Phải đo TPR và TNR của adjudicator trên dev.
- Kết quả "abstain" hay "error" của P không được tính là Null. Program trả rỗng chưa đủ để kết luận Null, text path cũng phải nói Null.
- Gemma-3-4B có thể viết code yếu. Đừng để P thắng mặc định trên backbone yếu, và phải tune luật fallback riêng cho từng backbone.

---

## 5. Kế hoạch thí nghiệm

Bước đầu tiên là pilot trên dev, chỉ dùng CPU và API, tốn khoảng $3–5. Chạy S, P, G trên 991 câu dev, log đầy đủ, rồi đo:
- độ chính xác của từng voter,
- co-failure của từng cặp (cả hai cùng sai), so với mức kỳ vọng nếu hai voter độc lập,
- tỉ lệ agree-while-wrong của cả nhóm voter, cũng là trần của mọi gate,
- recall của gate, tức P(gate bật | đáp án cuối sai),
- oracle-of-3.

Nếu co-failure(S,P) không thấp hơn rõ so với co-failure(S,FS), hiện đang gấp 2,30 lần mức độc lập, thì P không mang lại diversity. Khi đó dừng lại xem xét trước khi viết thêm code.

Các so sánh chính chấm single-answer cho mọi hệ, dùng cùng một evaluator đã đóng băng, cùng formatter, và cùng Answerability Agent khi áp dụng được.

| Hệ | Vai trò |
|---|---|
| FS + formatter | Baseline đơn agent mạnh nhất |
| FS-SC@k cân token với v3, + formatter | Baseline cân compute. Reviewer chắc chắn sẽ đòi |
| POMA v1 single-answer + formatter | Bản trước |
| POMA v3 | Đề xuất |

Các ablation bắt buộc:
- −P, −G và −S (bỏ routed specialist, chỉ giữ P và G). Tôi coi −S là ablation quan trọng nhất. Nếu −S gần bằng bản đầy đủ thì specialization theo role không đóng góp gì, và paper phải nói thẳng rằng giá trị multi-agent đến từ việc trộn các cách suy luận khác nhau.
- Ba biến thể gate: không có adjudicator (dùng majority hoặc luật theo loại câu), adjudicator có chạy code, và adjudicator chỉ dùng LLM.
- Answerability với trigger chỉ-hedge so với trigger mọi-Null ở cùng số call, và bật hoặc tắt bước kiểm nhân quả cho Why.
- Thinking mode của Qwen3 bật và tắt cho verifier. AbstentionBench (2506.09038) thấy reasoning làm khả năng abstain giảm khoảng 24%.

Chỉ số và thống kê cần báo cáo:
- EM/F1/R1/MET single-answer. Best-of-K chỉ ghi như oracle upper bound và nói rõ như vậy.
- P/R/F1 của lớp Null và lớp Answerable, kèm số false abstention và hallucination.
- EM theo số call, theo loại câu và theo cấu trúc bảng.
- Paired bootstrap cluster theo bảng, vì các câu cùng bảng tương quan với nhau.
- Pin provider trên OpenRouter. Cùng một open model có thể lệch từ 36% đến 93% tùy provider (Willison, 8/2025).
- Hai backbone Qwen3-8B và Gemma-3-4B, đã có sẵn trong `run_q2_experiments.ps1`.

Claim multi-agent thất bại nếu hiệu giữa v3 và (FS + formatter + Answerability Agent) có CI chứa 0 trên cả hai backbone. Khi đó lối ra trung thực là viết một paper phân tích, với kết luận kiểu "Với Vietnamese table QA ở backbone 8B, role diversity gần như không tạo ra bất đồng có ích (88,7% câu chỉ route một specialist, 1,4% có bất đồng). Lợi ích đến từ canonicalization và các voter khác phương pháp." Kết quả đó vẫn đăng được ở LRE hoặc TALLIP.

---

## 6. Novelty và framing

Phần này dựa trên kết quả của Agent 5.

Những paper phải trích và phân biệt, nếu không reviewer sẽ tự nêu:
- MoRE (2305.14628, EMNLP-F'23) có specialist theo loại reasoning, một selector nhìn mọi output, feature đồng thuận, và abstain theo ngưỡng. Đây là prior art gần nhất của chính POMA v1, và paper hiện chưa trích.
- MATA (2602.09642, ACL-F'26) có agent CoT/PoT/SQL chạy code, một judge nhìn mọi candidate, và escalation theo ngưỡng confidence. POMA v3 khác ở chỗ không có thành phần nào phải train, trong khi scheduler và confidence checker của MATA đều phải train. v3 cũng có nhánh answerability mà MATA không có.
- MoT cascades, Mix-SC, SynTQA, MACT, PanelTR, AgentAuditor, ReConcile, USC, MoA.
- ViPanelTR (MAPR 2026, cùng nhóm) và Son et al.

Son et al. đăng ở ICCCI 2025 (CCIS 2747, tr. 454–467), nhóm tác giả ở UIT, có thầy Đặng Văn Thìn. Overlap thấp. Bài dùng một model GPT-4o sinh code Python/SQL trên bản dịch tiếng Việt của DataBench, không dùng Open-ViTabQA và không multi-agent. Vì có chung tác giả nên vẫn phải trích. Reviewer cũng có thể đòi baseline text-to-Python kiểu Son et al. trên Open-ViTabQA, và chạy riêng P agent của v3 là có luôn baseline này.

Không nên claim những điều sau vì đã có người làm:
- "first multi-agent Vietnamese table QA" (đã có ViPanelTR, POMA, và agent ở VLSP 2025 NumQA),
- "disagreement-gated verification" (MoT, MACT, PanelTR, MATA, DART),
- "confidence-weighted consolidation" (ReConcile, CISC),
- "two-axis answerability" như một khái niệm mới (Wagner, Joren et al.).

Những claim bảo vệ được đều hẹp:
1. Training-free, chỉ gọi API, không có thành phần nào phải train. Điểm này phân biệt v3 với MATA, TabLaP và SynTQA-RF.
2. Phân tích có kiểm soát giữa ba nguồn diversity (role, cách suy luận, sampling), cân compute, trên model nhỏ, bảng merged-cell và một ngôn ngữ ít tài nguyên. Agent 5 không tìm thấy paper nào làm đúng việc này, và trace của chính POMA đã cho kết quả âm rất rõ với role diversity.
3. Answerability như một agent riêng cho table QA, nơi Null là một đáp án được chấm điểm, kèm bước kiểm nhân quả cho câu Why.

Framing tôi đề xuất: *"A training-free, cost-aware multi-agent orchestration for low-resource-language table QA in which diversity comes from mixing text and program reasoning rather than from role prompts, with execution-grounded adjudication, a dedicated answerability agent, and a controlled analysis of where multi-agent gains come from."*

Có một rủi ro nộp trùng cần xử lý trước. README của repo ghi POMA đang nằm ở vòng review của KAIS. Nếu POMA v3 là bản thảo mới thì không được nộp song song khi bản cũ còn đang review. Phải rút bản cũ hoặc chờ kết quả, và disclose rõ POMA v1 cùng ViPanelTR.

---

## 7. Lỗi số liệu mới phát hiện trong paper hiện tại

Các lỗi này phải sửa dù chọn kiến trúc nào.

| # | Vấn đề | Bằng chứng [ĐO] | Cách sửa |
|---|---|---|---|
| 1 | Table 6 so hai tập khác nhau | "w/o AN" 68,41 bằng đúng 405/592 (tập có trace), còn "with AN" 80,24 là 796/992. Trên cùng 592 câu thì 68,24 → 79,56 | Báo cáo trên cùng một tập, tốt nhất là 992 câu sau khi chạy lại với log đủ |
| 2 | "177 flips / 17,84%" không tái lập được | Trace cho 67 flip trên 592 câu, không có flip nào từ đúng thành sai. Con số 177 trùng đúng 796 − 619, tức POMA trừ ZS | Viết lại §5.6 |
| 3 | Thiếu trace cho 400/992 câu | Log từng specialist chỉ có ở vị trí 400–991 (hp) và 371–991 (no_hp), trông như một run bị resume | Chạy lại với log đầy đủ |
| 4 | Evaluator drift | Evaluator hiện tại cho FS 67,34, ZS 63,10, CoT 59,48, TD 59,98 (paper ghi 67,14, 62,40, 59,17, 59,38). R1/MET của POMA là 84,48/85,17 (paper ghi 86,07/84,50) | Đóng băng một evaluator và chấm lại mọi hệ |
| 5 | Fig. 2 không khớp output | Output hiện tại cho Null-F1 của POMA là 52,24 và của FS là 59,20 (paper ghi 51,13 và 56,64) | Tính lại Fig. 2 |
| 6 | Claim "predicted > gold hints" đảo chiều | Evaluator hiện tại cho 80,24 (predicted) vs 80,34 (gold), single-answer 67,74 vs 68,35 | Bỏ claim |
| 7 | File ablation là gpt-4o-mini, không phải GPT-4o hay Qwen | Hồi quy cost theo token khớp đúng giá $0,150/$0,600 mỗi triệu token. File hp chỉ có 395 bản ghi | Không dùng. Ghi chú lại hoặc xóa |
| 8 | Code trên đĩa khác code đã sinh output | AN có lỗi mojibake trong biến thể yes (`CĂ³`, `ÄĂºng`, `Pháº£i`), và luật list-variant hiện tại không khớp với run đã ghi | Sửa encoding, gắn tag commit cho từng run |
| 9 | `outputs/poma/hint_predictor/qas_test.json` là một run khác | Chỉ trùng hint với run chính ở 549/992 câu | Ghi rõ hoặc xóa |

---

## 8. Đính chính cho các file review trước

| File và mục | Nội dung cũ | Đính chính |
|---|---|---|
| `review-POMA-JIT.md` W2 | "Nếu 62,40 đúng thì POMA không-AN thấp hơn FS 4,7 EM, câu chuyện orchestration sụp đổ" | 62,40 không phải EM không-AN của Qwen. Mâu thuẫn đến từ việc lẫn tập 592 với tập 992, và 177 là POMA trừ ZS. EM không-AN thật vào khoảng 68,2 (best-of-K). Kết luận cuối vẫn giữ, vì chấm single-answer thì POMA ngang FS (+0,40, không có ý nghĩa) |
| `review-POMA-JIT.md` F8 và W4 | "12 hallucination (text ghi 11), 4,4× chứ không phải 4,8×" | Output hiện tại cho 11, text của paper đúng. Con số 12 suy ngược từ F1 = 51,13, mà F1 đó lại không khớp output (52,24). Tỉ lệ 53/11 = 4,8× là đúng |
| `review-POMA-JIT.md` F9 | "+70% token có lẽ vì predicted hint kích hoạt nhiều specialist hơn, tức K lớn hơn" | Số specialist chỉ tăng 2,6% (1,113 vs 1,085). Phần +70% đến từ việc hint predictor đọc toàn bộ bảng |
| `boosting-novelty-plan-POMA-v2.md` §2 | Gọi 2605.29800 và 2609.14438 là "hai paper lý thuyết" | 2605.29800 (Nine Judges) là nghiên cứu thực nghiệm, chỉ 2609.14438 là lý thuyết |
| `boosting-novelty-plan-POMA-v2.md` §3.1 | "Dedicated Feedback and Edit Models (2503.04378)" | Tên bản v2 hiện tại là HelpSteer3, và model ở đó phải train (70B), nên không dùng làm thành phần được |
| `boosting-novelty-plan-POMA-v2.md` §3.1 | MARGIN là "online calibration không cần train", DRE "sửa lỗi trên Qwen3-8B" | MARGIN cần nhãn cho mọi dự đoán. DRE trên Qwen3-8B chỉ được 1,1–1,8 pp, kể cả với critic nhìn thấy ground truth |
| `boosting-novelty-plan-POMA-v2.md` §4 | Son et al. "cùng đúng bài toán", rủi ro cao | Bài ở ICCCI 2025, khác dataset và khác phương pháp nên rủi ro thấp, nhưng vẫn phải trích |

---

## 9. Thứ tự thực hiện đề xuất

1. Sửa hạ tầng trước, vì mọi việc khác phụ thuộc vào nó. Đóng băng evaluator, sửa encoding của AN, chạy lại POMA v1 trên test với log đầy đủ, và chấm lại mọi baseline. Xong bước này là giải quyết được 9 mục ở §7. Đây vẫn là Tier 1 của `fix-plan-POMA.md` (runbook có sẵn, khoảng $15–25).
2. Xác nhận trạng thái bản đang review ở KAIS trước khi đầu tư vào v3 (§6).
3. Pilot v3 trên dev, gồm P agent, G agent và đo co-failure (§5). Mất khoảng 1–2 ngày code và $3–5.
4. Nếu pilot đạt thì làm formatter trước vì rẻ nhất (khoảng +3,5 EM [ƯỚC]), sau đó tới gate và adjudicator có chạy code, rồi Answerability Agent. Ablate từng mảnh ngay trên dev.
5. Chạy test đúng một lần với cấu hình đã đóng băng, trên 2 backbone, bootstrap cluster theo bảng.
6. Viết paper theo framing ở §6. Nếu claim multi-agent thất bại (§5) thì chuyển sang paper phân tích.

---

## Phụ lục A. Nguồn chính, đã kiểm tra

Table QA và diversity:
- Mix-SC 2312.16702
- FlexTaF 2408.08841
- MoT cascades 2310.03094
- SynTQA 2409.16682
- MACT 2412.20145
- Orchestra 2601.03137
- H-STAR 2407.05952
- TableMaster 2501.19378
- RoT 2505.15110
- MFA 2604.12491
- DRE 2606.32029
- Table-Critic 2502.11799
- MATA 2602.09642
- MoRE 2305.14628

Answerability và abstention:
- Two Axes 2607.08456
- Sufficient Context 2411.06037
- Identify-then-Verify 2512.06476
- AbstentionBench 2506.09038
- Conformal abstention 2405.01563
- LofreeCP 2403.01216
- COMPETE 2402.00367
- Learn-then-Test 2110.01052
- COIN 2506.20178

Tương quan lỗi và aggregation:
- Nine Judges 2605.29800
- Condorcet latent 2609.14438
- Correlated errors 2506.07962
- Beyond Majority Voting 2510.01499
- MARGIN 2605.22949
- Minority Sentinel 2606.29270
- AgentAuditor 2602.09341
- Self-MoA 2502.00674
- Personas 2311.10054
- Debate vs voting 2508.17536
- Self-correction 2406.01297, 2310.01798

Blog:
- Anthropic, multi-agent research system (6/2025), harness design (3/2026), code execution with MCP (11/2025)
- Google Research, sufficient context (5/2025), scaling agent systems (1/2026)
- Samsung Research, SemEval-2025 Task 8
- Lilian Weng, "Why we think" (5/2025)
- Raschka, controlling reasoning effort (7/2026), using local coding agents (6/2026)
- Willison, inconsistent performance across providers (8/2025)
- Wolfe, stats for LLM evals (3/2026)
- Hamel, eval field guide
- OpenAI, why language models hallucinate (9/2025)

Tiếng Việt:
- Son et al., ICCCI 2025 (DOI 10.1007/978-3-032-10202-7_31)
- VLSP 2025 NumQA
- Open-ViTabQA (KBS 2025)

## Phụ lục B. File sinh ra trong phiên này

- `review-POMA-Boost-v2-architecture.md` là file này.
- `poma3.drawio.xml` và `poma3.drawio.png` là sơ đồ kiến trúc đề xuất, cùng style academic với poma2. Tôi không sửa poma2.
- `trace-analysis/` chứa báo cáo offline (`gate_headroom_report.md`), toàn bộ số liệu (`gate_headroom_results.json`) và script để chạy lại (xem `README.md` bên trong).
