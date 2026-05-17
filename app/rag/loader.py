import os
from pathlib import Path
from typing import List, Dict

import pdfplumber  # PDF 解析
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.rag.config import CHUNK_SIZE, CHUNK_OVERLAP
from app.utils import setup_logger

# 职责: 文档加载 -> chunk切分 -> 生成 metadata
logger = setup_logger("Rag loader")

def load_txt_or_md(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_pdf(path: Path) -> str:
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def load_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in [".txt", ".md"]:
        return load_txt_or_md(path)
    if suffix == ".pdf":
        return load_pdf(path)
    return ""


def load_docs_from_dir(dir_path="docs") -> List[Dict]:
    base = Path(dir_path)
    docs = []

    if not base.exists():
        logger.warning(f"文档目录不存在: {dir_path}")
        return []
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )

    for path in base.glob("**/*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in [".txt", ".md", ".pdf"]:
            continue

        text = load_file(path)
        if not text.strip():
            continue

        chunks = splitter.split_text(text)

        for idx, chunk in enumerate(chunks):
            docs.append(
                {
                    "content": chunk,
                    "source": f"{path.name}#chunk-{idx}",
                    "path": str(path),
                    "chunk_id": idx,
                }
            )

    return docs

def load_document(path: Path) -> List[Dict]:
    """
    加载单个文件并切分成 chunks, 返回 docs 列表
    """
    text = load_file(path)
    if not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    chunks = splitter.split_text(text)

    docs = []
    for idx, chunk in enumerate(chunks):
        docs.append(
            {
                "content": chunk,
                "source": f"{path.name}#chunk-{idx}",
                "path": str(path),
                "chunk_id": idx,
            }
        )

    return docs