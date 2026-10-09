from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import ASTRA_API_TOKEN
from app.utils.logger import setup_logger

logger = setup_logger("Auth")

# auto_error=False: token 为空（本地开发）时放行，由依赖内部判断
_bearer = HTTPBearer(auto_error=False)


def verify_api_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
):
    """共享令牌鉴权: ASTRA_API_TOKEN 非空时校验 Bearer token, 为空则放行"""
    if not ASTRA_API_TOKEN:
        return
    if not credentials or credentials.credentials != ASTRA_API_TOKEN:
        raise HTTPException(status_code=401, detail="invalid or missing token")


def warn_if_auth_disabled():
    if not ASTRA_API_TOKEN:
        logger.warning("ASTRA_API_TOKEN 未设置，写端点当前无鉴权（仅本地开发可用）")
