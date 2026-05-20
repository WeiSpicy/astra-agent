#!/bin/bash

# 1. 确保任何一个进程失败，整个脚本立刻退出，从而让 Docker 触发重启策略
set -e

echo "Starting FastAPI Backend..."
# 启动 FastAPI，放入后台，并记住它的进程 ID (PID)
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Starting Streamlit Frontend..."
# 启动 Streamlit，放入后台，并记住它的进程 ID (PID)
streamlit run frontend/streamlit_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 &
FRONTEND_PID=$!

echo "All services started. Monitoring processes..."

# 2. 使用 wait 监听这两个进程, 保证都存活
wait -n $BACKEND_PID $FRONTEND_PID

# 3. 同步杀死进程
kill $BACKEND_PID $FRONTEND_PID 2>/dev/null