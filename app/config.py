from dotenv import load_dotenv
import os
from pathlib import Path

# 项目根目录的 .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
# 请确保 .env里面填写了 key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")