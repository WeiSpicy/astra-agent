FROM python:3.11-slim AS builder

# 设置工作目录
WORKDIR /workspace

COPY pyproject.toml uv.lock ./

# 安装依赖
RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev

ENV PATH="/workspace/.venv/bin:$PATH"

# 后端
COPY app/ ./app
# 前端
COPY frontend/ ./frontend

COPY data/ ./data

# 服务启动脚本
COPY start.sh .

# 服务启动脚本
RUN chmod +x start.sh

# 暴露端口（FastAPI + Streamlit）
EXPOSE 8080
EXPOSE 8501

CMD ["bash", "start.sh"]