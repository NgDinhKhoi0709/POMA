# Hệ multi-agent / agentic dành riêng cho Table QA (2023 → 09/2026)

Ngày: 2026-09-26. Báo cáo hỗ trợ cho
[`../2026-09-26-multi-agent-tqa-de-xuat.md`](../2026-09-26-multi-agent-tqa-de-xuat.md).
Phạm vi: chỉ các hệ **dành riêng cho Table QA** (và vài hệ text-to-SQL có ý tưởng chuyển được).
Văn liệu chung về debate/vote/self-correction đã nằm trong khảo sát 2026-09-18, không lặp lại ở đây.

## Nguồn và cách đọc

- **Metadata arXiv** (ID, tiêu đề, tác giả, ngày, venue ghi trong comment): arXiv export API, mở
  trong một browser tab riêng (`tab-2`) của Browser pane. Ba lượt tra cứu theo `id_list` và
  `search_query`.
- **Nội dung paper**: alphaXiv MCP (`answer_pdf_queries`). Công cụ này trả về các trang liên quan
  nhất chứ không phải toàn văn, nên một số mục (ví dụ số call trung bình) có thể nằm ở trang chưa
  được trả về. Những chỗ như vậy được ghi rõ.
- **Paper không có trên arXiv**:
  - TaPERA: mở trang ACL Anthology bằng browser, PDF đọc qua alphaXiv.
  - CoAgt (PeerJ CS): trang PeerJ trả 403 cho cả browser lẫn WebFetch. Tôi đọc bản PDF có sẵn
    trong máy (`D:\.UIT\KLTN\multi_agent_system_docs\CoAgt.pdf`), trang 1–6 và 9–14.
- **Không dùng được**: DBLP (bị chặn bởi bot check Anubis, không vượt), Semantic Scholar API (lỗi
  429 rate limit).
- **Nguồn phụ trong repo**: `paper/jit-article.tex` (kết quả CoAgt/CoQ chạy lại trên
  Open-ViTabQA), `baselines/*/PROVENANCE.md`, và khảo sát
  `../2026-09-18-supporting/program-aided-shortlist.md`. Số liệu lấy từ khảo sát đó mà tôi không
  đọc lại được gắn nhãn *(theo khảo sát 09-18)*.

Quy ước: **"Kiểm soát"** cho biết có LLM nào quyết định luồng điều khiển hay không (chọn bước
tiếp theo, chọn công cụ, dừng hay lặp). **"Compute-matched"** nghĩa là baseline được cho cùng số
call hoặc cùng lượng token (ví dụ self-consistency với cùng N). **"≤10B"** là kết quả với backbone
có tối đa 10 tỷ tham số.

---

## 1. Tóm tắt

1. **Pattern lặp lại:** planner + coder dùng SQL/Python; vòng critic/verifier; nhiều đường rồi chọn; chuẩn hoá bảng trước khi suy luận.
2. **Phần lớn là workflow cố định.** LLM chỉ quyết định dừng hoặc chọn bước (ReAct); MATA điều khiển bằng classifier đã train.
3. **Compute-matched hiếm, và đều ở backbone lớn:** Mix-SC (10 vs 10 *mẫu*, +6,7), Table-Critic (vs SC-15, +7,2), MACT (vs SC, ~+6), CHASE-SQL (selector đã tune, +4,2).
4. **Ở cỡ 8B chỉ Mixture-of-Minds gần compute-matched:** Qwen3-8B, 3 call 47,38 vs SC-8 41,94; lợi chỉ ở câu tính toán; LLaMA-8B còn giảm.
5. **Bằng chứng ≤10B có** (Orchestra, CoQ, TableZoomer, MACT, MATA), **nhưng đối chứng là CoT/PoT một call**; Orchestra tốn khoảng 24 request mỗi câu.
6. **Critic trên đúng Qwen3-8B chỉ thêm khoảng 1–2 điểm** (DRE), dưới ngưỡng phân giải của 992 câu.
7. **Nhiều gain đo bằng EM nới lỏng** (chuẩn hoá trước EM, evaluator Binder, LLM chấm lại), nên số literature sẽ thổi phồng khi đặt cạnh EM chặt.
8. **SQL/Python và cấu trúc: bằng chứng lẫn lộn, tách theo độ sâu lồng.** Thắng trên IM-TQA và bảng lồng nông; thua khi chuyển vị (Mix-SC) hoặc lồng sâu (SSTQA).
9. **Merged header và unanswerable gần như bị bỏ qua.** Chỉ ST-Raptor có cây header tường minh và có đường "unanswerable"; không hệ nào đo abstention.
10. **Hai hệ chạy lại trong repo thua FS trên Open-ViTabQA:** CoAgt 32,36 EM, CoQ 57,86 EM, FS 67,14. Đây là số mô tả; bản CoQ thiếu clause agent.

---

## 2. Bảng tổng hợp

Ký hiệu: ✔ = có; ✘ = không; ~ = một phần. "Gain" là số điểm tuyệt đối so với baseline nêu trong
ngoặc, trên benchmark chính của paper.

| # | Hệ (năm, venue) | Pattern / kiểm soát | Backbone; có ≤10B? | Compute-matched? | Nguồn đa dạng | Benchmark (dạng đáp án) | Gain chính | Code |
|---|---|---|---|---|---|---|---|---|
| 1 | MACT (2024, NAACL-F'25) | planner + coder + tool, ReAct; LLM chọn intent/Finish; SC k=5 mỗi bước | GPT-3.5; Qwen2-72B+CodeLlama-34B; **✔ Qwen2-7B+DS-Coder-7B** | ~ (so SC(Qw+CL) 5 mẫu) | 2 model khác nhau + tool | WTQ, TAT, CRT, SciTab (span, EM) | +3,6 WTQ, ~+6 TB so SC(Qw72+CL34) | ✔ |
| 2 | Table-Critic (2025, ACL) | Judge/Critic/Refiner/Curator; Judge quyết dừng | Qwen2.5-72B, LLaMA3.3-70B, GPT-4o-mini; ✘ ≤10B | ✔ (vs Chain-of-Table SC-15) | persona cùng model + template tree | WikiTQ, TabFact | +8,9 WikiTQ (Qwen72B, vs CoTable) | ✔ |
| 3 | MATA (2026, ACL-F) | CoT/PoT/SQL agent + debug + Judge; **điều khiển bằng classifier có train** | 10 LLM gồm **✔ 3–8B** | ✘ (so latency, không so cùng call) | công cụ/đường suy luận | TableBench-entity, Penguins; WikiTQ phụ lục (EM/fuzzy/F1) | llama3.2-3b WikiTQ 0,535 vs MixSC 0,232 | ✔ |
| 4 | Chain-of-Query (2025, AACL) | Splitter/SQL Gen/Planner/Answer; Planner quyết thêm clause | GPT-3.5/4.1, LLaMA-2-13B, **✔ LLaMA-3.1-8B**, DS-V3 | ✘ | SQL + LLM (hybrid) | WikiTQ, TabFact, **FeTaQA**, **IM-TQA**, Open-WikiTable | +8,0 WikiTQ (8B, vs CoTable) | ✔ |
| 5 | TableZoomer (2025, arXiv) | 5 vai + ReAct (≤5 vòng) | **✔ Qwen3-8B** … 70B | ✘ (vs PoT 1 call) | table view (schema/zoom) | DataBench, TableBench, WikiTQ | +19,3 DataBench (Qwen3-8B) | ✔ |
| 6 | MAPLE (2025, ALTA) | Solver(ReAct)/Checker/Reflector/Archiver | GPT-4o-mini, 70B, 72B; ✘ ≤10B | ✘ | persona cùng model + memory | WikiTQ, TabFact | +6,3 TB WikiTQ | ✔ |
| 7 | PanelTR (2025, IJCNN) | 5 persona nhà khoa học, self/peer review, vote | DeepSeek-V3; ✘ | ✘ | persona cùng model | TAT-QA, SEM-TAB-FACTS, WikiSQL, FEVEROUS | +9,2 EM TAT-QA vs vanilla | ✔ |
| 8 | DataFactory (2026, IP&M) | Leader ReAct + DB team + KG team | GPT-4o-mini, DS-V3, Gemini, Qwen3-14B…235B; ✘ ≤10B | ✘ | công cụ (SQL vs Cypher/KG) | TabFact, WikiTQ, **FeTaQA** | 72,8 vs AutoPrep 67,2 (TB 3 model) | ✘ (hứa công bố) |
| 9 | Mixture-of-Minds (2025, Meta) | plan → code → answer cố định; MCTS + GRPO từng agent | **✔ Qwen3-8B, LLaMA-3.1-8B**, 27–70B | **✔ gần** (workflow 3 call vs base SC-8) | vai tuần tự | TableBench, FinQA | Qwen3-8B 41,98 → 47,38 (chưa train), 57,44 (đã train) | không thấy |
| 10 | AutoPrep (2024, VLDB'25) | Planner (Chain-of-Clauses) → Programmer (Filter/Derive/Normalize) → Executor | DS-V2.5, GPT-3.5, 70B, 72B; ✘ | ✘ | operator chuẩn bị dữ liệu | WikiTQ, TabFact, TableBench | NL2SQL +13,3 WikiTQ; vs CoTable +3,05 | ✔ |
| 11 | ReAcTable (2023, VLDB'24) | 1 LLM ReAct chọn SQL/Python/answer + voting | Codex, GPT-3.5/4; Orchestra chạy lại ở 7–8B | ~ (so các biến thể voting) | tool (SQL vs Python) | WikiTQ, TabFact, FeTaQA | 68,0 WikiTQ (Codex) | ✔ |
| 12 | H-STAR (2024, NAACL'25) | trích cột → trích dòng (SQL+text) → suy luận thích ứng; cố định | GPT-3.5, PaLM-2, GPT-4o-mini, Gemini, Llama-3-70B; ✘ | ✘ | view (bảng gốc + chuyển vị), SQL vs text | WikiTQ, TabFact, **FeTaQA** | +9,6 WikiTQ GPT-3.5 vs CoTable | ✔ |
| 13 | PoTable (2024, TKDE'26) | 5 stage cố định, plan-then-execute trong stage | GPT-4o-mini, Llama-3.1-70B; ✘ | ✘ | — | WikiTQ, TabFact | +4,4–5,9 WikiTQ vs runner-up | ✔ |
| 14 | TableMind / TableMind++ (2025/26) | 1 agent đã train (SFT+RL) + 16 path + memory + vote | **✔ Qwen3-8B (fine-tune)** | ✘ | sampling | WikiTQ, TabFact, **HiTab**, FinQA | WikiTQ 78,07; HiTab 73,69 | ✔ |
| 15 | TableMaster (2025, ICLR'26) | focus → verbalize → text/symbolic thích ứng | GPT-4o-mini/4o/3.5; ✘ | ✘ | text vs program | WikiTQ, TabFact, FeTaQA | 78,13 WikiTQ | chưa thấy |
| 16 | Mix-SC (2023, NAACL'24) | song song DP + PyAgent, vote có trọng số ưu DP | GPT-3.5; ✘ | **✔ theo số mẫu** (10 vs 10; mỗi mẫu PyAgent ≤5 bước) | **tool/view (text vs Python)** | WTQ | 73,06 vs SC-10 66,39 | chưa thấy |
| 17 | NormTab (2024, EMNLP-F) | chuẩn hoá bảng 1 lần rồi text-to-SQL | GPT-3.5, GPT-4-turbo, Gemini-1.5-flash; ✘ | ✘ | — | WikiTQ, TabFact | SQL 51,3 → 61,2 | ✔ |
| 18 | TaPERA (2024, ACL; không arXiv) | planner hỏi–đáp lặp → Python → answer gen; planner quyết dừng | GPT-3.5; Llama-2-7B thất bại | ✘ | — | **FeTaQA**, QTSumm (dài) | người chấm +0,26 faithfulness; **metric tự động thấp hơn** | ✔ |
| 19 | CoAgt (2025, PeerJ CS; không arXiv) | Collectors (chunk 1000 token) → Synthesizer → Refiner; cố định | GPT-4o; ✘ | ✘ | chia bảng | WikiTQ, TabFact | 85,4 WikiTQ (EM **sau chuẩn hoá**) | ✔ |
| 20 | ST-Raptor (2025, SIGMOD'26 ext.) | HO-Tree + pipeline thao tác cây + verify xuôi/ngược | DeepSeek-V3 + InternVL2.5-26B; ✘ | ✘ | — | **SSTQA (bán cấu trúc, merged)**, WikiTQ-ST, TempTabQA-ST | SSTQA +5,9 vs GPT-4o, +9,2 vs DS-V3 (LLM chấm) | ✔ |
| 21 | Orchestra (2026, ICDE) | logic agent ↔ query agent + decision agent, MC 5 lần | **✔ Qwen2.5-7B, Llama3.1-8B, Mistral-7B, Gemma2-9B**, … | ✘ (vs CoT 1 call, ReAcTable) | tách ngữ cảnh + sampling | WikiTQ, TabFact, TableBench | Qwen2.5-7B WikiTQ 48,7 → 68,6 | ✔ |
| 22 | Critic DRE (2026, ACL Oral) | critic (Sonnet+gt / Critic-4B đã train) + rejection sampling | **✔ Qwen3-8B**, 1,7–20B | ~ (N=8 mẫu) | — | WTQ, TableBench, FinQA | Qwen3-8B +1,1 (Critic-4B), +1,8 (có gold) | ✔ |
| 23 | Table-R1 (Yale, 2025, EMNLP) | 1 model RLVR, không tool | **✔ Qwen2.5-7B, Llama-3.1-8B (checkpoint công bố)** | ✘ | — | 13 bộ gồm **FeTaQA, HiTab** | WTQ 54,8 → 79,8 (Qwen7B) | ✔ + HF |
| 24 | MATATA (2024, ICDAR'25) | planner đã train chọn chuỗi tool; LoRA mỗi tool | **✔ Phi3-mini 3,8B, Ministral-8B (fine-tune)** | ✘ | tool | FinQA, TAT-QA, TabMWP | FinQA 47,1 → 70,1 (3,8B, PE → train) | chưa thấy |
| 25 | Chain-of-Table (2024, ICLR) | LLM lập kế hoạch động trên 5 phép bảng | PaLM 2, GPT-3.5, "LLaMA-2-17B" | ✘ | — | WikiTQ, TabFact, **FeTaQA** | +5,8 WikiTQ PaLM2 | ✔ |
| 26 | CHASE-SQL (2024, text-to-SQL) | 3 generator + fixer + **selector cặp đã fine-tune** | Gemini-1.5 | **✔ (vs SC)** | nhiều prompt/CoT | BIRD (SQL) | 73,01 vs SC 68,84 | chưa thấy |

**Chỉ xác minh ID và tiêu đề qua arXiv API, không đọc toàn văn.** Số liệu trong dòng này lấy từ
bảng của paper khác. Binder 2210.02875 (ICLR'23, ~50 call), Dater 2301.13808 (SIGIR'23, ~100
call), TabSQLify 2404.10150 (NAACL'24, WikiTQ 64,7 với GPT-3.5), Tree-of-Table 2411.08516
(≤29 call), ALTER 2407.03061 (WikiTQ 67,4 với GPT-3.5 theo H-STAR), TableRAG 2410.04739
(NeurIPS'24, bảng triệu token), SheetAgent 2403.03636 (WWW'25, thao tác spreadsheet),
Plan-of-SQLs 2412.12386 (TMLR'25), Weaver 2505.18961 (dùng metric REM *(theo khảo sát 09-18)*),
MAC-SQL 2312.11242 (COLING'25; CoQ chạy lại được 52,92 WikiTQ), MAG-SQL 2408.07930 (55,87),
Table-r1 cho SLM 2506.06137 (LLaMA-8B, RL program-based), Reasoning-Table 2506.01710,
OpenTable-R1 2507.03018 (4B, open-domain), TableMind 2509.06278, OHD 2602.01969 (ICML'26, biểu
diễn merged/header phân cấp), STR 2605.31550 (triplet cho bảng phân cấp), TraceBack 2602.13059
(attribution), TabTrim 2601.03851 (ACL'26, pruning bảng), "Evolving from Lessons" 2607.22633
(ICDE'27).

---

## 3. Method cards

Các card xếp theo mức liên quan tới Open-ViTabQA. Mỗi card kết thúc bằng một dòng **Áp dụng**.

### 3.1 Orchestra — Accurate Table Question Answering with Accessible LLMs
- **Nguồn:** Jiang et al., ICDE 2026. arXiv [2601.03137](https://arxiv.org/abs/2601.03137), đã
  mở metadata và đọc PDF.
- **Vai và tương tác:**
  - *logic agent* suy luận và ra chỉ thị, không viết code.
  - *query agent* dịch chỉ thị thành SQL/Python.
  - *decision agent* trả lời dựa trên ngữ cảnh đã được lọc: bỏ few-shot và code, chỉ giữ bảng
    trung gian.
  - Logic agent quyết định khi nào dừng (tối đa 5 vòng). Chạy 5 lần Monte Carlo ở nhiệt độ 0,7
    để hiệu chỉnh đáp án.
  - Đây là **agency thật** ở bước dừng. Tương tác logic ↔ query là hai chiều.
- **Backbone:** Mistral-7B, Gemma2-9B, Llama3.1-8B/70B, Qwen2.5-7B/14B/72B, DeepSeek-V3.
- **Kết quả ≤10B**, theo thứ tự CoT / ReAcTable / Orchestra:
  - WikiTQ, Qwen2.5-7B: 48,7 / 57,9 / 68,6. Llama3.1-8B: 40,3 / **2,5** / 64,9.
    Gemma2-9B: 43,6 / 46,0 / 64,2.
  - TabFact, Qwen2.5-7B: 71,1 / 74,2 / 82,7.
  - TableBench, Qwen2.5-7B: 31,6 / 35,5 / 52,6.
- **Baseline:** không compute-matched. CoT chỉ 1 call, không có SC. Chi phí trên TableBench với
  Qwen2.5-7B là **23,7 request, khoảng 180k token input mỗi câu**, so với 1 request và 818 token
  của CoT. Ablation: hệ hai agent đã hơn ReAcTable, và thêm decision agent thì lợi thêm; lợi này
  giảm dần khi model lớn lên (hình trong paper, không trích số).
- **Đa dạng đến từ:** tách ngữ cảnh theo vai trên cùng một model, cộng với sampling.
- **Merged header / unanswerable:** không đề cập.
- **Code:** github.com/Yangfan-Jiang/orchestra.
- **Áp dụng:** đây là bằng chứng rõ nhất rằng *tách ngữ cảnh* (logic không thấy code, quyết định
  không thấy few-shot) giúp model 7–9B, và ReAcTable sụp ở 8B. Nhưng baseline yếu, và chi phí
  khoảng 24× so với FS+normalize của ta chưa được đối chứng.

### 3.2 Chain-of-Query (CoQ)
- **Nguồn:** Sui et al., AACL-IJCNLP 2025 (oral). arXiv
  [2508.15809](https://arxiv.org/abs/2508.15809), đã đọc.
- **Vai:** Semantic Splitter (tạo schema dạng ngôn ngữ tự nhiên, tách câu hỏi con song song) → SQL
  Query Generator (sinh từng clause, sửa lỗi, rollback về query hợp lệ gần nhất) ⇄ Dynamic Planner
  (quyết định thêm clause hay dừng vì dữ liệu đã đủ) → Answer Generator. Planner là **một điểm
  quyết định của LLM**, còn lại là pipeline.
- **Backbone:** GPT-3.5, GPT-4.1, LLaMA-2-13B, **LLaMA-3.1-8B**, DeepSeek-V3.
- **Kết quả ≤10B, WikiTQ, LLaMA-3.1-8B:** CoQ 62,18 (SQL lỗi 5,62%), Chain-of-Table 54,17,
  Few-shot QA 39,94, MAG-SQL 45,49.
- **Kết quả khác:**
  - GPT-3.5: 74,77 so với Tree-of-Table 61,11.
  - IM-TQA (bảng phức tạp: chuyển vị, lồng, bất quy tắc): 74,96 so với MAG-SQL 68,90 và
    Chain-of-Table 48,80. Đoạn đã đọc không nêu backbone của bảng này.
  - **FeTaQA, GPT-3.5:** BLEU 22,19 so với CoTab 20,45; ROUGE-L 0,54 so với 0,52.
- **Baseline:** không compute-matched. Các baseline Few-shot, Binder, Dater được lấy lại từ paper
  Chain-of-Table. Trung bình 7,63 call, tối đa 22.
- **Ablation (WikiTQ, GPT-3.5):**
  - bỏ hybrid reasoning (SQL chỉ lấy dữ liệu trung gian, LLM suy luận logic): −18,81
  - bỏ sinh SQL từng clause: −17,04
  - bỏ schema dạng ngôn ngữ tự nhiên: −10,12
  - bỏ tách câu hỏi song song: −1,82
- **Đa dạng:** kênh SQL cộng kênh LLM. **Giới hạn:** chỉ tiếng Anh và tiếng Trung. Empty result
  được xử lý như lỗi cần sửa, không phải tín hiệu abstain.
- **Code:** github.com/SongyuanSui/ChainofQuery.
- **Bản chạy lại trong repo:** 57,86 EM / 73,20 F1 trên Open-ViTabQA. `PROVENANCE.md` ghi rõ bản
  snapshot **thiếu clause agent** nên chạy chế độ `coq_base_sql_fallback`. Như vậy chưa phải CoQ
  đầy đủ.
- **Áp dụng:** ý tưởng đáng giá là "SQL chỉ để lấy dữ liệu, LLM suy luận trên kết quả", vì nó
  tránh việc executor ghi đè đáp án như D04. Kết quả IM-TQA là phản ví dụ quan trọng cho nhận định
  "SQL hỏng trên bảng phức tạp": ở đó mọi phương pháp dùng SQL đều hơn text (xem mục 4.2). Nhưng
  muốn kết luận thì phải chạy lại bản có clause agent.

### 3.3 MATA
- **Nguồn:** Hyeon et al., ACL Findings 2026. arXiv
  [2602.09642](https://arxiv.org/abs/2602.09642), đã đọc.
- **Vai:**
  - 6 LLM agent **cùng backbone**: CoT, PoT, text2SQL, Python-debug, SQL-debug, Judge (Judge gọi
    được tool).
  - 3 "tool" nhỏ: Scheduler (MobileBERT + MLP, 24,65M, **có train**), Confidence Checker
    (DeBERTaV3-large, **fine-tune** trên 173.664 mẫu sinh bằng các model 13–14B trên
    WikiTQ/TabMWP/TabFact), Format Matcher (Qwen2.5-0.5B, không train).
- **Luồng điều khiển:** CoT luôn chạy. Scheduler chọn PoT hay SQL chạy trước; nếu kết quả trùng
  CoT thì bỏ đường thứ ba. CC chấm điểm các ứng viên; chỉ khi điểm thấp mới gọi Judge. Tức là
  **điều khiển nằm ở classifier đã train**, không nằm ở LLM.
- **≤10B:** llama3.2-3b, mistral-7b, phi4-mini-3.8b, qwen2.5-3b, qwen2.5-7b. EM trên toàn bộ test
  WikiTQ với llama3.2-3b: MATA 0,535, MixSC 0,232, TabLaP 0,220. Số của MixSC ở 3B thấp bất
  thường, có thể do cách cài lại baseline.
- **Baseline:** không compute-matched. So latency: MATA 27,55 giây, TabLaP (12 call) 48,89,
  MixSC (10 call) 44,48, SynTQA (3 call) 6,86.
- **Ablation:** CC là thành phần quan trọng nhất. Nó giảm số lần gọi Judge 95,8% trên Penguins và
  60,6% trên TableBench mà không mất độ chính xác. Scheduler giảm 7,6–14,6% số call; trên
  TableBench, bỏ Scheduler đôi khi còn tốt hơn một chút. Judge và FM quan trọng hơn trên bộ khó.
- **Benchmark:** TableBench chỉ dùng tập con đáp án dạng thực thể (693/886 câu), Penguins-in-a-
  Table. Metric EM, fuzzy, F1. Không có dữ liệu phân cấp hay unanswerable.
- **Code:** github.com/AIDASLab/MATA.
- **Áp dụng:** cơ chế early-exit theo độ đồng thuận (chỉ leo thang khi các đường bất đồng) hợp
  với tập của ta, vì 43% đáp án là một ô duy nhất. Nhưng MATA cần classifier có train. Format
  Matcher của nó thực chất là bộ chuẩn hoá đáp án, nên phải ablate riêng.

### 3.4 Mixture-of-Minds
- **Nguồn:** Zhou et al. (Meta AI), 10/2025. arXiv
  [2510.20176](https://arxiv.org/abs/2510.20176), đã đọc.
- **Vai:** planning → coding (pandas, thực thi) → answering. Luồng **cố định**. Mỗi agent được
  train riêng bằng GRPO trên các trajectory pseudo-gold lấy từ rollout MCTS.
- **Kết quả ≤10B, TableBench** (fact-checking / numerical / data-analysis, rồi trung bình):
  - Qwen3-8B, direct: 78,12 / 53,90 / 24,11 → 41,98.
  - Qwen3-8B, workflow chưa train: 79,17 / **68,18** / 21,37 → 47,38.
  - LLaMA-3.1-8B: 15,42 → 14,58. Riêng FC rơi 54,17 → 30,21.
  - Sau train (1 lượt): Qwen3-8B 57,44; LLaMA-3.1-8B 46,72.
- **Compute-matched (gần đúng):** base Qwen3-8B chạy song song 8 lần + SC chỉ đạt **41,94**, thua
  workflow 3 call chưa train (47,38). Trên FinQA ngoài miền, Qwen3-8B: single agent train bằng
  GRPO đạt 44,57, workflow chưa train đạt 54,63.
- **Đa dạng:** vai tuần tự. **Không có dữ liệu phân cấp hay free-form tiếng Việt.** Không thấy
  link code hay checkpoint trong các trang đã đọc.
- **Áp dụng:** là bằng chứng hiếm có ở ≤10B rằng tách plan/code thắng SC cùng compute. Nhưng toàn
  bộ lợi nằm ở câu tính toán, mà câu cần tính trong tập của ta chỉ chiếm 3%, và workflow làm hại
  câu fact-checking trên LLaMA-8B. Trần áp dụng thấp.

### 3.5 MACT — Efficient Multi-Agent Collaboration with Tool Use
- **Nguồn:** Zhou et al. (Bosch), NAACL Findings 2025. arXiv
  [2412.20145](https://arxiv.org/abs/2412.20145), đã đọc.
- **Vai:**
  - Planning agent sinh (thought, action, estimated observation) theo kiểu ReAct, với 6 intent:
    Retrieval, Calculation, Search, Read, Ask, Finish.
  - Coding agent sinh Python. Có thêm calculator và Wikipedia search.
  - Mỗi bước lấy 5 mẫu rồi self-consistency. Observation cuối là phiếu trội giữa ước lượng của
    planner và kết quả code thực thi.
  - Có module "efficiency": nếu 5 mẫu của planner đồng thuận hoàn toàn (α=1) thì trả lời ngay
    không dùng tool.
  - Planner quyết định Finish, nên đây là **agency thật**.
- **Backbone:** GPT-3.5; Qwen2-72B (planner) + CodeLlama-34B (coder).
- **Kết quả ≤10B, WTQ / TAT / CRT / SciTab:**
  - Qwen2-7B + DeepSeek-Coder-7B: 58,4 / 61,9 / 46,4 / 45,9.
  - LLaMA-7B + DS-Coder-7B: 38,1 / 28,3 / 40,0 / 41,1.
  - Không có baseline single-model 7B cùng bảng; chỉ so với các model đã fine-tune.
- **Baseline (gần compute-matched):** SC(Qwen72B + CL34B) với 5 mẫu CoT đạt 69,0 / 56,7 / 61,4 /
  54,4; MACT đạt 72,6 / 66,2 / 64,4 / 59,8, trung bình hơn khoảng 6 EM. Nhưng MACT dùng 5–65 call,
  khoảng 15 call với efficiency module trên WTQ theo ước tính của chính paper, so với 10 call của
  SC.
- **Ablation:** bỏ coder và tool: WTQ 72,6 → 67,1. Bỏ search gần như không đổi. Với GPT-3.5,
  **Mix-SC vẫn thắng MACT trên WTQ** (73,6 so với 70,4). Tác giả quy cho "table-cleaning và
  kiểm soát định dạng đáp án theo dataset" của Mix-SC.
- **Lỗi:** khoảng một nửa do coder viết code sai hoặc hiểu sai cấu trúc bảng; **khoảng 1/3 do EM
  quá chặt**. Trên TAT, GPT-4 chấm 87,8 trong khi EM chỉ 66,2.
- **Merged header / unanswerable:** không báo cáo.
- **Code:** github.com/boschresearch/MACT. Chỉ tiếng Anh.
- **Áp dụng:** kênh tool có đóng góp đo được (−5,5 khi bỏ). Nhưng chính paper cho thấy chuẩn hoá
  định dạng đáp án ngang giá với cả kiến trúc. Cùng chẩn đoán với POMA.

### 3.6 Table-Critic
- **Nguồn:** Yu et al., ACL 2025. arXiv [2502.11799](https://arxiv.org/abs/2502.11799), đã đọc.
- **Vai:** Judge (xác định bước sai, đi theo cây lỗi) → Critic (phê bình bước sai đầu tiên, dựa
  trên template) → Refiner (chỉ giữ chuỗi đến trước bước sai rồi làm lại phần sau) → lặp cho tới
  khi Judge nói "Correct" hoặc K=5. Curator cập nhật "self-evolving template tree" sau mỗi câu,
  tức là học xuyên suốt tập test mà không dùng gold. Cùng một model đóng mọi vai, nhiệt độ 0.
  Chuỗi ban đầu lấy từ Chain-of-Table.
- **Backbone:** Qwen2.5-72B, LLaMA3.3-70B, GPT-4o-mini. **Không có kết quả ≤10B.**
- **Kết quả WikiTQ:** Qwen72B 77,2 (CoTable 68,3); LLaMA70B 70,1 (Critic-CoT 66,8);
  GPT-4o-mini 73,9 (CoTable 67,5).
- **Tỉ lệ sửa và phá (Qwen72B, WikiTQ):** sửa đúng 9,6% và làm hỏng 0,7%, cả hai tính trên **tổng số câu** (9,6 − 0,7 = 8,9 = 77,2 − 68,3). Critic-CoT:
  sửa 5,6%, phá 4,9%.
- **Compute-matched:** ✔. Chain-of-Table với SC 15 lời giải chỉ đạt 70,0 WikiTQ, còn Table-Critic
  tốn khoảng 1,87× token và đạt 77,2. Bỏ cơ chế self-evolving: −1,1.
- **Đa dạng:** persona trên cùng model, cộng tri thức lỗi tích luỹ qua template. **Merged /
  unanswerable:** không có.
- **Code:** github.com/Peiying-Yu/Table-Critic.
- **Áp dụng:** tỉ lệ phá thấp là nhờ critic *định vị bước* và bám cây lỗi (Row Error / Column
  Error), chứ không phải critic chung chung. Nhưng bằng chứng chỉ có ở cỡ ≥70B, và critic trên
  Qwen3-8B (card DRE) chỉ thêm khoảng 1 điểm.

### 3.7 Critic DRE — When LLMs Read Tables Carelessly
- **Nguồn:** Yang et al., ACL 2026 Oral. arXiv [2606.32029](https://arxiv.org/abs/2606.32029),
  đã đọc.
- **Nội dung:** đo "data referencing error" (trích sai ô, bỏ sót dòng) rồi dùng critic để lọc
  hoặc rejection-sample. Không phải hệ multi-agent đầy đủ, nhưng là bằng chứng critic **trên đúng
  Qwen3-8B**.
- **Số liệu, Qwen3-8B trên WTQ:**
  - accuracy 77,14%, DRE rate 14,04%.
  - Prompt yêu cầu "không trích sai" chỉ đưa DRE xuống 12,50% và accuracy không đổi.
  - Rejection sampling với Sonnet-3.7 được nhìn gold (cận trên): +1,80.
  - Với Critic-4B (SFT + RLVR, dữ liệu gán nhãn bởi Sonnet): +1,11 trên WTQ, +1,02 trên
    TableBench, +0,26 trên FinQA.
  - Model yếu lợi nhiều hơn: Distill-Qwen-7B +4,5 đến +6,9.
- **Chi phí:** N=8 mẫu cộng các lượt gọi critic.
- **Code:** github.com/ayyyq/table-referencing.
- **Áp dụng:** với Qwen3-8B, trần lợi của critic định vị ô vào khoảng 1–2 điểm, dưới ngưỡng
  phân giải khoảng 2 EM của test 992 câu. Critic chỉ đáng thử nếu nhắm đúng nhóm lỗi đặc thù
  (merged cell), và phải đo tỉ lệ phá.

### 3.8 TableZoomer
- **Nguồn:** Xiong et al. (TeleAI), 09/2025. arXiv
  [2509.01312](https://arxiv.org/abs/2509.01312), đã đọc.
- **Vai:** Table Describer (tạo schema JSON một lần cho mỗi bảng) → Query Planner (tách câu hỏi
  con, phân loại column-only hay row-column) → Table Refiner (chọn cột, liên kết thực thể bằng LCS
  với ngưỡng 0,6, zoom schema) → Code Generator (PoT có sửa lỗi) → Answer Formatter. Có vòng ReAct
  tối đa 5 lượt, trong đó LLM quyết có hỏi tiếp không. Tác giả tự nhận workflow là cố định.
- **≤10B, Qwen3-8B (thinking):** DataBench 67,82 → 87,16; TableBench FC 54,17 → 79,17, NR 54,41
  → 66,25. Baseline là PoT một call, **không compute-matched**.
- **Ablation (DataBench, Qwen3-8B):** schema thay bảng +6,51 → thêm chọn cột 84,67 → thêm entity
  linking 86,40 → thêm ReAct 87,16. Vòng ReAct chỉ thêm 0,76.
- **Chi phí:** tối thiểu 5 call. **Bảng DataBench trung bình 513.359 ô**, tức lợi ích tập trung ở
  bảng khổng lồ.
- **Code:** github.com/ccx06/TableZoomer.
- **Áp dụng:** thấp. Tập của ta có p50 là 647 token, nên cơ chế "zoom" chỉ chạm phần đuôi bảng
  dài. Entity linking theo LCS có thể hữu ích cho tên riêng tiếng Việt có dấu.

### 3.9 AutoPrep
- **Nguồn:** Fan et al., VLDB 2025. arXiv [2412.10422](https://arxiv.org/abs/2412.10422), đã đọc.
- **Vai:** Planner dùng Chain-of-Clauses (sinh "Analysis Sketch" giống SQL, rồi xét từng clause
  cùng dữ liệu cột liên quan để đề xuất thao tác) → Programmer riêng cho Filter / Derive /
  Normalize, chọn hàm từ function pool (`to-numerical`, `format-datetime`, `clean-string`,
  `infer` …) → Executor (chạy, gửi lỗi về) → Analyzer (mặc định NL2SQL). LLM quyết *thao tác
  nào*, nhưng thứ tự stage cố định.
- **Backbone:** DeepSeek-V2.5, GPT-3.5, Llama-3.1-70B, Qwen2.5-72B. **Không có ≤10B.**
- **Kết quả (DeepSeek), WikiTQ:** NL2SQL 52,83 → 66,09; End2End 56,65 → 63,14; CoT 54,95 →
  61,12. So với CoTable, trung bình +3,05 WikiTQ và +1,96 TabFact.
- **Ablation (DeepSeek), WikiTQ / TabBench:** bỏ Normalize −4,07 / −8,52; bỏ Derive −4,30;
  bỏ Filter −3,31; thay Chain-of-Clauses bằng prompt trực tiếp 66,09 → 58,17.
- **Metric:** dùng evaluator của Binder, tức là so khớp nới lỏng về ngữ nghĩa.
- **Code:** github.com/ruc-datalab/AutoPrep.
- **Áp dụng:** trung bình. Chuẩn hoá giá trị ô *theo câu hỏi* (số và ngày kiểu Việt như
  "1.234,5" hay "tháng 3 năm 2020") có cơ chế rõ cho kênh chương trình. Với kênh đọc text, lợi
  chủ yếu đến từ Filter.

### 3.10 H-STAR
- **Nguồn:** Abhyankar et al., NAACL 2025. arXiv [2407.05952](https://arxiv.org/abs/2407.05952),
  đã đọc.
- **Luồng (cố định):**
  - Trích cột bằng SQL trên bảng gốc cộng trích cột bằng text trên **bảng chuyển vị** ("multi-
    view"). Sau đó trích dòng bằng SQL cộng kiểm tra dòng bằng text.
  - Suy luận thích ứng: LLM quyết câu có cần tính toán không; nếu cần thì dùng kết quả SQL làm
    bằng chứng phụ cho bước suy luận text.
  - Tổng khoảng 10 call: mỗi bước trích lấy 2 mẫu, cộng 1–2 call suy luận.
- **Backbone:** GPT-3.5, PaLM-2, GPT-4o-mini, Gemini-1.5-Flash, Llama-3-70B. Không có ≤10B.
- **Kết quả WikiTQ:** GPT-3.5 69,56 (CoTable 59,94, TabSQLify 64,70); Llama-3-70B 75,76
  (CoT 65,49).
- **Ablation (PaLM-2, WikiTQ):**
  - bỏ suy luận thích ứng: −7,15
  - chỉ dùng text (H-STAR_text): 61,47; chỉ dùng SQL (H-STAR_sql): **46,09**
  - bỏ suy luận text: 54,35
- **Bảng dài (>4000 token):** 64,84 so với CoTable 44,87.
- **Code:** github.com/nikhilsab/H-STAR. Tác giả đưa bảng phân cấp vào hướng tương lai.
- **Áp dụng:** trung bình. Nguyên tắc "text là xương sống, SQL chỉ là bằng chứng phụ" khớp với
  thất bại của D04. Cơ chế view chuyển vị là một nguồn đa dạng *không phải persona*.

### 3.11 Mix Self-Consistency (Rethinking Tabular Data Understanding)
- **Nguồn:** Liu et al., NAACL 2024. arXiv [2312.16702](https://arxiv.org/abs/2312.16702), đã đọc.
- **Luồng:** đường text (DP) và PyAgent (tối đa 5 bước Python) chạy song song, mỗi đường 5 mẫu ở
  nhiệt độ 0,8, bỏ phiếu và ưu tiên DP khi hoà. Thêm NORM: dùng LLM quyết dòng đầu hay cột đầu là
  header, chuyển vị nếu cần. **Không có LLM điều khiển.**
- **Compute-matched ✔ theo số mẫu, không theo số call** (GPT-3.5, WTQ lấy mẫu; mỗi mẫu PyAgent
  có thể tốn tới 5 bước shell):
  - DP + SC 10 mẫu: 66,39; PyAgent + SC 10 mẫu: 61,39.
  - **Mix-SC 5+5: 73,06.** Trên toàn bộ WTQ: 73,6.
  - Self-evaluation chọn giữa 2 đường: 64,22.
- **Độ bền cấu trúc:**
  - chuyển vị: DP 59,50 → 51,14; PyAgent 55,91 → **12,45**
  - chuyển vị + xáo dòng: PyAgent rơi xuống 8,96
  - NORM phục hồi được, nhưng trên bảng gốc làm DP giảm 0,84
- **Lỗi bổ sung cho nhau:** DP sai chủ yếu vì hiểu sai bảng (42%); PyAgent sai chủ yếu vì code
  (38%).
- **Áp dụng:** là bằng chứng compute-matched sạch nhất rằng *đa dạng công cụ/view* hơn *lặp một
  đường*. Nhưng dựa trên GPT-3.5 với sampling ở nhiệt độ cao, trong khi ta chạy nhiệt độ 0. Thí
  nghiệm độ bền đo chuyển vị và xáo dòng, không đo merged cell; nó chỉ áp dụng cho Open-ViTabQA
  nếu biểu diễn Flatten của ta sinh ra kiểu nhiễu cấu trúc tương tự (xem mục 4.2).
- **Merged header / unanswerable:** không báo cáo.

### 3.12 TableMaster
- **Nguồn:** Cao & Liu, ICLR 2026. arXiv [2501.19378](https://arxiv.org/abs/2501.19378), đã đọc.
- **Luồng:** trích cấu trúc (header, cột khoá) → tra cột/dòng (dòng bằng SQL) → tạo
  table-of-focus → kiểm tra đủ thông tin (thiếu thì thêm cột) → verbalize bảng → LLM chọn suy
  luận text hay text-guided symbolic. Luồng cố định, có hai điểm LLM tự chọn.
- **Kết quả:** GPT-4o-mini WikiTQ 78,13, TabFact 90,12. Ablation: bỏ suy luận text −4,28; bỏ
  symbolic −2,03; bỏ verbalization −2,35.
- **Text và symbolic (WikiTQ):**
  - gpt-4o: text 83,98, symbolic 74,63
  - gpt-4o-mini: text 72,97, symbolic 61,83
  - Chỉ gpt-3.5 có text-guided symbolic (61,97) thắng text (59,92).
- **Giới hạn:** tác giả giả định bảng phẳng. Bước chuẩn hoá bảng "hoang dã" không bật trong thí
  nghiệm vì bảng đã sạch. Số HiTab (74,2, phải dùng o1 để làm phẳng, thua E5 77,3) *(theo khảo sát
  09-18)*. Đoạn đã đọc không có URL code và số call.
- **Áp dụng:** cung cấp số đo nói rằng symbolic chỉ nên là phụ trợ cho model yếu. Không giúp gì
  cho header phân cấp.

### 3.13 PoTable
- **Nguồn:** Mao et al., IEEE TKDE 2026. arXiv [2412.04272](https://arxiv.org/abs/2412.04272),
  đã đọc.
- **Luồng:** 5 stage cố định (khởi tạo DataFrame → chọn dòng → làm sạch kiểu dữ liệu → suy luận →
  trả lời). Trong mỗi stage, LLM lập danh sách thao tác rồi sinh và chạy code từng thao tác, sửa
  lỗi tối đa 1 lần. Tối đa khoảng 10 call: 3 call lập kế hoạch, ≤6 call sinh code, ≤1 call sửa.
- **Kết quả (GPT-4o-mini / Llama-3.1-70B):** WikiTQ(D) 63,58 / 65,10 so với runner-up +4,38 /
  +2,71. TabFact(S) 88,93.
- **Ablation (TabFact S):** gộp thành một stage suy luận duy nhất (≤6 call) đạt 85,92.
- **Merged header / unanswerable:** không báo cáo.
- **Code:** github.com/Double680/PoTable. **Áp dụng:** thấp. Stage "làm sạch kiểu dữ liệu" tường
  minh là điểm đáng chú ý duy nhất; phần còn lại là PoT có cấu trúc, trần thấp vì 3% câu cần tính.

### 3.14 ReAcTable
- **Nguồn:** Zhang et al., VLDB 2024. arXiv [2310.00815](https://arxiv.org/abs/2310.00815). Đọc
  phần phương pháp; phần kết quả không được trả về.
- **Luồng:** một LLM, mỗi vòng chọn SQL, Python hoặc trả lời; code chạy ra bảng trung gian nối
  vào prompt. Có 3 kiểu voting: majority, tree-exploration, execution-based. Retry SQL trên các
  bảng trung gian trước đó.
- **Số liệu (từ nguồn khác):**
  - tự báo cáo 68,0 WikiTQ với Codex
  - bản GPT-3.5 đạt 52,4–52,5 (bảng của MACT và H-STAR)
  - **Orchestra chạy lại:** Llama3.1-8B 2,5%, Mistral-7B 3,6%, Qwen2.5-7B 57,9 WikiTQ; trung
    bình 10,7 request mỗi câu trên TableBench
  - MACT ghi 15–125 call
- **Code:** github.com/yunjiazhang/ReAcTable.
- **Áp dụng:** là phản ví dụ. Một agent ReAct với prompt dài sụp đổ ở 8B.

### 3.15 DataFactory
- **Nguồn:** Wang et al., Information Processing & Management 2026. arXiv
  [2603.09152](https://arxiv.org/abs/2603.09152), đã đọc.
- **Vai:** Data Leader (ReAct, chọn team bằng ngôn ngữ tự nhiên) + Database team (SQL) +
  Knowledge-Graph team (bảng được chuyển thành KG, truy vấn bằng Cypher). Cùng một LLM cho mọi
  vai. Đây là **agency thật**.
- **Kết quả, trung bình GPT-4o-mini / DS-V3 / Gemini-2.5-Flash, WikiTQ (EM):**
  End-to-End 54,6, MACT 66,1, AutoPrep 67,2, TabSQLify 69,6, DataFactory 72,8. Con số "+23,9%"
  trong abstract là *mức tăng tương đối trung bình so với tất cả baseline*, không phải điểm.
- **Model nhỏ nhất (Qwen3-14B):** WikiTQ 53,7, thấp hơn End-to-End của GPT-4o-mini. Bỏ KG team,
  Qwen3-14B chỉ còn 39,0; nghĩa là team ảnh hưởng mạnh ở model yếu. FeTaQA ROUGE-L 0,41–0,51.
- **"Inverted-U":** độ chính xác cao nhất ở 1–3 call và sụp khi trên 6 call (GPT-4o-mini trên
  WikiTQ: 77,0 → 5,9). Kết quả này bị gây nhiễu vì câu khó tự nhiên cần nhiều call hơn.
- **Chi phí:** khoảng 5k token mỗi câu WikiTQ. **Code:** chưa công bố.
- **Áp dụng:** thấp. KG và Cypher là thừa cho bảng nhỏ đơn lẻ. Dữ kiện "nhiều vòng thì hỏng" là
  quan sát chứ không phải thí nghiệm có đối chứng.

### 3.16 MAPLE
- **Nguồn:** Bai et al., ALTA 2025. arXiv [2506.05813](https://arxiv.org/abs/2506.05813), đã đọc.
- **Vai:** Solver (ReAct trên bảng) → Checker (chấm 0–2 cho kiểu đáp án, định dạng, căn cứ) →
  nếu chưa đủ điểm thì Reflector (chẩn đoán và đưa kế hoạch sửa) → lặp. Archiver quản lý
  long-term memory.
- **Kết quả WikiTQ:** GPT-4o-mini 67,13; LLaMA3.3-70B 74,01; Qwen2.5-72B 73,39. Trung bình hơn
  baseline tốt nhất 6,29.
- **Ablation cộng dồn (LLaMA-70B):** baseline 45,58 → Solver 63,81 → + Checker 65,91 →
  + Reflector 71,09 → + Archiver 74,01. Memory không evolve đạt 67,89.
- **Số call mỗi câu:** không báo cáo trong các trang đã đọc; số vòng bị chặn bởi tham số
  "remaining attempts" `r`. **Merged header / unanswerable:** không báo cáo.
- **⚠ Rò rỉ khả dĩ:**
  - Eq. 4 và Algorithm 2 cho thấy Archiver tóm tắt memory dùng **đáp án gold `a_g`**.
  - Bảng 8 báo 1.023 note, bằng "23,5%" số mẫu, khớp đúng 4.344 câu **test** WikiTQ. TabFact có
    427 note, bằng 21,1% của 2.024 câu test.
  - Paper không nói memory xây trên tập nào. Cần đọc code trước khi tin số của Archiver
    (+2,9, và +6,1 so với không evolve).
- **Code:** github.com/bettyandv/MAPLE-table-reasoning. Không có ≤10B.
- **Áp dụng:** thấp. Phần Checker/Reflector có đóng góp đo được (+7,3), nhưng chỉ ở 70B.

### 3.17 PanelTR
- **Nguồn:** Ma, IJCNN 2025. arXiv [2508.06110](https://arxiv.org/abs/2508.06110), đã đọc.
- **Luồng:** 5 persona "nhà khoa học" (Einstein, Newton, Curie, Turing, Tesla) trên cùng
  DeepSeek-V3 ở nhiệt độ 1,0. Mỗi persona tự điều tra rồi tự review, sau đó peer review; không
  đồng thuận thì bỏ phiếu đa số. t_max=1. **Luồng cố định**, được viết cứng bằng AutoGen.
- **Kết quả:** TAT-QA EM 58,0 → 67,2; SEM-TAB-FACTS dev 74,3 → 87,1; WikiSQL dev 85,6 → 87,2;
  FEVEROUS acc 74,6 → 75,5. Bảng VI lại ghi 73,0 cho PanelTR đầy đủ, không nhất quán.
- **Baseline:** vanilla một call. Không compute-matched, không so với MAS nào (tác giả tự nhận).
- **Ablation quan trọng:** đổi persona ngẫu nhiên hoặc sang nghề khác (bác sĩ, nghệ sĩ …) cho kết
  quả tương đương. **Danh tính persona không đóng vai trò gì.** Thêm vòng thảo luận thì kết quả
  giảm.
- **Code:** github.com/rexera/PanelTR.
- **Áp dụng:** không. Đây là tiền thân của ViPanelTR cùng nhóm, và chính ablation của nó ủng hộ
  việc loại D14.

### 3.18 CoAgt — Chain of Agents cho dữ liệu bảng
- **Nguồn:** Alrayzah & Alqhtani, PeerJ Computer Science 11:e3423 (2025), DOI
  10.7717/peerj-cs.3423. Không có arXiv. Đọc PDF trong máy, trang 1–6 và 9–14.
- **Luồng (cố định):** bảng chia chunk khoảng 1.000 token → mỗi chunk một Collector (nhiệt độ
  0,2) → Synthesizer (0,5) → Answer Refiner (định dạng, chữ hoa/thường). Tiền xử lý chuẩn hoá số
  và ngày. Số call bằng số chunk cộng 2, tức khoảng **3 call cho bảng cỡ p50 của ta** (chỉ 1
  collector).
- **Kết quả:** GPT-4o WikiTQ 85,4, TabFact 96,5. Nhưng các baseline lấy từ literature với
  Codex/ChatGPT (không cùng backbone). EM được tính **sau bước chuẩn hoá số và ngày**. Chunk
  1.000 token đạt 85,4, chunk 2.500 token đạt 81,5 (trên một mẫu). Trong các trang đã đọc không có
  ablation bỏ agent.
- **Code:** github.com/Asmaa-Alrayzah/CoAgt.
- **Bản chạy lại trong repo:** 32,36 EM / 68,87 F1 trên Open-ViTabQA. F1 cao nhưng EM thấp là dấu
  hiệu đáp án dài dòng.
- **Áp dụng:** không. Cơ chế chia chunk vô nghĩa với bảng ≤1.000 token, và số 85,4 phụ thuộc
  metric nới lỏng cộng backbone mạnh.

### 3.19 TaPERA
- **Nguồn:** Zhao et al., ACL 2024 (Long), ACL Anthology
  [2024.acl-long.692](https://aclanthology.org/2024.acl-long.692/). **Không có arXiv.** Đã mở
  trang Anthology và đọc PDF.
- **Luồng:** Content Planner (tách câu hỏi con, lặp; **LLM quyết khi nào plan đã xong**) →
  Execution-based Reasoner (Python + self-debug cho mỗi câu hỏi con) → Answer Generator (câu trả
  lời con, rồi câu trả lời dài bám theo output chương trình). Trung bình 2,6 cặp QA mỗi plan trên
  FeTaQA.
- **Backbone:** GPT-3.5-turbo-1106. Tác giả ghi **Llama-2-7B few-shot "struggles to generate
  executable programs"**.
- **Kết quả, người chấm FeTaQA:** faithfulness 4,18 so với Dater 3,92; comprehensiveness 4,10 so
  với Blueprint 3,94.
- **Kết quả, metric tự động:**
  - FeTaQA: ROUGE-L 53,4 so với Dater 54,0 và 1-shot 50,3; BLEU 29,5 so với Dater 29,8.
  - QTSumm: TaPERA **thấp nhất** (BLEU 14,6 so với 1-shot 20,5).
- **Code:** github.com/yilunzhao/TaPERA.
- **Áp dụng:** cảnh báo cho metric n-gram. Phân rã rồi tổng hợp làm câu trả lời lệch văn phong
  so với câu tham chiếu, nên lợi về độ trung thực không hiện lên ROUGE/METEOR, là các metric
  Open-ViTabQA chấm.

### 3.20 ST-Raptor
- **Nguồn:** Tang et al. (SJTU), bản mở rộng của paper SIGMOD 2026. arXiv
  [2508.18190](https://arxiv.org/abs/2508.18190), đã đọc.
- **Luồng:**
  - Table2Tree: VLM InternVL2.5-26B nhận diện header, luật heuristic và DFS dựng **HO-Tree**
    (Meta-Tree cho header phân cấp, Body-Tree cho nội dung, xử lý merged cell).
  - Question2Pipeline: DeepSeek-V3 tách câu hỏi con thành chuỗi thao tác cây.
  - AnswerVerifier: kiểm tra xuôi (tham số phải khớp ô thật, kết quả phải đủ; **có thể dừng và
    trả "unanswerable"**) và kiểm tra ngược (sinh câu hỏi khác có cùng đáp án, so độ tương tự
    pipeline).
- **Kết quả:** SSTQA (764 câu, bán cấu trúc) 72,39 so với GPT-4o 66,45 và DeepSeek-V3 63,22.
  WikiTQ-ST 71,17 so với DS-V3 69,64. Accuracy **do LLM chấm**.
- **Ablation:** bỏ Table2Tree −15,15; bỏ verifier −6,29; bỏ thao tác xử lý dữ liệu −7,30.
- **Bằng chứng theo độ sâu lồng (Bảng 4–5):** WikiTQ có độ sâu lồng 1,30 và merge ratio 0,009;
  SSTQA có độ sâu 2,52 và merge ratio 0,054. ReAcTable (SQL/Python) đạt 68,00 trên WikiTQ-ST, gần
  DeepSeek-V3 (69,64), nhưng chỉ 37,24 trên SSTQA (DeepSeek-V3: 63,22).
- **Chi phí:** khoảng 30 giây mỗi câu, trung bình 2,89 thao tác.
- **Code:** github.com/weAIDB/ST-Raptor.
- **Áp dụng:** trung bình. Đây là hệ duy nhất xử lý merged cell và header phân cấp bằng cấu trúc
  tường minh, và là hệ duy nhất có đường "unanswerable". Nhưng nó dựa trên model 671B cộng VLM
  26B, và biểu diễn cây phải so với 8+4 biểu diễn đã đo (D09, D12).

### 3.21 TableMind / TableMind++
- **Nguồn:** Cheng et al. (USTC). TableMind arXiv 2509.06278 (chỉ metadata);
  TableMind++ arXiv [2603.07528](https://arxiv.org/abs/2603.07528), đã đọc.
- **Cơ chế:** **một agent** Qwen3-8B, SFT trên 200 mẫu cộng RL (RAPO), vòng plan–action–reflect
  với sandbox code, tối đa 3 lượt tool. TableMind++ thêm lúc suy luận: 16 path, lọc plan bằng
  memory (trajectory trên tập train), sửa hành động khi độ tự tin token thấp, rồi vote có trọng
  số.
- **Kết quả:** WikiTQ 78,07; TabFact 93,73; **HiTab (ngoài miền) 73,69**; FinQA 45,48. Base
  Qwen3-8B trong bảng của họ: 50,47 / 70,34 / 63,12 / 27,83. Số base WikiTQ này thấp so với
  literature.
- **Code:** github.com/fishsure/TableMind-PP. Không thấy thông tin checkpoint.
- **Áp dụng:** cần fine-tune, ngoài phạm vi hiện tại. Không phải multi-agent.

### 3.22 Table-R1 (Yale) — Inference-Time Scaling for Table Reasoning
- **Nguồn:** Yang et al., EMNLP 2025. arXiv [2505.23621](https://arxiv.org/abs/2505.23621), đã
  đọc.
- **Cơ chế:** một model, không tool. Table-R1-SFT chưng cất từ DeepSeek-R1; Table-R1-Zero dùng
  RLVR. Train trên WTQ, HiTab, TabFact, FeTaQA; FeTaQA dùng reward BLEU + ROUGE-L.
- **Kết quả, Qwen2.5-7B-Instruct → Zero:** FeTaQA BLEU 21,0 → 30,6; WTQ 54,8 → 79,8; HiTab
  61,8 → 78,1.
- **Kết quả, Llama-3.1-8B-Instruct → Zero:** FeTaQA 21,7 → 32,7; WTQ 52,3 → 81,2.
- **Metric:** EM, câu trượt EM thì **chấm lại bằng GPT-4.1-mini**.
- **Checkpoint:** công bố tại huggingface.co/Table-R1.
- **Đối chiếu:** theo DRE, Table-R1-Zero-7B có DRE rate 19,29% trên WTQ, cao hơn Qwen3-8B.
- **Áp dụng:** không phải MAS. Checkpoint 7B/8B có thể thử như backbone thay thế mà không cần
  train, nhưng dữ liệu train chỉ tiếng Anh, và khả năng tiếng Việt chưa được kiểm.

### 3.23 MATATA
- **Nguồn:** Vinayagame et al., ICDAR 2025. arXiv [2411.18915](https://arxiv.org/abs/2411.18915),
  đã đọc.
- **Cơ chế:**
  - Planner sinh chuỗi tool: tra dòng/cột, trích ngữ cảnh, sinh chương trình, thực thi, tìm đơn
    vị (scale), trích đáp án.
  - Mỗi tool và planner là một LoRA trên Phi3-mini 3,8B hoặc Ministral-8B.
  - Train bằng weak supervision: chỉ dùng đáp án cuối, qua IT rồi KTO.
- **Kết quả (3,8B / 8B):**
  - FinQA: prompt-engineered cùng framework 47,06 / 57,11 → sau train 70,10 / 77,59.
  - TAT-QA: 43,05 / 51,29 → 74,44 / 77,81.
- **Áp dụng:** là bằng chứng rằng framework nhiều tool ở 3,8–8B **chỉ bằng prompt thì yếu**; phần
  lợi đến từ train. Code không thấy trong các trang đã đọc.

### 3.24 Chain-of-Table
- **Nguồn:** Wang et al., ICLR 2024. arXiv [2401.04398](https://arxiv.org/abs/2401.04398), đã
  đọc.
- **Cơ chế:** LLM chọn phép tiếp theo trong 5 phép (add/select column, select row, group,
  sort), sinh tham số, thực thi, lặp; tối đa 25 call.
- **Backbone:** PaLM 2, GPT-3.5 và "LLaMA 2 (Llama-2-17B-chat)". Paper ghi đúng như vậy, và **cỡ
  17B không tồn tại**.
- **Kết quả:** với LLaMA 2, WikiTQ 42,61 so với Dater 41,44 và few-shot 35,52. FeTaQA (PaLM 2):
  BLEU 32,61 so với End-to-End 28,37; ROUGE-L 0,56 so với 0,53.
- **Merged header / unanswerable:** không báo cáo. **Code:** github.com/google-research/chain-of-table
  (theo phần tham khảo của AutoPrep).
- **Áp dụng:** là baseline nền, cũng là chuỗi khởi tạo cho Table-Critic. Ở 8B đã bị CoQ và
  Orchestra vượt.

### 3.25 CHASE-SQL (text-to-SQL, ý tưởng chuyển được)
- **Nguồn:** Pourreza et al. (Google), 10/2024. arXiv
  [2410.01943](https://arxiv.org/abs/2410.01943), đã đọc.
- **Cơ chế:** 3 generator (divide-and-conquer CoT, query-plan CoT, ví dụ tổng hợp online), mỗi
  cái 7 ứng viên → query fixer → **selection agent so từng cặp** (fine-tune nhị phân).
- **Số liệu then chốt (BIRD dev, Gemini-1.5-pro):**
  - SC 68,84, selector 73,01, oracle 82,79.
  - "Ranker agent" nhét mọi ứng viên vào một prompt: 65,51, **tệ hơn cả SC**.
  - Độ chính xác chọn cặp khi một đúng một sai: Claude-3.5-sonnet chưa tune 60,21, Gemini-1.5-pro
    chưa tune 63,98, **Gemma-2-9B đã tune 64,28**, Gemini-flash đã tune 71,01.
- **Áp dụng:** adjudicator chưa tune chỉ đúng khoảng 60–64% trên các cặp bất đồng. Con số này là
  tham chiếu định lượng khi xét một "judge" chọn giữa các nhánh POMA.

---

## 4. Pattern chuyển được và pattern không chuyển được sang Open-ViTabQA

Các ràng buộc dùng để lọc lấy từ đề bài: p50 647 token; 43% đáp án là một ô; 4,5% `Null`;
53,5% câu có merged cell; 91% câu có đúng một hint; backbone Qwen3-8B ở nhiệt độ 0; hiệu ứng
dưới khoảng 2 EM không phân giải được; D04 và D14 đã bị loại.

### 4.1 Pattern có cơ chế hợp lý

1. **Nhiều đường với nguồn đa dạng là công cụ hoặc view, không phải persona. Chúng bỏ phiếu chứ
   không ghi đè.**
   - *Bằng chứng:* Mix-SC khớp theo số mẫu (10 vs 10, +6,7 điểm); lỗi của DP và PyAgent phân bố
     khác nhau. H-STAR dùng SQL làm bằng chứng phụ chứ không làm đáp án. CoQ tách "SQL lấy dữ
     liệu, LLM suy luận" (−18,8 khi bỏ).
   - *Cơ chế trên dữ liệu ta:* kênh chương trình mạnh ở đếm và tìm cực trị (group-by, sort); kênh
     text mạnh ở tra ô và ngữ nghĩa.
   - *Khác D04:* D04 *ghi đè* đáp án bằng executor. Mix-SC và H-STAR chỉ dùng kết quả chương
     trình như một phiếu hoặc bằng chứng, và ưu tiên text khi hoà.
   - *Giới hạn:* Mix-SC cần sampling ở nhiệt độ 0,8, không phải 0. Câu cần tính chỉ chiếm 3%.
     Độ bền của đường chương trình phụ thuộc cấu trúc: nó sụp khi bảng bị chuyển vị (Mix-SC),
     nhưng thắng trên IM-TQA (CoQ) và bảng lồng nông (ReAcTable trên WikiTQ-ST). Xem mục 4.2.

2. **Early-exit và cascade theo đồng thuận.**
   - *Bằng chứng:* MATA giảm 60–96% số lần gọi Judge mà không mất độ chính xác. MACT đi đường tắt
     khi 5 mẫu đồng thuận, tiết kiệm tới 33% vòng lặp mà không mất điểm. Scheduler của MATA chỉ
     chạy đường thứ ba khi hai đường đầu bất đồng.
   - *Cơ chế:* 43% đáp án là một ô, nên phần lớn câu có thể dừng ngay sau một hai call. Compute
     chỉ dồn vào các câu bất đồng.
   - *Giới hạn:* bộ chấm độ tin (CC) của MATA phải train. Mọi lợi ích cuối cùng vẫn phụ thuộc vào
     chất lượng bộ chọn trên các câu bất đồng; xem gạch đầu dòng cuối của mục 4.2.

3. **Tách ngữ cảnh theo vai cho model nhỏ.**
   - *Bằng chứng:* Orchestra, 7–9B, 4 họ model: agent logic không thấy code, agent quyết định
     không thấy few-shot. ReAcTable, vốn nhét mọi thứ vào một prompt, sụp ở Llama-8B và
     Mistral-7B.
   - *Cơ chế:* model nhỏ dễ bị nhiễu bởi ngữ cảnh dài và hỗn tạp.
   - *Giới hạn:* baseline trong paper là CoT một call; chi phí khoảng 24×. Chưa ai so với
     "few-shot cộng chuẩn hoá đáp án".

4. **Chuẩn hoá hoặc chuẩn bị giá trị ô, tách khỏi suy luận.**
   - *Bằng chứng:* AutoPrep (bỏ Normalize: −4,1 đến −8,5), NormTab (+9,9 cho SQL; 9% bảng bị hại),
     NORM của Mix-SC, bước chuẩn hoá của CoAgt và TableMaster.
   - *Cơ chế:* định dạng số và ngày tiếng Việt (dấu chấm phân tách nghìn, "tháng … năm …") phá
     phép so sánh và tính toán của SQL/pandas.
   - *Giới hạn:* lợi chủ yếu cho kênh chương trình. Với kênh text, NORM làm DP giảm 0,84.

5. **Tầng định dạng đáp án riêng, được ablate riêng.**
   - *Bằng chứng:* Format Matcher của MATA (0,5B), Answer Formatter của TableZoomer, Refiner của
     CoAgt, Answer Generator bám output chương trình của TaPERA. MACT thừa nhận 1/3 lỗi là do EM
     chặt, và thua Mix-SC vì Mix-SC kiểm soát định dạng.
   - *Cơ chế:* khớp văn phong tham chiếu cho EM, ROUGE, METEOR. Điều này nhất quán với phát hiện
     rằng gain của POMA chủ yếu đến từ chuẩn hoá.

6. **Critic định vị bước hoặc ô, có taxonomy lỗi.**
   - *Bằng chứng:* Table-Critic (tỉ lệ phá 0,7% trên tổng số câu, so với 4,9% của Critic-CoT, nhờ cây lỗi
     Row/Column Error), DRE
     critic, AnswerVerifier của ST-Raptor (−6,3 khi bỏ).
   - *Giới hạn:* trên Qwen3-8B, trần lợi khoảng 1–2 điểm (DRE), dưới ngưỡng phân giải. Chỉ đáng
     cân nhắc nếu nhắm đúng nhóm lỗi merged cell, và phải báo cả tỉ lệ sửa lẫn tỉ lệ phá.

7. **Biểu diễn cây cho header phân cấp, dùng như thao tác chứ không như chuỗi serialize.**
   - *Bằng chứng:* HO-Tree của ST-Raptor (−15,2 khi bỏ). Các hướng không-agent cùng mục tiêu:
     OHD (ICML'26) và STR, mới chỉ xác minh metadata.
   - *Cơ chế:* 53,5% câu có merged cell. Làm phẳng để chạy SQL thì mất thông tin (ST-Raptor và
     TableMaster đều ghi nhận).
   - *Giới hạn:* phải khác về cơ chế so với các biểu diễn đã đo ở D09/D12, tức là thao tác trên
     cây thay vì một cách serialize mới.

### 4.2 Pattern không chuyển (hoặc đã có bằng chứng ngược)

- **Persona và panel cùng backbone** (PanelTR, và phần "cùng model khác vai" của MAPLE/Table-
  Critic): ablation của chính PanelTR cho thấy danh tính persona không có tác dụng; thêm vòng thì
  tệ hơn. D14 đã đo và loại.
- **Chia chunk, bảng dài, KG** (CoAgt collectors, TableZoomer zoom, TableRAG, Tree-of-Table, ALTER,
  KG team của DataFactory): p50 là 647 token, nên hầu hết bảng chỉ có 1 chunk. Bản CoAgt chạy lại
  chỉ đạt 32,36 EM.
- **SQL-first trên bảng merged: bằng chứng lẫn lộn, tách theo độ sâu lồng.** Không nên loại cả
  khối; cần xác định Open-ViTabQA nằm ở phía nào.
  - *Chống SQL:*
    - Mix-SC: chuyển vị làm PyAgent rơi −77,7%. Đây là chuyển vị và xáo dòng, không phải merged
      cell.
    - H-STAR: chỉ-SQL đạt 46,09, chỉ-text 61,47.
    - CoQ với LLaMA-2: 13–24% SQL lỗi.
    - ST-Raptor, bảng lồng sâu (SSTQA, độ sâu lồng 2,52): NL2SQL đạt 24,0, ReAcTable 37,24, trong
      khi DeepSeek-V3 đọc HTML đạt 63,22.
  - *Ủng hộ SQL:*
    - IM-TQA (bảng chuyển vị, lồng, bất quy tắc): Few-shot 52,47, Chain-of-Table 48,80, Basic
      Text-to-SQL 63,16, MAG-SQL 68,90, CoQ 74,96.
    - Bảng lồng nông (WikiTQ-ST, độ sâu 1,30, merge ratio 0,009): ReAcTable 68,00, gần DeepSeek-V3
      69,64.
  - *Biến quyết định là độ sâu lồng và tỉ lệ merge*, chứ không phải chỉ con số 53,5% "có merged
    cell". Số liệu độ sâu lấy từ Bảng 4 của ST-Raptor. Muốn biết bằng chứng nào áp dụng, cần đo
    các chỉ số đó trên 329 bảng của Open-ViTabQA.
- **Memory dùng gold trên tập test (MAPLE):** Archiver tóm tắt memory có `a_g`, và số note khớp
  kích thước tập test. Nếu đúng là vậy thì đây là rò rỉ và số của Archiver không hợp lệ.
- **Template tree của Table-Critic là chuyện khác:** nó không dùng nhãn gold. Đây là thích nghi
  lúc test không cần nhãn; kết quả phụ thuộc thứ tự câu, nhưng không phải rò rỉ.
- **Lặp nhiều vòng:** DataFactory sụp khi trên 6 call; PanelTR càng nhiều vòng càng giảm;
  Table-Critic bão hoà sau khoảng 5 vòng. Với 91% câu chỉ một hint, lặp dài không có đối tượng để
  phục vụ.
- **Agent đơn với ngữ cảnh dài, hoặc backbone đời cũ, ở ≤8B:** ReAcTable ở Llama-3.1-8B đạt 2,5%;
  TaPERA với Llama-2-7B không sinh nổi code chạy được; MATATA bản prompt đạt FinQA 47–57;
  Mixture-of-Minds trên LLaMA-3.1-8B giảm 0,8. Ngược lại, các hệ prompt-only *giữ ngữ cảnh mỗi
  call ngắn và tách vai* lại chạy được ở 7–9B đời mới (Orchestra, CoQ-8B, TableZoomer-8B; mục
  4.1.3). Ranh giới là lượng ngữ cảnh mỗi call và đời backbone, không phải "prompt hay train".
  Riêng các agent đã train bằng RL (Table-R1, TableMind, Mixture-of-Minds bản train, MATATA) cần
  fine-tune, ngoài phạm vi hiện tại.
- **Bộ chọn chưa train gom mọi ứng viên vào một prompt:** ranker agent của CHASE-SQL tệ hơn SC
  3,3 điểm; bộ chọn cặp chưa tune chỉ đúng khoảng 60–64%.

### 4.3 Lưu ý khi đem số liệu literature so với POMA

1. **Metric:** nhiều gain trên WikiTQ dùng EM đã nới lỏng (Binder evaluator, chuẩn hoá trước EM,
   LLM chấm lại). Open-ViTabQA dùng EM chặt cộng F1/ROUGE/METEOR, nên các gain đó sẽ thu nhỏ
   lại. TaPERA cho thấy phân rã có thể *làm giảm* ROUGE dù người chấm đánh giá tốt hơn.
2. **Baseline ở ≤10B** gần như luôn là CoT hoặc PoT một call (Orchestra, TableZoomer, CoQ).
   Không paper nào so với few-shot cộng chuẩn hoá đáp án, là đối chứng mạnh nhất của ta.
3. **Ngôn ngữ:** không tìm thấy hệ agent TQA nào đánh giá trên tiếng Việt, ngoài các công trình
   của chính nhóm. MACT, H-STAR, TableMaster chỉ tiếng Anh; CoQ tiếng Anh và tiếng Trung.
4. **Hai bản chạy lại trong repo:** CoAgt 32,36 EM và CoQ 57,86 EM, so với Qwen3-8B few-shot
   67,14 trong cùng bảng của `paper/jit-article.tex`. Chỉ là mô tả: backbone của lần chạy đầy đủ
   không ghi trong repo (chỉ thấy smoke run với gpt-4o-mini), và bản CoQ thiếu clause agent.

---

## 5. Danh sách không xác minh được hoặc chỉ xác minh một phần

- **CoAgt:** trang PeerJ trả 403 cho browser và WebFetch. Chỉ đọc PDF trong máy (trang 1–6 và
  9–14); phần ablation hoặc thảo luận ở trang 15–22 chưa đọc.
- **ReAcTable:** không lấy được phần kết quả của chính paper; các con số dùng ở trên lấy từ bảng
  của MACT, H-STAR, Orchestra và CoAgt.
- **MATA:** số call trung bình mỗi câu không trích được. Khảo sát 09-18 ghi 5,5–7, tôi chưa đọc
  lại.
- **Mixture-of-Minds:** không thấy link code hay checkpoint trong các trang đã đọc.
- **TableMaster:** URL code và số call không trích được. Số HiTab lấy *(theo khảo sát 09-18)*.
- **AutoPrep:** chỉ có hình thời gian và chi phí đô-la, không có số call.
- **MAPLE:** việc memory được xây trên tập test là *suy luận* từ Eq. 4 và Bảng 8, chưa xác nhận
  bằng code.
- **CoQ:** backbone của bảng IM-TQA/Open-WikiTable (Table 4) không nêu trong đoạn đã đọc.
- **PanelTR:** FEVEROUS mâu thuẫn giữa Bảng V (75,5) và Bảng VI (73,0).
- **Chain-of-Table:** paper ghi "Llama-2-17B-chat", một cỡ model không tồn tại. Không xác định
  được model thật.
- **PanelTR, số call:** paper không báo. Ước lượng của tôi là khoảng 25 call (5 persona × 3 bước
  cộng trình bày và thảo luận). Chưa kiểm.
- **Orchestra:** định nghĩa metric (EM chặt hay nới lỏng) không có trong các trang đã đọc.
- **Chỉ có metadata arXiv, không đọc toàn văn:** Binder, Dater, TabSQLify, Tree-of-Table, ALTER,
  TableRAG, SheetAgent, Plan-of-SQLs, Weaver, MAC-SQL, MAG-SQL, Table-r1 (SLM), Reasoning-Table,
  OpenTable-R1, TableMind (bản gốc), OHD, STR, TraceBack, TabTrim, Evolving-from-Lessons.
- **MoRSE (2608.09251):** abstract mô tả MAS tổng quát; chưa xác định có đánh giá TQA không.
  Không đưa vào.
- **Hệ TQA tiếng Việt hoặc đa ngữ có agent:** arXiv search không trả kết quả. Chỉ tìm được
  benchmark đa ngữ (MULTITAT 2502.17253, M3TQA 2508.16265, TableEval 2506.03949, đều chỉ metadata,
  không phải agent). ViPanelTR (MAPR 2026, cùng nhóm) và Son et al. (ICCCI 2025, một GPT-4o sinh
  code, không phải multi-agent) chỉ biết qua tài liệu trong repo (`docs/research/Khoi/`), không
  đọc lại.
- **DBLP và Semantic Scholar:** không truy cập được (bot check và 429), nên venue của các paper
  2026 chỉ dựa vào comment trên arXiv.
- **E5** (NAACL'24, bảng phân cấp, HiTab 77,3): chỉ biết qua khảo sát 09-18 và các bảng so sánh
  của H-STAR; chưa mở paper, chưa xác minh ID.
- **Agent ở VLSP 2025 NumQA / ViNumQA:** được nhắc trong `docs/research/Khoi/` (tốt nhất 84,0;
  Qwen3-8B 79,1). Tôi chưa tìm kiếm hay xác minh; đây có thể là hệ agent TQA tiếng Việt duy nhất
  ngoài công trình của nhóm.
