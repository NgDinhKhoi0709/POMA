#!/usr/bin/env bash
cd /d/.UIT/KLTN/github/POMA
. outputs/mas_tqa/.vllm_env
export PYTHONIOENCODING=utf-8
/d/.virtual_env/anaconda/envs/kltn/python.exe scripts/run_mas_tqa.py --method suite_v9 --qas dataset/qas_test.json --run v9test --workers 24 > outputs/mas_tqa/logs/qas_test.suite_v9.runv9test.log 2>&1
echo V9_TEST_DONE >> outputs/mas_tqa/logs/v9.log
