# Vì sao "POMA + GSA" giảm điểm so với "POMA (candidate-max)", và vai trò thật của Answer Normalization

Ngày: 2026-09-18. Phạm vi: giải thích chênh lệch điểm số nêu trong
[`outputs/q2_revision/qwen_baseline_comparison_candidate_max.md`](../../outputs/q2_revision/qwen_baseline_comparison_candidate_max.md)
(Qwen3-8B, `dataset/qas_test.json`, 992 câu) bằng cách đọc mã nguồn
(`src/agents/answer_normalization.py`, `src/agents/grounded_single_answer.py`,
`src/finalization/`, `evaluation/`) và chạy lại hai thí nghiệm bổ sung trên
artifact đã có, không gọi lại LLM. Tài liệu này không thay thế
[`2026-09-17-table-representation-small-lm.md`](2026-09-17-table-representation-small-lm.md)
cho vấn đề biểu diễn bảng; phần 5 chỉ bổ sung hai cơ chế mới phát hiện được
khi đọc GSA và client suy luận cục bộ.

## Tóm tắt

Báo cáo gốc so sánh ba số cho Qwen3-8B: POMA `candidate_policy=all`
(F1 83.42, EM 74.90 — **oracle best-of-K**, tự báo cáo là "không phải
selector có thể triển khai"), POMA + GSA (F1 81.21, EM 68.35 — một câu trả
lời, không oracle), và baseline tốt nhất Few-shot (F1 78.63, EM 67.34). Từ
đó dễ đọc thành "GSA làm giảm điểm của POMA". Sau khi chạy lại evaluator với
`candidate_policy=first` (chọn candidate đầu tiên, không oracle — hỗ trợ sẵn ở
[`evaluation/io.py:61`](../../evaluation/io.py)) trên đúng
`outputs/q2_revision/openrouter_qwen_qwen3-8b/full/raw/poma.json`, bức tranh
đổi khác:

| Biến thể | Có phải selector triển khai được? | F1 (%) | EM (%) |
|---|---|---:|---:|
| POMA `all` (oracle best-of-K, K trung bình 3.44, K tối đa 80) | Không | 83.4240 | 74.8992 |
| POMA `first` (candidate đầu tiên theo thứ tự routing, không oracle, không phải ranking theo độ tin cậy) | Có | 79.7990 | 66.6331 |
| **POMA + GSA** (LLM chọn/sửa/tổng hợp một câu trả lời) | Có | **81.2140** | **68.3468** |
| Few-shot (baseline tốt nhất) | Có | 78.6251 | 67.3387 |

GSA cao hơn `first` cả hai chỉ số (+1.42 F1, +1.71 EM) và cao hơn Few-shot cả
hai chỉ số. Vậy trong số các cách triển khai thật (không oracle), GSA là
phương án tốt nhất, không phải phương án tệ nhất. "Điểm giảm khi chạy GSA"
chỉ đúng khi mốc so sánh là con số oracle `all`, và mốc đó tự thân đã được
tài liệu hoá là không dùng để triển khai. Đây là nguyên nhân gốc thứ nhất.

Phần còn lại của tài liệu giải thích: (1) vì sao khoảng cách `all` → `first`
lớn đến vậy (8.3 điểm EM, cơ chế của Answer Normalization và của evaluator);
(2) một phần khoảng cách `all`/`first` so với baseline là do các rule
gắn cứng theo answer key của tập test, không phải khả năng suy luận bảng
tổng quát; (3) một lỗi cụ thể trong rule boolean khiến việc mở rộng biến thể
Có/Không/Đúng/Sai/Phải bị vô hiệu với dữ liệu tiếng Việt thật; (4) hai cơ chế
mới cho vấn đề OOM/hallucination ở model dưới 10B.

## 1. F1 ở đây là F1 theo tập ký tự, không phải theo token — đây là lý do EM rơi mạnh hơn F1 nhiều

[`evaluation/f1.py:12-13`](../../evaluation/f1.py) dựng
`{char for char in normalize_text(...) if not char.isspace()}` — **tập hợp
ký tự** (đã khử trùng lặp) của chuỗi đã chuẩn hoá, rồi tính precision/recall/F1
trên phần giao của hai tập. Số liệu này rất khoan dung với khác biệt bề mặt:
`"236"` so với `"236 m (774 ft)"` vẫn còn overlap ký tự cao vì cùng chứa các
chữ số và ký tự la-tinh phổ biến; đảo thứ tự từ, thêm/bớt tiền tố, đổi định
dạng ngày tháng hầu như không đổi tập ký tự. EM
([`evaluation/exact_match.py`](../../evaluation/exact_match.py)) thì ngược
lại: yêu cầu `normalize_text(prediction) == normalize_text(reference)` sau
khi hạ chữ thường/NFC/bỏ khoảng trắng thừa — tuyệt đối không khoan dung với
khác biệt bề mặt. Vì vậy khi một cơ chế chỉ đổi *hình thức* câu trả lời (ví
dụ "7" ↔ "Tháng 7", "1709" ↔ "Năm 1709") mà không đổi *nội dung*, nó gần như
không ảnh hưởng F1 nhưng quyết định toàn bộ điểm EM. Đây chính là lý do
POMA `all` → POMA + GSA giảm 2.21 điểm F1 nhưng giảm tới 6.55 điểm EM: phần
lớn "giá trị" mà oracle `all` khai thác được nằm ở việc thử nhiều biến thể
hình thức cho tới khi trúng đúng hình thức của gold, không phải ở việc suy
luận ra nội dung đúng hơn.

## 2. Answer Normalization là "cỗ máy sinh biến thể bề mặt"; GSA hoàn toàn không đi qua nó

`AnswerNormalizationAgent.run` ([`src/agents/answer_normalization.py:753-791`](../../src/agents/answer_normalization.py))
nhận một câu trả lời thô của specialist rồi sinh ra một *danh sách* biến thể
tương đương theo nghĩa nhưng khác bề mặt: `_numeric_variants` (nhóm chữ số,
đổi dấu phẩy/chấm thập phân, thêm/bớt đơn vị — dòng 506-527), `_date_variants`
(6 định dạng ngày khác nhau cho cùng một ngày — dòng 303-363), `_rank_variants`
("1" / "#1" / "Thứ 1" / "Nhất" — dòng 266-300), `_text_context_variants` (bỏ
tiền tố "thôn nào"/"bằng gì", bỏ chú thích ngoặc đơn, bỏ trích dẫn "[12]" —
dòng 657-705). Khi evaluator dùng `candidate_policy="all"`,
[`evaluation/f1.py:30`](../../evaluation/f1.py) và
[`evaluation/exact_match.py:17-18`](../../evaluation/exact_match.py) lấy
`max`/`any` trên toàn bộ các biến thể này cho từng câu — đây chính là cơ chế
sinh ra K trung bình 3.44 và K tối đa 80 trong báo cáo gốc: K lớn không phải
vì POMA "thử nhiều đáp án khác nhau", mà chủ yếu vì một đáp án đúng được viết
lại thành nhiều hình thức rồi được evaluator âm thầm chọn hình thức khớp gold.

`GroundedSingleAnswerFinalizer.finalize`
([`src/finalization/finalizers.py:140-162`](../../src/finalization/finalizers.py))
gọi thẳng `GroundedSingleAnswerAgent.run` trên
`request.candidates` và trả về `[grounded_answer.final_answer]` — **một**
chuỗi duy nhất, không qua `AnswerNormalizationAgent`. Nguồn của
`request.candidates` trong báo cáo GSA là `_poma_candidates`
([`src/finalization/sources.py:119-144`](../../src/finalization/sources.py)),
đọc trực tiếp `steps.3_specialists` — tức câu trả lời **thô** của specialist,
trước cả bước normalization. Đây không phải một lỗi tích hợp ngẫu nhiên: nhìn
vào `scripts/run_finalizer.py:50` (`_FINALIZERS = ("an-native", "an-common",
"gsa")`) thì `an-native`/`an-common` và `gsa` là ba **policy tách biệt** để
so sánh, không phải các bước nối tiếp nhau trong một pipeline. Vì vậy GSA về
kiến trúc không bao giờ được hưởng lợi từ bất kỳ biến thể nào mà
`answer_normalization.py` biết cách sinh ra.

Bằng chứng thực nghiệm (chạy lại trên artifact có sẵn, không gọi LLM): lọc
315/992 câu GSA có EM=0, rồi kiểm tra xem gold answer có nằm trong danh sách
"all"-candidate của `poma.json` cho đúng qa_id đó không (tức là: normalization
*đã* biết sinh đúng hình thức, chỉ là GSA không dùng nó).

```
GSA EM=0: 315/992
Trong đó, gold answer đã có sẵn trong candidate pool của POMA (all): 92 (29.2%)
```

Sáu ví dụ đại diện (qa_id, gold, câu trả lời GSA, candidate pool của POMA,
decision):

- `99922_2_82`: gold `"7"`; GSA trả `"Tháng 7"`; pool POMA có `["Tháng 7",
  "Tháng 7,", "Tháng bảy", "7", "Ngày tháng 7", "Tháng thứ bảy"]` — `"7"` đã
  có sẵn nhưng GSA không chọn hình thức đó.
- `99918_0_10`: gold `"Ngày 30 tháng 5 năm 2023"`; GSA trả `"30 tháng 5 năm
  2023"` (thiếu tiền tố "Ngày"); pool POMA có cả hai hình thức.
- `6_0_1`: gold `"nhất"`; GSA trả `"thứ nhất"`; pool POMA có
  `["thứ nhất", "1", "#1", "Thứ 1", "Nhất"]` — biến thể rank do
  `_rank_variants` sinh ra khớp gold, GSA không có quyền truy cập nó.
- `1_3_292`, `6_0_31`, `10_1_48`: cùng mẫu hình — GSA chọn đúng nội dung
  nhưng sai hình thức trong khi normalization (không chạy trong nhánh GSA)
  đã có sẵn hình thức đúng.

Điều đo được chính xác là: với gần 30% các câu GSA sai EM, *normalization đã
từng sinh ra đúng hình thức gold cho câu đó* nhưng GSA không có quyền truy
cập nó — một số trong đó (ví dụ `99922_2_82`, `"7"` so với `"Tháng 7"`) gần
ranh giới giữa khác biệt hình thức và khác biệt ngữ nghĩa nhẹ, nên nên đọc là
cận trên của lỗi-hình-thức chứ không khẳng định tuyệt đối. 70% còn lại
không kiểm chứng được bằng phép đo này (gold không nằm trong candidate pool
của POMA); trong đó có cả lỗi suy luận thật (ví dụ `3_1_104` gold `"7"`, GSA
tổng hợp `"14"` với `decision=synthesized`) lẫn lỗi từ vựng boolean nêu ở
mục 3.

## 3. Rule "Có/Không/Đúng/Sai/Phải" bị hỏng vì mojibake — một lỗi cụ thể, không phải giả thuyết

Đọc trực tiếp mã nguồn (không phải suy diễn từ log):
[`src/agents/answer_normalization.py:43-44`](../../src/agents/answer_normalization.py)

```python
_BOOLEAN_TRUE_VARIANTS = ("CĂ³", "ÄĂºng", "Pháº£i")
_BOOLEAN_FALSE_VARIANTS = ("Không", "Sai", "Không phải")
```

`"CĂ³"` và `"ÄĂºng"` không phải chữ tiếng Việt hợp lệ — đây là mojibake của
`"Có"` và `"Đúng"` (chuỗi UTF-8 bị giải mã nhầm qua một bảng mã 1-byte rồi mã
hoá lại). `_BOOLEAN_TRUE_NORMALIZED` (dòng 45-47) build từ các chuỗi hỏng
này cộng với `"yes"`, `"true"`; `_boolean_variants` (dòng 366-372) chỉ mở
rộng câu trả lời thành bộ đầy đủ `{Có, Đúng, Phải}` hay `{Không, Sai, Không
phải}` khi `normalize_match_text(answer)` khớp một trong các chuỗi đã chuẩn
hoá đó. Vì `"CĂ³"`/`"ÄĂºng"` chuẩn hoá ra chuỗi rác chứ không phải `"có"`/
`"đúng"`, một câu trả lời tiếng Việt thật là `"Có"` sẽ **không** khớp tập
này (nó chỉ khớp nếu chuẩn hoá ra đúng `"yes"`/`"true"`, không xảy ra với
văn bản tiếng Việt) — nhánh mở rộng coi như luôn rơi về `return [answer]`,
tức là không có biến thể nào được sinh thêm cho câu trả lời "Có".

Đã xác minh trực tiếp cơ chế này trên đúng ví dụ thất bại ở mục 2
(`99917_3_67`, câu hỏi `"Có phải có 3 tòa nhà cao từ 150m trở lên?"`, gold
`"Phải"`, cả specialist lẫn GSA chỉ tạo ra `"Có"`), bằng cách gọi trực tiếp
các hàm nội bộ:

```
_is_boolean_answer("Có")               -> False   # do tập mojibake, không phải "yes"/"true"
_looks_like_boolean_question(question) -> True    # cue "có phải" khớp _BOOLEAN_CUE_RE
_infer_answer_kind("Có", question)     -> "boolean"  # đi qua nhánh cue câu hỏi, không qua _is_boolean_answer
_boolean_variants("Có")                -> ["Có"]  # không mở rộng thêm gì
```

Tức là `answer_kind` vẫn được suy ra đúng là `"boolean"` (nhờ cue câu hỏi),
nhưng `_boolean_variants` — nơi thực sự sinh biến thể — vẫn dùng tập
mojibake nên trả nguyên `["Có"]`. Nếu sửa `_BOOLEAN_TRUE_VARIANTS` thành
`("Có", "Đúng", "Phải")` hợp lệ, `_boolean_variants("Có")` sẽ trả về
`["Có", "Đúng", "Phải"]` và khớp gold `"Phải"`. Lỗi này ảnh hưởng đồng đều đến mọi cấu hình
dùng `answer_normalization.py` (an-native, an-common, và cả pipeline
`run_poma.py` chính), không riêng GSA — nhưng nó góp phần giải thích vì sao
ngay cả con số oracle `all` cũng chưa phải trần trên thật của khả năng khớp
boolean.

## 4. Một phần khoảng cách so với baseline đến từ rule khớp theo answer key của chính tập test

`answer_normalization.py` chứa một số rule không phải chuẩn hoá hình thức
chung mà là literal khớp với nội dung cụ thể của vài câu hỏi/câu trả lời
trong tập dữ liệu đang dùng để đánh giá:

- `_should_force_null_why` (dòng 538-545): trả `"Null"` khi câu hỏi chứa
  đồng thời `"vi sao"`, `"% gni"`, `"cao nhat"`, `"thap nhat"` — bốn cụm gắn
  với một câu hỏi cụ thể, không phải một lớp câu hỏi chung.
- `_text_context_variants` (dòng 697-703): có một `re.search` literal cho
  cụm `"không chấp nhận sự cai trị của ông"` để thêm biến thể trả lời cố
  định `"Vì không chấp nhận sự cai trị của ông"`.
- `_INVALID_WHY_RATIONALE_MARKERS`, `_HOW_RESULT_ONLY_QUESTION_CUES`,
  `_HOW_EXPLANATORY_ANSWER_CUES` (dòng 67-115): danh sách cụm từ tiếng Việt
  khá dài, đọc như được rút ra bằng cách xem lỗi trên tập dev/test rồi thêm
  rule vá từng trường hợp.

Về mặt phương pháp luận, đây là một dạng leakage nhẹ: nếu các rule này được
tinh chỉnh bằng cách nhìn vào câu hỏi/câu trả lời của chính `qas_test.json`
(hoặc `qas_dev.json` có phân bố câu hỏi trùng lặp closely), thì một phần
chênh lệch F1/EM giữa POMA và các baseline không phản ánh khả năng suy luận
bảng tổng quát mà phản ánh việc normalization "biết trước" vài câu hỏi cụ
thể trong bộ test. Baseline (Few-shot/Zero-shot/CoT/Task decomposition) không
được hưởng bất kỳ rule tương đương nào, nên đây là một so sánh không hoàn
toàn công bằng cho tới khi có ablation làm rõ đóng góp của các rule này. Nên
lưu vết provenance của rule (nguồn: quan sát QA nào, ngày thêm) và ablate
bằng cách chạy lại `an-native`/`an-common` sau khi xoá các rule literal ở
trên, so điểm trước/sau trên cùng `qas_test.json`. Nếu điểm giảm đáng kể chỉ
với vài rule bị xoá, đó là bằng chứng trực tiếp cho hiện tượng overfitting
answer key.

## 5. Hai cơ chế mới cho vấn đề OOM/hallucination ở model dưới 10B

Bổ sung cho [`2026-09-17-table-representation-small-lm.md`](2026-09-17-table-representation-small-lm.md)
(giữ nguyên khuyến nghị selector BM25/dense/hybrid ở đó); không lặp lại nội
dung đã có, chỉ nêu hai điểm mới thấy khi đọc `grounded_single_answer.py` và
`local_transformers_client.py`:

1. **Vòng sửa lỗi của GSA nhân đôi bảng đầy đủ trong prompt.**
   `GroundedSingleAnswerAgent.run`
   ([`src/agents/grounded_single_answer.py:49-61`](../../src/agents/grounded_single_answer.py))
   khi validation ngữ nghĩa thất bại (`final_answer` không khớp candidate
   nào), xây `repair_prompt = f"{prompt}\n\n...{json.dumps(data)}..."` —
   `prompt` gốc **đã chứa toàn bộ Flatten V1 table**, nên lần gọi sửa lỗi gửi
   lại nguyên bảng lần thứ hai cộng thêm JSON response lỗi. Với bảng lớn và
   model cục bộ dưới 10B, đây là điểm nhiều khả năng nhất gây tràn bộ nhớ
   hoặc vượt `max_input_tokens`, và nó vô hình trong theo dõi token ở luồng
   thành công (chỉ cộng dồn sau khi request thứ hai đã chạy). Số liệu K tối
   đa 80/K trung bình 3.44 trong báo cáo gốc không tính chi phí này vì đó là
   thống kê candidate, không phải thống kê gọi LLM; cần đo riêng
   `structured_calls`/`repair_attempted_calls` (đã có trong trace, xem
   `scripts/run_finalizer.py:238-273`) theo kích thước bảng để định lượng.

2. **`LocalTransformersClient` chặn cứng khi vượt ngân sách token, không
   hạ cấp — nhưng không hề rút gọn bảng trước đó.**
   [`src/services/local_transformers_client.py:107-123`](../../src/services/local_transformers_client.py)
   ném `ContextOverflowError` ngay khi `prompt_tokens > max_input_tokens`,
   trước khi gọi `generate()`. Đây là hành vi thất bại sạch (không sinh văn
   bản rác), nhưng vì không có bước rút gọn bảng nào trước khi build prompt
   ( `table_preview.py` chỉ áp dụng cho `HintPredictorAgent`, dòng 27-28 xác
   nhận "answer-producing stages continue to receive the complete table"),
   với bảng dài, gần như mọi specialist trong stage 3 sẽ cùng vượt ngưỡng và
   toàn bộ QA đó thất bại ở tầng specialist — khác với triệu chứng "hallucinate"
   (model vẫn sinh ra nhưng sai) mà đề bài mô tả. Đã đọc cả hai client cục bộ:
   `LocalVLLMClient.generate_with_usage`
   ([`src/services/local_vllm_client.py:83-88`](../../src/services/local_vllm_client.py))
   import và dùng lại đúng `ContextOverflowError` từ
   `local_transformers_client.py`, nên cả hai backend cục bộ (Transformers và
   vLLM) đều thất bại rõ ràng thay vì hallucinate khi vượt ngân sách token.
   Ngược lại, đường API từ xa (`src/services/llm_client.py`, nhánh không bắt
   đầu bằng `local/`/`local:`, dòng 493-519) chỉ đặt `max_tokens` cho **đầu
   ra**, không có bước kiểm tra số token **đầu vào** trước khi gọi; với
   backend này, bảng quá dài nhiều khả năng bị nhà cung cấp API tự cắt bớt
   hoặc gây lỗi phía server thay vì được chặn sớm ở phía POMA — đây là con
   đường hợp lý hơn dẫn tới hallucination thay vì lỗi cứng, nhưng cần đo
   thực nghiệm qua log lỗi API theo kích thước bảng để xác nhận, chưa kiểm
   chứng trực tiếp trong tài liệu này. Khuyến nghị
   hành động không đổi so với tài liệu 09-17 (selector không dùng LLM ở P0):
   thêm ở đây là nên đo riêng tỷ lệ `ContextOverflowError` theo kích thước
   bảng cho backend cục bộ như một chỉ số proxy rẻ cho "bảng nào sẽ gây vấn
   đề", trước khi đầu tư vào selector phức tạp hơn.

## 6. Khuyến nghị hành động

1. Khi báo cáo con số POMA, luôn đi kèm ba mức thay vì một: `all` (trần
   oracle, chỉ để chẩn đoán), `first` (điểm sàn không selector), và điểm của
   selector triển khai được thật sự (GSA, hoặc bất kỳ policy nào khác) — như
   bảng ở phần Tóm tắt. Không dùng riêng `all` để so với baseline.
2. Thử một pipeline GSA-sau-normalization: chạy `AnswerNormalizationAgent`
   trên từng candidate trước, đưa **toàn bộ tập biến thể** (không chỉ câu trả
   lời thô) làm `candidates` cho `GroundedSingleAnswerAgent`, để GSA vẫn giữ
   được tính "một câu trả lời, có kiểm chứng bảng" nhưng không mất khả năng
   khớp hình thức. Đo lại 315 câu EM=0 nêu ở mục 2 xem tỷ lệ lỗi hình thức
   thuần tuý có giảm không.
3. Sửa `_BOOLEAN_TRUE_VARIANTS`/`_BOOLEAN_FALSE_VARIANTS` thành đúng
   `"Có"`, `"Đúng"`, `"Phải"` (UTF-8 hợp lệ); thêm test đơn vị khẳng định
   `normalize_match_text("Có") in _BOOLEAN_TRUE_NORMALIZED` để lỗi mojibake
   không tái diễn khi có chỉnh sửa file bằng công cụ/encoding khác.
4. Ablate các rule literal nêu ở mục 4 (`_should_force_null_why`, regex
   "không chấp nhận sự cai trị của ông", các cue-list dài) trên
   `qas_test.json`; nếu đóng góp điểm số đáng kể, tách chúng khỏi
   `answer_normalization.py` chung và ghi rõ là rule đặc thù tập dữ liệu,
   không đưa vào so sánh POMA-vs-baseline như năng lực tổng quát.
5. Log riêng, theo từng finalizer (`an-native`/`an-common`/`gsa`), tỷ lệ câu
   mà gold answer nằm trong candidate pool nhưng finalizer không chọn được —
   chỉ số "surface-form-miss rate" này rẻ hơn nhiều so với việc suy diễn từ
   F1/EM tổng và tách bạch lỗi hình thức khỏi lỗi suy luận nội dung.
