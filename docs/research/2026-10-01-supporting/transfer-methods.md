# Hướng chuyển giao ngoài Table QA: kiểm chứng và phối hợp agent không huấn luyện

Ngày khảo sát: 01/10/2026. Phạm vi: nguồn sơ cấp đã mở nội dung paper, ưu tiên phương pháp suy luận với trọng số cố định, phù hợp thực nghiệm Qwen3-8B và GPT-4o-mini. Kết quả dưới đây chưa phải bằng chứng trên Vietnamese Table QA. Các đoạn **Đề xuất chuyển giao** là thiết kế của khảo sát, không phải kết quả paper.

## Kết luận lựa chọn

Ưu tiên **agent giải + agent kiểm chứng bằng dữ liệu/công cụ + sửa có điều kiện**. Nếu còn bất đồng, thêm nhánh độc lập và kiểm tra phản ví dụ. Debate tự do và phản tư nhiều vòng nên là baseline/ablation, không mặc định là đóng góp chính. DPC 2026 là prior work rất gần ý tưởng kiểm chứng SQL bằng Python và bảng phản ví dụ: đổi tên agent không tạo novelty.

## 1. CRITIC — phản biện có công cụ

**Paper:** Gou và cộng sự, ICLR 2024, [bản đầy đủ](https://arxiv.org/html/2305.11738v3).

**Cơ chế và huấn luyện:** khởi tạo đáp án, dùng công cụ để thu phản hồi, critique rồi sửa; không cần huấn luyện bổ sung. Công cụ gồm tìm kiếm cho QA và interpreter cho chương trình toán. Phần D.5 có LLaMA-2-7B: TabMWP, PoT 36.3 → CRITIC 41.0; GSM8K 18.7 → 20.7. Đây là evidence ở 7B, chưa phải Qwen3-8B hay tiếng Việt. Kết quả CRITIC* dùng oracle biết câu nào sai, phải tách khỏi cấu hình triển khai. Paper chỉ ra critique không dùng tool thường kém hơn. [Nguồn](https://arxiv.org/html/2305.11738v3)

**Đề xuất chuyển giao:** solver tạo phép toán và cell evidence; verifier kiểm cột/hàng/tập lọc và thực thi phép toán trên bảng thật. Repair nhận lỗi cụ thể như `missing_constraint`, `unit_mismatch`, `wrong_cell`, không chỉ “hãy xem lại”. Execution thành công không chứng minh câu hỏi được hiểu đúng. Giới hạn ban đầu một vòng sửa, đo sai→đúng và đúng→sai.

## 2. Self-Refine — baseline phản tư tối thiểu

**Paper:** Madaan và cộng sự, NeurIPS 2023, [bản đầy đủ](https://arxiv.org/html/2303.17651v2).

**Cơ chế và huấn luyện:** cùng một LLM thực hiện generate → feedback → refine bằng ba prompt; không cập nhật trọng số. Thử nghiệm trên bảy tác vụ, với mô hình như GPT-3.5, ChatGPT, GPT-4; tối đa bốn vòng feedback/refine. Các kết quả đa nhiệm không đủ để khẳng định tăng accuracy Table QA của model nhỏ. Bản gốc là single-model self-refinement; chuyển thành hai agent có context tách biệt là thay đổi thiết kế của ta. [Nguồn](https://arxiv.org/html/2303.17651v2)

**Đề xuất chuyển giao:** baseline solver–critic không tool, cố định một vòng. Giữ cùng prompt giải ban đầu và cùng token budget với cấu hình tool-verifier. Không dùng Self-Refine làm bằng chứng rằng critic bằng ngôn ngữ tự nhiên chắc chắn sửa được lỗi số học/ngữ nghĩa.

## 3. Reflexion — ghi bài học bằng văn bản

**Paper:** Shinn và cộng sự, NeurIPS 2023, [bản đầy đủ](https://arxiv.org/html/2303.11366v4).

**Cơ chế và huấn luyện:** actor nhận feedback, reflection chuyển lỗi thành bài học, lưu episodic memory cho lần thử sau; “reinforcement” ở đây không cập nhật trọng số. Paper có cải thiện mạnh GPT-4 HumanEval, nhưng Appendix A cho starchat-beta: baseline 0.26 và Reflexion 0.26, không tăng. Một số cấu hình QA sử dụng phản hồi ground truth; không được đem cơ chế đó vào test khi gold answer không có. [Nguồn](https://arxiv.org/html/2303.11366v4)

**Đề xuất chuyển giao:** trong từng câu, lưu lỗi đã được tool xác nhận: “đã lấy doanh thu riêng thay hợp nhất”, “đọc triệu thành tỷ”. Nếu lưu xuyên câu, xây memory từ dev rồi đóng băng trước test; không đưa gold/test feedback vào bank. Memory dài có thể làm solver bám bài học không phù hợp, cần ablation không memory.

## 4. Chain-of-Verification — kiểm tra độc lập với đáp án nháp

**Paper:** Dhuliawala và cộng sự, 2023/2024, [bản đầy đủ](https://arxiv.org/html/2309.11495v2).

**Cơ chế và huấn luyện:** draft → lập câu hỏi kiểm chứng → trả lời độc lập → đáp án cuối. Factored verification tránh cho phần trả lời kiểm chứng nhìn trực tiếp đáp án nháp. Không huấn luyện bổ sung cho CoVe; thực nghiệm chính dùng Llama 65B, có đối chiếu Llama2-70B-chat. MultiSpanQA few-shot F1 0.39 → factored CoVe 0.48. Đây là closed-book/longform QA, không chứng minh hiệu quả ở 8B. [Nguồn](https://arxiv.org/html/2309.11495v2)

**Đề xuất chuyển giao:** verifier nhận câu hỏi gốc, bảng và checklist nhưng ban đầu không nhận đáp án solver: kỳ nào, scope nào, đơn vị nào, mẫu số nào? Sau khi verifier xác định cells/điều kiện, mới đối chiếu kết quả. Không tách ra quá nhiều câu kiểm chứng nhỏ vì chi phí tăng theo số câu và dễ bỏ sót quan hệ giữa chúng.

## 5. System 2 Attention — lọc context có kiểm soát

**Paper:** Weston và Sukhbaatar, 2023, [bản đầy đủ](https://arxiv.org/html/2311.11829v1).

**Cơ chế và huấn luyện:** LLM tạo lại context chỉ giữ phần liên quan rồi trả lời; sử dụng prompt, không cần huấn luyện bổ sung. Thực nghiệm chính LLaMA-2-70B-chat trên QA có distractor/opinion, toán có thông tin nhiễu và sinh văn bản. Vì vậy đây là evidence về lọc context cho model lớn, không phải evidence trên bảng hay Qwen3-8B. [Nguồn](https://arxiv.org/html/2311.11829v1)

**Đề xuất chuyển giao:** grounding agent chọn subtable bằng ID ô, giữ header nhiều tầng, đơn vị, chú thích và cột dùng cho filter. Tránh LLM viết lại giá trị ô. Verifier được phép quay về full table khi thiếu evidence. Đánh giá riêng recall của evidence, không chỉ độ ngắn prompt: lọc mất hàng tổng hoặc chú thích có thể khiến cả nhóm đồng thuận trên dữ liệu thiếu.

## 6. AgentVerse — phân vai nhưng không mặc định càng đông càng tốt

**Paper:** Chen và cộng sự, ICLR 2024, [bản đầy đủ](https://arxiv.org/html/2308.10848v2).

**Cơ chế và huấn luyện:** expert recruitment → collaborative decision → action execution → evaluation, bằng prompt và tools. Thử nghiệm zero-shot với GPT-3.5-Turbo-0613/GPT-4-0613. MGSM GPT-3.5: Solo 82.4, Group 80.8; GPT-4: Solo 96.0, Group 95.2. Nhóm không luôn hơn solo; paper giới hạn toán còn hai agents vì thêm reviewers dễ đưa critique sai. Không có evidence trực tiếp Qwen3-8B hoặc GPT-4o-mini trong paper này. [Nguồn](https://arxiv.org/html/2308.10848v2)

**Đề xuất chuyển giao:** vai trò gắn với năng lực kiểm được: grounding/solver/verifier, thay vì chuyên gia tự do. Bắt đầu ba vai trò; chỉ mở agent đối chứng khi có lý do. Ablation cần một agent thực hiện cùng bước/tool để tách lợi ích decomposition khỏi lợi ích có nhiều agents.

## 7. Scaling Test-time Compute for LLM Agents — chọn thời điểm phản tư

**Paper:** Zhu và cộng sự, 2025, [bản đầy đủ](https://arxiv.org/html/2506.12928v1).

**Cơ chế và huấn luyện:** khảo sát parallel sampling, sequential revision, verifier/merging và diversification ở inference. Kết quả chính GPT-4.1 trên GAIA: baseline 55.76, phản tư mỗi bước 55.15; threshold chọn lọc `<2` đạt 56.36. Best-of-N với list-wise selection đạt 63.03, voting 56.8. Evidence này trên GPT-4.1/GAIA, không phải model nhỏ/table QA. Pass@K khi trộn rollout khác nhau là khả năng có đáp án đúng trong tập ứng viên, không phải accuracy sau bộ chọn. [Nguồn](https://arxiv.org/html/2506.12928v1)

**Đề xuất chuyển giao:** gate bằng sự kiện quan sát được: tool lỗi, thiếu evidence, đơn vị chưa thống nhất, hai kết quả không khớp. Không bê ngưỡng score 2/10 sang tiếng Việt. Dừng khi hết lỗi được kiểm hoặc hết budget; so với cùng số lượt gọi và cùng lượng token, không chỉ cùng số agents.

## 8. Debate or Vote — baseline ensemble bắt buộc

**Paper:** Choi, Zhu và Li, NeurIPS 2025, [bản đầy đủ](https://arxiv.org/html/2508.17536v1).

**Cơ chế và evidence:** tách voting của các lời giải độc lập khỏi trao đổi debate. Table 1 với Qwen2.5-7B-Instruct: average single 0.7205, majority vote 0.7691, decentralized debate hai vòng 0.7377; dùng năm agents. Có Llama3.1-8B và Qwen2.5-32B. Lợi ích debate không vượt voting ổn định. Kết quả lý thuyết martingale dựa trên mô hình Bayesian/DCM của paper, không phải định luật áp dụng cho mọi hệ multi-agent. [Nguồn](https://arxiv.org/html/2508.17536v1)

**Đề xuất chuyển giao:** ít nhất một baseline lấy ba lời giải độc lập rồi vote đáp án chuẩn hóa; thêm baseline vote theo execution result. Đây là ensemble nhiều instance, chưa chứng minh collaboration có ích. Phải kiểm soát chi phí token: debate có lịch sử dài hơn sampling độc lập dù cùng số agents.

## 9. Talk Isn't Always Cheap — bằng chứng sát GPT-4o-mini

**Paper:** Wynn, Satija và Hadfield, ICML MAS Workshop 2025/preprint, [bản đầy đủ v2](https://arxiv.org/html/2509.05396v2).

**Evidence:** thử GPT-4o-mini, Llama3.1-8B-Instruct, Mistral7B trên CSQA/MMLU/GSM8K; 100 câu mỗi task, năm seeds, hai vòng debate. Nhóm 2 GPT-4o-mini + 1 Mistral7B: MMLU voting trước debate 82.8 → sau debate 80.8. Ba GPT-4o-mini trên GSM8K lại tăng nhẹ 94.0 → 94.4. Debate có thể làm đúng→sai, kể cả model mạnh chiếm đa số; không được kết luận tất cả debate đều hại. Cỡ mẫu nhỏ và task tiếng Anh giới hạn chuyển giao. [Nguồn](https://arxiv.org/html/2509.05396v2)

**Đề xuất chuyển giao:** giữ đáp án trước sửa, thống kê answer corruption. Agent chỉ thay kết quả khi cung cấp ô/điều kiện/chạy tool chứng minh lỗi; đồng thuận không là tiêu chí đúng. Homogeneous experiments cho mỗi backbone trước; cấu hình trộn Qwen/GPT là thí nghiệm riêng.

## 10. SQLHD — metamorphic testing không cần đáp án chuẩn

**Paper:** Yang và cộng sự, 24/12/2025, [bản đầy đủ](https://arxiv.org/html/2512.22250v1).

**Cơ chế và huấn luyện:** hai giai đoạn schema-linking/logic synthesis với 8 structure-aware và 9 logic-aware metamorphic relations; so sánh output của input gốc với biến đổi có quan hệ đã biết, không cần gold SQL ở inference. Thử nghiệm gồm GLM-4, GPT-3.5-Turbo, DeepSeek-V3, Qwen2.5-32B. Chưa có evidence Qwen3-8B/GPT-4o-mini. Đây là detection, không phải chứng minh tăng end-to-end QA. Bản preprint có cách mô tả positive/no-hallucination và chỉ số chưa đủ rõ để chuyển F1 thành “accuracy phát hiện lỗi”; không dùng con số đó làm luận điểm chính. [Nguồn](https://arxiv.org/html/2512.22250v1)

**Đề xuất chuyển giao:** verifier chọn tối đa một MR theo loại phép toán; execution kiểm quan hệ trước/sau. Vi phạm là lý do mở repair, nhưng vượt qua MR không đảm bảo đúng. MR sai điều kiện tạo false alarm; đây là vấn đề cần đo trong ablation.

## 11. DPC — prior work gần nhất cho kiểm chứng phản ví dụ bằng hai chương trình

**Paper:** Li và cộng sự, ACL 2026 Main, [ACL](https://aclanthology.org/2026.acl-long.313/), [bản đầy đủ](https://arxiv.org/html/2604.15163v1).

**Cơ chế và evidence:** Slicer/Tester tạo Minimal Distinguishing Database để SQL ứng viên cho kết quả khác; Solver sinh Python/Pandas độc lập; chọn theo execution consistency. Không train verifier. Qwen2.5-Coder-7B trên BIRD: self-consistency 46.4 → DPC 47.6; Spider 76.5 → 77.5. Selection trung bình ~3.8k tokens, ~4.2s, SC ~0.8s trong cấu hình paper; không là latency dự báo trên máy ta. Nhóm majority-correct mất 3 điểm accuracy. Paper thừa nhận database tổng hợp có thể lệch các ràng buộc ngầm, adaptive verification là hướng tương lai. Python do LLM sinh vẫn có thể sai, không phải oracle. [Nguồn](https://arxiv.org/html/2604.15163v1)

**Đề xuất chuyển giao:** khi hai cách giải bất đồng, dựng bảng 3–8 hàng phân biệt `>`/`>=`, `COUNT`/`COUNT DISTINCT`, khoảng thời gian, scope tổng/hạng mục. Với bảng phân cấp Việt, giữ hierarchy và unit metadata. Novelty phải ở grounding tiếng Việt, phép biến đổi giữ semantics và gate theo evidence; “SQL + Python + multi-agent” đã có prior work này.

## 12. ConMem — memory không train, nhưng có feedback xuyên tác vụ

**Paper:** Tan và cộng sự, 07/06/2026 preprint, [bản đầy đủ](https://arxiv.org/html/2606.08702v1).

**Cơ chế và evidence:** trích trajectory thành strategy cards, graph quan hệ, retrieval và composition trong token budget; host/model cố định. Main runs dùng Qwen3-4B-Instruct-2507, TriviaQA/PopQA/KodCode/PDDL và AutoGen/CAMEL/MacNet. Evaluation prequential: chỉ đọc card đã có trước câu hiện tại; sau prediction, evaluator có thể cung cấp correctness/pass-fail cho memory update. Vì vậy training-free không đồng nghĩa hoàn toàn không cần outcome supervision. Paper chưa chứng minh Table QA tiếng Việt hoặc không-feedback memory. [Nguồn](https://arxiv.org/html/2606.08702v1)

**Đề xuất chuyển giao:** ưu tiên thấp hơn verifier/stateless cho luận văn hiện tại. Nếu thử, chỉ xây card từ dev hoặc lỗi tool tự xác minh; đóng băng bank và ngưỡng trước test. Không dùng correctness của câu test trước để hỗ trợ câu test sau rồi so với baseline stateless mà không khai báo khác protocol.

## Thiết kế chuyển giao tối thiểu đề xuất

Phần này là giả thuyết thực nghiệm của khảo sát, chưa có kết quả đo.

### A. Grounding–Solve–Verify với feedback theo lỗi

1. Grounder trả ID cell/header, kỳ, scope, đơn vị, điều kiện lọc; giá trị lấy từ bảng gốc bằng code.
2. Solver nhận evidence và sinh phép toán/chương trình, đáp án nháp.
3. Verifier đọc câu hỏi gốc và bảng; kiểm ngữ nghĩa tách khỏi kết quả solver rồi đối chiếu execution.
4. Chỉ repair khi có lỗi cụ thể. Verifier kiểm lại một lần; hết budget thì trả kết quả với trạng thái unresolved nội bộ, không tự gán confidence cao.

**Câu hỏi nghiên cứu:** feedback theo lỗi có giảm repair đúng→sai hơn critic chung khi chi phí suy luận tương đương? Grounder có làm mất evidence quan trọng không?

### B. Metamorphic verifier cho bảng tiếng Việt

| Quan hệ đề xuất | Điều kiện áp dụng | Kết quả kỳ vọng | Lỗi có thể lộ |
|---|---|---|---|
| Đảo thứ tự hàng | Query không dựa vào thứ tự/“hàng đầu” | Đáp án không đổi | Positional shortcut |
| Đổi `triệu đồng` → `tỷ đồng`, chia trị số 1000 | Chỉ đổi biểu diễn tiền, giữ mọi giá trị/metadata liên quan và làm tròn đủ chính xác | Giá trị vật lý không đổi sau canonicalization | Nhầm hệ số/đơn vị |
| Thêm một hàng ngoài kỳ/phạm vi hỏi | Hàng không thay tổng đã cho và không thuộc tập điều kiện | Đáp án không đổi | Filter sai/thiếu scope |
| Thêm bản sao hàng | Chỉ với truy vấn đã xác định COUNT hay COUNT DISTINCT | COUNT thay đổi, DISTINCT không đổi theo quy tắc | Sai phép đếm |
| Đổi dấu so sánh sát biên | Có giá trị đúng ngưỡng; không thay đổi ngữ nghĩa khác | `>` khác `>=` trên hàng biên | Nhầm “trên”/“từ…trở lên” |

Không dùng scale invariance cho mọi câu hỏi: phần trăm và tên đối tượng có semantics khác tiền; không đảo hàng nếu đó là chuỗi thời gian có thứ tự hoặc quan hệ cha–con. “Không đổi kết quả” chỉ là điều kiện cần. Bản biến đổi phải được tool kiểm cấu trúc/đơn vị; không cho LLM tùy ý viết lại bảng.

### C. Bất đồng có điều kiện và early stopping

Chạy hai nhánh độc lập khi verifier có cờ ambiguity, evidence thiếu hoặc kết quả mâu thuẫn. Nhánh 1 giải trực tiếp từ cells; nhánh 2 dùng SQL/Python trên bảng chuẩn hóa. Nếu cùng đáp án nhưng cùng evidence sai thì agreement không giúp; cần ghi cả evidence agreement lẫn answer agreement. Dừng theo tập kiểm tra đã hoàn tất và budget, không dừng chỉ vì agent nói “tôi chắc”.

## Kiểm chứng thực nghiệm cần giữ

- Hai bộ thí nghiệm độc lập: mọi vai trò cùng Qwen3-8B; mọi vai trò cùng GPT-4o-mini. Cấu hình mixed-model là kết quả phụ riêng.
- Đối chứng: direct prompting; single-agent cùng tool/bước; self-refine không tool; ba lời giải độc lập + voting; multi-agent verifier; MR/dual-path khi có gate.
- Metric: answer accuracy/F1 theo chuẩn dataset, evidence precision/recall nếu annotate được, tool-validity, wrong→right và right→wrong, unresolved, tổng token/input-output, số calls, median/p95 latency.
- Tách nhóm số học, lookup, cực trị, lọc nhiều điều kiện, thời gian, hierarchy và đơn vị; mọi ngưỡng/gate/few-shot chọn trên dev rồi đóng băng.
- Cùng token/call budget và cùng tool availability cho các đối chứng chính; dùng multiple seeds vì prompt sampling/debate có stochasticity. Không dùng gold để dừng hoặc chọn đáp án test.

**Ưu tiên triển khai:** A trước; B/C là ablation và ứng viên đóng góp. Memory graph và recruitment tự động để sau, vì tăng biến số mà chưa có evidence cần thiết cho tác vụ này.
