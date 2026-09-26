# Multi-agent cho Table QA: khảo sát 2023–2026 và đề xuất cho Open-ViTabQA

Ngày: 2026-09-26. Tài liệu này nối tiếp hai tài liệu:

- [`2026-09-18-multi-agent-small-llm-huong-di.md`](2026-09-18-multi-agent-small-llm-huong-di.md):
  bằng chứng chung về debate/vote/self-correction ở cỡ 8B;
- [`enhance_poma/direction-progress.md`](enhance_poma/direction-progress.md): kết quả D01–D13 đã đo.

Ba báo cáo chi tiết nằm trong [`2026-09-26-supporting/`](2026-09-26-supporting/). Mỗi báo cáo do
một agent viết, và các agent đọc nguồn bằng browser và alphaXiv:

| Báo cáo | Phạm vi | Số nguồn đã mở |
|---|---|---|
| [`tqa-multi-agent-systems.md`](2026-09-26-supporting/tqa-multi-agent-systems.md) | Hệ multi-agent/agentic dành riêng cho Table QA | 26 hệ đọc từ paper, ~20 hệ chỉ khớp ID |
| [`small-model-collab-orchestration.md`](2026-09-26-supporting/small-model-collab-orchestration.md) | Phối hợp model nhỏ, dị thể backbone, orchestration học được, MARL | 40 ID arXiv (23 đọc full text) |
| [`blogs-practitioner.md`](2026-09-26-supporting/blogs-practitioner.md) | Blog kỹ thuật: Raschka, Anthropic, Cognition, LangChain, HF, Google, Uber, Snowflake… | 32 bài |

## Tóm tắt

1. **Nếu không fine-tune, literature không cho thấy multi-agent thật sự (có tương tác) có lợi ở cỡ
   8B khi so cùng ngân sách.** Ngoại lệ có huấn luyện là MALT: ba vai được train riêng trên
   Llama-3.1-8B, thắng debate ở cùng số lệnh gọi trên toán (xem P5).
   - Hầu hết hệ "multi-agent" cho Table QA là workflow cố định kiểu planner → coder → critic.
   - Đối chứng cùng ngân sách hiếm, và gần như chỉ có ở backbone ≥70B (Mix-SC, Table-Critic, MACT,
     CHASE-SQL).
   - Ở Qwen3-8B chỉ có hai kết quả:
     - Mixture-of-Minds: lợi chỉ ở câu tính toán, loại câu chỉ chiếm 3,0% dữ liệu của ta.
     - Critic DRE: +1,1 đến +1,8, dưới ngưỡng phân giải.
   - Không paper nào so với few-shot + chuẩn hoá đáp án, là đối chứng mạnh nhất của ta.
   - Agent A không tìm thấy hệ agent Table QA tiếng Việt nào ngoài ViPanelTR/POMA của nhóm.
     `docs/research/Khoi/` có nhắc một agent ở VLSP 2025 NumQA, nhưng hệ đó chưa được kiểm tra.
2. **Cơ chế có bằng chứng ở ≤10B là đa dạng nguồn ứng viên (công cụ, góc nhìn hoặc model) cộng
   với một bước chọn, không phải persona.**
   - Ví dụ: Mix-SC, MATA, CHASE-SQL, LLM-Blender.
   - Practitioner cũng khuyên vậy: control flow đặt trong code, bước cuối *chọn* chứ không *viết
     lại* đáp án.
   - Google (arXiv 2512.08296) đo được multi-agent âm khi hệ đơn đã đạt trên ~45%; hệ của ta ở ~70%.
3. **Thí nghiệm thử trên dev hôm nay, 0 lệnh gọi API** (§4.1): bỏ phiếu giữa ba ứng viên có sẵn
   thuộc **hai họ prompt khác nhau** (GaP A5, few-shot + Verbalize, GaP A2b) đạt **74,67 EM**.
   - So với A5: **+1,41 [+0,30; +2,62]**.
   - So với FS+Verbalize: **+2,83 [+1,01; +4,74]**.
   - Bốn arm **cùng họ prompt GaP** thì cho −0,30, dù tốn nhiều lệnh gọi hơn.
   - Vậy lợi ích đến từ **đa dạng họ prompt**, không đến từ số lệnh gọi.
   - Đây là số hậu nghiệm và **chưa qua cổng ≥ 2 EM so với A5**, nên phải xác nhận trên dữ liệu mới.
4. **Đây là một workflow, không phải multi-agent.**
   - Nếu luận văn muốn giữ chữ "multi-agent" thì phải có một phép thử tương tác thật.
   - Phép thử rẻ nhất là **đối chất giữa hai reader trên 22,4% câu chúng bất đồng** (P2b), so với
     các phiếu bầu tốn cùng số lệnh gọi.
5. **Cần mở lại một hướng đã bị loại.**
   - [`direction-progress.md`](enhance_poma/direction-progress.md) ghi "consensus + adjudicator:
     loại bằng số học, chưa chạy". Phép loại đó dựa trên cặp POMA–FS trên test: 44,2% câu bất đồng
     là cả hai cùng sai.
   - Trên dev, cặp A5–FS+v có 36,0% (80/222) câu bất đồng mà cả hai cùng sai, và chỉ thêm một phiếu
     thứ ba đã được +1,41.
   - Hai con số khác nhau cả về split, parser lẫn hệ, nên không so trực tiếp được. Tuy vậy phép loại
     bằng số học không còn đứng vững.

## 1. Định nghĩa dùng trong tài liệu: multi-agent hay workflow

Mỗi đề xuất bên dưới được gắn nhãn theo hai tiêu chí:

- **Tự chủ:** có LLM nào quyết định bước tiếp theo không (gọi công cụ nào, dừng hay lặp lại)?
- **Tương tác:** có hai vai nào đọc output của nhau và phản hồi không?

| Nhãn | Tự chủ | Tương tác | Ví dụ trong repo |
|---|---|---|---|
| **Workflow** | Không | Không | GaP-TQA A5, POMA hiện tại (router 1:1, specialist không thấy nhau) |
| **Agent đơn** | Có | Không | ReAct một model gọi SQL/Python |
| **Multi-agent** | Có hoặc không | **Có** | Critic đọc lời giải rồi yêu cầu sửa; planner nhận phản hồi từ executor |

POMA và GaP-TQA hiện đều là workflow. Nếu luận văn muốn giữ chữ "multi-agent" thì phải có ít nhất
một kênh tương tác thật và một phép đo cô lập đóng góp của kênh đó.

Literature dùng từ này lỏng hơn nhiều: Uber gọi mỗi lệnh gọi LLM hẹp là một "agent", Chip Huyen
gọi plan → validate → execute là multi-agent. Vì vậy khi trích một paper "multi-agent", cần xem nó
thuộc hàng nào của bảng trên.

## 2. Ràng buộc đã đo — mọi đề xuất phải qua

| Đại lượng | Giá trị | Hệ quả |
|---|---|---|
| Kích thước bảng | p50 ≈ 647 token, p90 ≈ 2.097 | Phương pháp giải bài toán ngữ cảnh dài chỉ chạm ~10% dữ liệu |
| Dạng đáp án gold (test) | 1 ô 44,0%; Yes/No 19,3%; span trong ô 10,4%; văn bản tự do 7,1%; số có sẵn 5,1%; nhiều ô 5,0%; `Null` 4,5%; **số phải tính 3,0%** | Kênh tính toán có trần rất thấp |
| Số hint mỗi câu | 91% chỉ 1 nhãn | "Nhiều specialist song song" hầu như không song song |
| Tương quan lỗi POMA–FS (test, cùng backbone) | cùng sai 240/992, gấp 2,30 lần kỳ vọng độc lập; κ = 0,62 | Ensemble cùng backbone có trần thấp |
| Độ lệch giữa hai lần chạy cùng cấu hình | 0,44 và 1,7 điểm EM (hai quan sát) | Hiệu ứng < ~2 điểm không diễn giải được |
| Đối chứng mạnh nhất (dev, 991 câu) | FS + Verbalize **71,85**; GaP A5 73,26 (+1,41 [−0,71; +3,53] so với FS+v, chọn sau khi xem dev) | Mọi đề xuất phải so với FS+Verbalize và A5, không phải zero-shot |
| Backbone thứ hai | Gemma-3-4B: POMA thua ZS 12,89 điểm (KTC loại 0) | Pipeline nhiều bước hại model yếu |

Các hướng đã đo và loại; chỉ đề xuất lại nếu có cơ chế mới:

| Hướng | Mã | Kết quả |
|---|---|---|
| Executor DSL ghi đè đáp án | D04 | 0 thắng / 2 thua |
| Các cách biểu diễn bảng | D09, D12 | 8 + 4 cách, không cách nào có ý nghĩa |
| LLM lọc header | D13 | −14,5 |
| Cổng answerability kiểu v3lite | D11 | 16 lần thay: 5 cứu, 4 phá |
| Hội đồng persona cùng backbone | D14 | Không giúp |
| Trọng số theo confidence | — | AUROC 0,588 |
| `empty → Null` | — | −8,88 |
| Locate theo ID + phát ô | GaP A4 | −1,51 so với A1; −3,03 so với FS+v |

## 3. Literature nói gì

### 3.1 Bản đồ các pattern multi-agent cho Table QA

Nhãn ở cột cuối dùng định nghĩa của §1.

| Pattern | Hệ tiêu biểu | Bằng chứng ở ≤10B | Cùng ngân sách? | Với Open-ViTabQA | Nhãn |
|---|---|---|---|---|---|
| Planner + coder (SQL/Python), ReAct | MACT, ReAcTable, TableZoomer, Orchestra, Chain-of-Query | Có (Qwen2-7B, Llama-3.1-8B, Qwen3-8B), nhưng chỉ so với CoT một call; ReAcTable ở Llama-3.1-8B chỉ đạt 2,5% | Không | Kênh code nhắm vào 3,0% câu có số phải tính; D04 đã cho 0/2 | Agent đơn / workflow |
| Nhiều đường khác công cụ hoặc view, rồi vote/chọn | Mix-SC, MATA, H-STAR, CHASE-SQL | MATA (3–8B + bộ chọn DeBERTa 435M) | Mix-SC theo số mẫu (+6,7); CHASE-SQL so với SC (+4,2) | **Khớp với pilot §4.1** → P1, P3 | Workflow |
| Vòng critic/verifier | Table-Critic, Critic DRE, ST-Raptor, MAPLE | DRE trên Qwen3-8B: +1,1 (critic 4B đã train), +1,8 (critic thấy gold) | Table-Critic ở 72B | Dưới ngưỡng phân giải; tín hiệu kích hoạt yếu (D18: AUROC 0,52) → P4 ưu tiên thấp | Multi-agent |
| Panel persona cùng model | PanelTR, một phần MAPLE | — | Không | Ablation của PanelTR cho thấy danh tính persona không có tác dụng; D14 | Multi-agent |
| Chia chunk, bảng dài, KG | CoAgt, TableRAG, DataFactory, Tree-of-Table | — | Không | p50 647 token nên đa số bảng chỉ có 1 chunk; CoAgt chạy lại trong repo đạt 32,36 EM | Workflow |
| Agent huấn luyện bằng RL/SFT | Table-R1, TableMind, Mixture-of-Minds, MATATA, MALT | Có (7–8B) | Mixture-of-Minds: gần cùng ngân sách, lợi chỉ ở câu tính toán, MARL chỉ +0,6 | Cần fine-tune (quyết định #6 của GVHD) → P5 | Tuỳ hệ |
| Orchestration học được | Puppeteer, MasRouter, MaAS, AFlow, MAS-GPT, OptiMAS | Executor gần như luôn ≥32B | MAS-GPT chỉ hơn SC +0,6 đến +1,2 | Không hợp một đề tài 8B | Multi-agent |
| Router/cascade giữa các model | RouteLLM, Router-R1, "routing plateau" (2606.07587) | Có | — | Router kNN ngang router huấn luyện và cách oracle 10–30 điểm; hợp để giảm chi phí hơn là tăng EM | Workflow |

Ba cảnh báo khi đặt số literature cạnh số của ta:

1. **EM nới lỏng.** Nhiều gain đo bằng EM đã chuẩn hoá hoặc do LLM chấm lại: CoAgt, AutoPrep dùng
   evaluator Binder, Table-R1, ST-Raptor. EM chặt của Open-ViTabQA sẽ làm các gain này co lại.
2. **Baseline yếu ở ≤10B.** Orchestra, CoQ-8B và TableZoomer-8B chỉ so với CoT/PoT một call.
   Orchestra tốn khoảng 24 request mỗi câu.
3. **Nghi vấn rò rỉ ở MAPLE.** Memory của MAPLE tóm tắt từ đáp án gold, và số note khớp kích thước
   tập test. Đây là suy luận của agent, chưa kiểm trên code. Không dùng MAPLE làm căn cứ.

### 3.2 Bài học từ practitioner

Các bài học dưới đây nhất quán giữa Anthropic, LangChain, Cognition, HF, Google và Raschka.
Chi tiết ở [`blogs-practitioner.md`](2026-09-26-supporting/blogs-practitioner.md).

- **Chỉ dùng multi-agent khi task song song hoá được và vượt ngữ cảnh một agent.** Anthropic đo
  được +90,2% nhưng tốn khoảng 15× token, và token giải thích 80% phương sai. Bảng nhỏ và câu hỏi
  một bước không thuộc chế độ đó.
- **So ở cùng lượng tính toán**, với self-consistency hoặc best-of-N của prompt tốt nhất.
- **Bước cuối chọn hoặc chép, không diễn đạt lại.** LangChain đo được supervisor mất điểm vì
  "dịch" lại output của sub-agent. Với 44% đáp án là nguyên một ô, đây là rủi ro EM trực tiếp.
- **Ưu tiên kiểm tra tất định hơn LLM critique**, ví dụ đáp án có khớp một ô không, hay phép tính có
  tái tạo được bằng code không.
- **Model 8B yếu ở quyết định "làm gì tiếp" và chịu "structure tax" khi phải sinh JSON giữa các
  vai.** Vì vậy luồng điều khiển nên nằm trong code.

Mọi con số định lượng ở đây đo trên frontier model; áp sang Qwen3-8B là suy luận.

## 4. Đo trên dữ liệu của ta (0 lệnh gọi API)

Hai phép đo dưới đây dùng hai split khác nhau và hai thế hệ artifact khác nhau, nên **không ghép
chung một bảng**.

### 4.1 Dev, 991 câu: gộp ứng viên từ các arm đã lưu

- **Dữ liệu:** đúng các artifact trong bảng kết quả dev của
  [GaP-TQA dev plan](GRAPH/2026-09-23-gap-tqa-dev-plan.md). EM từng arm khớp báo cáo: A5 73,26;
  FS+v 71,85.
- **Vote:** plurality trên đáp án đã `normalize_text`; hoà thì lấy A5.
- **Bộ chọn:** LogisticRegression trên đặc trưng của từng ứng viên, đánh giá bằng 5-fold GroupKFold
  theo `table_id`. Đặc trưng gồm:
  - số arm ủng hộ và arm nào ủng hộ;
  - đáp án khớp nguyên văn hoặc nằm trong một ô;
  - độ dài, có phải `Null` không;
  - lớp câu hỏi do router dự đoán.
- Mọi KTC là bootstrap ghép cặp 95%.

| Pool | Lệnh gọi/câu | Oracle | Vote | Bộ chọn | Vote − A5 | Bộ chọn − A5 | Bộ chọn − FS+v |
|---|---|---|---|---|---|---|---|
| {A5, FS+v} | ~2,0 | 78,81 | 73,26 (= A5) | 74,17 | 0 | +0,91 [0,00; +1,92] | +2,32 [+0,40; +4,24] |
| **{A5, FS+v, A2b}** | **~2,25** (A2b chỉ khi bất đồng) | 80,42 | **74,67** | 75,08 | **+1,41 [+0,30; +2,62]** | +1,82 [+0,50; +3,23] | +3,23 [+1,51; +4,94] |
| {A5, A2a, A2b, A3}, cùng họ prompt GaP | ~4,1 | 79,52 | 72,96 | 72,86 | −0,30 [−1,01; +0,40] | −0,40 [−1,61; +0,81] | +1,01 [−1,11; +3,13] |
| Cả 9 arm (A0, A1, A2a, A2b, A3, A4, A5, FS+v, ZS+v) | ~9 | 83,45 | 73,56 | 74,97 | +0,30 [−1,11; +1,72] | +1,72 [+0,30; +3,23] | +3,13 [+1,41; +4,94] |

Bộ chọn hơn vote cùng pool **+0,40 [−0,40; +1,21]** ở pool 3 arm, và +1,41 [+0,40; +2,52] ở pool
9 arm.

Cách đọc:

1. **Đa dạng họ prompt mới là nguồn lợi, không phải số lệnh gọi.**
   - Pool cùng họ GaP tốn ~4,1 lệnh gọi mà không hơn A5.
   - Pool khác họ tốn ~2,25 lệnh gọi mà hơn A5 +1,41.
   - Pool cùng họ vì vậy đóng vai **đối chứng tính toán** không chính thức.
   - Điều này khớp Self-MoA (arXiv 2502.00674): trộn chỉ có lợi khi các thành viên ngang sức và có
     lỗi khác nhau.
2. **Ở pool nhỏ, vote đã lấy gần hết phần lợi.** Bộ chọn học được chỉ có lợi rõ khi pool lớn và
   có thành viên yếu (pool 9 arm). Vì vậy luật chính nên là vote, còn bộ chọn là nhánh phụ.
3. **Cascade theo đồng thuận.**
   - A5 và FS+v đồng ý trên 769/991 câu (77,6%), với EM 83,09 trên nhóm này.
   - Chỉ 222 câu bất đồng cần phiếu thứ ba. Trong đó 80 câu cả hai cùng sai (36,0%), A5 đúng 87 câu,
     FS+v đúng 73 câu.
   - Trần của một bước chọn hoàn hảo là +55 câu so với A5 (+5,55 EM); phiếu A2b thực tế thu được
     +14 câu.
4. **Chi phí.**
   - Prompt token của pool 3 arm có cascade ≈ 1,46M (A5) + 2,40M (FS) + 0,224 × 3,31M (A2b)
     ≈ **4,6M**.
   - Con số này gấp ~1,9 lần FS và ~3,2 lần A5, tức **không cùng ngân sách**.
   - Muốn so công bằng phải có đối chứng cùng token, ví dụ pool cùng họ ở trên hoặc A5 chạy lại
     nhiều lần.

Bốn lý do khiến các con số trên **lạc quan**:

- A5 được chọn sau khi xem dev.
- Các pool con được chọn sau khi đã chạy 5 pool.
- Mỗi arm chỉ có một lần chạy, trong khi độ lệch giữa các lần chạy lên tới 1,7 điểm.
- Khoảng +1,4 trong mức +3,2 so với FS+v là lợi thế sẵn có của A5 so với FS+v.

Vì vậy số dẫn đầu là mức so với A5 (+1,41), và nó **chưa qua cổng ≥ 2 EM**.

### 4.2 Test, 991 câu: trần oracle khi thêm backbone khác

Nguồn: agent B đo trên artifact legacy, tính EM raw trước finalizer. Tôi đã chạy lại script của
agent và các số khớp. Script chỉ có ở Phụ lục A của
[`small-model-collab-orchestration.md`](2026-09-26-supporting/small-model-collab-orchestration.md),
không có trong `scripts/`.

| Pool (raw, test) | EM thành viên tốt nhất | Oracle | Vote |
|---|---|---|---|
| Qwen 4 prompt (FS, ZS, CoT, TD) | 67,41 | 76,39 | 65,19 |
| + Gemma-3-4B + SEA-LION v3 8B | 67,41 | 80,73 | 66,80 |
| + POMA (7 hệ) | 67,41 | 82,85 | 69,12 |
| Tham chiếu: FS + GSA, một hệ | 69,93 | — | — |

Số trong bảng này lệch vài phần mười so với slide (FS raw 67,34; FS+GSA 70,16). Lý do là bảng này
chấm với `candidate_policy=first` trên giao 991 `qa_id` của mọi hệ, còn số chính thức chấm với
`single-required` trên đủ 992 câu.

Hai backbone khác mở thêm **+4,34 EM trần**, nhưng vote không lấy được phần này. Lý do nằm ở độ
chênh sức giữa các thành viên:

- Pool test gồm các thành viên yếu hơn hẳn: Gemma 40,26, SEA-LION 49,45, CoT 59,43, so với Qwen FS
  67,41.
- Pool dev ở §4.1 gồm các thành viên sát nhau, từ 71,1 đến 73,3.

Hệ quả: backbone yếu chỉ nên vào pool **qua một bộ chọn học được**, không qua vote (P3).

## 5. Đề xuất

Ba tiêu chí chung cho mọi đề xuất:

- **Cổng:** `interpretation_gate` của repo, tức EM tăng ≥ 2 điểm **và** KTC ghép cặp 95% không
  chứa 0.
- **Nơi chọn phương pháp:** dev hoặc mẫu train chưa dùng. Test chỉ chạy một lần.
- **Cặp so sánh:** khớp mọi trường của cấu hình (model, provider, parser, prompt, lần chạy), theo
  bài học của slide Attribution.

### P1 — Cascade chéo họ prompt + vote *(workflow)*

**Luật chốt trước khi chạy xác nhận** (ghi ở đây để không chọn lại sau khi thấy kết quả):

1. Chạy A5 và FS+Verbalize trên mọi câu.
2. Hai đáp án trùng nhau sau `normalize_text` thì dừng.
3. Nếu khác nhau thì chạy A2b làm phiếu thứ ba. Lấy plurality; hoà thì lấy A5.

Bộ chọn học được là nhánh phụ, huấn luyện trên dev và áp nguyên lên mẫu xác nhận.

**Cơ sở:**
- Mix-SC: vote giữa hai công cụ khác nhau thắng SC cùng số mẫu.
- MATA: chỉ chạy đường thứ ba khi hai đường đầu bất đồng.
- MACT: dừng sớm khi các mẫu đồng thuận.
- Self-MoA: trộn chỉ có lợi khi các thành viên ngang sức.
- Pilot §4.1.

**Các cặp phải báo cáo, trên cùng một lần chạy:**
- (a) P1 − A5;
- (b) P1 − FS+v;
- (c) đối chứng tính toán: vote trên pool cùng họ {A5, A2a, A2b, A3};
- (d) prompt token và số lệnh gọi mỗi câu.

**Dữ liệu xác nhận:** `outputs/gap_tqa/train_sample1000`.
- Mẫu này đã có A5 và A2a. Cần chạy thêm FS, A2b và A3; A3 là cần cho đối chứng (c). Tổng khoảng
  3.100 lệnh gọi, ước ~$0,6–0,8.
- Phải dùng đúng prompt few-shot `v3_fs_structured_vi`, lấy từ commit `bb42794`. Template hiện tại
  trong `baseline/prompts.py` là bản khác.
- Các ví dụ few-shot của prompt đó là bảng tự dựng, không có trong dataset (đã kiểm tra), nên không
  lo rò ví dụ.
- Router của A5 được viết từ train, nên bước route trên mẫu này chưa hoàn toàn sạch.

**Trần:** oracle của pool 3 arm trên dev là 80,42, tức +7,16 so với A5. Mức kỳ vọng là khoảng +1,4.

**Quyết định theo kết quả (chốt trước):**

| Kết quả P1 − A5 trên mẫu xác nhận | Quyết định |
|---|---|
| ≥ +2 và KTC không chứa 0 | Chạy test một lần với luật trên |
| KTC không chứa 0 nhưng < +2 | **Không** thay A5. Ghi thành kết quả phụ: "đa dạng họ prompt có hiệu ứng thật nhưng nhỏ, với giá 1,9–3,2× token". Chỉ chuyển sang P2/P3 nếu cần thêm trần |
| KTC chứa 0 | Dừng P1. Pilot dev coi như do chọn sau khi xem |

Vì P1 tốn nhiều token hơn, kết quả hoà được tính là thua.

### P2 — Xử lý câu bất đồng: giám khảo (P2a, workflow) và đối chất (P2b, multi-agent thật)

Đây là phép thử rẻ nhất cho câu hỏi "tương tác giữa các agent có giá trị không". Cả hai nhánh chỉ
kích hoạt ở 222 câu dev mà A5 và FS+v bất đồng (22,4%).

Các file đã lưu của A5 và FS chỉ có đáp án, không có ô bằng chứng. Vì vậy ô bằng chứng phải do
chính lệnh gọi mới tự tìm, không lấy lại từ artifact.

**P2a — Giám khảo, 1 lệnh gọi, workflow.**
- Qwen3-8B nhận câu hỏi, bảng và hai đáp án. Nó phải chọn một đáp án, dẫn ô bảng làm bằng chứng,
  hoặc trả `Null`. Không được viết đáp án mới.
- Không ai phản hồi lại giám khảo, nên theo §1 đây là workflow (pattern "LLM judge" của CHASE-SQL
  và MACT).
- **Đối chứng cùng số lệnh gọi:** phiếu thứ ba A2b ở P1. Phải vượt **74,67** trên dev.

**P2b — Đối chất, khoảng 2 lệnh gọi, multi-agent.**
- Mỗi reader được gọi lại bằng đúng họ prompt của mình. Nó được xem đáp án của bên kia và phải
  hoặc giữ đáp án kèm ô bằng chứng, hoặc đổi sang đáp án kia.
- Kết thúc sau **một vòng**, vì literature cho thấy thêm vòng thì tệ hơn. Nếu vẫn bất đồng, lấy
  đáp án có ô bằng chứng khớp, rồi đến A5.
- Hai reader đọc và phản hồi output của nhau, nên theo §1 đây là multi-agent.
- **Đối chứng ở ≤ 2 lệnh gọi trên câu bất đồng:**
  - pool 3 arm, 1 lệnh gọi thêm: vote 74,67;
  - pool 4 arm {A5, FS+v, A2a, A2b}, 2 lệnh gọi thêm: vote 73,56, bộ chọn 74,87.
  - Phải vượt đối chứng mạnh nhất, tức 74,87.

Với cả hai nhánh, báo cáo số thắng/thua trên 222 câu so với vote và so với bộ chọn (0 lệnh gọi).

**Bằng chứng dự báo là âm:**
- Debate or Vote: tương tác không tăng kỳ vọng so với vote khi các agent đồng nhất.
- CHASE-SQL: ranker LLM chưa tune kém SC 3,3 điểm.
- MACT: chọn bằng LLM kém SC trong Table QA.

Điểm khác ở đây là hai reader thuộc hai họ prompt khác nhau. Dị thể là kết quả dương duy nhất của
literature debate.

**Trần và chi phí:**
- Trần: +55 câu so với A5 trên dev. Phiếu A2b đã thu được +14 câu.
- Chi phí: P2a khoảng 222 lệnh gọi, P2b khoảng 444 lệnh gọi, tổng ~$0,1–0,2.
- Với chỉ 222 câu, KTC sẽ rộng. Vì vậy phải chạy lại trên phần bất đồng của mẫu train xác nhận ở P1.

**Ý nghĩa của kết quả:**
- Nếu P2b thắng mọi đối chứng cùng số lệnh gọi, luận văn có một đóng góp multi-agent đo được.
- Nếu P2a thắng mà P2b không hơn P2a, thì phần có giá trị là bước chọn, không phải tương tác.
- Nếu cả hai thua, đó là một kết quả âm có kiểm soát, củng cố hướng viết bài dạng chẩn đoán
  (Option C ở `slide/context/08`).

### P3 — Backbone khác làm ứng viên cho bộ chọn học được *(workflow)*

**Cơ chế:** thêm một ứng viên từ backbone khác vào pool của P1, và chỉ đưa vào qua bộ chọn học được
(§4.2 cho thấy vote bị thành viên yếu kéo xuống). Ba ứng viên có thể dùng:

| Ứng viên | Chạy ở đâu | Lý do |
|---|---|---|
| SEA-LION v3 8B | Local vLLM trên Kaggle | Đã có pipeline chạy |
| Checkpoint Table-R1 7B (Qwen2.5-7B huấn luyện RLVR cho bảng, đã công bố) | Local | Chuyên bảng, khác cách huấn luyện; tiếng Việt chưa kiểm |
| `gemma-4-E4B-it` | — | Tài liệu 09-18 đã khuyến nghị: khác lab, CI tiếng Việt chồng với Qwen3-8B |

**Cặp so sánh:**
- Chính: bộ chọn trên {A5, FS+v, X} so với bộ chọn trên {A5, FS+v, A2b}. Cặp này có cùng số lệnh
  gọi, nên cô lập được riêng phần dị thể backbone.
- Bộ chọn nên huấn luyện trên 1–2 nghìn câu train. Bắt đầu bằng đặc trưng như pilot; chỉ chuyển
  sang cross-encoder PhoBERT hoặc mDeBERTa (kiểu MATA hoặc LLM-Blender PairRanker) khi đặc trưng
  bão hoà.

**Cảnh báo:** "routing plateau" cho thấy phần thu được thực tế thường rất nhỏ so với trần +4,34.
Chỉ làm P3 nếu P1 đứng vững.

### P4 — Critic bám ô, có một vòng sửa *(multi-agent)* — ưu tiên thấp

**Cơ chế:**
1. Reader trả về đáp án kèm tham chiếu ô.
2. Một bộ kiểm tra tất định xem ô có tồn tại không, và đáp án có nằm trong ô không.
3. Nếu kiểm tra không qua, critic phân loại lỗi theo cây lỗi hàng/cột của Table-Critic.
4. Reader sửa một lần.

**Bằng chứng ngược:**
- DRE chỉ cho +1,1 đến +1,8 trên Qwen3-8B.
- Tín hiệu "ô tồn tại" có AUROC 0,52 (D18), nên bộ kích hoạt gần như ngẫu nhiên.
- Tỉ lệ phá câu đúng thấp của Table-Critic chỉ được chứng minh ở ≥70B.

**Pilot:** 200 câu dev, ~$0,1. Đếm số câu sửa đúng và số câu phá. Dừng nếu sửa/phá < 3 hoặc lợi
ròng < +2 câu trên 100.

### P5 — Huấn luyện vai kiểu MALT *(multi-agent lúc huấn luyện)* — chỉ khi GVHD cho fine-tune

**Cơ chế:** huấn luyện LoRA ba vai generator, verifier, refiner trên SEA-LION hoặc Qwen3-8B local,
với dữ liệu 7,9k câu train. MALT dùng 2–6k cặp mỗi vai, cùng quy mô với dữ liệu của ta.

**Đối chứng bắt buộc:**
- SFT **một** model trên cùng dữ liệu, kiểu STaR;
- pool P1 ở cùng số lệnh gọi.

**Lưu ý:** Mixture-of-Minds cho thấy trên Qwen3-8B phần lớn lợi ích đến từ workflow có công cụ, và
MARL chỉ thêm +0,6. Vì vậy có thể kỳ vọng phần đóng góp của "multi-agent" nhỏ hơn phần đóng góp của
dữ liệu.

## 6. Không đề xuất, và lý do

| Hướng | Lý do | Căn cứ |
|---|---|---|
| Panel persona hoặc hội đồng cùng backbone | Danh tính persona không có tác dụng; thêm vòng thì tệ hơn | PanelTR ablation; D14; tài liệu 09-18 |
| Debate nhiều vòng | Không tăng kỳ vọng so với vote | Debate or Vote (2508.17536) |
| Orchestration học được (Puppeteer, MasRouter, MaAS, AFlow, MAS-GPT, OptiMAS) | Executor ≥32B hoặc API; chỉ hơn SC +0,6 đến +1,2 | [small-model-collab-orchestration.md](2026-09-26-supporting/small-model-collab-orchestration.md) |
| Fusion sinh lời mới (MoA, GenFuser) | Viết lại đáp án làm mất EM trên 44% đáp án là một ô | LangChain "translation"; §3.2 |
| Agent chia chunk, bảng dài, KG | p50 647 token | CoAgt 32,36 EM trong repo; D10 |
| Planner + coder SQL/Python làm đường chính | Số phải tính chỉ 3,0%; executor 0/2; độ sâu lồng header của 329 bảng chưa đo | D04; Mixture-of-Minds; ST-Raptor so với IM-TQA. Chỉ nên vào pool P3 như một ứng viên |
| Router học được giữa các backbone (không có bộ chọn) | Kỳ vọng < 2 EM | Routing plateau; trần Qwen–SEA-LION có GSA +4,84 |
| Memory kiểu MAPLE | Nghi rò rỉ gold | [tqa-multi-agent-systems.md](2026-09-26-supporting/tqa-multi-agent-systems.md) §4.2 |

Hai tiền ấn phẩm được agent dẫn nhưng không kiểm chứng được tác giả hay trạng thái bình duyệt là
2609.04217 (planner/critic tiến hoá về prompt rỗng ở 7B cùng số lệnh gọi) và 2606.27288 (trần
co-failure). Không đề xuất nào ở trên dựa vào hai bài này. Trần oracle = 1 − β là một đồng nhất thức
sơ cấp, đúng bất kể phần thực nghiệm của 2606.27288.

## 7. Thứ tự làm

| # | Việc | Chi phí | Điều kiện |
|---|---|---|---|
| 0 | N1: đo độ lệch giữa các lần chạy (`slide/context/08`) | ~$5 | Làm song song; quyết định mức hiệu ứng nào tin được |
| 1 | Xác nhận P1 trên `train_sample1000` theo luật đã chốt ở §5 | ~$0,6–0,8 | Cần khôi phục `baseline/prompts.py` từ `bb42794` khi chạy FS |
| 2 | P2a giám khảo và P2b đối chất trên câu bất đồng: dev, rồi xác nhận trên cùng mẫu train | ~$0,2–0,4 | Chạy sau bước 1 để dùng lại các đáp án của mẫu train |
| 3 | P3 thêm backbone khác qua bộ chọn | Kaggle (miễn phí) + vài $ API | Chỉ khi P1 qua cổng |
| 4 | P4 critic bám ô | ~$0,1 | Chỉ như một pilot để bác bỏ |
| 5 | P5 huấn luyện vai | GPU Kaggle | Chỉ khi GVHD cho fine-tune |

**Cách đóng khung trong luận văn.** Nếu P1 qua cổng mà P2 không thắng phiếu thứ ba, câu chuyện
trung thực là:

> Ở 8B, đa dạng họ prompt cộng với một bước tổng hợp đơn giản có ích; tương tác giữa các agent
> (đối chất) không thêm gì so với vote ở cùng số lệnh gọi.

Đó là một kết luận đo được, và phù hợp với Option C.

## Tái lập

- Pilot §4.1: `python scripts/pool_selector_pilot.py --pool A5 fs+v A2b`. Arm đứng đầu `--pool` là
  arm phá hoà, nên luôn đặt A5 đầu tiên.
  - Pool cùng họ: `--pool A5 A2a A2b A3`.
  - Pool 4 arm dùng làm đối chứng cho P2b: `--pool A5 fs+v A2a A2b`.
  - Cả 9 arm: chạy không có `--pool` (A5 đứng đầu mặc định).
- Số câu bất đồng/đồng ý của cặp A5–FS+v tính bằng `load_arm` của cùng script.
- Trần oracle trên test (§4.2): script ở Phụ lục A của
  [`small-model-collab-orchestration.md`](2026-09-26-supporting/small-model-collab-orchestration.md).
