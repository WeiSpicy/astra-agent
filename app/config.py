from dotenv import load_dotenv
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 项目根目录的 .env
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
# 请确保 .env里面填写了 key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# 历史对话的长度
MAX_HISTORY = int(os.getenv("MAX_HISTORY", 15))

# 知识库存放的位置
KNOWLEDGE_DIR = BASE_DIR / os.getenv("KNOWLEDGE_DIR", "data/knowledge")

CORS_ALLOW_ORIGIN = os.environ.get("CORS_ALLOW_ORIGIN", "*").split(";")

# 和凤天气
HF_API_HOST = os.getenv("HF_API_HOST", '')
HF_PROJECT_ID = os.getenv("HF_PROJECT_ID", '')
HF_PROJECT_KID = os.getenv("HF_PROJECT_KID", '')
HF_KEY_DIR = BASE_DIR / os.getenv("HF_KEY_DIR", "keys")
HF_PRIVATE_KEY_PATH = os.path.join(HF_KEY_DIR, "ed25519-private.pem")
HF_PUBLIC_KEY_PATH = os.path.join(HF_KEY_DIR, "ed25519-public.pem")
# GEO https://dev.qweather.com/docs/api/geoapi/city-lookup/
HF_GEO_API_PATH = "/geo/v2/city/lookup"
# 实时天气API https://dev.qweather.com/docs/api/weather/weather-now/
HF_NOW_WEATHER_PATH = "/v7/weather/now"