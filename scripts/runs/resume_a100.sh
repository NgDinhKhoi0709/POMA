#!/usr/bin/env bash
# Chạy tiếp mọi job dở dang trên A100 (runner tự bỏ qua câu đã có).
cd /d/.UIT/KLTN/github/POMA
export PYTHONIOENCODING=utf-8
PY=/d/.virtual_env/anaconda/envs/kltn/python.exe
DEV=outputs/mas_tqa/qas_dev_200.json
TEST=outputs/mas_tqa/qas_test_200.json
q() { QAS=$1 W=$2 bash outputs/mas_tqa/queue.sh "${@:3}"; }

# Dev: v5 (2 câu còn lại), SC3 run 3, MemXam-SC v6.
q $DEV 2 suite3:v5r1 &
q $DEV 8 knn_sc3:3 &
q $DEV 16 suite_sc:v6r1 &
# Parse-Critic rồi cặp so sánh có/không ghi chú parse.
( $PY scripts/run_parse_critic.py --qas $DEV --workers 4 >> outputs/mas_tqa/logs/parse_critic.dev200.log 2>&1 &&
  { q $DEV 12 knn_fs_pnotes:p1 & q $DEV 12 knn_fs:p1; wait; } ) &
# Test (do session khác khởi chạy): FS, suite v4, MemXam-SC v6.
q $TEST 8 fs:t1 &
q $TEST 10 suite:v4t1 &
q $TEST 10 suite_sc:v6t1 &
wait
echo ALL_DONE >> outputs/mas_tqa/logs/resume_a100.log
