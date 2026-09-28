#!/bin/bash
# Mag7 observer daily pipeline
# 1) data  2) chart  3) dashboard  4) report HTML  5) push TG
set -e
cd /opt/data/mag7_observer

# load bot token (REDACTED in public export)
# 真實 token 由 gateway 注入 env var $TELEGRAM_BOT_TOKEN，
# fallback 從 /opt/data/.env 讀（不 export 出嚟）。
# 古神合併後需自行確保 env var 設定。
if [ -z "$TELEGRAM_BOT_TOKEN" ] && [ -f /opt/data/.env ]; then
    export TELEGRAM_BOT_TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' /opt/data/.env | cut -d= -f2)
fi

PY=.venv/bin/python3

$PY mag7_data.py
$PY mag7_chart.py
$PY mag7_dashboard.py
$PY mag7_report.py

# 預設 push daily kind
KIND=${1:-daily}
$PY mag7_push.py $KIND

echo "[mag7-pipeline] done at $(date -u +%FT%TZ) kind=$KIND"