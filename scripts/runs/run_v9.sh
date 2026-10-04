#!/usr/bin/env bash
# v9 (A/B kèm lý do + chấm điểm) trên dev đầy đủ, song song với chấm điểm không lý do trên trace v8 dev.
cd /d/.UIT/KLTN/github/POMA
. outputs/mas_tqa/.vllm_env
export PYTHONIOENCODING=utf-8
PY=/d/.virtual_env/anaconda/envs/kltn/python.exe
until curl -s -o /dev/null -w '%{http_code}' -m 5 -H "Authorization: Bearer $VLLM_API_KEY" $VLLM_BASE_URL/models | grep -q 200; do sleep 15; done
echo READY >> outputs/mas_tqa/logs/v9.log
MAS_SCORE_TRACE=outputs/mas_tqa/qas_dev/memxam_sckv.runv8dev.jsonl $PY scripts/run_mas_tqa.py --method llm_score --qas outputs/mas_tqa/qas_dev_multi.json --run s1 --workers 8 > outputs/mas_tqa/logs/llm_score.dev.log 2>&1 &
$PY scripts/run_mas_tqa.py --method suite_v9 --qas dataset/qas_dev.json --run v9dev --workers 40 > outputs/mas_tqa/logs/qas_dev.suite_v9.runv9dev.log 2>&1
wait
echo V9_DEV_DONE >> outputs/mas_tqa/logs/v9.log
