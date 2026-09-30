# Abstract AAMAS 2027 (bản nháp để hỏi thầy)

Nguồn số liệu: `docs/research/2026-09-26-memxam-multi-agent-qwen3-8b.md` §19–§21 (test 992 câu, Qwen3-8B,
MemView v11). "EM chặt" là EM gốc của repo; "EM mọi cách viết" chấp nhận các cách viết cùng nghĩa.

Mỗi phiên bản có hai bản: **bản gốc** do ChatGPT viết (2026-09-30, cuộc trò chuyện "Write AAMAS 2027
abstract") và **bản đã chỉnh**, kèm danh sách thay đổi.

## Tiêu đề đề xuất (ChatGPT)

1. MemView: Shared Memory and Complementary Table Views for Vietnamese Table Question Answering
2. When Do Small-LLM Agents Help? An Empirical Study of Memory and Multi-Agent Table Reasoning
3. Memory Drives the Gains: Small-LLM Multi-Agent Reasoning over Vietnamese Tables

Nếu chọn hướng bài phân tích thực nghiệm, tiêu đề 2 khớp nhất với nội dung.

# Vòng 2 (bản dùng): EM chặt, F1, R1, MET, BIF

Thống nhất: EM là EM chặt (EM gốc của repo, cùng loại với bài báo dataset); F1 theo ký tự; R1 = ROUGE-1;
MET = METEOR chuẩn (nltk, có phạt phân mảnh, giống bài báo dataset); BIF = PhoBERT-BERTScore + ViNLI
(checkpoint 3 nhãn của mình, thang 0–1). Cách mô tả bài toán và metric theo abstract của bài báo dataset
(Dao et al., Open-ViTabQA). Số của bài báo lấy từ Table 11 của bài báo.

| Hệ (test 992 câu) | EM | F1 | R1 | MET | BIF |
|---|---:|---:|---:|---:|---:|
| MemView | 81,85 | 90,66 | 87,38 | 64,37 | 0,711 |
| Bảng chưa thấy (memory từ bảng khác) | 79,03 | 88,69 | 84,85 | 62,36 | 0,699 |
| MemView không memory | 74,90 | 86,01 | 81,81 | 59,74 | 0,685 |
| Few-shot + self-consistency | 73,89 | 84,99 | 79,63 | 57,60 | 0,676 |
| Few-shot | 73,29 | 84,76 | 79,69 | 57,72 | 0,676 |
| Multi-agent debate | 72,58 | 84,57 | 79,20 | 57,42 | 0,673 |
| Zero-shot | 71,77 | 84,25 | 78,66 | 57,07 | 0,672 |
| Chain-of-Table | 54,74 | 73,05 | 65,16 | 47,83 | 0,616 |
| CoAgt | 48,59 | 68,16 | 58,37 | 44,97 | 0,555 |
| *Bài báo dataset:* Human | 83,43 | 86,49 | 90,69 | 60,02 | 0,781 |
| *Bài báo dataset:* Gemini 1.5 Pro | 60,80 | 59,80 | 71,90 | 49,80 | 0,649 |
| *Bài báo dataset:* Gemini 2.0 Flash Exp. | 60,20 | 60,50 | 70,10 | 50,00 | 0,644 |
| *Bài báo dataset:* ViT5 large (fine-tune) | 45,13 | 45,22 | 51,87 | 37,12 | 0,562 |

BIF của bài báo dùng checkpoint riêng của họ, nên chỉ so BIF giữa các hệ mình tự chạy.

## Phiên bản 1: nhấn mạnh phương pháp

### Bản gốc (ChatGPT, vòng 2)

Question answering over open-domain Vietnamese Wikipedia tables involves merged cells, questions requiring
computation, and both extractive and abstractive answers. We present MemView, a multi-agent system using
Qwen3-8B in thinking mode without fine-tuning. Shared memory retrieves training question–answer pairs
exclusively from the same table using Jaccard similarity. One agent generates three samples from Flatten V1
with 16 exemplars; another reads Markdown key–value tables with eight exemplars and cites evidence cells.
Unanimous agreement returns an answer directly; otherwise, a validator examines both representations and
candidate rationales. This design averages 2.4 LLM calls per question. Evaluation uses EM, character-level F1,
ROUGE-1, METEOR, and BIF, which combines PhoBERT embeddings within BERTScore for semantic similarity
with ViNLI for logical consistency. On Open-ViTabQA's 992 test questions, MemView obtains 81.85 EM, 90.66
F1, 87.38 ROUGE-1, 64.37 METEOR, and 0.711 BIF. Its EM exceeds the strongest published baseline, Gemini 1.5
Pro (60.80), while remaining 1.58 points below human performance (83.43). Memory accounts for most gains;
additional agents contribute only 0.3–1.2 EM points. Restricting memory to other tables, a proxy for unseen
tables, yields 79.03 EM. Within our evaluation, removing memory lowers BIF to 0.685. These findings indicate
that complementary agents provide modest improvements beyond relevant exemplar memory.

### Bản đã chỉnh

Question answering over open-domain Vietnamese Wikipedia tables involves merged cells, questions requiring
computation, and both extractive and abstractive answers. We present MemView, a multi-agent system built on
a small open language model (Qwen3-8B, thinking mode) without fine-tuning. All agents share a memory of
training question–answer pairs retrieved from the same table. Agent A reads a flattened serialization with 16
exemplars and draws three samples; agent B reads a Markdown key–value serialization with eight exemplars
and cites evidence cells. When A's samples agree and B concurs, the answer is returned directly; otherwise an
LLM validator reads both representations and the agents' rationales and scores each candidate. MemView uses
2.4 LLM calls per question on average. We evaluate with EM, character-level F1, ROUGE-1, METEOR, and BIF,
which combines PhoBERT embeddings within BERTScore for semantic similarity with ViNLI for logical
consistency. On the 992 test questions of Open-ViTabQA, MemView obtains 81.85 EM, 90.66 F1, 87.38
ROUGE-1, 64.37 METEOR, and 0.711 BIF, exceeding the strongest published baseline, Gemini 1.5 Pro (60.80
EM), by 21 points and remaining 1.58 EM below human performance (83.43). Ablations show that memory
accounts for most of the gain, while the second agent and the validator add 0.3–1.2 EM; with memory drawn
only from other tables, a proxy for unseen tables, MemView still reaches 79.03 EM.

Thay đổi so với bản gốc vòng 2:

- "Unanimous agreement" nói rõ: 3 mẫu của A trùng nhau và B đồng ý; "a validator" nói rõ là LLM validator.
- Gọi tên agent A và agent B cho khớp với phần phương pháp của bài.
- Nêu mức chênh với Gemini 1.5 Pro (khoảng 21 điểm EM).
- Bỏ câu "Within our evaluation, removing memory lowers BIF to 0.685" (lủng củng, lặp ý với câu ablation) và
  câu kết chung chung, để giữ khoảng 200 từ.

## Phiên bản 2: nhấn mạnh phân tích thực nghiệm

### Bản gốc (ChatGPT, vòng 2)

Question answering over open-domain Vietnamese Wikipedia tables includes merged cells, computational
questions, and extractive and abstractive answers. We examine when multi-agent systems built on small
language models help, using Qwen3-8B in thinking mode without fine-tuning. MemView combines shared
memory of same-table training question–answer pairs with complementary table readers and validation of
disagreements. We evaluate EM, character-level F1, ROUGE-1, METEOR, and BIF, which combines PhoBERT
embeddings within BERTScore for semantic similarity with ViNLI for logical consistency. On Open-ViTabQA's
992 test questions, MemView achieves 81.85 EM, 90.66 F1, 87.38 ROUGE-1, 64.37 METEOR, and 0.711 BIF. EM
exceeds few-shot prompting (73.29), three-sample self-consistency (73.89), and multi-agent debate (72.58). It
also exceeds the strongest published baseline, Gemini 1.5 Pro (60.80), but remains 1.58 EM points below
humans (83.43). Removing memory reduces EM to 74.90, whereas the additional reader and validator
contribute only 0.3–1.2 EM points. Restricting retrieval to other tables, a proxy for unseen tables, yields 79.03
EM. BIF comparisons within our evaluation likewise favor MemView over its memory-free variant (0.711 versus
0.685); published BIF scores use a different checkpoint. These findings identify memory as the principal source
of improvement, with complementary views and selective validation providing smaller gains at 2.4 LLM calls per
question.

### Bản đã chỉnh

Question answering over open-domain Vietnamese Wikipedia tables involves merged cells, questions requiring
computation, and both extractive and abstractive answers. We ask when multi-agent systems built on small
language models help this task, using Qwen3-8B without fine-tuning. We design MemView, which combines a
shared memory of same-table training question–answer pairs, two agents that read the table in complementary
representations, and an LLM validator invoked only when the agents disagree (2.4 LLM calls per question). We
evaluate with EM, character-level F1, ROUGE-1, METEOR, and BIF, which combines PhoBERT embeddings within
BERTScore for semantic similarity with ViNLI for logical consistency. On the 992 test questions of
Open-ViTabQA, MemView achieves 81.85 EM, 90.66 F1, 87.38 ROUGE-1, 64.37 METEOR, and 0.711 BIF. Its EM
exceeds few-shot prompting (73.29), three-sample self-consistency (73.89), multi-agent debate (72.58), and the
strongest published baseline, Gemini 1.5 Pro (60.80), and is 1.58 points below human performance (83.43).
Controlled ablations locate the gain: removing memory lowers EM to 74.90, whereas the second agent and the
validator add only 0.3–1.2 EM over a single agent. With memory drawn only from other tables, a proxy for
unseen tables, MemView still reaches 79.03 EM. At this scale, relevant shared memory matters far more than
the number of agents.

Thay đổi so với bản gốc vòng 2:

- Gộp hai câu so sánh EM thành một; nói rõ validator chỉ chạy khi các agent bất đồng.
- Bỏ câu so BIF với bản không memory và câu ghi chú checkpoint (chi tiết này để trong phần thực nghiệm), để
  giữ khoảng 200 từ.
- Câu kết ngắn hơn, nêu thẳng phát hiện chính.

# Vòng 1 (lưu để tham khảo): EM chấp nhận mọi cách viết

## Phiên bản 1: nhấn mạnh phương pháp

### Bản gốc (ChatGPT)

We present MemView, a multi-agent system for Vietnamese table question answering using Qwen3-8B in
thinking mode without fine-tuning. MemView combines shared exemplar memory with complementary table
representations. Agents retrieve training question–answer pairs by Jaccard similarity, prioritizing examples from
the query's table. Agent A reads a Flatten V1 serialization with 16 exemplars and generates three samples;
agent B reads a Markdown key–value representation with eight exemplars and cites evidence cells before
answering. Unanimous agreement returns an answer directly; otherwise, a validator examines both views and
candidate rationales, assigning normalized probabilities to candidate answers. Direct agreement resolves 80%
of questions, with an average of 2.4 LLM calls per question. On Open-ViTabQA, comprising 329 Vietnamese
Wikipedia tables and 7,928/991/992 train/development/test questions, MemView achieves 81.85% strict exact
match and 85.69% exact match accepting equivalent surface forms, compared with 73.29% and 77.92% for few-
shot prompting. Ablations show that memory accounts for most of the improvement, while the additional
agents contribute 0.6–1.1 exact-match points. On unseen tables, strict exact match remains 79.03%. These
results support complementary views and selective validation as modest additions to exemplar memory, rather
than evidence that agent multiplicity alone produces substantial gains.

### Bản đã chỉnh

We present MemView, a multi-agent system for Vietnamese table question answering built on a small open
language model (Qwen3-8B, thinking mode) without fine-tuning. MemView combines two ideas. *Mem*: all agents
share a memory of training question–answer pairs from the same table, retrieved by lexical similarity. *View*:
two agents read the table in complementary serializations. Agent A reads a flattened pipe format with 16
exemplars and draws three samples; agent B reads a Markdown key–value format with eight exemplars and must
cite evidence cells before answering. When A's samples agree and B concurs (80% of questions), the answer is
returned directly; otherwise an LLM validator reads both views, inspects each candidate together with the
agents' rationales, and assigns it a probability. MemView uses 2.4 LLM calls per question on average. On the
992 test questions of Open-ViTabQA, it reaches 81.85 strict exact match (85.69 when equivalent surface forms
are accepted), compared with 73.29 for few-shot prompting in the same prompt frame and 72.58 for multi-agent
debate. Ablations show that same-table memory drives most of the gain, while the second agent and the
validator add 0.6–1.1 points. With memory restricted to other tables, a proxy for unseen tables, MemView
still reaches 79.03.

Thay đổi so với bản gốc:

- Sửa lỗi: bản gốc viết memory "prioritizing examples from the query's table", nhưng memory chỉ lấy câu
  mẫu **từ đúng bảng đang hỏi**.
- "Unanimous agreement" được nói rõ: 3 mẫu của A trùng nhau **và** B đồng ý.
- Nói rõ validator là LLM và chỉ chạy ở phần câu còn lại.
- Thêm multi-agent debate làm mốc so sánh, vì đây là baseline multi-agent chuẩn mà reviewer AAMAS sẽ tìm.
- Nói rõ "unseen tables" là kịch bản mô phỏng (memory chỉ lấy từ bảng khác), không phải bảng thật chưa thấy.
- Bỏ ký hiệu "%" sau EM; bỏ câu kết mang tính biện hộ, để phiên bản này tập trung vào phương pháp.

## Phiên bản 2: nhấn mạnh phân tích thực nghiệm

### Bản gốc (ChatGPT)

When do multi-agent systems built on small language models improve table question answering? We
investigate this question on Open-ViTabQA, a Vietnamese Wikipedia table benchmark, using Qwen3-8B in
thinking mode without fine-tuning. Our system, MemView, combines shared memory of retrieved training
question–answer pairs, two agents operating on complementary table representations, and an LLM validator
invoked when their answers disagree. On 992 test questions, MemView achieves 81.85% strict exact match,
85.69% exact match accepting equivalent surface forms, and 90.66% F1. Strict exact match exceeds few-shot
prompting using the same prompt frame (73.29%), three-sample self-consistency (73.89%), and multi-agent
debate (72.58%). Ablations reveal that exemplar memory is the main source of improvement: removing
memory reduces strict exact match to 74.90%, whereas adding the second reader and validator improves exact
match by only 0.6–1.1 points over the first reader alone. With memory restricted to other tables, unseen-table
performance reaches 79.03% strict exact match. Agreement permits direct answers for 80% of questions,
yielding 2.4 LLM calls per question on average. These findings suggest that, in this setting, small-LLM multi-
agent systems benefit chiefly from relevant shared memory, with complementary views and selective validation
providing smaller incremental gains.

### Bản đã chỉnh

When do multi-agent systems built on small language models help table question answering? We study this
question on Open-ViTabQA, a benchmark of Vietnamese Wikipedia tables, using Qwen3-8B without fine-tuning.
We design MemView, which combines a shared memory of training question–answer pairs from the same table,
two agents that read the table in complementary representations, and an LLM validator invoked only when
the agents disagree (20% of questions; 2.4 LLM calls per question overall). On 992 test questions, MemView
reaches 81.85 strict exact match and 85.69 when equivalent surface forms are accepted, well above few-shot
prompting in the same prompt frame (73.29), three-sample self-consistency (73.89), and multi-agent debate
(72.58); CoAgt and Chain-of-Table with their original prompts score below 55. Controlled ablations separate
the sources of this gain. Removing the memory lowers exact match to 74.90, whereas the second agent and the
validator add only 0.6–1.1 points over a single agent, a margin comparable to run-to-run variation. With
memory drawn only from other tables, a proxy for unseen tables, MemView still reaches 79.03, about six
points above few-shot prompting. These results indicate that, at this scale, relevant shared memory matters
far more than the number of agents, and that agent interaction yields modest gains.

Thay đổi so với bản gốc:

- Nói rõ memory lấy từ **cùng bảng**, và validator chỉ chạy ở 20% câu.
- Gộp số lệnh gọi vào cùng câu mô tả hệ thống; bỏ F1 để abstract gọn (F1 để trong bảng kết quả).
- Thêm CoAgt và Chain-of-Table (dưới 55 EM) để cho thấy đã so với các hệ multi-agent Table QA khác.
- Nói rõ phần lợi của multi-agent (0,6–1,1) ngang mức dao động giữa các lần chạy, đúng với dữ liệu hiện có.
- Nói rõ kịch bản bảng chưa thấy là mô phỏng, và vẫn hơn few-shot khoảng 6 điểm EM chặt (79,03 so với 73,29).
- Bỏ ký hiệu "%" sau EM.

## Câu hỏi cần hỏi thầy

- Chọn phiên bản 1 (phương pháp) hay phiên bản 2 (phân tích thực nghiệm)?
- Báo cáo EM chặt hay EM mọi cách viết làm số chính?
- Có nêu CoAgt và Chain-of-Table trong abstract không, khi hai hệ này giữ prompt tiếng Anh gốc?
- Câu "comparable to run-to-run variation" cần chạy lặp để có số cụ thể trước khi nộp.
