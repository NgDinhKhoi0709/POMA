#!/usr/bin/env bash
# v8 trên A100: dev đầy đủ (chọn luật) rồi test đầy đủ (cùng suite, luật chọn trên dev). Cần VLLM_BASE_URL, VLLM_API_KEY.
cd /d/.UIT/KLTN/github/POMA
. outputs/mas_tqa/.vllm_env
q() { QAS=$1 W=$2 bash outputs/mas_tqa/queue.sh "${@:3}"; }
q dataset/qas_dev.json ${WDEV:-40} suite_v8:v8dev
echo V8_DEV_DONE >> outputs/mas_tqa/logs/v8.log
