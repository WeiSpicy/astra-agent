#!/bin/bash

# 任何进程失败都退出脚本
set -e

echo "Starting FastAPI Backend..."

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Starting Streamlit Frontend..."

streamlit run frontend/streamlit_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 &
FRONTEND_PID=$!

echo "All services started. Monitoring processes..."

wait -n $BACKEND_PID $FRONTEND_PID

kill $BACKEND_PID $FRONTEND_PID 2>/dev/null