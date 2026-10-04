# Script chạy thực nghiệm trên GPU (MemView, mas_tqa)

Bản sao các script đã dùng để chạy trên A100 thuê ở Vast.ai (bản gốc nằm trong `outputs/mas_tqa/`, bị gitignore).
Chạy từ gốc repo bằng Git Bash; các script gọi `scripts/run_mas_tqa.py` và đọc `outputs/mas_tqa/.vllm_env`.

## Script ứng với kết quả trong research note và paper

| Script | Kết quả |
|---|---|
| `run_v11.sh`, `run_v11b.sh` | MemView v11 (`suite_v10 --run v11test`) và few-shot cùng khung (`fs_qwen --run q2`) trên test đầy đủ |
| `run_v10.sh` | MemView v10 trên test |
| `run_baselines.sh` | zero-shot, few-shot SC3, multi-agent debate, MemView không memory, CoAgt, Chain-of-Table |
| `run_cross.sh` | MemView với memory chỉ lấy từ bảng khác (`MAS_MEMORY_SCOPE=cross --run cross1`) |
| `run_v8.sh`, `run_v9.sh`, `run_v9_test.sh`, `run_full_test.sh`, `queue.sh`, `resume_a100.sh` | các phiên bản trước (v6–v9) |

Mỗi script chạy bù (resume theo `qa_id`) tới khi đủ 992 câu; câu lỗi được chạy lại ở lượt sau.

## Server vLLM

- Image `vllm/vllm-openai:latest` (vLLM 0.30.0), một A100 SXM4 80GB.
- Tham số: `--model Qwen/Qwen3-8B --dtype bfloat16 --max-model-len 32768 --gpu-memory-utilization 0.90 --port 8000
  --max-num-seqs 48 --api-key <khoá tự tạo>`.
- Các lần chạy baseline và bảng chưa thấy thêm `--reasoning-parser qwen3` để tách phần thinking khỏi `content`
  (CoAgt và Chain-of-Table dùng OpenAI SDK, cần `content` sạch). Client mas_tqa cho kết quả như nhau ở cả hai cách,
  vì `strip_think` tự bỏ phần `<think>`.

`outputs/mas_tqa/.vllm_env` (không commit) có dạng:

```bash
export VLLM_BASE_URL=http://<ip>:<port>/v1
export VLLM_API_KEY=<khoá tự tạo>
```

## Chấm điểm sau khi chạy

```bash
python scripts/score_lenient.py --ref fs_qwen.runq2 --files memview_q.runv11test fs_qwen.runq2
python scripts/score_paper_metrics.py --files memview_q.runv11test fs_qwen.runq2
python scripts/bif_all.py --ref fs_qwen.runq2 --files memview_q.runv11test fs_qwen.runq2
python scripts/extract_b_only.py
python scripts/analyze_weak_groups.py
python scripts/convert_baseline_run.py outputs/baselines/coagt/qwen3-8b-q1/results.jsonl outputs/mas_tqa/qas_test/coagt.runq1.jsonl
```
