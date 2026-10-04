#!/usr/bin/env bash
# Chạy toàn bộ 992 câu test trên A100: FS + MemXam-SC (v6) song song; FS xong thì chạy MemXam-SC-KV (v7).
cd /d/.UIT/KLTN/github/POMA
TEST=dataset/qas_test.json
q() { QAS=$1 W=$2 bash outputs/mas_tqa/queue.sh "${@:3}"; }
( q $TEST 24 fs:full; q $TEST 24 suite_sckv:v7full ) &
q $TEST 24 suite_sc:v6full &
wait
echo FULL_DONE >> outputs/mas_tqa/logs/full_test.log
