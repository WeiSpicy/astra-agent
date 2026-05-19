import asyncio
import uuid

from fastapi import APIRouter, UploadFile, File
from pathlib import Path
import shutil

from app.config import KNOWLEDGE_DIR
from app.upload.service import process_file
from app.upload.task_store import task_progress, file_index

# SSE
from fastapi.responses import StreamingResponse
import json
import asyncio
from app.utils import setup_logger, file_md5

router = APIRouter()
logger = setup_logger("Upload")

DOCS_DIR = KNOWLEDGE_DIR


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    """上传文件完成后会返回一个知识库处理的task_id"""
    suffix = Path(file.filename).suffix.lower()

    if suffix not in [".txt", ".md", ".pdf", ".csv"]:
        return {"success": False, "message": "仅支持 txt/md/pdf 文件"}

    save_path = Path(DOCS_DIR) / file.filename

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 计算文件内容的 MD5
    new_md5 = file_md5(save_path)
    if file_index.get(file.filename) == new_md5:
        return {
            "success": True,
            "task_id": None,
            "filename": file.filename,
            "message": "文件内容未变化，跳过处理",
        }

    # 记录文件的 MD5
    file_index[file.filename] = new_md5

    task_id = str(uuid.uuid4())

    asyncio.create_task(process_file(task_id, save_path))

    return {
        "success": True,
        "task_id": task_id,
        "filename": file.filename,
        "message": f"上传完成, 准备开始处理{file.filename}",
    }


@router.get("/progress/{task_id}")
async def get_progress(task_id: str):
    """SSE 返回文件处理进度"""
    logger.debug(f"开始处理上传的文件 {task_id}")

    async def event_generator():

        while True:

            progress = task_progress.get(task_id)

            if progress:

                yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"

                if progress["status"] in ["done", "error"]:
                    break

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
