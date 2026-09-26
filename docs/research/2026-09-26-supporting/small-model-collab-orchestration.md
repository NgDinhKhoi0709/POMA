# Cộng tác đa tác tử với backbone nhỏ (≤10B), cộng tác dị thể và orchestration học được: khảo sát 2025 → 09/2026

Ngày: 2026-09-26. Báo cáo này bổ sung cho khảo sát 2026-09-18. Khảo sát đó đã kết luận hai điều: persona debate trên cùng một backbone không giúp ở cỡ 8B, và voting ≥ debate. Báo cáo này chỉ xét những gì **mới hoặc khác**: tác tử khác nhau về *mô hình*, *công cụ* hoặc *góc nhìn*, và orchestration *học được* thay vì viết tay.

**Cách xác minh.** Mọi arXiv ID trong bảng đều đã được mở trên trang `arxiv.org/abs/<id>` trong tab trình duyệt riêng (tab-3), và tiêu đề đã được đối chiếu. Nội dung chi tiết được đọc bằng alphaXiv (`answer_pdf_queries` trên full text, hoặc `get_paper_content`, là báo cáo do AI tóm tắt). Cột "Nguồn đọc" trong bảng ghi rõ từng bài được đọc ở mức nào. Không trang nào bị từ chối, và tôi không đăng nhập hay gửi form nào.

**Có một phép đo thật trên dữ liệu POMA (§4.0).** Tôi đo tỉ lệ *tất cả mô hình cùng sai* (co-failure β) trên các file dự đoán đã có trong `outputs/`. Script chỉ đọc dữ liệu; tôi không sửa gì trong repo. Toàn văn script và đường dẫn các file dự đoán nằm ở Phụ lục A để tái lập.

---

## 1. Tóm tắt (10 dòng)

1. Đo trên dữ liệu POMA (EM raw, n=991, §4.0), mô hình dị thể **có** mở thêm dư địa oracle. Pool 4 prompt của Qwen3-8B có β=23,6%; thêm Gemma-3-4B và SEA-LION thì β giảm còn 19,3%, tức **+4,3 EM trần** so với chỉ dùng biến thể prompt. Riêng pipeline POMA đóng góp +3,4 EM trần theo cách tương tự. Ở pool cùng cỡ 3, dị thể (β 23,8%) nhỉnh hơn ba prompt Qwen (24,7–25,3%).
2. Nhưng dư địa đó **không thu được bằng vote**. Mọi pool không có POMA đều vote thấp hơn Qwen few-shot raw (67,41), thua 0,6 đến 3,9 EM. Có POMA thì vote đạt 67,81 (5 hệ) và 69,12 (7 hệ), đều dưới ngưỡng phân giải, và vẫn thua một lần gọi few-shot có finalizer GSA (69,93). Điều này khớp với phát hiện "naive diversity is a liability" của 2606.27288. Muốn thu dư địa thì cần một *bộ chọn học được*.
3. Self-MoA (2502.00674) cho thấy chất lượng quan trọng hơn đa dạng. Lấy mẫu mô hình mạnh nhất nhiều lần thắng trộn nhiều mô hình ở cỡ 7–9B. Mixed chỉ thắng khi các thành viên *ngang tài*: thêm Llama-3.1-8B được +2%, thêm một mô hình yếu hơn 5% thì mất −1,5%.
4. Co-failure β, chứ không phải tương quan cặp ρ, mới là thứ chặn trần. Định dạng câu trả lời tự do làm β tăng mạnh: GPQA từ ≈0 lên 12,7% khi bỏ lựa chọn (2606.27288). Open-ViTabQA là QA tự do, nên nằm ở chế độ "ceiling-bound".
5. Router học được mắc kẹt ở "routing plateau": router kNN ngang router huấn luyện, và cách oracle 10–30 điểm (2606.07587). Với 7,9k cặp train, kỳ vọng thực tế chỉ thu được một phần nhỏ của trần +9 đến +13 EM.
6. Trên bảng, lợi ích có bằng chứng ở ≤10B đến từ **đa dạng công cụ/góc nhìn cộng với một bộ chọn học được**, không đến từ persona. MATA với qwen2.5-7b và bộ chọn DeBERTa 435M đạt 0,951 so với MixSC 0,597. MACT (Qwen-7B+coder-7B) đạt 58,4 trên WTQ. Tuy vậy, không bài nào so sánh cùng số lần gọi LLM.
7. Mixture-of-Minds (Meta, bảng) trên Qwen3-8B: lợi ích chủ yếu đến từ *workflow có code*, không đến từ MARL. Trên FinQA, workflow chưa huấn luyện được 54,63, sau MARL được 55,25 (+0,6), còn Direct GRPO chỉ 44,57.
8. Các bài có đối chứng cùng ngân sách đều theo hướng "giảm phát". Với 7B đóng băng và cùng số call, planner/critic tiến hoá về prompt rỗng (2609.04217). Với token khớp nhau, MAS trung bình −0,3% và âm khi baseline đơn tác tử >45% (2512.08296). POMA đang ở mức ~70%.
9. Orchestration học được (Puppeteer, MasRouter, MaAS, AFlow, FlowReasoner, MAS-GPT, OptiMAS) hầu như chỉ thử với executor ≥32B hoặc API. Cải thiện so với self-consistency co lại còn +0,6 đến +1,2 khi executor mạnh (MAS-GPT). Nhóm này không đáng làm cho một đề tài 8B.
10. RL đa tác tử ở ≤8B là có thật: MALT (Llama-3.1-8B, 2–6k cặp mỗi vai, LoRA) đạt MATH 57,25 so với SC@3 52,50; HACRL dùng rollout của mô hình dị thể. Nhưng các baseline không khớp số call, và chi phí GPU vượt Kaggle nếu RL online.

---

## 2. Bảng tổng hợp

Chú thích: "≤10B?" nghĩa là có kết quả với backbone ≤10B hay không. "Matched?" nghĩa là có baseline đơn tác tử hoặc self-consistency (SC) cùng số call hoặc token hay không. Mức đọc: **F** = full text qua alphaXiv PDF; **R** = báo cáo AI của alphaXiv; **A** = chỉ abstract trên arXiv.

| # | Paper (arXiv) | Nhóm | Nguồn đa dạng | ≤10B? | Matched? | Task | Chi phí train | Code | Đọc | Verdict ViTabQA |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Mixture-of-Agents (2406.04692) | 1 | khác model | Không (≥70B) | Không (so với GPT-4o theo $) | AlpacaEval, MT-Bench, MATH | 0 | Có | F | Fusion sinh lời diễn giải lại, rủi ro EM; không làm |
| 2 | Rethinking MoA / Self-MoA (2502.00674) | 1 | cùng model lấy mẫu vs khác model | **Có** (Qwen2-7B, Llama-3.1-8B, Gemma-2-9B) | **Có** (cùng số forward pass; Self-USC) | AlpacaEval, MMLU, CRUX, MATH | 0 | Có | F | Ủng hộ "chất lượng > đa dạng"; ở temp 0 phải đổi prompt |
| 3 | LLM-Blender (2306.02561) | 1 | khác model (11 LLM ~7–13B) | Có | Không | MixInstruct | PairRanker 400M, 1×RTX8000 2 ngày | Có | F | PairRanker (chọn, không fuse) đáng thử; GenFuser thì không |
| 4 | Correlated Errors in LLMs (2506.07962, ICML'25) | 1 | 350+ model | Có (nhiều 7–9B) | n/a | MMLU (HF, HELM) | 0 | Có | F | Nền lý thuyết: cùng họ/cùng nhà → sai giống nhau |
| 5 | Co-failure ceiling (2606.27288) | 1/4 | 67 model | Có trong pool | n/a (chứng chỉ $0) | MATH, code, GPQA | 0 | Có (`beta_certificate.py`) | F | **Đã áp dụng ở §4.0**; phép đo đầu tiên nên làm |
| 6 | Router-R1 (2506.09033) | 1/2 | khác model (7B–70B pool) | Router 3B | Không | NQ, HotpotQA… (EM) | PPO, 14k mẫu, A6000 | Có | F | Router 3B học gọi model khác; pool của ta quá nhỏ |
| 7 | RouteLLM (2406.18665, ICLR'25) | 1 | mạnh/yếu | Có (Llama-3.1-8B là "weak") | Không (tối ưu chi phí) | MT-Bench, MMLU, GSM8K | 65k cặp Arena + augment | Có | F | Mục tiêu là tiết kiệm chi phí, không tăng EM |
| 8 | Routing Plateau (2606.07587) | 1 | 21 router | n/a | n/a | 5 benchmark routing | 30k→300k truy vấn | ? | F | kNN ≈ router huấn luyện; oracle gap 10–30 điểm |
| 9 | Puppeteer / Evolving Orchestration (2505.19591, NeurIPS'25) | 2 | khác model + tool + pattern | **Có** ("Mimas": 3–14B) | Không | GSM-Hard, MMLU-Pro, SRDD | RL, 8×A800, 2–6 giờ | Có | F | Ý tưởng hay nhưng cần nhiều agent/tool; không khớp bài toán |
| 10 | MasRouter (2502.11133) | 2 | khác model + vai + topology | Không (API, 70B) | Có SC nhưng không khớp $ | MMLU, GSM8K, MATH, HumanEval, MBPP | controller nhẹ, policy gradient | Có | F | Không có kết quả ≤10B |
| 11 | AFlow (2410.10762) | 2 | workflow tìm kiếm (MCTS) | Không | SC là operator | HotpotQA, DROP, code, math | optimizer Claude-3.5 | Có | R | Có thể "tìm prompt/workflow" trên dev; lợi ích <2 EM khó đo |
| 12 | MaAS (2502.04180) | 2 | supernet toán tử | Không (gpt-4o-mini) | Không | math, code, GAIA | $3,38 (MATH) | Có | R | Early-exit theo query là ý hay; phần còn lại thì không |
| 13 | FlowReasoner (2504.15257) | 2 | meta-agent sinh MAS theo query | Meta-agent 7B/14B | Không | code (BigCodeBench…) | distill R1 + GRPO | Có | R | Chỉ làm code; bảng thì không |
| 14 | MAS-GPT (2503.03686) | 2 | LLM sinh MAS | Generator 32B (có 7B/14B yếu hơn) | **Có SC** | MATH, GSM8K, MMLU, GPQA… | 11k cặp, 16×A100 | Có | F | Hơn SC chỉ +0,6/+1,2 khi executor mạnh |
| 15 | OptiMAS (2608.21918) | 2 | tiến hoá prompt/skill/topology | Không (GPT-5-nano, Qwen3.6-35B-A3B) | Không | WorkBench, GAIA, SWE | 1,4–3,2M token/bước | Có | F | Dành cho agent tool dài hạn; không hợp |
| 16 | MAPoRL (2502.18439) | 3 | cùng/khác model, debate | **Có** (Phi-3 3.4B, Qwen2.5-3B, Llama-3-8B) | Không (3 agent × 3 lượt vs 1) | GSM8K, ANLI | QLoRA; 12,8k mẫu | Có | F | RL cho debate; debate đã bị loại |
| 17 | MALT (2412.01928, COLM'25) | 3 | cùng model, 3 vai được huấn luyện riêng | **Có** (Llama-3.1-8B) | Một phần (debate cùng số call; SC@3 ít call hơn) | MATH, GSM8K, CSQA | 2–6k cặp/vai, LoRA SFT+DPO | Có (project page) | F | **Khả thi nhất nếu fine-tune**; phải so với SFT đơn trên cùng dữ liệu |
| 18 | ReMA (2503.09501) | 3 | meta-thinker + reasoner | **Có** (Llama-3-8B, Qwen2.5-7B) | Có SARL, không khớp call | Math, LLM-as-judge | GRPO | Có | R | Chủ yếu là math OOD; bảng thì chưa thấy |
| 19 | Stronger-MAS / AT-GRPO (2510.11062) | 3 | vai khác, policy chung hoặc riêng | **Có** (Qwen3 1.7B/8B) | Có SA+GRPO, không khớp call | planning, code, math | GRPO, cluster | Có (PettingLLMs) | R | Lợi lớn ở planning dài; math/code chỉ +3,9 đến +17,9 |
| 20 | HACRL / HACPO (2603.02604) | 3 | **khác model** (chia sẻ rollout lúc train) | **Có** (Qwen3 1.7/4/8B, Llama3.2 1/3B) | **Có** (GSPO×2 cùng số rollout) | Math | 8 GPU, ~5,5 giờ (1.7B+4B), MATH 7.5k | ? | F | Ý tưởng đáng giá (suy luận vẫn đơn); GPU vượt Kaggle |
| 21 | RL Tango (2505.15034) | 3/5 | generator + verifier (khác backbone) | **Có** (7B/8B) | Có GRPO đơn | Math, OOD (có TableBench) | 113k SFT + 455k RL | ? | R | Chi phí dữ liệu quá lớn |
| 22 | Mixture-of-Minds (2510.20176) | 3/5 | plan/code/answer + **tool** | **Có** (Qwen3-8B, Llama-3.1-8B) | **Có** Direct GRPO cùng dữ liệu; SC 8× | TableBench, FinQA | 4,9k QA, ~100 bước GRPO | ? | F | **Liên quan trực tiếp**; lợi ích đến từ code-tool, không từ MARL |
| 23 | MAST: Why Do MAS Fail? (2503.13657, NeurIPS'25 D&B) | 4 | 7 framework | Có CodeLlama-7B | n/a | code, math, agent | 0 | Có | F | Checklist lỗi; 23,5% lỗi thuộc verification |
| 24 | Towards a Science of Scaling Agent Systems (2512.08296) | 4 | 5 kiến trúc × 3 họ model | Không | **Có** (4,8k token/trial) | 6 benchmark agentic | 0 | Có (data) | F | Saturation ở 45% → POMA 70% dự báo MAS âm |
| 25 | Small LMs are the Future of Agentic AI (2506.02153) | 4 | position paper | n/a | n/a | — | — | — | R | Luận điểm "SLM chuyên hoá + dị thể"; không có thí nghiệm |
| 26 | At Equal Inference Cost… (2609.04217) | 4 | P→E→C cùng 7B đóng băng | **Có** (Qwen2.5-7B, temp 0) | **Có** (iso-call) | ALFWorld, WebShop | 0 (prompt evolution) | ? | F | Bằng chứng mạnh nhất cho "cấu trúc không trả đủ phí" ở 7B |
| 27 | Table-Critic (2502.11799) | 5 | Judge/Critic/Refiner/Curator cùng model | Không (≥70B, gpt-4o-mini) | Tuyên bố hơn majority vote ở "chi phí tương đương" | WikiTQ, TabFact | 0 | Có | F | Tỉ lệ làm hỏng câu đúng thấp (0,7%) nhưng chưa thử ≤10B |
| 28 | MACT (2412.20145) | 5 | **planner khác model với coder** + tool | **Có** (Qwen-7B + DeepSeek-coder-7B) | Có SC(Qw+CL) nhưng 5–65 call vs 10 | WTQ, TAT, CRT, SciTab | 0 | Có | F | Hơn SC dị thể +6 EM ở 72B; ≤10B không có SC |
| 29 | MATA (2602.09642) | 5 | **CoT/PoT/SQL** + selector nhỏ | **Có** (3–8B, 5 model) | Không trực tiếp (MixSC 10 call) | Penguins, TableBench | CC: DeBERTa-v3-large 435M, 57,9k cặp | Có | F | **Mẫu gần nhất cần thử**: trình chọn nhỏ > LLM judge |
| 30 | Generative Verifiers / GenRM (2408.15240, ICLR'25) | 5 | verifier sinh (CoT + vote) | **Có** (Gemma 2B/7B, Gemma2-9B) | **Có** (SC cùng N) | GSM8K, MATH, thuật toán | SFT verifier; rationale tổng hợp | data | F | Verifier nhỏ tốt hơn SC ở cùng N; cần rationale cho bảng |

Các ID đã mở trên arXiv nhưng chỉ đọc đến mức abstract (mức A) được liệt kê ở §3.6.

---

## 3. Method cards

### 3.1 Cộng tác dị thể, Mixture-of-Agents, router/cascade

**[1] Mixture-of-Agents Enhances LLM Capabilities**: Wang, Wang, Athiwaratkun, Zhang, Zou (Together AI), 2024. arXiv 2406.04692, đã mở https://arxiv.org/abs/2406.04692.
- *Cơ chế*: các lớp proposer → aggregator. Mỗi agent ở lớp i+1 đọc toàn bộ output của lớp i qua prompt "Aggregate-and-Synthesize". Luồng điều khiển cố định bằng code (3 lớp × 6 model).
- *Backbone*: Qwen1.5-110B/72B, WizardLM-8x22B, Llama-3-70B, Mixtral-8x22B, dbrx. **Không có kết quả ≤10B.**
- *Matched?* Không so với SC cùng số call. Chỉ có phân tích chi phí $ và TFLOPs so với GPT-4. Thí nghiệm single-proposer (6 mẫu, T=0,7, từ cùng một model) được 56,7, còn multi-proposer được 61,3 (AlpacaEval LC, n=6).
- *Đa dạng*: khác model.
- *Task/gain*: AlpacaEval 2.0 LC 65,1% so với GPT-4o 57,5%. Trên MATH (Bảng 8), aggregator Qwen-72B đi từ 0,428 lên 0,552 qua 3 lớp. Một LLM-ranker (chỉ *chọn* một output) thua fusion trên AlpacaEval.
- *Train*: 0. *Code*: https://github.com/togethercomputer/moa.
- *Verdict*: đo bằng GPT-4 judge trên văn bản mở; fusion viết lại câu trả lời, nên nguy hiểm với EM khi 43% đáp án là một ô nguyên văn. Không nên làm.

**[2] Rethinking Mixture-of-Agents: Is Mixing Different LLMs Beneficial? (Self-MoA)**: Li, Lin, Xia, Jin (Princeton), 2025. arXiv 2502.00674, đã mở.
- *Cơ chế*: Self-MoA lấy mẫu N output từ **một** model tốt nhất rồi dùng aggregator để tổng hợp. Self-MoA-Seq tổng hợp theo cửa sổ trượt. Luồng cố định.
- *≤10B*: có. Ba model chuyên biệt là Qwen2-7B-Instruct (i), Qwen2-Math-7B (m) và DeepSeek-Coder-V2-Lite (d, 16B MoE). Self-MoA dùng model tốt nhất cho từng task thắng **cả 13 cấu hình Mixed-MoA** (MMLU 69,01; CRUX 50,75; MATH 68,42 với aggregator i). Trên MMLU, với Llama-3.1-8B (l) và Qwen2-7B (i) ngang tài, "llllll" được 71,27, "iiilll" (mixed) được 70,73, "iiiiii" được 69,01. Với Gemma-2-9B-SimPO/WPO: Self-MoA tăng +2 đến +3 LC trên AlpacaEval.
- *Matched?* **Có.** Các cấu hình dùng cùng số forward pass. Bảng 12 (7 pass): Self-MoA 65,7 > Self-USC 60,2 > Mixed-MoA 59,1 > Mixed-USC 53,8 (AlpacaEval).
- *Phát hiện chính*: hồi quy trên hơn 200 cấu hình cho thấy hiệu năng MoA nhạy với *chất lượng* hơn *đa dạng* (α > β). Mixed chỉ thắng khi các thành viên ngang tài: trong Self-MoA-Seq, thêm Llama-3.1-8B được +2%, thêm DeepSeek-Coder-Lite (yếu hơn 5%) mất −1,5%.
- *Train*: 0. *Code*: có. *Tham số*: proposer T=0,7, aggregator T=0.
- *Verdict*: Qwen3-8B mạnh hơn Gemma-4B và SEA-LION 8B lần lượt khoảng 27 và 18 điểm EM trên dữ liệu của ta (§4.0). Theo bài này, *fusion hay vote* trộn mô hình sẽ hại, và §4.0 xác nhận vote dưới mức Qwen đơn. Tuy nhiên, §4.0 cũng cho thấy các mô hình yếu vẫn đúng ở những câu Qwen sai: trần giảm β thêm 4,3 điểm. Vì vậy dị thể chỉ có ích qua một bộ *chọn*. Ở temperature 0, đa dạng "trong model" phải đến từ biến thể prompt hoặc biến thể bảng, không từ sampling.

**[3] LLM-Blender**: Jiang, Ren, Lin (AI2/USC/ZJU), 06/2023. arXiv 2306.02561, đã mở.
- *Cơ chế*: PairRanker (DeBERTa-v3-large ~400M, cross-encoder cặp) xếp hạng N output, sau đó GenFuser (Flan-T5-XL 3B) trộn top-3. Luồng cố định.
- *≤10B*: pool gồm 11 LLM mở thời 2023 (Vicuna, OpenAssistant, Alpaca, MPT…), hầu hết 7–13B. Model tốt nhất chỉ đứng hạng 1 ở 21% câu, nên oracle khác model tốt nhất rất nhiều.
- *Matched?* Không (ensemble 11 call).
- *Kết quả*: GPT-Rank 3,01 (Blender) so với 3,20 (PairRanker) và 3,90 (OpenAssistant). PairRanker đơn đã hơn model tốt nhất.
- *Train*: PairRanker trên 100k MixInstruct, 1×RTX 8000, 2 ngày. *Code*: có.
- *Verdict*: phần *ranker/chọn* chuyển được sang bảng dưới dạng một cross-encoder tiếng Việt chọn giữa các ứng viên. Phần *fuser* không nên dùng vì dễ phá EM.

**[4] Correlated Errors in Large Language Models**: Kim, Garg, Peng, Garg (Cornell), ICML 2025. arXiv 2506.07962, đã mở.
- *Nội dung*: trên 349 model (HF leaderboard) và 71 model (HELM), tỉ lệ hai model chọn **cùng** đáp án sai khi cả hai đều sai là 0,423 (HF, ngẫu nhiên 0,127) và 0,60 (HELM, ngẫu nhiên 1/3). Cùng công ty +0,066; cùng kiến trúc +0,076. Model càng chính xác thì lỗi càng tương quan, kể cả khi khác nhà cung cấp.
- *Hệ quả*: LLM-as-judge thổi phồng điểm của model yếu hơn nó, nhất là model cùng họ.
- *Code*: https://github.com/nikhgarg/llm_correlated_errors_public.
- *Verdict*: đây là cảnh báo cho mọi "judge" hoặc "critic" trong POMA. Trên dữ liệu của ta (EM raw), Qwen và SEA-LION chọn cùng một đáp án sai ở 35,5% số câu mà cả hai cùng sai (92/259); Qwen và Gemma là 27,2% (§4.0).

**[5] When Does Combining Language Models Help? A Co-Failure Ceiling on Routing, Voting, and MoA Across 67 Frontier Models**: Josef Chen (KAIKAKU), 06/2026. arXiv 2606.27288, đã mở.
- *Luận điểm*: mọi chính sách *chọn* một đáp án của thành viên (router, vote, cascade, và cả self-consistency) có accuracy ≤ 1 − β, với β = P(mọi model cùng sai). Lợi ích tối đa so với model đơn tốt nhất bằng P(best sai) − β. Tương quan cặp ρ **không** xác định được β. Chặn dưới Clopper–Pearson của β cho một "chứng chỉ $0" trước khi huấn luyện router.
- *Số liệu*: MATH-500 β=0,052 (67 model), trong khi single-factor copula dự báo 0,021–0,023 (thấp hơn khoảng 2,5 lần). Code thi đấu β=0,079. GPQA khi bỏ lựa chọn: β từ ≈0 lên **0,127**. Vote ngây thơ trên 455 bộ ba có lợi ích trung bình **âm** (−0,10 ở tập khó, −0,02 ở tập bão hoà). Router học được thu gần như 0 phần lợi ích oracle. Cùng chất lượng, ensemble đa dạng (ρ thấp) thắng Self-MoA (ρ cao).
- *Pool*: 67 model, gồm cả model mở nhỏ (Gemma, Phi). Không tách riêng kết quả ≤10B.
- *Code*: có, phát hành ma trận kết quả và `beta_certificate.py`.
- *Verdict*: **áp dụng ngay** (§4.0 đã làm). Lưu ý: fusion kiểu MoA *có thể* vượt 1−β vì sinh ra đáp án mới, nhưng với đáp án là ô bảng nguyên văn thì điều này hiếm.

**[6] Router-R1**: Zhang, Feng, You (UIUC), 2025. arXiv 2506.09033, đã mở.
- *Cơ chế*: một policy LLM 3B (Qwen2.5-3B hoặc Llama-3.2-3B) xen kẽ `<think>` và `<search>` (gọi một model trong pool, tối đa 4 bước), rồi tổng hợp. Luồng điều khiển do **policy học bằng PPO** quyết định. Reward gồm format, EM, và chi phí.
- *Pool*: Qwen2.5-7B, Llama-3.1-8B/70B, Mistral-7B, Mixtral-8x22B, Gemma-2-27B.
- *Kết quả (EM, 7 QA)*: Router-R1-Qwen 0,416 trung bình, so với "Largest LLM" 0,338 và RouterDC 0,314. Mỗi câu gọi trung bình 1,01–1,36 lần. Qwen2.5-7B đơn trên NQ chỉ 0,138 EM.
- *Matched?* Không có SC cùng call. Router cũng tự trả lời được.
- *Train*: 14k mẫu (NQ + HotpotQA), 225 bước PPO, A6000. *Code*: có.
- *Verdict*: lợi ích đến từ việc *gọi model lớn hơn*. Pool của ta không có model nào mạnh hơn Qwen3-8B, nên không có "chuyên gia" để route tới.

**[7] RouteLLM**: Ong et al. (Berkeley/Anyscale), ICLR 2025. arXiv 2406.18665, đã mở.
- *Cơ chế*: router nhị phân (similarity-weighted BT, matrix factorization, BERT, hoặc Llama-3-8B classifier) quyết định giữa model mạnh và model yếu.
- *Kết quả*: tiết kiệm tới 3,66 lần chi phí ở 95% chất lượng GPT-4 (MT-Bench). Trên MMLU, router huấn luyện chỉ bằng Arena ≈ ngẫu nhiên; thêm khoảng 1.500 mẫu có nhãn vàng in-domain thì APGR +20%. Router tổng quát hoá được sang cặp Llama-3.1-70B/8B mà không cần huấn luyện lại.
- *Train*: 65k cặp Arena, cộng 120k nhãn GPT-4 judge (~$700). *Code*: có.
- *Verdict*: mục tiêu là *giảm chi phí*, không phải tăng EM. Bài này chỉ hữu ích nếu muốn cascade Gemma → Qwen để tiết kiệm.

**[8] The Routing Plateau**: Lu et al. (Rice/Amazon), 05/2026. arXiv 2606.07587, đã mở.
- *Phát hiện*: 21 router trên 5 benchmark. Top-5 chỉ cách nhau 0,22 điểm. kNN nằm trong top-2 ở mọi benchmark. Router tốt nhất vẫn cách oracle 10–30 điểm. Nguyên nhân là "correctness-prediction bottleneck": router học được xu hướng năng lực *trung bình* của model, không học được tín hiệu theo từng câu.
- *Phá plateau*: tăng dữ liệu từ 30k lên 300k, encoder từ ModernBERT-base lên large, và fine-tune end-to-end. Tổng cộng chỉ được +1,24 điểm, tối đa +2,13, và thu hẹp được khoảng 8,5–14,6% khoảng cách tới oracle.
- *Verdict*: với 7,9k câu train, kỳ vọng hợp lý cho một router Qwen/SEA-LION là một kNN trên embedding câu hỏi và bảng. Mức tăng khó vượt ngưỡng 2 EM.

### 3.2 Orchestration học được / tự động thiết kế MAS

**[9] Multi-Agent Collaboration via Evolving Orchestration ("Puppeteer")**: Dang, Qian et al. (Tsinghua/SJTU), NeurIPS 2025. arXiv 2505.19591, đã mở.
- *Cơ chế*: một orchestrator trung tâm (policy khởi tạo từ một biến thể Llama-3.1) chọn *agent kế tiếp* ở mỗi bước. Mỗi agent là một tổ hợp (model, reasoning pattern, tool). Policy được huấn luyện bằng REINFORCE, với reward là accuracy trừ λ·token. Output được gộp bằng majority vote.
- *≤10B*: có. Không gian "Mimas" gồm Qwen-2.5-7B/14B, Llama-3.1-8B, Llama-3.2-3B, Mistral-7B, Mistral-Nemo-12B. Puppeteer (dị thể, evolved) đạt trung bình 0,6324, Puppeteer-Mono (Llama-3.1-8B) đạt 0,6147, còn Llama-3.1-8B đơn đạt 0,4214. Tuy nhiên, Self-Refine hay AFlow chạy trên *Llama-3.1-8B* chỉ được 0,47–0,54.
- *Matched?* Không có SC cùng số token. Token giảm dần trong quá trình huấn luyện nhưng không được khớp với baseline.
- *Train*: 8×A800, 2–6 giờ, online. *Code*: https://github.com/OpenBMB/ChatDev/tree/puppeteer.
- *Verdict*: cấu trúc tìm được là "chu trình gọn". Với bài toán một bước suy luận (91% câu chỉ có một nhãn), không gian hành động gần như suy biến.

**[10] MasRouter**: Yue, Zhang et al., 2025. arXiv 2502.11133, đã mở.
- *Cơ chế*: một controller cascade (VAE latent + MiniLM) chọn chế độ cộng tác (CoT, SC, debate, chain…), số agent, vai (26 vai) và LLM cho từng agent. Huấn luyện bằng policy gradient với utility − λ·cost.
- *Backbone*: gpt-4o-mini, claude-3.5-haiku, gemini-1.5-flash, llama-3.1-70b. **Không có ≤10B.**
- *Kết quả*: trung bình 85,93 so với SC(ComplexCoT, gpt-4o-mini) 81,43 và AFlow 84,20. Trên MBPP được 84,0 với $1,04, so với SC 75,6 với $0,49.
- *Verdict*: ngoài phạm vi. Pool của ta chỉ có 3 model mở với chất lượng lệch nhau lớn.

**[11] AFlow**: Zhang, Xiang et al. (DeepWisdom), 10/2024 (v4 04/2025). arXiv 2410.10762, đã mở. Đọc ở mức R.
- *Cơ chế*: MCTS trên workflow biểu diễn bằng code, với các operator Ensemble (SC), Review & Revise, Programmer… Optimizer là Claude-3.5-Sonnet. Validation chiếm 20% dữ liệu, mỗi workflow chạy 5 lần.
- *Backbone executor*: gpt-4o-mini, DeepSeek-V2.5… Không có ≤10B.
- *Kết quả*: +5,7% so với workflow viết tay (có HotpotQA, DROP dùng F1). Nếu bỏ operator định sẵn, AFlow *tự phát minh* ensemble.
- *Verdict*: về thực chất đây là "tìm prompt/workflow trên dev". Với ViTabQA, chỉ đáng dùng như một công cụ tìm prompt, và cần một held-out đủ lớn vì gain <2 EM không đo được.

**[12] MaAS (Agentic Supernet)**: Zhang et al., 02/2025. arXiv 2502.04180, đã mở. Đọc ở mức R.
- *Cơ chế*: một phân phối các kiến trúc (supernet) gồm các operator (CoT, SC, Debate, Self-Refine, ReAct, **Early-exit**…). Controller kiểu MoE (MiniLM) lấy mẫu kiến trúc theo từng query. Toán tử được cập nhật bằng "textual gradient".
- *Backbone*: gpt-4o-mini; chuyển được sang Qwen-2.5-72B và Llama-3.1-70B. Không có ≤10B.
- *Chi phí*: train $3,38 trên MATH, so với AFlow $22,5.
- *Verdict*: ý **early-exit theo độ khó** đáng giữ: câu dễ chỉ cần 1 call. Phần còn lại không phù hợp.

**[13] FlowReasoner**: Gao et al. (Sea AI Lab), 2025. arXiv 2504.15257, đã mở. Đọc ở mức R.
- *Cơ chế*: meta-agent DeepSeek-R1-Distill-Qwen-7B/14B, được distill từ R1 rồi GRPO, sinh *một MAS cho mỗi query* dựa trên phản hồi thực thi (test case).
- *Kết quả*: 14B đạt 81,89% trên 3 benchmark code, cao hơn MaAS 5 điểm. Worker là o1-mini.
- *Verdict*: cần tín hiệu thực thi (unit test). QA bảng không có tín hiệu tương đương lúc suy luận, nên không áp dụng được.

**[14] MAS-GPT**: Ye, Tang et al. (SJTU/Shanghai AI Lab), 2025. arXiv 2503.03686, đã mở.
- *Cơ chế*: SFT **Qwen2.5-Coder-32B** trên khoảng 11k cặp (query → MAS dạng code), sau đó sinh MAS bằng *một* lần suy luận. Executor là Llama-3-70B, Qwen2.5-72B hoặc GPT-4o-mini.
- *≤10B*: có biến thể generator 7B/14B nhưng yếu hơn rõ (Fig. 5c). Executor luôn ≥ gpt-4o-mini.
- *Matched?* **Có SC.** Với Llama-3-70B: MAS-GPT 65,47, SC 61,58, đơn 59,83. Với Qwen2.5-72B: 74,46 so với SC 73,88 (+0,6). Với GPT-4o-mini: 70,50 so với SC 69,29 (+1,2).
- *Train*: 16×A100, 3 epoch. *Code*: https://github.com/rui-ye/MAS-GPT.
- *Verdict*: khoảng cách với SC co lại khi executor mạnh. Không đáng làm.

**[15] OptiMAS**: Cheng, Liu et al. (HKU/Huawei), 08/2026. arXiv 2608.21918, đã mở.
- *Cơ chế*: optimizer tác tử (Gemini-3-Flash) tiến hoá prompt, skill, topology và tool bằng textual gradient cùng bộ nhớ giả thuyết dài hạn.
- *Backbone*: GPT-5-Nano, Qwen3.6-35B-A3B, Gemini-3-Flash. Không có ≤10B dense. Tác giả nêu rõ model yếu "may struggle".
- *Chi phí*: 1,4–3,2M token mỗi bước tối ưu.
- *Verdict*: dành cho agent dùng tool trong thời gian dài; không phù hợp.

### 3.3 Multi-agent huấn luyện bằng RL

**[16] MAPoRL**: Park, Han et al. (MIT/Stanford/Amazon), 2025. arXiv 2502.18439, đã mở.
- *Cơ chế*: debate 2–3 agent. Một verifier (cùng họ model) chấm câu trả lời và thưởng cho hành vi "sửa đúng" hoặc "thuyết phục đúng". Mỗi agent được huấn luyện bằng PPO độc lập (MARL).
- *≤10B*: Phi-3-mini (3,4B), Qwen2.5-3B, Llama-3-8B, QLoRA. GSM8K: off-the-shelf 0,677 → 0,689 → 0,639 qua các lượt; MAPoRL 0,677 → 0,797 → 0,809. **Single-agent RL với cùng verifier chỉ đạt 0,732**, nhưng đó là 1 call so với 3 agent × 3 lượt cộng vote, tức *không khớp ngân sách*. Có thử cặp dị thể (Phi-3 + Qwen2.5-3B, Phi-3 + Llama-3-8B), nhưng kết quả chỉ ở dạng hình.
- *Phát hiện phụ*: SFT trên top 10% quỹ đạo debate tốt còn **giảm** accuracy (−0,11). Verifier khác họ với generator làm tín hiệu reward kém đi và generator "trôi" về phong cách của verifier.
- *Train*: GSM8K 7,5k (cho verifier) + TinyGSM 12,8k. *Code*: có.
- *Verdict*: vẫn là debate, hướng đã bị loại. Điểm đáng nhớ: SFT trên hội thoại tốt không dạy được cộng tác.

**[17] MALT: Multi-Agent LLM Training**: Motwani et al. (Oxford), COLM 2025. arXiv 2412.01928, đã mở.
- *Cơ chế*: Generator → Verifier → Refiner, cùng base Llama-3.1-8B nhưng mỗi vai có một LoRA riêng. Dữ liệu được tạo từ cây mẫu n=3 (27 quỹ đạo mỗi câu). Credit được gán bằng value iteration từ đáp án cuối, rồi SFT + DPO cho từng vai. Lúc suy luận: 3 lượt tuần tự × MV@3.
- *≤10B*: Llama-3.1-8B. MATH / CSQA / GSM8K: đơn 49,50 / 74,50 / 84,25; SC@3 52,50 / 75,75 / 86,75; MA không huấn luyện + MV 53,50 / 79,00 / 87,00; **MALT 57,25 / 81,50 / 90,50**. Bỏ verifier (G+R) còn 54,75 / 76,25 / 84,75.
- *Matched?* Một phần. Debate 3×3 cùng ngân sách suy luận; STaR (SFT đơn trên dữ liệu dương) cùng ngân sách huấn luyện. SC@3 dùng ít call hơn MALT (9 call).
- *Train*: 2k–6k cặp nhãn mỗi vai mỗi benchmark, từ khoảng 7,5k câu train. Quy mô này **tương đương 7,9k cặp của ViTabQA**. LoRA, T=0,3.
- *Verdict*: **khả thi nhất nếu có fine-tune**. Đáp án bảng kiểm được bằng EM nên dán nhãn cây được. Nhưng phải so với (a) SFT/DPO *một* model trên cùng dữ liệu và (b) SC@9 prompt-variant.

**[18] ReMA**: Wan, Li et al. (SJTU/UCL/UBC), 2025. arXiv 2503.09501, đã mở. Đọc ở mức R.
- *Cơ chế*: meta-thinking agent (lập kế hoạch/giám sát) và reasoning agent (thực thi), huấn luyện luân phiên bằng GRPO. Bản multi-turn chia sẻ tham số và dùng turn-level ratio.
- *≤10B*: Llama-3-8B, Llama-3.1-8B, Qwen2.5-7B. So với SARL (single-agent RL), gain lớn nhất ở OOD (AMC23 +20% với Llama3-8B). Model 1B hội tụ về hành động "EMPTY", tức không học được meta-thinking.
- *Verdict*: tách "kế hoạch" khỏi "trả lời" không có lợi rõ khi 91% câu chỉ có một loại suy luận.

**[19] Stronger-MAS (AT-GRPO)**: Zhao et al. (UCSD/Intel), 2025. arXiv 2510.11062, đã mở. Đọc ở mức R.
- *Cơ chế*: GRPO nhóm theo (agent, lượt) với lấy mẫu dạng cây, reward trộn team và local, policy chung hoặc riêng theo vai.
- *≤10B*: Qwen3-1.7B/8B. Planning/game tăng từ 14–47% (SA+GRPO) lên 96–99,5%; code +3,9 đến +7,6; math +9,0 đến +17,9. Áp GRPO thẳng vào MAS làm *giảm* (CodeContests 17,6 → 10,3).
- *Verdict*: lợi lớn ở bài toán nhiều bước có trạng thái; QA bảng một bước không phải loại đó.

**[20] Heterogeneous Agent Collaborative RL (HACRL/HACPO)**: Zhang, Huang et al. (Beihang/ByteDance/Tsinghua/PKU/Apple), 03/2026. arXiv 2603.02604, đã mở.
- *Cơ chế*: nhiều model **khác nhau** cùng giải một prompt, *chia sẻ rollout đã kiểm chứng* khi huấn luyện, và **suy luận độc lập**. Bốn cơ chế đi kèm: advantage theo năng lực, hệ số chênh lệch năng lực, importance sampling mũ, và clipping theo bước.
- *≤10B*: Qwen3-1.7B/4B/8B-Base, Llama3.2-1B/3B. Trung bình 7 benchmark toán: Qwen3-4B 0,412 → HACPO 0,601 (GSPO×2: 0,575); Llama3.2-3B 0,289 → 0,390 (GSPO×2: 0,334); Qwen3-8B-Base (cặp với 4B) 0,630 so với GSPO×2 0,595. Qua 5 seed, 1.7B được 65,5 ± 0,7 so với 62,4 ± 0,3.
- *Matched?* **Có**: baseline GSPO×2 cùng tổng số rollout.
- *Train*: MATH train (7,5k), 1 epoch, 8 GPU; cặp 1.7B+4B mất 5 giờ 31 phút.
- *Verdict*: ý tưởng *đúng hướng* cho "dị thể không tốn call lúc suy luận". Nhưng phải có trọng số cả hai model (Gemma chỉ có qua API; SEA-LION thì chạy local được) và cần 8 GPU. Kaggle 2×T4 không đủ cho RL online cỡ 8B.

**[21] RL Tango**: Zha et al. (MIT), 05/2025 (NeurIPS 2025 theo báo cáo alphaXiv, chưa kiểm trên PDF). arXiv 2505.15034, đã mở. Đọc ở mức R.
- *Cơ chế*: generator (Qwen2.5-Math-7B) và verifier *sinh, cấp bước* (Qwen2.5-7B) được huấn luyện RL xen kẽ. Verifier chỉ cần nhãn đúng/sai ở cấp output.
- *Kết quả*: +25,5% tương đối trên math, +7,3% trên OOD (có TableBench). Hiệu quả huấn luyện tăng 3,3 lần so với GRPO.
- *Train*: 113k SFT + 455k câu RL, **quá lớn** so với 7,9k.
- *Verdict*: chỉ lấy ý "verifier sinh học từ nhãn cuối"; không tái lập được.

**[22] Mixture-of-Minds**: Zhou et al. (Meta), 10/2025. arXiv 2510.20176, đã mở. Bài đã được nêu ở khảo sát 09-18; ở đây bổ sung góc MARL.
- *Cơ chế*: planning → coding (pandas, thực thi) → answering, cùng một model. Dữ liệu vàng trung gian lấy từ MCTS rollout. Mỗi agent được GRPO tuần tự với reward BLEU (plan), exec/op-F1/output (code) và EM (answer).
- *≤10B*: Qwen3-8B TableBench: direct 41,98; SC 8× của direct 41,94 (**SC không giúp**); workflow chưa huấn luyện 47,38; sau huấn luyện 57,44; song song 8× được 60,35. Llama-3.1-8B: 15,42 → 14,58 (chưa huấn luyện) → 46,72.
- *Matched?* **Có một baseline quan trọng**: Direct GRPO cùng dữ liệu. Trên FinQA (OOD), Qwen3-8B: Direct GRPO 44,57, MoM *chưa huấn luyện* 54,63, MoM huấn luyện 55,25. Với Qwen3-8B, *công cụ code* đóng góp khoảng 10 điểm, còn MARL chỉ +0,6.
- *Train*: TableInstruct 4.897 QA, G=8, lr 1e-6, khoảng 100 bước mỗi agent. Số GPU không tìm thấy trong phần đã đọc.
- *Verdict*: **liên quan trực tiếp nhất**. Khác biệt với ViTabQA: TableBench nặng tính toán, còn ViTabQA có 43% câu là tra ô, nơi code ít lợi. Khảo sát 09-18 đã ghi lại rằng deterministic executor override bị loại; nên dùng code-path như một *ứng viên* chứ không phải lệnh ghi đè.

### 3.4 Phân tích thất bại và scaling của MAS

**[23] Why Do Multi-Agent LLM Systems Fail? (MAST)**: Cemri, Pan, Yang et al. (Berkeley), NeurIPS 2025 Datasets & Benchmarks. arXiv 2503.13657, đã mở.
- *Nội dung*: 1.642 trace từ 7 framework. 14 failure mode chia 3 nhóm: System design 44,2%, Inter-agent misalignment 32,3%, **Task verification 23,5%** (premature termination 6,2%, no/incomplete verification 8,2%, incorrect verification 9,1%). κ người = 0,88; LLM-judge (o1) κ = 0,77.
- *≤10B*: ChatDev/MetaGPT với CodeLlama-7B có nhiều lỗi hơn rõ so với Qwen2.5-Coder-32B.
- *Can thiệp*: chỉnh role spec được +9,4% (ChatDev); thêm bước kiểm tra mục tiêu cấp cao được +15,6%. Tác giả kết luận "sửa lẻ" là không đủ.
- *Code/data*: https://github.com/multi-agent-systems-failure-taxonomy/MAST.
- *Verdict*: dùng làm checklist gán nhãn lỗi cho trace của POMA. Nhóm FC3 tương ứng đúng với các vai "verifier/finalizer".

**[24] Towards a Science of Scaling Agent Systems**: Kim et al. (Google Research/DeepMind/MIT), 12/2025, v3 04/2026. arXiv 2512.08296, đã mở.
- *Thiết kế*: 260 cấu hình, 5 kiến trúc (SAS; MAS Independent, Centralized, Decentralized, Hybrid), 3 họ model, 6 benchmark agentic. **Token khớp nhau (trung bình 4.800/trial)**, cùng tool, cùng prompt.
- *Kết quả*: MAS trung bình −0,3% (CI [−58,7%, +77,2%]). Finance +80,8% (Centralized), PlanCraft −39% đến −70%. **Capability saturation**: khi baseline đơn tác tử >~45%, thêm agent cho lợi ích âm (β = −0,236, p = 0,004). Khuếch đại lỗi: Independent ×17,2, Centralized ×4,4. Success/1k token: SAS 67,7, MAS 13,6–42,4.
- *≤10B*: không có (nhỏ nhất là GPT-5-nano). *Code/data*: per-instance results có công bố.
- *Verdict*: POMA đơn tác tử đã ~70% EM, nên theo quy luật này MAS thuần cấu trúc sẽ âm. Đây là khung lý giải cho kết quả 70,16 > 68,45 của POMA.

**[25] Small Language Models are the Future of Agentic AI**: Belcak et al. (NVIDIA Research/Georgia Tech), 06/2025 (v3 09/2026). arXiv 2506.02153, đã mở. Đọc ở mức R.
- *Nội dung*: position paper. SLM đủ mạnh, rẻ hơn 10–30 lần, dễ chuyên hoá; hệ tác tử nên dị thể (SLM làm phần lặp lại, LLM chỉ gọi khi cần). Có thuật toán 6 bước chuyển từ LLM sang SLM (log call → cluster → fine-tune).
- *Lưu ý*: không có thí nghiệm có đối chứng. NVIDIA có lợi ích thương mại trong kết luận này.
- *Verdict*: củng cố luận điểm "chuyên hoá một model nhỏ" hơn là "thêm agent".

**[26] At Equal Inference Cost, Multi-Agent Structure Does Not Beat a Single Frozen Agent**: Dylan, Brennan et al. (Trinity College Dublin/UCD/DCU theo trang 1), 06/2026. arXiv 2609.04217, đã mở.
- *Thiết kế*: Planner→Executor→Critic trên **Qwen2.5-7B đóng băng, temperature 0**. Tiến hoá prompt theo từng vai (GEPA) với **tổng số call LLM cố định** (iso-call).
- *Kết quả*: ALFWorld: tiến hoá executor đơn +0,097 (p = 0,021); team 0,769 so với đơn 0,754 (Δ = +0,015, p = 0,80) mà tốn **1,8 lần** call. Planner và critic tiến hoá về prompt **rỗng**; ảnh hưởng tới hành động chỉ 0,14 và 0,41; critic restate-rate 0,00. WebShop: team −0,060. Ngay cả khi cho team thêm 2–3 lần compute, team chỉ *hoà* với đơn tác tử.
- *Hạn chế*: n = 134 và 80, một lượt greedy, không thử bảng. Danh tính tác giả không kiểm được (xem §5).
- *Verdict*: bằng chứng "iso-call" sạch nhất ở 7B, ở cùng chế độ temp 0 với POMA. Nó dự báo đúng kết quả POMA.

### 3.5 Verifier/selector với mô hình nhỏ và bảng

**[27] Table-Critic**: Yu, Chen, Wang (Soochow/ICT-CAS), 02/2025 (v3 05/2025; venue không kiểm). arXiv 2502.11799, đã mở.
- *Cơ chế*: Judge (xác định câu sai và loại lỗi) → Critic (tìm bước sai đầu tiên, dùng template) → Refiner (viết lại *từ bước sai*) → lặp tối đa 5 vòng. Curator nuôi một "cây template" lỗi tự tiến hoá. Chạy trên Chain-of-Table, temperature 0.
- *Backbone*: Qwen2.5-72B, Llama3.3-70B, GPT-4o-mini. **Không có ≤10B.**
- *Kết quả*: WikiTQ 77,2 so với Chain-of-Table 68,3 (Qwen-72B). Sửa đúng 9,6% câu sai, **chỉ làm hỏng 0,7%** câu đúng; Critic-CoT làm hỏng 4,9%. Chi phí bằng 1,87 lần Chain-of-Table. Tác giả tuyên bố hơn majority voting ở chi phí tương đương, nhưng không có con số cụ thể trong phần đã đọc.
- *Verdict*: số liệu "tỉ lệ làm hỏng" là tiêu chí nên đo cho mọi vai critic của POMA. Critic ở 8B có đạt 0,7% hay không thì chưa có bằng chứng.

**[28] MACT: Efficient Multi-Agent Collaboration with Tool Use for Online Planning in Complex TQA**: Zhou, Mesgar, Friedrich, Adel (Bosch/Augsburg), 12/2024 (v2 02/2025; venue không kiểm). arXiv 2412.20145, đã mở.
- *Cơ chế*: planning agent (ReAct, lấy k = 5 mẫu hành động, chọn bằng SC) và coding agent **khác model** (Python/calculator/Wikipedia), lặp tối đa 7 vòng. Có shortcut hiệu quả: nếu mọi dự đoán ước lượng trùng nhau thì trả lời ngay, tiết kiệm tới 33% vòng.
- *≤10B*: **MACT (Qwen-7B planner + DeepSeek-coder-7B)**: WTQ 58,4, TAT 61,9, CRT 46,4, SciTab 45,9. Llama-7B + coder-7B chỉ 38,1 trên WTQ. Planner mạnh quyết định phần lớn kết quả.
- *Matched?* Ở cỡ 72B+34B có baseline SC(Qw+CL): voting dị thể 5 + 5 call. MACT hơn khoảng 6 EM, nhưng dùng 5–65 call. Chọn hành động bằng LLM judge *thua* SC (WTQ 70,7 so với 72,6). **Một phần ba lỗi là do EM chấm quá chặt** (TAT: 66,2 EM so với 87,8 khi GPT-4 chấm ngữ nghĩa).
- *Verdict*: "coder khác planner" là dị thể có lý do (chuyên môn). Nhưng pool của ta không có coder chuyên biệt, và ViTabQA ít phép tính. Ghi nhận thêm: vấn đề EM chấm chặt cũng xuất hiện ở đây.

**[29] MATA: Multi-Agent Framework for Reliable and Flexible TQA**: Hyeon, Oh, Cho, Do (SNU), 02/2026 (v2 04/2026). arXiv 2602.09642, đã mở.
- *Cơ chế*: CoT, PoT và text2SQL là **ba góc nhìn khác nhau** (cùng backbone), có Debug agent cho code. Scheduler (MobileBERT 24,65M) chọn PoT hay SQL chạy trước; nếu khớp với CoT thì bỏ nhánh còn lại. **Confidence Checker** (DeBERTa-v3-large 435M) chấm từng ứng viên; chỉ khi không ứng viên nào đủ tự tin mới gọi Judge LLM. Format Matcher (Qwen2.5-0.5B) rút gọn đáp án.
- *≤10B*: EM với qwen2.5-7b: Penguins **0,951** (SynTQA 0,813, MixSC 0,597); TableBench **0,354** (SynTQA 0,302). Llama3.2-3b trên WikiTQ full test: 0,535 so với MixSC 0,232.
- *Ablation*: bỏ CC (để Judge LLM chọn mọi câu) làm trung bình giảm 0,881 → 0,774 (Penguins) và 0,451 → 0,399 (TableBench); riêng qwen2.5-7b: 0,951 → 0,854. **Bộ chọn nhỏ đã huấn luyện thắng LLM judge**, và CC cắt 60,6–95,8% số lần gọi judge. Phụ lục A: ở 3B/7B general, CoT > SQL > PoT; PoT chỉ mạnh ở ≥14B hoặc model code.
- *Matched?* Không có SC cùng số call. MixSC dùng 10 call, TabLaP 12, SynTQA 3; MATA biến thiên nhưng latency thấp hơn MixSC.
- *Train*: CC/Sch trên 57.888 cặp (bảng, câu hỏi) × 3 đường, sinh bằng các LLM 13–14B; 1×A100.
- *Code*: https://github.com/AIDASLab/MATA.
- *Verdict*: **mẫu gần nhất nên thử**: sinh ứng viên đa góc nhìn, rồi dùng một *bộ chọn nhỏ đã huấn luyện* (không phải LLM judge). Tiếng Việt cần encoder khác (PhoBERT hoặc mDeBERTa), huấn luyện trên dự đoán của train 7,9k.

**[30] Generative Verifiers (GenRM)**: Zhang, Hosseini et al. (Google DeepMind), ICLR 2025. arXiv 2408.15240, đã mở.
- *Cơ chế*: verifier SFT dự đoán token "Yes/No"; biến thể CoT sinh lý do rồi majority vote K = 32 lý do. Đây là best-of-N với generator cố định.
- *≤10B*: verifier Gemma-2B/7B và Gemma2-9B. GSM8K best-of-16 từ 73,0% lên **93,4%** (generator Gemini 1.0 Pro). Trên MATH, GenRM-CoT tiết kiệm mẫu 6,4 lần so với verifier phân biệt, **vượt SC** ở cùng N. Verifier fine-tune 2B–9B vượt LLM-as-judge dùng Gemini 1.0 Pro. Weighted SC kết hợp với GenRM hiệu quả gấp 2,5 lần.
- *Train*: lý do tổng hợp có "reference-guided" (cần đáp án đúng); nhiều lý do cho mỗi lời giải thì tốt hơn.
- *Verdict*: dạng verifier này đòi N ứng viên *đa dạng*. Ở temp 0 phải tạo đa dạng bằng prompt hoặc biến thể bảng. Mỗi câu tốn thêm N + K call, nên chỉ đáng nếu trần headroom đủ lớn (§4.0: +7 đến +13 EM tuỳ pool).

### 3.6 Đã mở trên arXiv nhưng chỉ đọc abstract (mức A), chưa có card đầy đủ

| arXiv | Tên | Ghi chú một dòng |
|---|---|---|
| 2305.05176 | FrugalGPT (Chen, Zaharia, Zou) | Cascade theo độ tin cậy; Router-R1 dùng làm baseline (0,318 so với 0,416 EM). |
| 2410.11782 | G-Designer (Zhang et al.) | GNN thiết kế topology giao tiếp; backbone API. |
| 2410.02506 | AgentPrune ("Cut the Crap") | Tỉa cạnh giao tiếp để giảm token; bổ trợ cho G-Designer. |
| 2408.08435 | ADAS (Hu, Lu, Clune) | Meta-agent tìm agent dạng code; OptiMAS báo ADAS thấp hơn đơn tác tử ở nhiều cấu hình. |
| 2505.14996 | MAS-ZERO (Ke, Xu, Ming, Nguyen, Chin, Xiong, Joty) | Thiết kế MAS không giám sát lúc suy luận (meta-agent tự đánh giá). |
| 2502.04306 | ScoreFlow (Wang, Yang et al.) | Tối ưu workflow bằng Score-DPO; báo cáo +8,2% (chỉ có báo cáo AI mỏng). |
| 2504.16129 | MARFT (Liao et al.) | Khung multi-agent RL fine-tuning; Stronger-MAS báo MAS chưa huấn luyện của họ hơn MARFT đã huấn luyện. |
| 2508.04652 | MAGRPO (Liu et al., Amato) | Cộng tác LLM như MARL hợp tác (Dec-POMDP), GRPO đa tác tử. |
| 2607.16133 | When Do MAS Help? An Information Bottleneck Perspective | MAS chỉ lợi khi nén ngữ cảnh lợi hơn mất mát thông tin qua relay; bảng ViTabQA p50 ≈ 647 token nên ít cần nén. |
| 2606.05670 | Do More Agents Help? (BenchAgent) | Cùng protocol với GPT-4.1: tối đa 1/6 MAS hơn đơn tác tử; 5 MAS còn lại thua 2,56–11,29 điểm. |

---

## 4. Cơ chế nào có thể chuyển sang pipeline table-QA 8B, và phép so sánh cùng ngân sách để kiểm

Các nguyên tắc dùng thống nhất ở mọi mục:
- **Qwen3-8B chạy temp 0.** "Self-MoA/SC" phải tạo đa dạng bằng prompt, few-shot, biến thể biểu diễn bảng hoặc đường code. Lấy mẫu nhiệt độ thì phải mở riêng và báo cáo riêng.
- **43% đáp án là một ô nguyên văn và được chấm EM.** Mọi bước tổng hợp nên là *chọn* một ứng viên đã chuẩn hoá, không *sinh lại*.
- **Ngưỡng phân giải khoảng 2 EM trên 992 câu.** Mọi so sánh dưới đây phải là cặp (paired): McNemar hoặc paired bootstrap trên cùng qa_id, như `evaluation/bootstrap.py` đã có.

### 4.0 Đã đo: co-failure β và trần oracle trên dự đoán hiện có

*Cách làm*: đọc các file dự đoán trong `outputs/`, gióng hàng với `dataset/qas_test.json` bằng `evaluation.io.align_records` (candidate policy `first`), chấm bằng `evaluation.exact_match.score_sample`. Mọi thành viên của phép so sánh chính đều là **EM raw**, trước finalizer/GSA. File few-shot GSA chỉ dùng ở hàng tham chiếu cuối. Tất cả các pool dùng chung giao 991 qa_id. Plurality vote gộp theo `normalize_text`; khi hoà thì lấy model tốt nhất. Đường dẫn file và script nằm ở Phụ lục A.

| Pool (raw) | Cỡ | EM từng thành viên | β (mọi model sai) [95% CP] | Oracle = 1−β | Trần so với model tốt nhất | Plurality vote |
|---|---|---|---|---|---|---|
| Qwen few-shot + zs + CoT | 3 | **67,41** / 63,17 / 59,43 | 24,72% [22,06; 27,53] | 75,28 | +7,87 | 65,79 |
| Qwen few-shot + zs + TD | 3 | 67,41 / 63,17 / 59,94 | 25,13% | 74,87 | +7,47 | 65,49 |
| Qwen few-shot + CoT + TD | 3 | 67,41 / 59,43 / 59,94 | 25,33% | 74,67 | +7,27 | 63,47 |
| **Dị thể**: Qwen few-shot + Gemma-3-4B zs + SEA-LION v3 8B few-shot | 3 | 67,41 / 40,26 / 49,45 | **23,81%** [21,19; 26,59] | 76,19 | **+8,78** | 65,29 |
| Qwen 4 prompt (fs, zs, CoT, TD) | 4 | xem trên | 23,61% [21,00; 26,38] | 76,39 | +8,98 | 65,19 |
| **Union**: Qwen 4 prompt + Gemma + SEA-LION | 6 | xem trên | **19,27%** [16,86; 21,87] | 80,73 | **+13,32** | 66,80 |
| Qwen 4 prompt + POMA (raw) | 5 | … / POMA 66,70 | 20,18% | 79,82 | +12,41 | 67,81 |
| Union + POMA | 7 | xem trên | 17,15% [14,86; 19,65] | 82,85 | +15,44 | 69,12 |
| *Tham chiếu*: Qwen few-shot **GSA** + Gemma + SEA-LION | 3 | 69,93 / 40,26 / 49,45 | 23,21% | 76,79 | +6,86 | 67,00 |

Khi cả hai cùng sai (raw), tỉ lệ *cùng một đáp án sai* là: Qwen–SEA-LION 35,5% (92/259), Qwen–Gemma 27,2% (75/276), Gemma–SEA-LION 26,8% (111/414).

Cách đọc:
1. **Dị thể có đóng góp dư địa riêng.** Thêm Gemma và SEA-LION vào 4 prompt Qwen làm β giảm từ 23,61% xuống 19,27%, tức **+4,34 EM trần biên**, lớn hơn ngưỡng 2 EM. Ở cùng cỡ 3, pool dị thể có β thấp hơn cả ba pool prompt Qwen khoảng 0,9–1,5 điểm. Các khoảng tin cậy chồng nhau, nên ở cỡ 3 khác biệt này chưa chắc chắn. Pipeline POMA cũng đóng góp dư địa riêng (+3,4 EM so với 4 prompt), đúng những câu few-shot bỏ lỡ.
2. **Vote không thu được dư địa đó.** Mọi pool không có POMA đều vote dưới Qwen few-shot raw (67,41), thua 0,6 đến 3,9 EM. Pool có POMA vote được 67,81 (5 hệ) và 69,12 (7 hệ), tức +0,4 và +1,7, đều dưới ngưỡng 2 EM. Cả hai vẫn thua *một* call few-shot có GSA (69,93). Chuẩn hoá/finalizer rẻ hơn và tốt hơn vote.
3. Như vậy "chất lượng > đa dạng" của Self-MoA đúng với *vote/fusion*, nhưng không đúng với *trần oracle*. Chỉ một bộ chọn học được (§4.1) mới có thể khai thác dị thể.
4. Một phần của β ≈ 19–25% là lỗi định dạng EM chứ không phải lỗi suy luận (MACT ghi nhận 1/3 lỗi đến từ EM chặt). Hàng tham chiếu GSA cho thấy finalizer lấy lại khoảng 2,5 EM cho Qwen. Phần đó thuộc về chuẩn hoá, không thuộc về orchestration.

Các kiểm tra kế tiếp (§4.1–4.6) chỉ đáng chạy vì trần này > 2 EM. Nhưng routing plateau (2606.07587) và phần "realizable" gần 0 trong 2606.27288 cảnh báo rằng thực tế chỉ thu được một phần nhỏ của trần.

### 4.1 Bộ chọn nhỏ đã huấn luyện trên các ứng viên đa góc nhìn (MATA-CC, PairRanker, GenRM)
- *Chuyển gì*: dùng một cross-encoder tiếng Việt (PhoBERT hoặc mDeBERTa, ~0,1–0,4B) làm bộ chọn, nhận (câu hỏi, bảng đã rút gọn, ứng viên) và trả xác suất đúng. Nó chọn giữa K ứng viên đã có: Qwen few-shot, zero-shot, CoT, POMA, SEA-LION, Gemma, và đường code nếu có. Theo §4.0, các mô hình dị thể và POMA là những nguồn mở thêm trần nhiều nhất. Nhãn là EM của ứng viên trên dự đoán của train 7,9k.
- *So sánh cùng ngân sách*: K call sinh ứng viên + bộ chọn, đối chứng với (a) Qwen few-shot 1 call; (b) plurality vote trên cùng K ứng viên; (c) Qwen tự chọn ("LLM judge") trên cùng K ứng viên, tức K+1 call; (d) *SC K prompt-variant* của few-shot, cùng K call. Báo cáo thêm tỉ lệ "làm hỏng câu đúng" theo cách của Table-Critic.
- *Chi phí*: phải chạy K prompt trên tập train (khoảng 7,9k × K call API). Nếu không, dùng dev hoặc một phần train.

### 4.2 Đa dạng công cụ/góc nhìn thay vì persona (MACT, MATA, Mixture-of-Minds)
- *Chuyển gì*: thêm một ứng viên sinh bằng code (pandas/SQL trên bảng Flatten) *làm ứng viên cho bộ chọn ở 4.1*, không ghi đè kết quả. Có thể thêm một ứng viên từ biểu diễn bảng khác (Flatten V1 và V2).
- *So sánh*: {few-shot, code-path} + bộ chọn, đối chứng với {few-shot, few-shot-variant} + cùng bộ chọn, cùng 2 call. Cách này tách được đóng góp của *góc nhìn* khỏi đóng góp của *số call*. Nên đo theo nhãn suy luận: code-path chỉ kỳ vọng lợi ở câu tính toán, còn 43% câu tra ô thì không. MATA phụ lục A cảnh báo rằng ở 7B general, PoT thường kém CoT.

### 4.3 Router/cascade Qwen ↔ SEA-LION/Gemma
- *Trần*: cặp Qwen few-shot (GSA) + SEA-LION few-shot có β = 25,23%, tức trần +4,84 EM (n = 991). Router thực tế thường thu được ít hơn nhiều.
- *So sánh*: một router kNN trên embedding câu hỏi (huấn luyện bằng EM của hai model trên train), 1 call mỗi câu, đối chứng với Qwen 1 call. Kỳ vọng dưới 2 EM. Chỉ nên làm để *xác nhận âm tính*, hoặc nếu mục tiêu là giảm chi phí (cascade Gemma → Qwen) thay vì tăng EM.

### 4.4 Tổng hợp kiểu Self-MoA ở temp 0
- *Chuyển gì*: K biến thể prompt của Qwen, sau đó một aggregator Qwen bị *ràng buộc chọn nguyên văn* một trong K đáp án, hoặc trả "Null".
- *So sánh*: cùng K + 1 call, đối chứng với plurality vote K + 1 (thêm một prompt-variant nữa). Self-MoA thắng USC ở cùng số pass trên văn bản mở, nhưng với EM thì chưa có bằng chứng. MACT cho thấy LLM-selection kém SC ở TQA.

### 4.5 Huấn luyện vai (MALT) hoặc huấn luyện dị thể (HACRL), nếu mở hướng fine-tune
- *MALT*: Llama-3.1-8B với 2–6k cặp mỗi vai, LoRA SFT + DPO. Đây là quy mô dữ liệu *tương đương* ViTabQA. Với Qwen3-8B và 7,9k câu: cây n = 3 tức 27 quỹ đạo mỗi câu, khoảng 213k lần gọi sinh, tốn kém nhưng làm được bằng vLLM trên Kaggle nếu dùng SEA-LION hoặc Qwen local.
  - *So sánh bắt buộc*: (a) SFT/DPO **một** model trên cùng dữ liệu (baseline STaR) với 1 call; (b) SC@9 prompt-variant với 9 call. Không có hai đối chứng này thì mọi gain đều bị nhiễu bởi dữ liệu và số call.
- *HACRL*: chia sẻ rollout Qwen3-8B ↔ SEA-LION khi huấn luyện, suy luận đơn. Không tốn call suy luận, nhưng RL online cỡ 8B+8B cần khoảng 8 GPU. Coi là **ngoài tầm Kaggle**, trừ khi hạ xuống 1.7B/4B.
- *Mixture-of-Minds* nhắc rằng với Qwen3-8B, phần lớn gain là do *workflow có công cụ*, không phải MARL (+0,6 trên FinQA). Nên kiểm 4.2 trước 4.5.

### 4.6 Những gì không nên chuyển
- Orchestration học được kiểu Puppeteer, MasRouter, MaAS, AFlow, FlowReasoner, MAS-GPT, OptiMAS: executor ≥32B hoặc API, tín hiệu thực thi (code), hoặc tác vụ nhiều bước.
- Generative fusion kiểu MoA hoặc GenFuser: rủi ro EM.
- Thêm vai planner/critic trên cùng Qwen: 2609.04217 và 2512.08296 đều dự báo âm ở mức baseline đơn tác tử 70%.

---

## 5. Không xác minh được / hạn chế

- **2609.04217**: arXiv v1 có định dạng IEEE TPAMI, 6 tác giả với tên khá chung chung (Dublin), 0 vote. Tôi không kiểm chứng được danh tính tác giả hay trạng thái bình duyệt. Số liệu được lấy nguyên từ PDF và nên coi là tiền ấn phẩm.
- **2606.27288**: một tác giả, tổ chức "KAIKAKU", và dùng tên các model (GPT-5.5, Claude Opus 4.8, Qwen3.7-Max…) mà tôi không kiểm chứng độc lập được. Mệnh đề 1−β là một đồng nhất thức sơ cấp (Kuncheva's Oracle) nên đứng vững bất kể phần thực nghiệm.
- **Đọc ở mức R** (báo cáo AI của alphaXiv, không phải full text): AFlow, MaAS, FlowReasoner, ReMA, Stronger-MAS, RL Tango, NVIDIA SLM. Các số chi tiết (GPU, số bước) của nhóm này **chưa được kiểm trên PDF**. ScoreFlow chỉ có báo cáo rất mỏng.
- **Đọc ở mức A**: 10 bài ở §3.6.
- **Mixture-of-Minds**: không tìm thấy số GPU trong các trang đã đọc.
- **Table-Critic**: câu "hơn majority voting ở chi phí tương đương" chỉ thấy trong phần đóng góp; bảng số liệu đối chứng không có trong các trang đã đọc.
- **Phép đo §4.0**: so sánh chính chỉ dùng EM raw. Hàng "tham chiếu" và cặp ở §4.3 dùng few-shot GSA (có finalizer). Candidate policy là `first`, trong khi evaluator chính thức dùng `single-required`. Vì vậy Gemma được chấm trên đủ 991 qa_id; file đánh giá chính thức `outputs/evaluation/bif_new/gemma_zero_shot.json` chỉ phủ 542 qa_id do lỗi policy. Dự đoán rỗng được scorer tính là "Null": có 31 trường hợp SEA-LION đúng nhờ quy tắc này. Nếu coi chúng là sai, β của union chỉ đổi từ 19,27% lên 19,37%, và của pool dị thể 3 từ 23,81% lên 24,02%. Mỗi hệ chỉ chạy một lượt ở temp 0 (Gemma qua OpenRouter, SEA-LION local). Số few-shot raw (67,41) và GSA (69,93) lệch vài phần mười so với báo cáo chính thức (70,16).
- Không gặp trang nào từ chối truy cập. Trình duyệt dùng riêng tab-3. Không đăng nhập, không gửi form.

---

## Phụ lục A. Tái lập phép đo §4.0

Chạy từ thư mục gốc repo bằng interpreter của env `kltn`: `D:/.virtual_env/anaconda/envs/kltn/python.exe cofailure.py` (cần `scipy`). Script chỉ đọc dữ liệu. Các thành viên và file dự đoán:

| Khoá | File | Ghi chú |
|---|---|---|
| qwen_fs_raw | `outputs/d01/openrouter_qwen_qwen3-8b/few_shot_adapted.json` | few-shot raw (legacy baseline → canonical, 18 lỗi parse) |
| qwen_fs_gsa | `outputs/d01/openrouter_qwen_qwen3-8b/few_shot_gsa.json` | few-shot + finalizer GSA (chỉ dùng cho hàng tham chiếu) |
| qwen_zs / qwen_cot / qwen_td | `outputs/baseline/qwen/full_{zs,cot,td}/qwen3-8b.json` | raw |
| qwen_poma | `outputs/d01/openrouter_qwen_qwen3-8b/poma_first.json` | POMA raw, first candidate |
| gemma_zs | `outputs/q2_revision/openrouter_google_gemma-3-4b-it/full/raw/zero_shot/openrouter_google_gemma-3-4b-it.json` | Gemma-3-4B qua OpenRouter |
| sealion_fs | `outputs/notebooks/sea_lion_v3_8b_it/test/few_shot/predictions.jsonl` | SEA-LION v3 8B local |

```python
"""Đo co-failure (beta) / oracle-of-N trên các dự đoán đã có của POMA (chỉ đọc, không sửa repo)."""
import itertools
import sys
from collections import Counter
from pathlib import Path

from scipy.stats import beta as B

ROOT = Path(r"D:\.UIT\KLTN\github\POMA")
sys.path.insert(0, str(ROOT))
from evaluation.io import align_records, load_json_records  # noqa: E402
from evaluation.exact_match import score_sample  # noqa: E402
from evaluation.normalization import normalize_text  # noqa: E402

QAS = load_json_records(ROOT / "dataset/qas_test.json")
SYSTEMS = {
    "qwen_fs_raw": "outputs/d01/openrouter_qwen_qwen3-8b/few_shot_adapted.json",
    "qwen_fs_gsa": "outputs/d01/openrouter_qwen_qwen3-8b/few_shot_gsa.json",
    "qwen_zs": "outputs/baseline/qwen/full_zs/qwen3-8b.json",
    "qwen_cot": "outputs/baseline/qwen/full_cot/qwen3-8b.json",
    "qwen_td": "outputs/baseline/qwen/full_td/qwen3-8b.json",
    "qwen_poma": "outputs/d01/openrouter_qwen_qwen3-8b/poma_first.json",
    "gemma_zs": "outputs/q2_revision/openrouter_google_gemma-3-4b-it/full/raw/zero_shot/openrouter_google_gemma-3-4b-it.json",
    "sealion_fs": "outputs/notebooks/sea_lion_v3_8b_it/test/few_shot/predictions.jsonl",
}


def load(path):
    samples, _ = align_records(load_json_records(ROOT / path), QAS, candidate_policy="first")
    return {s.qa_id: (score_sample(s).value, normalize_text(s.prediction[0])) for s in samples}


def cp(k, n, a=0.05):
    lo = 0.0 if k == 0 else B.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else B.ppf(1 - a / 2, k + 1, n - k)
    return lo, hi


def pool_report(name, data, members, ids):
    n = len(ids)
    em = {m: sum(data[m][i][0] for i in ids) / n for m in members}
    best = max(em, key=em.get)
    k = sum(all(data[m][i][0] == 0 for m in members) for i in ids)
    lo, hi = cp(k, n)
    vote = 0
    for i in ids:
        c = Counter(data[m][i][1] for m in members)
        top, cnt = c.most_common(1)[0]
        pick = data[best][i][1] if sum(1 for v in c.values() if v == cnt) > 1 else top
        vote += next(data[m][i][0] for m in members if data[m][i][1] == pick)
    print(f"[{name}] n={n} {members}")
    print("   EM " + " / ".join(f"{m}={100*v:.2f}" for m, v in em.items()))
    print(f"   beta={100*k/n:.2f} (k={k}, CP95 [{100*lo:.2f},{100*hi:.2f}]) oracle={100*(1-k/n):.2f} "
          f"headroom={100*(1-k/n-em[best]):.2f} vote={100*vote/n:.2f} (vs best {100*em[best]:.2f})")
    return k / n


def main():
    data = {k: load(v) for k, v in SYSTEMS.items()}
    ids = sorted(set.intersection(*(set(v) for v in data.values())))
    Q = ["qwen_fs_raw", "qwen_zs", "qwen_cot", "qwen_td"]
    H = ["gemma_zs", "sealion_fs"]
    print("== RAW, equal size 3 ==")
    for pair in itertools.combinations(Q[1:], 2):
        pool_report("Qwen raw 3", data, ["qwen_fs_raw", *pair], ids)
    pool_report("Hetero raw 3", data, ["qwen_fs_raw", *H], ids)
    print("== RAW, Qwen-4 vs union ==")
    b4 = pool_report("Qwen raw 4", data, Q, ids)
    bu = pool_report("Union Qwen4+Gemma+SEA-LION", data, Q + H, ids)
    print(f"   marginal headroom from heterogeneous models = {100*(b4-bu):.2f} EM")
    pool_report("Qwen raw 4 + POMA", data, Q + ["qwen_poma"], ids)
    print("== secondary: GSA few-shot ==")
    pool_report("Qwen GSA+zs+cot+td", data, ["qwen_fs_gsa", "qwen_zs", "qwen_cot", "qwen_td"], ids)
    pool_report("Hetero GSA 3", data, ["qwen_fs_gsa", *H], ids)
    for a, b in itertools.combinations(["qwen_fs_raw", *H], 2):
        both = [i for i in ids if data[a][i][0] == 0 and data[b][i][0] == 0]
        agree = sum(data[a][i][1] == data[b][i][1] for i in both)
        print(f"   both-wrong {a}/{b}: {len(both)}, same wrong answer {agree} ({100*agree/max(1, len(both)):.1f}%)")
    for m in ["qwen_fs_raw", *H]:
        e = sum(1 for i in ids if data[m][i][1] == "" and data[m][i][0] == 1)
        print(f"   {m}: empty prediction credited as correct Null = {e}")


if __name__ == "__main__":
    main()
```
