# Python 并发模型全景图

## 四种并发模型速览

| 方案 | 适用场景 | 是否绕过 GIL | 资源消耗 | 学习成本 |
|------|----------|:---:|:---:|:---:|
| **多线程** `threading` | IO 密集（网络、文件） | ❌ | 低 | 低 |
| **多进程** `multiprocessing` | CPU 密集（计算） | ✅ | 高 | 中 |
| **异步编程** `asyncio` | 高并发 IO | ❌ | 极低 | 高 |
| **线程/进程池** `concurrent.futures` | 批量并行任务 | 取决于线程/进程 | 中 | 低 |

---

## 一、多线程 (threading)

### 工作原理

多个线程共享同一个进程的内存空间，但 GIL 保证同一时刻只有一个线程执行 Python 字节码。

```python
import threading
import time

def worker(name, delay):
    for i in range(3):
        print(f"[{name}] 第 {i+1} 次执行")
        time.sleep(delay)  # IO 等待时释放 GIL

t1 = threading.Thread(target=worker, args=("A", 0.5))
t2 = threading.Thread(target=worker, args=("B", 0.5))
t1.start()
t2.start()
t1.join(); t2.join()
print("全部完成")
```

### 线程同步工具

```python
lock = threading.Lock()       # 互斥锁
rlock = threading.RLock()     # 可重入锁
sem = threading.Semaphore(3)  # 信号量（最多 3 个线程同时访问）
event = threading.Event()     # 事件通知
barrier = threading.Barrier(4)# 栅栏（4 个线程到齐才放行）

# 线程安全的数据结构
from queue import Queue
q = Queue(maxsize=10)  # 内置锁的线程安全队列
```

### 优缺点

- ✅ 共享内存、通信简单、库支持完善
- ✅ IO 密集场景有效（GIL 在 IO 等待时释放）
- ❌ CPU 密集场景无效（GIL 导致串行）
- ❌ 调试困难（竞态条件、死锁）

---

## 二、多进程 (multiprocessing)

### 工作原理

每个进程有独立的 Python 解释器和内存空间，GIL 不再互斥。

```python
from multiprocessing import Process, Queue, Pool
import time

def cpu_task(n):
    """每个进程独立执行，真正并行"""
    return sum(i * i for i in range(n))

# 方法 1：直接创建进程
p1 = Process(target=cpu_task, args=(10**7,))
p2 = Process(target=cpu_task, args=(10**7,))
p1.start(); p2.start()
p1.join(); p2.join()

# 方法 2：进程池（推荐）
with Pool(processes=4) as pool:
    results = pool.map(cpu_task, [10**7] * 4)
```

### 进程间通信

```python
# 1. Queue（队列）
queue = Queue()
p = Process(target=lambda: queue.put("数据"))
p.start()
data = queue.get()  # 阻塞获取

# 2. Pipe（管道）
parent_conn, child_conn = Pipe()
# 父进程写 → 子进程读

# 3. Manager（共享状态）
from multiprocessing import Manager
with Manager() as manager:
    shared_dict = manager.dict()     # 跨进程 dict
    shared_list = manager.list()     # 跨进程 list
    counter = manager.Value("i", 0)  # 跨进程 int
```

### 优缺点

- ✅ 真正并行，CPU 密集任务加速明显
- ✅ 进程隔离，一个进程崩了不影响其他
- ❌ 内存开销大（每个进程独立 Python 解释器）
- ❌ 进程间通信慢（序列化开销）
- ❌ Windows 不支持 `fork()`，调试麻烦

---

## 三、异步编程 (asyncio)

### 工作原理

单线程事件循环，用协程切换代替线程切换。没有线程创建开销、没有 GIL 竞争、没有锁。

```python
import asyncio

async def fetch(name, delay):
    print(f"[{name}] 开始请求")
    await asyncio.sleep(delay)  # 非阻塞等待
    print(f"[{name}] 请求完成")
    return f"{name}-result"

async def main():
    # 并发执行 3 个协程
    results = await asyncio.gather(
        fetch("A", 1),
        fetch("B", 0.5),
        fetch("C", 2),
    )
    print(results)  # ['A-result', 'B-result', 'C-result']

asyncio.run(main())
```

### 核心概念

```python
# Task — 把协程包装成可调度任务
task = asyncio.create_task(fetch("test", 1))

# Semaphore — 限制并发数
sem = asyncio.Semaphore(5)
async with sem:
    await fetch("limited", 1)

# Queue — 异步队列
queue = asyncio.Queue()
await queue.put(data)
item = await queue.get()

# 同步代码 → 线程池执行
result = await asyncio.to_thread(blocking_db_query, id=123)

# 超时控制
try:
    result = await asyncio.wait_for(slow_task(), timeout=5.0)
except asyncio.TimeoutError:
    print("超时")

# 事件循环
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
```

### Async vs Sync：同一个操作的两种写法

```python
import httpx  # 第三方，支持同步和异步

# 同步版
def get_all(urls):
    with httpx.Client() as client:
        return [client.get(url).text for url in urls]
# 耗时：n * 请求时间

# 异步版
async def get_all_async(urls):
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [r.text for r in responses]
# 耗时：单次请求时间（全部并发）
```

### 优缺点

- ✅ 极低资源消耗（单线程处理数万连接）
- ✅ 没有锁竞争、没有线程切换开销
- ❌ 周边生态必须支持 async（数据库驱动、HTTP 客户端等）
- ❌ "传染性"——异步函数只能在异步函数中被 await
- ❌ CPU 密集任务会阻塞事件循环

---

## 四、concurrent.futures（高级封装）

统一接口，线程和进程通用。

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

urls = ["https://httpbin.org/delay/1"] * 20

# IO 密集 → 线程池
with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(download, urls))

# CPU 密集 → 进程池
with ProcessPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(compute, data))

# 异步提交
futures = [executor.submit(task, arg) for arg in args]
for f in concurrent.futures.as_completed(futures):
    result = f.result()
```

---

## 五、真实场景选型

### 场景 1：Web 服务 / API

```python
# FastAPI + asyncio——Python 后端的事实标准
from fastapi import FastAPI
import asyncio

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    # 数据库查询天然是 IO
    user = await db.fetch_one("SELECT * FROM users WHERE id = $1", user_id)
    return user
```

### 场景 2：AI Agent / LLM 应用

```python
# 混合模式：asyncio 主循环 + run_in_executor 处理阻塞操作
async def agent_run(user_input: str):
    # 并行执行多个知识库检索
    results = await asyncio.gather(
        retrieve("知识库A", user_input),
        retrieve("知识库B", user_input),
    )
    # LLM 调用可能是同步 SDK → 放线程池
    answer = await asyncio.to_thread(llm_client.generate, prompt)
    return answer
```

### 场景 3：数据处理 Pipeline

```python
# 多进程——每个步骤独立进程，解耦 + 并行
# 数据流：Reader → Processor(Pool) → Writer
from multiprocessing import Pool, Queue

raw_queue = Queue()
processed_queue = Queue()

# Reader 进程读取原始数据
# Processor Pool 并行处理
# Writer 进程写入结果
```

### 场景 4：定时任务 + Web 服务

```
FastAPI 主进程（处理 API 请求）
  +
子进程 / Celery Worker（处理异步任务：发邮件、生成报表）
```

---

## 决策树

```
你的任务是什么？
│
├─ 主要是 IO（网络、文件、数据库）
│  ├─ 有 async 生态 → asyncio
│  └─ 无 async 生态 → threading / ThreadPoolExecutor
│
├─ 主要是 CPU（计算、模型推理）
│  ├─ 可拆分 → multiprocessing / ProcessPoolExecutor
│  └─ 不可拆分 → C 扩展 或 独立服务
│
└─ 混合型
   └─ asyncio + run_in_executor（桥接 CPU 密集部分）
```

---

## 常见误区

| 误区 | 真相 |
|------|------|
| "asyncio 比多线程快" | 在 CPU 密集场景下 asyncio 更慢（单线程） |
| "多线程完全没用" | IO 密集场景多线程有效，GIL 在 IO 时释放 |
| "多进程总是最好" | 内存和通信开销大，简单任务得不偿失 |
| "Python 性能差所以并发不行" | 并发 ≠ 并行，IO 密集场景 Python 异步表现优秀 |

## 核心结论

**现代 Python 开发 = 异步主循环 + 按需多进程 + 合理线程桥接**

- 主流程全部走 `async/await`
- CPU 密集部分用 `run_in_executor` 或独立进程
- 不要同时用 `asyncio` 和 `threading` 操作同一份数据
