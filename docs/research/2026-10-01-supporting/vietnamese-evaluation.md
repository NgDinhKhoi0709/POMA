# Vietnamese Table QA: dữ liệu, backbone và protocol thực nghiệm

Ngày kiểm tra: 01/10/2026. Đây là ghi chú hỗ trợ nghiên cứu; không thay đổi runtime, không chạy LLM và không xác nhận các điểm số đã ghi trong README.

## 1. Bằng chứng về dữ liệu và nghiên cứu đa ngôn ngữ

**Open-ViTabQA** là tên dataset chính thức: bài Knowledge-Based Systems, ngày 25/11/2025, DOI `10.1016/j.knosys.2025.114391`, công bố 9.911 QA, 329 bảng Wikipedia và 41 miền. Bài giới thiệu BIF kết hợp BERTScore và NLI; merged cells là một thách thức được khảo sát. Đây là benchmark đầu vào có bảng được cung cấp, không tự động suy ra yêu cầu truy hồi bảng trên toàn Wikipedia từ cụm “open domain”. [Bài gốc](https://www.sciencedirect.com/science/article/pii/S0950705125014303), [repository tác giả](https://github.com/DuzDao/Open-ViTabQA).

**M3TQA, Findings ACL 2026** là benchmark bổ sung đáng chú ý: bản xuất bản nêu 97 ngôn ngữ, 6.606 QA trong M3TQA-BENCH; Appendix Table 8 ghi Vietnamese `vi`: 429 train và 78 test. Dataset được mở rộng từ nguồn Trung/Anh nên có đặc điểm dịch đa ngôn ngữ, khác với bảng Wikipedia tiếng Việt gốc. Có thể dùng 78 mẫu tiếng Việt như kiểm tra chuyển miền nhỏ; không đủ để thay thế Open-ViTabQA. Bài có phần huấn luyện, nhưng việc chỉ đánh giá checkpoint có sẵn trên benchmark phù hợp giới hạn không train. Không dùng con số 2.916 QA của preprint 2025 thay cho bản published. [Bản xuất bản](https://aclanthology.org/2026.findings-acl.1134/), [PDF, Appendix Table 8](https://aclanthology.org/2026.findings-acl.1134.pdf).

**MultiTAT, Findings EMNLP 2025** phân tách linking bằng ngôn ngữ gốc và reasoning qua Python ở tiếng Anh. Bài cho thấy suy luận bằng tiếng Anh đơn thuần không giải quyết hết khó khăn liên kết chứng cứ. Đây là tiền lệ phù hợp cho agent định vị ô tiếng Việt → agent lập chương trình → agent kiểm chứng. [Bài xuất bản](https://aclanthology.org/2025.findings-emnlp.33/), [mô tả phương pháp](https://arxiv.org/html/2502.17253v1). Repository chính chủ liệt kê 11 ngôn ngữ gồm tiếng Anh và 10 bản dịch, **không có tiếng Việt**; dùng như nguồn phương pháp, không gọi là Vietnamese benchmark. [Repository](https://github.com/zhxlia/MULTITAT).

**XLT, Findings EMNLP 2023** dùng cross-lingual-thought prompting, không cập nhật tham số. Đây là cơ sở cho ablation “plan tiếng Việt” so với “plan tiếng Anh”, nhưng bằng chứng không phải kết quả trực tiếp trên Qwen3-8B/Open-ViTabQA. [Bài gốc](https://aclanthology.org/2023.findings-emnlp.826/).

**ViPanelTR: A Multi-Agent Framework for Vietnamese Table Question Answering** xuất hiện trong danh sách bài được chấp nhận MAPR 2026, paper ID 10. Chỉ xác minh được tên và acceptance; chưa có full paper/code trong các nguồn đã kiểm tra để xác nhận kiến trúc, backbone hoặc yêu cầu train. Cần đối chiếu trước khi tuyên bố tính mới, đặc biệt “first Vietnamese multi-agent Table QA”. [Nguồn hội nghị](https://mapr.uit.edu.vn/list-accepted-papers-mapr-2026).

## 2. Kiểm tra trực tiếp repository POMA

Nguồn là các tệp local đọc ngày 01/10/2026, không phải khẳng định từ paper. JSON QA có wrapper `qas`, JSON bảng có wrapper `table`. QA chứa `qa_id`, `table_id`, `question`, `answer`, `hints`; bảng chứa HTML, title, domain, type và bản flattened.

| Split local | QA | Bảng duy nhất | Gold `Null`/`Nul` |
|---|---:|---:|---:|
| train | 7.928 | 329 | 346 |
| dev | 991 | 296 | 41 |
| test | 992 | 289 | 46 |

Nguồn: `dataset/qas_train.json`, `qas_dev.json`, `qas_test.json`, `table.json`.

Giao bảng train–dev = 296, train–test = 289, dev–test = 271. Nghĩa là mọi bảng của test đều có câu hỏi ở train. Đây là protocol **câu hỏi mới trên bảng đã thấy**; không tự thân là lỗi dataset hay leakage, nhưng không chứng minh khái quát hóa sang bảng chưa thấy. Nếu dùng few-shot retrieval, cần tránh lấy exemplar có cùng bảng với mẫu đánh giá khi muốn khảo sát transfer thực sự.

329 bảng có nhãn `normal` 146 lần, `contain_merged_header` 93 lần, `contain_merged_value` 132 lần. Nhãn là multilabel nên tổng vượt 329. Báo metric theo merged-header và merged-value riêng, không coi ba nhóm mặc định loại trừ nhau.

POMA hiện có hint predictor, question refiner, router tất định, specialist song song và answer normalization. Baseline direct/CoT/task-decomposition/few-shot đã tồn tại; có AST executor, table search và finalizer dùng một đáp án. Có thể tận dụng thay vì dựng framework mới. Nguồn: `README.md`, `src/orchestration/pipeline.py`, `src/agents/router.py`, `src/table_executor/`, `poma_v3lite/table_search.py`, `src/finalization/`.

Tài liệu local `docs/research/2026-09-26-memxam-multi-agent-qwen3-8b.md` đã ghi thực nghiệm MemXam-SC-KV trên Qwen3-8B tự host, dev/test subset 200. Theo báo cáo đó, nguồn lợi chính là train-QA memory cùng bảng; lợi ích riêng của đối chất chưa tách được khỏi bỏ phiếu. Có kết quả âm cho judge/verifier và parse-critic; không nên mặc định thêm verifier chắc chắn cải thiện. Đây là kết quả lịch sử được đọc lại, **không reproduce hoặc kiểm định lại trong lượt này**. Phương pháp mới phải đối chiếu kNN-FS/kNN-SC3 với cùng memory, không chỉ few-shot bốn ví dụ.

**Rủi ro đánh giá đã xác minh:**

- `run_eval.py` mặc định `--candidate-policy all`. `evaluation/exact_match.py` dùng any candidate khớp; `f1.py` dùng candidate có F1 cao nhất theo reference. `bif_score.py` cũng chọn max-BIF theo gold và bỏ mẫu prediction trống trong denominator BIF. Đây là oracle đánh giá nếu nhiều phương án đầu ra, không tương đương chọn đáp án online.
- Primary result phải xuất **một đáp án cuối cùng** cho mỗi QA và dùng `--candidate-policy single-required --strict`. Oracle best-of-K, oracle hint và oracle evidence chỉ dùng chẩn đoán, ghi riêng.
- `--use-dataset-hints` sử dụng nhãn reasoning đã annotated: chỉ đặt vào arm oracle. Batch CLI hiện mặc định predicted hints; phải ghi lại `hint_source` ở từng run, không chỉ tin setting mặc định.
- README cảnh báo adapter Chain-of-Query hiện là `coq_base_sql_fallback` do thiếu clause-agent modules. Không gọi kết quả đó là full Chain-of-Query.

Lệnh đánh giá có sẵn, sau khi hệ thống đã tạo prediction một đáp án:

```powershell
conda run -n kltn python run_eval.py --pred outputs/experiment/final.json --qas dataset/qas_test.json --tables dataset/table.json --candidate-policy single-required --strict
```

## 3. Hai backbone và kiểm soát inference

Qwen3-8B có 8,2B tham số, context native 32.768 tokens; 131.072 cần cấu hình YaRN. Không mặc định coi 128K là context local sẵn có. [Model card chính chủ](https://huggingface.co/Qwen/Qwen3-8B).

Qwen mặc định bật thinking. `enable_thinking=False` là hard switch; `/no_think` là soft switch khi thinking được bật. Thinking khuyến nghị temperature 0,6/top-p 0,95/top-k 20; non-thinking 0,7/0,8/20. Tránh greedy cho thinking theo hướng dẫn tác giả. Không truyền nguyên thinking history giữa agents. [Model card, usage](https://huggingface.co/Qwen/Qwen3-8B), [Qwen vLLM docs](https://qwen.readthedocs.io/en/latest/deployment/vllm.html).

GPT-4o mini có context 128.000, tối đa 16.384 output tokens, text/image input và text output; hỗ trợ function calling/structured outputs. Snapshot được docs liệt kê là `gpt-4o-mini-2024-07-18`. [OpenAI model docs](https://developers.openai.com/api/docs/models/gpt-4o-mini).

**Đề xuất protocol, không phải kết quả đã chứng minh:** bảng chính gồm Qwen non-thinking và GPT-4o mini, cùng nguồn bảng textual/HTML đã parse; thinking Qwen là arm riêng. Giới hạn context chung theo Qwen native hoặc phép chọn vùng giống nhau. Agent roles đều dùng cùng backbone trong từng arm. Heterogeneous Qwen+GPT là nghiên cứu mở rộng riêng.

Không ép hai tokenizer có cùng số token rồi xem như thông tin đầu vào giống nhau: cung cấp cùng ô/chứng cứ, báo usage từng tokenizer. Khóa model revision, quantization, backend/provider, prompt/schema, truncation và decoding trong manifest. Trong repo alias `qwen3-8b` đi qua OpenRouter/Alibaba; nó không tự chứng minh cùng runtime với local checkpoint. Wrapper vLLM local hiện gọi chat template không set thinking và sampling temperature 0; cần audit cấu hình trước khi dùng Qwen thinking. Đây là nhận xét mã nguồn, chưa thử inference. Nguồn: `baseline/llm_client.py`, `src/services/local_vllm_client.py`, `src/config/settings.py`.

## 4. Protocol tối thiểu để trả lời câu hỏi khoa học

**Câu hỏi chính:** ở cùng ngân sách inference, phân vai gắn chứng cứ có cải thiện một đáp án cuối cùng, tính đúng số và khả năng từ chối câu ngoài bảng hay không?

Không train/fine-tune là không cập nhật weights. Dùng train để chọn few-shot và dev để chọn prompt/gate vẫn là model selection; phải ghi rõ. Không dùng test gold, test hint, test oracle score để chọn prompt/threshold/route/answer. Nếu test này đã được dùng nhiều lần để phát triển POMA thì freeze bây giờ không biến nó thành blind test: báo là reused benchmark và bổ sung untouched holdout/new tables khi khả thi. Thiết kế grouped-by-table hoặc grouped-by-source-page nên giữ mọi QA cùng bảng/page trong cùng split; công bố đó là split bổ sung, không thay tên official test.

| Arm tối thiểu | Mục đích |
|---|---|
| Direct và CoT, một đáp án | Mốc đơn giản, cùng preprocessing |
| Single agent + tools/AST | Tách lợi ích executor khỏi multi-agent |
| Self-consistency + selector, cùng call/token cap | Tách lợi ích tăng compute khỏi phân vai |
| kNN-FS và kNN-SC3 cùng train-only memory | Baseline mạnh theo báo cáo MemXam local; tách memory khỏi agency |
| POMA hiện tại, single-final answer/predicted hints | Đối chiếu cải tiến với hệ thống local |
| Phương pháp đề xuất đầy đủ | Evidence agent → solver → verifier; bounded repair |

Ablation ưu tiên: bỏ verifier; bỏ executor; bỏ định vị chứng cứ; native-only so với plan tiếng Anh; một representation so với view phụ; có/không memory và same-table/leave-table-out memory. Mỗi lần chỉ thay thành phần đang khảo sát và giữ budget. Có thể tái sử dụng cùng candidates tầng đầu cho nhánh vote và nhánh tương tác để ghép cặp sạch hơn. Oracle hints/evidence/best-of-K không nằm chung bảng chính.

**Ngân sách đề xuất ban đầu:** 3 lời gọi thường (evidence/plan, solver, verifier/finalizer), tối đa 5 nếu có một vòng sửa solver→verifier. Python/AST execution tất định không tính là LLM agent; vẫn tính tool invocations/time. Nếu dùng hai solver độc lập song song thì 4 calls thường, cap 6. Chọn một biến thể trước khi test, không trộn hai con số.

Khởi đầu tổng output cap 4.096 tokens/QA cho non-thinking; phân bổ theo vai rồi pilot trên dev. Thinking cần budget riêng, cộng cả reasoning tokens và đo tỷ lệ truncated/không ra final JSON. Không ngầm dùng output 4.096 riêng cho mỗi agent rồi gọi đó là cùng ngân sách với baseline 4.096 tổng. Token input lớn vì bảng lặp qua calls cũng phải báo; dựng đường accuracy–total-tokens–latency thay vì một điểm số. Retry/schema repair tính vào budget và lỗi hết retry là failure, không bỏ câu khó. Các mức trên là điểm xuất phát cần pilot, không phải ngưỡng tối ưu phổ quát.

**Metrics chính:** single-answer EM và token F1; thêm exact numeric/unit/date/list correctness với canonicalization đã khóa. Giữ dấu tiếng Việt; NFC và khoảng trắng được chuẩn hóa. Với list cần phân biệt tập không thứ tự và ranking có thứ tự; không tự split mọi dấu phẩy vì có thể là số thập phân hoặc chuỗi có dấu phẩy. Báo answerability macro-F1 và riêng Null precision/recall: test chỉ 46/992 Null nên overall accuracy dễ che lỗi từ chối. BIF/ROUGE/METEOR là bổ sung, không thay tính đúng số và entailment từ bảng. BIF dựa reference/prediction không tự xác nhận evidence grounding; dùng checkpoint NLI có sẵn là evaluation, không yêu cầu train phương pháp QA.

Báo theo toán/đa điều kiện/lookup/list/why-how, bảng merged, độ dài bảng, và nguồn answerability. Gold hints chỉ dùng stratification sau inference. Trace ghi evidence cell IDs, kết quả executor, route, verifier decision, output/token/calls/latency và parse/retry failures. Chấm manual một tập dev nhỏ có evidence gold nếu dataset thiếu; freeze annotation trước so sánh. Không dùng judge chính là backbone đang được quảng bá làm nguồn đánh giá duy nhất.

**Thống kê:** paired bootstrap difference trên cùng QA IDs; ưu tiên cluster bootstrap theo `table_id` vì nhiều QA chia sẻ cùng bảng, có thể bổ sung QA bootstrap để đối chiếu. Repo đã có paired QA bootstrap trong `evaluation/bootstrap.py`, chưa xác minh cluster variant. Repeated decoding 3 seeds trên dev/final shortlisted arms nếu sampling stochastic và ngân sách cho phép; công bố CI và cost distribution, không claim ý nghĩa thống kê từ một run.

**Robustness bổ sung:** paraphrase tiếng Việt được kiểm chứng giữ nghĩa; NFC/NFD; đổi thứ tự hàng với QA không phụ thuộc vị trí; alias column; distractor row. QA ranking/“hàng đầu tiên” không được đổi hàng tùy ý. Noise strength và ngưỡng reject phải chọn trên dev; không hứa một threshold phổ quát. Dùng bảng mới hoặc counterfactual cell values được kiểm chứng để giảm suy luận từ trí nhớ, nhưng không coi chúng là bằng chứng đã loại trừ hoàn toàn pretraining contamination.

## 5. Hướng đề xuất có khả năng tạo đóng góp thực nghiệm

Ưu tiên **multi-agent định vị chứng cứ + thực thi toán có kiểm chứng + sửa có điều kiện**, tận dụng parser/AST/table search/finalizer có sẵn. Đặc thù tiếng Việt nằm ở entity alias, dấu/Unicode, số và đơn vị, phủ định/điều kiện kết hợp, và bảo toàn header ancestry qua merged cells. Không cần một agent riêng cho mọi từ hỏi. Đóng góp nên là cơ chế chứng cứ/verification và chứng minh budget-matched, thay vì chỉ đặt tên mới cho nhiều prompts.

Hướng hai, scope hẹp hơn: native-language evidence agent và English-plan agent với shared cell IDs, final answer tiếng Việt. Ablation trực tiếp theo MultiTAT/XLT; giữ tên riêng và dữ liệu ô gốc, tránh dịch nguyên bảng tạo thêm lỗi. **Giả thuyết:** lợi ích có thể tập trung ở chương trình toán; phải đo vì không có nguồn đã xác nhận trên hai backbone này.

Hướng ba: verifier phát hiện thiếu evidence rồi gọi search/table view bổ sung tối đa một lần. **Giả thuyết:** giảm hallucination/Null sai dưới bảng dài; cần so với always-repair và no-repair cùng chi phí, đồng thời đo verifier sửa đúng thành sai.
