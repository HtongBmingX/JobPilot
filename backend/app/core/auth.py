"""
JWT 鉴权核心模块

包含四个功能：
1. 密码哈希（bcrypt）——注册时加密，登录时验证
2. JWT 签发（encode）——登录成功后生成 token
3. JWT 验证（decode）——每次请求校验 token 有效性
4. get_current_user（FastAPI Depends）——从 token 中提取当前用户

设计决策：

Q: 为什么 JWT 而不是 session cookie？
A: 前后端分离架构。session 需要服务端存储会话状态（Redis/DB），
   JWT 是无状态的——token 本身包含了用户身份信息，服务端只需要验证签名。
   不需要查数据库就能知道"这个请求是谁发的"，减少了一次 IO。

Q: 为什么 access_token 只有 30 分钟？
A: 安全原则——token 泄露后的攻击窗口最小化。30 分钟足够完成一个
   分析会话。refresh_token 7 天免去频繁登录。

Q: 为什么 refresh token 也是 JWT 而不是随机字符串？
A: JWT 自带过期时间和签名验证，不需要查数据库就能判断是否有效。
   而且后续可以扩展 refresh token 中存储额外信息（如设备指纹）。

Q: get_current_user 每次请求都要查数据库？不是说 JWT 无状态吗？
A: 这是安全折中。JWT 确实可以完全无状态（直接从 token 的 sub
   字段拿 user_id 就返回），但如果用户被删除/禁用，应该立即拒绝请求。
   查数据库确认用户存在是一个轻量级的安全检查（SQLite 主键查询 ~0.1ms）。
   面试时可以明确地说：JWT 本身无状态，但加一次数据库查询获取最新的
   用户状态是安全增强，不是"破坏了无状态设计"。
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.repositories.user_repo import UserRepository
from backend.app.core.logger import logger

# ============================================================
# 配置 — 从环境变量读取，带开发期默认值
# ============================================================

# openssl rand -hex 32 生成，上线前换成自己的
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me-in-production-please")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ============================================================
# 密码哈希 — bcrypt
# ============================================================

# passlib 的 CryptContext 封装了 bcrypt 的加盐和哈希细节
# schemes=["bcrypt"]: 使用 bcrypt 算法
# deprecated="auto": 自动标记过时的哈希方案（未来升级算法时用）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """明文密码 → bcrypt 哈希（用于注册）"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否匹配哈希（用于登录）"""
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================
# JWT Token 模型和签发/验证
# ============================================================

class TokenResponse(BaseModel):
    """登录成功后返回的 token 对"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# 注意：JWT payload 中的 exp 必须是 int（Unix 时间戳），
# 不能传 datetime 对象，否则 python-jose 的行为不确定
# （不同版本可能不报错但产出无效 token）。


def create_access_token(user_id: int) -> str:
    """签发 access_token（短期，30 分钟）"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # sub 必须是字符串（python-jose 要求），存 user_id 的字符串表示
    payload = {"sub": str(user_id), "exp": int(expire.timestamp()), "type": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """签发 refresh_token（长期，7 天）"""
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": int(expire.timestamp()), "type": "refresh"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    验证 JWT 签名并解析 payload。
    验证失败时抛出 JWTError（调用方捕获后返回 401）。
    返回原始 dict — 避免 Pydantic datetime 序列化兼容问题。
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload


# ============================================================
# FastAPI Depends — 从 HTTP Header 提取当前用户
# ============================================================

# HTTPBearer 是 FastAPI 内置的安全方案——从 `Authorization: Bearer <token>`
# 头部自动提取 token。比手写 Header 解析更规范，也自动生成 OpenAPI 文档。
security = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    核心鉴权中间件 — 从 JWT token 解析出当前用户。

    使用方式：在需要登录的端点参数中声明
        @app.get("/profile")
        def profile(user = Depends(get_current_user)):
            ...

    FastAPI 的依赖注入系统会自动调用此函数：
    1. HTTPBearer 从请求头解析 token
    2. decode_token 验证签名 + 过期时间
    3. 查数据库确认用户存在
    4. 返回 User 对象注入到端点函数

    返回 401 的场景：
    - 没有 Authorization 头（HTTPBearer 自动处理）
    - token 格式错误 / 签名无效 / 已过期（JWTError）
    - token 有效但用户已被删除（数据库查无此人）
    """
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except Exception as e:
        logger.warning(f"JWT 解码失败 ({type(e).__name__})：{e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已过期，请重新登录",
        )

    logger.info(f"JWT 验证通过：user_id={payload.get('sub')}, type={payload.get('type')}")

    # 只允许 access_token，refresh_token 不能用于业务请求
    if payload.get("type") != "access":
        logger.warning(f"token 类型不匹配：期望 access，实际 {payload.get('type')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请使用 access_token 访问，refresh_token 仅用于刷新",
        )

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(int(payload["sub"]))
    if user is None:
        logger.warning(f"用户不存在：user_id={payload.get('sub')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    logger.info(f"鉴权成功：{user.username}")
    return user
