# Table QA frontier: phương pháp chuyển được sang Vietnamese Table QA

Ngày kiểm chứng: **01/10/2026**. Phạm vi ưu tiên: suy luận không cập nhật trọng số, Qwen3-8B và GPT-4o-mini. Đây là nghiên cứu tài liệu; không phải kết quả chạy lại. Khảo sát 26/09 trong repo chỉ được dùng để tìm đầu mối. Các số dưới đây đọc từ nguồn sơ cấp mới trong lượt này.

## 1. Mười hai công trình ưu tiên và mức độ chuyển giao

| Công trình và trạng thái đã kiểm chứng | Cơ chế | Có phù hợp inference-only? | Bằng chứng và giới hạn đáng chú ý |
|---|---|---|---|
| **Binder — Binding Language Models in Symbolic Languages**, ICLR 2023 camera-ready | Chèn lời gọi LLM vào chương trình SQL/Python cho phần ngữ nghĩa khó biểu diễn bằng chương trình | **Có**: few-shot, không training riêng | Dùng Codex. Giá trị chuyển giao là phân công ngữ nghĩa cho LLM, phép toán cho executor; chưa có bằng chứng trực tiếp Qwen3-8B hay tiếng Việt trong nguồn đã đọc. [Paper](https://arxiv.org/abs/2210.02875), [code chính chủ](https://github.com/xlang-ai/Binder). |
| **DATER — Large Language Models are Versatile Decomposers**, SIGIR 2023 | Phân rã bảng và câu hỏi; parsing–execution–filling tách tính toán khỏi lý luận | **Có** | Hữu ích khi bằng chứng phân tán hoặc bảng lớn; chọn nhầm hàng/cột có thể mất bằng chứng. Không suy từ thành tích Codex sang Qwen3. [Paper](https://arxiv.org/abs/2301.13808), [ACM proceedings](https://doi.org/10.1145/3539618.3591708). |
| **Chain-of-Table**, ICLR 2024 | LLM chọn thao tác; executor cập nhật bảng trung gian; bước sau nhìn kết quả bước trước | **Có**: paper nói in-context learning | Một phương pháp agentic một LLM; không tự động thành multi-agent chỉ vì có nhiều bước. Phù hợp làm đối chứng phân rã/thao tác bảng. [Paper hội nghị](https://proceedings.iclr.cc/paper_files/paper/2024/file/f53fd88a4340063ecd258c0ae9948b40-Paper-Conference.pdf), [code](https://github.com/google-research/chain-of-table). |
| **Tab-PoT — Efficient Prompting for LLM-based Generative Internet of Things**, IEEE IoT Journal; online 2024, bản tập 12(1) năm 2025 | Planning → Python execution → correction; dùng demonstrations liên quan | **Có** | Tên paper không phải “Tab-PoT”. Là baseline sát với plan–code–repair. Không thể tuyên bố pipeline ba bước là đóng góp mới. [arXiv và DOI tạp chí](https://arxiv.org/abs/2406.10382), [bản tác giả trong kho MBZUAI](https://irep.mbzuai.ac.ae/server/api/core/bitstreams/85e91d12-f0a5-4af1-b87b-22cc39da9747/content). |
| **TableZoomer**, Vicinagearth 2025 | Schema gọn → chọn cột/link entity → PoT → ReAct | **Có** | **Qwen3-8B thinking**, DataBench: 67,82 → 87,16; TableBench numeric 54,41 → 66,25. Đây là điểm phần trăm, không phải mức tăng tương đối; không phải Vietnamese QA. Baseline PoT chưa được cân bằng token. [Tạp chí chính thức](https://link.springer.com/article/10.1007/s44336-025-00016-x), [toàn văn, bảng 2–6](https://arxiv.org/html/2509.01312v1). |
| **TALON**, EMNLP 2025 | Planner gọi tool để thăm dò bảng theo feedback; critic kiểm tra thao tác và kế hoạch | Chuyển được cơ chế suy luận; không có training được nêu trong abstract | Đích là **50 đến hơn 10.000 hàng**; lợi ích này không mặc định áp dụng cho bảng nhỏ. Cần đọc setup chi tiết trước khi khẳng định hiệu quả 8B. [ACL chính thức](https://aclanthology.org/2025.emnlp-main.1393/), [code](https://github.com/Wwestmoon/TALON). |
| **TABGR — Beyond Linearization: Attributed Table Graphs for Table Reasoning**, arXiv v2 ngày 27/08/2026; lab tác giả ghi EMNLP 2026, chưa xác minh proceedings | Đồ thị hàng–cột–ô; question-guided PageRank ưu tiên triples; reasoning path gắn bằng chứng | **Có**, training-free | GPT-4o-mini WikiTQ 77,1 vs RoT 74,2. Llama3.1-8B 64,2 vs RoT 63,7: gain nhỏ ở 8B. Kháng xáo trộn là điểm đáng thử; graph phẳng chưa giải quyết đầy đủ merged header. [Paper v2, kết quả 8B ở bảng 19](https://arxiv.org/html/2601.08444v2), [trang lab](https://www.raids-lab.com/publications/wang2026beyond/). |
| **MATA**, Findings ACL 2026 | CoT/PoT/SQL + debug; scheduler và confidence checker tiết kiệm calls | **Không hoàn toàn** | Scheduler MobileBERT+MLP **đã train**; Confidence Checker DeBERTaV3-large **fine-tuned**; Format Matcher 0,5B không tune. Có thể thay controller bằng rule nhưng đó là biến thể cần đánh giá mới. [ACL](https://aclanthology.org/2026.findings-acl.1672.pdf), [toàn văn mục 3](https://arxiv.org/html/2602.09642v2). |
| **CRAFT — A Unified Counterfactual Reasoning Framework for Tabular Question Answering and Fact Verification**, preprint 05/06/2026 | Rewriter/Reverser/Extractor/Rethinker; xét claim và counterfactual; tích hợp trong Table-Critic | **Có** theo phương pháp đã đọc | Nhỏ nhất open backbone **14B**, không có 8B. So SC-3/CW-3 chưa chứng minh token-matched. Appendix C: weighted tokens WikiTQ CRAFT c=1 37,1M vs Table-Critic 20,3M. Counterfactual challenge đã có tiền lệ rất gần. [Method/appendix](https://arxiv.org/html/2606.06842v1). |
| **ODUTQA-MDC / MAIC-TQA**, ACL 2026 | Nhận diện câu hỏi thiếu xác định, hỏi làm rõ, lấy bảng rồi SQL | Hướng chuyển giao suy luận; **chưa kiểm tra toàn bộ training protocol** | Benchmark có 209 bảng, 25.105 QA và simulator phản hồi. Mở hướng conversational Vietnamese QA; cần tách với fixed single-turn benchmark. Không coi simulator là người thật. [ACL chính thức](https://aclanthology.org/2026.acl-long.499/). |
| **RePo — Language Models with Context Re-Positioning**, ICML 2026 | Module học vị trí token phi tuyến; continual pretraining trên OLMo-2 1B/7B | **Không** | Là thay đổi kiến trúc/huấn luyện, không phải đơn giản xếp lại dòng bằng prompt. Chỉ chuyển được giả thuyết “cấu trúc/vị trí có ảnh hưởng”; không thể ghép nguyên bản vào API GPT-4o-mini. [PMLR chính thức](https://proceedings.mlr.press/v306/li26jq.html). |
| **Table-R1 — Inference-Time Scaling for Table Reasoning Tasks**, EMNLP 2025 | Distillation reasoning traces hoặc RLVR/GRPO | **Không** với backbone nguyên bản | “Inference-time scaling” trong tiêu đề không có nghĩa không train: hai chiến lược đều post-training. Checkpoint công bố có thể là đối chứng riêng; không dùng score để dự đoán Qwen3-8B chưa tune. [ACL chính thức](https://aclanthology.org/2025.emnlp-main.1040/), [code/training scripts](https://github.com/Table-R1/Table-R1). |

## 2. Phát hiện mới cần ưu tiên hơn thêm một critic

### 2.1 Chuyển tác vụ từ đọc chuỗi sang grounding cấu trúc

**Đề xuất nghiên cứu của người khảo sát**, chưa phải kết luận của paper: xây header-path và cell-ID từ HTML, để một agent chọn đường header/ô, một agent độc lập lập ràng buộc câu hỏi rồi kiểm tra chúng trên cùng dữ liệu. Hai vai tạo tín hiệu khác nhau thay vì đọc cùng prompt với hai persona.

Với bảng nhỏ, bắt đầu bằng danh sách cạnh/header-path; chưa cần graph database hay GNN. Đánh giá phần grounding trước: đúng ô nhưng sai đáp án khác với chọn sai ô. So sánh 4 cấu hình: bảng gốc; chỉ đổi biểu diễn; biểu diễn + grounding; biểu diễn + grounding + challenge. Chỉ giữ graph traversal nếu vượt baseline cùng ngân sách.

### 2.2 Challenge có mục tiêu, không chỉ “hãy kiểm tra lại”

**Giả thuyết mở**: chọn một kiểm tra dựa trên constraint của câu hỏi: phạm vi năm, đơn vị, điều kiện lọc, tính duy nhất của cực trị, hoặc cột con dưới merged header. Agent challenge nhìn bảng và constraint trước khi xem đáp án ban đầu để giảm anchoring; nếu có vi phạm xác định thì cho một lần repair.

Không tuyên bố counterfactual verification là mới: CRAFT đã làm việc rất gần. Điểm khác cần chứng minh là kiểm tra có chứng cứ cấp ô/header, controller không train và ngân sách nhỏ trên tiếng Việt. Cần baseline CRAFT rút gọn, generic critic và self-consistency với cùng số calls **và** báo tokens.

### 2.3 Chuẩn hoá có bảo toàn nguồn

**Đề xuất**: lưu đồng thời raw value, parsed value, unit và cell-ID; phép toán dùng parsed value, lời đáp bám raw/evidence. Các trường hợp Việt cần kiểm tra gồm “1.234,5”, phần trăm, nghìn/triệu/tỷ, quý/năm, footnote và “—”. Không mặc định dấu chấm luôn là phân cách nghìn: xác định theo cột/bảng, và giữ trạng thái chưa rõ thay vì ép số.

Đối chứng phải có phiên bản chuẩn hoá mà không multi-agent; nếu lợi chỉ đến từ parse số/format đáp án thì gọi đúng tên đóng góp.

### 2.4 Tách thiếu bằng chứng khỏi câu hỏi mơ hồ

**Đề xuất**: nhãn “không đủ dữ liệu” khác “cần hỏi rõ năm/đơn vị/tiêu chí”. Với single-turn dataset, đánh giá abstention trên tập chẩn đoán riêng; với sản phẩm hội thoại, dùng một câu hỏi làm rõ có mục tiêu. Không biến ground-truth thiếu hoặc lỗi annotation thành unanswerable tự động.

## 3. Chú ý tên gọi và claim dễ sai

- **Table-Critic** đã có ACL 2025, bốn vai Judge/Critic/Refiner/Curator và cây template kinh nghiệm; do đó “multi-agent sửa từng bước” đã là phương pháp có trước. [Paper ACL](https://aclanthology.org/2025.acl-long.853.pdf).
- **MAPLE** đã xuất bản ở **ALTA 2025**, không chỉ preprint. Solver/Checker/Reflector/Archiver là workflow rất gần reflection + memory. Chưa audit code memory leakage trong lượt này, nên không coi nhận định rò rỉ ở khảo sát cũ là đã chứng minh. [ACL proceedings](https://aclanthology.org/2025.alta-main.10.pdf).
- **ReAcTable** là framework ReAct cho TQA, có SQL/Python/answer và voting; paper phân biệt rõ training/non-training baselines. Không suy rằng nhiều công cụ là nhiều LLM agents. [PVLDB 17, paper chính thức](https://www.vldb.org/pvldb/vol17/p1981-zhang.pdf).
- **CoAgt**: truy cập trực tiếp PeerJ thất bại trong lượt này; chỉ tìm thấy bản mirror và thông tin đã có trong repo. Không dùng score 85,4/96,6 làm bằng chứng mới đã kiểm chứng sơ cấp. Đặc biệt không chuyển score GPT-4o sang GPT-4o-mini hay Qwen3. [URL tạp chí cần kiểm tra thêm](https://peerj.com/articles/cs-3423/).
- **MAS-TQA**: chưa tìm được nguồn sơ cấp theo tên chính xác qua các biến thể truy vấn; không coi đây là tên paper đã xác minh. Có thể là tên mô tả nội bộ.
- **Plan-of-Thought/POT/POMA**: thuật ngữ dễ lẫn với **Program-of-Thoughts (PoT)**, **Plan-of-SQLs (POS)** và **PoTable**. Chưa xác minh một paper riêng có đúng title “Plan-of-Thought” dành TQA trong lượt này; POMA là hệ trong repo, không tự gắn venue.
- **Table-R1** trùng tên: ngoài bản Yang et al. còn **Region-based Reinforcement Learning for Table Understanding** [2505.12415](https://arxiv.org/abs/2505.12415) và **Table-r1: Self-supervised and Reinforcement Learning for Program-based Table Reasoning in Small Language Models** [2506.06137](https://arxiv.org/abs/2506.06137). Đều cần training; không trộn tác giả và kết quả.
- **Reasoning by Commented Code for Table Question Answering** là preprint 2026 có ý tưởng prompt chuyển được, nhưng có bước tạo dữ liệu SFT và selector train. **70,9 là Fuzzy Match** của Qwen2.5-Coder-7B; **84,3** là hệ ghép code model + Table-R1 + selector Qwen3-4B, không phải raw Qwen3-4B. [Mục 3.2–4.7](https://arxiv.org/html/2602.00543v1).
- Có **hai CRAFT khác nhau**: bản counterfactual ở trên và **CRAFT: Training-Free Cascaded Retrieval for Tabular QA** ACL 2026. Không trộn citation; bản retrieval phù hợp open-domain/multi-table hơn closed-table QA. [ACL long.149](https://aclanthology.org/2026.acl-long.149/).

## 4. Bộ thí nghiệm tối thiểu để quyết định hướng

1. Baseline tốt nhất hiện có + cùng chuẩn hoá đầu vào/đáp án; chạy riêng Qwen3-8B và GPT-4o-mini.
2. Candidate approach với trần calls rõ: grounding độc lập → solve → chỉ một challenge khi có dấu hiệu → tối đa một repair. Báo tokens/calls/latency, không chỉ accuracy.
3. Ablation biểu diễn, parser số, constraint grounding, challenge và repair; giữ constant demonstrations và formatter.
4. Chẩn đoán nhỏ: merged header, locale số/đơn vị, nhiều điều kiện, phủ định, thiếu dữ liệu, order-sensitive. Có nhóm clean để đo tỷ lệ làm hỏng câu đang đúng.
5. Robustness bằng phép biến đổi bảo toàn nghĩa: đổi thứ tự hàng/cột **chỉ khi câu hỏi không phụ thuộc thứ tự**, format số tương đương, thay cách diễn đạt tiếng Việt. Chấm consistency cùng correctness; consistency sai vẫn là sai.
6. Cell/header evidence precision/recall trên subset có annotation; correction rate, degradation rate; paired bootstrap/McNemar trên câu hỏi dùng chung. Không chọn hyperparameter bằng test gold; memory/demonstrations chỉ từ train/dev.

Khuyến nghị: bắt đầu **grounding cấu trúc + kiểm tra ràng buộc độc lập có mục tiêu**, giữ program execution cho câu số học. Xem đây là giả thuyết cần kiểm chứng; bằng chứng 8B hiện nay hỗ trợ khả năng chuyển giao, chưa đảm bảo lợi trên tiếng Việt.
