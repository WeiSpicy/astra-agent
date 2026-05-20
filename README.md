# Astra Agent

## 项目简介
AstraAgent 是一个基于 FastAPI + LangChain/LlamaIndex 的轻量级 AI Agent 工作流 Demo

## 为什么做这个项目
这个项目的目标是构建一个结构简洁、易于扩展的 AI Agent 示例，用于探索对话管理、检索增强生成（RAG）和工具调用等常见能力。
希望通过这个项目验证一些工程实践，包括模块化设计、清晰的 API 边界，以及在实际应用中如何组织 Agent 的工作流。

## 技术栈
- FastAPI
- OpenAI Compatible API
- LangChain（探索中）
- SQLite / FAISS
- Python 3.11

## 功能特性
- [X] 多轮对话管理
- [X] 基于 LLM 的意图识别
- [X] RAG 知识问答(FAISS + FastEmbed)
- [X] 文档上传与向量库持久化
- [X] 自定义工具链(calc / now / weather)
- [X] 动态 Agent 工作流
- [X] REST API(FastAPI)

### Weather 工具（可选）

项目支持基于和风天气 API 的 weather 工具。

由于和风天气采用 Ed25519 JWT 鉴权方式，
如需启用 weather 工具，请自行配置：

- ed25519-private.pem
- ed25519-public.pem

并在和风天气控制台绑定对应公钥。

未配置时，weather 工具会自动降级为不可用状态。

## 项目结构

```text
## 项目结构

```text
astra_agent/
├── app/                          # 核心应用代码
│   ├── main.py                   # FastAPI 应用入口
│   ├── config.py                 # 全局配置（环境变量、路径、模型配置等）
│   ├── dev.sh                    # 本地开发启动脚本
│   ├── start.sh                  # 服务启动脚本
│   │
│   ├── routers/                  # API 路由层
│   │   ├── chat.py               # 聊天 / Agent 对话接口（支持 SSE 流式）
│   │   ├── rag.py                # RAG 检索与问答接口
│   │   ├── tool.py               # 工具调用接口
│   │   ├── memory.py             # 对话历史查询接口
│   │   └── upload.py             # 文件上传与进度查询接口
│   │
│   ├── agent/                    # Agent 核心逻辑
│   │   ├── core.py               # Agent 主入口与调度
│   │   ├── planner.py            # 动态工作流规划器（Planner）
│   │   ├── workflow_executor.py  # 工作流执行器（支持流式执行）
│   │   ├── intent.py             # 用户意图识别
│   │   ├── memory.py             # 对话记忆管理（deque）
│   │   └── tools/                # 内置工具模块
│   │
│   ├── llm/                      # LLM 相关封装
│   │   ├── llm_client.py         # 普通 LLM 调用封装
│   │   ├── stream_llm.py         # DeepSeek 流式输出封装
│   │   ├── intent_llm.py         # 基于 LLM 的意图识别
│   │   └── tool_llm.py           # Tool Call 推理封装
│   │
│   ├── rag/                      # RAG 知识库模块
│   │   ├── rag_pipeline.py       # RAG 主流程（检索 + 生成）
│   │   ├── loader.py             # 文档加载与 chunk 切分
│   │   ├── vector_store.py       # FAISS 向量库封装（增量更新）
│   │   ├── config.py             # RAG 配置项
│   │   └── __init__.py
│   │
│   ├── upload/                   # 文件上传任务模块
│   │   ├── service.py            # 文件解析与向量化服务
│   │   ├── progress.py           # 上传进度管理
│   │   └── task_store.py         # 上传任务状态存储
│   │
│   ├── model/                    # Pydantic 数据模型
│   │   ├── agent.py              # Agent 数据结构
│   │   ├── chat.py               # Chat 请求/响应模型
│   │   ├── rag.py                # RAG 请求/响应模型
│   │   ├── tool.py               # Tool 请求/响应模型
│   │   ├── upload.py             # Upload 请求/响应模型
│   │   └── sse.py                # SSE Event 数据结构
│   │
│   ├── utils/                    # 通用工具模块
│   │   ├── logger.py             # 日志封装
│   │   ├── file_hash.py          # 文件 MD5 计算
│   │   └── __init__.py
│   │
│   └── common/                   # 公共模块（预留扩展）
│
├── frontend/                     # Streamlit 前端
│   └── streamlit_app.py          # 聊天 UI（流式对话）
│
├── data/                         # 原始数据与知识库文件
│   ├── knowledge/                # RAG 知识库目录
│   │   ├── fastapi_intro.md
│   │   ├── gil_deep_dive.md
│   │   ├── jokers.md
│   │   └── python_concurrency_overview.md
│   └── other/                    # 其他数据目录
│
├── docs/                         # 项目文档
│   └── architecture.md           # 系统架构设计说明
│
├── vector_store/                 # FAISS 向量索引持久化目录
│   ├── index.faiss
│   └── index.pkl
│
├── models/                       # Embedding 模型缓存目录
│   └── models--Qdrant--bge-small-zh-v1.5
│
├── keys/                         # 密钥文件
│   ├── ed25519-private.pem
│   └── ed25519-public.pem
│
├── Dockerfile                    # Docker 镜像构建文件
├── docker-compose.yaml           # Docker Compose 部署配置
├── deploy.sh                     # 部署脚本
├── start.sh                      # 项目统一启动脚本
│
├── README.md                     # 项目说明文档
├── pyproject.toml                # Python 项目依赖配置
├── uv.lock                       # uv 锁定依赖版本
└── .env                          # 环境变量配置
```

## 如何运行

### 本地开发

```bash
cp .env.example .env

uv sync

source .venv/bin/activate

# backend
uvicorn app.main:app --reload --reload-dir app

# frontend
streamlit run frontend/streamlit_app.py
```

- FastAPI Docs: `http://localhost:8000/docs`
- Streamlit UI: `http://localhost:8501`

---

### Docker 部署

```bash
docker compose up -d
```

项目已提供：

- `Dockerfile`
- `docker-compose.yaml`
- `deploy.sh`