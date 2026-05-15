from fastapi import FastAPI
from app.routers import chat

app = FastAPI(
    title="Wei Spicy",
    docs_url="/docs",
    redoc_url=None,
)


@app.get("/")
def home():
    return {"msg": "O_o 主页是什么也没有的"}


app.include_router(chat.router, prefix="/chat", tags=["chat"])
