from pathlib import Path
import time

from app.rag.loader import load_document_with_progress
from app.rag.vector_store import vector_manager
from app.upload.progress import update_progress
import asyncio

async def process_file(task_id: str, save_path: Path):
    loop = asyncio.get_event_loop()
    # 将文件处理丢入线程池子内执行
    await loop.run_in_executor(None, sync_process_file, task_id, save_path)

def sync_process_file(task_id: str, save_path: Path):
    
    update_progress(task_id,
        status="processing",
        stage="loading",
        message="正在读取文件",
        progress=0
    )
    
    def loader_cb(p: int):
        update_progress(task_id, status="processing", stage="loading", message=f"读取文件 {p}", progress=p)

    docs = load_document_with_progress(save_path, progress_callback=loader_cb)

    # Step 3：embedding
    def embedding_cb(p):
        update_progress(task_id,
            status="processing",
            stage="embedding",
            message=f"向量化 {p}%",
            progress=40 + int(p * 0.6)
        )

    vector_manager.add_documents(
        docs,
        progress_callback=embedding_cb,
        batch_size=256
    )

    update_progress(task_id,
        status="done",
        message="完成",
        progress=100
    )