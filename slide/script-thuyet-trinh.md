# Script thuyết trình — POMA progress report

Kịch bản nói cho `progress-report.pdf` (19 trang: 18 slide nội dung + 1 slide kết).
Mỗi mục dưới đây gồm: **mục tiêu** của slide, **lời nói** (viết sẵn để đọc hoặc
diễn đạt lại), **số phải nhấn**, và **điều không được nói** — vì nhiều con số trong
deck này rất dễ bị phát biểu quá mạnh.

**Về cách đọc số:** script dùng đúng ký hiệu trên slide (dấu chấm thập phân:
`70.16`, `2,000`), để bạn nhìn slide và đọc script không bị lệch. Khi nói tiếng Việt
thì vẫn đọc tự nhiên: "bảy mươi phẩy một sáu".

**Quy ước chung khi đọc khoảng tin cậy:** "KTC" = khoảng tin cậy 95% ghép cặp
(paired bootstrap trên cùng bộ câu hỏi). Khoảng chứa 0 → **không** kết luận được
bên nào hơn. Chỉ khi cả khoảng nằm hẳn một phía mới được nói "hơn" hay "kém".

## Ngân sách thời gian (đủ bộ khoảng 25 phút; mục tiêu 20 phút thì cắt theo dòng dưới bảng)

| Trang | Slide | Phút |
|---:|---|---:|
| 1–2 | Bìa + Outline | 1 |
| 3–4 | Bài toán + Dữ liệu | 2,5 |
| 5 | Pipeline POMA | 1 |
| **6** | **Audit — so sánh then chốt** | **2,5** |
| 7 | Hai cặp so khớp điều kiện | 1,5 |
| 8 | Thước đo BIF + ViNLI tự fine-tune | 1,5 |
| 9 | Tổng quan thực nghiệm (14 dòng) | 3 |
| 10 | Ba ví dụ tiêu biểu | 1,5 |
| 11 | POMA v3lite | 1,5 |
| 12 | Backbone thứ hai và thứ ba | 1,5 |
| 13 | Vì sao GaP-TQA có hình dạng này | 1,5 |
| 14–16 | GaP-TQA A1, A2a, A5 (ba sơ đồ) | 2 |
| 17 | GaP-TQA so với zero-shot và few-shot | 1,5 |
| 18 | Bước tiếp theo: cải tiến GaP-TQA | 0,5 |

Để về 20 phút: bỏ trang 10 (khoảng 1,5 phút); trang 14–16 chỉ nói một câu mỗi sơ đồ;
trang 9 chỉ đọc đoạn mở và đoạn chốt, bỏ phần từng dòng (phần từng dòng dùng khi thầy
chỉ vào một dòng cụ thể); trang 8 rút xuống một câu.
**Không bao giờ bỏ trang 6.**

---

## Trang 1 — Bìa

**Mục tiêu:** vào thẳng vấn đề, không mất thời gian giới thiệu lại đề tài.

> "Em báo cáo tiến độ đề tài POMA — hệ đa tác tử song song cho hỏi đáp trên bảng
> tiếng Việt. Buổi hôm nay em xin trình bày: hệ thống hiện tại chạy ra sao, số liệu
> sau khi em audit lại, các hướng em đã thử kèm kết quả đo được, một hệ thống mới là
> GaP-TQA, và kế hoạch tiếp theo."

**Lưu ý:** đừng hứa "kết quả tốt". Đặt kỳ vọng đúng ngay từ câu đầu: phần lớn báo cáo
này nói về **kết quả đo được không như mong đợi**, và vì sao điều đó vẫn có giá trị.

---

## Trang 2 — Outline

**Mục tiêu:** cho thầy bản đồ, 20 giây.

> "Em đi theo năm phần: dữ liệu thật sự chứa gì, hệ thống hiện tại, đối chiếu số đã
> công bố với số em audit lại, các thực nghiệm — tám hướng cải tiến POMA cộng một hệ
> thống riêng là GaP-TQA — và cuối cùng là bài học cùng kế hoạch."

Không dừng lâu ở slide này.

---

## Trang 3 — Bài toán

**Mục tiêu:** chốt phạm vi và ràng buộc, để sau này không ai hỏi "sao không fine-tune".

> "Bài toán là trả lời câu hỏi tiếng Việt trên bảng bán cấu trúc lấy từ Wikipedia,
> benchmark Open-ViTabQA. Câu nào không trả lời được thì phải trả đúng chuỗi `Null`.
> Ba thách thức được nêu trong bài là header nhiều tầng và ô gộp, suy luận nhiều
> bước qua nhiều hàng hoặc cột, và quyết định có trả lời được hay không.
>
> Ràng buộc của đề tài: backbone mở dưới 10 tỷ tham số, **không fine-tune** mô hình
> QA. Em chỉ được can thiệp ở tầng prompt và cấu trúc pipeline. Ràng buộc này quan
> trọng, vì nó quyết định gần như toàn bộ những gì em có thể thử."

---

## Trang 4 — Dữ liệu

**Mục tiêu:** chứng minh em đo dữ liệu chứ không chép lại từ paper, và rút ra hệ quả
thiết kế từ chính dữ liệu đó. Đọc theo cột phải ("Why it matters"), đừng đọc từng con số.

> "Đây là số em đo trực tiếp từ file trong repo, không lấy từ paper. Em xin nói năm
> dòng quan trọng, theo cột bên phải.
>
> **Câu không trả lời được chỉ chiếm 4.5%** — 45 trên 992 câu test. Đây là một lớp
> hiếm, nên mọi cơ chế từ chối trả lời phải tính tới cái giá của việc từ chối nhầm.
>
> **Độ dài bảng trung vị chỉ 647 token**, p90 là 2,097 — bảng rất nhỏ. Nghĩa là các
> phương pháp sinh ra để giải bài toán context quá dài đang giải sai bài toán cho phần
> lớn dữ liệu này.
>
> Nhưng **15.6% số câu có bảng dài trên 2,000 token lại chiếm tới 54.8% tổng số token
> bảng** — chi phí tập trung ở một nhóm nhỏ. Đây chính là lý do em chỉ chạy hướng rút
> gọn bảng trên nhóm đó.
>
> **Trung bình chỉ 1.10 nhãn hint mỗi câu, 91% số câu có đúng một nhãn** — nên thực tế
> chỉ có một specialist được gọi.
>
> Và **42.3% đáp án là bản sao nguyên một ô**, tức phần lớn bài toán là định vị ô chứ
> không phải tính toán."

**Số phải nhấn:** 647 token trung vị · 15.6% câu giữ 54.8% token · 91% một nhãn.

**Nếu thầy hỏi về rò rỉ dữ liệu giữa các split:** toàn bộ 296 bảng của tập dev và
289 bảng của tập test đều xuất hiện trong tập train, nên mọi phương pháp dùng dữ liệu
train — few-shot cố định, rule suy từ train, retrieval — phải báo cáo riêng phần bảng
đã thấy và chưa thấy.

**Nếu thầy hỏi "bản thảo có ghi sai gì không":** có bốn chỗ — unanswerable **4.5% chứ
không phải ~10%**; `table_type` là **bốn nhóm chứ không phải ba** (126 câu thuộc cả
hai); trace ghi **46** gold `Null` trong khi file phát hành có **45**; và "chạy song
song" thực tế chỉ xảy ra ở khoảng 11% số câu. Chi tiết ở
[`context/01-boi-canh-va-du-lieu.md`](context/01-boi-canh-va-du-lieu.md).

---

## Trang 5 — POMA đang chạy như thế nào

**Mục tiêu:** mô tả pipeline trong 45 giây, không đi sâu.

> "Đây là POMA đang chạy. HTML được parse thành lưới logic, giải `rowspan`/`colspan`,
> rồi serialize thành biểu diễn Flatten V1. Sau đó hint predictor gán nhãn loại suy
> luận, question refiner viết lại câu hỏi thành truy vấn có ràng buộc tường minh,
> router tất định ánh xạ 1:1 từ nhãn sang specialist, mười specialist chạy song song,
> và cuối cùng answer normalization gộp kết quả. Không có bước huấn luyện nào."

Đừng giải thích từng agent.

**Nếu thầy hỏi "song song thì có lợi gì":** ba ý, nói thẳng —
(1) router chỉ là bảng tra 1:1, quyết định thật nằm ở hint predictor, mà độ chính xác
của hint predictor chưa từng được báo cáo; (2) các specialist không thấy output của
nhau, decoding nhiệt độ 0, nên song song hay tuần tự cho cùng một đáp án — lợi ích duy
nhất có thể có là độ trễ, và bài chưa đo độ trễ; (3) song song gần như không xảy ra:
**880 trên 992 câu chỉ gọi đúng một specialist**.

---

## Trang 6 — Audit ⭐ SLIDE QUAN TRỌNG NHẤT

**Mục tiêu:** nếu thầy chỉ nhớ một slide, phải là slide này. Nói chậm, đi từng dòng.

> "Đây là slide quan trọng nhất của buổi hôm nay. Tất cả các dòng đều trên đủ 992
> câu test.
>
> Dòng đầu, **74.90** — đó là POMA ở chế độ `all`, chấm theo kiểu **best-of-K**: hệ
> sinh ra nhiều đáp án ứng viên, trung bình 3.44, nhiều nhất tới 80, rồi bộ chấm chọn
> ứng viên khớp đáp án chuẩn nhất. Đó là một **trần oracle**, vì khi chạy thật ta chưa
> biết đáp án đúng để mà chọn. Vì vậy dòng này không có BIF.
>
> Dòng thứ hai: **cùng lần chạy đó**, chỉ lấy đáp án đầu tiên thì POMA còn **66.63**.
> Khoảng 8 điểm chênh lệch này **hoàn toàn do cách chấm**, không phải do mô hình suy
> luận tốt hơn.
>
> Few-shot thô, một lệnh gọi, được 67.34 — đã nhỉnh hơn POMA-first.
>
> Hai dòng cuối là phép so công bằng nhất: áp **cùng một bộ finalizer GSA** — một bước
> chọn ra đúng một chuỗi đáp án — cho cả hai bên. POMA được 68.45, còn **few-shot được
> 70.16**. Tức là **baseline một lệnh gọi đang cao hơn POMA** về EM."

**Khối đỏ:**

> "Cụ thể: hiệu là **âm 1.71 điểm EM**, khoảng tin cậy từ âm 3.93 tới dương 0.50;
> 53 câu thắng, 70 câu thua, 869 câu hòa. Đây là phép so sánh vững nhất em có, vì cả
> hai nhánh GSA được chạy lại cùng nhau. BIF thì nghiêng ngược lại một chút, dương
> 0.33, nhưng khoảng tin cậy từ âm 0.98 tới dương 1.63 — tức BIF cũng đồng ý là
> **không có bên thắng**."

**Cách phát biểu đúng — học thuộc câu này:**

> "Khoảng tin cậy vẫn chứa 0, nên em **không** kết luận rằng few-shot tốt hơn POMA.
> Điều em kết luận được là: **không có bằng chứng nào cho thấy POMA tốt hơn few-shot**
> khi chấm công bằng."

**Tuyệt đối không nói:** "POMA thua few-shot" (KTC chứa 0) hoặc "POMA không hoạt động".

**Nếu thầy hỏi về 80.24 trong bản thảo:** "80.24 cũng là điểm oracle best-of-K, cùng
kiểu với 74.90 ở đây. Cùng lần chạy trong bản thảo, lấy đáp án đầu thì còn 67.74 —
chênh 12.50 điểm, hoàn toàn do cách chấm."

---

## Trang 7 — Hai cặp so khớp điều kiện, không tính điểm oracle

**Mục tiêu:** bỏ hẳn điểm oracle, chỉ giữ những cặp mà hai bên cùng xuất một đáp án
và được chấm như nhau, để thấy kết luận của trang 6 vẫn đúng khi nhìn cả bốn chỉ số.
Đọc theo hai dòng Δ, đừng đọc từng ô.

> "Slide này bỏ dòng oracle 74.90 ở trang trước. Em chỉ giữ hai cặp, trong mỗi cặp hai
> bên đều xuất đúng một đáp án và được chấm giống nhau. Ngoài EM em thêm F1 ký tự, R1 là
> ROUGE-1 và MET là METEOR. Thầy nhìn dòng Δ, tức là POMA trừ few-shot.
>
> **Cặp 1 — một đáp án, chưa có finalizer.** POMA-first thấp hơn few-shot thô 0.71 EM,
> nhưng cao hơn 1.2 đến 2.2 điểm ở F1, R1 và METEOR. Cặp này có một điểm yếu: số
> few-shot thô là kết quả cũ, không rõ lần chạy, nên hai bên không chạy cùng lúc. Thêm
> nữa, 0.71 điểm còn nhỏ hơn độ trôi giữa hai lần chạy y hệt nhau, có lúc tới 1.7 EM,
> như dòng N1 ở trang 9. Nên cặp này em coi là gần như hòa.
>
> **Cặp 2 — cả hai cùng qua GSA, trong cùng một lần chạy.** Đây là cặp chặt nhất. POMA
> thấp hơn 1.71 EM, khoảng tin cậy từ âm 3.93 tới dương 0.50, vẫn chứa 0. Ở ba chỉ số
> còn lại, chênh lệch chỉ còn từ âm 0.2 tới dương 0.9, riêng F1 đã chuyển sang âm.
>
> Tóm lại: về EM, POMA không vượt few-shot ở cặp nào. Chút lợi thế của POMA ở F1, R1,
> METEOR gần như biến mất khi hai bên cùng dùng GSA. Con số 'POMA thắng' lớn như 74.90
> chỉ xuất hiện khi chấm kiểu oracle, không xuất hiện trong phép so công bằng."

**Số phải nhấn:** −0.71 EM (cặp 1, khác run) · −1.71 EM, KTC [−3.93, +0.50] (cặp 2,
cùng run) · F1 từ +1.17 xuống −0.21.

**Không được nói:**
- "POMA thua few-shot" — KTC của cặp 2 chứa 0; cặp 1 chưa có KTC và hai bên khác run.
  Nói "POMA **không vượt** few-shot".
- "POMA tốt hơn ở F1/METEOR" — ba chỉ số này chưa có KTC ghép cặp, và lợi thế co về gần
  0 khi thêm GSA.

**Nếu thầy hỏi "sao cặp 1 POMA hơn ở F1 mà lại thua EM":** "F1 cho điểm một phần khi
đáp án khớp một phần, EM thì không. Em chưa phân tích lỗi riêng cho chênh lệch này;
điều em thấy được là khi cả hai cùng qua GSA thì chênh lệch F1 về gần 0."

**Nếu thầy hỏi "sao không có BIF":** "BIF của cặp 2 nằm ở trang 6: POMA 76.43, few-shot
76.10, hơn 0.33 nhưng KTC từ âm 0.98 tới dương 1.63 — cũng không có bên thắng."

---

## Trang 8 — Thước đo BIF và mô hình ViNLI

**Mục tiêu:** giải thích BIF là gì, và báo cáo rằng em đã tự fine-tune mô hình NLI cho nó.

> "Từ slide này, các bảng có thêm cột **BIF**. BIF là thước đo ngữ nghĩa theo đúng
> định nghĩa của bài Open-ViTabQA: một nửa là PhoBERTScore F1 giữa đáp án chuẩn và đáp
> án dự đoán, tính bằng PhoBERT-large ở tầng 17; nửa còn lại là xác suất một mô hình
> NLI bốn nhãn cho rằng đáp án dự đoán **được suy ra từ** đáp án chuẩn. Lý do cần nó:
> EM và F1 ký tự cho 0 điểm khi model trả `1709` còn gold là `Năm 1709`, trong khi về
> nghĩa là đúng.
>
> Để tính BIF cần mô hình NLI tiếng Việt bốn nhãn, nên **em tự fine-tune XLM-R Large
> trên ViNLI** theo đúng công thức của bài gốc: Adam, learning rate 1e-5, batch 16,
> 10 epoch, độ dài tối đa 128. Kích thước ba split khớp với bài. Trên tập test 2,991
> cặp, mô hình của em đạt **85.42 accuracy và 85.49 macro-F1**, thấp hơn bài gốc khoảng
> 0.6 điểm. Nhãn entailment — nhãn mà BIF dùng — đạt F1 83.61."

**Nếu thầy hỏi về giới hạn:** dữ liệu em dùng là bản mirror trên Hugging Face, không
phải bản tác giả phát hành, nên đây là replication chứ không phải tái hiện chính xác.
Và BIF là thước đo phụ: mọi kết luận trong deck vẫn dựa trên EM.

**Không được nói:** "BIF cho thấy POMA tốt hơn". POMA+GSA hơn FS+GSA +0.33 BIF nhưng
KTC chứa 0, còn EM thì ngược chiều.

---

## Trang 9 — Tổng quan thực nghiệm (bảng 14 dòng)

**Mục tiêu:** chứng minh khối lượng công việc và cách đọc bảng. Có thời gian thì đi
từng dòng theo phần dưới; thiếu thời gian thì chỉ đọc đoạn mở và đoạn chốt.

### Đoạn mở — cách đọc bảng

> "Bảng này là toàn bộ thực nghiệm em đã chạy, mỗi dòng là một câu hỏi nghiên cứu độc
> lập. Cột **n** là số câu dùng để đo. Cột **Parser** là phiên bản tiền xử lý bảng:
> *legacy* là bản cũ, *fixed* là bản đã sửa lỗi. Cột **EM effect** là chênh lệch Exact
> Match kèm khoảng tin cậy ghép cặp; cột **BIF effect** là chênh lệch trên thước đo ngữ
> nghĩa vừa nói.
>
> Cột Parser em xin thầy chú ý: ngày 19/9 em phát hiện hàm lấy text của ô HTML không
> chèn dấu phân cách, nên các đoạn cách nhau bởi thẻ `<br>` bị dính liền. Lỗi này ảnh
> hưởng 95 trên 329 bảng, 325 trên 992 câu test. Vì nó nằm phía trên mọi thí nghiệm,
> **các dòng legacy và các dòng fixed không so trực tiếp được với nhau**."

### Từng dòng

- **D01 — Fair scorer and provenance (n=992, legacy).**
  > "Đây là việc dựng lại bộ chấm công bằng và ghi rõ nguồn gốc của từng con số. Kết
  > quả chính là phép so ở trang 6: POMA trừ few-shot, cả hai có GSA, âm 1.71 EM, KTC
  > từ âm 3.93 tới dương 0.50; BIF dương 0.33, KTC cũng chứa 0. Kết luận: **không có
  > bằng chứng POMA hơn few-shot**."

- **D02 — GSA finalizer, xuất một đáp án (n=992, legacy).**
  > "Thêm bước GSA, chọn đúng một chuỗi làm đáp án cuối, vào cả hai hệ. POMA từ 66.63
  > lên 68.45, few-shot từ 67.34 lên 70.16. BIF tăng 1.43 cho POMA và 2.27 cho few-shot.
  > GSA **giúp cả hai, nhưng giúp few-shot nhiều hơn** — nên nó không thu hẹp mà còn
  > nới khoảng cách."

- **D04 — Bộ thực thi số học có cổng R2 (n=200, legacy).**
  > "Một executor tính toán, chỉ kích hoạt khi cổng R2 cho rằng câu hỏi cần phép tính.
  > Thử trên bốn reader khác nhau, cả bốn đều giảm khoảng 1 điểm EM, KTC từ âm 2.5 tới
  > 0; BIF âm 0.38. Nguyên nhân em sẽ nói ở trang headroom: cổng kích hoạt đúng vào
  > những câu reader đã làm đúng. **Loại bỏ.**"

- **D09 — Tám cách biểu diễn bảng (n=200, legacy).**
  > "Thử tám định dạng chuyển bảng thành chuỗi. Theo EM thì `md_kv` cao nhất, dương 4.0,
  > nhưng KTC từ âm 2 tới dương 10 — quá rộng. Theo BIF thì lại là `pipe_clean` dẫn,
  > dương 2.21. Hai thước đo chọn hai bản khác nhau, không bản nào có ý nghĩa thống kê:
  > **không có người thắng**."

- **D10 — Chọn hàng cho bảng dài (n=155, legacy).**
  > "Chỉ chạy trên 155 câu có bảng trên 2,000 token: giữ header cộng 20 hàng liên quan
  > nhất theo BM25. EM dương 1.9 nhưng KTC chứa 0; điểm chắc chắn là **token giảm
  > 46.6%**. Đây là lợi ích thật, nhưng về chi phí, không phải độ chính xác."

- **D11 — POMA v3 rút gọn, v3lite (n=992, legacy).**
  > "Năm nhánh lồng nhau, mỗi nhánh thêm một thành phần. Tổng cộng cả bản chỉ hơn
  > control 0.40 EM, KTC từ âm 0.50 tới dương 1.31; BIF dương 0.64. **Không thành phần
  > nào có ý nghĩa riêng.** Chi tiết ở trang 11."

- **D12 — Biểu diễn pipe (n=500, fixed).**
  > "Trên parser đã sửa, bản `pipe_nohdr` — bảng dạng pipe, bỏ dòng header — cho dương
  > 2.0 EM, KTC từ âm 1 tới dương 5; BIF dương 1.10, KTC cũng chứa 0. Sát biên, nên
  > **đáng xác nhận lại**, và thực tế em đã dùng lại nó trong GaP-TQA."

- **D13 — Lọc header bằng LLM (n=200, fixed).**
  > "Cho LLM chọn header để dựng một bảng rút gọn. EM âm 14.5, KTC từ âm 21 tới âm 8;
  > BIF âm 10.10, KTC từ âm 14.09 tới âm 6.37. Cả hai khoảng nằm hẳn phía âm: **loại bỏ,
  > gây hại rõ ràng**."

- **Parser-fix A/B (n=991, cả hai parser).**
  > "Chạy cùng một cấu hình với parser cũ và parser đã sửa. Bản sửa âm 1.41 EM, KTC từ
  > âm 3.13 tới dương 0.30; BIF âm 0.37, KTC chứa 0. Chỉ 72 trên 991 câu đổi kết quả.
  > Em **giữ bản sửa vì nó đúng về dữ liệu**, nhưng không tuyên bố nó cải thiện điểm."

- **N1 — Độ trôi giữa các lần chạy (n=900, legacy).**
  > "Chạy y hệt một cấu hình hai lần: lệch âm 0.44 EM; một quan sát khác lệch tới 1.7.
  > BIF lệch âm 0.12. Kết luận ở cột cuối: **độ trôi này lớn hơn các hiệu ứng em đo
  > được**: các hiệu ứng quanh ±2 điểm chưa diễn giải được cho tới khi đo đủ ba lần chạy."

- **Hybrid BM25 + PhoBERT (n=476).**
  > "Thử thay hoặc trộn truy xuất hàng bằng embedding PhoBERT với BM25. Truy xuất dày
  > **thua BM25 ở mọi giá trị k**, nên bị loại theo quy tắc em đặt ra **trước khi chạy**."

- **Backbone 2: Gemma-3-4B-IT (n=543, legacy).**
  > "Đổi backbone sang Gemma 4B. POMA trừ zero-shot là âm 12.89 EM, KTC từ âm 17.13 tới
  > âm 8.66; BIF âm 9.89, KTC từ âm 12.60 tới âm 7.14. **POMA thua rõ** baseline một
  > lệnh gọi. Lần chạy mới xong 543 câu. Chi tiết ở trang 12."

- **Backbone 3: SEA-LION v3 8B (n=992).**
  > "Ba baseline trên đủ tập test: zero-shot 49.50, few-shot 49.45, CoT 47.83. **Chưa có
  > phép so ghép cặp với POMA**, nên dòng này chưa có kết luận."

- **GaP-TQA, hệ thống riêng, trên dev (n=991, fixed).**
  > "Đây là hệ thống mới, không phải một bản sửa POMA. Bản tốt nhất A5 trừ few-shot cộng
  > Verbalize là dương 1.41 EM, KTC từ âm 0.71 tới dương 3.53 — chưa có ý nghĩa, nhưng
  > **rẻ hơn**: chỉ dùng 61% token prompt của few-shot. Trình bày ở trang 13 đến 17."

### Đoạn chốt

> "Đọc cả bảng: **chỉ có hai dòng có khoảng tin cậy không chứa 0 — D13 và Gemma — và cả
> hai đều âm.** Tức là những can thiệp duy nhất có ý nghĩa thống kê trong dự án này là
> những can thiệp **có hại**. Mọi hướng cải tiến còn lại đều nằm trong vùng không phân
> biệt được với 0. Lợi ích chắc chắn đo được là về chi phí — D10 và GaP-TQA — chứ không
> phải về độ chính xác."

Nếu thầy muốn chi tiết một dòng → mở `context/04-nhat-ky-thuc-nghiem.md`.

---

## Trang 10 — Ba ví dụ tiêu biểu

**Mục tiêu:** cho thấy chiều sâu phân tích, mỗi hướng một kiểu kết quả khác nhau.

> "Em lấy ba ví dụ đại diện cho ba kiểu kết quả.
>
> **D10** là kết quả dương, nhưng về chi phí chứ không phải độ chính xác: trên 155 câu
> bảng dài, token đầu vào giảm 46.6%, chi phí giảm 35.3%, độ trễ từ 29.3 xuống 17.4
> giây; EM từ 52.26 lên 54.19 nhưng KTC chứa 0. Khi ghép vào POMA nhiều tầng và tính
> trên cả 992 câu thì phần tiết kiệm **chỉ còn 6.4%** — bị pha loãng.
>
> **D11** là bản rút gọn của kiến trúc v3, em nói kỹ ở slide sau. Tóm tắt: từ 68.35
> lên 68.75, tổng cộng **13 câu thắng, 9 câu thua trên 992 câu** — mọi KTC đều chứa 0.
>
> **D13** là hướng bị loại: cho LLM chọn header. EM từ 65.5 xuống 51.0, tổng token tăng
> 75.9%, chi phí gấp 2.75 lần. **Cơ chế gây hại không như em dự đoán**: 179 trên 200 câu
> bộ lọc không chọn được hàng nào, vì 77.8% bảng không có cột header bên trái. Thiệt hại
> đến từ việc mất **cột dùng để định vị hàng**, không phải mất cột chứa đáp án. BIF đồng
> ý: từ 74.20 xuống 63.86, KTC từ âm 14.09 tới âm 6.37."

---

## Trang 11 — POMA v3lite

**Mục tiêu:** cho thầy thấy **cụ thể** đã xây cái gì, đã cắt cái gì, và mỗi thành phần
mua được bao nhiêu. Dùng sơ đồ để dẫn, đừng đọc bảng số trước.

**Cách dẫn sơ đồ — chỉ tay theo bốn khối lớn, mỗi khối một câu:**

> "Đây là bản v3 rút gọn mà em đã cài và chạy trên đủ 992 câu test.
>
> **Chuẩn bị đầu vào:** câu hỏi qua Question Analyzer để lấy hint; bảng về Flatten V1,
> và nếu dài trên 2,000 token thì H1 giữ header cộng top-k hàng theo BM25 — chính là D10.
>
> **Một solver, không ensemble:** specialist route theo hint, nhiệt độ 0, **một lệnh gọi
> LLM mỗi câu**, để chi phí ngang few-shot. Sau đó chuẩn hoá đáp án bằng quy tắc, không
> gọi LLM.
>
> **Cổng answerability:** chỗ duy nhất được phép xuất `Null`, và chỉ chạy khi đáp án là
> `Null` — tìm lại bằng chứng rồi trả lời lại, hoặc xác nhận đúng là `Null`.
>
> **Đầu ra:** formatter quy tắc, rồi GSA chọn đúng một chuỗi làm đáp án cuối."

**Phần đã cắt trước khi xây:**

> "Ba thành phần của v3 đầy đủ bị cắt **trước khi xây**, mỗi cái vì một số đo: program
> agent vì D04 cho thấy giá trị kỳ vọng thấp; generalist trên một view bảng khác; và
> tầng consensus cộng adjudicator."

**Rồi mới sang bảng số:**

> "Năm nhánh lồng nhau: control 68.35, cộng formatter 68.55, cộng H1 68.45, cộng cả hai
> 68.65, cộng cổng answerability 68.75. **Cả bản chỉ hơn control 0.40 EM**, KTC từ âm
> 0.50 tới dương 1.31; BIF dương 0.64.
>
> Vì sao từng tầng lấy được quá ít: H1 đổi bảng của 91 trên 992 câu, nhưng token prompt
> thực tế **chỉ giảm 6.4%**. Formatter gần như không đổi gì, vì POMA vốn đã chuẩn hoá
> đáp án. Còn cổng answerability thay `Null` 16 lần: **5 lần sửa được lỗi, 4 lần phá
> một `Null` vốn đúng**, 7 lần sai vẫn sai."

**Lưu ý khi trình bày:** chữ trong sơ đồ nhỏ, đừng bắt thầy đọc. Nếu thầy muốn đọc kỹ
thì mở `assets/poma-v3lite.png`.

---

## Trang 12 — Backbone thứ hai và thứ ba

**Mục tiêu:** trả lời trước câu hỏi chắc chắn sẽ bị hỏi.

> "Thầy có thể sẽ hỏi đã thử backbone khác chưa — em xin trả lời luôn.
>
> Với **Gemma-3-4B-IT** qua OpenRouter, POMA-first được 26.70 EM còn zero-shot được
> 39.59. Hiệu là **âm 12.89, KTC từ âm 17.13 tới âm 8.66 — không chứa 0**. BIF cũng
> vậy: âm 9.89, KTC từ âm 12.60 tới âm 7.14. Trên backbone yếu hơn thì POMA **thua rõ
> rệt** baseline một lệnh gọi.
>
> Giới hạn: lần chạy này mới xong **543 trên 992 câu**, parser cũ. Một câu bị loại khỏi
> cả hai nhánh khi tính BIF vì câu trả lời zero-shot quá dài làm sập bộ chấm
> PhoBERTScore — lỗi của scorer, không phải của dữ liệu.
>
> Với **SEA-LION v3 8B** chạy local trên Kaggle bằng vLLM, ba baseline trên đủ tập test
> chụm quanh 48–50 EM; POMA trên một tập con phân tầng 500 câu được 43.00. Nhưng hai
> bên **khác bộ câu hỏi**, nên chưa có phép so ghép cặp và em chưa kết luận gì."

**Khối đỏ:**

> "Mẫu chung: lợi ích của POMA — nếu có — **phụ thuộc vào backbone, và đảo chiều khi
> backbone yếu đi**."

---

## Trang 13 — Vì sao GaP-TQA có hình dạng này

**Mục tiêu:** giới thiệu hệ thống mới, và cho thấy hình dạng của nó đến từ số đo chứ
không phải sở thích.

> "Từ đây em chuyển sang một hệ thống riêng, GaP-TQA.
>
> Bảng bên trái em đếm trên 992 câu test, không gọi API: gold là **nguyên một ô ở 44%**,
> Có/Không 19.3%, một đoạn trong ô 10.4%, và chỉ **3.0% là con số phải tính ra**. Đó là
> lý do executor số học D04 không tìm được gì để sửa. Và chỉ 9% câu có từ hai nhãn hint
> trở lên, nên chia việc cho nhiều agent lúc chạy cũng không có gì để chia.
>
> Bên phải là một thí nghiệm miễn phí: một node **Verbalize** cho câu Có/Không. Gold dùng
> `Đúng`, `Phải` hay `Có` tùy đuôi câu hỏi, còn model gần như luôn trả `Có`. Một luật
> lấy từ train đổi đúng từ đó. Nó nâng few-shot cộng GSA từ **70.16 lên 73.29**, KTC từ
> dương 1.92 tới dương 4.33, và POMA cộng GSA từ 68.45 lên 71.77. Luật tái tạo đúng gold
> ở 90.1% train, 87.6% dev, 91.6% test — nên nó không bị khớp theo test. Trên test: 34
> câu thắng, 3 câu thua."

**Khối xanh — cả hai cổng đã chạy lại trên dev:**

> "Em đã kiểm tra lại trên dev. **Verbalize giữ được**: dương 1.21, KTC từ dương 0.30
> tới dương 2.12, riêng câu Có/Không từ 74.4 lên 81.7. Còn **`Locate`** — cho model
> định vị ID ô — đạt 78 đến 82% trên 133 câu tra cứu thuần, qua được ngưỡng; nhưng
> xuất nguyên văn ô đã định vị thì lại thua reader. Hướng đó em dừng."

**Không được nói:** "Verbalize cứu POMA". Node này giúp mọi hệ, nên nó không đổi thứ tự
POMA so với few-shot.

---

## Trang 14 — GaP-TQA A1: reader + Verbalize

> "Đây là bản đối chứng của GaP-TQA: một lệnh gọi reader trên bảng Flatten V1, rồi node
> Verbalize tất định. Trên dev 991 câu được **70.33 EM**; riêng Verbalize đóng góp dương
> 1.21, KTC từ dương 0.30 tới dương 2.12."

---

## Trang 15 — GaP-TQA A2a: bảng dạng pipe

> "Giống A1, chỉ đổi chuỗi bảng sang `pipe_nohdr` — bản đã sát biên ở D12. Được **71.95
> EM**, hơn A1 dương 1.61 nhưng KTC từ âm 0.30 tới dương 3.53, chưa có ý nghĩa. Em giữ
> lại vì nó rẻ hơn một chút."

---

## Trang 16 — GaP-TQA A5: graph cho từng lớp câu hỏi

> "A5 lấy ý tưởng từ bài GaP: thay vì để LLM tự làm hết, mỗi lớp câu hỏi có **một graph
> cố định**, và model 8B chỉ điền vào các node lá đọc bảng. Hàng neo — các hàng được
> chọn trước để định vị — chỉ dùng cho câu tra cứu. Em biết điều này vì đã thử bật cho
> mọi lớp ở A3, và câu hỏi dạng liệt kê tụt từ 78 xuống 56."

---

## Trang 17 — GaP-TQA so với zero-shot và few-shot, trên dev

**Mục tiêu:** đặt GaP-TQA cạnh đúng mốc so sánh, và nói rõ nó **chưa** thắng.

> "Tất cả trên Qwen3-8B, 991 câu dev, so với mốc mạnh nhất là **few-shot cộng Verbalize,
> 71.85**. Cột W/L là số câu thắng và thua.
>
> Zero-shot thua rõ, âm 9.18. Few-shot thô thua âm 3.53 — đúng bằng phần Verbalize. Các
> biến thể GaP: A1 âm 1.51, A2a dương 0.10, A2b với `markdown_kv` âm 0.71, A3 bật hàng
> neo cho mọi lớp âm 1.82, và **A4 — xuất nguyên ô đã định vị — âm 3.03, KTC không chứa
> 0, tức là thua thật**. Bản tốt nhất **A5 được 73.26, dương 1.41**, 69 thắng 55 thua."

**Khối đỏ:**

> "GaP-TQA thắng zero-shot rõ ràng, nhưng **chưa** thắng few-shot cộng Verbalize: dương
> 1.41 của A5 có KTC chứa 0, và A5 được chọn **sau khi đã nhìn dev**. Em kiểm tra thêm
> trên 1,000 câu train mới: A5 hơn A2a dương 1.10, KTC từ 0 tới dương 2.20 — vẫn chạm 0.
> Cái chắc chắn là chi phí: A5 chỉ dùng **61% token prompt** của few-shot. Và em chưa
> chạy hệ POMA nào trên dev."

**Không được nói:** "GaP-TQA đã tốt hơn few-shot".

---

## Trang 18 — Bước tiếp theo: thử nghiệm cải tiến GaP-TQA

**Mục tiêu:** một câu, nói rõ hướng đi tiếp theo.

> "Bước tiếp theo của em là tiếp tục thử nghiệm các cải tiến cho GaP-TQA."

**Nếu thầy hỏi cụ thể cải tiến gì:** hai việc gần nhất —
(1) một node Granularity: sau Verbalize, 96 lỗi test là do độ chi tiết hoặc định dạng,
kiểu `1709` so với `Năm 1709`; học chính sách theo từng lớp câu hỏi trên train, kiểm
trên dev; (2) sau khi đã ổn trên dev, chạy **một** lần test đóng băng: GaP A5 so với
few-shot cộng Verbalize — tập test vẫn chưa dùng cho GaP-TQA.

---

## Trang 19 — Slide kết

> "Em xin hết. Mong nhận được góp ý của thầy."

---

## Phần hỏi đáp — sáu việc nên chủ động nêu nếu có thời gian

Deck không có slide liệt kê các quyết định, nhưng sáu điều dưới đây vẫn cần ý kiến của
thầy. Nêu bằng lời trong phần thảo luận, theo thứ tự ưu tiên này. Bản đầy đủ ở cuối
[`context/08-huong-di-tiep-theo.md`](context/08-huong-di-tiep-theo.md).

1. **Nộp ở đâu.** README của repo ghi bài đang review ở KAIS, nhưng tên file bản thảo
   là JIT — mà JIT là tạp chí hệ thống thông tin/quản trị, gần như không hợp chủ đề.
   Cần xác nhận trạng thái nộp thật trước khi đầu tư sửa bài.
2. **Đóng khung lại bài theo hướng nào:** A sửa an toàn · B bài phương pháp ·
   **C bài chẩn đoán** (theo em khớp dữ liệu nhất) — hoặc chuyển trọng tâm sang GaP-TQA
   nếu lần chạy test đóng băng cho kết quả.
3. **Thầy có chấp nhận báo cáo kết quả âm không.** Nếu có thì C là hướng ít rủi ro nhất.
4. **Ưu tiên ngân sách API:** dồn cho việc củng cố phép so POMA (đo độ trôi, chạy few-shot + GSA và POMA cùng một lần), hay tập trung cải tiến GaP-TQA.
5. **ViPanelTR** — cùng nhóm, cùng benchmark, nhưng bản thảo POMA chưa trích. Phải
   công bố và phân biệt, tránh nộp trùng.
6. **Phạm vi có mở sang fine-tune không.** Hướng không-huấn-luyện đã thử gần hết.

---

## Phụ lục — Câu hỏi khó và cách trả lời

| Thầy hỏi | Trả lời ngắn |
|---|---|
| "Vậy 80.24 trong bài sai à?" | "Không sai về tính toán, nhưng đó là điểm oracle best-of-K, giống 74.90 ở trang 6 — không phải độ chính xác của hệ xuất một đáp án. Cùng lần chạy đó, lấy đáp án đầu là 67.74." |
| "Sao mấy tháng không cải thiện được gì?" | Trang 9, dòng N1. "Vì độ trôi giữa hai lần chạy giống hệt nhau là 0.44 đến 1.7 điểm, lớn hơn hầu hết hiệu ứng em đo được. Việc đầu tiên phải làm là đo cho ra sàn nhiễu đó." |
| "Em có chắc multi-agent không giúp không?" | "Em không kết luận mạnh như vậy. Em nói là trong cấu hình này — cùng backbone, dưới 10B, đồng nhất — em không đo được lợi ích, và literature cũng dự đoán như vậy." |
| "Sao không thử thêm hướng khác?" | "Em đã thử tám hướng. Vấn đề không phải thiếu ý tưởng, mà là cơ chế can thiệp không chạm đúng vào các câu đang sai: executor số học kích hoạt trên 11 câu mọi reader đã đúng và không chạm câu nào trong 15 câu sai. Nên em chuyển sang GaP-TQA." |
| "GaP-TQA có hơn không?" | Trang 17. "Chưa. A5 hơn few-shot cộng Verbalize 1.41 điểm nhưng KTC chứa 0, và A5 được chọn sau khi nhìn dev. Cái chắc chắn là chi phí: 61% token. Kết luận chỉ đến sau một lần chạy test đóng băng." |
| "Lỗi parser có làm hỏng hết kết quả cũ không?" | "Nó làm các kết quả trước và sau khi sửa không so trực tiếp được. Nhưng A/B đầy đủ cho hiệu âm 1.41 với KTC chứa 0 — chỉ 72 trên 991 câu đổi kết quả. Em giữ bản sửa vì nó **đúng về dữ liệu**, không tuyên bố nó cải thiện EM." |
| "Tốn bao nhiêu tiền rồi?" | "Một lần chạy POMA đầy đủ 992 câu khoảng 1,72 đô. Các thí nghiệm lẻ từ 0,08 đến 0,73 đô. Một lần chạy control nữa để đo độ trôi dự kiến khoảng 5 đô." |
| "Em định bảo vệ bài này kiểu gì?" | "Đóng khung lại thành nghiên cứu chẩn đoán: phần lớn 'gain' trong dạng bài này đến từ chuẩn hoá đáp án và cách chấm bất đối xứng, cộng cảnh báo phương pháp luận về độ trôi. Cái này có tiền lệ trích dẫn." |

## Nguồn số liệu

Mọi con số trong script này đều có trên slide tương ứng (`progress-report.typ`) và truy
ngược được về [`context/`](context/) — chủ yếu là
[`04-nhat-ky-thuc-nghiem.md`](context/04-nhat-ky-thuc-nghiem.md) (thực nghiệm),
[`05-bang-so-lieu-tong-hop.md`](context/05-bang-so-lieu-tong-hop.md) (metadata so sánh)
và [`07-bai-hoc-phuong-phap-luan.md`](context/07-bai-hoc-phuong-phap-luan.md) (bài học).
Các số chỉ có trong phần "Nếu thầy hỏi" (880/992 câu một specialist, lỗi parser 95/329
bảng, 67.74, 72/991) lấy từ bản script trước và `context/`, không có trên slide.
Nếu thầy hỏi chi tiết ngoài slide, mở đúng file đó thay vì trả lời từ trí nhớ.
