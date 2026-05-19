from typing import Dict

task_progress: Dict[str, dict] = {}
# 轻量级文件索引：记录每个文件的最新 MD5
# Demo阶段暂时不引入数据库
file_index = {}