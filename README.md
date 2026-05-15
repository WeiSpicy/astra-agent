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
- [ ] 对话管理
- [ ] 意图识别
- [ ] RAG 知识问答
- [ ] 自定义工具链（计算器、RAG、天气）
- [ ] Agent 工作流
- [ ] REST API

## 项目结构

```text
astra_agent/
  ├── app/
  │     ├── main.py
  │     ├── router_chat.py
  │     ├── agent/
  │     │      ├── intent.py
  │     │      ├── tools.py
  │     │      ├── rag.py
  │     │      └── agent_core.py
  │     └── config.py
  ├── docs/
  │     └── architecture.md
  ├── data/
  │     └── sample_docs/
  └── README.md
```

## 如何运行
开发中……

## 请求响应示例
开发中……