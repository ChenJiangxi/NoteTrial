"""
NoteTrial API - JWT 认证模块
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
from ..config import get_settings

router = APIRouter(prefix="/auth", tags=["认证"])

security = HTTPBearer()
settings = get_settings()


class TokenPayload(BaseModel):
    """Token 载荷"""
    user_id: str
    username: str
    exp: datetime


class UserLoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class UserRegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str
    email: Optional[str] = None


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """用户响应"""
    user_id: str
    username: str
    email: Optional[str]
    created_at: datetime


# 模拟用户存储
users_db: Dict[str, Dict[str, Any]] = {}


def create_access_token(user_id: str, username: str, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT Token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def decode_token(token: str) -> Optional[TokenPayload]:
    """解码 Token"""
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """获取当前用户（依赖注入）"""
    token = credentials.credentials
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": payload.user_id,
        "username": payload.username
    }


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest) -> TokenResponse:
    """用户登录"""
    # 模拟验证（实际应查询数据库）
    if request.username == "admin" and request.password == "admin":
        user_id = "user_admin"
        username = "admin"
    elif request.username in users_db:
        stored = users_db[request.username]
        if stored["password"] == request.password:
            user_id = stored["user_id"]
            username = request.username
        else:
            raise HTTPException(status_code=401, detail="密码错误")
    else:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    token = create_access_token(user_id, username)
    
    return TokenResponse(
        access_token=token,
        expires_in=86400  # 24小时
    )


@router.post("/register", response_model=UserResponse)
async def register(request: UserRegisterRequest) -> UserResponse:
    """用户注册"""
    if request.username in users_db:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    user_id = f"user_{len(users_db) + 1}"
    
    users_db[request.username] = {
        "user_id": user_id,
        "username": request.username,
        "password": request.password,
        "email": request.email,
        "created_at": datetime.utcnow()
    }
    
    return UserResponse(
        user_id=user_id,
        username=request.username,
        email=request.email,
        created_at=datetime.utcnow()
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    """获取当前用户信息"""
    username = current_user["username"]
    
    if username in users_db:
        user = users_db[username]
        return UserResponse(
            user_id=user["user_id"],
            username=user["username"],
            email=user.get("email"),
            created_at=user["created_at"]
        )
    
    # 模拟用户
    return UserResponse(
        user_id=current_user["user_id"],
        username=current_user["username"],
        email=None,
        created_at=datetime.utcnow()
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: dict = Depends(get_current_user)) -> TokenResponse:
    """刷新 Token"""
    token = create_access_token(
        current_user["user_id"],
        current_user["username"]
    )
    
    return TokenResponse(
        access_token=token,
        expires_in=86400
    )


@router.post("/logout")
async def logout():
    """退出登录（客户端清除 Token 即可）"""
    return {"message": "已退出登录"}
