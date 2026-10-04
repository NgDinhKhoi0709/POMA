// ============================================================
// MemView — báo cáo tiến độ cho giảng viên hướng dẫn (tiếng Việt)
// Nguồn số liệu: docs/research/2026-09-26-memxam-multi-agent-qwen3-8b.md (§5–§20)
// BIF = ViNLI 4 nhãn (XLM-R Large). Số viết theo kiểu Việt: 81,19 và 7.928.
// Build: python -c "import typst; typst.compile('memview-report.typ', output='memview-report.pdf')"
// ============================================================

#import "packages/ens-rennes-presentation/theme.typ": *

#let highlight-block = tblock.with(color: rgb("#2563eb")) // bối cảnh
#let result-block = tblock.with(color: rgb("#059669")) // kết quả tích cực rõ ràng
#let warning-block = tblock.with(color: rgb("#dc2626")) // hạn chế, lưu ý

#let head-fill = (x, y) => if y == 0 { rgb("#2563eb").lighten(82%) } else if calc.odd(y) { luma(246) } else { white }
#let meta(body) = text(size: 0.62em, fill: luma(90))[#body]

#show: ens-rennes-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [#text(size: 0.8em)[MemView: hệ multi-agent dùng LLM nhỏ cho hỏi–đáp trên bảng tiếng Việt]],
    subtitle: [Báo cáo tiến độ: hệ thống mới, kết quả trên test và bước tiếp theo],
    mini-title: [Table QA tiếng Việt],
    authors: [Nguyễn Đình Khôi],
    date: datetime(year: 2026, month: 9, day: 30),
  ),
  section-style: "named subsection",
  department: "info",
  display-dpt: false,
  named-index: true,
)

#title-slide(additional-content: [
  #v(0.6em)
  #text(size: 0.85em)[Giảng viên hướng dẫn: Đặng Văn Thìn]
  #v(2em)
])

// ============================================================
= Tổng quan
// ============================================================

#slide(title: [Nội dung])[
  #v(1fr)
  #enum(
    spacing: 1.1em,
    [*Hệ thống* — MemView: hai agent, bộ nhớ cùng bảng, LLM validator (agent V) khi bất đồng],
    [*Kết quả* — so với baseline, memory và multi-agent, LLM validator],
    [*Lỗi* — hệ thống còn yếu ở đâu, và những gì đã thử để sửa],
    [*Kế hoạch* — nơi nộp bài, các quyết định cần thầy góp ý],
  )
  #v(1fr)
]

// ============================================================
= Hệ thống
// ============================================================

== Bài toán

#slide(title: [Bài toán và ràng buộc])[
  #highlight-block(title: [Bài toán])[
    Trả lời câu hỏi tiếng Việt trên bảng Wikipedia (Open-ViTabQA: 329 bảng, 7.928 / 991 / 992
    câu train / dev / test). Mọi bảng trong test đều có câu train trên cùng bảng.
  ]
  #v(0.3em)
  #text(size: 0.84em)[
    #grid(
      columns: (1fr, 1fr),
      column-gutter: 1.2em,
      [
        *Ràng buộc*
        - Backbone dưới 10B: Qwen3-8B, chế độ thinking
        - Phương pháp multi-agent
        - Không fine-tune mô hình
      ],
      [
        *Thước đo*
        - EM: khớp chính xác, chấp nhận mọi cách viết cùng nghĩa (Có = Đúng = Phải, định dạng số, đơn vị)
        - F1: F1 theo ký tự giữa dự đoán và gold
        - BIF = 0,5 · PhoBERT-F1 + 0,5 · P(entailment)
      ],
    )
  ]
]

== Pipeline

#slide(title: [MemView])[
  #align(center)[
    #image("assets/memxam-pipeline.svg", width: 90%)
  ]
  #v(0.1em)
  #text(size: 0.6em)[
    *Tên gọi.* *Mem* = các agent dùng chung *bộ nhớ cùng bảng* (các cặp hỏi–đáp train trên cùng bảng);
    *View* = hai agent đọc bảng theo *hai view khác nhau* (Flatten V1 và Markdown-KV).
    Dừng ngay khi 3 mẫu của A trùng nhau và B đồng ý (80% câu trên test); còn lại *agent V* (LLM validator) đọc bảng theo cả
    hai view, xem đáp án kèm lý do của A và B rồi chấm xác suất cho từng ứng viên. Trung bình *2,4 lần gọi LLM mỗi câu*.
  ]
]

== Thiết kế

#slide(title: [Chọn hai view từ nhiều cách biểu diễn bảng])[
  #grid(
    columns: (1fr, 1.05fr),
    column-gutter: 1.2em,
    [
      #text(size: 0.64em)[
        #table(
          columns: (1.6fr, auto, auto, auto),
          inset: 3.5pt,
          align: (left, right, right, right),
          stroke: 0.4pt + luma(180),
          fill: (x, y) => if y == 0 { rgb("#2563eb").lighten(82%) } else if y == 3 or y == 6 { rgb("#059669").lighten(86%) } else if calc.odd(y) { luma(246) } else { white },
          table.header([*Biểu diễn*], [*EM*], [*F1*], [*BIF*]),
          [JSON], [51,0], [68,7], [63,06],
          [Markdown], [52,5], [69,8], [64,14],
          [*Flatten V1* (hiện tại)], [52,5], [69,9], [63,81],
          [Pipe + gộp header nhiều hàng], [55,5], [71,2], [64,52],
          [Pipe (Flatten V1 bỏ tag `<header>`)], [56,0], [71,6], [66,02],
          [*Markdown-KV*], [*56,5*], [*73,5*], [65,28],
        )
      ]
    ],
    text(size: 0.68em)[
      *Vì sao chọn Flatten V1 cho agent A*
      - Không biểu diễn nào hơn Flatten V1 một cách chắc chắn
      - Cùng view với baseline few-shot: phần hơn FS đo đúng tác dụng của memory và multi-agent
      - Gọn (≈ 2.700 ký tự/bảng): đủ chỗ cho 16 câu mẫu và 3 mẫu

      *Vì sao chọn Markdown-KV cho agent B*
      - EM và F1 cao nhất ở sàng lọc; mỗi giá trị viết kèm tên cột
      - Dev-200 (v5, 3 solver cùng phiên): solver đơn lẻ tốt nhất *80,9* EM so với 76,4 của Flatten V1
      - Bù lỗi tốt nhất: ít nhất một trong Flatten V1 / Markdown-KV đúng ở *84,4%* câu dev, so với 80,9% của Flatten V1 / lưới
      - Trên test (v11): A một mẫu 83,27%, B 83,22%, ít nhất một đúng *87,97%*
    ],
  )
]

// ============================================================
= Kết quả
// ============================================================

== Chính

#slide(title: [Test đầy đủ: so với baseline trên cùng Qwen3-8B])[
  #text(size: 0.68em)[
    #table(
      columns: (2.2fr, auto, auto, auto, auto),
      inset: 4.5pt,
      align: (left, right, right, right, right),
      stroke: 0.4pt + luma(180),
      fill: (x, y) => if y == 0 { rgb("#2563eb").lighten(82%) } else if y == 8 { rgb("#059669").lighten(86%) } else if calc.odd(y) { luma(246) } else { white },
      table.header([*Phương pháp*], [*EM*], [*F1*], [*BIF*], [*Lệnh gọi/câu*]),
      [CoAgt], [53,23], [68,16], [58,52], [3,5],
      [Chain-of-Table], [60,08], [73,05], [68,31], [24,3],
      [Zero-shot], [76,51], [84,25], [76,12], [1],
      [Multi-agent debate (3 agent × 2 vòng)], [77,52], [84,57], [76,68], [4],
      [Few-shot (FS)], [77,92], [84,76], [77,05], [1],
      [FS + self-consistency (3 mẫu)], [78,93], [84,99], [77,03], [1 (3 mẫu)],
      [MemView không memory], [80,14], [86,01], [77,99], [2,5],
      [*MemView*], [*85,69*], [*90,66*], [*81,66*], [2,4],
    )
  ]
  #v(0.3em)
  #meta[n = 992 (BIF: 991). Zero-shot, FS, SC, debate và MemView dùng cùng khung prompt và tham số thinking của Qwen3;
    debate theo code gốc Du et al. (zero-shot, vòng 2 đọc câu trả lời của agent khác, đa số).
    CoAgt và Chain-of-Table giữ prompt và tham số gốc của tác giả (prompt WikiTQ tiếng Anh; Chain-of-Table tắt thinking).
    Qwen3-8B bf16, vLLM trên A100, một lần chạy mỗi hệ; mọi lựa chọn làm trên dev.]
  #v(0.2em)
  #text(size: 0.68em)[
    #result-block(title: [Điểm chính])[
      MemView hơn FS *+7,8 EM*, hơn debate *+8,2 EM*. Các hệ multi-agent không dùng memory không hơn FS
      một agent: debate thấp hơn FS; CoAgt và Chain-of-Table thấp hơn nhiều trên bảng tiếng Việt.
    ]
  ]
]

== Đóng góp

#slide(title: [Phần lợi đến từ đâu: memory và multi-agent])[
  #text(size: 0.66em)[
    #table(
      columns: (2.9fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
      inset: 4pt,
      align: (left, right, right, right, right, right, right, right, right, right),
      stroke: 0.4pt + luma(180),
      fill: head-fill,
      table.header([], table.cell(colspan: 3)[*Không memory*], table.cell(colspan: 3)[*Memory từ bảng khác*], table.cell(colspan: 3)[*Memory cùng bảng*]),
      [*Cấu hình*], [*EM*], [*F1*], [*BIF*], [*EM*], [*F1*], [*BIF*], [*EM*], [*F1*], [*BIF*],
      [Chỉ agent A], [79,54], [85,56], [77,74], [82,16], [87,94], [79,54], [84,68], [89,96], [81,09],
      [A + B bỏ phiếu], [80,04], [85,82], [77,84], [83,06], [88,53], [79,96], [84,78], [89,82], [81,18],
      [MemView (A + B + agent V)], [80,14], [86,01], [77,99], [83,27], [88,69], [80,05], [*85,69*], [*90,66*], [*81,66*],
    )
  ]
  #v(0.3em)
  #meta[Mỗi nhóm cột là một lần chạy; ba hàng trong nhóm lấy từ cùng lần chạy. n = 992 (BIF: 991).
    Không memory: câu mẫu thay bằng ví dụ chung của prompt few-shot. Memory từ bảng khác (mô phỏng bảng chưa thấy):
    truy hồi Jaccard trên câu train của mọi bảng trừ bảng đang hỏi. Áp dụng cho cả A, B và agent V.]
  #v(0.2em)
  #text(size: 0.66em)[
    #result-block(title: [Bảng chưa thấy])[
      Memory từ bảng khác vẫn giữ *+3,1 EM* so với không memory (khoảng một nửa phần lợi của memory cùng bảng),
      và MemView vẫn hơn FS cùng khung *+5,4 EM*. Phần multi-agent thêm *+1,1 EM* so với chỉ agent A khi memory
      lấy từ bảng khác, nhiều hơn khi có memory cùng bảng (+1,0) hay không có memory (+0,6).
    ]
  ]
]

== Validator

#slide(title: [LLM validator (agent V) thay luật chọn tất định])[
  #text(size: 0.72em)[
    #table(
      columns: (2fr, auto, auto, auto),
      inset: 4.5pt,
      align: (left, right, right, right),
      stroke: 0.4pt + luma(180),
      fill: (x, y) => if y == 0 { rgb("#2563eb").lighten(82%) } else if y == 4 { rgb("#059669").lighten(86%) } else if calc.odd(y) { luma(246) } else { white },
      table.header([*Chọn đáp án (test)*], [*EM*], [*F1*], [*BIF*]),
      [Chỉ agent A (đa số 3 mẫu)], [84,68], [89,96], [81,09],
      [Chỉ agent B (Markdown-KV)], [83,06], [88,56], [80,08],
      [Luật tất định: A + B bỏ phiếu], [84,78], [89,82], [81,18],
      [*LLM validator (agent V)*], [*85,69*], [*90,66*], [*81,66*],
    )
    #text(size: 0.9em, fill: luma(90))[Bốn hàng lấy từ cùng một lần chạy v11 nên so ghép cặp trên cùng câu. n = 992 (BIF: 991).]
  ]
  #v(0.3em)
  #text(size: 0.66em)[
    #highlight-block(title: [Ở 195 câu agent V được gọi (20%)])[
      Agent V chọn đúng *120 câu (61,5%)*, luật bỏ phiếu chọn đúng 111 câu (56,9%).
      V sửa được *25 câu* bỏ phiếu chọn sai, nhưng làm hỏng *16 câu* bỏ phiếu chọn đúng.
    ]
  ]
]

// ============================================================
= Lỗi
// ============================================================

== Điểm yếu

#slide(title: [Hệ thống còn yếu ở đâu])[
  #text(size: 0.7em)[
    #table(
      columns: (1.8fr, auto, auto, auto),
      inset: 4.5pt,
      align: (left, right, right, right),
      stroke: 0.4pt + luma(180),
      fill: head-fill,
      table.header([*Nhóm câu (test)*], [*n*], [*MemView*], [*FS*]),
      [Câu hỏi "Làm thế nào"], [13], [53,8], [30,8],
      [Câu hỏi "Vì sao"], [27], [55,6], [44,4],
      [Đáp án gold ≥ 8 token], [81], [66,7], [51,9],
      [Bảng Flatten V1 ≥ 16.000 ký tự], [25], [68,0], [60,0],
      [Câu liệt kê, sắp xếp], [56], [76,8], [64,3],
      [Câu tính toán (sai nhiều nhất: 32 câu)], [195], [83,6], [75,9],
      [Toàn bộ test], [992], [85,7], [77,9],
    )
  ]
  #v(0.3em)
  #meta[EM mọi cách viết của MemView v11 và FS cùng khung prompt trên test, một lần chạy; nhóm câu theo hint của dataset.
    MemView hơn FS ở mọi nhóm; 142 câu sai.]
]

== Đã thử

#slide(title: [Các hướng đã thử trên dev, với các phiên bản trước v11])[
  #text(size: 0.62em)[
    #table(
      columns: (1.4fr, 2fr),
      inset: 4pt,
      align: (left, left),
      stroke: 0.4pt + luma(180),
      fill: head-fill,
      table.header([*Hướng thử (chọn trên dev)*], [*Kết quả*]),
      [Judge chọn giữa A và B], [đúng 2/10 và 0/6 câu tranh chấp],
      [Verifier chấm từng ứng viên], [chỉ bác được 35% đáp án sai; EM 83,0 → 82,5],
      [Agent C viết code pandas], [một mình 58,4 EM; 19% code lỗi; cứu được 3/125 câu],
      [Agent M (sinh biểu thức) + agent kiểm tra], [M đúng 43,7% so với 80,5% của MemView; luật ghép tốt nhất +0,41],
      [B phủ quyết khi 3 mẫu A trùng nhau], [+0,51],
      [Bộ chọn học được (logistic regression)], [+0,31],
      [Backbone dưới 10B khác], [tốt nhất Qwen3.5-9B 74,0 so với Qwen3-8B 82,0 (dev-200)],
      [Parse-Critic; prompt tiếng Anh], [−1,5 và −2,5 EM],
    )
  ]
  #v(0.3em)
  #meta[Các thí nghiệm này làm trên *dev* với *các phiên bản trước v11* (v5–v9, prompt cũ), EM chặt; dev đầy đủ (983 câu)
    trừ khi ghi khác. Không chạy lại trên v11 và không chạy trên test. Các mức tăng +0,3 đến +0,5 EM đều nhỏ hơn dao động giữa các lần chạy.]
  #v(0.2em)
  #text(size: 0.66em)[
    #highlight-block(title: [Điểm chung])[
      Lỗi nằm ở khâu chọn và lọc đúng hàng, không ở khâu tính (dev chỉ có 7 câu tính nhẩm sai thật).
      LLM 8B chấm đáp án trần không phân biệt được đúng sai; bắt nó *chỉ ra ô bảng* thì tốt hơn
      (agent kiểm tra xác nhận → M đúng 63%; bác → M chỉ đúng 11%).
    ]
  ]
]

// ============================================================
= Kế hoạch
// ============================================================

== Bài báo

#slide(title: [AAMAS 2027 (Hà Nội): abstract 1/10, bài 8/10])[
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 1.2em,
    text(size: 0.7em)[
      #highlight-block(title: [Hướng viết đề xuất])[
        Bài phân tích thực nghiệm ở area Generative and Agentic AI: *khi nào hệ multi-agent dùng
        LLM nhỏ thật sự có lợi trong Table QA?* 8 trang, ẩn danh hai chiều, nộp qua OpenReview.
      ]
    ],
    text(size: 0.7em)[
      *Thí nghiệm*
      - Đã xong: zero-shot, FS + SC, debate, CoAgt, Chain-of-Table, MemView không memory, bảng chưa thấy
      - Còn thiếu: chạy test 3 lần cho các cấu hình chính (≈ \$2)
    ],
  )
  #v(0.4em)
  #text(size: 0.66em)[
    #warning-block(title: [Rủi ro])[
      Mọi tác giả cần tài khoản OpenReview tạo trước 17/9. Mười ngày là rất sát.
      Phương án muộn hơn: ARR/ACL 2027 (≈ tháng 2/2027), IJCAI 2027 (≈ tháng 1/2027), workshop của AAMAS 2027.
    ]
  ]
]

== Quyết định

#slide(title: [Xin ý kiến thầy])[
  #v(1fr)
  #enum(
    spacing: 1em,
    [Viết theo hướng *phương pháp multi-agent mới* hay *phân tích khi nào multi-agent có lợi*?],
    [Memory cùng bảng có được xem là hợp lệ, hay báo cáo kết quả bảng chưa thấy làm kết quả chính?],
    [Có cần thêm dataset thứ hai hoặc backbone thứ hai trước khi nộp?],
    [Ngân sách cho các thí nghiệm còn thiếu (≈ \$2–3 GPU)?],
  )
  #v(1fr)
]

#focus-slide[
  Cảm ơn thầy — mong thầy góp ý.
]
