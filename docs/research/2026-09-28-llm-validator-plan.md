# Kế hoạch: LLM Validator cho MemXam-SC-KV (2026-09-28)

Câu hỏi: thay Validator tất định bằng một agent LLM kiểm tra thì có cải thiện EM/BIF không, và ghép vào
pipeline hiện tại thế nào cho hợp lý. Mọi số liệu dưới đây đo trên trace v8 dev (983 câu, luật v7, sau
agent định dạng), không tốn lệnh gọi mới.

## 1. Trả lời ngắn

**Không thay, mà thêm tầng.** Validator tất định chỉ tác động 28/983 câu (loại 33 ứng viên: 28 rỗng hoặc
không parse được, 5 sai loại Có/Không) và đóng góp +0,10 EM, nhưng gần như không sai và không tốn gì. Một
LLM không "kiểm tra" được đáp án rỗng hay JSON hỏng tốt hơn luật. Giá trị của LLM chỉ có thể đến từ kiểm
tra ngữ nghĩa (đúng ô, đúng hàng, đúng điều kiện), và chỉ đáng gọi ở vùng hệ thống đang yếu.

## 2. Lỗi nằm ở đâu (headroom)

| Vùng (dev) | Số câu | Đúng | Sai | Sai nhưng có ứng viên đúng trong pool |
|---|---:|---:|---:|---:|
| Đồng thuận 4/4 | 779 | 91,1% | 69 | 0 (không có ứng viên khác) |
| Đồng thuận 3/4 | 111 | 58,6% | 46 | 21 (phiếu thiểu số đúng) |
| Tranh chấp (đối chất) | 92 | 33,7% | 61 | 35 (oracle 66) |

- Vùng 4/4 (79% số câu) đúng 91%; muốn sửa phải bác cả 4 phiếu rồi giải lại, rủi ro cao hơn lợi. **Không gọi LLM ở đây.**
- Trần lý thuyết nếu LLM validator hoàn hảo ở hai vùng còn lại: +21 + 35 = 56 câu (+5,7 EM), đúng bằng
  khoảng cách tới oracle 87,7.

## 3. Bài học từ các lần trước

| Thử nghiệm | Kết quả |
|---|---|
| Verifier chấm từng ứng viên (48 câu tranh chấp, 101 ứng viên) | chấp nhận gần hết: recall 0,91, specificity 0,35; EM 83,0 → 82,5 |
| Judge chọn giữa A và B | đúng 2/10 và 0/6 câu |
| V kiểm tra lời giải có cấu trúc của agent M (§17 note chính) | V nói đúng → M đúng 63%; V nói sai → M đúng 11%: **phân biệt được** |

Khác biệt: V thấy từng ô được trích và phép tính, còn verifier/judge chỉ thấy đáp án trần. Thiết kế mới
phải buộc validator **chỉ ra ô bảng** cho mỗi phán quyết, và ô đó được kiểm tra tất định là có thật.

## 4. Điều kiện hoà vốn (quyết định trước khi chạy)

Gọi r = tỉ lệ validator chấp nhận ứng viên đúng, s = tỉ lệ bác ứng viên sai.

- Vùng 3/4, luật "bác đa số và chấp nhận thiểu số → đổi sang thiểu số":
  lợi ≈ 21·s·r, hại ≈ 65·(1−r)·(1−s).
  - Với mức của verifier cũ (r = 0,91; s = 0,35): +6,6 − 3,8 ≈ **+3 câu (+0,3 EM)**.
  - Với r = 0,95; s = 0,6: +12 − 1,3 ≈ **+11 câu (+1,1 EM)**.
- Vùng tranh chấp: lọc ứng viên bị bác trước khi bỏ phiếu; lợi tối đa 35 câu.

→ **Ngưỡng đi tiếp: s ≥ 0,6 khi r ≥ 0,9.** Dưới ngưỡng này, không luật nào kỳ vọng vượt +1 EM, dừng và ghi
kết quả âm.

## 5. Thiết kế

```
Câu hỏi + bảng → A (3 mẫu) + B → Validator tất định (giữ nguyên)
   ├─ 4/4 nhất trí (~79%) ─────────────────────────────→ Agent định dạng → Đáp án
   ├─ 3/4 (~11%) ─→ LLM Validator ─→ luật L1/L2 ──────→ Agent định dạng → Đáp án
   └─ tranh chấp (~9%) → đối chất → LLM Validator ─→ luật L3/L4 → Agent định dạng → Đáp án
```

LLM Validator gọi **một lần cho mỗi câu** (thấy mọi ứng viên cùng lúc, rẻ hơn gọi từng ứng viên), trên
~20% số câu:

- Đầu vào: bảng Markdown-KV, 8 câu mẫu cùng bảng, câu hỏi, danh sách ứng viên (kèm bằng chứng của B nếu có).
- Nhiệm vụ: với từng ứng viên, tự tìm các ô bảng quyết định, chép nguyên văn, rồi cho phán quyết
  `đúng` / `sai` / `không chắc` cùng độ tin cậy 0–1.
- Kiểm tra tất định sau đó: ô được trích phải có trong bảng; phán quyết dựa trên ô không có thật thì bị bỏ
  (coi như `không chắc`).

Hai nhánh so sánh:

| Nhánh | Backbone | Lý do | Giá OpenRouter (vào / ra, $/1M token) |
|---|---|---|---|
| V-cùng | Qwen3-8B thinking | cùng model với A/B | 0,117 / 0,455 |
| V-khác | Qwen3.5-9B thinking | model khác loại bớt lỗi tương quan khi tự kiểm tra | 0,10 / 0,15 |

Luật ghép (đánh giá offline trên trace v8 dev; v8 đã chạy đối chất cho mọi câu 3/4 nên A2/B2 có sẵn):

- **L1 (3/4):** validator bác đa số và chấp nhận thiểu số → đổi sang thiểu số.
- **L2 (3/4):** validator bác đa số → dùng kết quả đối chất có sẵn thay cho dừng sớm.
- **L3 (tranh chấp):** bỏ ứng viên bị bác trước khi bỏ phiếu cuối (nếu bị bác hết thì giữ nguyên).
- **L4 (tranh chấp):** chọn ứng viên có độ tin cậy cao nhất nếu vượt ngưỡng τ; τ chọn bằng CV theo bảng trên dev.

## 6. Quy trình và điểm dừng

| Giai đoạn | Việc | Chi phí ước tính | Điều kiện đi tiếp |
|---|---|---|---|
| 0 (xong) | Đo headroom, điều kiện hoà vốn | $0 | — |
| 1. Pilot | 60 câu dev (30 vùng 3/4 + 30 tranh chấp, chọn ngẫu nhiên phân tầng), chạy cả hai nhánh | ~$0,05 (V-cùng) + ~$0,02 (V-khác) | nhánh tốt nhất đạt s ≥ 0,6 khi r ≥ 0,9 |
| 2. Dev đủ | 203 câu vùng 3/4 + tranh chấp, nhánh tốt nhất; chọn luật và τ | ~$0,25 (V-cùng) hoặc ~$0,08 (V-khác) | luật tốt nhất hơn MemXam với KTC 95% ghép cặp > 0 trên 983 câu dev |
| 3. Test | Chạy đúng một lần luật đã chốt trên ~200 câu test thuộc hai vùng | ~$0,1–0,25 | — |

- Lưu ý test: trace v7 test không có A2/B2 cho vùng 3/4 (v7 dừng sớm ở 3/4). L1/L3/L4 chạy được trên
  trace sẵn có; L2 cần thêm lệnh gọi đối chất (~110 câu × 2 lệnh gọi).
- Credit OpenRouter hiện còn khoảng $0,40: đủ giai đoạn 1 và 2 (nhất là với V-khác), có thể thiếu cho
  giai đoạn 3 với V-cùng. Nếu cần: nạp thêm credit OpenRouter, hoặc thuê A100 trên Vast (credit $3,43,
  khoảng $0,6/giờ); cả hai cần bạn đồng ý.
- Báo cáo: EM gốc, EM mở rộng (yn / format), BIF4, BIF3; kèm r, s, tỉ lệ ô trích có thật, số câu sửa/hỏng.

## 7. Rủi ro

- **Tự kiểm tra thiên lệch:** cùng model dễ đồng ý với chính lỗi của mình (verifier cũ: s = 0,35) → nhánh V-khác.
- **Quá khớp dev:** vùng 3/4 + tranh chấp chỉ có 203 câu; mỗi luật chỉ có một tham số (τ), chọn bằng CV theo bảng.
- **Nhiễu nhãn:** Có/Phải/Đúng khác từ; so khớp bằng EM gốc và cả EM mở rộng để không chọn luật theo nhiễu.
- **Chi phí suy luận tăng:** thêm khoảng 0,2 lệnh gọi mỗi câu (2,19 → ~2,4), vẫn dưới M+V.

## 8. Sản phẩm dự kiến

- `mas_tqa/validator_llm.py`: prompt, parse, kiểm tra ô có thật; method `validate_llm` chỉ chạy trên câu thuộc hai vùng.
- `scripts/analyze_validator.py`: r, s, luật L1–L4, KTC ghép cặp, chọn τ bằng CV theo bảng.
- `tests/mas_tqa/test_validator_llm.py`: fake client, kiểm tra luật và bước kiểm tra ô.
- Một mục mới trong note chính, ghi cả trường hợp kết quả âm.
