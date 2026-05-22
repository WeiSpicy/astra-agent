# Architecture

AstraAgent 采用模块化 Agent Workflow 设计，
用于组织 Tool Calling、RAG Retrieval 与 LLM Response。

Planner 会根据用户输入动态生成执行步骤，
Workflow Executor 再按步骤顺序流式执行。

```text
User Input
    ↓
Intent Recognition
    ↓
Planner
(Generate Dynamic Workflow Steps)
    ↓
Workflow Executor
    ├── Tool Execution
    │     └── Tool Intent Parsing
    │
    ├── RAG Retrieval
    │
    └── LLM Response
    ↓
Streaming Response (SSE)
```