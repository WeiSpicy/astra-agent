from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.config import CORS_ALLOW_ORIGIN, ENABLE_UPLOAD
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chat, rag, tool, memory
from app.utils.logger import setup_logger
from app.rag import init_vectorstore
from app.auth import warn_if_auth_disabled

logger = setup_logger("APP")

# 初始化
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"准备初始化本地 RAG 向量库...")
    init_vectorstore()
    warn_if_auth_disabled()
    if not ENABLE_UPLOAD:
        logger.info("upload endpoint disabled")

    yield
    # 关闭逻辑
    logger.info(f"释放相关资源...")
    
app = FastAPI(
    title="Wei Spicy",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
    # 通配 * 与 credentials 同时开启不符合规范且不安全, 仅在明确指定来源时允许携带凭据
    allow_credentials=CORS_ALLOW_ORIGIN != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"msg": "O_o 主页是什么也没有的"}

@app.get("/health")
async def healthcheck():
    return {"status": True}

app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(rag.router, prefix="/api/v1/rag", tags=["rag"])
app.include_router(tool.router, prefix="/api/v1/tool", tags=["tool"])
if ENABLE_UPLOAD:
    from app.routers import upload
    app.include_router(upload.router, prefix="/api/v1/upload", tags=["upload"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["memory"])