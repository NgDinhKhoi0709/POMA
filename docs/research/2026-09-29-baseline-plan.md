# Kế hoạch: baseline zero-shot và các hệ multi-agent khác trên test đầy đủ (2026-09-29)

Mục tiêu: bảng so sánh công bằng cho paper, mọi hệ cùng backbone Qwen3-8B, cùng cách chấm, cùng 992 câu test.

## 1. Nguyên tắc so sánh

- Backbone: Qwen3-8B bf16, vLLM tự host trên A100, chế độ thinking.
- Lấy mẫu theo Qwen3: T = 0,6, top_p = 0,95, top_k = 20, không giới hạn max_tokens; hệ nào có temperature
  riêng trong bài gốc thì giữ temperature đó và ghi chú.
- Khởi động vLLM với `--reasoning-parser qwen3`: phần thinking tách khỏi `content`, để các baseline viết cho
  API OpenAI (CoAgt, Chain-of-Query, Chain-of-Table) đọc được đáp án. Client của mas_tqa vẫn chạy đúng
  (`strip_think` không còn gì để cắt).
- Chấm giống MemView: EM gốc, EM chuẩn hoá định dạng, EM mọi cách viết cùng nghĩa, PhoBERT, BIF4
  (`scripts/score_lenient.py`, `scripts/bif_all.py`); báo thêm số lệnh gọi và token mỗi câu.
- Một lần chạy mỗi hệ; nếu còn ngân sách, chạy lặp MemView v11 và FS cùng khung để có độ dao động.

## 2. Danh sách hệ cần chạy (theo thứ tự ưu tiên)

| # | Hệ | Loại | Lệnh gọi/câu | Thời gian A100 (ước) | Ghi chú |
|---|---|---|---:|---:|---|
| 1 | **Zero-shot** cùng khung prompt Qwen | 1 agent | 1 | ~15 phút | bỏ ví dụ, giữ system + bảng + định dạng đầu ra |
| 2 | **Multi-agent debate** (Du et al., 2023) | multi-agent đồng nhất | 3 agent × 2 vòng = 6 | ~1,5–2 giờ | cùng prompt few-shot; vòng 2 mỗi agent thấy đáp án của hai agent kia; bỏ phiếu cuối |
| 3 | **MemView không memory** | ablation | ~2,4 | ~1 giờ | thay câu mẫu cùng bảng bằng ví dụ chung: tách phần lợi của memory khỏi phần multi-agent |
| 4 | **Self-consistency ngang chi phí** (FS, 3 mẫu) | 1 agent, nhiều mẫu | 1 (n = 3) | ~20 phút | so với MemView ở mức chi phí gần nhau |
| 5 | **CoAgt** (có sẵn trong `baselines/coagt`) | multi-agent (collector theo đoạn bảng → synthesizer → refiner) | ~3–5 | ~1 giờ | prompt gốc của tác giả |
| 6 | **Chain-of-Table** (`baselines/chain_of_query/run_chain_of_table.py`) | agent gọi thao tác bảng nhiều bước | ~5–8 | ~1,5–2 giờ | prompt gốc tiếng Anh |
| 7 | Chain-of-Query (tuỳ chọn) | multi-agent sinh SQL | ~3–6 | ~1 giờ | bản công khai thiếu các clause agent; chỉ chạy được bản SQL cơ bản, ghi rõ hạn chế |

Đã có sẵn, không cần chạy lại: FS cùng khung prompt (73,29), MemView v11 (81,85), các ablation trong cùng
lần chạy (chỉ A, A + B bỏ phiếu).

## 3. Việc chuẩn bị trước khi thuê GPU (không tốn tiền)

1. Viết `zs_qwen`, `fs_qwen_sc3`, `memview_nomem` và `mad_debate` trong `mas_tqa/methods.py`, kèm test mock.
2. Chạy thử CoAgt và Chain-of-Table với 5 câu qua OpenRouter hoặc bằng mock để chắc adapter đọc được
   đáp án khi phần thinking đã được tách ra.
3. Script chạy tuần tự các hệ trên cùng một máy, ghi mốc hoàn thành, tự chạy bù câu lỗi (lần trước mất
   145 câu vì máy mất mạng), chỉ tắt GPU khi mọi file đủ 992 câu.

## 4. Chi phí và thời gian

- Tổng khoảng 6–8 giờ A100 (hai hệ chạy song song để GPU luôn bận); khoảng \$4–5 cộng thời gian khởi động.
- Credit Vast hiện còn \$0,33: cần nạp thêm khoảng \$6 (dư cho chạy bù và lặp FS/MemView).
- Nếu chỉ chạy các mục 1–4 (bắt buộc cho paper): khoảng 3,5 giờ, khoảng \$2,5.

## 5. Kết quả dự kiến đưa vào paper

Bảng chính: Zero-shot, Few-shot, FS self-consistency, Multi-agent debate, CoAgt, Chain-of-Table, MemView
không memory, MemView. Cột: EM, EM chuẩn hoá, PhoBERT, BIF, lệnh gọi/câu, token/câu.
