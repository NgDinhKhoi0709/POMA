# Agent 1: Decomposition / program-aided Table QA (da verify tu paper text)

## BA KET QUA TRU COT
(a) TAT-LLM (arxiv 2401.13223) ablation BO External Executor (executor la CODE TAT DINH, 0 LLM call):
    7B:  FinQA -16.66 EM, TAT-QA -17.80, TAT-DQA -16.54
    70B: FinQA  -6.71,    TAT-QA  -4.81,  TAT-DQA  -4.81
    => Gia tri cua viec DUA TINH TOAN RA NGOAI DAU LLM GIAM DON DIEU THEO SCALE.
    Day la bang chung sach nhat rang program-aided dang gia nhat DUNG o rang buoc <10B.
    TAT-LLM(7B) hon GPT-4 ca 3 bo: FinQA 64.60 vs 63.91; TAT-QA EM 74.56 vs 71.92.
    Theo loai cau hoi vs base LLaMA-2-7B-chat: Arithmetic +274.7%, Counting +109.1%, Span +41.6%
    External Executor Algorithm 1 (AN CAP NGUYEN VAN, khong can train):
      equation hop le -> round(eval(.),4); chua '#' -> dem so phan tach;
      chua '>' hoac '<' -> eval; 'N.A.' -> quay ve span cua Extractor
    Sau executor: KHONG CON loi execution nao; loi con lai deu la Extractor (48% sai evidence)
    va Reasoner (19% sai operator).

(b) Mixture-of-Minds (Meta, arxiv 2510.20176) chay workflow plan/code/answer KHONG TRAIN tren TableBench:
    LLaMA-3.1-8B: 15.42 -> 14.58  (KHONG CAI THIEN)
    Qwen3-8B:     41.98 -> 47.38  (+5.4)
    => Cung workflow, cung size class, KET QUA NGUOC NHAU. Backbone KHONG thay the duoc cho nhau.
    Sau MCTS+GRPO: 46.72 va 57.44.
    Sequential scaling (sinh lai code kem error message den khi chay duoc): +1.30% trung binh,
    nhung tren LLaMA-3.1-8B rieng Data Analysis 31.69 -> 49.47.

(c) TableMaster (ICLR 2026, arxiv 2501.19378) Table 11 WikiTQ - SYMBOLIC KHONG PHAI "kenh chinh xac":
    gpt-4o:        textual 83.98 | symbolic 74.63 | text-guided symbolic 76.82
    gpt-4o-mini:   textual 72.97 | symbolic 61.83 | text-guided 68.83
    gpt-3.5-turbo: textual 59.92 | symbolic 50.32 | text-guided 61.97  <- chi model YEU NHAT moi thang
    Weaver Table 6: GPT-4o-mini co TY LE LOI SQL 42.5% vs GPT-4o 15.0% - quy cho "smaller model size"

## CANH BAO LON NHAT CHO MERGED CELLS (53.5% cau hoi cua ta)
Mix Self-Consistency (NAACL 2024, arxiv 2312.16702), perturbation cau truc tren WikiTQ Table 1:
  Transposition: PyAgent 55.91 -> 12.45 (-77.73%) ; Direct Prompting chi -14.05%
  Transpose+shuffle: PyAgent -> 8.96 (-83.97%)
=> SUY LUAN SYMBOLIC MONG MANH VOI BIEN DOI CAU TRUC GAP ~5x so voi doc text.
   Voi 53.5% cau hoi tren bang merged, mot SQL agent ngay tho tren luoi flatten la RUI RO, khong phai tai san.
   NORM cua ho khoi phuc PyAgent ve 55.44.
Complementarity (50 loi moi ben): DP loi chinh la hieu sai bang (42%);
   PyAgent loi chinh la coding (38%) + execution (12%). PHAN BO LOI KHAC NHAU tren cung input
   = kenh doc lap that su. Self-eval chi voi 2 duong = bang 10 duong cua mot loai.
TableMaster tren HiTab: phai dung o1 chuyen bang phan cap thanh subtable quan he -> 74.2,
   THUA E5 (77.3) lam truc tiep tren phan cap. Tu chan doan: "information loss during conversion".
   => FLATTEN BANG PHAN CAP DE SQL CHAY DUOC LA PHA HUY THONG TIN.
ProgramTab (Tencent 2607.11207) cong thuc HiTab DON GIAN HON VA TOT HON: ghep header phan cap
   bang dau ':' -> HiTab 83.57.

## TOP 3 XEP HANG CUA AGENT 1
#1 Chain-of-Query (arxiv 2508.15809) - DUY NHAT bao cao sub-10B open-weight + ty le invalid-SQL
   LLaMA-3.1-8B: WikiTQ 62.18, invalid SQL 5.62% (vs basic text-to-SQL 44.13/16.71%, Chain-of-Table 54.17)
   Ablation WikiTQ/GPT-3.5: bo clause-by-clause SQL -17.04; bo hybrid reasoning division -18.81
     (hai muc giam lon nhat DEU la co che orchestration, khong phai prompt/format)
   Cost 7.63 call TB (toi da 22). 5 dataset ke ca IM-TQA (cau truc phuc tap) - CHUA VERIFY duoc so IM-TQA
   Xu ly loi: memory cac SQL da validate; clause hong khong sua duoc -> quay ve query hop le cuoi cung
#2 MATA - da co trong my_findings.md. Diem moi tu agent 1:
   5 model sub-10B: llama3.2-3b, mistral-7b, phi4-mini-3.8b, qwen2.5-3b, qwen2.5-7b
   llama3.2-3b full-test EM: WikiTQ .535 TabMWP .713 TabFact .688 (vs MixSC .232/.216/.612)
   Latency 27.55s vs TabLaP 48.89, MixSC 44.48. Tools chi ~0.6% latency
   Appendix A: KHONG co quy luat nhat quan model nao hop CoT/PoT/text2SQL - phan loai theo task type
     cua Mix-SC/SynTQA "do not generalize well across different model scales or series"
   CANH BAO: Format Matcher CHINH LA answer normalizer -> PHAI ablate rieng
#3 ProTrix (EMNLP 2024 Findings, arxiv 2403.02177) - RE NHAT: 2 call/cau
   Llama-3-8B fine-tune: WikiTQ 67.0, TabFact 79.4, FEVEROUS 84.5, 8 dataset
   Fine-tune RE THAT: 6,021 instance, 4x A40 48GB, ~5 gio
   DUY NHAT ablate execution-fallback RIENG (Table 10, GPT-3.5):
     co fallback 65.2/83.5/65.8 vs khong 60.5/79.6/53.8 (WikiTQ/TabFact/FEVEROUS)
   DUY NHAT co ghi nhan abstention: Appendix E "model refuses to write SQL when the table
     does not contain the necessary information" (dinh tinh)
   Han che: Table 24 "fails to identify the intrinsic hierarchical structure"

## KHOANG TRONG LON NHAT = CO HOI CUA LUAN VAN
KHONG MOT method nao trong ho program-aided danh gia cau hoi UNANSWERABLE.
WikiTQ/TabFact/FeTaQA/HiTab/FinQA/TAT-QA/IM-TQA/TableBench deu KHONG co lop unanswerable.
Cach moi he thong xu ly ket qua SQL RONG:
  ProTrix - tu choi viet SQL (chi case study) | TableMaster - sufficiency check nhung dung de MO RONG context
  ProgramTab - 5 lan retry that bai -> im lang bo cuoc | TabSQLify - va lai bang column-selection
  Chain-of-Query - quay ve query hop le cuoi | TableLLM - LOAI BO cac truy van Spider tra null khoi training
=> TAT CA coi ket qua rong la LOI CAN VA. Coi no la MOT LA PHIEU ABSTAIN la chua duoc cong bo.
   Day la tin hieu abstention CO CAN CU THUC THI, khong phai LLM, ma agent doc-text
   KHONG THE tao ra ve mat cau truc -> dung nghia "bang chung doc lap".

## CHI PHI (~$0.002 / cau-call, moc $2 = 1 call/cau x 992)
TableLLM 1 call ~$2 (+finetune) | ProTrix/TabSQLify 2 ~$4 | toi thieu 2 kenh ~3.2 ~$6.5
ProgramTab 4 ~$8 | Weaver 5.3-5.9 ~$11 | MATA 5.5-7 ~$11-14 | H-STAR 8-10 ~$16-20
Mix-SC 10 ~$20 | Chain-of-Query 7.63 ~$15 | Chain-of-Table <=25 <=$50
Binder 50-60 ~$100-120 | Dater 100 ~$200  <- Binder/Dater VUOT ngan sach 50-100x

## CANH BAO METRIC
Weaver dung REM (Relaxed Exact Match): LLM chuan hoa prediction ve dinh dang gold ROI moi exact-match.
Vi du: gold "17 years", pred "17" -> tu dong them don vi -> tinh la DUNG.
=> DUNG chinh hieu ung answer-normalization da cho POMA ~90% cai thien. So cua Weaver
   KHONG SO SANH DUOC voi raw EM.
TableLLM WikiTQ 89.10 cham bang DeepSeek-V3 cho diem 1-10, nguong 7 -> khong phai EM.

## KHONG VERIFY DUOC (agent tu khai bao)
- Chain-of-Table ghi "LLaMA 2 (Llama-2-17B-chat)" - KHONG TON TAI model nay; Appendix C khong ghi size
- So IM-TQA cua Chain-of-Query (quan trong vi IM-TQA la proxy gan nhat cho merged cell)
- Binder/Dater khong doc truc tiep (so lieu doi chieu tu 5 paper khac, deu khop)
- KHONG CO danh gia tieng Viet/da ngu o BAT KY bai nao trong ho nay.
  Weaver va H-STAR ghi ro English-only trong Limitations.
