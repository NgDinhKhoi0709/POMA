# Biểu diễn và rút gọn bảng cho LM dưới 10B

Ngày tra cứu: 2026-09-17. Phạm vi: TableQA văn bản (không phải bảng ảnh), ưu tiên tiền xử lý rẻ, không gọi LLM; sau đó mới đến pipeline nhiều tác nhân/lời gọi để rút gọn đầu vào. Nguồn bên ngoài ở đây là bài báo của tác giả và kho mã chính thức; các khuyến nghị cho POMA là suy luận kỹ thuật, không phải kết quả đã được xác minh trên Open-ViTabQA.

POMA hiện biến HTML thành lưới logic và dùng **Flatten V1**: từng hàng, ngăn cách bằng `|`, ô header có `<header>` ([`preprocessing/representation.py`](../../preprocessing/representation.py)). Đây là baseline đúng để giữ lại: thay đổi representation phải được đo cùng prompt, decoding, số token và evaluator.

## Kết luận ngắn

Với Qwen3-8B, SeaLLM hay Sea Lion 8B, nên bắt đầu bằng **giữ Flatten V1 + chọn hàng/cột cục bộ không dùng LLM + token budget rõ ràng**. Phương án rẻ nhất là lexical n-gram/BM25; khi có embedding đa ngữ chạy cục bộ, thêm semantic retrieval và một nhánh đa dạng (centroid/MMR). Cả hai chỉ trả về chỉ số hàng/cột rồi dựng lại subtable, vì vậy không được để selector tự bịa giá trị.

Chỉ thử multi-agent/LM selector khi ablation cho thấy recall của evidence bị thiếu ở câu hỏi đa điều kiện. Chi phí nhiều lượt và khả năng sai định dạng/SQL khiến nó không phải mặc định hợp lý cho nhóm model 8B hay ngân sách hạn chế.

## 1. Biểu diễn cố định và truy hồi không gọi LLM

### Cách làm

Tách bảng thành các đơn vị có provenance: `header`, `row`, `column`, và (nếu cần) cặp `(header, cell)`. Xếp hạng chúng theo câu hỏi, lấy top-*k* trong ngân sách token, rồi **tái dựng từ bảng gốc** theo các chỉ số đã chọn. Đưa `title/domain`, header, hàng được chọn và số hàng/cột gốc vào prompt; giữ thứ tự gốc thay vì để retriever viết lại bảng.

Ba selector theo mức chi phí:

- **Lexical/rule-based (mặc định P0):** chuẩn hoá Unicode, số/ngày/đơn vị; dùng overlap n-gram hoặc BM25 giữa câu hỏi với chuỗi hàng và header. Đây là biến thể “content snapshot” trong TAP4LLM, không cần embedding hay LLM. Paper báo nó kém query-specific hơn semantic sampling nhưng là lựa chọn hiệu quả, và dùng được khi không có hạ tầng embedding. [TAP4LLM, §2.1 và §3.2](https://arxiv.org/abs/2312.09039)
- **Dense local retrieval (P1):** mã hoá câu hỏi, header, hàng hoặc `(header, cell)` bằng encoder đa ngữ chạy cục bộ; cosine top-*k* rồi union hàng/cột. TAP4LLM định nghĩa semantic sampling như xếp hạng hàng/cột theo tương đồng utterance và cho thấy biến thể có column grounding tốt hơn các sampling đối chứng trên các benchmark của họ; đó là bằng chứng trên model/dataset của paper, không phải bằng chứng trực tiếp cho tiếng Việt/POMA. [TAP4LLM, Table 1](https://arxiv.org/abs/2312.09039)
- **Semantic + đa dạng:** thêm centroid/K-means hoặc MMR để không chỉ lấy các hàng gần như trùng nhau. TAP4LLM mô tả hybrid theo relevance và khoảng cách tới centroid; điều này hữu ích khi câu hỏi cần so sánh nhiều vùng bảng, nhưng tăng CPU/tuning. [TAP4LLM, §2.1.2](https://arxiv.org/abs/2312.09039)

Ở bảng rất lớn, hướng TableRAG là index schema và cặp `(column, cell)` (có budget cho số giá trị distinct), sau đó chỉ gửi top-*K* evidence vào solver. Thành phần index/retrieval có thể thay encoder bằng BM25 hoặc embedding local, **không cần LLM**; query expansion và chương trình-solver của framework gốc thì có gọi LM. Paper phân tích reasoning prompt là `O(K)`, còn xây cell index là `O(min(D,B))` token encoding với `O(NM)` CPU trong trường hợp quét bảng; trường hợp xấu khi mọi giá trị đều khác vẫn có thể làm rơi evidence do budget. [TableRAG, §3.4, §5 và limitations](https://arxiv.org/abs/2410.04739)

Inner Table Retrieval (ITR) là tiền lệ trực tiếp cho việc học/chấm row, column hoặc mixed subtable, nhưng không phải lựa chọn P0: nó cần retriever được train và, như PieTa cũng thảo luận, lựa chọn hàng/cột độc lập có thể bỏ phụ thuộc liên hàng/liên cột. Dùng ITR như baseline học có giám sát khi đã có nhãn evidence đáng tin, không như thay thế không-training cho BM25. [Robust TableQA: paper/mã chính thức](https://github.com/amazon-science/robust-tableqa)

### Phù hợp, đánh đổi và thí nghiệm cần làm

| Lựa chọn | Qwen3-8B / SeaLLM / Sea Lion 8B | Lợi ích | Rủi ro/giới hạn |
|---|---|---|---|
| Flatten V1 đầy đủ | dùng làm control | không mất evidence, thay đổi ít | token và distractor tăng theo kích thước bảng |
| BM25/n-gram hàng + header | rất phù hợp; không phụ thuộc khả năng tiếng Việt của generator | rẻ, quyết định tái lập, không có API call | synonym/diễn đạt khác có thể làm mất recall |
| Embedding local hàng/header | phù hợp nếu chọn encoder đa ngữ đã kiểm tra riêng | bắt semantic mismatch, vẫn không gọi generator | thêm RAM/latency; encoder có thể yếu với header viết tắt/đơn vị |
| Hybrid diversity | chỉ dùng khi câu hỏi so sánh hoặc nhiều evidence | giảm duplicate trong top-*k* | nhiều hyperparameter; có thể lấy hàng không liên quan |

**Khuyến nghị triển khai POMA.** (1) thêm interface selector trả về `row_ids`, `column_ids`, điểm và lý do máy được (BM25 score), không trả về text bảng mới; (2) thử `top_rows ∈ {5,10,20}`, `top_cols ∈ {all,5,10}` dưới **cùng** token budget; (3) luôn union với header, title và các hàng có exact match số/thực thể; (4) fallback sang Flatten V1 đầy đủ nếu subtable vượt ngưỡng thiếu dữ liệu hoặc selector không có hit; (5) log evidence-recall (gold cell/row khi có), input tokens, latency và EM/F1 theo kích thước bảng. Không chọn format HTML/XML chỉ vì paper gợi ý: TAP4LLM nêu markup có thể dễ hiểu hơn với các GPT được thử nhưng cũng tốn token; chưa có chứng cứ tương ứng cho ba backbone mục tiêu. [TAP4LLM, §2.3](https://arxiv.org/abs/2312.09039)

## 2. Rút gọn bằng nhiều lượt/tác nhân LM

### Các mẫu đã có bằng chứng

**TAP4LLM** không phải hệ multi-agent theo nghĩa có nhiều persona, nhưng là pipeline nhiều bước phù hợp để tách vai trò: sampler → augmenter → packer → solver. Nó so sánh rule, embedding và LLM sampling; chính paper cảnh báo LLM sampling tăng chi phí, gặp token/noise và có thể thành vòng tiền xử lý đệ quy. Với cấu hình đầy đủ, paper báo trung bình 4.7–8.4 LLM calls mỗi câu trên bốn dataset, nên không phù hợp làm baseline “rẻ”. [TAP4LLM, §2.1.3 và Table 4](https://arxiv.org/abs/2312.09039)

**PieTa (Piece of Table)** là mẫu divide–conquer thực sự cho giảm subtable: chia bảng thành cửa sổ chồng lấp `w×w`, selector LM giữ các cell liên quan trong từng cửa sổ, union chúng rồi lặp tới khi bảng không đổi. Selector trong paper được fine-tune từ Llama-3.1-8B-Instruct, nên về kích thước gần Qwen3/SeaLLM/Sea Lion 8B, nhưng đây **không** chứng minh chuyển ngôn ngữ hay zero-shot cho ba model đó. Trên thiết lập của paper, union table trung bình còn 13.91% số cell gốc; selector cuối đạt precision 60.88%, recall 99.12% trên WikiSQL. [PieTa, §3–4](https://arxiv.org/abs/2412.07629)

**TableRAG** là pipeline retrieval → solver thay vì nhiều agent persona: LM tạo tabular query expansion, retriever lấy schema/cell evidence, rồi LM program-aided solver trả lời. Đây là lựa chọn nhiều lượt đáng thử khi bảng quá lớn: paper báo `O(K)` token cho reasoning sau retrieval và kết quả tốt hơn các baseline của họ trên ArcadeQA/BirdQA, nhưng query expansion và solver vẫn cần LM. Mã chính thức nằm trong [google-research/table_rag](https://github.com/google-research/google-research/tree/master/table_rag); cần pin commit trước khi tái lập. [Paper, Algorithm 1 và Table 2](https://arxiv.org/abs/2410.04739)

### Quyết định cho ba backbone 8B

| Mức | Pipeline đề xuất | Gọi LM | Khi nào dùng | Guardrail bắt buộc |
|---|---|---:|---|---|
| P0 | selector cục bộ mục 1 → một lần POMA | 1 | mặc định mọi bảng | evidence IDs, fallback full table |
| P1 | selector cục bộ → model 8B chỉ trả lời/viết structured query | 1–2 | bảng dài, câu hỏi có filter rõ | validate JSON/query; thi hành truy vấn cục bộ |
| P2 | PieTa-style window selector fine-tune → union → answerer | nhiều lượt theo số cửa sổ | ablation cho thấy P0 thiếu evidence đa hàng/cột | dừng theo convergence, giới hạn window/round, đo recall trước EM |
| P3 | TableRAG-style retrieval + query expansion + solver | ≥2 | bảng cực lớn hoặc kho bảng | cache index; parser/executor an toàn; không tin SQL do LM sinh |

Với Qwen3-8B, SeaLLM và Sea Lion 8B, cùng một giao thức **có thể** áp dụng vì không đòi kiến trúc đặc biệt; đó là suy luận từ việc PieTa dùng Llama-3.1-8B và các pipeline làm việc trên interface text/indices, không phải claim benchmark. Qwen3-8B có context pretrained 32,768 (YaRN có thể mở rộng nhưng tài liệu Qwen cảnh báo bật dưới 32K có thể giảm chất lượng short-context), nên rút gọn vẫn giúp latency/KV cache ngay cả khi bảng còn “vừa”. [Qwen3 deployment docs](https://github.com/QwenLM/Qwen3/blob/main/docs/source/deployment/vllm.md) SeaLLM có tokenizer mở rộng cho các ngôn ngữ SEA, gồm tiếng Việt; Sea Lion có các biến thể 8B có context khác nhau, nên phải pin đúng checkpoint và đo bằng tokenizer thật thay vì suy ra từ số ký tự. [SeaLLM model card/paper](https://aclanthology.org/2024.acl-demos.28.pdf), [SEA-LION official repository](https://github.com/aisingapore/sealion). Hãy chạy từng backbone với cùng selector/model-independent index, cùng context cap và cùng decoding. Chỉ nâng lên P2/P3 nếu evidence recall và EM cải thiện đủ bù token, latency, lỗi structured output và số lần gọi.

## Khuyến nghị hành động và protocol đánh giá

1. Giữ `Flatten V1` làm control; bổ sung BM25 row+header selector trước, không thay prompt/agent khác trong experiment đầu.
2. Đánh giá paired trên split hiện có: full table vs top-*k* với *k* nêu trước; report EM/F1, evidence recall, median/p95 input tokens, latency, số LLM calls và failure rate. Chia breakdown theo hàng/cột và loại reasoning.
3. Nếu lexical mất recall vì paraphrase tiếng Việt, thêm dense local retriever; kiểm thử ablation exact-match safety net và diversity riêng.
4. Chỉ sau đó fine-tune PieTa selector trên dữ liệu train có evidence/SQL đáng tin; không sinh nhãn từ test. Với POMA, mọi cell được chọn phải retain `(row_id,column_id)` để truy vết.
5. Không gọi nhiều agent “để reasoning tốt hơn” nếu không có ablation reduction: điểm chính của phương án nhiều lượt ở đây là giảm context có kiểm chứng, không phải tạo thêm văn bản trung gian.

## Nguồn sơ cấp

- Yuan Sui et al., [TAP4LLM: Table Provider on Sampling, Augmenting, and Packing Semi-structured Data for Large Language Model Reasoning](https://arxiv.org/abs/2312.09039), arXiv:2312.09039v3 (2024).
- S.-A. Chen et al., [TableRAG: Million-Token Table Understanding with Language Models](https://arxiv.org/abs/2410.04739), arXiv:2410.04739 (2024); [mã tác giả](https://github.com/google-research/google-research/tree/master/table_rag).
- Wonjin Lee et al., [Piece of Table: A Divide-and-Conquer Approach for Selecting Subtables in Table Question Answering](https://arxiv.org/abs/2412.07629), arXiv:2412.07629v4 (2025).

## Ghi chú phương pháp

Đã dùng alphaXiv để phát hiện và đọc trực tiếp PDF của TAP4LLM, TableRAG và PieTa; các kết quả số trong báo cáo được giới hạn ở thiết lập do chính paper công bố. Không dùng blog hay benchmark thứ cấp để suy diễn hiệu năng của Qwen3-8B, SeaLLM hoặc Sea Lion 8B.
