# POMA — Q&A buổi trao đổi (đầy đủ)

**Ngày:** 2026-09-18
**Bối cảnh:** Trao đổi về việc review bản thảo POMA (Vietnamese Table QA, Nguyen Dinh Khoi & Dang Van Thin, UIT), so sánh với ViPanelTR (cùng nhóm tác giả), lập kế hoạch sửa bài và tăng novelty trước khi nộp lại tạp chí Q2.

---

## Q1. (Mở đầu — đính kèm `JIT_Khoi.pdf` và `MAPR_2026_Khoi.pdf`, không kèm câu hỏi cụ thể)

**A1.**
Đây là hai bài — **POMA** (Parallel Multi-Agent Orchestration) và **ViPanelTR** (framework multi-agent 5-role dạng panel), cả hai đều của Nguyen Dinh Khoi et al. về Vietnamese Table QA, đánh giá trên Open-ViTabQA.

Bạn muốn xử lý gì với hai bài này? Ví dụ:
- Review một hoặc cả hai theo chuẩn hội nghị (điểm yếu, novelty, khả năng accept/reject)
- So sánh hai cách tiếp cận, chỉ ra chỗ trùng lặp/xung đột giữa chúng
- Tóm tắt kết quả chính
- Việc khác

---

## Q2. Đính kèm 5 file (`POMA_Ke_hoach_chinh_sua_Q2.docx`, ảnh chụp comment reviewer, `review-POMA-JIT.md`, `journal-selection-POMA.md`, `fix-plan-POMA.md`) + yêu cầu: đây là thêm 2 review từ supervisor/meta-review cho POMA; đã chạy skill `/conference-reviewer` và `/argument-review` ra file `review-POMA-JIT.md`, rồi chuẩn bị fix plan + rescope chọn tạp chí Q2 khác phù hợp. Yêu cầu: đọc lại toàn bộ file; tác giả muốn **tăng novelty và đóng góp** của POMA, **giữ nguyên concept low-resource + Vietnamese Table QA**, nhưng tăng cường bằng **boosting methods**. Cho phép dùng alphaXiv, browser tra arxiv/alphaXiv, hoặc tìm phương pháp đáng thử trên blog `magazine.sebastianraschka.com`.

**A2.**
Đã đọc lại toàn bộ 5 file (kể cả nội dung đầy đủ của `review-POMA-JIT.md` và file `.docx` — trước đó chưa hiện trong context, phải trích xuất riêng). Ảnh chụp comment reviewer khớp y nguyên với phần trích dẫn đã có trong `journal-selection-POMA.md` — tức là xác nhận lại phân tích cũ (JIT có thể sai venue vì không đúng scope), không thêm thông tin mới.

Sau đó đã nghiên cứu qua alphaXiv, web search và blog của Sebastian Raschka, tìm các phương pháp "boosting" cho hệ multi-agent LLM, rồi tổng hợp thành file **`boosting-novelty-plan-POMA.md`**, với nội dung chính:

- **Chẩn đoán**: các finding của review (F4 — "parallel" không tác động gì vì specialist không thấy output của nhau, temperature 0; F5 — confidence field thu thập nhưng không dùng; F2/F3 — best-of-K khiến "zero regression" ở §5.6 chỉ là hệ quả tất yếu của cách chấm) đều chỉ về cùng một khoảng trống: POMA hiện tại về kiến trúc là **bagging** (specialist độc lập, song song, tổng hợp không trọng số), chứ chưa phải **boosting** như tên gọi ngụ ý.
- **Cơ sở tài liệu tham khảo** (đọc ở mức abstract, chưa verify chi tiết implementation):
  - *Boosting of Thoughts* (ICLR 2024, arXiv:2402.11140) — tiền lệ đặt tên "boosting" cho prompting loop tự sửa lỗi lặp lại.
  - *AgentAuditor* (arXiv:2602.09341, 2/2026) — chứng minh majority vote/best-of-K giả định lỗi các agent độc lập (Condorcet Jury Theorem), giả định này sai với LLM agent cùng bias huấn luyện; adjudication dựa trên evidence thắng majority vote tới 5 điểm.
  - *Two Axes of LLM Abstention* (arXiv:2607.08456, 7/2026) — một ngưỡng confidence duy nhất gộp lẫn hai lỗi khác nhau ("trả lời sai" vs "không nên trả lời") — giải thích trực tiếp vì sao POMA thua FS ở cả hai lớp answerability (F8).
  - *Beyond Majority Voting* (arXiv:2510.01499) — thuật toán tổng hợp có trọng số (Optimal Weight, ISP) thay cho majority vote thường.
  - *EDGE* (arXiv:2609.01360), *ReM-MoA* (arXiv:2606.24437) — lỗi trong hệ multi-agent thường là chuỗi nhiều lỗi liên quan, và chỉ thêm layer agent không tự động giúp nếu thiếu cơ chế tổng hợp.
  - *MoRSE* (arXiv:2608.09251), *MATA* (ACL Findings 2026, arXiv:2602.09642), *Mixture-of-Minds* (Meta, arXiv:2510.20176) — các hệ multi-agent Table QA/role-decomposition khác xuất hiện trong 2026, cần trích dẫn và phân biệt rõ để tránh lặp lại tình huống "bỏ sót ViPanelTR" (Part D của review).
  - Taxonomy inference-time scaling của Sebastian Raschka (bài "Categories of Inference-Time Scaling", 1/2026): CoT → Self-Consistency → Best-of-N → Rejection Sampling with Verifier → Self-Refinement → Search — POMA hiện nay chỉ nằm ở đầu rẻ/yếu nhất (CoT có route + best-of-K không trọng số).
- **Kiến trúc đề xuất — "POMA-Boost"**: thêm (1) disagreement-triggered boosting gate (chỉ kích hoạt agent sửa lỗi khi các specialist bất đồng — giữ chi phí thấp, biến điểm yếu ngân sách F10 thành điểm mạnh), (2) confidence-weighted single-answer combination (thay best-of-K), (3) two-axis answerability decoupling (tách riêng "đáp án đúng không" và "câu hỏi trả lời được không").
- **RQ4, RQ5** nối tiếp RQ1–RQ3 đã có trong file `.docx`.
- **Bảng thí nghiệm mới**, gắn vào đúng vị trí trong trình tự Tier 1/Tier 2 của `fix-plan-POMA.md`.
- **Bảng phân biệt** với ViPanelTR/MATA/MoRSE/Mixture-of-Minds để tránh rủi ro "trùng lặp chưa công bố" lần thứ hai.
- **Cập nhật lựa chọn tạp chí**: TALLIP vẫn là lựa chọn an toàn #1; nếu boosting thành công thật sự, KBS (Q1) trở thành mục tiêu khả thi hơn thay vì chỉ là lựa chọn xa vời.

*(Toàn văn kế hoạch nằm trong `boosting-novelty-plan-POMA.md`.)*

---

## Q3. Hiện tại đâu là những giới hạn **then chốt** của bài báo cần phải reframe/redesign, hoặc đề xuất một cách tiếp cận mới để xử lý?

**A3.**
Bài báo có hai loại vấn đề khác nhau, và chỉ một loại cần redesign thật sự.

**Không cần thiết kế lại — chỉ cần viết lại trung thực + chạy code đã có sẵn:**
- W1/F1 — khung "orchestration" overclaim so với chính số liệu Table 6 (AN chiếm ~90% mức tăng EM)
- W2 — mâu thuẫn số học giữa Table 6 và §5.6 (68.41 vs 62.40)
- W5 — một backbone, không có CI, câu văn "hết ngân sách" mâu thuẫn với Table 7
- W7 — chưa trích dẫn ViPanelTR dù trùng lặp

Tất cả đều là Tier 1 trong `fix-plan-POMA.md` — chạy runbook đã có, đối chiếu lại số liệu, thêm trích dẫn.

**Cần thiết kế lại — bài báo không thể tự sửa chỉ bằng viết lại hay chạy thêm baseline, vì thiết kế hiện tại không có cơ chế nào làm việc đó:**

| # | Giới hạn | Vì sao then chốt | Vì sao viết lại/thí nghiệm thêm không đủ |
|---|---|---|---|
| **F4** | Specialist "parallel" không có tác động nào lên accuracy về mặt cấu trúc — các agent không thấy output của nhau, temperature bằng 0 | Đây là từ khóa chủ đạo trong tiêu đề, mà lại không có tác dụng nhân quả nào | Không thể ablation ra một "parallel" có tác dụng — pipeline phải thực sự cho phép các specialist sửa lỗi cho nhau |
| **F5** | Trường confidence mà mọi specialist trả về không hề được dùng ở đâu | Cho thấy thiết kế thu thập một tín hiệu nhưng không hành động theo nó | Không có gì để báo cáo — chưa có logic tổng hợp nào dùng tới nó |
| **F2/F3/W3** | Chấm điểm best-of-K nghĩa là "thêm candidate không bao giờ làm giảm điểm" — nhận định "zero regression" ở §5.6 chỉ là hệ quả tất yếu | Đây chính là cơ chế đứng sau F1: nếu không sửa, không thể biết orchestration có thực sự làm gì hay không | Nêu rõ K và chấm đối xứng (Tier 1) chỉ cho thấy sự bất cân xứng — không thay thế best-of-K bằng một luật quyết định thật |
| **F8/W4** | POMA kém hơn chính baseline FS của nó ở **cả hai** lớp answerability | Đây là con số dễ bị reviewer soi nhất; motivation hứa hẹn answerability tốt hơn nhưng lại kém đi | Một điểm confidence duy nhất (Null-vs-answer) đang phải làm hai việc (đáp án đúng không? / câu hỏi trả lời được không?) — không thể tách hai việc này chỉ bằng cách thêm baseline |

Bốn điểm này chính là những gì kế hoạch boosting nhắm tới: một bước sửa lỗi kích hoạt theo mức độ bất đồng cho "parallel" một việc thật để làm và cuối cùng dùng đến trường confidence (F4/F5); một cách tổng hợp có trọng số ra một đáp án duy nhất thay cho best-of-K (F2/F3/W3); một luật answerability hai trục (tách riêng correctness-confidence và answerability-confidence) nhắm thẳng vào F8 — finding duy nhất hiện chưa có cách nào bảo vệ.

Một điểm nữa đáng gắn cờ là "cần thiết kế lại nhưng ưu tiên thấp hơn" — 10 specialist khớp 1:1 với đúng 10 nhãn hint của Open-ViTabQA, nên có rủi ro thật là overfit vào taxonomy của một dataset (docx §4, điểm 1). Điểm này lớp boosting không sửa được, và cũng không rẻ để sửa cho đàng hoàng, nên nên để lại làm future work thay vì cố redesign dưới áp lực deadline — đúng như cách chính bài review cũng khuyến nghị.

---

## Q4. Vậy các phương pháp cụ thể là gì? Và về điểm AN mới là đòn bẩy chính, không phải multi-agent orchestration — giải thích thế nào? Cách giải quyết ra sao?

**A4.**

### Các phương pháp (tóm tắt)

| Phương pháp | Làm gì | Xử lý vấn đề gì |
|---|---|---|
| **Disagreement-triggered boosting gate** | Tính tín hiệu bất đồng giữa các specialist; chỉ khi chúng mâu thuẫn (hoặc hedge Null+answer), mới gọi một agent "Booster" mới để giải quyết mâu thuẫn hoặc abstain | F4 (parallel không tác động gì), F5 (confidence không dùng) |
| **Confidence-weighted single-answer combination** | Thay best-of-K bằng weighted vote dựa trên confidence đã calibrate — ra một câu trả lời duy nhất, không phải "candidate nào trong set cũng được tính khớp" | F2/F3/W2/W3 (bất cân xứng best-of-K) |
| **Two-axis answerability decoupling** | Hỏi hai câu riêng — "đáp án này có đúng không?" vs "câu hỏi này có trả lời được không?" — abstain dựa trên trục thứ hai một cách độc lập | F8/W4 (kém hơn baseline FS ở cả hai lớp answerability) |

### Vì sao AN mới là đòn bẩy chính, không phải orchestration — giải thích

Đây là câu hỏi thú vị hơn, và chính số liệu trong bài đã gợi ý một chẩn đoán cụ thể:

**Metric (EM/F1/R1/MET) nhạy với surface-form, và nút thắt thật sự của backbone trên benchmark này chủ yếu nằm ở format, không phải ở việc tìm evidence.**

Ba bằng chứng từ chính bài báo ủng hộ điều này:

1. **TD và CoT đều điểm thấp hơn ZS (F7).** Nếu nút thắt thật sự là reasoning/chọn evidence, thêm decomposition hoặc chain-of-thought vào một lượt gọi lẽ ra phải giúp ích, hoặc ít nhất trung tính. Nhưng nó lại làm giảm điểm — điều này không khớp với "reasoning là phần khó", mà khớp hơn với "thêm text reasoning trên đường tới câu trả lời chỉ tạo thêm cơ hội để chuỗi output bị lộn xộn, format không nhất quán".
2. **Specialist chạy độc lập, một lượt, không có bước sửa lỗi (F4).** Prompt của specialist tập trung hơn few-shot chung, nhưng không cho model thêm thông tin nào mới, không có cách nào để tự kiểm tra evidence hay bắt lỗi chọn sai hàng/cột. Nên mức tăng accuracy từ routing lẽ ra phải nhỏ — đó là prompt specialization, không phải error correction — và đúng như Table 6 cho thấy: chỉ ~1.27 EM so với FS, trước khi có AN.
3. **Các thao tác thật sự của AN** — bỏ giải thích thừa, chuẩn hóa yes/no tiếng Việt, chuẩn hóa ngày/số/dấu phân cách list — **là fix trực tiếp cho đúng thứ mà EM phạt nặng nhất.** Qwen3-8B nhiều khả năng đã trích đúng giá trị phần lớn thời gian; chỉ là nó không xuất ra đúng chuỗi ký tự y hệt reference answer. AN đóng khoảng cách đó lại, và vì khoảng cách này lớn nhưng thuần túy hình thức, nó cộng ~11.8 EM.

Nên cách đọc trung thực nhất: **bài báo chẩn đoán đúng một vấn đề 4 phần ở §1 (grounding, reasoning, answerability, formatting đều dồn vào một lượt gọi), và xây hạ tầng cho 2 phần đầu, nhưng trên backbone+benchmark này, phần thứ 4 (formatting) mới là chỗ có nhiều dư địa cải thiện thật sự.** Specialist không giúp được nhiều không phải vì ý tưởng sai, mà vì một lượt few-shot mạnh vốn không để lại nhiều lỗi reasoning thật sự để mà phân rã ra sửa.

### Cách giải quyết

Hai bước, theo đúng thứ tự — đừng nhảy sang bước 2 mà bỏ qua bước 1:

**1. Đo đúng kích thước đóng góp thật của orchestration, một cách công bằng.** Hiện tại chưa thể biết ~1.27 EM (routing, trước AN) là thật hay chỉ là nhiễu, vì FS chưa từng được áp AN. Áp cùng module AN lên ZS/CoT/FS, chấm single-answer (không best-of-K), rồi xem còn lại bao nhiêu. Phần này đã build và test sẵn (`fix-plan-POMA.md` Tier 1) — đây là điều kiện tiên quyết, và rất có thể nó sẽ cho thấy đóng góp thật của orchestration là ~0 hoặc âm một khi confound về formatting được loại bỏ đối xứng ở cả hai phía.

**2. Nếu phần còn lại nhỏ (nhiều khả năng, theo F7), đừng cố nhồi thêm decomposition — nhắm vào đúng loại lỗi mà AN không sửa được.** AN dọn surface form; nó không thể sửa việc chọn sai hàng, bỏ sót điều kiện lọc multi-condition, hay đọc sai merged cell. Đó mới là lỗi reasoning thật sự, và trên backbone này chúng đủ hiếm để các specialist độc lập hiếm khi tạo ra bất đồng về chúng. Nên cách sửa không phải "thêm specialist" — mà là một cơ chế chuyên tìm và phân xử đúng những case mà các specialist bất đồng (disagreement gate ở trên), vì bất đồng là triệu chứng có thể quan sát được của một lỗi evidence-selection thật, không phải lỗi format. Đó là cách duy nhất khả dĩ để orchestration thắng được FS+AN: không phải bằng reasoning tốt hơn ở 90% câu dễ, mà bằng cách bắt được đúng lỗi thật ở phần khó, nơi một lượt đọc bảng bị sai.

Nếu ablation ở bước 2 vẫn không cho thấy gì vượt FS+AN dưới single-answer scoring công bằng, fallback trung thực là khung RQ2 đã có sẵn trong kế hoạch docx: công bố chính phát hiện AN-vs-orchestration làm kết quả chính ("với câu trả lời ngắn gọn tiếng Việt, surface-form normalization quan trọng hơn reasoning decomposition") — một kết quả hợp lệ, có thể trích dẫn, chỉ là không phải bài đang viết hiện tại.

---

*Xem thêm: `review-POMA-JIT.md` (review kỹ thuật gốc), `fix-plan-POMA.md` (fix bắt buộc + code đã có sẵn), `journal-selection-POMA.md` (câu hỏi chọn tạp chí), `boosting-novelty-plan-POMA.md` (kế hoạch tăng novelty chi tiết).*
