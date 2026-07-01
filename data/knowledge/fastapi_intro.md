# FastAPI 完整指南

## 什么是 FastAPI？

**FastAPI** 是 Python 现代 Web 框架，基于 **Starlette**（ASGI）和 **Pydantic**（数据校验），2018 年由 Sebastián Ramírez 发布。

核心卖点：
- **类型提示驱动**：用 Python type hints 同时完成参数校验、序列化、文档生成
- **原生异步**：原生支持 `async/await`，IO 密集型场景性能极高
- **自动文档**：自动生成 OpenAPI（Swagger UI + ReDoc），零配置
- **快**：性能对标 Node.js/Go，远超 Flask/Django

## 核心概念

### 1. 路由与请求方法

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items")
async def list_items():
    return {"items": []}

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    # item_id 自动转为 int，传 "abc" 则直接 422
    return {"item_id": item_id}

@app.post("/items")
async def create_item(name: str, price: float):
    return {"name": name, "price": price}

@app.put("/items/{item_id}")
@app.delete("/items/{item_id}")
@app.patch("/items/{item_id}")
```

### 2. 请求体与 Pydantic 模型

```python
from pydantic import BaseModel, Field
from typing import Optional

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(gt=0)
    tags: Optional[list[str]] = None

@app.post("/items", response_model=ItemCreate)
async def create_item(item: ItemCreate):
    # FastAPI 自动：
    # 1. 解析 JSON → ItemCreate 对象
    # 2. 校验 name 非空、price > 0
    # 3. 失败则返回 422 + 详细错误信息
    return item  # 自动序列化为 JSON
```

### 3. 查询参数与路径参数

```python
from fastapi import Query

@app.get("/search")
async def search(
    q: str = Query(..., min_length=2, description="搜索关键词"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sort: Optional[str] = None,
):
    return {"q": q, "page": page, "size": size, "sort": sort}
# GET /search?q=hello&page=1&size=20
```

### 4. 依赖注入（Dependency Injection）

```python
from fastapi import Depends

# 可复用的依赖
async def get_db():
    db = Database()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Header(...)):
    user = verify_token(token)
    if not user:
        raise HTTPException(401, "未认证")
    return user

@app.get("/me")
async def me(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    # 依赖可以嵌套、缓存、覆盖
    return current_user.to_dict()
```

### 5. 中间件（Middleware）

```python
from fastapi.middleware.cors import CORSMiddleware
import time

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 自定义中间件
@app.middleware("http")
async def add_process_time_header(request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.time() - start)
    return response
```

### 6. 异常处理

```python
from fastapi import HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.status_code},
    )

# 业务代码中抛出
@app.get("/items/{item_id}")
async def get_item(item_id: int):
    item = db.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="商品不存在")
    return item
```

### 7. 后台任务

```python
from fastapi import BackgroundTasks

def send_email(email: str, content: str):
    # 耗时操作，不阻塞响应
    smtp.send(email, content)

@app.post("/register")
async def register(email: str, background_tasks: BackgroundTasks):
    # 先返回 201，后台发邮件
    background_tasks.add_task(send_email, email, "欢迎注册")
    return {"msg": "注册成功"}
```

### 8. 流式响应

```python
from fastapi.responses import StreamingResponse
import asyncio

async def generate():
    for i in range(10):
        yield f"data: chunk {i}\n\n"
        await asyncio.sleep(0.5)

@app.get("/stream")
async def stream():
    return StreamingResponse(generate(), media_type="text/event-stream")
```

### 9. 文件上传

```python
from fastapi import UploadFile, File

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    # 保存到磁盘
    with open(f"uploads/{file.filename}", "wb") as f:
        f.write(content)
    return {"filename": file.filename, "size": len(content)}
```

### 10. Lifespan（启动/关闭钩子）

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    load_models()
    print("服务已启动")
    yield
    # 关闭时
    close_connections()
    print("服务已关闭")

app = FastAPI(lifespan=lifespan)
```

## 为什么 FastAPI 那么快？

| 层面 | 技术 |
|------|------|
| Web 层 | Starlette — 最快的 Python ASGI 框架之一 |
| 数据校验 | Pydantic v2 — Rust 实现核心，比纯 Python 快 10-30x |
| 序列化 | 编译时跳过反射，生成高效 JSON 代码 |
| 并发模型 | ASGI + Uvicorn，异步非阻塞 |

## FastAPI vs Flask vs Django

| | FastAPI | Flask | Django |
|---|---|---|---|
| 异步支持 | ✅ 原生 | ⚠️ 需插件 | ⚠️ 3.1+ 部分支持 |
| 自动文档 | ✅ Swagger + ReDoc | ❌ 需 flask-swagger | ⚠️ drf-spectacular |
| 数据校验 | ✅ 内置 Pydantic | ❌ 需自行处理 | ⚠️ DRF Serializer |
| 性能 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 生态成熟度 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 学习曲线 | 低 | 极低 | 高 |
| 适合 | API / 微服务 / AI | 小项目 / 原型 | 全栈应用 / 管理系统 |

## 项目结构推荐

```
app/
├── main.py          # 入口、lifespan、中间件
├── config.py        # 配置
├── routers/         # 路由（按模块拆分）
│   ├── chat.py
│   ├── rag.py
│   └── upload.py
├── model/           # Pydantic 模型（请求/响应）
├── services/        # 业务逻辑
├── utils/           # 工具函数
└── rag/             # RAG 子系统
```

## 常见坑

**1. 在 async 路由中调用同步阻塞代码**

```python
# ❌ 会阻塞整个事件循环
@app.get("/slow")
async def slow():
    time.sleep(5)  # 同步 sleep
    return {"done": True}

# ✅ 放到线程池
import asyncio

@app.get("/slow")
async def slow():
    await asyncio.to_thread(time.sleep, 5)
    return {"done": True}
```

**2. 把 CPU 密集计算放在主进程**

```python
# ❌ 阻塞事件循环
@app.post("/predict")
async def predict(data: Input):
    return ml_model.predict(data)  # 耗时 2s，阻塞所有请求

# ✅ 扔到进程池或独立推理服务
```

**3. 依赖循环导入**

模块之间交叉 import 容易死循环，用 `TYPE_CHECKING` 或拆分文件解决。

## 总结

FastAPI 是 Python 生态中做 API 的最佳选择：
- 类型提示一份代码同时完成**校验 + 序列化 + 文档**
- 异步原生，IO 密集场景下性能极高
- 适合 AI Agent、微服务、RAG 服务等场景
- 不适合 CPU 密集型主计算（配合 Celery/RQ/独立服务处理）
