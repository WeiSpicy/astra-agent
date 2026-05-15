from fastapi import FastAPI
from app.routers import chat

app = FastAPI(
    title="Wei Spicy",
    docs_url="/docs",
    redoc_url=None,
)


@app.get("/")
def home():
    return {"msg": "RAG PDF Bot"}


app.include_router(chat.router, prefix="/chat", tags=["chat"])
