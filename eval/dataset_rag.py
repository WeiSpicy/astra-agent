"""
RAG 检索 hit@k eval 数据集。

前提：gold_sources 基于当前 CHUNK_SIZE=400 / CHUNK_OVERLAP=100 的切分结果。
重建索引若改这两个参数，chunk_id 会重排，gold_sources 的 "#chunk-N" 可能失效
——那时报的 fail 是"标签过期"不是"检索退步"，需重新核对 gold_sources。

每条:
  - id:            短稳定标识（一旦定下不要改，用于 case 级回归追踪）
  - query:         检索输入
  - gold_sources:  期望的 source 主键列表 "{filename}#chunk-{idx}"

expected_hit1 基线独立存储在 eval/baseline_rag.json，与 case 定义分离。
用 `python eval/run_rag_eval.py --update-baseline` 更新基线。

语料（4 源文档，9 chunks）：
  - fastapi_intro.md       (3 chunks)
  - gil_deep_dive.md       (1 chunk)
  - jokers.md              (2 chunks)
  - python_concurrency_overview.md (3 chunks)
"""

CASES: list[dict] = [
    # ═══════════════════════════════════════════════════════════
    # 类别 1: 清晰单命中（每文档 2 条）
    # ═══════════════════════════════════════════════════════════

    # ── fastapi_intro.md ──
    {
        "id": "fastapi-intro",
        "query": "FastAPI 是什么框架",
        "gold_sources": ["fastapi_intro.md#chunk-0"],
    },
    {
        "id": "fastapi-di",
        "query": "FastAPI 依赖注入怎么实现",
        "gold_sources": ["fastapi_intro.md#chunk-1"],
    },

    # ── gil_deep_dive.md ──
    {
        "id": "gil-cpu",
        "query": "GIL 对 CPU 密集任务有什么影响",
        "gold_sources": ["gil_deep_dive.md#chunk-0"],
    },
    {
        "id": "gil-mechanism",
        "query": "GIL 的工作原理是什么",
        "gold_sources": ["gil_deep_dive.md#chunk-0"],
    },

    # ── python_concurrency_overview.md ──
    {   # 已知难例：gold 在 top-3 (#3 位)，asyncio chunk 排第一
        # embedding 把"多线程适合什么场景"和"asyncio 适用场景"混淆
        "id": "threading-usecase",
        "query": "Python 多线程适合什么场景",
        "gold_sources": ["python_concurrency_overview.md#chunk-0"],
    },
    {
        "id": "asyncio-usage",
        "query": "Python asyncio 怎么用",
        "gold_sources": ["python_concurrency_overview.md#chunk-1"],
    },

    # ── jokers.md ──
    {
        "id": "joke-programmer",
        "query": "讲一个程序员冷笑话",
        "gold_sources": ["jokers.md#chunk-0"],
    },
    {
        "id": "joke-any",
        "query": "有没有好笑的段子",
        "gold_sources": ["jokers.md#chunk-0"],
    },

    # ═══════════════════════════════════════════════════════════
    # 类别 2: 合理多命中（2 条）
    # ═══════════════════════════════════════════════════════════

    {
        "id": "concurrency-best",
        "query": "Python 并发编程的最佳实践",
        "gold_sources": [
            "python_concurrency_overview.md#chunk-0",
            "python_concurrency_overview.md#chunk-2",
        ],
    },
    {
        "id": "gil-concurrency",
        "query": "GIL 对 Python 多线程并发的影响",
        "gold_sources": [
            "gil_deep_dive.md#chunk-0",
            "python_concurrency_overview.md#chunk-0",
        ],
    },

    # ═══════════════════════════════════════════════════════════
    # 类别 3: 对抗干扰（3 条，验证不被 jokers.md 截胡）
    #
    # jokers.md#chunk-1 有"Python 的 GIL"笑话（"我不是不想并行，
    # 我只是……怕你们线程打架"）。以下 query 问的是 GIL 原理 / 并发
    # 概念，gold 必须是知识文档，不能被同主题的段子截胡。
    # ═══════════════════════════════════════════════════════════

    {
        "id": "gil-meaning",
        "query": "Python 的 GIL 是什么意思",
        "gold_sources": ["gil_deep_dive.md#chunk-0"],
    },
    {
        "id": "gil-no-parallel",
        "query": "Python 线程为什么不能并行执行",
        "gold_sources": ["gil_deep_dive.md#chunk-0"],
    },
    {   # 已知难例：gold 不在 top-5 中
        # embedding 没有把 "3.13"+"无 GIL 模式" 映射到 GIL 文档
        "id": "gil-313-free",
        "query": "Python 3.13 的无 GIL 模式",
        "gold_sources": ["gil_deep_dive.md#chunk-0"],
    },
]
