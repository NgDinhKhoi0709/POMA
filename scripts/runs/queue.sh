#!/usr/bin/env bash
# Chạy tuần tự các job "method:run" trên subset dev 200.
cd /d/.UIT/KLTN/github/POMA
export PYTHONIOENCODING=utf-8
PY=/d/.virtual_env/anaconda/envs/kltn/python.exe
for job in "$@"; do
  m=${job%%:*}; r=${job##*:}
  $PY scripts/run_mas_tqa.py --qas "${QAS:-outputs/mas_tqa/qas_dev_200.json}" --method "$m" --run "$r" --workers ${W:-7} >> "outputs/mas_tqa/logs/$(basename ${QAS:-dev_200} .json).$m.run$r.log" 2>&1
done
