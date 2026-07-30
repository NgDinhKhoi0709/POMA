# Runbook chạy thực nghiệm chỉnh sửa Q2

Tài liệu này là thứ tự chạy khuyến nghị sau khi hoàn tất implementation cho:

- so sánh công bằng giữa raw, AN-common, AN-native và GSA/AN-single;
- hai backbone Qwen3 8B và Gemma 3 4B;
- đánh giá single-answer và thống kê số lượng đáp án \(K\);
- hint-predictor accuracy, parallelism, bootstrap confidence interval, chi phí,
  latency và structured-output reliability.

Các lệnh bên dưới được viết cho **Anaconda Prompt (`cmd.exe`)** và phải chạy từ
thư mục gốc của repository. Mỗi command được giữ trên một dòng để có thể
copy-paste trực tiếp. Không dùng dấu backtick `` ` `` để xuống dòng: ký tự đó
chỉ hoạt động khi đang ở bên trong PowerShell.

## 1. Ma trận cần chạy

| Backbone | Generator | Raw | + AN-common | + AN-native | + GSA (AN-single) |
|---|---|---:|---:|---:|---:|
| Qwen3 8B | Zero-shot | Có | Có | Không | Có |
| Qwen3 8B | Chain-of-thought | Có | Có | Không | Có |
| Qwen3 8B | Task decomposition | Có | Có | Không | Có |
| Qwen3 8B | Few-shot | Có | Có | Không | Có |
| Qwen3 8B | POMA specialists | Chẩn đoán | Có | Có | Có |
| Gemma 3 4B | Zero-shot | Có | Có | Không | Có |
| Gemma 3 4B | Chain-of-thought | Có | Có | Không | Có |
| Gemma 3 4B | Task decomposition | Có | Có | Không | Có |
| Gemma 3 4B | Few-shot | Có | Có | Không | Có |
| Gemma 3 4B | POMA specialists | Chẩn đoán | Có | Có | Có |

Chính sách đánh giá phải giữ cố định như sau:

| Loại output | `--candidate-policy` | Ý nghĩa |
|---|---|---|
| Direct baseline raw | `single-required` | Bắt buộc đúng một đáp án |
| GSA/AN-single | `single-required` | Bắt buộc đúng một đáp án |
| AN-common và AN-native | `all` | Đánh giá danh sách ứng viên, đồng thời báo cáo \(K\) |
| POMA raw | `first` | Chỉ dùng làm chẩn đoán, không dùng làm so sánh công bằng chính |

Script điều phối đã mã hóa ma trận và các policy này. Không đổi policy giữa hai
backbone.

## 2. Chuẩn bị môi trường

```bat
conda activate kltn
python -m pip install openai requests beautifulsoup4 python-dotenv pytest jsonschema
```

Kiểm tra API key mà không in giá trị key:

```bat
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('OPENROUTER configured:', bool(os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENROUTER_API_KEYS') or os.getenv('OPENROUTER_API_KEY_1')))"
```

Kết quả phải là `OPENROUTER configured: True`.

Các model ID được script sử dụng:

```text
openrouter/qwen/qwen3-8b
openrouter/google/gemma-3-4b-it
```

Không cần truyền `--structured-output-mode`: implementation tự chọn chế độ đã
duyệt cho từng model. Không ghi API key vào command, log hoặc repository.

## 3. Chạy kiểm thử trước thực nghiệm

Chạy toàn bộ test:

```bat
python -m pytest
```

Có thể chạy riêng các test quan trọng cho Q2:

```bat
python -m pytest tests/scripts/test_q2_runbook.py tests/finalization tests/services tests/evaluation -q
```

Mốc đã xác minh ngày 2026-07-30: `222 passed`.

## 4. Dry-run ma trận

Lệnh này không gọi mạng và không tạo thư mục output:

```bat
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_q2_experiments.ps1 -Phase DryRun -OutputRoot outputs\q2_revision
```

Kết quả đúng phải in `66` lệnh:

- 8 lần chạy direct baseline;
- 2 lần chạy POMA;
- 22 lần chạy finalizer;
- 32 lần đánh giá;
- 2 lần chạy revision analysis.

Muốn lưu ma trận để kiểm tra:

```bat
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_q2_experiments.ps1 -Phase DryRun -OutputRoot outputs\q2_revision > outputs\q2_revision-dry-run.txt 2>&1
```

## 5. Chạy preflight 5 câu

Đây là lần đầu có call LLM và có phát sinh chi phí. Preflight dùng một subset cố
định theo seed `20260729`, chạy toàn bộ ma trận nhưng chỉ trên 5 câu:

```bat
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_q2_experiments.ps1 -Phase Preflight -PreflightLimit 5 -OutputRoot outputs\q2_revision
```

Chỉ chuyển sang full run khi thỏa tất cả điều kiện:

- process kết thúc với exit code `0`;
- cả hai backbone đều có đủ 5 QA;
- mọi finalizer báo `coverage: 5/5` và `failures: 0`;
- structured output hợp lệ sau tối đa một repair;
- không có `missing_predictions`, `extra_predictions` hoặc
  `candidate_policy_failures` trong report cần công bố;
- `revision_analysis.json` đọc được và có hint metrics, parallelism, bootstrap,
  cost/latency và structured-output summary.

Liệt kê toàn bộ report preflight:

```bat
dir /s /b outputs\q2_revision\*\preflight\reports\*.json
```

Đọc hai report tổng hợp:

```bat
python -c "import glob,json; files=glob.glob(r'outputs/q2_revision/*/preflight/reports/revision_analysis.json'); [print('\n===',p,'===\n',json.dumps({k:d.get(k) for k in ('configuration','hint_metrics','parallelism','interpretation_gate')},ensure_ascii=False,indent=2)) for p in files for d in [json.load(open(p,encoding='utf-8'))]]"
```

Preflight nằm trong nhánh `preflight`; không tái sử dụng các file này làm kết
quả full.

## 6. Chạy full test split 992 câu theo từng lượt

Full run gọi LLM nhiều lần và có thể kéo dài nhiều giờ. Cách an toàn nhất là
chạy riêng từng generator, finalizer và evaluation. Chỉ chuyển sang lệnh tiếp
theo khi lệnh hiện tại kết thúc với exit code `0`.

Trong Anaconda Prompt, kiểm tra exit code ngay sau mỗi lệnh `python` hoặc
`powershell` bằng:

```bat
echo %ERRORLEVEL%
```

Kết quả phải là `0`. Không dùng giá trị này để kết luận các lệnh `set` thành
công hay thất bại: `set` không reset `%ERRORLEVEL%`, nên nó có thể giữ lại mã
lỗi cũ. Muốn xóa mã lỗi cũ trước khi bắt đầu một khối mới:

```bat
cmd /c exit 0
echo %ERRORLEVEL%
```

Dòng thứ hai phải in `0`. Nếu các lệnh được đặt trong file `.bat`, có thể thêm
dòng sau ngay sau mỗi command `python` hoặc `powershell` để dừng sớm khi có lỗi:

```bat
if errorlevel 1 exit /b 1
```

Không chạy song song hai command ghi vào cùng một `OutputRoot`. Giữ nguyên toàn
bộ file JSONL đã sinh khi dừng giữa chừng vì baseline và POMA có thể tiếp tục từ
các QA đã hoàn tất.

### 6.1. Khởi tạo biến dùng chung

Chạy một lần:

```bat
if not exist outputs\q2_revision mkdir outputs\q2_revision
set "OUT=outputs\q2_revision"
set "QAS=dataset\qas_test.json"
set "TABLES=dataset\table.json"
set "LIMIT=992"
```

### 6.2. Qwen — chuẩn bị đường dẫn

```bat
set "MODEL=openrouter/qwen/qwen3-8b"
set "SLUG=openrouter_qwen_qwen3-8b"
set "PHASE_ROOT=%OUT%\%SLUG%\full"
set "RAW_ROOT=%PHASE_ROOT%\raw"
set "FINAL_ROOT=%PHASE_ROOT%\finalized"
set "REPORT_ROOT=%PHASE_ROOT%\reports"
```

### 6.3. Qwen — chạy từng baseline riêng

Trước mỗi lượt, chọn đúng `GEN` và `STYLE`.

Zero-shot:

```bat
set "GEN=zero_shot"
set "STYLE=zero_shot"
set "RAW=%RAW_ROOT%\%GEN%\%SLUG%.jsonl"
```

Chain-of-thought:

```bat
set "GEN=cot"
set "STYLE=cot"
set "RAW=%RAW_ROOT%\%GEN%\%SLUG%.jsonl"
```

Task decomposition:

```bat
set "GEN=task_decomposition"
set "STYLE=task_decomposition"
set "RAW=%RAW_ROOT%\%GEN%\%SLUG%.jsonl"
```

Few-shot:

```bat
set "GEN=few_shot"
set "STYLE=few_shot"
set "RAW=%RAW_ROOT%\%GEN%\%SLUG%.jsonl"
```

Sau khi chọn một cấu hình ở trên, chạy lần lượt sáu command dưới đây.

#### Lượt 1: sinh raw prediction

```bat
python run_baseline.py --qas "%QAS%" --tables "%TABLES%" --models "%MODEL%" --prompt-style "%STYLE%" --limit "%LIMIT%" --output_dir "%RAW_ROOT%" --id "%GEN%" --no-eval
```

Nếu bị dừng giữa chừng, chạy lại đúng command này. Baseline sẽ bỏ qua các QA đã
có trong JSONL.

#### Lượt 2: đánh giá raw prediction

```bat
python run_eval.py --qas "%QAS%" --pred "%RAW%" --output "%REPORT_ROOT%\%GEN%_raw.json" --candidate-policy single-required --fail-on-metric-error
```

#### Lượt 3: chạy AN-common

```bat
python scripts\run_finalizer.py --source "%RAW%" --source-kind direct-baseline --finalizer an-common --qas "%QAS%" --tables "%TABLES%" --model "%MODEL%" --provider openrouter --output "%FINAL_ROOT%\%GEN%_an-common.json" --limit "%LIMIT%"
```

#### Lượt 4: đánh giá AN-common

```bat
python run_eval.py --qas "%QAS%" --pred "%FINAL_ROOT%\%GEN%_an-common.json" --output "%REPORT_ROOT%\%GEN%_an-common.json" --candidate-policy all --fail-on-metric-error
```

#### Lượt 5: chạy GSA

```bat
python scripts\run_finalizer.py --source "%RAW%" --source-kind direct-baseline --finalizer gsa --qas "%QAS%" --tables "%TABLES%" --model "%MODEL%" --provider openrouter --output "%FINAL_ROOT%\%GEN%_gsa.json" --limit "%LIMIT%"
```

#### Lượt 6: đánh giá GSA

```bat
python run_eval.py --qas "%QAS%" --pred "%FINAL_ROOT%\%GEN%_gsa.json" --output "%REPORT_ROOT%\%GEN%_gsa.json" --candidate-policy single-required --fail-on-metric-error
```

Hoàn tất đủ sáu lượt cho `zero_shot`, `cot`, `task_decomposition` và
`few_shot` trước khi chuyển sang POMA.

### 6.4. Qwen — chạy POMA riêng

Khai báo đường dẫn:

```bat
set "POMA_RAW=%RAW_ROOT%\poma.json"
set "POMA_TRACES=%RAW_ROOT%\poma_traces.json"
```

#### Lượt 1: chạy POMA

```bat
python run_poma.py --qas "%QAS%" --tables "%TABLES%" --model "%MODEL%" --limit "%LIMIT%" --output "%POMA_RAW%" --no-eval
```

Nếu bị dừng giữa chừng, chạy lại đúng command này để tiếp tục các QA chưa hoàn
tất.

#### Lượt 2: đánh giá POMA raw ở chế độ diagnostic

```bat
python run_eval.py --qas "%QAS%" --pred "%POMA_RAW%" --output "%REPORT_ROOT%\poma_diagnostic.json" --candidate-policy first --fail-on-metric-error
```

#### Lượt 3: chạy POMA AN-common

```bat
python scripts\run_finalizer.py --source "%POMA_TRACES%" --source-kind poma-specialists --finalizer an-common --qas "%QAS%" --tables "%TABLES%" --model "%MODEL%" --provider openrouter --output "%FINAL_ROOT%\poma_an-common.json" --limit "%LIMIT%"
```

#### Lượt 4: đánh giá POMA AN-common

```bat
python run_eval.py --qas "%QAS%" --pred "%FINAL_ROOT%\poma_an-common.json" --output "%REPORT_ROOT%\poma_an-common.json" --candidate-policy all --fail-on-metric-error
```

#### Lượt 5: chạy POMA AN-native

```bat
python scripts\run_finalizer.py --source "%POMA_TRACES%" --source-kind poma-specialists --finalizer an-native --qas "%QAS%" --tables "%TABLES%" --model "%MODEL%" --provider openrouter --output "%FINAL_ROOT%\poma_an-native.json" --limit "%LIMIT%"
```

#### Lượt 6: đánh giá POMA AN-native

```bat
python run_eval.py --qas "%QAS%" --pred "%FINAL_ROOT%\poma_an-native.json" --output "%REPORT_ROOT%\poma_an-native.json" --candidate-policy all --fail-on-metric-error
```

#### Lượt 7: chạy POMA GSA

```bat
python scripts\run_finalizer.py --source "%POMA_TRACES%" --source-kind poma-specialists --finalizer gsa --qas "%QAS%" --tables "%TABLES%" --model "%MODEL%" --provider openrouter --output "%FINAL_ROOT%\poma_gsa.json" --limit "%LIMIT%"
```

#### Lượt 8: đánh giá POMA GSA

```bat
python run_eval.py --qas "%QAS%" --pred "%FINAL_ROOT%\poma_gsa.json" --output "%REPORT_ROOT%\poma_gsa.json" --candidate-policy single-required --fail-on-metric-error
```

#### Lượt 9: chạy revision analysis mặc định

Chỉ chạy sau khi `few_shot_gsa.json` và `poma_an-native.json` đã hoàn tất:

```bat
python scripts\run_revision_analysis.py --system "poma-an-native=%FINAL_ROOT%\poma_an-native.json" --system "few-shot-gsa=%FINAL_ROOT%\few_shot_gsa.json" --primary-system poma-an-native --baseline-system few-shot-gsa --qas "%QAS%" --poma-traces "%POMA_TRACES%" --bootstrap-samples 10000 --seed 20260729 --output "%REPORT_ROOT%\revision_analysis.json"
```

### 6.5. Gemma — chuẩn bị đường dẫn

Khối Gemma độc lập với khối Qwen. Có thể mở một Anaconda Prompt mới, chạy lại
Mục 6.1 rồi khai báo:

```bat
set "MODEL=openrouter/google/gemma-3-4b-it"
set "SLUG=openrouter_google_gemma-3-4b-it"
set "PHASE_ROOT=%OUT%\%SLUG%\full"
set "RAW_ROOT=%PHASE_ROOT%\raw"
set "FINAL_ROOT=%PHASE_ROOT%\finalized"
set "REPORT_ROOT=%PHASE_ROOT%\reports"
set "POMA_PARALLEL_WORKERS=1"
set "POMA_LLM_RETRY_DELAY=30"
```

### 6.6. Gemma — chạy từng baseline riêng

Chọn riêng một baseline:

Zero-shot:

```bat
set "GEN=zero_shot"
set "STYLE=zero_shot"
set "RAW=%RAW_ROOT%\%GEN%\%SLUG%.jsonl"
```

Chain-of-thought:

```bat
set "GEN=cot"
set "STYLE=cot"
set "RAW=%RAW_ROOT%\%GEN%\%SLUG%.jsonl"
```

Task decomposition:

```bat
set "GEN=task_decomposition"
set "STYLE=task_decomposition"
set "RAW=%RAW_ROOT%\%GEN%\%SLUG%.jsonl"
```

Few-shot:

```bat
set "GEN=few_shot"
set "STYLE=few_shot"
set "RAW=%RAW_ROOT%\%GEN%\%SLUG%.jsonl"
```

Sau khi chọn một baseline, chạy lần lượt sáu command Gemma sau.

#### Gemma baseline — lượt 1: sinh raw prediction

```bat
python run_baseline.py --qas "%QAS%" --tables "%TABLES%" --models "%MODEL%" --prompt-style "%STYLE%" --limit "%LIMIT%" --output_dir "%RAW_ROOT%" --id "%GEN%" --max_workers 1 --no-eval
```

#### Gemma baseline — lượt 2: đánh giá raw prediction

```bat
python run_eval.py --qas "%QAS%" --pred "%RAW%" --output "%REPORT_ROOT%\%GEN%_raw.json" --candidate-policy single-required --fail-on-metric-error
```

#### Gemma baseline — lượt 3: chạy AN-common

```bat
python scripts\run_finalizer.py --source "%RAW%" --source-kind direct-baseline --finalizer an-common --qas "%QAS%" --tables "%TABLES%" --model "%MODEL%" --provider openrouter --output "%FINAL_ROOT%\%GEN%_an-common.json" --limit "%LIMIT%"
```

#### Gemma baseline — lượt 4: đánh giá AN-common

```bat
python run_eval.py --qas "%QAS%" --pred "%FINAL_ROOT%\%GEN%_an-common.json" --output "%REPORT_ROOT%\%GEN%_an-common.json" --candidate-policy all --fail-on-metric-error
```

#### Gemma baseline — lượt 5: chạy GSA

```bat
python scripts\run_finalizer.py --source "%RAW%" --source-kind direct-baseline --finalizer gsa --qas "%QAS%" --tables "%TABLES%" --model "%MODEL%" --provider openrouter --output "%FINAL_ROOT%\%GEN%_gsa.json" --limit "%LIMIT%"
```

#### Gemma baseline — lượt 6: đánh giá GSA

```bat
python run_eval.py --qas "%QAS%" --pred "%FINAL_ROOT%\%GEN%_gsa.json" --output "%REPORT_ROOT%\%GEN%_gsa.json" --candidate-policy single-required --fail-on-metric-error
```

Hoàn tất đủ sáu lượt cho từng baseline `zero_shot`, `cot`,
`task_decomposition` và `few_shot`. Không cần chạy POMA xen giữa các baseline.

### 6.7. Gemma — chạy POMA riêng

Khối này chỉ cần các biến dùng chung ở Mục 6.1 và biến Gemma ở Mục 6.5. Không
phụ thuộc vào raw output của bốn direct baseline, ngoại trừ revision analysis
cuối cùng cần `few_shot_gsa.json`.

```bat
set "POMA_RAW=%RAW_ROOT%\poma.json"
set "POMA_TRACES=%RAW_ROOT%\poma_traces.json"
```

#### Gemma POMA — lượt 1: chạy POMA

```bat
python run_poma.py --qas "%QAS%" --tables "%TABLES%" --model "%MODEL%" --limit "%LIMIT%" --output "%POMA_RAW%" --workers 1 --no-eval
```

#### Gemma POMA — lượt 2: đánh giá raw diagnostic

```bat
python run_eval.py --qas "%QAS%" --pred "%POMA_RAW%" --output "%REPORT_ROOT%\poma_diagnostic.json" --candidate-policy first --fail-on-metric-error
```

#### Gemma POMA — lượt 3: chạy AN-common

```bat
python scripts\run_finalizer.py --source "%POMA_TRACES%" --source-kind poma-specialists --finalizer an-common --qas "%QAS%" --tables "%TABLES%" --model "%MODEL%" --provider openrouter --output "%FINAL_ROOT%\poma_an-common.json" --limit "%LIMIT%"
```

#### Gemma POMA — lượt 4: đánh giá AN-common

```bat
python run_eval.py --qas "%QAS%" --pred "%FINAL_ROOT%\poma_an-common.json" --output "%REPORT_ROOT%\poma_an-common.json" --candidate-policy all --fail-on-metric-error
```

#### Gemma POMA — lượt 5: chạy AN-native

```bat
python scripts\run_finalizer.py --source "%POMA_TRACES%" --source-kind poma-specialists --finalizer an-native --qas "%QAS%" --tables "%TABLES%" --model "%MODEL%" --provider openrouter --output "%FINAL_ROOT%\poma_an-native.json" --limit "%LIMIT%"
```

#### Gemma POMA — lượt 6: đánh giá AN-native

```bat
python run_eval.py --qas "%QAS%" --pred "%FINAL_ROOT%\poma_an-native.json" --output "%REPORT_ROOT%\poma_an-native.json" --candidate-policy all --fail-on-metric-error
```

#### Gemma POMA — lượt 7: chạy GSA

```bat
python scripts\run_finalizer.py --source "%POMA_TRACES%" --source-kind poma-specialists --finalizer gsa --qas "%QAS%" --tables "%TABLES%" --model "%MODEL%" --provider openrouter --output "%FINAL_ROOT%\poma_gsa.json" --limit "%LIMIT%"
```

#### Gemma POMA — lượt 8: đánh giá GSA

```bat
python run_eval.py --qas "%QAS%" --pred "%FINAL_ROOT%\poma_gsa.json" --output "%REPORT_ROOT%\poma_gsa.json" --candidate-policy single-required --fail-on-metric-error
```

#### Gemma POMA — lượt 9: revision analysis mặc định

```bat
python scripts\run_revision_analysis.py --system "poma-an-native=%FINAL_ROOT%\poma_an-native.json" --system "few-shot-gsa=%FINAL_ROOT%\few_shot_gsa.json" --primary-system poma-an-native --baseline-system few-shot-gsa --qas "%QAS%" --poma-traces "%POMA_TRACES%" --bootstrap-samples 10000 --seed 20260729 --output "%REPORT_ROOT%\revision_analysis.json"
```

Nếu terminal Gemma sẽ được dùng lại để chạy Qwen, xóa hai override trước:

```bat
set "POMA_PARALLEL_WORKERS="
set "POMA_LLM_RETRY_DELAY="
```

Đóng terminal Gemma cũng xóa các biến này. Không thêm chúng vào `.env`, vì
`.env` sẽ làm thay đổi concurrency của cả Qwen.

### 6.8. Bốn khối chạy độc lập

1. **Qwen Baselines:** Mục 6.2 và 6.3.
2. **Qwen POMA:** Mục 6.2 và 6.4.
3. **Gemma Baselines:** Mục 6.5 và 6.6.
4. **Gemma POMA:** Mục 6.5 và 6.7.

Có thể hoàn tất từng khối ở các thời điểm khác nhau. Không chạy đồng thời
`Baselines` và `POMA` của cùng backbone nếu chúng dùng chung model quota hoặc
muốn đo latency/chi phí trong điều kiện nhất quán. Không bắt đầu command tiếp
theo nếu command hiện tại có exit code khác `0`.

### 6.9. Lệnh điều phối toàn bộ, chỉ dùng khi muốn chạy liền mạch

Script điều phối vẫn có thể chạy toàn bộ 66 command:

```bat
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_q2_experiments.ps1 -Phase Full -OutputRoot outputs\q2_revision
```

Nếu muốn lưu log:

```bat
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_q2_experiments.ps1 -Phase Full -OutputRoot outputs\q2_revision > outputs\q2_revision\full-run.log 2>&1
```

Không dùng lệnh điều phối toàn bộ nếu đã có finalizer output chưa hoàn tất. Khi
đó, resume đúng finalizer bị dừng rồi tiếp tục bằng các command riêng.

Output được tách theo cấu trúc:

```text
outputs/q2_revision/
├── openrouter_qwen_qwen3-8b/
│   └── full/
│       ├── raw/
│       ├── finalized/
│       └── reports/
└── openrouter_google_gemma-3-4b-it/
    └── full/
        ├── raw/
        ├── finalized/
        └── reports/
```

Giữ nguyên toàn bộ `raw`, trace, incremental JSONL và manifest cho đến khi paper
được chốt. Chúng cần thiết để audit, resume và tính lại report mà không gọi LLM.

## 7. Chạy thêm hai so sánh công bằng chính

Script full đã tạo `revision_analysis.json` cho
`POMA AN-native` so với `few-shot GSA`. Sau full run, chạy thêm hai phép so sánh
paired-bootstrap cùng finalizer để trả lời trực tiếp câu hỏi về lợi ích của
orchestration.

### 7.1. AN-common so với AN-common

```bat
python scripts\run_revision_analysis.py --system "poma-an-common=outputs/q2_revision/openrouter_qwen_qwen3-8b/full/finalized/poma_an-common.json" --system "few-shot-an-common=outputs/q2_revision/openrouter_qwen_qwen3-8b/full/finalized/few_shot_an-common.json" --primary-system poma-an-common --baseline-system few-shot-an-common --qas dataset\qas_test.json --poma-traces outputs\q2_revision\openrouter_qwen_qwen3-8b\full\raw\poma_traces.json --bootstrap-samples 10000 --seed 20260729 --output outputs\q2_revision\openrouter_qwen_qwen3-8b\full\reports\revision_analysis_an-common.json
if errorlevel 1 exit /b 1

python scripts\run_revision_analysis.py --system "poma-an-common=outputs/q2_revision/openrouter_google_gemma-3-4b-it/full/finalized/poma_an-common.json" --system "few-shot-an-common=outputs/q2_revision/openrouter_google_gemma-3-4b-it/full/finalized/few_shot_an-common.json" --primary-system poma-an-common --baseline-system few-shot-an-common --qas dataset\qas_test.json --poma-traces outputs\q2_revision\openrouter_google_gemma-3-4b-it\full\raw\poma_traces.json --bootstrap-samples 10000 --seed 20260729 --output outputs\q2_revision\openrouter_google_gemma-3-4b-it\full\reports\revision_analysis_an-common.json
if errorlevel 1 exit /b 1
```

### 7.2. GSA/AN-single so với GSA/AN-single

```bat
python scripts\run_revision_analysis.py --system "poma-gsa=outputs/q2_revision/openrouter_qwen_qwen3-8b/full/finalized/poma_gsa.json" --system "few-shot-gsa=outputs/q2_revision/openrouter_qwen_qwen3-8b/full/finalized/few_shot_gsa.json" --primary-system poma-gsa --baseline-system few-shot-gsa --qas dataset\qas_test.json --poma-traces outputs\q2_revision\openrouter_qwen_qwen3-8b\full\raw\poma_traces.json --bootstrap-samples 10000 --seed 20260729 --output outputs\q2_revision\openrouter_qwen_qwen3-8b\full\reports\revision_analysis_gsa.json
if errorlevel 1 exit /b 1

python scripts\run_revision_analysis.py --system "poma-gsa=outputs/q2_revision/openrouter_google_gemma-3-4b-it/full/finalized/poma_gsa.json" --system "few-shot-gsa=outputs/q2_revision/openrouter_google_gemma-3-4b-it/full/finalized/few_shot_gsa.json" --primary-system poma-gsa --baseline-system few-shot-gsa --qas dataset\qas_test.json --poma-traces outputs\q2_revision\openrouter_google_gemma-3-4b-it\full\raw\poma_traces.json --bootstrap-samples 10000 --seed 20260729 --output outputs\q2_revision\openrouter_google_gemma-3-4b-it\full\reports\revision_analysis_gsa.json
if errorlevel 1 exit /b 1
```

Ba kết quả cần diễn giải cùng nhau là:

1. `POMA AN-common` so với `few-shot AN-common`;
2. `POMA GSA` so với `few-shot GSA`;
3. `POMA AN-native` so với `few-shot GSA` như một kết quả native, không phải
   phép so sánh finalizer-matched.

Không kết luận từ point estimate một mình; luôn báo cáo paired 95% CI và xem CI
có chứa 0 hay không.

## 8. Xuất bảng kết quả để đưa vào paper

Lệnh sau gom 32 evaluation report thành một CSV và in bảng tóm tắt trong
PowerShell:

```bat
powershell -NoProfile -Command "$rows=Get-ChildItem 'outputs/q2_revision/*/full/reports/*.json' | Where-Object {$_.BaseName -notlike 'revision_analysis*'} | ForEach-Object {$r=Get-Content $_.FullName -Raw | ConvertFrom-Json; [PSCustomObject]@{Backbone=$_.Directory.Parent.Parent.Name;System=$_.BaseName;Policy=$r.candidate_policy;EM=[math]::Round(100*$r.metrics.em.value,2);F1=[math]::Round(100*$r.metrics.f1.value,2);ROUGE1=[math]::Round(100*$r.metrics.rouge1.value,2);METEOR=[math]::Round(100*$r.metrics.meteor.value,2);MeanK=[math]::Round($r.source_candidate_statistics.mean,3);P95K=$r.source_candidate_statistics.p95;KEquals1Rate=[math]::Round(100*$r.source_candidate_statistics.k_equals_one_rate,2);PolicyFailures=@($r.candidate_policy_failures).Count;Missing=@($r.coverage.missing_predictions).Count}} | Sort-Object Backbone,System; $rows | Format-Table -AutoSize; $rows | Export-Csv 'outputs/q2_revision/q2_results_table.csv' -NoTypeInformation -Encoding UTF8"
```

Các hàng chính nên đưa vào bảng paper:

- bốn baseline raw;
- bốn baseline + AN-common;
- bốn baseline + GSA;
- POMA + AN-common;
- POMA + AN-native;
- POMA + GSA.

`poma_diagnostic` nên để ở bảng ablation/diagnostic hoặc appendix, vì policy
`first` không tương đương với các hệ single-answer.

## 9. Resume khi bị gián đoạn

`run_baseline.py` và `run_poma.py` mặc định bỏ qua QA đã có. Finalizer yêu cầu
resume tường minh để bảo vệ artifact.

Nếu một finalizer bị ngắt:

1. lấy đúng command bị lỗi trên màn hình hoặc trong `full-run.log`;
2. chạy lại đúng command đó và thêm `--resume`;
3. chỉ thêm `--retry-failed` nếu muốn gọi lại những QA đã được ghi nhận là
   failure;
4. sau khi finalizer hoàn tất, chạy lại command evaluation ngay sau nó;
5. tiếp tục các command còn lại theo thứ tự được in bởi dry-run.

Ví dụ resume POMA GSA của Qwen:

```bat
python scripts\run_finalizer.py --source outputs\q2_revision\openrouter_qwen_qwen3-8b\full\raw\poma_traces.json --source-kind poma-specialists --finalizer gsa --qas dataset\qas_test.json --tables dataset\table.json --model openrouter/qwen/qwen3-8b --provider openrouter --output outputs\q2_revision\openrouter_qwen_qwen3-8b\full\finalized\poma_gsa.json --limit 992 --resume
```

Không chạy lại toàn bộ `-Phase Full` sau khi đã có một phần output finalizer:
script điều phối cố ý từ chối ghi đè finalizer đã tồn tại. Resume command bị
ngắt rồi tiếp tục các command còn lại.

## 10. Thứ tự ưu tiên khi ngân sách hoặc thời gian hạn chế

1. Test và dry-run.
2. Preflight đầy đủ hai backbone.
3. Full Qwen: direct baselines, POMA, AN-common và GSA.
4. Full Gemma với đúng ma trận đối xứng.
5. Ba revision analysis cho mỗi backbone và xuất bảng CSV.
6. Chỉ sau đó mới cân nhắc transfer sang dataset khác hoặc evidence-support
   verifier.

Hiện repository chưa có CLI chuyên biệt cho cross-dataset transfer hoặc một
evidence-support verifier độc lập. Vì vậy hai mục này không thuộc lệnh chạy bắt
buộc và không nên tuyên bố đã thực hiện chỉ từ output GSA.
