# POMA-Boost v2 — kế hoạch approach mới, grounded bằng research thực tế

**Ngày:** 2026-09-18
**Phương pháp:** 5 agent research song song (arXiv/alphaXiv, blog ML, kiểm tra lại repo GitHub) — xem chi tiết từng agent ở cuối file.
**Ràng buộc giữ nguyên (theo yêu cầu):** low-resource (không fine-tune, chỉ gọi API model có sẵn — Qwen3-8B/Gemma-3-4B-IT qua OpenRouter), multi-agent làm kiến trúc trọng tâm, task + dataset giữ nguyên (Vietnamese Table QA, Open-ViTabQA).

---

## 0. Việc đầu tiên: xác nhận repo chưa đổi gì

Agent kiểm tra lại repo (`NgDinhKhoi0709/POMA`, HEAD `50e3a217`, commit cuối 2026-08-21) xác nhận: **toàn bộ 12 claim trong `fix-plan-POMA.md` vẫn đúng**, chưa có gì thay đổi trong ~4 tuần qua. `outputs/q2_revision/` vẫn chưa tồn tại — nghĩa là **Tier 1 của `fix-plan-POMA.md` (chạy runbook có sẵn) vẫn là việc phải làm trước, mọi thứ dưới đây là RQ4/RQ5 nối tiếp sau khi có kết quả Tier 1**, không thay thế nó.

Một chi tiết nhỏ: `run_revision_analysis.py` không có hàm tên `interpretation_gate` như mô tả cũ — nó là một **key trong dict** `build_report()` (logic tương đương vẫn có: EM gain ≥0.02 và CI bootstrap loại trừ 0). Không ảnh hưởng kế hoạch, chỉ là sai sót nhỏ trong tài liệu trước.

---

## 1. Xác minh lại các paper đã trích dẫn trong plan cũ

Tất cả agent đều được yêu cầu **verify độc lập**, không tin lại mô tả cũ. Kết quả: **không có paper nào bị hallucinate** — tất cả arXiv ID khớp đúng tiêu đề:

| Paper cũ | arXiv ID | Trạng thái |
|---|---|---|
| Boosting of Thoughts (ICLR 2024) | 2402.11140 | ✅ xác nhận |
| AgentAuditor | 2602.09341 | ✅ xác nhận (tên đầy đủ: "Auditing Multi-Agent LLM Reasoning Trees Outperforms Majority Vote and LLM-as-Judge") |
| Beyond Majority Voting | 2510.01499 | ✅ xác nhận |
| EDGE | 2609.01360 | ✅ xác nhận |
| ReM-MoA | 2606.24437 | ✅ xác nhận |
| Two Axes of LLM Abstention | 2607.08456 | ✅ xác nhận (Wagner, City St George's, 2026-07-09) |

→ Có thể yên tâm trích dẫn các paper này. Nhưng **research mới cho thấy có phương án tốt hơn/mới hơn** cho gần như mọi thành phần — xem bên dưới.

---

## 2. Chẩn đoán không đổi, nhưng có thêm bằng chứng lý thuyết

Giữ nguyên chẩn đoán cũ: POMA hiện tại là **bagging** (agent độc lập, song song, không thấy nhau, vote không trọng số) chứ không phải **boosting**. Hai paper mới củng cố thêm *tại sao* bagging không nên được kỳ vọng giúp ích ở đây:

- **"A Latent Dimension of Condorcet's Jury Theorem"** (arXiv:2609.14438) — bất đồng quan sát được giữa các LLM panelist tăng nhanh hơn độ tin cậy khi tăng số agent.
- **"Nine Judges, Two Effective Votes"** (arXiv:2605.29800) — lỗi tương quan (correlated errors) giữa các LLM nghĩa là panel N-agent thường có số "vote hiệu lực" ít hơn N rất nhiều.

→ Dùng hai paper này làm cơ sở lý thuyết trong bài, giải thích vì sao thiết kế 10-specialist song song không tự động đáng tin hơn 1 lần gọi.

---

## 3. Kiến trúc đề xuất — "POMA-Boost v2"

Điểm mới quan trọng nhất so với plan cũ: **Anthropic's multi-agent research system** (tìm thấy qua blog Simon Willison, tóm tắt lại bài kỹ thuật gốc của Anthropic) không phải bagging đối xứng — nó dùng **visibility bất đối xứng**: các subagent chạy độc lập/mù (giữ nguyên chi phí thấp), nhưng có **một lead/aggregator agent duy nhất nhìn thấy TẤT CẢ output** và chỉ tổng hợp/escalate khi cần. Đây chính là mảnh còn thiếu trong POMA, và rẻ hơn nhiều so với việc làm specialist thấy nhau (sẽ làm mất tính "parallel", tăng chi phí N×N).

### Sơ đồ

```
10 specialist (giữ nguyên: độc lập, song song, temperature 0)
        │  (answer, evidence, confidence, reason) × N specialist kích hoạt
        ▼
┌─────────────────────────────────────────┐
│  Aggregator agent (MỚI — 1 lệnh gọi/câu) │  ← nhìn thấy tất cả output specialist
│  - Tính disagreement signal (số answer   │
│    khác nhau sau AN, có/không hedge Null)│
└─────────────────────────────────────────┘
        │
        ├── ĐỒNG THUẬN (dự kiến ~80-90% câu, khớp với phần "dễ" mà FS+AN đã giải quyết tốt)
        │       → nhận consensus answer, KHÔNG gọi thêm — chi phí ≈ pipeline hiện tại
        │
        └── BẤT ĐỒNG / hedge (Null + answer cùng lúc)
                → escalate: chỉ nhóm câu này mới trả thêm chi phí
                │
                ├── (a) Row/Column grounding verifier — kiểm tra candidate có khớp
                │       đúng cell đã trích dẫn không (Table-Critic / DRE-style)
                ├── (b) Tie-breaker bằng câu hỏi phân biệt (S*-style) — sinh 1
                │       sub-query mới để phân xử giữa các candidate bất đồng,
                │       thay vì vote mù
                └── (c) Weighted consolidation (OW/ISP) thay best-of-K —
                        trọng số theo confidence đã hiệu chỉnh (MARGIN), ra
                        MỘT câu trả lời duy nhất, chấm single-answer
```

**Vì sao rẻ (giữ đúng constraint low-resource):** chỉ nhóm câu bất đồng mới tốn thêm lệnh gọi. Bài báo hiện tại đã tự chứng minh 1 lần chạy POMA đầy đủ tốn $2.06 (Table 7) — thêm 1 aggregator call/câu (992 câu) + verifier chỉ trên tập con bất đồng vẫn nằm trong ngân sách tương tự.

### 3.1. Thành phần cụ thể, map trực tiếp vào từng finding của review

| Thành phần | Nguồn (verified) | Sửa finding nào |
|---|---|---|
| **Aggregator bất đối xứng** (nhìn tất cả, escalate có điều kiện) | Anthropic multi-agent system (qua Simon Willison blog) + Context Quarantine pattern (Drew Breunig) | F4 (parallel không có tác dụng cấu trúc) — giờ "song song" thực sự dẫn tới một quyết định tổng hợp có điều kiện |
| **Disagreement-triggered escalation** | Minority Sentinel (arXiv:2606.29270) — dùng disagreement fingerprint để quyết định khi nào lật lại consensus | F4, F10 (ngân sách) — biến điểm yếu "budget" cũ thành lợi thế: chi phí tỉ lệ với độ khó câu hỏi |
| **Row/Column grounding verifier** | DRE paper (arXiv:2606.32029) — đo & sửa lỗi trích dẫn sai hàng/cột **trên đúng backbone Qwen3-8B**; Table-Critic (arXiv:2502.11799) — 4-agent Judge/Critic/Refiner, node lỗi phân loại rõ Row Error/Column Error, +6.3% WikiTQ | Lỗi reasoning thật (chọn sai hàng/cột/merged cell) — đúng loại lỗi mà AN không sửa được |
| **Tie-breaker qua discriminating query** | S* test-time scaling (arXiv:2502.14382, qua bài Raschka) | Khi 2 candidate bất đồng, không vote mù mà sinh câu hỏi phụ để phân xử — cụ thể, ít tốn kém |
| **Critique/Edit tách vai** | Dedicated Feedback and Edit Models (arXiv:2503.04378) | Nếu cần sửa answer, dùng agent critique riêng + agent edit riêng — tránh 1 agent vừa chê vừa tự sửa (kém tin cậy hơn theo paper này) |
| **Weighted consolidation thay best-of-K** | Beyond Majority Voting — Optimal Weight / ISP (arXiv:2510.01499) | F2/F3/W2/W3 — thay "thêm candidate không bao giờ giảm điểm" bằng trọng số thật, chấm single-answer |
| **Hiệu chỉnh confidence trước khi dùng làm trọng số** | MARGIN (arXiv:2605.22949) — online calibration không cần train | Raw confidence tự báo cáo của LLM đã biết là kém hiệu chỉnh — không nên dùng thẳng làm trọng số |
| **Correctness-confidence** (trục 1) | COMPETE (Feng et al., arXiv:2402.00367) — chèn 1 câu trả lời thay thế hợp lý từ bảng, xem agent có đổi ý không | F8 (answerability) — tách "câu trả lời này đúng không" |
| **Answerability-confidence** (trục 2, độc lập) | API-only conformal / LofreeCP (arXiv:2403.01216) — resample k lần, dùng entropy + tần suất, không cần logit/fine-tune | F8 — tách riêng "câu hỏi này có trả lời được không", KHÔNG gộp chung với trục 1 (đây chính là nguyên nhân gốc theo paper "Two Axes of LLM Abstention", arXiv:2607.08456 — verified) |

**Lưu ý quan trọng:** paper "Two Axes of LLM Abstention" đề xuất linear probe trên hidden state đạt AUROC 0.97-0.99, nhưng **không dùng được** vì cần truy cập activation/logit — vi phạm ràng buộc "chỉ gọi API". Phần dùng được của paper này là *chẩn đoán* (một tín hiệu duy nhất không thể tách hai loại lỗi — giải thích trực tiếp F8), còn *cơ chế sửa* nên lấy từ COMPETE + LofreeCP (cả hai đều thuần API/prompting).

### 3.2. Thành phần cân nhắc nhưng KHÔNG dùng làm core (ghi chú lý do)

- **DiscoUQ** (arXiv:2603.20975) — tốt nhưng biến thể mạnh nhất cần train một logistic regression nhỏ trên dữ liệu nhãn → chỉ dùng biến thể "LLM Aggregator" zero-training của nó (1 lệnh gọi judge đọc hết reasoning, ra answer+confidence dạng JSON) làm baseline so sánh, không làm core.
- **MATA** (arXiv:2602.09642, ACL Findings 2026) — kiến trúc rất gần POMA (multi-agent + confidence-checker), nhưng Scheduler/Confidence-Checker/Format-Matcher là **classifier nhỏ có train** (MobileBERT/DeBERTa) → chỉ trích dẫn để so sánh/phân biệt, không copy cơ chế.
- **ReM-MoA** (arXiv:2606.24437) — cơ chế boosting-qua-nhiều-vòng thật sự nhưng tốn nhiều lệnh gọi hơn (multi-layer) → để làm stretch goal nếu ngân sách còn dư sau Tier 1.
- **EDGE** (arXiv:2609.01360), **Bayesian Self-Escalation** (arXiv:2608.24087) — liên quan nhưng cần counterfactual rollout / dữ liệu calibration có nhãn, nặng hơn cần thiết → chỉ nêu ở related work.

---

## 4. Rủi ro trùng lặp MỚI phát hiện — cần xử lý trước khi nộp

Ngoài ViPanelTR (đã biết), agent tìm thấy một paper **rất mới, cùng đúng bài toán**:

> **"Vietnamese Question Answering on Tabular Data via Large Language Models"** (Springer, 2026, Son et al., DOI 10.1007/978-3-032-10202-7_31)

Bài này bị paywall (chưa đọc được full text), nhưng tiêu đề khớp gần như y hệt phạm vi của POMA (Vietnamese table QA qua LLM). **Cần lấy được bản đầy đủ và kiểm tra overlap trước khi nộp lại** — cùng rủi ro như trường hợp ViPanelTR (W7 trong review cũ), chỉ khác là đây là nhóm tác giả khác nên là rủi ro "bị scoop" chứ không phải "tự trùng lặp". Ưu tiên: **cao, cần làm sớm** (đọc được bài này có thể đổi cả câu chuyện novelty).

Điểm tích cực: các benchmark SEA khác được tìm thấy (INDOTABVQA cho tiếng Indonesia, SEATauBench) xác nhận Vietnamese/SEA table QA vẫn là ngách ít người làm — ủng hộ novelty ở trục *dataset+ngôn ngữ*, nhưng novelty ở trục *phương pháp* nên dựa vào verifier row/column (mục 3.1) chứ không phải chỉ "làm bằng tiếng Việt".

---

## 5. Thứ tự thực hiện đề xuất (nối tiếp `fix-plan-POMA.md`)

1. **(Đã có, blocking)** Tier 1 của `fix-plan-POMA.md`: chạy runbook, áp AN lên baseline, chấm single-answer, 2 backbone, bootstrap CI, hint metrics — **chưa đổi gì, vẫn phải làm trước tiên.**
2. **Kiểm tra rủi ro trùng lặp**: tìm cách đọc bài Son et al. 2026 (mục 4) — song song với bước 1, không cần chờ.
3. **Sau khi có số liệu Tier 1**, nếu orchestration thật sự đóng góp gần 0 (khả năng cao theo F7/F4 cũ) → triển khai POMA-Boost v2 theo đúng thứ tự trong bảng mục 3.1:
   a. Aggregator + disagreement gate (rẻ nhất, tác động lớn nhất tới F4)
   b. Weighted consolidation thay best-of-K (sửa F2/F3 trực tiếp)
   c. Row/column verifier trên tập bất đồng (nhắm đúng lỗi reasoning thật)
   d. Two-axis answerability (COMPETE + LofreeCP) — sửa F8
4. **Đo lại toàn bộ** bằng đúng runbook đã có (single-answer scoring, symmetric AN, bootstrap CI) — không cần hạ tầng đánh giá mới, hạ tầng cũ đã đủ.
5. Nếu POMA-Boost v2 thắng FS+AN có ý nghĩa thống kê → KBS (Q1) khả thi hơn; nếu không → TALLIP vẫn là lựa chọn an toàn (theo `journal-selection-POMA.md`), và kết quả "AN + verifier bất đồng > orchestration ngây thơ" vẫn là một finding hợp lệ để công bố.

---

## Phụ lục: chi tiết 5 agent research (tóm tắt)

1. **Multi-agent boosting/aggregation scout** — verify 5 paper cũ (tất cả thật), tìm thêm Minority Sentinel (2606.29270), CONCAT (2605.29612), MARGIN (2605.22949), 2 paper lý thuyết Condorcet.
2. **Selective prediction/abstention scout** — verify "Two Axes" (thật), tìm COOPERATE/COMPETE (2402.00367), LofreeCP (2403.01216), DiscoUQ (2603.20975).
3. **Table QA/low-resource scout** — tìm DRE paper trên đúng backbone Qwen3-8B (2606.32029), Table-Critic (2502.11799), MATA (2602.09642), PanelTR (2508.06110), và cảnh báo bài Son et al. 2026 (mục 4).
4. **Blog scan (Sebastian Raschka + Simon Willison)** — taxonomy self-consistency/best-of-N/rejection-sampling-with-verifier, S* tie-breaker, TPO contrastive critique, và insight quan trọng nhất: kiến trúc bất đối xứng của Anthropic's multi-agent system.
5. **Repo state check** — xác nhận repo chưa đổi gì kể từ `fix-plan-POMA.md` (17/9), Tier 1 vẫn chưa chạy.

*Xem thêm: `review-POMA-JIT.md`, `fix-plan-POMA.md`, `journal-selection-POMA.md`, `POMA-review-session-QA.md`.*
