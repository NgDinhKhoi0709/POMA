# Hồ sơ sửa bài POMA

Folder này chứa toàn bộ tài liệu cho việc sửa và nâng cấp bài báo **POMA: A Parallel Multi-Agent Orchestration for Vietnamese Table Question Answering** (Nguyễn Đình Khôi, Đặng Văn Thìn, UIT). Bài làm trên benchmark Open-ViTabQA với backbone Qwen3-8B qua API. Code nằm ở https://github.com/NgDinhKhoi0709/POMA.

Tài liệu được tạo qua ba phiên làm việc ngày 17–18/9/2026. Phiên đầu review bài và lập kế hoạch sửa. Phiên hai tìm hướng tăng novelty và vẽ kiến trúc POMA-Boost v2 (poma2). Phiên ba kiểm poma2 bằng output thật trong repo, bác bỏ nó, và đề xuất POMA v3 (poma3).

## Kết luận mới nhất

- Chấm công bằng (mỗi hệ nộp 1 đáp án) thì POMA hiện tại ngang few-shot: 67,74 so với 67,34.
- Kiến trúc poma2 không nên xây, vì 88,7% câu hỏi chỉ gọi 1 specialist, nên cơ chế "phân xử bất đồng" gần như không có việc để làm.
- Hướng đề xuất là POMA v3: ba agent giải bằng ba cách khác nhau (text, code, view bảng khác), cộng một agent riêng cho quyết định Null.
- Trước khi làm gì mới, paper hiện tại phải sửa một số lỗi số liệu (Table 6, Fig. 2, evaluator drift).

Chi tiết nằm trong `review-POMA-Boost-v2-architecture.md`.

## Nên đọc gì trước

| Bạn muốn | Đọc theo thứ tự |
|---|---|
| Nắm nhanh toàn bộ câu chuyện | `POMA-v3-review-session-QA.md`, rồi `README.md` này |
| Biết bài hiện tại sai ở đâu và sửa gì | `review-POMA-JIT.md`, `fix-plan-POMA.md`, rồi §7 và §8 của `review-POMA-Boost-v2-architecture.md` |
| Làm kiến trúc mới (v3) | `review-POMA-Boost-v2-architecture.md` (§4, §5, §9), `poma3.drawio.png`, `trace-analysis/gate_headroom_report.md` |
| Chọn tạp chí | `journal-selection-POMA.md`, rồi §6 của `review-POMA-Boost-v2-architecture.md` (rủi ro nộp trùng với KAIS) |
| Hiểu vì sao bỏ poma2 | §0 đến §3 của `review-POMA-Boost-v2-architecture.md` |

## Từng file làm gì

### Bài báo gốc

| File | Là gì | Dùng thế nào |
|---|---|---|
| `JIT_Khoi.pdf` | Bản thảo POMA đã nộp và bị reviewer nhận xét (4 nhận xét chung chung). Đây là đối tượng chính của mọi review trong folder | Đọc để đối chiếu số liệu. Các số trong Table 2, 5, 6, 7 và Fig. 2 được nhắc tới khắp các file review |
| `MAPR_2026_Khoi.pdf` | Bài ViPanelTR (MAPR 2026) của cùng nhóm, cùng benchmark, cùng backbone | Dùng để kiểm tra overlap. Bài POMA phải trích và phân biệt với bài này |
| `POMA_Ke_hoach_chinh_sua_Q2.docx` | Kế hoạch sửa bài do tác giả tự viết (tiếng Việt), map 4 nhận xét của reviewer sang việc cần làm, kèm mẫu thư phản hồi reviewer | Dùng làm khung cho thư response-to-reviewers. Những điểm kế hoạch này còn thiếu được liệt kê ở Part E của `review-POMA-JIT.md` |

### Review và kế hoạch

| File | Là gì | Vai trò | Còn đúng không |
|---|---|---|---|
| `review-POMA-JIT.md` | Review kỹ thuật đầy đủ của bản thảo: argument review (F1–F10), review kiểu hội nghị (W1–W7, chấm 4/10), map nhận xét của editor, overlap với ViPanelTR, audit kế hoạch docx | Danh sách lỗi gốc mà mọi file sau tham chiếu (F4, F8, W2…) | Phần lớn còn đúng. Ba mục đã được đính chính: W2, F8, F9 (xem §8 của `review-POMA-Boost-v2-architecture.md`) |
| `fix-plan-POMA.md` | Kế hoạch sửa dựa trên code thật trong repo. Phát hiện repo đã có sẵn hầu hết công cụ cần (áp AN lên baseline, chấm single-answer, bootstrap CI, 2 backbone) nhưng chưa chạy | Việc phải làm đầu tiên (Tier 1): chạy runbook có sẵn, khoảng $15–25 | Còn đúng, vẫn là bước chặn mọi việc khác |
| `journal-selection-POMA.md` | Phân tích xem JIT có phải tạp chí phù hợp không (nhiều khả năng không, vì JIT là tạp chí Hệ thống thông tin/quản trị), đề xuất TALLIP, KAIS, KBS, LRE, ESWA | Chọn nơi nộp | Còn đúng. Cần xử lý thêm việc README repo ghi bài đang review ở KAIS |
| `boosting-novelty-plan-POMA-v2.md` | Kế hoạch tăng novelty theo hướng "boosting", tổng hợp từ 5 agent research. Là cơ sở của poma2 | Lịch sử quyết định, nguồn trích dẫn | Đã bị thay thế một phần. Một số mô tả paper sai (MARGIN, DRE, HelpSteer3, Son et al.), đã đính chính ở §8 của review mới |
| `review-POMA-Boost-v2-architecture.md` | Review poma2 bằng dữ liệu thật và research mới. Có đề xuất POMA v3, kế hoạch thí nghiệm, novelty, lỗi số liệu mới phát hiện, đính chính file cũ | **Tài liệu chính hiện tại** | Mới nhất (18/9/2026) |

### Nhật ký Q&A theo phiên

Mỗi file ghi lại một phiên làm việc dưới dạng hỏi đáp: user hỏi gì, Claude làm gì, kết quả ra sao. Dùng để nhớ lại vì sao đi tới từng quyết định.

| File | Phiên | Nội dung chính |
|---|---|---|
| `POMA-review-session-QA.md` | Phiên 1 | Review bài, so với ViPanelTR, chẩn đoán "AN mới là đòn bẩy chính chứ không phải multi-agent", ý tưởng boosting ban đầu |
| `POMA-Boost-architecture-session-QA.md` | Phiên 2 | Research SOTA, đề xuất POMA-Boost, vẽ và chỉnh các phiên bản sơ đồ trong draw.io |
| `POMA-v3-review-session-QA.md` | Phiên 3 | Review poma2 bằng trace, đề xuất v3, các hướng không dùng multi-agent, SOTA table QA |

### Sơ đồ kiến trúc

| File | Là gì | Dùng thế nào |
|---|---|---|
| `poma2.drawio.xml`, `poma2.drawio.png` | Kiến trúc POMA-Boost v2 (3 stage: specialist song song, aggregation và escalation, consolidation). **Không khuyến nghị xây**, lý do ở §2 và §3 của review mới | Giữ làm tham chiếu. Không bị chỉnh sửa trong phiên 3 |
| `poma3.drawio.xml`, `poma3.drawio.png` | Kiến trúc đề xuất POMA v3 (4 stage: chuẩn bị, 3 solver khác phương thức, đồng thuận và kiểm chứng, xuất 1 đáp án). Cùng style academic với poma2 | Dùng cho slide hoặc làm bản nháp Figure của paper. Khi đưa vào paper, chuyển caption trong hình sang `\caption{}` |

Mở và sửa sơ đồ:
- Mở file `.xml` bằng draw.io desktop (có sẵn ở `C:\Program Files\draw.io\draw.io.exe`) hoặc app.diagrams.net, qua menu File → Open.
- Xuất PNG bằng dòng lệnh:

```bash
"/c/Program Files/draw.io/draw.io.exe" -x -f png -s 1 -o poma3.drawio.png poma3.drawio.xml
```

### Phân tích trace (`trace-analysis/`)

Phân tích offline trên output có sẵn trong repo POMA. Không gọi API, tốn $0. Đây là nguồn của mọi con số có ghi [ĐO] trong review mới.

| File | Là gì |
|---|---|
| `gate_headroom_report.md` | Báo cáo đầy đủ, 11 câu hỏi: dữ liệu có toàn vẹn không, bao nhiêu specialist mỗi câu, tỉ lệ bất đồng, trần của gate, mức thổi phồng của best-of-K, lỗi Null, confidence, evidence, voter khác phương pháp, kết quả theo loại câu, độ chính xác của hint predictor. **Đọc file này trước** |
| `gate_headroom_results.json` | Toàn bộ số liệu dạng máy đọc được, dùng khi cần trích số chính xác |
| `README.md` | Hướng dẫn chạy lại |
| `common.py` | Hàm dùng chung: đường dẫn tới repo, load dữ liệu, chuẩn hóa đáp án |
| `q1_integrity.py`, `q1_extra.py` | Kiểm tra dữ liệu: số bản ghi, model nào sinh file ablation, tái lập 80,24 và Table 6 |
| `build_instances.py` | Gộp mọi nguồn thành một bảng, mỗi câu hỏi một dòng |
| `analysis.py` | Các câu 2–7, 9 và 10 (specialist, bất đồng, trần của gate, best-of-K, Null, voter) |
| `q8_q11.py` | Câu 8 và 11 (evidence, hint predictor, token) |
| `refine.py` | Các phân tích bổ sung (formatter yes/no, luật vote) |

Chạy lại:
1. Clone repo POMA vào một thư mục tên `poma_repo` đặt cạnh thư mục chứa script. `common.py` tìm repo ở `../poma_repo`.
2. Chạy theo thứ tự `q1_integrity.py`, `build_instances.py`, `analysis.py`, `q8_q11.py`, `refine.py`, `q1_extra.py`.
3. Trên Windows đặt `PYTHONIOENCODING=utf-8` để in được tiếng Việt.

Lưu ý: phân tích này chạy trên tập test. Nó đủ để bác bỏ poma2, nhưng mọi quyết định thiết kế cho v3 phải làm lại trên tập dev.

### File hệ thống

| File | Là gì |
|---|---|
| `.claude/settings.local.json`, `.claude/worktrees/` | Cấu hình của Claude Code cho folder này, không liên quan tới nội dung nghiên cứu. Không cần mở |

## Quan hệ giữa các file

```
JIT_Khoi.pdf + nhận xét reviewer
  └► review-POMA-JIT.md ─► fix-plan-POMA.md ─► journal-selection-POMA.md       (phiên 1)
        └► boosting-novelty-plan-POMA-v2.md ─► poma2.drawio                     (phiên 2)
              └► trace-analysis/ + 6 agent research
                    └► review-POMA-Boost-v2-architecture.md ─► poma3.drawio      (phiên 3)
```

Mỗi phiên có file Q&A tương ứng ghi lại quá trình.

## File được nhắc tới nhưng không có trong folder

Các file Q&A cũ nhắc tới vài file không còn ở đây:
- `boosting-novelty-plan-POMA.md` (bản đầu, đã được thay bằng bản v2).
- `poma-boost-architecture.drawio`, `poma-boost-architecture-detailed.drawio`, `poma-boost-architecture-stages.drawio` (các bản sơ đồ trung gian, bản cuối là poma2).

Nếu cần xem lại, tìm trong thư mục khác hoặc lịch sử phiên cũ.

## Việc tiếp theo

Theo §9 của `review-POMA-Boost-v2-architecture.md`:
1. Sửa hạ tầng: đóng băng evaluator, sửa lỗi encoding của AN, chạy lại POMA v1 với log đầy đủ, chấm lại mọi baseline.
2. Xác nhận trạng thái bài đang review ở KAIS.
3. Pilot v3 trên tập dev (khoảng $3–5).
4. Làm từng mảnh của v3 và ablate trên dev, rồi chạy test một lần.
5. Viết paper. Nếu claim multi-agent không đứng được thì chuyển sang dạng bài phân tích.
