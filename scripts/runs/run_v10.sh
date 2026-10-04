#!/usr/bin/env bash
# v10 trên test đầy đủ + few-shot cùng khung prompt. Cần outputs/mas_tqa/.vllm_env.
cd /d/.UIT/KLTN/github/POMA
. outputs/mas_tqa/.vllm_env
export PYTHONIOENCODING=utf-8
PY=/d/.virtual_env/anaconda/envs/kltn/python.exe
until curl -s -o /dev/null -w '%{http_code}' -m 5 -H "Authorization: Bearer $VLLM_API_KEY" $VLLM_BASE_URL/models | grep -q 200; do sleep 15; done
echo READY >> outputs/mas_tqa/logs/v10.log
$PY scripts/run_mas_tqa.py --method fs_qwen --qas dataset/qas_test.json --run q1 --workers 8 > outputs/mas_tqa/logs/qas_test.fs_qwen.runq1.log 2>&1 &
$PY scripts/run_mas_tqa.py --method suite_v10 --qas dataset/qas_test.json --run v10test --workers 28 > outputs/mas_tqa/logs/qas_test.suite_v10.runv10test.log 2>&1
wait
echo V10_TEST_DONE >> outputs/mas_tqa/logs/v10.log
