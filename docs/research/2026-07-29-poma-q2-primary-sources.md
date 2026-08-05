# POMA Q2: lựa chọn thực nghiệm dựa trên nguồn sơ cấp

Ngày tra cứu: 2026-07-29.

## Kết luận khuyến nghị

Gói thực nghiệm có tỷ lệ công sức/giá trị phản biện tốt nhất gồm:

1. **Cross-lingual có đối chứng:** chạy POMA trên cặp tiếng Việt–tiếng Anh của **M3TQA-Bench**, giữ cùng nguồn bảng và loại câu hỏi để đo chênh lệch theo ngôn ngữ.
2. **Cross-dataset:** chạy bản tiếng Anh của **WikiTableQuestions (WTQ) v1.0.2**, split `pristine-unseen-tables`, bằng official evaluator. Đây là bằng chứng chuyển miền tốt hơn việc chỉ đổi seed trên cùng dữ liệu POMA.
3. **Native Vietnamese audit set:** nếu pipeline không thể hỗ trợ WTQ, hoặc để khắc phục việc M3TQA là dữ liệu dịch, xây một test-only audit set từ bảng tiếng Việt xuất bản gần đây bởi nguồn chính thức; không dùng tập này để chỉnh prompt.
4. **Backbone generalization:** thêm `google/gemma-3-12b-it` làm backbone chính thứ hai. Nếu đủ ngân sách, thêm `meta-llama/Llama-3.1-8B-Instruct` như một stress test 8B, nhưng phải ghi rõ Meta không liệt kê tiếng Việt trong tám ngôn ngữ được hỗ trợ chính thức.
5. **Đánh giá nghiêm ngặt:** báo cáo single-run deterministic, nhiều seed/sample, oracle `pass@K` chỉ như upper bound, paired bootstrap CI trên cùng câu hỏi/bảng, và một robustness suite nhỏ với perturbation bảo toàn đáp án.

Không nên dùng `VietnameseTableVQA` như benchmark gold độc lập mà không audit: dataset card nói rõ câu hỏi–đáp án do Gemini-1.5-Flash sinh. Nó phù hợp hơn với vai trò **stress-test pool** để lấy mẫu và thẩm định thủ công.

## 1. Benchmark và audit set

### 1.1 M3TQA-Bench: lựa chọn ưu tiên cho cross-lingual

Paper ACL 2026 giới thiệu M3TQA với bảng được mở rộng từ nguồn tiếng Trung và tiếng Anh sang 97 ngôn ngữ. Bản cuối ghi M3TQA-Bench có 6.606 QA được kiểm tra thủ công; phụ lục liệt kê tiếng Việt (`vi`) có **78 mẫu test**. Benchmark bao gồm bốn loại tác vụ: numerical computation, cell extraction, factual verification và open-ended QA. Nguồn: [paper ACL 2026](https://aclanthology.org/2026.findings-acl.1134.pdf), [dataset chính thức của tác giả](https://huggingface.co/datasets/sdxvv/m3TQA-Bench).

Thực nghiệm đề xuất:

- Lấy toàn bộ subset `language == "Vietnamese"` và subset tiếng Anh tương ứng.
- So sánh trên cùng `table_type`, `answer_type` và nguồn QA; báo cáo macro theo bốn loại tác vụ, không chỉ một điểm gộp.
- Báo cáo `Vi`, `En`, và `gap = Vi - En`. Đây là phép đo cross-lingual có kiểm soát vì hai ngôn ngữ bắt nguồn từ cùng tập bảng.
- Dùng metric theo task của paper: Jaccard cho numerical/cell extraction, F1 cho factual verification, ROUGE-L cho open-ended; nếu dùng thêm evaluator POMA thì trình bày nó như metric phụ.

Giới hạn phải nêu:

- Dữ liệu gốc chỉ đến từ tiếng Trung/Anh rồi dịch; chính tác giả thừa nhận nó không nắm đầy đủ sắc thái văn hóa của ngôn ngữ đích. Vì vậy đây là **cross-lingual transfer**, không thay thế một corpus native Vietnamese.
- Paper ACL cuối ghi 2.916 QA do LLM sinh + 3.690 QA do người xây dựng = 6.606 và 78 mẫu test tiếng Việt. Kiểm tra trực tiếp revision dưới đây cho thấy 7.210 hàng tổng cộng và **82 hàng tiếng Việt**. Cần ghi revision, actual N sau filter và giải thích version drift thay vì chỉ ghi “latest”.
- Revision dataset đã kiểm tra: `sdxvv/m3TQA-Bench@54c1484ff6c9447c3b4a55dc856a7241b62903f9` (tra từ [HF dataset API](https://huggingface.co/api/datasets/sdxvv/m3TQA-Bench)).

### 1.2 WikiTableQuestions v1.0.2: lựa chọn ưu tiên cho cross-dataset

WTQ có 22.033 ví dụ; official repository chỉ dẫn train trên `training.tsv`, test trên `pristine-unseen-tables.tsv`, dùng `evaluator.py`, và `targetValue` có thể là danh sách phân cách bằng `|`. Nguồn: [trang chính thức](https://ppasupat.github.io/WikiTableQuestions/), [repository và evaluator chính thức](https://github.com/ppasupat/WikiTableQuestions).

Thực nghiệm đề xuất:

- Chỉ evaluation/zero-shot adaptation; không fine-tune hoặc chọn prompt trên test.
- Dùng release **v1.0.2** và split unseen-table.
- Chuyển output POMA thành danh sách denotation rồi chấm bằng official evaluator; giữ nguyên normalization số/ngày của benchmark.
- Báo cáo overall denotation accuracy và breakdown theo single-answer/multi-answer.

WTQ là tiếng Anh, nên kết quả chứng minh **cross-dataset/cross-language generalization của kiến trúc**, không trực tiếp chứng minh chất lượng tiếng Việt.

### 1.3 VietnameseTableVQA: chỉ dùng như stress-test pool có audit

Dataset card cung cấp bảng dạng ảnh, CSV và HTML, có subset `VNwtqa` 6,55k hàng và tổng 19.638 hàng. Tuy nhiên card nói rõ QA được Gemini-1.5-Flash sinh từ bảng Wikipedia tiếng Việt. Nguồn: [dataset card](https://huggingface.co/datasets/YuukiAsuna/VietnameseTableVQA). Revision đã kiểm tra: `96a40888df28991b6fd81fe96875ba3ad2a3daac`.

Nếu dùng, nên:

- Lấy stratified sample 200–300 câu từ trường HTML/CSV, không dùng ảnh nếu POMA là text-only.
- Hai người Việt kiểm tra độc lập tính trả lời được, đáp án và đơn vị; adjudicate bất đồng.
- Chỉ công bố kết quả trên phần audit-pass và công bố tỷ lệ loại. Không gọi toàn bộ dataset là human-verified benchmark.

### 1.4 Phương án native Vietnamese audit set nếu không có benchmark thứ hai phù hợp

Thiết kế tối thiểu đề xuất: 50 bảng × 4 câu = khoảng 200 QA, chỉ dùng test. Lấy bảng xuất bản năm 2025–2026 từ tài liệu tiếng Việt nguyên bản, ưu tiên [Cơ quan Thống kê Quốc gia: Data and statistics](https://www.gso.gov.vn/en/data-and-statistics/) và [Niên giám thống kê](https://www.gso.gov.vn/nien-giam/). TableEval dùng tài liệu thực tế gần đây để giảm leakage và phủ bốn miền government/finance/academia/industry; M3TQA dùng kiểm tra nhiều giai đoạn, kiểm tra bản dịch chéo và native-speaker validation. Pal et al. là tiền lệ TableQA low-resource thu thập bảng ngay trong ngôn ngữ đích thay vì chỉ dịch benchmark tiếng Anh. Nguồn: [TableEval, EMNLP 2025](https://aclanthology.org/2025.emnlp-main.363/), [M3TQA, ACL 2026](https://aclanthology.org/2026.findings-acl.1134.pdf), [Pal et al., EMNLP 2024](https://aclanthology.org/2024.emnlp-main.5/).

Protocol nên pre-register:

- Chia theo **table/document source**, không chia ngẫu nhiên theo câu hỏi.
- Cân bằng bốn nhóm: lookup/cell extraction, aggregation–arithmetic, comparison–ranking, multi-answer.
- Mỗi QA có answer set chuẩn hóa, đơn vị, cell evidence và phép tính/rationale ngắn.
- Hai annotator độc lập; adjudicator thứ ba xử lý bất đồng. Báo cáo agreement trước adjudication và tỷ lệ câu bị loại/sửa.
- Freeze tập audit trước khi chạy; không sửa prompt/agent sau khi xem lỗi. Nếu cần development set, lấy từ nguồn tài liệu khác.
- Phát hành danh sách URL, ngày truy cập, hash bảng đã trích và guideline annotation để có thể tái lập.

Các con số 50 bảng/200 QA là khuyến nghị thiết kế cho POMA, không phải ngưỡng do các paper nguồn quy định.

## 2. Backbone open-weight

### 2.1 Khuyến nghị chính: Gemma 3 12B IT

- Model ID: `google/gemma-3-12b-it`
- Revision pin đã kiểm tra: `96b6f1eccf38110c56df3a15bffe176da04bfd80`
- Model card của Google nêu: open weights, 12B, instruction-tuned, context 128K, hỗ trợ hơn 140 ngôn ngữ và phù hợp QA/reasoning. Nguồn: [official model card](https://huggingface.co/google/gemma-3-12b-it), [HF model API](https://huggingface.co/api/models/google/gemma-3-12b-it).
- Caveat vận hành: repository gated; phải chấp nhận Gemma Terms.

Đây là backbone thứ hai tốt nhất để kiểm tra kết luận POMA có phụ thuộc Qwen hay không: khác họ model, gần cùng scale, và có tuyên bố multilingual chính thức rộng.

### 2.2 Tùy chọn stress test: Llama 3.1 8B Instruct

- Model ID: `meta-llama/Llama-3.1-8B-Instruct`
- Revision pin đã kiểm tra: `0e9e39f249a16976918f6564b8830bc894c89659`
- Model card chính thức nêu 8B, 128K context, instruction-tuned và static release. Nguồn: [Meta model card](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md), [HF model/API](https://huggingface.co/api/models/meta-llama/Llama-3.1-8B-Instruct).
- Caveat quan trọng: tám ngôn ngữ hỗ trợ được liệt kê không có tiếng Việt; model card còn xem use ngoài tám ngôn ngữ là ngoài phạm vi hỗ trợ chính thức. Vì vậy kết quả tiếng Việt nên được gọi là stress test/transfer, không phải so sánh multilingual hoàn toàn ngang bằng.

Nếu ngân sách chỉ đủ một backbone bổ sung, chọn Gemma 3 12B IT; Llama chỉ thêm khi cần kiểm tra robustness qua ba họ model.

## 3. Protocol đánh giá

### 3.1 Multi-answer

Với câu có nhiều đáp án, chấm **tập denotation không thứ tự** sau normalization, không chấm chuỗi giải thích nguyên văn. WTQ biểu diễn target có thể là danh sách và cung cấp official evaluator có normalization số/ngày. Nguồn: [WTQ official repository](https://github.com/ppasupat/WikiTableQuestions).

Báo cáo tối thiểu:

- exact set match;
- set precision/recall/F1 hoặc Jaccard làm chẩn đoán;
- accuracy tách single-answer và multi-answer;
- lỗi thừa đáp án và thiếu đáp án.

Không trộn alternative references (nhiều cách viết cho cùng đáp án) với multi-answer (nhiều phần tử đều bắt buộc).

### 3.2 Oracle best-of-K / pass@K

Paper Codex định nghĩa `pass@K` là xác suất ít nhất một trong K mẫu đúng và đưa unbiased estimator khi sinh `n >= K` mẫu, có `c` mẫu đúng:

`pass@K = 1 - C(n-c, K) / C(n, K)`.

Paper cũng nói rõ đây là best-of-K do **oracle có trước ground-truth/unit tests** chọn, khác với selector có thể triển khai. Nguồn: [Chen et al., 2021, Sec. 2.1 và 3.3](https://arxiv.org/pdf/2107.03374).

Protocol đề xuất:

- Primary: greedy/temperature 0, `K=1`.
- Stochastic stability: 5 seed hoặc 5 samples với cùng temperature/top-p cho mọi hệ thống; báo cáo mean, SD và per-item consistency.
- Diagnostic upper bound: `pass@1`, `pass@3`, `pass@5` bằng estimator trên; ghi số mẫu, temperature và tổng token/cost.
- Nếu POMA chọn một answer trong K bằng confidence/voting, báo cáo riêng **selected@K**. Tuyệt đối không gọi oracle@K là accuracy triển khai.
- Mọi baseline phải có cùng sampling budget; không so POMA oracle@5 với baseline greedy@1.

### 3.3 Paired significance và confidence intervals

Koehn mô tả paired bootstrap: trên cùng test items, lặp lại việc lấy mẫu có hoàn lại, tính điểm cho cả hai hệ thống trên cùng resample, rồi ước lượng độ tin cậy của chênh lệch. Nguồn: [Koehn, EMNLP 2004](https://aclanthology.org/W04-3250.pdf).

Áp dụng cho POMA:

- Lưu per-item score/correctness cho mọi cấu hình.
- 10.000 paired bootstrap resamples; báo cáo `Δ`, 95% CI và two-sided p-value.
- Vì nhiều câu có thể dùng chung bảng, resample theo **table/document cluster**, không theo từng QA, để không giả định các câu cùng bảng độc lập. Đây là suy luận thiết kế từ yêu cầu giữ cặp và xử lý tương quan theo nguồn, không phải quy tắc được WTQ quy định.
- Xác định trước primary comparison (POMA vs mạnh nhất) và primary metric; các breakdown là secondary.

### 3.4 Robustness

RobuT xây perturbation cho table header, table content và question trên WTQ/WikiSQL-Weak/SQA; FREB-TQA yêu cầu đánh giá (i) thay đổi cấu trúc bảng, (ii) phụ thuộc đúng vào relevant cells thay vì bias, và (iii) numerical reasoning. Nguồn: [RobuT, ACL 2023](https://aclanthology.org/2023.acl-long.334/), [FREB-TQA, NAACL 2024](https://aclanthology.org/2024.naacl-long.137/).

Một suite nhỏ nhưng thuyết phục:

- shuffle hàng/cột khi semantics không phụ thuộc thứ tự;
- chuyển relevant row lên đầu/giữa/cuối;
- thêm hàng/cột distractor không liên quan;
- paraphrase header và question bằng người, giữ entity/numeral;
- thay đổi giá trị evidence rồi cập nhật gold answer để kiểm tra model có thực sự đọc bảng.

Báo cáo clean score, perturbed score, absolute drop, và **consistency** giữa cặp clean–perturbed. Tách answer-invariant perturbations khỏi counterfactual perturbations.

## 4. Ma trận chạy ưu tiên

| Mức | Thực nghiệm | Cấu hình tối thiểu | Giá trị cho claim |
|---|---|---|---|
| P0 | Backbone × POMA/baseline trên test hiện tại | Qwen3-8B + Gemma3-12B; cùng decoding | Không phụ thuộc một model |
| P0 | Paired bootstrap | 10k cluster resamples, 95% CI | Chênh lệch có độ tin cậy |
| P0 | M3TQA Vi–En | 78 Vi + matched En, breakdown theo task | Cross-lingual có kiểm soát |
| P1 | WTQ v1.0.2 | unseen-table + official evaluator | Cross-dataset |
| P1 | Robustness suite | 100–200 cặp clean/perturbed | Bền vững trước serialization/bias |
| P1 | Sampling | K=1/3/5, oracle và selected tách riêng | Stability và compute–accuracy |
| P2 | Native audit set | 50 bảng/200 QA, double annotation | External validity tiếng Việt |

Nếu thiếu compute/thời gian, ưu tiên P0 rồi WTQ hoặc native audit set; không nên dàn trải nhiều backbone mà thiếu significance, breakdown và kiểm soát evaluator.

## 5. Các rủi ro cần ghi thẳng trong paper

- M3TQA Vietnamese là translated benchmark và nhỏ (78 test); không đủ một mình để claim “general Vietnamese TableQA”.
- HF M3TQA và con số trong bản ACL cuối không khớp; bắt buộc pin revision, ghi filter và số mẫu sau preprocessing.
- VietnameseTableVQA là synthetic QA; chỉ dùng sau human audit.
- Llama 3.1 8B không hỗ trợ tiếng Việt chính thức; hiệu năng thấp không chứng minh POMA thất bại.
- Oracle best-of-K dùng gold để chọn nên chỉ là upper bound; claim chính phải dựa trên K=1 hoặc selector không dùng gold.
- Nếu chọn prompt/agent dựa trên audit/test errors thì tập đó không còn là held-out test.
