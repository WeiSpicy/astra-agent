from dotenv import load_dotenv
import os
from pathlib import Path

# 项目根目录的 .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
# 请确保 .env里面填写了 key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# 历史对话的长度
MAX_HISTORY = int(os.getenv("MAX_HISTORY", 5))

CORS_ALLOW_ORIGIN = os.environ.get("CORS_ALLOW_ORIGIN", "*").split(";")