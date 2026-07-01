"""
意图路由 eval 数据集。

每条: (用户输入, 期望桶)
桶: chat / rag / tool / dynamic
"""

BASE_CASES: list[tuple[str, str]] = [
    # ── chat: 普通对话、闲聊、问候、情绪表达 ──
    ("你好", "chat"),
    ("今天心情不太好", "chat"),
    ("谢谢你的帮助", "chat"),
    ("你能做什么", "chat"),
    ("哈哈太搞笑了", "chat"),
    ("晚安", "chat"),
    ("你叫什么名字", "chat"),

    # ── rag: 知识、原理、解释、定义 ──
    ("什么是机器学习", "rag"),
    ("Python 的 GIL 是什么", "rag"),
    ("解释一下量子纠缠的原理", "rag"),
    ("TCP 和 UDP 有什么区别", "rag"),
    ("介绍一下 Docker 的工作原理", "rag"),
    ("傅里叶变换是做什么的", "rag"),
    ("RESTful API 的设计原则有哪些", "rag"),

    # ── tool: 单一明确工具调用 ──
    ("帮我算一下 123 * 456", "tool"),
    ("现在几点了", "tool"),
    ("北京今天天气怎么样", "tool"),
    ("计算 2 的 10 次方", "tool"),
    ("上海明天会下雨吗", "tool"),
    ("9876 除以 3 等于多少", "tool"),
    ("现在日期是多少", "tool"),

    # ── dynamic: 一句话包含多个不同动作 ──
    ("帮我查一下北京天气，然后算一下今天气温和华氏度的转换", "dynamic"),
    ("先解释什么是 RAG，然后帮我查一下现在的时间", "dynamic"),
    ("帮我算一下 100 * 200，然后告诉我现在几点", "dynamic"),
    ("查一下上海的天气，如果下雨就提醒我带伞", "dynamic"),
    ("告诉我现在几点，然后解释一下什么是 Docker", "dynamic"),
    ("现在几点了，今天天气怎么样", "dynamic"),
]

BOUNDARY_CASES: list[tuple[str, str]] = [
    # ── 边界混淆对：容易在两个桶之间翻车的 case ──
    #
    # rag ↔ tool：命令式外壳 + 知识内核
    ("帮我解释一下什么是熵", "rag"),
    # rag ↔ tool：含"天气"词但不是工具调用
    ("什么是天气", "rag"),
    # tool ↔ rag：含"明天"但明确是天气查询 → 仍是 tool
    ("帮我查一下明天上海的天气", "tool"),
    # chat ↔ dynamic：两句同类动作，不该判 dynamic
    ("晚安，明天再聊", "chat"),
    # chat ↔ tool：问候 + 工具，问候只是礼貌用语不是独立动作
    ("你好，现在几点了", "tool"),
    # rag ↔ dynamic：情绪 + 知识，"开心"是语境不是独立动作
    ("我今天很开心，顺便问一下 Docker 是什么", "rag"),
    # dynamic：两个 tool 类动作，容易判成单个 tool
    ("帮我算 100 * 200，再查一下北京的天气", "dynamic"),
    # dynamic ↔ rag：知识 + 工具，有"然后"明确分步
    ("解释一下什么是 API，然后帮我查现在的时间", "dynamic"),
    # dynamic：真实用户口语，问候 + 时间 + 条件 + 多城天气
    ("你好啊宝子，今天是星期几啊，如果是周三的话，帮我看看厦门和杭州的天气怎么样吧", "dynamic"),
]

CASES: list[tuple[str, str]] = BASE_CASES + BOUNDARY_CASES
