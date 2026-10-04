#!/usr/bin/env bash
# 6 baseline trên test đầy đủ, hai hàng đợi song song; mỗi hệ chạy bù (resume) tới khi đủ 992 câu.
cd /d/.UIT/KLTN/github/POMA
. outputs/mas_tqa/.vllm_env
export PYTHONIOENCODING=utf-8 OPENAI_BASE_URL=$VLLM_BASE_URL OPENAI_API_KEY=$VLLM_API_KEY
[ -n "$OPENAI_BASE_URL" ] || { echo "thiếu OPENAI_BASE_URL"; exit 1; }
PY=/d/.virtual_env/anaconda/envs/kltn/python.exe
T=outputs/mas_tqa/qas_test L=outputs/mas_tqa/logs LOG=outputs/mas_tqa/logs/baselines.log
mkdir -p $L
n() { [ -f "$1" ] && grep -c . "$1" || echo 0; }
retry() {  # retry <tên> <file đếm> <lệnh...>
  local name=$1 file=$2; shift 2
  for i in 1 2 3 4; do
    [ "$(n $file)" -ge 992 ] && break
    "$@" >> $L/base.$name.log 2>&1
  done
  echo "$(date +%T) DONE $name $(n $file)" >> $LOG
}
mas() { retry $1 $T/$4.run$2.jsonl $PY scripts/run_mas_tqa.py --method $1 --qas dataset/qas_test.json --run $2 --workers $3; }
CO=outputs/baselines/coagt/qwen3-8b-q1
coagt() {
  mv -f $CO/errors.jsonl $CO/errors.$(date +%s).jsonl 2>/dev/null  # câu lỗi phải được chạy lại
  $PY scripts/run_baseline.py coagt --model Qwen/Qwen3-8B --max-workers 24 --run-id qwen3-8b-q1 --resume --skip-eval
}
cot() { $PY baselines/chain_of_query/run_chain_of_table_open_vitabqa.py --workers 16; }

echo "$(date +%T) START" >> $LOG
( mas zs_qwen q1 16 zs_qwen; mas mad_debate q1 16 mad_debate
  retry chain_of_table $T/chain_of_table.runq1.jsonl cot ) &
( mas fs_qwen_sc3 q1 16 fs_qwen_sc3; mas suite_v10_nomem q1 28 memview_nm
  retry coagt $CO/results.jsonl coagt ) &
wait
echo "$(date +%T) ALL_DONE" >> $LOG
