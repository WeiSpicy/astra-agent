from fastapi import APIRouter, UploadFile, File
from pathlib import Path
import shutil

from app.rag.loader import load_document
from app.rag.vector_store import rebuild_vectorstore
from app.config import KNOWLEDGE_DIR

router = APIRouter()

DOCS_DIR = KNOWLEDGE_DIR


@router.post("")
async def upload_file(file: UploadFile = File(...)):

    suffix = Path(file.filename).suffix.lower()

    if suffix not in [".txt", ".md", ".pdf"]:
        return {
            "success": False,
            "message": "仅支持 txt/md/pdf 文件"
        }

    save_path = Path(DOCS_DIR) / file.filename

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 解析文档 → 切 chunk → 得到 docs
    docs = load_document(save_path)

    # 重建向量库
    rebuild_vectorstore(docs)

    return {
        "success": True,
        "filename": file.filename,
    }