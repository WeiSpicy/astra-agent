from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.config import CORS_ALLOW_ORIGIN
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chat
from app.utils.logger import setup_logger
from app.rag import init_vectorstore

logger = setup_logger("APP")

# 初始化
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"准备初始化本地 RAG 向量库...")
    init_vectorstore()
    
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"msg": "O_o 主页是什么也没有的"}

@app.get("/health")
async def healthcheck():
    return {"status": True}

app.include_router(chat.router, prefix="/chat", tags=["chat"])
