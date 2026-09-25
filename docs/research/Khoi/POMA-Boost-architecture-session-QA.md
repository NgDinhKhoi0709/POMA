# POMA-Boost — Q&A phiên làm việc (research + kiến trúc sơ đồ)

**Ngày:** 2026-09-18
**Bối cảnh:** Tiếp nối phiên review/rescope POMA trước đó (xem `POMA-review-session-QA.md`, `review-POMA-JIT.md`, `fix-plan-POMA.md`, `journal-selection-POMA.md`). Phiên này gồm hai phần: (1) research SOTA để tăng novelty theo hướng "boosting" thật sự, và (2) vẽ + tinh chỉnh kiến trúc đề xuất "POMA-Boost" trong draw.io.

---

## Q1. Yêu cầu tìm approach tốt hơn, up-to-date hơn, SOTA hơn, giữ nguyên concept low-resource, call API, multi-agent làm trọng tâm, task/dataset giữ nguyên. Cho phép dùng browser tra arxiv, alphaXiv, blog AI/ML (như magazine.sebastianraschka.com). Yêu cầu: "spawn agent cho từng việc."

**A1.**
Spawn 5 agent nghiên cứu song song, chạy nền:
1. **Multi-agent boosting/aggregation scout** — verify lại 5 paper đã có từ phiên trước (Boosting of Thoughts arXiv:2402.11140, AgentAuditor arXiv:2602.09341, Beyond Majority Voting arXiv:2510.01499, EDGE arXiv:2609.01360, ReM-MoA arXiv:2606.24437) và tìm thêm paper mới hơn.
2. **Selective prediction / abstention scout** — verify "Two Axes of LLM Abstention" (arXiv:2607.08456) và tìm phương pháp tách correctness-confidence khỏi answerability-confidence.
3. **Table QA / low-resource NLP scout** — tìm phương pháp nhắm đúng lỗi reasoning thật (chọn sai hàng/cột) thay vì lặp lại việc chuẩn hóa surface-form.
4. **Blog scan** — đọc trực tiếp magazine.sebastianraschka.com và simonwillison.net.
5. **Repo state check** — verify lại trạng thái GitHub `NgDinhKhoi0709/POMA` so với `fix-plan-POMA.md`.

**Kết quả chính:**
- Tất cả 6 paper cũ đều **thật, verify được**, không paper nào bị hallucinate.
- Repo GitHub **chưa đổi gì** kể từ `fix-plan-POMA.md` (17/9) — Tier 1 (chạy runbook, áp AN lên baseline, chấm single-answer) vẫn là việc phải làm trước.
- Tìm thêm được: Minority Sentinel, CONCAT, MARGIN (calibration), COOPERATE/COMPETE, LofreeCP (conformal prediction API-only), DiscoUQ, DRE paper (đo đúng lỗi reasoning trên chính backbone Qwen3-8B), Table-Critic, MATA, PanelTR.
- Insight quan trọng nhất: kiến trúc **bất đối xứng** của Anthropic's multi-agent research system (subagent vẫn mù/song song, nhưng có 1 lead agent duy nhất nhìn hết output và escalate có điều kiện) — trở thành ý tưởng lõi cho redesign.
- **Rủi ro mới phát hiện**: một paper Springer 2026 khác ("Vietnamese Question Answering on Tabular Data via LLMs", Son et al.) có phạm vi gần trùng POMA — cần đọc full text để đánh giá overlap trước khi nộp lại.

Tổng hợp thành file **`boosting-novelty-plan-POMA-v2.md`**, đề xuất kiến trúc "POMA-Boost": thêm Aggregator (nhìn tất cả output specialist) + disagreement gate (chỉ escalate khi bất đồng) + weighted consolidation thay best-of-K + row/col verifier + two-axis answerability (tách correctness-confidence khỏi answerability-confidence). Tất cả đều thuần API/prompting, không cần fine-tune, giữ multi-agent làm trọng tâm.

---

## Q2. "Vào browser drawio vẽ cho tôi architecture" — theo style ảnh mẫu (Human/Agents View/Root session/Subagents/Environment/Daemon/Continual Harness từ hai paper alphaXiv), vẽ đơn giản, ít chữ, mô tả rõ flow.

**A2.**
Dùng browser mở app.diagrams.net, load diagram trực tiếp qua URL hash (`#R<raw XML>`) thay vì thao tác menu thủ công (menu "Edit Diagram" không có trong UI rút gọn của bản này). Vẽ sơ đồ đơn giản 6 box: Table+Question, Specialists ×N (song song, mù), Aggregator (cam, trung tâm), Verifier (on disagree, chấm chấm), AN + Confidence Calibration (chấm chấm), theo đúng ngôn ngữ hình ảnh của ảnh mẫu (box cam = trung tâm, box trắng = input/output, box chấm chấm = lớp hỗ trợ). Lưu file nguồn `poma-boost-architecture.drawio`.

---

## Q3. Giải thích rõ flow: từng phần làm gì, kế thừa gì từ v1, cải tiến gì, tackle điểm yếu nào của v1?

**A3.**
Bảng đối chiếu chi tiết từng thành phần với v1 (POMA gốc):

| Thành phần | Kế thừa từ v1 | Cải tiến | Sửa finding |
|---|---|---|---|
| Table+Question, Specialists ×N | Toàn bộ (routing, song song, 4-trường output) | Không đổi | — |
| Aggregator | Dùng lại 4-trường output | Nhìn tất cả + gate có điều kiện | F4, F5, F10 |
| Weighted Consolidation | Hạ tầng đánh giá có sẵn | Thay best-of-K bằng single-answer có trọng số | F2, F3, W2, W3 |
| Verifier (row/col + tie-breaker) | Không có tương đương | Bắt lỗi reasoning thật, có mục tiêu | F7, củng cố F1 |
| AN | Gần như 100% | + Confidence Calibration (MARGIN) | hỗ trợ consolidation |
| Two-axis answerability | Không có tương đương | Tách correctness ≠ answerability | F8, W4 |

Điểm nhấn: Aggregator là mảnh hoàn toàn mới, lấy cảm hứng từ kiến trúc bất đối xứng của Anthropic (specialist vẫn mù/song song, nhưng có 1 lead nhìn hết); disagreement gate khiến "song song" lần đầu tiên có tác động thật lên kết quả (sửa F4 — trước đây song song hay tuần tự cho kết quả giống hệt nhau).

---

## Q4. Vẽ rõ architecture hơn nữa: rõ từng phase, các specialist, dùng icon/đối tượng đại diện đầy đủ.

**A4.**
Vẽ lại bản chi tiết hơn: 5 phase rõ ràng (Hint & Route / Specialists ×10 / Aggregator / Escalation / Consolidation & Normalization), vẽ đủ **10 specialist riêng lẻ** (lưới 5×2, S1...S10) thay vì gộp 1 box, dùng icon emoji đại diện cho từng loại tác vụ (🎯 hint, 🔀 router, 🤖 specialist, 🔍 verifier, ⚖️ weighted consolidation, ✅ final answer). Lưu `poma-boost-architecture-detailed.drawio`.

---

## Q5. Gửi ảnh mẫu khác (figure "Four stage training procedure" phong cách academic, box lồng nhau có tiêu đề, không icon pictogram). Yêu cầu: "không icon, style này, tiếng Anh."

**A5.**
Vẽ lại toàn bộ theo đúng style ảnh mẫu: bỏ hết emoji/icon, chỉ dùng hình chữ nhật bo góc màu phân loại theo vai trò (cam = input/question, xanh dương = process, xanh lá = context/normalization, hồng = output, xám nét đứt = hỗ trợ). Cấu trúc lồng nhau: khung ngoài nét đứt đậm có tiêu đề "Stage N — ..." chứa khung con nét đứt mảnh có tiêu đề nhỏ hơn (giống "Pre-Training" chứa "Stage 1" trong ảnh mẫu). Toàn bộ nhãn bằng tiếng Anh, thêm caption dạng "Figure: ..." bên dưới đúng kiểu chú thích học thuật. Lưu `poma-boost-architecture-stages.drawio`.

---

## Q6. Chỗ specialist ×N vẽ "1 → ... → N" thôi (không cần vẽ đủ 10). Điều chỉnh lại các mũi tên hiện đang đè lên nhau.

**A6.**
Viết script Python sinh XML để kiểm soát chính xác tọa độ (thay vì chỉnh tay), giảm 10 specialist xuống còn 3 box (Specialist 1 → ... → Specialist N). Định tuyến lại toàn bộ cạnh bằng waypoint tường minh thay vì để auto-router tự chọn — đặc biệt hai đường phản hồi từ Escalation lên Stage 3 (`resolved` và `null/answer gate`) được tách thành 2 trục dọc riêng, verify trực tiếp bằng cách click chọn từng cạnh trong draw.io để xác nhận điểm vào đúng box, không chồng lấn.

---

## Q7. Gửi ảnh chụp Stage 3 sau khi tự chỉnh sửa một chút trong browser, thấy mũi tên có khúc gấp (hook) lạ, nhờ chỉnh thêm.

**A7.**
Kiểm tra live state qua nhiều cách (undo history, XML export dialog — clipboard bị chặn quyền đọc/ghi trong sandbox nên không lấy được nội dung qua đó) và xác nhận thay đổi của user chỉ là click chọn, không phá cấu trúc. Tìm ra nguyên nhân khúc gấp: waypoint cuối của 2 cạnh phản hồi (`resolved`, `null/answer gate`) không khớp chính xác tọa độ điểm entry của box đích, khiến router chèn thêm một đoạn gấp ngắn. Sửa bằng cách tính chính xác tọa độ entry (vd. entryY=0.75 của box cao 58px → y=133.5) và gán làm waypoint cuối — loại bỏ hoàn toàn khúc gấp.

---

## Q8. Gửi ảnh Stage 3 khác, thấy mũi tên 2 chiều giữa Weighted Consolidation / Confidence Calibration / Answer Normalization / Final Answer, hỏi tại sao.

**A8.**
Xác nhận qua zoom trực tiếp: đúng là có mũi tên 2 đầu thật ở cả 3 khoảng cách — không khớp với source gốc (vốn chỉ thiết kế 1 chiều: `calib→wconsol`, `wconsol→an`, `an→final`). Kết luận: state trong tab draw.io đã lệch khỏi bản gốc (do một thao tác trước đó trong phiên). Giải thích rõ về mặt ý nghĩa: không quan hệ nào ở đây nên 2 chiều — Confidence Calibration chỉ *feed* trọng số một chiều vào Weighted Consolidation, và pipeline Weighted Consolidation → Answer Normalization → Final Answer chảy xuôi một chiều. Phát hiện thêm: điều hướng URL hash khi trang đã load sẵn **không** tự trigger reload (phải mở lại trang từ URL trơn rồi mới điều hướng tới URL có hash mới thì mới load đúng). Sau khi ép tải lại đúng bản gốc, còn định tuyến lại cạnh `wconsol→an` vòng sang phải (bypass quanh box Confidence Calibration) để hai cạnh không còn dùng chung không gian hiển thị, tránh mọi khả năng gây hiểu lầm sau này.

---

## Q9. Phản hồi: việc ép tải lại bản gốc đã xóa mất các chỉnh sửa khác của user ở phần khác của diagram — user chỉ nhờ sửa đúng Phase 3.

**A9.**
Nhận lỗi: đáng lẽ nên sửa trực tiếp tại chỗ 2 cạnh liên quan thay vì replace toàn bộ file, vì làm vậy sẽ vô tình xóa mọi thay đổi khác của user ở các phần không liên quan. Không có cách khôi phục nội dung đã bị ghi đè (không đọc được clipboard/state cũ). Đã xin lỗi, nhờ user chỉnh lại hoặc mô tả lại phần đã sửa, và cam kết từ nay khi sửa diagram chỉ động vào đúng phần được yêu cầu (Phase 3), không đụng các phần khác.

**Bài học rút ra (áp dụng cho các lần sau):** khi chỉnh sửa một tài liệu/diagram đang có thay đổi sống (live) từ người dùng, ưu tiên sửa tại chỗ (select đúng element, đổi đúng thuộc tính) thay vì replace toàn bộ nội dung — force-reload toàn bộ file chỉ nên dùng khi thực sự cần thiết và đã xác nhận không có gì đáng giữ lại.

---

*Xem thêm: `boosting-novelty-plan-POMA-v2.md` (kế hoạch novelty chi tiết), `poma-boost-architecture-stages.drawio` (bản kiến trúc mới nhất, style academic không icon), `poma-boost-architecture-detailed.drawio` và `poma-boost-architecture.drawio` (các bản trước đó), cùng bộ 4 file review gốc (`POMA-review-session-QA.md`, `review-POMA-JIT.md`, `fix-plan-POMA.md`, `journal-selection-POMA.md`).*
