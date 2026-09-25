# POMA v3: Q&A phiên review kiến trúc poma2 và tìm hướng thay thế

**Ngày:** 2026-09-18
**Bối cảnh:** Tiếp nối hai phiên trước (`POMA-review-session-QA.md`, `POMA-Boost-architecture-session-QA.md`). Phiên trước đã chốt kiến trúc "POMA-Boost v2" trong `poma2.drawio.xml`/`.png`. Phiên này review lại kiến trúc đó bằng dữ liệu thật trong repo và research mới, đề xuất kiến trúc thay thế POMA v3, bàn các hướng không dùng parallel multi-agent, và tóm tắt SOTA table QA.

---

## Q1. Review kiến trúc poma2 (`poma2.drawio`). Tài liệu nền gồm các file Q&A, file docx kế hoạch sửa, paper `JIT_Khoi.pdf` và repo GitHub. Yêu cầu giữ nguyên concept low-resource, chỉ gọi API, multi-agent làm trọng tâm, giữ bài toán và dataset. Nếu cần thì spawn agent tìm approach phù hợp, mỗi agent một việc, được dùng browser, arXiv, alphaXiv và blog AI/ML.

**A1.**
Đọc lại toàn bộ tài liệu (paper, docx, các file review, fix plan, journal selection, Q&A, XML và PNG của poma2), clone repo, rồi spawn 6 agent song song:

1. **Phân tích trace offline.** Dùng output có sẵn trong repo và evaluator của chính repo, không gọi API, tốn $0.
2. **Kiểm tra trích dẫn.** Verify 23 paper mà poma2 dựa vào, xem có được dùng đúng không.
3. **Scout nguồn diversity cho table QA.** Text vs code, nhiều view bảng, nhiều model khác nhau.
4. **Scout answerability và cascade.**
5. **Kiểm tra novelty và overlap,** kể cả bài Son et al.
6. **Scan blog:** Raschka, Willison, Anthropic engineering, Weng, Hamel, Eugene Yan, Wolfe, HF, Google Research.

**Kết quả trace analysis (con số quyết định):**

| Đo được | Hệ quả |
|---|---|
| 88,7% câu chỉ route tới 1 specialist | "Parallel" gần như không xảy ra; gate "Disagree?" không có gì để so |
| Specialist bất đồng ở khoảng 1,4% số câu; resolver hoàn hảo chỉ thêm +0,3 EM | Nhánh disagree của poma2 gần như vô dụng |
| 92,9% lỗi nằm ngoài tầm của gate | Lỗi đến từ một specialist duy nhất sai, hoặc các specialist đồng thuận nhưng cùng sai |
| Chấm 1 đáp án: POMA 67,74 vs FS 67,34 (không có ý nghĩa) | 12,5 điểm "tăng" là do best-of-K nộp nhiều biến thể; riêng Có/Đúng/Phải chiếm 49 câu |
| 77,9% confidence bằng đúng 1,0; evidence có AUROC 0,52 | Không calibrate hay dùng làm verifier được |
| Nhánh hedge chỉ thấy 8/64 lỗi answerability, 0/11 hallucination | Tách hai trục mà chỉ chạy trên hedge thì bỏ sót gần hết |
| FS: 42 Null sai, 9 câu bịa; POMA: 53 và 11 | FS tốt hơn POMA ở cả hai hướng lỗi |

**Kết quả kiểm tra trích dẫn:**
- Cả 23 paper đều có thật.
- Dùng sai 3 thành phần:
  - LofreeCP đo correctness chứ không đo answerability.
  - S\* bắt buộc phải chạy code.
  - OW/ISP không hợp với đáp án tự do.
- MARGIN và COMPETE phải mô tả lại. DRE chỉ sửa được 1–2 pp trên Qwen3-8B.

**Kết quả research:**
- **Diversity:** trộn text với code là nguồn diversity mạnh nhất đã được đo trên bảng. Mix-SC đạt 73,1 so với 66,4 (chỉ text) và 61,4 (chỉ code). FlexTaF trên Llama3-8B tăng từ 49,1 lên 55,7.
- **Role prompt yếu:** role prompt chạy T=0 là nguồn diversity yếu nhất.
- **Null:** Null là một đáp án được chấm điểm, nên chỉ một nhánh answerability riêng mới được phép xuất Null, và phải kích hoạt trên mọi dự đoán Null.

**Novelty:**
- MoRE (EMNLP-F'23) là prior art gần nhất của chính POMA v1 mà paper chưa trích.
- MATA (ACL-F'26) có aggregator, escalation và thực thi code, nhưng dùng thành phần phải train.
- Son et al. (ICCCI 2025) overlap thấp nhưng phải trích vì có chung tác giả.
- Có rủi ro nộp trùng: README ghi POMA đang review ở KAIS.

**Kết luận:** không nên xây poma2 như đang vẽ. Đề xuất **POMA v3**:
- **3 agent giải song song bằng 3 cách khác nhau:**
  - Specialist theo hint (chính là POMA v1).
  - Program agent viết pandas và chạy trên máy.
  - Generalist few-shot đọc bảng ở view khác.
- **Chuẩn hóa đáp án bằng luật trước khi so.**
- **Gate:**
  - Khớp thì nhận luôn.
  - Lệch thì một adjudicator viết và chạy code để phân xử.
  - Có Null hoặc là câu Why thì chuyển sang agent answerability, thành phần duy nhất được xuất Null.
- **Formatter** học từ tập train rồi xuất 1 đáp án.

**Phát hiện phụ phải sửa trong paper hiện tại:**
- **Table 6 so hai tập khác nhau.** 68,41 = 405/592, trong khi 80,24 là trên 992 câu. Đây là lời giải cho mâu thuẫn 68,41 vs 62,40.
- **"177 flips" không tái lập được.** 177 thực ra bằng POMA trừ ZS.
- **Thiếu trace cho 400 câu.**
- **Evaluator drift** so với số trong paper.
- **Fig. 2 lệch output:** Null-F1 thực tế là 52,24, paper ghi 51,13.
- **Claim "predicted > gold hints" đảo chiều** khi chấm bằng evaluator hiện tại.
- **File ablation là gpt-4o-mini,** không phải Qwen.
- **Code AN có lỗi mojibake.**

**Đính chính các file review cũ:**
- **W2:** 62,40 không phải EM không-AN.
- **F8:** là 11 hallucination, không phải 12.
- **F9:** phần +70% token đến từ việc hint predictor đọc cả bảng, không phải do route thêm specialist.

**File tạo ra:**
- `review-POMA-Boost-v2-architecture.md`: review đầy đủ.
- `poma3.drawio.xml` và `poma3.drawio.png`: sơ đồ v3, cùng style academic với poma2, export bằng draw.io CLI. Không sửa poma2.
- `trace-analysis/`: báo cáo, số liệu JSON và script để chạy lại.

---

## Q2. `/unslop` (chạy skill loại bỏ dấu hiệu văn AI)

**A2.**
Áp dụng cho `review-POMA-Boost-v2-architecture.md`, giữ nguyên số liệu và nội dung. Những gì đã sửa:
- Bỏ toàn bộ em dash.
- Giảm bold xuống còn một câu kết luận.
- Đổi các dòng "**nhãn:** nội dung" thành câu văn bình thường.
- Viết lại câu bị động cho rõ ai làm gì.
- Bỏ ẩn dụ ("thu hoạch diversity", "hợp đồng đánh giá"), bỏ emoji ⚠, bỏ chữ in hoa nhấn mạnh.
- Thêm ngôi thứ nhất ở những chỗ là ý kiến.

Kiểm lại bằng script: 0 em dash, 0 curly quote, 0 emoji.

---

## Q3. Tóm gọn approach dễ hiểu bằng tiếng Việt: cải tiến gì so với v1, v2, và lý do concrete?

**A3.**
Ý tưởng một câu: thay vì để 10 specialist cùng một kiểu suy luận rồi chờ chúng bất đồng, v3 cho 3 agent giải cùng một câu bằng 3 cách khác nhau, và chỉ tốn thêm call khi chúng không khớp hoặc có Null.

**So với v1:**

| Vấn đề của v1 | Số đo được | v3 sửa thế nào |
|---|---|---|
| "Parallel" gần như không chạy | 88,7% câu chỉ có 1 specialist | Luôn có 3 agent chạy song song |
| Lỗi tương quan | POMA và FS cùng sai 240 câu, gấp 2,3 lần mức nếu độc lập | Thêm agent chạy code, loại agent sai theo kiểu khác |
| Best-of-K | Chấm 1 đáp án thì POMA 67,74, ngang FS | Xuất 1 đáp án; formatter học từ train, ước tính +3,5 |
| Null | 53 Null sai và 11 câu bịa, tệ hơn FS | Mọi Null đều qua kiểm tra trong bảng |
| Câu Why | 40,7 so với FS 55,6 | Luôn kiểm quan hệ nhân quả |

**So với v2:**

| v2 dựa vào | Thực tế | v3 thay bằng |
|---|---|---|
| Bất đồng giữa specialist | 1,4% số câu, tối đa +0,3 EM | Tự tạo bất đồng bằng 3 cách giải khác nhau |
| Trọng số theo confidence | 77,9% bằng 1,0 | Tin kết quả chạy code, hoặc dùng luật theo loại câu |
| Answerability chỉ khi hedge | 8/64 lỗi, 0/11 câu bịa | Kiểm trên mọi dự đoán Null |
| LofreeCP, COMPETE, S\*, OW/ISP | Dùng sai nguồn | Kiểm bằng code chạy thật và tìm trực tiếp trong bảng |

**Lý do tin v3 sẽ hiệu quả:**
- Mix-SC và FlexTaF cho thấy trộn text với code giúp ở cùng ngân sách.
- Chỉ cần vote khi POMA và FS lệch nhau đã được +2,1 điểm.
- Sửa hết 53 Null sai thì Null-F1 lên khoảng 0,85.
- Chi phí khoảng 1,2–1,5 lần v1.

**Chưa chắc chắn:**
- Code agent ở cỡ 8B có thể giòn với ô gộp và số kiểu Việt.
- Phải pilot trên dev trước (khoảng $3–5). Nếu lỗi của code agent vẫn dính với specialist như FS đang dính thì dừng lại xem xét.

---

## Q4. Nếu không theo hướng parallel multi-agent thì có thể làm gì?

**A4.**
Theo dữ liệu, điểm nghẽn thật của POMA nằm ở format đáp án, bảng có ô gộp, phép tính và quyết định Null, chứ không phải thiếu agent. Có năm hướng mà vẫn giữ task, dataset và không fine-tune:

1. **Chọn few-shot động từ tập train.** Tập train 7.928 câu hiện chưa dùng vào việc gì. Ví dụ mẫu có đáp án đúng dạng sẽ dạy model format ngay lúc sinh.
2. **Biểu diễn bảng theo cấu trúc.** Dùng dạng header-path, hoặc đọc theo hàng/cột. 55,6% bảng có ô gộp, và FS mất 10–14 EM trên các bảng này. Header-path hơn markdown tới 16 EM (OHD). RoT đưa Llama3.1-8B trên HiTab từ 46,5 lên 56,6.
3. **Một agent dùng code, chạy tuần tự, có sửa lỗi.** Câu Math của POMA thua FS. TableZoomer với Qwen3-8B tăng từ 67,8 lên 87,2 (bảng tiếng Anh sạch).
4. **Tập trung vào answerability.** Có thể tạo câu Null mới bằng cách xóa hàng hoặc cột chứa bằng chứng. Ý này chưa kiểm novelty.
5. **Bài phân tích và chuẩn đánh giá.** Gồm error taxonomy, đo mức EM phạt oan đáp án cùng nghĩa khác chữ, và chấm lại các baseline. Hợp với tạp chí LRE.

Nếu nới ràng buộc "chỉ gọi API" thì còn hướng 6: fine-tune bằng LoRA một model 1,7B–4B trên GPU miễn phí.

**Đề xuất:** gộp hướng 1, 2, 3 và formatter thành một pipeline một agent, viết thành bài nghiên cứu có kiểm soát kiểu *"What actually helps small LLMs on Vietnamese table QA"*. Mỗi mảnh nhắm vào đúng một điểm nghẽn đã đo, rẻ, ablate riêng được, và câu chuyện trung thực.

Lưu ý: novelty và số liệu của hướng 1 và ý tạo câu Null chưa được agent verify.

---

## Q5. SOTA của table QA nói chung hiện tại là gì?

**A5.**
Đã spawn 3 agent: con số SOTA theo từng benchmark, xu hướng phương pháp, và model nhỏ cùng đa ngôn ngữ. User dừng các agent giữa chừng (kể cả các agent con của agent 1), nên câu trả lời dựa trên số đã được kiểm trong các lượt research trước của phiên. Đây chưa phải một lượt quét bảng xếp hạng đầy đủ.

**Bảng tóm tắt:**

| Benchmark | Nhóm | Kết quả đã kiểm |
|---|---|---|
| WTQ | Không train, model tầm trung/lớn | TableMaster 78,1 (GPT-4o-mini); Table-Critic 77,2 (Qwen2.5-72B); Mix-SC 73,1 (GPT-3.5) |
| WTQ | Có train | Pipeline code + Table-R1 + bộ chọn có train khoảng 84 (chưa đối chiếu bảng gốc); TabLaP 76,6 |
| WTQ | Không train, ≤8B | Orchestra 68,6 (Qwen2.5-7B), 64,9 (Llama3.1-8B); RoT 61,7; FlexTaF 55,7 |
| TabFact | ≤8B không train | Khoảng 80–83 |
| HiTab | Bảng phân cấp | OHD 60,2 EM (72B); ≤8B khoảng 56–59 (RoT) |
| DataBench | Có code | TableZoomer với Qwen3-8B 87,2; Son và Thìn 89,5 (top 4) |
| Open-ViTabQA | Đã công bố | Gemini 2.0 Flash khoảng 60 EM; con người 83,4 |
| Open-ViTabQA | Đo lại offline từ output của repo | Qwen3-8B few-shot 67,3 đã vượt số công bố; POMA chấm 1 đáp án 67,7 |
| ViNumQA (VLSP 2025) | | Tốt nhất 84,0; Qwen3-8B 79,1 |

**Rút ra:**
- Hướng mạnh nhất hiện nay là trộn text với code và biểu diễn bảng tốt.
- Multi-agent chỉ đứng top khi có thành phần được train.
- Model nhỏ muốn lên nữa thường phải train (RL, họ Table-R1 và TableMind), điều này phạm ràng buộc "chỉ gọi API".
- Ở cỡ 7–8B không train, mức trần thực tế khoảng 65–69 trên WTQ.
- Open-ViTabQA ít người làm: dễ vượt số đã công bố, nhưng reviewer sẽ so với baseline mạnh. Khoảng cách tới con người mới là câu chuyện đáng kể.

**Bài học rút ra:** với câu hỏi tra cứu nhanh kiểu "SOTA là gì", nên trả lời trước bằng dữ liệu đã có trong phiên, rồi hỏi user có cần quét sâu không. Không nên mở ngay một đợt research lớn: agent 1 tự spawn thêm 5 agent con, và user đã phải dừng từng cái.

---

*Xem thêm:*
- `review-POMA-Boost-v2-architecture.md`: review đầy đủ và đề xuất v3.
- `poma3.drawio.xml` và `poma3.drawio.png`: sơ đồ v3.
- `trace-analysis/gate_headroom_report.md`: số liệu offline.
- Các file trước: `POMA-Boost-architecture-session-QA.md`, `POMA-review-session-QA.md`, `boosting-novelty-plan-POMA-v2.md`, `review-POMA-JIT.md`, `fix-plan-POMA.md`, `journal-selection-POMA.md`.
