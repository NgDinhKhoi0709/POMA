# Hướng nghiên cứu Vietnamese Table QA bằng multi-agent, không huấn luyện

Ngày khảo sát: **01/10/2026**. Backbone dự kiến: **Qwen/Qwen3-8B** và **GPT-4o mini**.

Đây là khảo sát có chọn lọc từ nguồn sơ cấp, không phải systematic review bao phủ mọi công trình. Ba subagent khảo sát Table QA, hướng chuyển giao và giao thức tiếng Việt; báo cáo này tổng hợp và đối chiếu với POMA. Các đề xuất dưới đây **chưa được thực nghiệm trong lượt làm việc này**. Số liệu paper là kết quả do tác giả báo cáo; số liệu lịch sử trong repo chưa được tái chạy.

## 1. Khuyến nghị chính

Ưu tiên nghiên cứu **hai agent có nhiệm vụ khác nhau: một agent trả lời, một agent độc lập kiểm tra cách ánh xạ từng điều kiện của câu hỏi vào cấu trúc bảng**, sau đó trao đổi tối đa một vòng bằng bằng chứng cụ thể. Giữ trọng tâm ở grounding và coverage: đúng ô chưa đủ; cần đúng hàng, đúng nhánh header, đúng điều kiện và đủ các phần tử cần trả lời.

Thử ba cơ chế riêng trước khi ghép thành hệ lớn:

1. **Kiểm chứng điều kiện và bằng chứng có cấu trúc**: hướng thực dụng nhất để bổ sung POMA/MemXam.
2. **Phối hợp qua quan hệ hàng–cột–ô và đường dẫn header**: hướng phù hợp bảng tiếng Việt có ô gộp; lấy cảm hứng TabGR và TableZoomer.
3. **Kiểm chứng phản thực tế hoặc metamorphic có điều kiện**: hướng nghiên cứu đáng thử, nhưng rủi ro và chi phí cao hơn; phải đối chiếu CRAFT, DPC và SQLHD.

Adaptive routing là cơ chế quản lý ngân sách dùng cho các hướng trên, không tự nó chứng minh đóng góp mới. Bảng dài và hỏi đáp làm rõ mơ hồ là hai hướng phụ, phù hợp khi mở rộng phạm vi dữ liệu.

**Không hứa mức tăng EM.** Literature có bằng chứng trên 7B/8B hoặc GPT-4o mini cho một số cơ chế, nhưng chưa xác lập lợi ích của chính hệ đề xuất trên Vietnamese Table QA.

## 2. Những công trình nên đọc và cách dùng

### 2.1. Grounding, biểu diễn và thực thi

- **Chain-of-Table — ICLR 2024.** LLM sinh thao tác, công cụ biến đổi bảng, bảng trung gian trở thành trạng thái suy luận. Dùng in-context learning, không phải một phương pháp buộc fine-tune. Học cách truyền kết quả có cấu trúc giữa các bước; nguyên bản không đủ để kết luận đóng góp của multi-agent. [Paper](https://proceedings.iclr.cc/paper_files/paper/2024/file/f53fd88a4340063ecd258c0ae9948b40-Paper-Conference.pdf), [code chính chủ](https://github.com/google-research/chain-of-table).

- **TableZoomer — 2025, bài báo trên Vicinagearth.** Phối hợp schema, chọn cột, entity linking, PoT và ReAct. Có bằng chứng trực tiếp Qwen3-8B thinking trên DataBench: accuracy 67,82 → 87,16; ablation cho thấy schema và zooming đóng góp lớn hơn bước ReAct cuối. Đây là kết quả trên benchmark khác, không phải mức tăng dự kiến của Open-ViTabQA. Học grounding theo truy vấn, nhưng luôn bảo toàn cột điều kiện và khả năng quay lại bảng gốc. [Bài báo và bảng ablation](https://link.springer.com/article/10.1007/s44336-025-00016-x), [repo](https://github.com/ccx06/TableZoomer).

- **TabGR / Beyond Linearization — arXiv 2026, bản v2 ngày 27/08/2026.** Attributed Table Graph giữ quan hệ hàng–cột–ô; Question-Guided Personalized PageRank sắp thứ tự bằng chứng, không cần task-specific training. WikiTQ với GPT-4o mini đạt 77,1 so với RoT 74,2. Với Llama3.1-8B, TabGR 64,2 so với RoT 63,7: lợi ích nhỏ hơn nhiều. Dùng như nguồn ý tưởng biểu diễn và một baseline đơn agent mạnh; bản chuyển sang multi-agent là đề xuất của ta. Không gắn nhãn proceedings đã xuất bản khi mới có thông tin acceptance ngoài proceedings. [Paper v2, Table 1 và 19](https://arxiv.org/html/2601.08444v2).

- **TALON — EMNLP 2025.** Multi-agent khám phá và trả lời trên bảng dài. Đáng dùng khi bằng chứng vượt cửa sổ ngữ cảnh hoặc nằm rải rác; cần đánh giá riêng nhóm bảng dài trước khi đưa vào toàn bộ Open-ViTabQA. [Nguồn hội nghị](https://aclanthology.org/2025.emnlp-main.1393/).

### 2.2. Phản biện và kiểm chứng

- **Table-Critic — ACL 2025.** Judge, Critic, Refiner và Curator kết hợp phê bình, sửa lời giải và cây template tích lũy kinh nghiệm. Có tương tác giữa các vai; không đồng nghĩa cần cập nhật trọng số, nhưng bộ nhớ tự phát triển vẫn cần kiểm soát nguồn dữ liệu. Đây là prior work trực tiếp: không thể gọi việc thêm critic hay một vòng sửa là novelty riêng. [Paper](https://aclanthology.org/2025.acl-long.853/).

- **CRAFT — preprint 05/06/2026.** Rewriter, Reverser, Extractor, Rethinker xây hai đường suy luận factual và counterfactual. Phần được khảo sát là prompt-based, không có training stage. Bảng chính dùng DeepSeek-R1-14B, Qwen2.5-72B, Llama3.3-70B và GPT-5-mini, nên chưa có bằng chứng trực tiếp cho hai backbone dự kiến của ta. Không coi so sánh với sampling cùng số ứng viên là đã cân bằng token. [Paper và phụ lục](https://arxiv.org/html/2606.06842v1).

- **DPC — ACL 2026, Text-to-SQL.** Slicer và Tester dựng Minimal Distinguishing Database; Solver dùng Python/Pandas đối chiếu ứng viên SQL. Không cần training cho cơ chế chọn. Có thí nghiệm Qwen2.5-Coder-7B; nhưng Python do LLM sinh là reference có thể sai, không phải ground truth. Chuyển giao ý tưởng kiểm tra lỗi bỏ điều kiện hoặc sai cột; không bê nguyên pipeline database nhiều bảng vào bảng HTML tiếng Việt. [Paper](https://aclanthology.org/2026.acl-long.313/).

- **SQLHD — preprint 24/12/2025, Text-to-SQL.** Kiểm tra metamorphic thay đổi schema và logic để phát hiện bất nhất, không cần gold SQL cho từng phép kiểm. Có thể chuyển sang Table QA dưới dạng phép biến đổi đã biết quan hệ đáp án. Metric phát hiện hallucination của paper không phải EM/accuracy QA. [Paper](https://arxiv.org/abs/2512.22250).

- **CRITIC — ICLR 2024.** Feedback từ công cụ hỗ trợ sửa đáp án, thay vì tự đánh giá thuần lời văn. Có thí nghiệm Llama-2-7B trên bài toán toán bảng; là căn cứ để ưu tiên feedback có thể thực thi. Phải tách nhánh sử dụng oracle trong paper khỏi thiết lập triển khai. [Paper](https://arxiv.org/html/2305.11738v3); chi tiết và bảng nguồn nằm trong [báo cáo chuyển giao](2026-10-01-supporting/transfer-methods.md).

### 2.3. Hướng mở rộng và những phương pháp không dùng nguyên bản

- **ODUTQA-MDC / MAIC-TQA — ACL 2026.** Task về câu hỏi bảng thiếu đặc tả, với đối thoại làm rõ và framework multi-agent. Hợp cho nghiên cứu tiếng Việt về đại từ, chủ thể, thời gian hoặc nhánh header mơ hồ. Tuy nhiên hỏi lại người dùng thay đổi giao thức single-turn; cần bộ đánh giá riêng, không thay câu trả lời bằng câu hỏi làm rõ khi chấm Open-ViTabQA. [Paper](https://aclanthology.org/2026.acl-long.499/).

- **MATA — Findings ACL 2026.** Nguồn ý tưởng nhiều đường CoT/PoT/SQL; nguyên bản có Scheduler và Confidence Checker được huấn luyện. Chỉ chuyển ý tưởng đa dạng đường giải và thay scheduler bằng quy tắc cố định, không gọi bản gốc training-free. [Paper](https://aclanthology.org/2026.findings-acl.1672/).

- **Table-R1 và các pipeline RL/SFT.** Cần kiểm tra đúng title, arXiv ID và phần training vì tên Table-R1 được dùng cho nhiều công trình. Không dùng nguyên bản nếu cần SFT, RL, distillation hay một selector/router học mới. Tương tự, thành tích của hệ kết hợp Commented Code với thành phần đã train không phải thành tích inference-only của Commented Code. Nguồn phân biệt từng trường hợp nằm trong [khảo sát Table QA](2026-10-01-supporting/tableqa-frontier.md).

Các paper dùng đơn agent, graph hoặc công cụ vẫn liên quan: chúng cung cấp cơ chế để thiết kế vai và kênh trao đổi. Cần chứng minh **tương tác giữa các agent** giúp thêm so với việc một agent được cùng biểu diễn, công cụ và ngân sách.

**MultiTAT — Findings EMNLP 2025** là nguồn chuyển giao đa ngôn ngữ đáng đọc: linking bằng ngôn ngữ gốc, reasoning bằng Python ở tiếng Anh. Dataset của bài không có tiếng Việt; không gọi nó là bằng chứng thực nghiệm Vietnamese QA. [Paper](https://aclanthology.org/2025.findings-emnlp.33/), [repo chính chủ](https://github.com/zhxlia/MULTITAT). **XLT — Findings EMNLP 2023** cung cấp cross-lingual-thought prompting, không cập nhật trọng số, để làm ablation ngôn ngữ của plan. [Paper](https://aclanthology.org/2023.findings-emnlp.826/).

## 3. Bằng chứng cần thận trọng khi chuyển sang model nhỏ

Persona khác nhau không bảo đảm lỗi độc lập. Debate có thể làm agent từ đúng đổi sang sai; majority vote và self-consistency là đối chứng bắt buộc, đặc biệt ở cỡ 7B/8B. Các nghiên cứu được xác minh trong [báo cáo chuyển giao](2026-10-01-supporting/transfer-methods.md) gồm thí nghiệm gần GPT-4o mini và Llama3.1-8B.

**Towards a Science of Scaling Agent Systems**, bản v3 tháng 04/2026, cho thấy tác dụng phối hợp phụ thuộc task và kiến trúc. Không lấy ngưỡng khoảng 45% từng được nhắc trong bản cũ làm luật phổ quát để bác bỏ Vietnamese Table QA: tập benchmark và mô hình nghiên cứu khác bài toán của ta. [Bản v3](https://arxiv.org/abs/2512.08296v3).

**RobuT — ACL 2023** cho thấy Table QA nhạy với perturbation bảng và câu hỏi. Lấy benchmark và taxonomy lỗi làm cơ sở đánh giá robustness; giải pháp augmentation để huấn luyện trong paper nằm ngoài ràng buộc của người dùng. [Paper](https://aclanthology.org/2023.acl-long.334/).

## 4. Thiết kế được ưu tiên: reader và inspector kiểm tra từng điều kiện

Đây là **đề xuất nghiên cứu**, kết hợp và thu hẹp cơ chế từ các công trình trên. Không phải một phương pháp đã có kết quả tiếng Việt, cũng chưa có căn cứ gọi là đầu tiên.

### 4.1. Vai và luồng tương tác

1. **Reader** nhận câu hỏi, bảng nguyên và few-shot hợp lệ; trả một đáp án cùng row/cell ID và phép suy luận ngắn.
2. **Inspector** đọc độc lập câu hỏi và bảng, chưa xem đáp án Reader. Nó xác định target, từng constraint, cột/nhánh header tương ứng và phạm vi cần kiểm tra. Độc lập ở đây là độc lập đầu vào ban đầu, không phải giả định độc lập thống kê về lỗi.
3. **Công cụ tất định** so các tham chiếu với bảng; thực thi các điều kiện có thể biểu diễn chính xác như lọc, giao tập hàng, đếm, so sánh. Điều kiện ngữ nghĩa chưa ánh xạ được phải được đánh dấu chưa kiểm chứng.
4. **Inspector nhận output Reader** khi có xung đột hoặc phần kiểm chứng chưa đủ. Nó chỉ phản biện bằng điều kiện cụ thể, hàng phản ví dụ, nhánh header bị nhầm hoặc phần tử bị bỏ sót. Không yêu cầu phản đối bằng mọi giá.
5. **Reader sửa tối đa một lần** khi feedback được hỗ trợ bởi bảng; xuất đúng một đáp án cuối. Nếu kiểm tra không phân biệt được hai lời giải, dùng fallback đã chốt trước trên dev, không mặc định coi critic đúng.

Hai vai LLM có kênh phản hồi thật. Công cụ thực thi và router tất định không cần được gọi là agent. Cấu hình đầu có hai lượt gọi độc lập; khi mở feedback thêm tối đa hai lượt: tổng **2–4 lượt LLM/câu**, gồm cả lượt sửa. Token và thời gian phải đo thực tế; cùng số lượt gọi chưa phải cùng chi phí.

### 4.2. Khác biệt cần kiểm tra với POMA và MemXam

Inspector kiểm tra **các điều kiện đủ để suy ra đáp án**, không chỉ trích một ô chứa đáp án hay đóng vai solver thứ hai. Với câu liệt kê, cần kiểm tra cả phần tử thừa và thiếu. Với câu phủ định, phải kiểm tra phạm vi đã khảo sát. Với câu cực trị, phải bảo toàn mọi hàng thuộc miền so sánh.

Ví dụ minh họa tự tạo: “Những vận động viên Việt Nam giành huy chương vàng năm 2023 là ai?” Cần đồng thời khớp quốc gia, loại huy chương, năm và cột tên. Một tên có thật trong bảng vẫn sai nếu hàng thuộc năm 2022. Trích đúng một tên vẫn chưa đủ nếu có ba hàng thỏa điều kiện. Inspector phải trả bằng chứng cho từng điều kiện và miền hàng, thay vì một confidence tự khai báo.

**Cổng mở trao đổi** có thể dùng: mâu thuẫn điều kiện; tham chiếu ngoài bảng; nhầm nhánh header trùng tên; chênh tập đáp án có witness; hoặc `Null` nhưng tìm được hàng phù hợp. Cổng phải được đo precision/recall trên tập phân tích có nhãn. Nếu dùng dấu hiệu câu hỏi phức tạp hay inspector không chắc, báo riêng tỷ lệ kích hoạt và false alarm.

`Null` là không đủ thông tin theo giao thức task; không phải “program lỗi”, “retrieval không thấy” hay “hai agent bất đồng”. Thiếu bằng chứng ở một subtable không chứng minh thiếu trong bảng gốc. Một literal không xuất hiện nguyên văn cũng chưa chứng minh unanswerable, vì câu trả lời có thể được tính hoặc diễn đạt lại.

### 4.3. Giới hạn và tiêu chí bác bỏ

LLM vẫn có thể ánh xạ sai constraint vào cột; thực thi đúng chương trình sai ý câu hỏi không bảo đảm đáp án đúng. Nếu Inspector lặp cùng lỗi Reader hoặc làm đúng→sai nhiều hơn sai→đúng, cơ chế không đạt mục tiêu. Không mở rộng số role hay số vòng trước khi kiểm tra điều này.

Giả thuyết chính: với cùng budget, feedback có witness/coverage giảm lỗi grounding và điều kiện tốt hơn generic critic, self-refinement và SC. Bác bỏ nếu kết quả ghép cặp không cho thấy lợi ích, hoặc lợi ích biến mất khi baseline dùng cùng biểu diễn/công cụ/memory.

## 5. Hai hướng biến thể đáng nghiên cứu riêng

### 5.1. Grounder và reasoner trao đổi qua cấu trúc bảng

Grounder gắn câu hỏi với các quan hệ `row → header_path → cell`, giữ nguồn ô gộp và các cột điều kiện. Reasoner suy luận trên các quan hệ ấy; khi thiếu điều kiện hoặc miền so sánh, yêu cầu Grounder mở rộng phạm vi một lần.

Đây là chuyển giao ý tưởng TabGR sang multi-agent, không phải đổi Markdown sang JSON đơn thuần. Bắt đầu bằng cell ID, header path và nguồn merged cell đã có ở parser; chưa cần graph database, GNN hoặc embedding được train. Full graph một agent là baseline bắt buộc để tách lợi ích biểu diễn khỏi tương tác.

Ưu tiên merged-header, merged-value, các cột lặp nhãn theo năm/nhóm. So với Flatten V1 và biểu diễn có địa chỉ ô trên đúng cùng thông tin. Không xóa sớm cột dùng định vị hàng. Cần đánh giá grounding accuracy và tỷ lệ bỏ mất điều kiện, không chỉ độ ngắn của prompt.

### 5.2. Tester và solver kiểm tra phản thực tế/metamorphic

Tester tạo một phép kiểm có quan hệ đáp án đã biết; Solver kiểm tra trên môi trường thử, rồi phản hồi bằng mismatch cho agent trả lời. Phải giữ bảng thử tách khỏi bảng thật: đáp án cuối luôn trả lời trên bảng thật.

Ví dụ: đổi thứ tự cột và giữ quan hệ header–cell thì đáp án không đổi; đổi thứ tự hàng chỉ hợp lệ nếu câu hỏi không phụ thuộc vị trí/thứ tự; đổi một giá trị điều kiện ở hàng đang được dùng có thể tạo witness cho predicate bị bỏ quên. Với câu “đầu tiên”, “cuối cùng”, “hàng thứ ba”, không áp invariant xáo hàng một cách máy móc.

Một metamorphic test thất bại là dấu hiệu bất nhất, không tự xác định đáp án đúng. Hai đáp án sai vẫn có thể nhất quán. Phép phản thực tế bằng phủ định ngôn ngữ cũng không phải chứng minh nhân quả; nó có thể thay luôn nghĩa câu hỏi. Cần validity audit cho phép biến đổi, nhất là tiếng Việt có phủ định, lượng từ và so sánh.

Dùng một phép thử khi đã có nghi vấn cụ thể; đối chứng bằng một lượt solve/refine thêm cùng ngân sách. Nếu dựng bảng phân biệt và chạy SQL/Python, overlap với DPC; nếu factual/counterfactual rồi tổng hợp, overlap với CRAFT. Đóng góp khả dĩ là xử lý cấu trúc và điều kiện tiếng Việt, validity của phép kiểm, cùng gate inference-only; chưa phải novelty đã được chứng minh.

### 5.3. Grounding tiếng Việt và plan chương trình bằng tiếng Anh

Một biến thể đa ngôn ngữ: Grounder giải quyết tên riêng, alias, điều kiện và đường dẫn header bằng tiếng Việt; Programmer nhận các cell ID cùng raw values để lập chương trình bằng tiếng Anh/Python; hai vai trao đổi khi programmer gặp điều kiện chưa ánh xạ được. Đáp án cuối giữ tiếng Việt và giá trị gốc trong bảng.

Lấy cơ chế từ MultiTAT/XLT, không dịch nguyên bảng rồi coi đó là bản tương đương miễn phí. So với native-only và English-plan trong cùng một agent, cùng công cụ và budget. Hướng này hợp với phần câu cần thực thi hơn là toàn bộ lookup; chưa có bằng chứng cho lợi riêng của hai vai trên Qwen3-8B/Open-ViTabQA.

Với số và đơn vị, giữ raw value, parsed value, unit và nguồn ô. `1.234,5`, triệu/tỷ, quý/năm, tỷ lệ và dấu `—` cần giải thích theo ngữ cảnh cột; không ép mọi dấu chấm thành phân cách nghìn hoặc mọi ô trống thành số 0. Chuẩn hóa tất định không agent phải là một đối chứng riêng.

## 6. Những gì repo đã làm và hệ quả cho nghiên cứu mới

Các kết luận sau là **ghi nhận lịch sử nội bộ**, không phải tái lập trong lượt khảo sát:

- [Nhật ký D01–D13](enhance_poma/direction-progress.md) cho thấy best-of-K khác chính sách một đáp án; executor số học D04 chưa tạo lợi ích, lọc header D13 mất cột điều kiện, và đổi biểu diễn chưa có thắng lợi ổn định. Vì vậy không đề xuất lại “thêm Python cho mọi câu” hay “lọc bảng càng nhỏ càng tốt”.
- [MemXam ngày 26/09](2026-09-26-memxam-multi-agent-qwen3-8b.md) đã có solver nhiều view, memory từ train cùng bảng và đối chất. Báo cáo ghi nguồn lợi chính là memory; lợi riêng của tương tác chưa tách khỏi 0. Nghiên cứu mới cần vượt **kNN-FS và kNN-SC**, không chỉ zero-shot, và cần có feedback mới mà baseline chưa có.
- [Khảo sát 26/09](2026-09-26-multi-agent-tqa-de-xuat.md) là nguồn gợi ý đọc, không thay cho việc kiểm tra bản paper mới. Chẳng hạn abstract Scaling Agent Systems đã sửa giữa các version.
- POMA có parser giữ `rowspan`, `colspan`, `merged_from`; có contracts, finalizer một đáp án và AST executor. Có thể tái sử dụng khi triển khai sau, nhưng khảo sát này không sửa runtime. Module AST ghi yêu cầu giữ semantics của protocol D04, nên không sửa âm thầm để biến thành protocol mới.

Không lấy các con số lịch sử khác endpoint, parser, split hoặc candidate policy để kết luận hệ nào tốt hơn trong một phép so sánh mới.

## 7. Giao thức thực nghiệm cho hai backbone

### 7.1. Dữ liệu và phạm vi tổng quát hóa

Open-ViTabQA là nguồn tiếng Việt phù hợp với POMA: bảng bán cấu trúc, nhiều loại reasoning và đáp án `Null`. [Nguồn xuất bản](https://doi.org/10.1016/j.knosys.2025.114391), [schema trong repo](../../dataset/README.md).

Kiểm kê local của subagent: train 7.928 QA/329 bảng; dev 991/296; test 992/289; cả 289 bảng test và 296 bảng dev đều có trong train. Official split vì vậy đo câu hỏi mới trên **bảng đã thấy**, không đủ chứng minh unseen-table generalization. Train QA làm few-shot là hợp lệ với setting này nếu khai báo và cấp memory giống nhau cho baseline.

No-training nghĩa là không cập nhật trọng số, không học router/verifier mới. Few-shot/retrieval từ train và chốt prompt trên dev vẫn hợp lệ; retrieval không được đọc gold của dev/test. Chặn câu trùng/gần trùng, báo cách xử lý và đánh giá bổ sung khi bỏ chúng. Nếu claim tổng quát hóa sang bảng mới, tạo grouped-by-table split giữ toàn bộ QA của bảng holdout ngoài memory, hoặc thu thập bảng mới có kiểm tra thủ công.

Repo đã dùng một số test samples để phân tích và chọn hướng trước đây. Kết quả test hiện hữu phải mô tả là đánh giá trên benchmark đã tiếp xúc; để có xác nhận độc lập, cần holdout chưa dùng hoặc dữ liệu mới. Không gọi một tập đã xem nhiều lần là blind test.

**M3TQA — Findings ACL 2026** có 78 mẫu Vietnamese test trong phụ lục bản published; có thể dùng như kiểm tra chuyển miền nhỏ, không thay benchmark chính. Dữ liệu dịch đa ngôn ngữ có đặc tính khác bảng Wikipedia tiếng Việt gốc. Dùng benchmark để đánh giá trọng số có sẵn phù hợp no-training; không cần dùng phần training method của bài. [Nguồn và Appendix Table 8](https://aclanthology.org/2026.findings-acl.1134.pdf).

### 7.2. Baseline tối thiểu

Chạy riêng cùng ma trận trên mỗi backbone:

1. Few-shot một agent + finalizer chung.
2. kNN-FS cùng bảng từ train, nếu proposed system được dùng memory này.
3. kNN-SC3/SC ở mức budget đã chọn; sampling và memory giống hệ mới.
4. Single-agent self-refine có cùng công cụ và budget.
5. POMA/MemXam cấu hình chốt, predicted hints và một final answer.
6. Proposed system và bản **bỏ kênh tương tác**, giữ nguyên input/memory/candidates ban đầu.

Baseline TableZoomer/TabGR hữu ích để đối chiếu mechanism. Nếu code Table-Critic/CRAFT chưa tái lập được, một critic theo prompt tự viết phải gọi là adaptation. Adapter Chain-of-Query trong repo ghi `coq_base_sql_fallback`; không báo nó là full CoQ. Chi tiết baseline đang có ở [README](../../baselines/README.md).

### 7.3. Backbone và ngân sách

Chạy homogeneous trước: mọi vai dùng Qwen3-8B trong một thí nghiệm, mọi vai dùng GPT-4o mini trong thí nghiệm kia. Mixed Qwen reader + GPT inspector là mở rộng sau, phải đối chứng bằng GPT reader đơn hoặc cascade cùng chi phí để tránh nhầm lợi của model với lợi phối hợp.

Qwen3: ghi model ID chính xác, provider/backend, precision hoặc quantization, context length, thinking flag, decoding và giới hạn token. Thinking/non-thinking là ablation riêng; mọi baseline trong phép so phải cùng mode. GPT-4o mini: pin snapshot nếu endpoint hỗ trợ; không suy ra số tham số từ tên “mini”. Structured outputs cần validation local ở cả hai model, số repair giới hạn và tính vào budget. Nguồn chính chủ và cấu hình repo được ghi trong [báo cáo giao thức](2026-10-01-supporting/vietnamese-evaluation.md).

Budget báo theo token input/output/thinking nếu backend cung cấp, số call gồm repair/retry, latency p50/p95 và chi phí thực tế. Không ép đơn giá API của GPT sang Qwen tự host; báo riêng GPU/time. Có đường accuracy–budget với các cap nhỏ, chẳng hạn 2/3/4 call, nhưng token/cost mới cho biết so sánh có cân bằng không. Các cap này là cấu hình đề xuất, không phải budget tối ưu đã đo.

### 7.4. Ablation và metric

- **Bỏ tương tác:** output hai vai ban đầu + chọn tất định; so với feedback/repair trên cùng nguồn candidates. Budget còn lại cấp cho SC/refine đối chứng.
- **Bỏ grounding có cấu trúc:** evidence text vs cell ID/header path, giữ nguyên thông tin bảng.
- **Bỏ kiểm tra đủ điều kiện:** chỉ cell tồn tại vs constraint + scope coverage.
- **Generic critic vs diagnostic feedback:** cùng số lượt và trần token.
- **Always-on vs có gate:** báo trigger rate, số lỗi chạm được, false alarm và lợi ích toàn tập.
- **Không memory vs có memory:** proposed và baseline cùng quyền truy cập memory; không đổi nhiều yếu tố cùng lúc.

Metric chính: EM và F1 của **một đáp án cuối**. ROUGE-1, METEOR, BIF là phụ trợ theo protocol thống nhất; BIF dùng scorer/checkpoint đã có, không train scorer mới. Báo Null precision/recall/F1 và hai lỗi false abstention/hallucination riêng. Nếu một metric lỗi, ghi coverage và lý do; không âm thầm bỏ câu rồi trình bày như đủ N.

Đo thêm: wrong→right, right→wrong, net repair gain, condition-grounding accuracy, list completeness, tool success và semantic correctness của plan. Một tập nhỏ được gán nhãn evidence/constraints thủ công phục vụ đánh giá cơ chế, **không đưa các nhãn ấy vào runtime**.

Lệnh đánh giá một đáp án mà repo đã hỗ trợ:

```powershell
conda run -n kltn python run_eval.py --pred outputs/research/<predictions>.json --qas dataset/qas_test.json --tables dataset/table.json --candidate-policy single-required --strict --metrics em,f1,rouge1,meteor,answerability_f1,metrics_by_table_type
```

Lệnh minh họa này chưa được chạy; thay đường dẫn placeholder bằng artifact thực. Best-of-candidates và gold hints chỉ báo oracle/diagnostic, không làm kết quả chính.

Lặp cấu hình đã chốt để đo biến thiên giữa lần chạy. Dùng paired confidence interval và bổ sung bootstrap theo cụm `table_id`, vì nhiều câu dùng chung bảng; hàm bootstrap hiện tại trong repo lấy mẫu theo QA, chưa thay cho clustered bootstrap. Không diễn giải một quan sát chênh 1–2 điểm thành “sàn nhiễu” phổ quát, không chọn phiên có điểm cao nhất. Chốt một giả thuyết chính để hạn chế chọn hậu nghiệm giữa nhiều nhánh.

## 8. Thứ tự làm thực tế và đóng góp có thể viết thành paper

1. Chọn một tập dev phân tích có phủ lookup, multi-condition, list, Yes/No, Null và merged tables. Chỉ chọn hướng theo dev; ghi trước ngân sách và tiêu chí đánh giá.
2. Chạy reader + inspector có cell/constraint grounding và một vòng diagnostic feedback. So với kNN-SC và single-agent cùng input/tool/budget trên cả hai backbone.
3. Nếu grounding có tín hiệu, thử quan hệ graph/header như một ablation. Nếu generic feedback không sửa được lỗi, thử một metamorphic/counterfactual test có validity audit; không thêm cả graph, memory, coder và nhiều critic cùng lúc.
4. Chỉ triển khai full/new holdout khi cấu hình đã chốt. Báo cả kết quả âm: không được giấu việc critic làm đúng→sai hoặc memory mới là nguồn lợi.

Đóng góp khả dĩ là **cơ chế phối hợp dựa trên grounding và kiểm chứng điều kiện cho bảng tiếng Việt, với bằng chứng cô lập lợi của tương tác trên model nhỏ**. Muốn claim mạnh hơn cần novelty review và thực nghiệm; chỉ ghép reader/critic hoặc đổi tên role chưa đủ.

**ViPanelTR** đã xuất hiện trong danh sách accepted MAPR 2026; hiện nguồn được kiểm chứng mới xác nhận tên và acceptance, chưa đủ để kết luận cơ chế hay setting training. Phải kiểm tra overlap trước claim “đầu tiên” hoặc novelty về Vietnamese multi-agent Table QA. [Danh sách chính thức](https://mapr.uit.edu.vn/list-accepted-papers-mapr-2026).

## 9. Báo cáo nguồn chi tiết

- [Table QA và các công trình 2025–2026](2026-10-01-supporting/tableqa-frontier.md).
- [Các phương pháp chuyển giao, evidence model nhỏ và kết quả âm](2026-10-01-supporting/transfer-methods.md).
- [Vietnamese datasets, backbone và thiết kế đánh giá](2026-10-01-supporting/vietnamese-evaluation.md).

Các báo cáo phân biệt nguồn đã đọc với thông tin chưa đủ kiểm chứng. Không có thí nghiệm LLM có phí, thay đổi pipeline hay cài thêm dependency trong lượt nghiên cứu này.
