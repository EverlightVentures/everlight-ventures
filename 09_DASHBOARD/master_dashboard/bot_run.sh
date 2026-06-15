#!/usr/bin/env bash
set -euo pipefail

# Start Crypto Bot Streamlit dashboard on 8501
export STREAMLIT_SERVER_PORT=8501
python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot/dashboard.py &

# Start XLM Bot Streamlit dashboard on 8502
export STREAMLIT_SERVER_PORT=8502
python3 /mnt/sdcard/AA_MY_DRIVE/xlm_bot/dashboard.py &

echo "Dashboards started: Crypto Bot (8501), XLM Bot (8502)"
