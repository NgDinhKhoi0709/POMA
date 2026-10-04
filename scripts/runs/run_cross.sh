#!/usr/bin/env bash
# MemView với memory khác bảng (mô phỏng bảng chưa thấy) trên test đầy đủ; chạy bù tới đủ 992 câu.
cd /d/.UIT/KLTN/github/POMA
. outputs/mas_tqa/.vllm_env
export PYTHONIOENCODING=utf-8 MAS_MEMORY_SCOPE=cross
PY=/d/.virtual_env/anaconda/envs/kltn/python.exe
F=outputs/mas_tqa/qas_test/memview_q.runcross1.jsonl L=outputs/mas_tqa/logs/cross.log
for i in 1 2 3 4; do
  [ "$(grep -c . $F 2>/dev/null || echo 0)" -ge 992 ] && break
  $PY scripts/run_mas_tqa.py --method suite_v10 --qas dataset/qas_test.json --run cross1 --workers 40 >> $L 2>&1
done
echo "$(date +%T) DONE $(grep -c . $F)" >> $L
