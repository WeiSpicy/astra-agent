import os
import time
import jwt
import requests
from app.config import (
    HF_API_HOST,
    HF_PROJECT_ID,
    HF_PROJECT_KID,
    HF_PRIVATE_KEY_PATH,
    HF_PUBLIC_KEY_PATH,
    HF_GEO_API_PATH,
    HF_NOW_WEATHER_PATH,
)
from app.utils import setup_logger

logger = setup_logger("weather tool")

# 一个完整的API请求URL由scheme，host，path，path parameters和query parameters组成：
BASE_URL = f"https://{HF_API_HOST}"
# GEO 城市缓存
CITY_CACHE = {}
# 令牌缓存
JWT_CACHE = {
    "token": None,
    "expire_at": 0
}

def _load_private_key():
    if not os.path.exists(HF_PRIVATE_KEY_PATH):
        return None
    with open(HF_PRIVATE_KEY_PATH, "rb") as f:
        return f.read()


def _generate_jwt():
    "生成JWT访问令牌"
    
    private_key = _load_private_key()
    if not private_key:
        return None

    headers = {
        "kid": HF_PROJECT_KID,
    }
    
    payload = {
        "sub": HF_PROJECT_ID,
        "iat": int(time.time()) - 30,
        "exp": int(time.time()) + 900,
    }

    try:
        return jwt.encode(payload, private_key, algorithm="EdDSA", headers=headers)
    except Exception:
        return None
    
def _get_jwt():
    """获取JWT访问令牌"""
    
    now = int(time.time())
    
    # 如果缓存有效，直接返回
    if JWT_CACHE["token"] and now < JWT_CACHE["expire_at"]:
        return JWT_CACHE["token"]
    
    # 否则重新生成
    token = _generate_jwt()
    if not token:
        return None
    
    # 缓存 15 分钟
    JWT_CACHE["token"] = token
    JWT_CACHE["expire_at"] = now + 900
    
    return token

def _get_city_id(city: str, jwt_token: str):
    """通过和风天气 GEOAPI 查询城市的 LocationID"""
    
    # 先查缓存
    if city in CITY_CACHE:
        return CITY_CACHE[city]
    
    req_url = f"{BASE_URL}{HF_GEO_API_PATH}?location={city}"
    
    try:
        resp = requests.get(
            req_url,
            timeout=5,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        data = resp.json()
    except Exception:
        return None

    logger.debug(f"GEO RES: {data}")
    if "location" not in data:
        return None

    city_id = data["location"][0]["id"]
    # 写入缓存
    CITY_CACHE[city] = city_id
    
    return data["location"][0]["id"]

def weather(city: str):
    """使用和风天气 + JWT 查询实时天气"""

    token = _get_jwt()
    if not token:
        return {"error": "无法生成 JWT, 请检查私钥或 KID"}
     
    logger.debug(f"生成的JWT token 为: {token}")
    
    # 1. 查询城市 ID
    city_id = _get_city_id(city, token)
    if not city_id:
        return {"error": f"无法找到城市: {city}"}

    # 2. 查询实时天气
    url = f"{BASE_URL}{HF_NOW_WEATHER_PATH}?location={city_id}"

    try:
        resp = requests.get(
            url,
            timeout=5,
            headers={"Authorization": f"Bearer {token}"}
        )
        data = resp.json()
    except Exception:
        return {"error": "天气查询失败"}

    if "now" not in data:
        return {"error": "天气查询失败"}

    now = data["now"]

    return {
        "city": city,
        "temp": now.get("temp"),
        "text": now.get("text"),
        "wind": now.get("windDir"),
        "humidity": now.get("humidity"),
    }
