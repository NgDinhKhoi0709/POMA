# Khảo sát blog practitioner: multi-agent LLM, thiết kế, failure modes, và agent cho table/structured-data QA

Ngày khảo sát: 2026-09-26. Phạm vi: blog và bài kỹ thuật của practitioner, không phải paper. Mục đích là cung cấp bằng chứng cho việc thiết kế multi-agent trên Open-ViTabQA (Qwen3-8B, bảng nhỏ, câu trả lời free-form tiếng Việt).

**Cách đọc nguồn:** mọi trang liệt kê ở mục 2 đều được mở bằng browser pane (tab riêng `tab-1`). WebSearch chỉ dùng để *tìm* URL (mục bảng/text-to-SQL, Interconnects, Arctic). Những nguồn chỉ thấy qua kết quả search được ghi riêng ở mục 6. Trích dẫn nguyên văn tối đa một câu ngắn (<15 từ) cho mỗi nguồn, phần còn lại đều là diễn giải.

**Lưu ý về số liệu:** hầu hết con số định lượng dưới đây đo trên **frontier model** (Claude Opus/Sonnet 4, GPT-4o/5, Gemini) và trên các task agentic dài (research, browsing, tool use), không phải trên QA một bảng nhỏ. Bằng chứng đo trên model ≤10B rất mỏng và được gom riêng ở mục 4.0.

---

## 1. Tóm tắt 10 dòng: đồng thuận và mâu thuẫn

1. **Đồng thuận mạnh nhất:** bắt đầu bằng một LLM call được tối ưu (retrieval + few-shot), chỉ thêm bước hoặc agent khi *đo được* là tốt hơn. Anthropic, smolagents/HF, Phil Schmid, BAIR và Raschka đều nói vậy.
2. **Multi-agent thắng khi task song song hóa được và vượt context một agent.** Ví dụ là research diện rộng (Anthropic +90.2%) hay Finance-Agent (Google +81%). Nó **thua trên task tuần tự**: Google đo PlanCraft −39 đến −70%.
3. Anthropic cho rằng **phần lớn lợi ích của MAS đến từ việc tiêu nhiều token hơn**: token usage giải thích 80% phương sai trên BrowseComp. MAS tốn khoảng 15× token so với chat. Vì vậy mọi so sánh phải khớp compute.
4. **Context engineering là nút thắt chung** (Cognition, LangChain, Anthropic, Raschka). Mỗi lần "dịch" hay chuyển tay giữa các agent đều làm mất thông tin: LangChain đo được supervisor diễn đạt lại sai ("translation") và sửa bằng `forward_message`, còn Anthropic dùng cụm "game of telephone" khi khuyên subagent ghi output ra filesystem.
5. Đọc thì dễ song song hóa, viết thì không (LangChain, Schmid). Khâu viết câu trả lời cuối nên do **một** agent làm.
6. Khi có tín hiệu kiểm chứng tất định, **verification** (dry-run, parse, execution, test) được ưa hơn LLM critique. Ví dụ: Google Cloud với text-to-SQL, Anthropic với coding, Raschka với S*.
7. **Model nhỏ yếu ở chính các kỹ năng mà agent cần**: chọn tool, tuân thủ JSON/format, phán đoán bước tiếp theo. HF gọi đây là "structure tax", Raschka thấy gemma4:e2b đạt 0/5. Cho model nhỏ thì control flow nên nằm trong code (workflow), không nên để model quyết (agent).
8. **Mâu thuẫn 1:** Anthropic "xây MAS" đối lập Cognition "đừng xây MAS". LangChain và Schmid hòa giải bằng trục read/write và context-sharing, nhưng tranh luận vẫn còn về chuyện có nên cho các agent *viết song song* hay không.
9. **Mâu thuẫn 2:** Google thấy orchestrator *chặn* lỗi (error amplification 4.4× so với 17.2× ở hệ độc lập), còn LangChain thấy supervisor *gây* lỗi dịch thuật. Raschka nói harness quan trọng ngang hoặc hơn model, trong khi Anthropic thấy nâng cấp model có lợi hơn nhân đôi token.
10. **Mâu thuẫn 3 (định nghĩa):** Chip Huyen coi pipeline plan → validate → execute đã là "multi-agent", Anthropic gọi cùng thứ đó là "workflow". Nhiều tranh luận "MAS có giúp không" thực chất là tranh luận về nhãn. Ví dụ, Uber gọi từng LLM call hẹp là "agent".

---

## 2. Bảng nguồn

Cột "Cách đọc" có ba giá trị: **Full** là đọc toàn văn; **Sect** là đọc các mục liên quan hoặc heading; **Pay** là trang bị paywall, chỉ đọc được phần mở.

| # | Nguồn (tác giả) | Ngày | Claim chính | Loại bằng chứng | Cách đọc |
|---|---|---|---|---|---|
| R1 | Raschka, *Components of A Coding Agent* | 2026-04-04 | Harness (context, tool, memory, subagent có giới hạn) quyết định nhiều như model; subagent phải bị "bind" | Ý kiến + mô tả code (mini-coding-agent) | Full |
| R2 | Raschka, *Using Local Coding Agents* | 2026-06-27 | Model open-weight nhỏ yếu ở phán đoán agentic; token usage do harness quyết định | Benchmark nhỏ tự làm (5 task) | Full |
| R3 | Raschka, *Categories of Inference-Time Scaling* | 2026-01-24 | 6 nhóm: CoT, self-consistency, best-of-N, rejection sampling + verifier, self-refinement, search | Tổng quan (paywall) | Pay (chỉ intro + mục lục) |
| R4 | Raschka, *The State of LLM Reasoning Model Inference* | 2025-03-08 | Inference scaling giúp model nhỏ bắt kịp; không có kỹ thuật nào thắng mọi task; có cảnh báo chi phí | Tổng quan paper | Full |
| R5 | Raschka, *The State Of LLMs 2025* | 2025-12-30 | 2026 sẽ là năm của inference-scaling và tooling; tiến bộ đến từ hệ thống bao quanh model | Ý kiến/dự báo | Full |
| R6 | Raschka, *Controlling Reasoning Effort in LLMs* | 2026-07-18 | Effort là một input tường minh; Qwen3 có công tắc bật/tắt thinking và budget cứng; auto-effort còn khó | Tổng quan kỹ thuật | Sect |
| R7 | Raschka, *Understanding the 4 Main Approaches to LLM Evaluation* | 2025-10-05 | Verifier chỉ dùng được cho domain kiểm chứng được; LLM judge cần judge mạnh và có bias | Tutorial + code | Sect |
| R8 | Raschka, *The State of RL for LLM Reasoning* | 2025-04-19 | RL trên model distill nhỏ có hiệu quả, nhưng nhiều mức "cải thiện" chỉ là nhiễu seed | Tổng quan paper | Sect |
| R9 | Raschka, 3 danh sách paper (2025 H1, 2025 H2, 2026 Jan–May) | 2025-07-01 / 2025-12-30 / 2026-06-06 | Có mục "Agent Systems and Tool Use" (2026) | Danh mục | Pay |
| R10 | Raschka, *GPT-6 Astra, Looped Transformers* và *Beyond Standard LLMs* | 2026-09-09 / 2025-11-04 | Liên quan thấp (kiến trúc) | Tổng quan | Sect (heading) |
| A1 | Anthropic (Erik S. & Barry Zhang), *Building effective agents* | 2024-12-19 | Phân biệt workflow và agent; 5 pattern; giữ đơn giản | Kinh nghiệm khách hàng | Full |
| A2 | Anthropic (Hadfield et al.), *How we built our multi-agent research system* | 2025-06-13 | Orchestrator-worker +90.2%; ~15× token; token giải thích 80% phương sai | Eval nội bộ, BrowseComp | Full |
| C1 | Cognition (Walden Yan), *Don't Build Multi-Agents* | 2025-06-12 | Chia sẻ toàn bộ trace; hành động mang theo quyết định ngầm; nên dùng agent đơn tuyến | Lập luận + ví dụ | Full |
| L1 | LangChain (Harrison Chase), *How and when to build multi-agent systems* | 2025-06-16 | Hòa giải A2/C1: context engineering; đọc thì song song, viết thì đơn | Phân tích | Full |
| L2 | LangChain (Will Fu-Hinthorn), *Benchmarking Multi-Agent Architectures* | 2025-06-10 | Single agent tốt nhất khi có ≤1 domain nhiễu; supervisor mất điểm do "translation" | Thí nghiệm gpt-4o, τ-bench retail | Full |
| H1 | HF (Roucher et al.), *Introducing smolagents* | 2024-12-31 | Agency là một phổ; agent thường là overkill; code action tốt hơn JSON | Mô tả + benchmark | Full |
| H2 | HF (Roucher et al.), *Open-source DeepResearch* | 2025-02-04 | GAIA: CodeAgent 55.15% so với JSON agent 33% | Benchmark (frontier LLM) | Full |
| H3 | HF (Reedi & Roucher), *CodeAgents + Structure* | 2025-05-28 | Structured output +2–7 điểm với model mạnh; model nhỏ chịu "structure tax" | Benchmark 15.7k trace | Full |
| G1 | Google Research (Kim & Liu), *Towards a science of scaling agent systems* | 2026-01-28 (paper 2512.08296) | 180 cấu hình: +81% trên task song song, −39..−70% trên task tuần tự; error amplification 17.2× so với 4.4× | Thí nghiệm có kiểm soát (GPT/Gemini/Claude) | Full |
| CH | Chip Huyen, *Agents* | 2025-01-07 | Tách plan khỏi execute; lỗi cộng dồn (95%/bước qua 10 bước còn 60%); taxonomy lỗi | Khung lý thuyết (sách AI Engineering) | Sect |
| B1 | BAIR Blog, *The Shift from Models to Compound AI Systems* | 2024-02-18 | Cải tiến bằng thiết kế hệ thống thường rẻ hơn scaling; cần tối ưu end-to-end (DSPy) | Phân tích + ví dụ | Sect |
| LW | Lilian Weng, *LLM Powered Autonomous Agents* | 2023-06-23 | Khó ở planning dài và ở độ tin cậy của giao diện ngôn ngữ tự nhiên (lỗi format) | Tổng quan | Sect |
| HH | Hamel Husain & Shreya Shankar, *AI Evals FAQ* | 2026-09-18 (tài liệu sống) | Error analysis; ghi nhận lỗi đầu tiên ở upstream; transition failure matrix; eval nhị phân | Kinh nghiệm dạy >5.000 kỹ sư | Sect |
| EY | Eugene Yan, *Evaluating Long-Context Q&A Systems* | không hiện ngày | Tách faithfulness khỏi helpfulness; ba nhãn refusal (đúng, sai, bịa) | Tổng quan | Sect |
| PS | Philipp Schmid, *Single vs Multi-Agent System?* | 2025-06-20 | Bảng so sánh; đọc thì dùng MAS, viết thì dùng single | Tổng hợp | Full |
| NL | Nathan Lambert, *Use multiple models* | 2026-01-11 | Model "jagged" theo nhiều kiểu khác nhau; đổi sang model khác chỉ giúp khi mỗi model đã có xác suất thành công khá | Kinh nghiệm cá nhân | Full |
| GC | Google Cloud (Per Jacobsson), *Techniques for improving text-to-SQL* | 2025-05-17 | Text-to-SQL agent: disambiguation, dry-run/validation, self-consistency qua nhiều prompt/model | Mô tả hệ thống production | Full |
| SF | Snowflake (Borchmann et al.), *Real-Time Text2SQL Behind Snowflake Intelligence* | 2025-11-04 | Model chuyên biệt + RL bằng execution reward đạt ngang Sonnet 4.5, nhanh hơn; orchestrator bỏ qua reasoning cho câu đã verify | Benchmark nội bộ | Full |
| UB | Uber (Khune et al.), *QueryGPT* | 2024-09-19 | Các "agent" hẹp (intent, table, column-prune) rất tốt; eval tách rời bằng oracle; bỏ qua dao động ~5% | Production + eval nội bộ | Full |

Tổng cộng 32 trang bài viết (không tính trang archive/index): 18 đọc toàn văn, 10 đọc theo mục/heading, 4 bị paywall.

---

## 3. Ghi chú theo nguồn

### 3.1 Sebastian Raschka, *Ahead of AI*

Đã mở archive (https://magazine.sebastianraschka.com/archive) và lọc mọi bài từ 04/2025 đến 09/2026 liên quan agent, reasoning, inference scaling, model nhỏ, tool use và các danh sách paper. **Blog của Raschka không có bài riêng về multi-agent**, và **các phần đọc được không nêu paper table-QA nào.** Góc nhìn của ông về agent là góc nhìn harness (một agent cộng subagent có giới hạn), không phải hội đồng nhiều persona.

**R1. *Components of A Coding Agent*** (2026-04-04), https://magazine.sebastianraschka.com/p/components-of-a-coding-agent
- Định nghĩa phân tầng: LLM là engine, reasoning model là LLM được train hoặc prompt để tốn thêm compute lúc suy luận, agent là vòng lặp điều khiển quanh model, harness là phần mềm quản lý context, tool, state.
- Sáu thành phần: (1) live repo context, (2) prompt prefix ổn định và cache, (3) tool có cấu trúc, được validate và qua approval, (4) giảm context bloat bằng clip, dedupe, tóm tắt, giữ phần gần đây chi tiết hơn, (5) session memory hai tầng (full transcript và working memory), (6) **delegation cho subagent bị giới hạn**: subagent thừa hưởng đủ context để hữu ích nhưng chỉ được đọc (read-only) và có giới hạn độ sâu đệ quy.
- Quan điểm riêng: vì các model gốc hiện nay có năng lực gần nhau, harness thường là yếu tố phân biệt. Câu then chốt: "A lot of apparent 'model quality' is really context quality."
- Liên quan model nhỏ và bảng: gián tiếp. Harness *bớt* tự do cho model (tool có tên, tham số được kiểm tra) và nhờ đó tăng độ tin cậy.
- **Takeaway cho Open-ViTabQA:** chất lượng context đưa vào (cách biểu diễn bảng, chọn few-shot) nhiều khả năng quan trọng hơn số vai. Nếu có subagent thì chỉ nên là bước hẹp, chỉ đọc.

**R2. *Using Local Coding Agents*** (2026-06-27), https://magazine.sebastianraschka.com/p/using-local-coding-agents. Đây là nguồn duy nhất trong khảo sát có số liệu trên model nhỏ, chạy local.
- Tự làm bộ 5 task lý luận kèm tool-call (model chỉ trả về tool call, không thực thi): Qwen3.6-35B-A3B (MoE, ~3B tham số active) đạt 3/5, North Mini Code 1/5, **gemma4:e2b 0/5**. Lỗi không nằm ở format mà ở phán đoán: chọn sai tool, hỏi lại dù context đã đủ, chọn sai file.
- Kết luận của ông: 3/5 là dùng được nhưng chưa tin cậy cho tool use tự chủ. Một harness biết ràng buộc hành động, thêm retry và cung cấp context tốt hơn có thể giúp. Model rất nhỏ chỉ hợp với task hẹp, bị ràng buộc chặt.
- Trong harness đầy đủ (bộ 5 bài agent): Qwen3.6 và North Mini Code giải 4/5 trong Qwen-Code; Qwen3.6 làm tốt hơn trong Codex so với harness "gốc" của nó, trái với kỳ vọng. Gemma 4 E2B trượt nhiều.
- **Token usage chủ yếu do harness quyết định, không phải model.** Claude Code tốn nhiều token nhất vì đưa lại context đầu vào qua các lượt (một lần chạy khoảng 578k input so với khoảng 4.5k output trong 25 lượt), Codex tốn ít nhất. Khi hai harness cho tỉ lệ thành công bằng nhau, harness tốn ít token hơn là thắng lớn.
- Có dẫn paper Polar (arXiv 2605.24220): Qwen3.5-4B chạy tốt nhất trong harness mà nó được tối ưu cho.
- **Takeaway:** với 8B, đừng giao cho model quyết định luồng (chọn bước hay tool tiếp theo). Hãy để luồng trong code. Chi phí của một pipeline đến từ việc lặp lại context qua các vai, nên cần đo token.

**R3. *Categories of Inference-Time Scaling*** (2026-01-24, bài trả phí), https://magazine.sebastianraschka.com/p/categories-of-inference-time-scaling
- Chỉ đọc được phần mở đầu và mục lục: CoT, self-consistency, best-of-N ranking, rejection sampling với verifier, self-refinement, search over solution paths, rồi "Conclusions, Categories, and Combinations".
- Ông cho biết chương sách về inference scaling đưa base model từ khoảng 15% lên khoảng 52% (trên benchmark toán của sách, không phải table QA). Phần phân tích còn lại bị khóa.
- **Takeaway:** trong khung phân loại của ông, "multi-agent debate" không phải một nhóm riêng. Nó rơi vào self-consistency/voting hoặc self-refinement, nên nên được so sánh với chính các baseline này ở cùng compute.

**R4. *The State of LLM Reasoning Model Inference*** (2025-03-08), https://magazine.sebastianraschka.com/p/state-of-llm-reasoning-and-inference-scaling
- Tóm tắt 13 paper về inference scaling sau R1: s1 với budget forcing và token "Wait", TPO, underthinking, Can 1B surpass 405B, S*, Chain of Draft, feedback/edit models, v.v.
- Quan điểm riêng: (a) tăng compute lúc suy luận giúp model nhỏ thu hẹp khoảng cách với model lớn; (b) **không có kỹ thuật nào tốt nhất trên mọi task**, dẫn paper benchmark "Inference-Time Computations for LLM Reasoning and Planning" (trang dùng lại link của mục trước nên ID chưa xác định, xem mục 5); (c) cảnh báo chi phí: dùng model nhỏ với nhiều inference scaling hay dùng model lớn là một bài toán kinh tế; (d) CoT không cần cho câu hỏi dữ kiện đơn giản.
- Feedback + Edit models (2503.04378) là dạng generator, critic, editor cho task mở, nhưng critic và editor ở đó *được train riêng*, không phải cùng model đóng nhiều persona.
- **Takeaway:** khoảng 43% câu trả lời là một ô nguyên văn, tức là câu hỏi đơn giản, nơi CoT hay thêm bước được Raschka nhận định là không cần thiết.

**R5. *The State Of LLMs 2025*** (2025-12-30), https://magazine.sebastianraschka.com/p/state-of-llms-2025
- Dự báo 2026: phần lớn tiến bộ benchmark sẽ đến từ tooling và inference-time scaling, không từ model lõi. Hiệu năng sẽ trông như tăng nhưng thực ra do ứng dụng bao quanh tốt lên. Dev sẽ tập trung giảm reasoning token ở chỗ không cần.
- "Benchmaxxing": benchmark chỉ còn là ngưỡng cần vượt, không còn xếp hạng đáng tin.
- Ông dẫn DeepSeekMath-V2 kết hợp self-consistency với self-refinement, lặp nhiều vòng refine thì tăng độ chính xác (trên toán thi đấu).
- Ông dự báo RAG kiểu cũ sẽ phai dần nhường chỗ cho long-context. Với bảng p50 khoảng 650 token thì vấn đề này không liên quan.
- **Takeaway:** cải thiện nên được đánh giá như cải thiện của "hệ thống", đi kèm chi phí, và phải xét độ ồn benchmark.

**R6. *Controlling Reasoning Effort in LLMs*** (2026-07-18), https://magazine.sebastianraschka.com/p/controlling-reasoning-effort-in-llms (đọc mục 4, 5.1, 6.5, 7)
- Qwen3: `enable_thinking=False` chèn một khối `<think></think>` rỗng (công tắc cứng), `/think` và `/no_think` là công tắc mềm, học qua giai đoạn "Thinking Mode Fusion". Qwen3 còn có budget cứng: khi tới ngưỡng thì dừng suy nghĩ và chèn chỉ thị kết thúc, hành vi này tự phát sinh sau Fusion chứ không được train trực tiếp.
- Effort tăng thì token tăng, độ chính xác tăng nhưng lợi ích giảm dần.
- Chọn effort tự động còn khó. Auto mode của GPT-5 "trúng ít trượt nhiều" và đã bị gỡ. Ông kỳ vọng một router rẻ hoặc chính harness sẽ chọn mode.
- **Takeaway:** với Qwen3-8B, "thinking on/off/budget" là một núm compute sẵn có, rẻ hơn thêm agent. Router chọn mode theo loại câu hỏi là một workflow hẹp, đúng loại bước mà các practitioner khen.

**R7. *Understanding the 4 Main Approaches to LLM Evaluation*** (2025-10-05), https://magazine.sebastianraschka.com/p/llm-evaluation-4-approaches
- Verifier chấp nhận câu trả lời free-form nhưng cần domain kiểm chứng được, và outcome verifier chỉ chấm kết quả cuối. LLM judge hợp với free-form nhưng phụ thuộc năng lực judge, prompt và style. Ông cho rằng ensemble judge làm kết quả bền hơn.
- Lý do judge hoạt động: đánh giá thường dễ hơn sinh câu trả lời.
- **Takeaway:** Open-ViTabQA nằm giữa hai loại. Ô nguyên văn gần như kiểm chứng được (khớp chuỗi), còn câu trả lời diễn giải cần judge. Nên tách hai loại khi đo.

**R8. *The State of Reinforcement Learning for LLM Reasoning*** (2025-04-19), https://magazine.sebastianraschka.com/p/the-state-of-llm-reasoning-model-training (đọc có chọn lọc)
- RL cho model distill nhỏ (1.5B, 7k ví dụ, khoảng $42) vượt o1-preview trên AIME24 (2503.16219). Tuy nhiên "A Sober Look at Progress in LM Reasoning" chỉ ra đổi random seed có thể lệch vài điểm phần trăm trên benchmark nhỏ.
- **Takeaway:** củng cố ngưỡng nhiễu khoảng 2 EM trên 992 câu. Mọi so sánh vai/agent cần nhiều seed hoặc kiểm định cặp.

**R9. Các danh sách paper** (2025 H1: https://magazine.sebastianraschka.com/p/llm-research-papers-2025-list-one; 2025 H2: /p/llm-research-papers-2025-part2; 2026 Jan–May: /p/llm-research-papers-2026-part1)
- Cả ba đều **bị paywall**. Bản 2026 để lộ rằng có mục "Agent Systems and Tool Use" và "Coding Agents and Software Engineering", nhưng không lộ nội dung. Bản 2025 H1 bị cắt ở mục 1b. Bản 2025 H2 chỉ lộ danh mục.
- **Không thấy paper table-QA hay multi-agent nào trong phần đọc được.**

**R10. *GPT-6 Astra, Looped Transformers*** (2026-09-09) và ***Beyond Standard LLMs*** (2025-11-04): đã mở, liên quan thấp (kiến trúc looped/recursive; TRM/HRM chỉ áp dụng cho câu đố). Một ý phụ ở bài Astra: với model *mới, mạnh*, nên bớt AGENTS.md hay các chỉ dẫn cầm tay vì có thể gò bó model. Đây là nhận xét về frontier model, không nên suy ra cho 8B.

### 3.2 Anthropic

**A1. *Building effective agents*** (2024-12-19), https://www.anthropic.com/engineering/building-effective-agents
- Phân biệt **workflow** (LLM và tool đi theo code path định sẵn) với **agent** (LLM tự điều khiển quy trình).
- Năm pattern: prompt chaining (có gate), routing, parallelization (sectioning và voting), orchestrator-workers, evaluator-optimizer.
- Khi nào dùng: chaining khi task tách sạch thành các bước cố định. Routing khi có các loại tách biệt *và* phân loại được chính xác. Voting khi cần nhiều góc nhìn để tăng độ tin cậy. Evaluator-optimizer khi có tiêu chí đánh giá rõ và phản hồi thực sự cải thiện được output.
- Nhấn mạnh: tối ưu một LLM call với retrieval và ví dụ in-context thường là đủ. Nguyên văn: "you should consider adding complexity only when it demonstrably improves outcomes".
- Agent cần "ground truth" từ môi trường ở mỗi bước. Lỗi cộng dồn là cái giá của tự chủ.
- Về ACI (agent-computer interface): giữ format gần văn bản tự nhiên, tránh overhead format (escape, đếm dòng), và "poka-yoke" tool. Họ dành nhiều thời gian tối ưu tool hơn prompt.
- **Takeaway:** pipeline POMA hiện là một workflow. Câu hỏi đúng là bước nào *chứng minh được* giá trị, không phải có nên dùng agent hay không.

**A2. *How we built our multi-agent research system*** (2025-06-13), https://www.anthropic.com/engineering/multi-agent-research-system
- Orchestrator-worker: lead agent cộng các subagent chạy song song, mỗi subagent có context riêng. Lý do chính là **nén thông tin** từ khối dữ liệu lớn vượt một context window.
- Số liệu: MAS gồm Opus 4 làm lead và Sonnet 4 làm subagent hơn Opus 4 đơn lẻ **90.2%** trên eval research nội bộ. Trên BrowseComp, 3 yếu tố giải thích 95% phương sai, trong đó **token usage riêng nó giải thích 80%**. Agent tốn khoảng 4× token so với chat, MAS khoảng **15×**. Nâng Sonnet 3.7 lên Sonnet 4 lợi hơn nhân đôi token budget.
- Nguyên văn: "Multi-agent systems work mainly because they help spend enough tokens to solve the problem."
- Không hợp khi các agent phải chia sẻ cùng context hoặc phụ thuộc lẫn nhau nhiều (phần lớn coding).
- Failure modes ban đầu: sinh 50 subagent cho câu hỏi đơn giản, subagent trùng việc, hiểu sai task do chỉ dẫn mơ hồ. Cách sửa: dạy orchestrator giao việc kèm objective, format output, tool và ranh giới; ghi quy tắc scale effort theo độ phức tạp vào prompt (câu hỏi fact đơn giản chỉ cần 1 agent với 3–10 tool call).
- Eval: bắt đầu với khoảng 20 câu vì lúc đầu hiệu ứng lớn (ví dụ 30% lên 80%). Dùng **một** LLM-judge call với rubric và thang 0–1 kèm pass/fail thì nhất quán và khớp người hơn nhiều judge. Kiểm tra thủ công vẫn cần.
- Phụ lục: cho subagent ghi output ra filesystem và chỉ truyền tham chiếu về, để tránh "game of telephone" khi coordinator chép lại.
- **Takeaway:** lý do MAS thắng ở đây (vượt context, song song, token nhiều) gần như không có mặt trong Open-ViTabQA (bảng p50 khoảng 650 token, một câu hỏi, một đáp án). Nếu MAS có gain thì phải kiểm tra lại với baseline cùng token.

### 3.3 Cognition, *Don't Build Multi-Agents*

Walden Yan, 2025-06-12, https://cognition.ai/blog/dont-build-multi-agents (chuyển hướng sang cognition.com)
- Hai nguyên tắc: (1) chia sẻ context, và là *toàn bộ trace* chứ không chỉ message; (2) "Actions carry implicit decisions, and conflicting decisions carry bad results."
- Ví dụ Flappy Bird: subagent hiểu sai subtask hoặc làm với style mâu thuẫn nhau, rồi agent tổng hợp phải ghép hai kết quả sai.
- Mặc định nên là agent đơn tuyến. Khi context tràn thì dùng một model nén lịch sử (họ fine-tune model nhỏ cho việc này).
- **Edit-apply model:** model lớn mô tả thay đổi, model nhỏ áp dụng. Cách này hay hỏng vì model nhỏ hiểu sai chỉ dẫn chỉ vì những mơ hồ rất nhỏ. Ngày nay quyết định và áp dụng thường gộp vào một model, một hành động.
- Agent tranh luận với nhau (debate) chưa đáng tin hơn một agent (quan sát năm 2025).
- **Takeaway:** mỗi lần chuyển tay giữa các vai trong POMA (planner, reasoner, finalizer) là một điểm hiểu sai. Ví dụ edit-apply cho thấy trực tiếp rủi ro model nhỏ diễn giải sai chỉ dẫn của model hay vai phía trước.

### 3.4 LangChain

**L1. *How and when to build multi-agent systems*** (Harrison Chase, 2025-06-16), https://blog.langchain.com/how-and-when-to-build-multi-agent-systems/
- Hòa giải A2 và C1: cả hai đều nói về context engineering. MAS thiên về "đọc" dễ hơn thiên về "viết". Trong hệ của Anthropic, phần viết báo cáo cuối do **một** agent làm trong một call.
- **Takeaway:** đọc hay trích bảng có thể tách ra, còn soạn câu trả lời cuối nên là một bước duy nhất.

**L2. *Benchmarking Multi-Agent Architectures*** (Will Fu-Hinthorn, 2025-06-10), https://blog.langchain.com/benchmarking-multi-agent-architectures/
- Thiết lập: gpt-4o, 100 câu đầu của τ-bench retail, thêm 0–7 domain gây nhiễu (mỗi domain 19 tool). So ba kiến trúc: single agent, swarm, supervisor.
- Kết quả: single agent tụt mạnh khi có từ 2 domain nhiễu trở lên, **nhưng tốt hơn một chút khi chỉ có 1 domain nhiễu**. Swarm hơn supervisor một chút. Supervisor mất điểm vì lớp "translation", tức phải diễn đạt lại output của sub-agent.
- Cách sửa đã làm: bỏ handoff message khỏi context của sub-agent; thêm tool `forward_message` để supervisor chuyển *nguyên văn* output thay vì viết lại; thử cách đặt tên tool. Bản supervisor đầu tiên rất kém, các sửa đổi này cho khoảng +50%.
- Chưa giải được: vẫn chưa bằng single agent khi ít nhiễu.
- **Takeaway cho POMA:** đây là bằng chứng đo được gần nhất với hiện tượng "finalizer làm hỏng đáp án". Một lớp tổng hợp diễn đạt lại có thể biến ô nguyên văn đúng thành sai. Cách tương ứng là cho phép *chép hay forward* span thay vì sinh lại.

### 3.5 Hugging Face

**H1. *Introducing smolagents*** (2024-12-31), https://huggingface.co/blog/smolagents
- Agency là một phổ: processor, router, tool call, multi-step agent, multi-agent. Agent thường là overkill. Nếu workflow tất định đáp ứng được thì cứ code nó.
- Viết action bằng code tốt hơn JSON (dẫn CodeAct 2402.01030).
- Có ví dụ text-to-SQL agent trong phần docs (không mở).

**H2. *Open-source DeepResearch*** (2025-02-04), https://huggingface.co/blog/open-deep-research
- Trên GAIA validation, dùng frontier LLM: CodeAgent đạt 55.15%, đổi sang JSON agent cùng thiết lập còn 33%. Code action cần ít hơn khoảng 30% số bước (theo CodeAct).
- **Takeaway:** với phép tính trên bảng (đếm, so sánh, cộng), gọi code hay pandas đáng tin hơn để model tự tính. Đây là "tool", không phải "thêm agent".

**H3. *CodeAgents + Structure*** (2025-05-28), https://huggingface.co/blog/structured-codeagent
- Ép output dạng JSON gồm thoughts và code giúp model mạnh thêm 2–7 điểm (GAIA, MATH, SimpleQA, Frames).
- Trong 15.724 trace, 2.4% gặp lỗi parse ở call đầu. Nhóm đó thành công 42.3%, nhóm không lỗi 51.3%. Lỗi đầu kéo theo chuỗi lỗi phía sau.
- **Structure tax:** model nhỏ (ví dụ Mistral-7B) không đồng thời xử lý được JSON, cú pháp Python và bài toán. Họ khuyến nghị structured output chỉ cho model khoảng 32B trở lên hoặc frontier. Qwen nhỏ cũng bị ảnh hưởng.
- **Takeaway:** các contract JSON giữa vai (ví dụ `src/contracts/`) đánh thuế trực tiếp lên 8B và 4B. Nên đo riêng tỉ lệ lỗi parse theo vai.

### 3.6 Google Research, *Towards a science of scaling agent systems*

Yubin Kim & Xin Liu, 2026-01-28; paper arXiv 2512.08296. https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/
- Thiết kế: 180 cấu hình, 5 kiến trúc (single agent, independent, centralized, decentralized, hybrid), 4 benchmark (Finance-Agent, BrowseComp-Plus, PlanCraft, WorkBench), 3 họ model (GPT, Gemini, Claude).
- Kết quả: centralized MAS **+80.9%** trên Finance-Agent (task song song hóa được). Trên PlanCraft (tuần tự), **mọi biến thể MAS kém hơn 39–70%**, vì overhead giao tiếp làm phân mảnh lập luận và không còn đủ "cognitive budget". Khi số tool tăng, chi phí điều phối tăng không tương xứng.
- Error amplification: independent MAS **17.2×**, centralized **4.4×**, vì orchestrator đóng vai "validation bottleneck".
- Có mô hình dự đoán kiến trúc tối ưu (R²=0.513) chọn đúng cho 87% cấu hình chưa thấy, dựa trên độ phân rã được và số tool.
- Blog phản bác niềm tin "càng nhiều agent càng tốt" (dẫn 2402.05120, 2406.07155).
- **Takeaway:** Open-ViTabQA thuộc loại tuần tự, ít tool, context nhỏ, tức vùng mà MAS thua. Nếu giữ nhiều vai thì dạng centralized (có bước kiểm tra tập trung) an toàn hơn các vai độc lập rồi gộp.

### 3.7 Chip Huyen, *Agents*

2025-01-07, https://huyenchip.com/2025/01/07/agents.html (trích từ sách *AI Engineering*)
- **Tách plan khỏi execute:** sinh plan, validate bằng heuristic (tool có tồn tại không, số bước có vượt ngưỡng không), rồi mới chạy. Bà viết rằng khi coi mỗi thành phần là một agent thì hầu hết agent đều là multi-agent, tức một bất đồng về định nghĩa.
- **Lỗi cộng dồn:** 95% mỗi bước qua 10 bước chỉ còn khoảng 60%, qua 100 bước khoảng 0.6%.
- Plan bằng ngôn ngữ tự nhiên cộng một "translator" dịch sang lệnh: dịch dễ hơn lập kế hoạch nên có thể giao cho model yếu hơn.
- Reflection có thể là self-critique hoặc một scorer riêng (Reflexion).
- Taxonomy lỗi: planning failure (tool không hợp lệ, tham số không hợp lệ, giá trị tham số sai, trượt mục tiêu, reflection tưởng đã xong nhưng chưa), tool failure (bao gồm lỗi translation), efficiency.
- Nhắc Chameleon: TabMWP (toán trên bảng) dùng bộ tool khác hẳn ScienceQA, và mỗi model có sở thích tool riêng.
- **Takeaway:** mỗi vai thêm vào là một hệ số nhân dưới 1 cho độ chính xác. Với 2–4 vai tuần tự trên 8B, xác suất thành công cả chuỗi giảm rõ rệt nếu không có bước kiểm tra tất định.

### 3.8 BAIR, *The Shift from Models to Compound AI Systems*

BAIR Blog (tác giả không trích), 2024-02-18, https://bair.berkeley.edu/blog/2024/02/18/compound-ai-systems/
- Hệ thống ghép nhiều thành phần thắng vì cải tiến bằng thiết kế thường rẻ hơn scaling (ví dụ AlphaCode sinh và lọc), vì hệ thống có thể động, kiểm soát được, và điều chỉnh được giữa chi phí và chất lượng.
- Thách thức: không gian thiết kế rộng, phân bổ budget giữa các thành phần, **cần đồng tối ưu** các thành phần (DSPy tối ưu prompt và few-shot cho từng module theo metric end-to-end). FrugalGPT định tuyến theo budget.
- **Takeaway:** nếu giữ pipeline nhiều bước thì các bước cần được tối ưu *cùng nhau* theo EM/F1 cuối, không tối ưu riêng từng vai.

### 3.9 Lilian Weng, *LLM Powered Autonomous Agents*

2023-06-23, https://lilianweng.github.io/posts/2023-06-23-agent/
- Ba thành phần: planning (decomposition, reflection), memory, tool use. Case study: ChemCrow, Generative Agents.
- Thách thức: planning dài hơi và **độ tin cậy của giao diện ngôn ngữ tự nhiên**. Model hay lỗi format, nên phần lớn code demo là để parse output.
- **Takeaway:** lỗi parse giữa các vai là vấn đề đã biết từ 2023. Với 8B, rủi ro này còn cao hơn (xem H3).

### 3.10 Hamel Husain & Shreya Shankar, *AI Evals FAQ*

Xuất bản 2026-09-18, sửa 2026-09-21, tài liệu sống. https://hamel.dev/blog/posts/evals-faq/
- Pipeline nhiều bước: log toàn bộ, **chỉ annotate lỗi đầu tiên ở upstream** vì lỗi phía sau thường là hệ quả. Dùng **transition failure matrix**: hàng là trạng thái thành công cuối, cột là nơi lỗi đầu tiên xảy ra. Ví dụ text-to-SQL: GenSQL→ExecSQL chiếm 12 lỗi.
- Cải thiện ở tầng đầu có tác động lớn hơn vì lỗi lan trong chuỗi LLM.
- Chấm nhị phân pass/fail thay vì thang Likert. Các chỉ số tương đồng chung (BERTScore, ROUGE) phần lớn vô dụng.
- Dùng cùng model làm judge thường chấp nhận được nếu judge làm phân loại nhị phân hẹp và được kiểm tra TPR/TNR với nhãn người. Chỉ đưa cho judge phần trace nó cần, vì thừa context thì judge kém đi.
- **Takeaway:** trước khi thêm vai, dựng transition matrix trên các trace hiện có để biết lỗi nằm ở vai nào.

### 3.11 Eugene Yan, *Evaluating Long-Context Question & Answer Systems*

Ngày không hiện trên trang; theo thứ tự trang Writing thì khoảng 2025. https://eugeneyan.com/writing/qa-evals/
- Hai trục độc lập: **faithfulness** (chỉ dựa vào tài liệu) và **helpfulness**.
- Nhãn cho câu không có thông tin: trả lời sai hoặc bịa, **từ chối sai** (thông tin có nhưng model nói không có), từ chối đúng.
- Chỉ số chồng token (ROUGE) tương quan kém với đánh giá của người trên Q&A, và thiên vị câu trả lời dài.
- **Takeaway:** với 4.5% câu không trả lời được, cần đếm riêng từ chối đúng và từ chối sai. Một "verifier" hay "abstainer" quá bảo thủ sẽ làm tăng từ chối sai trên 95.5% câu còn lại.

### 3.12 Philipp Schmid, *Single vs Multi-Agent System?*

2025-06-20, https://www.philschmid.de/single-vs-multi-agents
- Bảng so sánh: single agent phù hợp task tuần tự, phụ thuộc trạng thái ("viết"), còn MAS phù hợp task song song, khám phá ("đọc"). Nhắc lại con số 4× và 15× token của A2.
- Task hỗn hợp nên tách pha đọc và pha viết trong kiến trúc. Đừng over-engineer vì model tiến bộ nhanh.
- **Takeaway:** tách "đọc bảng" khỏi "viết câu trả lời", còn phần viết nên là một bước.

### 3.13 Nathan Lambert (Interconnects), *Use multiple models*

2026-01-11, https://www.interconnects.ai/p/use-multiple-models
- Model "jagged" theo những cách khác nhau. Khi một model kẹt, chuyển cùng câu hỏi sang một model ngang hàng thường gỡ được.
- Lập luận: đổi model chỉ thường xuyên thành công nếu *mỗi* model đã có xác suất thành công khá cao. Nếu xác suất thấp thì đổi gần như luôn thất bại.
- Tác giả cho biết model open-weight chưa gần các model frontier trong trải nghiệm của ông.
- **Takeaway:** đa dạng thật đến từ *model khác nhau* chứ không từ persona của cùng model. Chỉ đáng thử khi mỗi backbone (Qwen3-8B, SEA-LION 8B, Gemma-3-4B) đều đủ mạnh trên câu đó.

### 3.14 Agent cho structured data và text-to-SQL

**GC. Google Cloud, *Techniques for improving text-to-SQL*** (Per Jacobsson, 2025-05-17), https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql
- Ba vấn đề chính: context nghiệp vụ, ý định người dùng mơ hồ, giới hạn khi sinh (sai chi tiết dialect).
- Kỹ thuật: retrieval bảng và cột, few-shot theo nghiệp vụ, **disambiguation** (trước hết kiểm tra câu hỏi có trả lời được với schema không, nếu không thì hỏi lại), **validation bằng cách không dùng AI** (parse, dry-run) rồi reprompt kèm lỗi, **self-consistency** qua nhiều prompt hoặc biến thể model.
- **Takeaway:** "vai kiểm tra" có giá trị nhất khi tín hiệu tất định, ví dụ đáp án có khớp một ô trong bảng không, hay phép tính có tái tạo được bằng code không.

**SF. Snowflake, *Real-Time Text2SQL Behind Snowflake Intelligence*** (Borchmann et al., 2025-11-04), https://www.snowflake.com/en/blog/engineering/real-time-text-to-sql-snowflake-intelligence/
- Arctic-Text2SQL-R1.5 là một model reasoning chuyên biệt, train SFT rồi GRPO với **reward là kết quả thực thi**. Đạt execution accuracy 45% so với 44% của Sonnet 4.5 trên benchmark nội bộ Snowflake, và nhanh hơn tới 3× với các mẫu query đã được verify.
- Orchestrator chọn độ sâu reasoning động: câu giống câu đã verify thì bỏ qua reasoning sâu, câu mới thì dùng đủ.
- **Takeaway:** hướng của practitioner cho model nhỏ là *chuyên biệt hóa một model* (RL với reward kiểm chứng được) cộng một router quyết định độ sâu reasoning, không phải thêm nhiều agent.

**UB. Uber, *QueryGPT*** (Khune, Busch, Johnson et al., 2024-09-19), https://www.uber.com/en-US/blog/query-gpt/
- Kiến trúc: intent agent (ánh xạ câu hỏi sang domain), table agent (chọn bảng, người dùng xác nhận), column-prune agent (cắt cột thừa để giảm token), rồi sinh SQL.
- Bài học: "LLMs are excellent classifiers". Mỗi agent tốt vì chỉ làm *một đơn vị việc hẹp*. Ảo giác cột và bảng vẫn chưa giải được. Họ định thêm validation agent.
- Eval: luồng *Vanilla* so với *Decoupled* (đưa intent và bảng đúng từ oracle vào để đo từng thành phần độc lập). Chỉ số: intent, table overlap, chạy được hay không, có output hay không (bắt được lỗi bịa giá trị filter), độ tương đồng do LLM chấm. **Họ không ra quyết định dựa trên dao động khoảng 5% giữa các lần chạy.**
- **Takeaway:** "agent" hiệu quả trong production thực chất là các bước phân loại hay lọc hẹp trong một workflow. Kỹ thuật eval decoupled bằng oracle là cách quy trách nhiệm cho từng vai của POMA.

---

## 4. Heuristic thiết kế cho pipeline 8B, bảng nhỏ, câu trả lời tự do tiếng Việt

Các heuristic dưới đây rút từ nguồn và đi kèm cơ chế. Đây không phải đề xuất dự án. Mỗi heuristic ghi nguồn và mức độ bằng chứng có khớp điều kiện POMA hay không.

### 4.0 Bằng chứng thực sự đo trên model ≤10B (hoặc gần mức đó)

| Bằng chứng | Model | Task | Kết quả |
|---|---|---|---|
| R2 Raschka | gemma4:e2b; Qwen3.6-35B-A3B (khoảng 3B active) | 5 task phán đoán tool-call | 0/5; 3/5, lỗi ở chọn tool hay bước chứ không ở format |
| H3 HF structure tax | Mistral-7B (ví dụ), Qwen nhỏ | CodeAgent + JSON | Model nhỏ bị lỗi cú pháp khi phải xử lý đồng thời nhiều cấu trúc |
| SF Snowflake / Arctic-R1 (2505.20315, qua search) | 7B | Text2SQL với RL execution reward | 7B vượt các hệ 70B-class trước đó (theo tóm tắt WebSearch, chưa mở arXiv) |
| R8 "A Sober Look" | model distill nhỏ | Toán | Nhiễu seed lệch vài điểm phần trăm |

Mọi con số khác (+90.2%, 15×, +81% hay −70%, 17.2×, 55% so với 33%) đều đo trên frontier model và task agentic dài.

### 4.1 Heuristic

1. **Task tuần tự và context nhỏ thì mặc định dùng một luồng.** Google (G1) thấy mọi biến thể MAS thua 39–70% trên task tuần tự. Lý do MAS thắng ở Anthropic và Cognition là context tràn và cần song song, trong khi bảng p50 khoảng 650 token không bao giờ tràn. *Khớp với POMA:* kết quả "single few-shot + finalizer thắng pipeline nhiều vai" phù hợp với dự đoán của G1.
2. **So sánh ở cùng compute.** Theo A2, token giải thích 80% phương sai. Mọi cấu hình nhiều vai phải so với self-consistency hoặc best-of-N của cùng một prompt tốt nhất *ở cùng số call hoặc token* (R3, R4, GC). Nếu không làm vậy thì "gain" có thể chỉ là compute.
3. **Không diễn đạt lại đáp án ở bước cuối.** LangChain (L2) đo được mất điểm do "translation" ở supervisor và sửa bằng `forward_message`. Anthropic dùng artifact hay filesystem để tránh "telephone". Cognition kể lại thất bại của edit-apply model. *Áp vào POMA:* với khoảng 43% đáp án là một ô nguyên văn, bước cuối nên *chọn hoặc chép* span (hay ô) từ output trước, không sinh lại. Cần đo tỉ lệ finalizer biến một đáp án đúng ở upstream thành sai.
4. **Bước hẹp dạng phân loại hay định tuyến là nơi LLM sub-call phát huy tốt nhất.** Bằng chứng: Uber với intent, table và column-prune; Anthropic routing; Raschka với router effort (R6). *Áp vào POMA:* khoảng 91% câu có đúng một nhãn reasoning-type, nên routing sang few-shot hoặc cách biểu diễn theo loại là một *workflow* hợp chuẩn. Điều kiện của A1 là bộ phân loại phải đủ chính xác, nên cần đo accuracy của router trước.
5. **Kiểm tra tất định tốt hơn critic LLM.** Bằng chứng: GC (parse, dry-run), A1 (ground truth từ môi trường), S* trong R4, HH (dùng code assertion cho gì khách quan). Với bảng, các kiểm tra rẻ gồm: đáp án có khớp nguyên văn hay chuẩn hóa một ô không; phép đếm hay tổng có tái tạo được bằng code hay pandas không (H2: code action tốt hơn JSON). Evaluator-optimizer chỉ nên dùng khi tiêu chí rõ (A1).
6. **Giảm "structure tax" giữa các vai.** H3 cho thấy model nhỏ mất điểm khi phải sinh JSON phức tạp, LW nêu giao diện ngôn ngữ tự nhiên kém tin cậy, A1 khuyên giữ format gần văn bản tự nhiên. Nên đo tỉ lệ lỗi parse theo vai. Lỗi ở call đầu kéo theo chuỗi lỗi (H3: 42.3% so với 51.3%).
7. **Luồng điều khiển nằm trong code, không giao cho 8B.** R2 cho thấy model nhỏ phán đoán kém "làm gì tiếp theo". Smolagents (H1) khuyên chọn mức agency thấp nhất đủ dùng. Anthropic (A2) phải ghi hẳn quy tắc scale effort vào prompt ngay cả với frontier model.
8. **Đa dạng thật đến từ model hoặc biểu diễn khác nhau, không từ persona.** NL: chuyển sang model ngang hàng chỉ giúp khi mỗi model đã đủ mạnh. GC: self-consistency qua nhiều prompt hoặc biến thể model. Cognition: debate chưa đáng tin hơn một agent. *Khớp với POMA:* persona debate cùng backbone không giúp. Nếu thử đa dạng thì dùng các backbone hoặc biểu diễn bảng khác nhau, nhưng lưu ý Gemma-3-4B có thể kéo điểm vote xuống.
9. **Dùng núm "thinking" trước khi thêm agent.** R6 mô tả Qwen3 có công tắc bật/tắt thinking và budget cứng. Effort tăng thì độ chính xác tăng nhưng lợi ích giảm dần. Chọn effort tự động còn khó, nên nếu định tuyến thì dùng tín hiệu rõ như reasoning-type.
10. **Chất lượng context trước số vai.** R1 cho rằng "chất lượng model" phần lớn là chất lượng context, tức biểu diễn bảng, chọn few-shot, cắt nhiễu (Uber column-prune). Ngược lại, A2 thấy nâng model lợi hơn nhân đôi token. Đây là căng thẳng chưa ngã ngũ.
11. **Tối ưu các bước cùng nhau theo metric cuối.** B1 (DSPy) cho rằng nếu giữ nhiều bước thì prompt và few-shot của từng bước nên được chọn theo EM/F1 end-to-end.
12. **Quy trách nhiệm theo thành phần trước khi thiết kế thêm.** Các công cụ: Uber *decoupled eval* (đưa đầu vào đúng từ oracle cho từng vai); Hamel ghi lỗi đầu tiên ở upstream và *transition failure matrix*; Eugene Yan tách từ chối đúng và từ chối sai cho 4.5% câu không trả lời được.
13. **Tôn trọng nhiễu.** Uber bỏ qua dao động khoảng 5% giữa các lần chạy; R8 cho thấy nhiễu seed; POMA có ngưỡng khoảng 2 EM trên 992 câu. Nên dùng kiểm định cặp hoặc nhiều seed, không so một lần chạy.
14. **Judge free-form phải được kiểm tra với nhãn người.** HH cho phép cùng model làm judge nếu TPR/TNR tốt. A2 thấy một judge call đơn nhất quán hơn nhiều judge. R7 lưu ý judge phụ thuộc năng lực và bias style.

---

## 5. Paper tìm thấy qua blog (cho agent khảo sát paper)

ID được ghi khi thấy trực tiếp trên trang đã mở; ngoại lệ được đánh dấu.

**Multi-agent: khi nào giúp hay hại**
- *Towards a Science of Scaling Agent Systems*: **2512.08296** (G1)
- *More Agents Is All You Need*: **2402.05120** (G1)
- Link có chữ "collaborative scaling research": **2406.07155** (G1; tên đầy đủ không có trên trang đã mở, chưa xác minh)
- Benchmark dùng trong G1: BrowseComp-Plus **2508.06600**, PlanCraft **2412.21033**, WorkBench **2405.00823**
- *Polar: Agentic RL on Any Harness at Scale*: **2605.24220** (R2; model nhỏ Qwen3.5-4B theo harness)

**Tool, code action, format**
- *Executable Code Actions Elicit Better LLM Agents* (CodeAct): **2402.01030** (H1, H2)
- *DynaSaur*: **2411.01747**; *If LLM Is the Wizard, Then Code Is the Wand*: **2401.00812** (H1)
- Chameleon (Lu et al., 2023): dùng TabMWP (toán trên bảng). Nhắc trong CH, ID không hiện trên trang.

**Inference-time scaling (danh sách của Raschka, R4)**
- *Scaling LLM Test-Time Compute Optimally…*: **2408.03314**
- s1: **2501.19393**; TPO: **2501.12895**; Underthinking: **2501.18585**; Self-Backtracking: **2502.04404**; Recurrent depth: **2502.05171**
- *Can 1B LLM Surpass 405B LLM?*: **2502.06703** (compute-optimal cho model nhỏ)
- *Inference-Time Computations for LLM Reasoning and Planning: A Benchmark*: trên trang, link trùng với mục #9 (2502.12521), nên **ID chưa xác định**
- S*: **2502.14382**; Chain of Draft: **2502.18600**; *Dedicated Feedback and Edit Models*: **2503.04378**
- Zero-shot CoT: **2205.11916**

**RL và model nhỏ (R8, R9)**
- *RL for Reasoning in Small LLMs: What Works and What Doesn't*: **2503.16219**
- *A Sober Look at Progress in LM Reasoning*: nhắc trong R8, ID không nằm trong đoạn đã trích
- Phần đọc được của danh sách 2025 H1: RL Tango **2505.15034**, Enigmata **2505.19914**, RLVR Implicitly Incentivizes Correct Reasoning **2506.14245**, Meta-CoT **2501.04682**, Lessons of PRMs **2501.07301**, LIMO **2502.03387**

**Structured data và table**
- *Arctic-Text2SQL-R1: Simple Rewards, Strong Reasoning in Text-to-SQL*: **2505.20315** (thấy qua WebSearch, không mở trang arXiv; Findings ACL 2026)
- Reflexion **2303.11366**, Tree of Thoughts **2305.10601** (LW)

---

## 6. Không xác minh được hoặc hạn chế

- **Raschka, phần bị paywall:** *Categories of Inference-Time Scaling* (chỉ đọc intro và mục lục), danh sách 2026 (mục "Agent Systems and Tool Use" chỉ thấy tiêu đề), danh sách 2025 H1 (cắt ở mục 1b), danh sách 2025 H2 (chỉ thấy danh mục). Có thể có paper table-QA hay multi-agent nằm trong các phần này. Không đăng ký hay đăng nhập.
- **Trong các phần đọc được của Raschka không có paper table-QA nào.**
- **Chỉ thấy qua WebSearch, không mở:** TableZoomer (Springer *Vicinagearth*, 2025; kết quả search nói có thí nghiệm với Qwen3-8B), *Interpretable LLM-based Table QA* (POS, 2412.12386), *Can AI Agents Answer Your Data Questions? A Benchmark for Data Agents* (2603.20576), Snowflake *Agentic Semantic Model Improvement*, Interconnects *Get Good at Agents* và *The AI Agent Spectrum*. ID Arctic-R1 2505.20315 cũng lấy từ kết quả search.
- **Eugene Yan:** trang không hiện ngày đăng.
- **Hamel FAQ:** là tài liệu sống, nội dung có thể đổi sau 2026-09-21.
- **Chuyển hướng URL:** cognition.ai sang cognition.com; blog.langchain.com sang www.langchain.com/blog/...; uber.com/blog/query-gpt sang uber.com/us/en/blog/query-gpt/ (link gốc /blog/query-gpt/ báo 404 theo vùng). Nội dung được đọc từ URL đích.
- **Mở rộng số liệu sang POMA:** A2, G1, L2, H2 và H3 dùng frontier model hoặc gpt-4o trên task agentic nhiều bước. Việc áp các con số này vào QA một bảng nhỏ với 8B là suy luận, không phải bằng chứng trực tiếp.
- **Không tìm được** blog practitioner nào báo cáo riêng về *table QA free-form trên model ≤10B* bằng multi-agent. Các bài gần nhất đều là text-to-SQL (Google Cloud, Snowflake, Uber).
