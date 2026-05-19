import hashlib
from pathlib import Path

def file_md5(path: Path) -> str:
    """
    计算文件的 MD5 哈希值，用于判断文件内容是否发生变化。
    """
    md5 = hashlib.md5()

    # 分块读取文件，避免大文件占用过多内存
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)

    return md5.hexdigest()
