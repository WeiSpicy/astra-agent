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
│   ├── main.py                   # FastAPI 入口文件
│   ├── config.py                 # 配置管理（环境变量、API Keys等）
│   ├── routers/                  # API 路由层
│   │   ├── chat.py               # 对话主接口
│   │   ├── rag.py                # RAG 知识检索接口
│   │   ├── tool.py               # 工具调用相关接口
│   │   └── upload.py             # 文件上传接口
│   ├── agent/                    # Agent 核心逻辑
│   │   ├── core.py               # Agent 入口与协调
│   │   ├── planner.py            # 动态工作流规划器
│   │   ├── workflow_executor.py  # 工作流执行引擎
│   │   ├── intent.py             # 意图识别
│   │   ├── memory.py             # 对话记忆管理
│   │   └── tools/                # 工具模块
│   ├── llm/                      # LLM 相关封装
│   │   ├── llm_client.py         # LLM 调用客户端
│   │   ├── intent_llm.py
│   │   └── tool_llm.py
│   ├── rag/                      # RAG 知识库模块
│   │   ├── rag_pipeline.py       # RAG 主流程
│   │   ├── loader.py             # 文档加载
│   │   ├── vector_store.py       # 向量存储
│   │   └── config.py
│   ├── model/                    # Pydantic 数据模型
│   └── utils/                    # 工具函数
│       └── logger.py
├── data                          # 原始数据与示例文档
│   ├── knowledge                 # 知识库
│   │   ├── fastapi_intro.md
│   │   ├── gil_deep_dive.md
│   │   ├── jokers.md
│   │   └── python_concurrency_overview.md
├── docs/                         # 项目文档
│   └── architecture.md
├── vector_store/                 # FAISS 向量索引（持久化）
├── models/                       # 嵌入模型缓存
├── keys/                         # 密钥文件（如 JWT）
├── README.md
├── .env                          # 环境变量（API Key 等）
└── pyproject.toml
```

## 如何运行
开发中……

## 请求响应示例
开发中……