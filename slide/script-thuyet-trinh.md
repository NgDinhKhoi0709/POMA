# Script thuyết trình — POMA progress report

Kịch bản nói cho `progress-report.pdf` (20 trang: 19 slide đánh số + 1 slide kết).
Mỗi mục dưới đây gồm: **mục tiêu** của slide, **lời nói** (viết sẵn để đọc hoặc
diễn đạt lại), **số phải nhấn**, và **điều không được nói** — vì nhiều con số trong
deck này rất dễ bị phát biểu quá mạnh.

**Về cách đọc số:** script dùng đúng ký hiệu trên slide (dấu chấm thập phân:
`80.24`, `2,000`), để bạn nhìn slide và đọc script không bị lệch. Khi nói tiếng Việt
thì vẫn đọc tự nhiên: "tám mươi phẩy hai bốn".

## Ngân sách thời gian (đủ bộ khoảng 24 phút; mục tiêu 15–20 phút thì cắt theo dòng dưới bảng)

| Trang | Slide | Phút |
|---:|---|---:|
| 1–2 | Bìa + Nội dung | 1 |
| 3–4 | Bài toán + Dữ liệu | 2,5 |
| 5–6 | Hệ thống | 2 |
| **7** | **Chuỗi 80.24** | **2,5** |
| 8 | Quy kết phần tăng | 1,5 |
| 9 | Thước đo BIF + ViNLI tự fine-tune | 1,5 |
| 10–11 | Tổng quan thực nghiệm + ba ví dụ | 2,5 |
| 12 | POMA v3lite (có sơ đồ) | 1,5 |
| 13 | Backbone thứ hai | 1,5 |
| **14** | **Độ trôi giữa các lần chạy** | **2** |
| 15–16 | Headroom + Literature | 2 |
| 17 | Kế hoạch + phát biểu kết luận | 1,5 |
| 18–19 | Hệ thống mới GaP-TQA (sơ đồ + bằng chứng) | 2,5 |

Để về 20 phút: bỏ trang 11, 15, 16 (khoảng 3 phút), rồi rút trang 9 và 19 xuống một câu mỗi trang. **Không bao giờ bỏ trang 7 và 14.**

---

## Trang 1 — Bìa

**Mục tiêu:** vào thẳng vấn đề, không mất thời gian giới thiệu lại đề tài.

> "Em báo cáo tiến độ đề tài POMA — hệ đa tác tử song song cho hỏi đáp trên bảng
> tiếng Việt. Buổi hôm nay em xin trình bày ba việc: hệ thống hiện tại đang chạy ra
> sao, các hướng cải tiến em đã thử và kết quả đo được, và kế hoạch tiếp theo."

**Lưu ý:** đừng hứa "kết quả tốt". Đặt kỳ vọng đúng ngay từ câu đầu là phần lớn
báo cáo này nói về **kết quả đo được không như mong đợi**, và vì sao điều đó lại
có giá trị.

---

## Trang 2 — Nội dung

**Mục tiêu:** cho thầy bản đồ, 20 giây.

> "Em đi theo năm phần: dữ liệu thật sự chứa gì, hệ thống hiện tại, đối chiếu số đã
> công bố với số em audit lại, các thực nghiệm đã chạy, và cuối cùng là bài học
> cùng kế hoạch."

Không dừng lâu ở slide này.

---

## Trang 3 — Bài toán

**Mục tiêu:** chốt phạm vi và ràng buộc, để sau này không ai hỏi "sao không fine-tune".

> "Bài toán là trả lời câu hỏi tiếng Việt trên bảng bán cấu trúc lấy từ Wikipedia,
> benchmark Open-ViTabQA. Câu nào không trả lời được thì phải trả đúng chuỗi `Null`.
> Ba thách thức được nêu trong bài là header nhiều tầng và ô gộp, suy luận nhiều
> bước, và quyết định có trả lời được hay không.
>
> Ràng buộc của đề tài: backbone mở dưới 10 tỷ tham số, **không fine-tune**. Em chỉ
> được can thiệp ở tầng prompt và cấu trúc pipeline. Ràng buộc này quan trọng, vì nó
> quyết định gần như toàn bộ những gì em có thể thử."

**Khối đỏ cuối slide** — đọc chậm, đây là lý do của cả buổi báo cáo:

> "Bản thảo đã nộp báo cáo 80.24 EM. Phần lớn công việc mấy tháng qua của em thực ra
> là đi kiểm tra lại chính con số đó."

---

## Trang 4 — Dữ liệu

**Mục tiêu:** chứng minh em đo dữ liệu chứ không chép lại từ paper, và rút ra hệ quả
thiết kế từ chính dữ liệu đó. Đọc theo cột phải ("Why it matters"), đừng đọc từng con số.

> "Đây là số em đo trực tiếp từ file trong repo, không lấy từ paper. Em xin nói năm
> dòng quan trọng, theo cột bên phải.
>
> **Câu không trả lời được chỉ chiếm 4.5%** — đây là một lớp hiếm, nên mọi cơ chế
> abstention phải tính tới cái giá của việc từ chối nhầm, với tỉ lệ mất cân bằng
> khoảng 20 trên 1.
>
> **Kích thước bảng trung vị chỉ 647 token** — bảng rất nhỏ. Nghĩa là các phương
> pháp sinh ra để giải bài toán context quá dài đang giải sai bài toán cho khoảng
> 90% dữ liệu này.
>
> Nhưng **15.6% số câu có bảng dài trên 2,000 token lại chiếm tới 54.8% tổng số
> token bảng** — chi phí tập trung ở một nhóm nhỏ. Đây chính là lý do em chỉ chạy
> hướng rút gọn bảng trên nhóm đó.
>
> **Trung bình chỉ 1.10 nhãn hint mỗi câu, 91% số câu có đúng một nhãn** — nên thực
> tế chỉ có một specialist được gọi. Em sẽ quay lại ý này ở slide sau.
>
> Và **42.3% đáp án là bản sao nguyên một ô**, tức phần lớn bài toán là định vị ô
> chứ không phải tính toán."

**Số phải nhấn:** 647 token trung vị · 15.6% câu giữ 54.8% token · 91% một nhãn.

**Nếu thầy hỏi về rò rỉ dữ liệu giữa các split:** toàn bộ 296 bảng của tập dev và
289 bảng của tập test đều xuất hiện trong tập train, nên mọi phương pháp dùng dữ
liệu train — few-shot cố định, rule suy từ train, retrieval — phải báo cáo riêng
phần bảng đã thấy và chưa thấy. Em đã bỏ khỏi slide cho gọn.

**Nếu thầy hỏi "bản thảo có ghi sai gì không":** có bốn chỗ, em cũng đã bỏ bảng đó
khỏi slide — nêu bằng lời: unanswerable **4.5% chứ không phải ~10%**; `table_type`
là **bốn nhóm chứ không phải ba** (126 câu thuộc cả hai); trace ghi **46** gold
`Null` trong khi file phát hành có **45**; và "chạy song song" thực tế chỉ xảy ra ở
khoảng 11% số câu. Chi tiết ở
[`context/01-boi-canh-va-du-lieu.md`](context/01-boi-canh-va-du-lieu.md).

---

## Trang 5 — Hệ thống

**Mục tiêu:** mô tả pipeline trong 45 giây, không đi sâu.

> "Đây là POMA đang chạy. HTML được parse thành lưới logic, giải `rowspan`/`colspan`,
> rồi serialize thành biểu diễn Flatten V1. Sau đó hint predictor gán nhãn loại suy
> luận, question refiner viết lại câu hỏi thành truy vấn có ràng buộc tường minh,
> router ánh xạ nhãn sang specialist, các specialist chạy song song, và cuối cùng
> answer normalization gộp kết quả. Không có bước huấn luyện nào."

Đừng giải thích từng agent — slide sau mới là phần quan trọng.

---

## Trang 6 — Ba điểm về kiến trúc

**Mục tiêu:** đây là slide tự phê bình. Nói thẳng, không phòng thủ.

> "Có ba điểm về kiến trúc em cần nói thẳng.
>
> Thứ nhất, **router chỉ là một bảng tra 1:1**. Nó không đưa ra quyết định nào cả;
> quyết định thật nằm ở hint predictor — mà độ chính xác của hint predictor thì chưa
> từng được báo cáo trong bài.
>
> Thứ hai, **chữ 'song song' không thể ảnh hưởng tới độ chính xác**. Các specialist
> không nhìn thấy output của nhau, decoding ở nhiệt độ 0. Chạy song song hay tuần tự
> đều cho đúng một đáp án như nhau. Lợi ích duy nhất có thể có là độ trễ, và bài
> chưa đo độ trễ.
>
> Thứ ba, **song song gần như không xảy ra**: 880 trên 992 câu chỉ gọi đúng một
> specialist."

**Khối đỏ — lỗi parser:**

> "Ngoài ra, ngày 19/9 em phát hiện một lỗi ở tầng tiền xử lý: hàm lấy text của ô
> HTML không có dấu phân cách, nên các đoạn cách nhau bởi thẻ `<br>` bị dính liền
> không khoảng trắng. Phạm vi là **95 trên 329 bảng, ảnh hưởng 325 trên 992 câu
> test**. Lỗi này nằm phía trên mọi thí nghiệm, nên kết quả trước và sau khi sửa
> không so trực tiếp được với nhau. Em sẽ nhắc lại chỗ này ở bảng tổng hợp."

---

## Trang 7 — Chuỗi 80.24 ⭐ SLIDE QUAN TRỌNG NHẤT

**Mục tiêu:** nếu thầy chỉ nhớ một slide, phải là slide này. Nói chậm, đi từng dòng.

> "Đây là slide quan trọng nhất của buổi hôm nay.
>
> Dòng đầu, **80.24** — đó là con số trong bài. Nhưng nó được chấm theo kiểu
> **best-of-K**: hệ sinh ra nhiều đáp án ứng viên, rồi bộ chấm chọn ứng viên khớp
> đáp án chuẩn nhất. Đó là một **trần oracle**, vì khi chạy thật ta chưa biết đáp án
> đúng để mà chọn.
>
> Dòng thứ hai: **cũng lần chạy đó**, nếu chỉ lấy đáp án đầu tiên thì còn **67.74**.
> Chênh lệch 12.50 điểm này **hoàn toàn do cách chấm**, không phải do mô hình suy
> luận tốt hơn.
>
> Bốn dòng dưới là lần chạy mới, cùng scorer, cùng chính sách một đáp án, cho cả
> POMA lẫn baseline. POMA lấy đáp án đầu 66.63; few-shot thô 67.34. Khi áp cùng một
> bộ finalizer GSA cho cả hai thì POMA được 68.45 — còn **few-shot được 70.16**.
>
> Tức là **baseline một lệnh gọi đang cao hơn POMA**."

**Khối đỏ:**

> "Cụ thể: hiệu là **âm 1.71 điểm EM**, khoảng tin cậy ghép cặp 95% từ âm 3.93 tới
> dương 0.50; 53 câu thắng, 70 câu thua, 869 câu hòa. Đây là phép so sánh vững nhất
> em có, vì cả hai nhánh GSA được chạy lại cùng một phiên, cùng bộ câu hỏi."

**Cách phát biểu đúng — học thuộc câu này:**

> "Khoảng tin cậy vẫn chứa 0, nên em **không** kết luận rằng few-shot tốt hơn POMA.
> Điều em kết luận được là: **không có bằng chứng nào cho thấy POMA tốt hơn few-shot**
> khi chấm công bằng."

**Tuyệt đối không nói:** "POMA thua few-shot" (KTC chứa 0) hoặc "POMA không hoạt động".

---

## Trang 8 — Phần tăng đến từ đâu

**Mục tiêu:** trả lời "vậy 13 điểm chênh lệch trong bài là từ đâu ra".

> "Nếu 80.24 không phải là độ chính xác thật, thì phần tăng trong bài đến từ đâu?
> Bảng này lấy từ chính ablation của bài: few-shot 67.14, POMA bỏ answer
> normalization 68.41, POMA đầy đủ 80.24. Tức là **90% phần tăng EM đến từ bước
> chuẩn hoá đáp án**, chứ không phải từ kiến trúc đa tác tử.
>
> Vấn đề là answer normalization **độc lập hoàn toàn với thiết kế đa tác tử** — áp
> nó lên baseline thì baseline cũng tăng y như vậy.
>
> Thêm hai điểm nữa: baseline được chấm trên một chuỗi, còn POMA chấm best-of-K — mà
> thêm ứng viên vào tập best-of-K thì **không bao giờ làm điểm giảm**. Và chính
> baseline của bài cũng phản bác tiền đề: task decomposition 59.38 và
> chain-of-thought 59.17 đều **thấp hơn** zero-shot 62.40 — tức là thêm bước phân rã
> vào một lệnh gọi lại làm hại, điều này bài không thảo luận."

**Khối đỏ:**

> "Còn một mâu thuẫn số học chưa giải quyết: mục 5.6 nói chuẩn hoá lật 177 trên 992
> câu từ sai thành đúng, suy ra bỏ chuẩn hoá phải còn 62.40, không phải 68.41 như
> Bảng 6. Và 68.41% không phải là k chia 992 với bất kỳ k nguyên nào."

---

## Trang 9 — Thước đo BIF và mô hình ViNLI

**Mục tiêu:** giải thích BIF là gì, và báo cáo rằng em đã tự fine-tune mô hình NLI cho nó.

> "Từ slide này, các bảng có thêm cột **BIF**. BIF là thước đo ngữ nghĩa mà chính bài
> Open-ViTabQA dùng: một nửa là PhoBERTScore F1 giữa đáp án chuẩn và đáp án dự đoán,
> nửa còn lại là xác suất mô hình NLI cho rằng đáp án dự đoán **được suy ra từ** đáp án
> chuẩn. Lý do cần nó: EM và F1 ký tự cho 0 điểm khi model trả `1709` còn gold là
> `Năm 1709`, trong khi về nghĩa là đúng.
>
> Để tính BIF cần một mô hình NLI tiếng Việt bốn nhãn, nên **em tự fine-tune XLM-R Large
> trên ViNLI** theo đúng cấu hình của bài gốc: Adam, learning rate 1e-5, batch 16,
> 10 epoch. Trên tập test 2,991 cặp, mô hình của em đạt **85.42 accuracy và 85.49
> macro-F1**, thấp hơn bài gốc khoảng 0.6 điểm."

**Khối đỏ:**

> "Có hai giới hạn. Dữ liệu em dùng là bản mirror trên Hugging Face, không phải bản
> tác giả phát hành, nên đây là tái lập kiểu replication chứ không phải tái hiện chính
> xác. Và BIF chỉ là thước đo phụ: đa số chênh lệch BIF chưa có khoảng tin cậy ghép
> cặp, nên mọi kết luận trong deck vẫn dựa trên EM."

**Không được nói:** "BIF cho thấy POMA tốt hơn". POMA+GSA hơn FS+GSA +0.33 BIF nhưng
không có khoảng tin cậy, còn EM thì ngược chiều.

---

## Trang 10 — Tổng quan thực nghiệm

**Mục tiêu:** chứng minh khối lượng công việc. Đừng đọc hết 13 dòng.

> "Bảng này là toàn bộ thực nghiệm em đã chạy. Em không đọc từng dòng, chỉ xin nêu
> cách đọc.
>
> Cột áp chót là hiệu ứng EM kèm khoảng tin cậy ghép cặp. **Mọi khoảng tin cậy của
> các hướng cải tiến đều chứa 0** — trừ đúng một dòng: D13, và dòng đó **âm**, tức
> là can thiệp duy nhất có ý nghĩa thống kê trong dự án này là một can thiệp **có hại**.
>
> Cột 'Parser' là cột em xin thầy chú ý: D01 đến D11 chạy trên parser cũ, D12 và D13
> chạy trên parser đã sửa. Hai nhóm này **không so trực tiếp được với nhau**, vì
> chuỗi bảng đầu vào đã khác."

Nếu thầy muốn chi tiết một dòng nào đó → mở `context/04-nhat-ky-thuc-nghiem.md`.

---

## Trang 11 — Ba ví dụ tiêu biểu

**Mục tiêu:** cho thấy chiều sâu phân tích, mỗi hướng một kiểu kết quả khác nhau.

> "Em lấy ba ví dụ đại diện cho ba kiểu kết quả.
>
> **D10** là kết quả dương duy nhất, nhưng là về chi phí chứ không phải độ chính xác:
> rút gọn bảng dài giảm 46.6% token đầu vào, giảm 35.3% chi phí, độ trễ từ 29.3 xuống
> 17.4 giây, mà EM không giảm. Nhưng khi ghép vào POMA nhiều tầng và tính trên cả 992
> câu thì phần tiết kiệm **chỉ còn 6.4%** — bị pha loãng.
>
> **D11** là bản rút gọn của kiến trúc v3, em sẽ nói kỹ ở slide sau. Tóm tắt: từ
> 68.35 lên 68.75, tổng cộng **13 câu thắng, 9 câu thua trên 992 câu** — mọi khoảng
> tin cậy đều chứa 0.
>
> **D13** là hướng bị loại: cho LLM chọn header để dựng bảng compact. EM từ 65.5
> xuống 51.0. Điều thú vị là **cơ chế gây hại không phải như em dự đoán**: chỉ 7
> trong 38 câu thua là do mất ô chứa đáp án; phần lớn là do **mất cột dùng để định vị
> hàng**. Và 179 trên 200 câu bộ lọc không chọn được hàng nào, vì 77.8% bảng không có
> cột header bên trái. Chi phí thì tăng gấp 2.75 lần. BIF đồng ý: từ 74.20 xuống
> 63.86, khoảng tin cậy ghép cặp âm 14.09 tới âm 6.37 — cũng không chứa 0."

---

## Trang 12 — POMA v3lite

**Mục tiêu:** cho thầy thấy **cụ thể** đã xây cái gì, đã cắt cái gì, và mỗi thành
phần mua được bao nhiêu. Dùng sơ đồ để dẫn, đừng đọc bảng số trước.

**Cách dẫn sơ đồ — chỉ tay theo bốn stage, mỗi stage một câu:**

> "Đây là sơ đồ của bản v3 rút gọn mà em đã cài và chạy trên toàn bộ 992 câu test.
>
> **Stage 1 — chuẩn bị đầu vào:** câu hỏi đi qua Question Analyzer để lấy hint; bảng
> HTML được đưa về Flatten V1 đã làm sạch, rồi nếu bảng dài trên 2.000 token thì H1
> giữ header cộng top-k hàng theo BM25. Đây chính là D10.
>
> **Stage 2 — một solver duy nhất, không ensemble:** specialist được route theo hint,
> nhiệt độ 0, **một lệnh gọi LLM cho mỗi câu**. Ý đồ ở đây là giữ chi phí ngang
> few-shot, vì few-shot mới là mốc mà POMA đang thua. Sau đó Answer Canonicalizer
> chuẩn hoá yes/no, số, ngày, danh sách — **không gọi LLM**.
>
> **Stage 3 — cổng answerability:** đây là chỗ duy nhất trong sơ đồ được phép xuất
> `Null`. Chỉ khi đáp án là `Null` thì cổng mới chạy: tìm bằng chứng còn thiếu, đối
> chiếu thực thể trong câu hỏi với bảng, rồi trả lời lại kèm ô được trích, hoặc xác
> nhận đúng là `Null`.
>
> **Stage 4 — đầu ra:** formatter quy tắc về đơn vị, dấu thập phân, ngày tháng, rồi
> GSA chọn ra **đúng một chuỗi** làm đáp án cuối."

**Nói phần đã cắt — quan trọng, vì nó cho thấy quyết định dựa trên số đo:**

> "Ba thành phần của sơ đồ v3 đầy đủ đã bị cắt **trước khi xây**, mỗi cái vì một số
> đo cụ thể: **program agent** vì D04 đo trần chỉ 1.8 đến 3.2 điểm mà thực tế lấy
> được 0; **generalist trên view thay thế** vì majority của 3 view chỉ được 55.5%,
> thấp hơn chính nhánh markdown-KV đơn lẻ 56.5%; và **tầng consensus cộng
> adjudicator** vì trong các câu hai nhánh bất đồng thì 44.2% là **cả hai cùng sai**,
> tức là không có gì để chọn."

**Rồi mới sang bảng số:**

> "Bảng bên trái là năm nhánh lồng nhau, mỗi dòng cộng thêm đúng một thành phần:
> control 68.35, cộng formatter 68.55, cộng H1 68.45, cộng cả hai 68.65, cộng cổng
> answerability 68.75. **Tổng cộng cả bản v3lite chỉ hơn control 0.40 điểm**, khoảng
> tin cậy từ âm 0.50 tới dương 1.31.
>
> Và đây là phần em muốn nhấn: **vì sao từng tầng lấy được quá ít**. H1 đổi bảng của
> 91 trên 992 câu, nhưng khi triển khai thật thì token prompt **chỉ giảm 6.4%** — bị
> pha loãng vì trong POMA nhiều tầng, phần bảng chiếm tỉ lệ nhỏ trong prompt.
> Formatter gần như không đổi gì, vì POMA vốn đã có answer normalization nên đầu ra
> đã sạch sẵn. Còn cổng answerability thay `Null` 16 lần: **5 lần cứu đúng, 4 lần phá
> một `Null` vốn đúng**, 7 lần sai vẫn sai."

**Lưu ý khi trình bày:** chữ trong sơ đồ nhỏ, đừng bắt thầy đọc. Chỉ tay theo bốn
khối lớn và nói. Nếu thầy muốn đọc kỹ thì mở file gốc
`docs/research/Khoi/poma3_rutgon.png`.

---

## Trang 13 — Backbone thứ hai

**Mục tiêu:** trả lời trước câu hỏi chắc chắn sẽ bị hỏi.

> "Thầy có thể sẽ hỏi đã thử backbone thứ hai chưa — em xin trả lời luôn ở đây.
>
> Với **Gemma-3-4B-IT**, POMA được 26.70 EM còn zero-shot được 39.59. Hiệu là **âm
> 12.89 điểm, khoảng tin cậy từ âm 17.13 tới âm 8.66 — không chứa 0**. Đây là một
> trong rất ít kết quả có ý nghĩa thống kê của cả dự án, và nó nói rằng trên backbone
> yếu hơn thì POMA **thua rõ rệt** baseline một lệnh gọi.
>
> Em cần nói rõ giới hạn: lần chạy này mới xong **543 trên 992 câu**, chưa đầy đủ.
> BIF đồng thuận: âm 9.89 điểm, khoảng tin cậy âm 12.60 tới âm 7.14, cũng không
> chứa 0. Một câu bị loại khỏi cả hai nhánh vì nó làm sập bộ chấm PhoBERTScore —
> một lỗi của scorer với câu trả lời quá dài, không phải lỗi dữ liệu.
>
> Với **SEA-LION 8B** chạy local, ba baseline chụm quanh 48–50, POMA được 43.0 —
> nhưng trên một tập con khác, nên **chưa có phép so ghép cặp** và em chưa kết luận gì."

**Khối đỏ:**

> "Mẫu chung qua ba backbone: lợi ích của POMA — nếu có — **phụ thuộc vào backbone,
> và đảo chiều khi backbone yếu đi**."

---

## Trang 14 — Độ trôi giữa các lần chạy ⭐ SLIDE QUAN TRỌNG THỨ HAI

**Mục tiêu:** đây là câu trả lời có dữ liệu cho "tại sao mấy tháng chưa cải thiện
được gì". Trình bày như một **phát hiện**, không phải như một lời biện hộ.

> "Slide này giải thích vì sao đến giờ em chưa chứng minh được cải tiến nào.
>
> Em chạy **y hệt một cấu hình hai lần** — cùng model, cùng provider, cùng prompt,
> cùng hint lấy sẵn, cùng parser. Lần một 68.33, lần hai 67.89, lệch 0.44 điểm. Và
> **98 trên 900 câu, tức gần 11%, cho đáp án khác nhau về mặt chữ dù em không đổi bất
> cứ thứ gì**. Một quan sát thứ hai cho độ lệch tới 1.7 điểm.
>
> Bảng bên phải đặt các hiệu ứng em đo được cạnh vùng trôi đó: D10 cộng 1.9, D12 cộng
> 2.0, parser trừ 1.41, D11 cộng 0.40 — **tất cả đều nằm trong hoặc sát vùng trôi**.
> Chỉ có D13, trừ 14.5, là vượt hẳn ra ngoài. Cột BIF bên cạnh kể đúng câu chuyện
> đó lần nữa: cũng nhỏ, cũng trong vùng trôi, trừ D13.
>
> Nói cách khác: **phần lớn những gì em đo được trong mấy tháng qua có độ lớn nhỏ hơn
> chính nhiễu của phép đo.**"

**Khối đỏ — nói rõ giới hạn, đây là chỗ dễ bị vặn:**

> "Em cũng xin nói rõ: đây mới là **hai quan sát đơn lẻ**, chưa phải độ lệch chuẩn đã
> đo. Cần ít nhất ba lần chạy mới ước lượng được khoảng dao động. Đó chính là việc
> đầu tiên trong kế hoạch của em."

---

## Trang 15 — Headroom và phần lấy được

**Mục tiêu:** giải thích **cơ chế** vì sao các can thiệp đều thất bại.

> "Slide này trả lời câu hỏi sâu hơn: vì sao các can thiệp đều không ăn thua.
>
> Cột giữa là trần lý thuyết, cột phải là phần thực tế lấy được. Executor số học trần
> 1.8 đến 3.2 điểm, lấy được **0**. Cổng answerability trần 4.7 điểm, lấy được **0.1**.
>
> Nguyên nhân chung là: **cơ chế can thiệp không phân biệt được trường hợp nên sửa với
> trường hợp không nên sửa.** Cụ thể, executor kích hoạt đúng 11 câu mà **mọi reader
> đã làm đúng rồi**, và **không chạm câu nào trong 15 câu reader làm sai**. Cổng
> answerability thay `Null` 16 lần: 5 lần cứu đúng, 4 lần **phá một `Null` vốn đúng**,
> 7 lần sai vẫn sai."

**Khối xanh — bài học rút ra:**

> "Nên em rút ra một quy tắc: trước khi cài một can thiệp, phải đo **độ chính xác có
> điều kiện của cổng kích hoạt**, chứ không chỉ đếm xem có bao nhiêu câu đang sai.
> Headroom cho biết có bao nhiêu câu sai; cái cần biết là cổng có chạm đúng những câu
> đó không."

---

## Trang 16 — Literature

**Mục tiêu:** đổi khung từ "em làm thất bại" sang "kết quả này đã được dự đoán trước".

> "Điều đáng nói là kết quả của em **không phải một thất bại bất thường**.
>
> Choi và cộng sự ở NeurIPS 2025 chạy đúng cấu hình của POMA — các tác tử đồng nhất
> trên cùng một backbone 7 đến 8 tỷ tham số — và thấy bỏ phiếu đa số **bằng hoặc hơn
> mọi topology tranh luận**, kèm một chứng minh martingale rằng tranh luận không thể
> làm tăng kỳ vọng đúng. Bertalanič và Fortuna chạy 10 tác tử đồng nhất và thấy tranh
> luận thua self-correction cô lập, mà tốn gấp 2 đến 3.4 lần token."

**Khối xanh dương:**

> "Nghĩa là con số 1.27 EM của phần orchestration **nằm đúng trong dải hiệu ứng đã
> công bố** cho deliberation đồng nhất ở quy mô 8B. Nó là kết quả được dự đoán trước."

**Khối xanh lá — đây là phần em muốn đề xuất làm đóng góp:**

> "Và đây là chỗ em nghĩ có thể thành đóng góp công bố được. Choi và cộng sự báo cáo
> **cùng một model** đạt 0.8713 hoặc 0.6620 trên GSM8K, **chỉ khác nhau ở bộ trích
> xuất đáp án**. Họ kết luận rằng cách trích xuất đáp án có thể đảo ngược cả kết luận
> của thí nghiệm. Kết quả answer normalization của POMA chính là một bản **tái lập
> độc lập hiện tượng đó**, trên một ngôn ngữ và một tác vụ khác. Cái này đã có tiền
> lệ để trích dẫn."

---

## Trang 17 — Kế hoạch

**Mục tiêu:** cho thấy bước tiếp theo là **đo**, không phải thử thêm.

> "Kế hoạch của em đặt đo lường trước can thiệp.
>
> **N1** là chạy đúng một cấu hình control ba lần để đo khoảng dao động EM. Khoảng
> 5 đô và 3 giờ, **không cần viết code mới**. Kết quả của nó đặt ngưỡng: hiệu ứng
> phải lớn hơn bao nhiêu thì mới đáng tin, và dưới ngưỡng đó thì không đáng chạy test.
>
> **N2** là chạy lại few-shot cộng GSA **trong cùng một phiên** với control mới. Hiện
> tại phép so sánh trung tâm của luận văn đang đặt 68.75 cạnh 70.16, mà hai số đó từ
> hai phiên khác nhau — trong khi em đã biết là có độ trôi giữa các phiên.
>
> **N3** là siết điều kiện thay thế của cổng answerability, nhưng chỉ làm nếu N1 cho
> thấy sàn nhiễu đủ nhỏ. **N4** là hoàn tất ma trận Gemma. **N5** là hạ k của H1 — rẻ
> và có cơ sở, vì hàng chứa đáp án có thứ hạng BM25 trung vị 0 mà em đang giữ tới 20 hàng.
>
> **N6** là một hệ thống mới cho bài sau, GaP-TQA. Em trình bày ở hai slide tiếp theo."

**Khối đỏ:**

> "Và đây là những việc em **không** định làm tiếp: thêm một tầng nữa vào pipeline,
> thử thêm một cách biểu diễn bảng, xây tầng consensus hay adjudicator, cổng bất đồng
> giữa specialist, hay cân trọng số theo confidence. Mỗi thứ đều đã được đo và đều
> nằm ở hoặc dưới mức nhiễu."

**Khối xanh dương — câu kết của cả buổi, đọc chậm và nguyên văn:**

> "Nếu phải phát biểu vị trí hiện tại của đề tài, em sẽ nói thế này: **chưa có phép
> so sánh công bằng nào — cùng phiên, một đáp án, cùng finalizer — cho thấy POMA
> vượt few-shot; mọi khoảng tin cậy đều chứa 0; và một số tuyên bố trong bản thảo
> không tái lập được.** Nhưng đó **không** đồng nghĩa với 'POMA không hoạt động' —
> dữ liệu chưa đủ để nói mạnh như vậy."

---

## Trang 18 — Hệ thống mới đề xuất: GaP-TQA

**Mục tiêu:** trình bày hướng hệ thống mới cho bài tiếp theo, tách khỏi bản sửa POMA.

> "Đây là hướng em đề xuất cho bài sau, lấy ý tưởng từ GaP, một bài robot học tháng 7
> năm nay. GaP không để LLM viết code tự do cho từng lần chạy. Nó xây **một graph có
> kiểu cho cả một lớp tác vụ**, tập dượt trên nhiều trường hợp, sửa từng node, rồi đóng
> băng graph và chạy mà không cần agent.
>
> Em ánh xạ sang table QA như sau. Phần trên là **học ngoại tuyến trên train**: một model
> mạnh sinh graph cho mỗi lớp câu hỏi, graph được chạy thử trên 100 câu train, mỗi lỗi
> được quy về node gây ra nó bằng cách so với gold, rồi sửa đúng một node và giữ bản sửa
> nếu tốt hơn trên dev. Phần dưới là **lúc test**: graph đã đóng băng, một interpreter
> tất định chạy nó. Qwen3-8B chỉ làm các node lá màu cam: định vị ID ô, trích đoạn,
> phán đoán Có/Không. Nó không bao giờ phải viết chương trình."

---

## Trang 19 — Vì sao GaP-TQA có hình dạng này

**Mục tiêu:** cho thấy hình dạng hệ thống đến từ số liệu đo, không phải từ sở thích.

> "Bảng bên trái em đếm trên 992 câu test, không gọi API. 44% đáp án là nguyên một ô,
> gần 20% là Có/Không, và chỉ **3%** là con số phải tính ra. Đó là lý do executor số học
> D04 không tìm được gì để sửa. Chỉ 9% câu có từ hai nhãn hint trở lên, nên chia việc
> cho nhiều agent lúc chạy cũng không có gì để chia.
>
> Bên phải là một thí nghiệm miễn phí cho node đầu tiên. Gold dùng `Đúng`, `Phải` hay
> `Có` tùy đuôi câu hỏi, còn model gần như luôn trả `Có`. Một luật lấy từ train đổi đúng
> từ đó, và nâng few-shot cộng GSA từ **70.16 lên 73.29 EM**, khoảng tin cậy ghép cặp
> từ +1.92 đến +4.33. Luật tái tạo đúng gold ở 90% train, 88% dev và 92% test, nên nó
> không bị khớp theo test."

**Khối đỏ:**

> "Con số này không bị ảnh hưởng bởi độ trôi ở trang 14: node chỉ đổi nhãn trên đáp án
> đã lưu, không sinh lại gì, nên chạy lại bao nhiêu lần cũng ra đúng 73.29.
>
> Nhưng node này giúp mọi hệ, kể cả POMA, nên nó không cứu được POMA so với few-shot.
> Đối chứng mới phải là 73.29. Bước tiếp theo là xác nhận trên dev, rồi kiểm tra Qwen3-8B
> có định vị đúng ô ít nhất 70% không. Không đạt thì dừng hướng này."

**Không được nói:** "GaP-TQA đã tốt hơn". Mới có một node tất định được đo, và đo
hậu nghiệm trên test.

---

## Trang 20 — Slide kết

> "Em xin hết. Mong nhận được góp ý của thầy."

---

## Phần hỏi đáp — sáu việc nên chủ động nêu nếu có thời gian

Deck **không còn slide liệt kê các quyết định**, nhưng sáu điều dưới đây vẫn cần ý
kiến của thầy. Nêu bằng lời trong phần thảo luận, theo thứ tự ưu tiên này. Bản đầy
đủ ở cuối [`context/08-huong-di-tiep-theo.md`](context/08-huong-di-tiep-theo.md).

1. **Nộp ở đâu.** README của repo ghi bài đang review ở KAIS, nhưng tên file bản thảo
   là JIT — mà JIT là tạp chí hệ thống thông tin/quản trị, gần như không hợp chủ đề.
   Cần xác nhận trạng thái nộp thật trước khi đầu tư sửa bài.
2. **Đóng khung lại bài theo hướng nào:** A sửa an toàn · B bài phương pháp ·
   **C bài chẩn đoán** (theo em khớp dữ liệu nhất).
3. **Thầy có chấp nhận báo cáo kết quả âm không.** Nếu có thì C là hướng ít rủi ro nhất.
4. **Ưu tiên ngân sách API:** dồn cho N1 và N2, hay tiếp tục thử can thiệp mới.
5. **ViPanelTR** — cùng nhóm, cùng benchmark, nhưng bản thảo POMA chưa trích. Phải
   công bố và phân biệt, tránh nộp trùng.
6. **Phạm vi có mở sang fine-tune không.** Hướng không-huấn-luyện đã thử gần hết.

---

## Phụ lục — Câu hỏi khó và cách trả lời

| Thầy hỏi | Trả lời ngắn |
|---|---|
| "Vậy 80.24 sai à?" | "Không sai về mặt tính toán, nhưng nó là điểm oracle best-of-K, không phải độ chính xác của hệ xuất một đáp án. Cùng lần chạy đó, lấy đáp án đầu là 67.74." |
| "Sao mấy tháng không cải thiện được gì?" | Trang 14. "Vì độ trôi giữa hai lần chạy giống hệt nhau là 0.44 đến 1.7 điểm, lớn hơn mọi hiệu ứng em đo được. Nên việc đầu tiên phải làm là đo cho ra sàn nhiễu đó." |
| "Em có chắc multi-agent không giúp không?" | "Em không kết luận mạnh như vậy. Em nói là trong cấu hình này — cùng backbone, dưới 10B, đồng nhất — em không đo được lợi ích, và literature cũng dự đoán như vậy." |
| "Sao không thử thêm hướng khác?" | Trang 15. "Em đã thử 8 hướng. Vấn đề không phải thiếu ý tưởng, mà là cơ chế can thiệp không chạm đúng vào các câu đang sai. Em nghĩ nên đo trước rồi mới can thiệp tiếp." |
| "Tốn bao nhiêu tiền rồi?" | "Một lần chạy POMA đầy đủ 992 câu khoảng 1,72 đô. Các thí nghiệm lẻ từ 0,08 đến 0,73 đô. N1 dự kiến khoảng 5 đô." |
| "Lỗi parser có làm hỏng hết kết quả cũ không?" | "Nó làm các kết quả trước và sau khi sửa không so trực tiếp được. Nhưng khi em chạy A/B đầy đủ thì hiệu chỉ là âm 1.41 điểm với KTC chứa 0 — chỉ 72 trên 991 câu đổi kết quả. Em giữ bản sửa vì nó **đúng về mặt dữ liệu**, chứ không tuyên bố nó cải thiện EM." |
| "Em định bảo vệ bài này kiểu gì?" | Trang 16 + 17. "Em đề xuất đóng khung lại thành một nghiên cứu chẩn đoán: đóng góp là chỉ ra phần lớn 'gain' trong dạng bài này đến từ chuẩn hoá đáp án và cách chấm bất đối xứng, cộng với cảnh báo phương pháp luận về độ trôi. Cái này có tiền lệ trích dẫn được." |

## Nguồn số liệu

Mọi con số trong script này đều có trên slide tương ứng và truy ngược được về
[`context/`](context/) — chủ yếu là
[`04-nhat-ky-thuc-nghiem.md`](context/04-nhat-ky-thuc-nghiem.md) (thực nghiệm),
[`05-bang-so-lieu-tong-hop.md`](context/05-bang-so-lieu-tong-hop.md) (metadata so sánh)
và [`07-bai-hoc-phuong-phap-luan.md`](context/07-bai-hoc-phuong-phap-luan.md) (bài học).
Nếu thầy hỏi chi tiết ngoài slide, mở đúng file đó thay vì trả lời từ trí nhớ.
