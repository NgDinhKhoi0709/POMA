# Review abstract AAMAS 2027 (ChatGPT đóng vai reviewer)

Ngày 2026-09-30, cuộc trò chuyện mới trong ứng dụng ChatGPT (Codex, "Review MemView abstract versions"). Đầu vào là
hai cặp tiêu đề + abstract đã chỉnh ở `paper/aamas2027-abstract.md` (vòng 2); yêu cầu chỉ đánh giá dựa trên văn bản
được đưa, không thêm số hay chi tiết.

## Tóm tắt

| | Phiên bản 1 (phương pháp) | Phiên bản 2 (phân tích thực nghiệm) |
|---|---|---|
| Điểm dự đoán | 6/10, borderline | 7/10, weak accept nếu bài chứng minh được so sánh có kiểm soát |
| Điểm mạnh | mô tả phương pháp cụ thể; trung thực về phần đóng góp nhỏ của multi-agent | có câu hỏi nghiên cứu và phát hiện rõ; có số ablation không memory (74,90) |
| Điểm yếu chính | đọc như một ensemble nhiều prompt + judge, ít mới về cơ chế phối hợp agent | tiêu đề quá rộng so với một backbone, một dataset; câu kết "number of agents" vượt quá thí nghiệm |

**Khuyến nghị của reviewer:** nộp **phiên bản 2**, thu hẹp tiêu đề và câu kết; đưa chi tiết định tuyến (khi nào gọi
validator) của phiên bản 1 vào phần phương pháp. Tiêu đề đề xuất: *"MemView: An Empirical Study of Shared Memory and
Multi-Agent Reasoning for Vietnamese Table Question Answering"*.

## Các câu hỏi của reviewer mà dữ liệu hiện có trả lời được

- **2,4 lệnh gọi mà A có 3 mẫu:** 3 mẫu của A nằm trong **một request** (n = 3), nên A tính 1 lệnh gọi, B 1 lệnh
  gọi, agent V chạy thêm ở 20% câu (2 lệnh gọi, mỗi view một lệnh). Cần viết rõ trong bài; có thể báo thêm token mỗi
  câu (đã có trong kết quả).
- **Khi nào gọi validator:** khi 3 mẫu của A không trùng nhau, hoặc B khác đáp án của A. Validator chấm các ứng viên
  hợp lệ khác nhau (3 mẫu A và B), không biết số phiếu; hoà thì theo số phiếu.
- **"Single agent" là cấu hình nào:** agent A có memory (Flatten V1, 16 câu mẫu, đa số 3 mẫu), lấy từ cùng lần chạy.
  Khoảng 0,3–1,2 EM là mức hơn của MemView so với chỉ A ở ba điều kiện memory: không memory (+0,3), memory bảng khác
  (+1,2), memory cùng bảng (+1,0). Nên viết rõ như vậy.
- **So sánh baseline có công bằng không:** zero-shot, few-shot và debate dùng cùng khung prompt, cùng tham số lấy
  mẫu; CoAgt và Chain-of-Table giữ prompt gốc. Gemini 1.5 Pro là số công bố trong bài báo dataset, không cùng điều
  kiện; abstract của reviewer đã đổi thành "the reported EM".
- **Có hơn trên các metric khác không:** có, MemView cao nhất ở F1, R1, MET và BIF trong các hệ mình chạy (bảng ở
  `paper/aamas2027-abstract.md`). Có thể thêm một câu hoặc để trong bảng.

## Các câu hỏi chưa trả lời được

- **Độ dao động giữa các lần chạy và ý nghĩa thống kê** của mức +0,3 đến +1,2 EM: cần chạy lặp MemView v11 (đã có
  khoảng tin cậy ghép cặp, nhưng chưa có nhiều lần chạy).
- **Lợi ích theo từng loại câu hỏi** nêu ở câu mở đầu (ô gộp, tính toán, không trả lời được): đã có số theo nhóm hint
  cho tính toán; chưa có bảng riêng cho câu không trả lời được.
- **"Controlled ablations":** bỏ agent B cũng bỏ luôn view Markdown-KV và yêu cầu trích bằng chứng, nên chưa tách được
  phần lợi do view hay do agent. Nên bỏ chữ "controlled" như reviewer gợi ý.

## Nguyên văn review

**Version 1 — System contribution, likely score: 6/10**

This is a clear, results-rich abstract for a potentially useful table-QA system. Its main vulnerability for AAMAS is that the strongest contribution appears to be access to relevant examples, while the contribution of multiple agents is modest. Based only on this text, I would lean borderline: the performance is promising, but the abstract does not establish substantial novelty in agent coordination.

**Strengths**

- The method is unusually concrete: different table representations, exemplar counts, three samples from agent A, evidence citations from agent B, and a conditional validator.
- The evaluation identifies the backbone, dataset, test size, metrics, and several relevant comparison methods.
- Reporting that memory accounts for most of the improvement strengthens credibility. The abstract does not hide the modest contribution of the second agent and validator.
- The other-table memory experiment addresses an important limitation of same-table retrieval, although it cannot establish unseen-table generalization by itself.

**Weaknesses and reviewer questions**

- **AAMAS fit and agent novelty.** The application fits agentic AI, but the mechanism currently reads as an ensemble with different prompts and a judge. What makes the coordination a research contribution? Do agents interact, revise their answers, or update shared memory? Reading the same static collection of examples is a weaker notion of shared memory than maintaining a common evolving state.
- **Complementarity is asserted rather than demonstrated.** Different serializations plausibly produce different errors, but the aggregate scores do not establish this. Are the gains caused by complementary table views, different exemplar counts, evidence prompting, or additional sampling?
- **Same-table retrieval is central to interpreting the results.** How are training and test questions separated? Can retrieved examples contain closely related questions or answers? Same-table training examples are not automatically leakage, but their availability defines a materially different setting from answering questions about tables with no prior labeled examples.
- **The call count needs a precise explanation.** Three samples from A can be compatible with 2.4 calls on average if one request returns multiple completions. If each sample requires a separate call, the description is difficult to reconcile. Calls also do not establish token cost or latency.
- **Candidate selection remains ambiguous.** What happens when A’s samples disagree? Which candidates does the validator score, and what determines the final answer? Are evidence citations checked against the table?
- **The benchmark comparisons are numerically persuasive but methodologically underspecified.** Every stated baseline EM is below 81.85, and the stated human gap is arithmetically correct. However, the text does not establish matched access to retrieved examples, comparable inference budgets, or identical evaluation conditions. “Strongest published baseline” also requires a clear scope.
- **Small gains need uncertainty estimates.** The reported 0.3–1.2 EM improvements are modest on 992 questions. Their robustness across runs and configurations matters. The abstract supports a numerical improvement, but not statistical significance.
- **The additional metrics lack comparison context.** Their absolute values are reported, but no baseline values establish improvement on those metrics. BIF’s definition also leaves unclear how its semantic and logical components are combined and validated.
- **The task challenges are not individually evaluated here.** The abstract motivates merged cells, computation, and unanswerable questions, but provides no evidence that MemView specifically improves each category.

**Concrete edits**

Use “example memory” to distinguish retrieved demonstrations from an evolving agent memory. Make the final inference more cautious, retain the operational details, and avoid implying that the published-baseline comparison establishes superiority under matched conditions.

Suggested title:

**MemView: Shared Example Memory and Complementary Table Views for Vietnamese Table Question Answering**

Suggested abstract:

> Question answering over open-domain Vietnamese Wikipedia tables must handle merged cells, computational questions, and questions that cannot be answered from the table. We present MemView, a multi-agent system using a small language model without fine-tuning. All agents retrieve training question-answer pairs from the same table as shared example memory. Agent A reads a flattened table serialization with 16 exemplars and generates three answer samples. Agent B reads a Markdown key-value serialization that represents each row as a block of “column: value” lines, uses eight exemplars, and cites evidence cells before answering. The system returns an answer when A’s samples agree and B concurs; otherwise, an LLM validator scores candidate answers using both serializations and the agents’ rationales. MemView averages 2.4 LLM calls per question. We evaluate using EM, character-level F1, ROUGE-1, METEOR, and BIF, which combines semantic similarity from BERTScore using PhoBERT embeddings with logical consistency from ViNLI. On the 992 test questions of Open-ViTabQA, MemView with Qwen3-8B obtains 81.85 EM, 90.66 F1, 87.38 ROUGE-1, 64.37 METEOR, and 0.711 BIF. Its EM exceeds that of zero-shot prompting (71.77), few-shot prompting (73.29), multi-agent debate (72.58), Chain-of-Table (54.74), and CoAgt (48.59) using the same backbone. It also exceeds the reported EM of the strongest published baseline, Gemini 1.5 Pro (60.80), and is 1.58 EM below human performance (83.43). Ablations attribute most of the improvement to memory, with gains of 0.3–1.2 EM from the second agent and validator. Restricting memory to examples from other tables yields 79.03 EM, providing a proxy evaluation for the absence of same-table examples.

The call-count interpretation and the precise attribution of the 0.3–1.2 gains still need clarification in the paper; rewriting cannot resolve those missing details.

**Version 2 — Empirical contribution, likely score: 7/10**

This is the stronger research framing. It turns the modest multi-agent gains into an informative finding rather than relying primarily on architectural novelty. I would lean weak accept if the full paper substantiates the controlled comparisons. The main weakness is that the title asks a broad question that the reported experiment answers only within a narrow setting.

**Strengths**

- The abstract states a research question and ends with an interpretable finding.
- The memory ablation result, 74.90 EM, makes the argument more concrete than Version 1’s qualitative statement.
- The framing is relevant to AAMAS: it examines whether additional agents contribute beyond another important system component.
- It acknowledges the limited contribution of additional agents and includes an experiment that reduces dependence on same-table examples.
- The performance and comparison details remain sufficiently specific to assess the reported outcome.

**Weaknesses and reviewer questions**

- **The title overstates the scope.** “When do small-LLM agents help?” suggests identifying conditions across models, tasks, resource budgets, or question categories. The text reports one backbone on one dataset, with component ablations. It supports a finding in this setting, not a general account of when agents help.
- **AAMAS fit is stronger, but depends on the experimental design.** A careful empirical study of agent coordination can be valuable without a novel architecture. However, a table-QA benchmark result with a small agent ablation could still appear more appropriate for an NLP venue unless it yields a clear insight about agent systems.
- **Multi-agent novelty remains limited.** Complementary readers plus a conditional judge are plausible components, but no new coordination mechanism is established. The empirical contribution must carry the paper.
- **“Controlled ablations” is stronger than the description supports.** Are memory access, examples, sampling, prompts, and inference budgets held comparable? Removing an agent may also remove its distinct representation or evidence instructions. Those changes complicate causal attribution.
- **The validator trigger is underspecified.** “Only when the agents disagree” does not explain how agreement is determined or whether disagreement among samples also triggers validation. The reader cannot reconstruct the routing policy from this version.
- **“Over a single agent” needs an explicit reference configuration.** Does that agent use memory? Which serialization does it read? Are the second agent and validator evaluated independently or as successive additions? The 0.3–1.2 range is difficult to interpret without those answers.
- **The conclusion reaches beyond the manipulated variable.** “The number of agents” implies a study of varying agent counts. The text establishes only the contribution of a second agent and validator. “Relevant” memory also implies a relevance comparison that is not directly reported.
- **Other-table memory remains a proxy.** It removes same-table examples from retrieval, but does not establish that the evaluation tables are otherwise unseen.
- **The same numerical limitations apply.** The EM ranking and human gap are supported by the stated numbers. Fair comparison conditions, significance of the small agent gains, superiority on the other metrics, and benefits for the motivated question categories are not established.

**Concrete edits**

Narrow the title to the actual empirical setting. Replace the final claim about agent count with a statement about the evaluated components. Avoid “controlled” unless the paper documents the necessary controls.

Suggested title:

**MemView: An Empirical Study of Shared Memory and Multi-Agent Reasoning for Vietnamese Table Question Answering**

Suggested abstract:

> Question answering over open-domain Vietnamese Wikipedia tables must handle merged cells, computational questions, and questions that cannot be answered from the table. We examine the contributions of shared example memory and multiple agents to this task using a small language model without fine-tuning. We introduce MemView, which combines retrieved same-table training question-answer pairs, two agents reading complementary table serializations, and an LLM validator invoked when the agents disagree. The serializations are a flattened table and a Markdown key-value form that represents each row as “column: value” lines. MemView averages 2.4 LLM calls per question. We evaluate using EM, character-level F1, ROUGE-1, METEOR, and BIF, which combines semantic similarity from BERTScore using PhoBERT embeddings with logical consistency from ViNLI. On the 992 test questions of Open-ViTabQA, MemView with Qwen3-8B achieves 81.85 EM, 90.66 F1, 87.38 ROUGE-1, 64.37 METEOR, and 0.711 BIF. Its EM exceeds that of zero-shot prompting (71.77), few-shot prompting (73.29), multi-agent debate (72.58), Chain-of-Table (54.74), and CoAgt (48.59) using the same backbone. It also exceeds the reported EM of the strongest published baseline, Gemini 1.5 Pro (60.80), and is 1.58 EM below human performance (83.43). Removing memory lowers EM to 74.90, whereas the reported gains from the second agent and validator over a single agent are 0.3–1.2 EM. Restricting memory to examples from other tables yields 79.03 EM, providing a proxy evaluation for the absence of same-table examples. In this setting, the reported contribution of memory is substantially larger than the gains from the additional agent and validator.

**Recommendation**

Submit **Version 2 with the narrower title and conclusion**. Its empirical framing better matches the evidence: memory contributes most, and the additional agent components provide smaller gains. Version 1 offers a clearer operational description, but invites a stronger architectural-novelty objection. The best submission uses Version 2’s contribution framing and supplies Version 1’s routing detail in the method section.
