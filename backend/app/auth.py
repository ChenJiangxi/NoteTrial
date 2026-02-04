"""
NoteTrial Backend - 认证模块
JWT Token 生成和验证、密码哈希、OAuth2 认证
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from enum import Enum

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from uuid import uuid4

from .config import get_settings

settings = get_settings()

# ============== 密码哈希配置 ==============
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============== OAuth2 配置 ==============
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    scheme_name="JWT"
)


class UserRole(str, Enum):
    """用户角色"""
    USER = "user"
    ADMIN = "admin"


# ============== Pydantic Models ==============

class UserCreate(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=6)
    confirm_password: str


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str


class Token(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 过期时间（秒）


class TokenData(BaseModel):
    """Token 数据"""
    user_id: str
    username: str
    role: UserRole
    exp: datetime


class UserResponse(BaseModel):
    """用户响应（标准化格式）"""
    id: str
    username: str
    email: str
    role: UserRole
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """数据库中的用户模型"""
    hashed_password: str


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """刷新 Token 响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ============== 简单的用户存储（可替换为真实数据库）==============
class UserStore:
    """简单用户存储 - 内存实现，可替换为数据库"""
    
    def __init__(self):
        self.users: dict[str, UserInDB] = {}
    
    def create_user(self, user: UserCreate) -> UserInDB:
        """创建新用户"""
        # 检查用户名是否已存在
        for existing_user in self.users.values():
            if existing_user.username == user.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="用户名已被注册"
                )
            if existing_user.email == user.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被注册"
                )
        
        # 创建用户
        now = datetime.now(timezone.utc)
        user_id = str(uuid4())
        
        hashed_password = pwd_context.hash(user.password)
        
        db_user = UserInDB(
            id=user_id,
            username=user.username,
            email=user.email,
            role=UserRole.USER,
            hashed_password=hashed_password,
            created_at=now,
            updated_at=now
        )
        
        self.users[user_id] = db_user
        return db_user
    
    def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """根据用户名获取用户"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """根据ID获取用户"""
        return self.users.get(user_id)
    
    def update_user(self, user_id: str, **kwargs) -> Optional[UserInDB]:
        """更新用户信息"""
        if user_id in self.users:
            user = self.users[user_id]
            for key, value in kwargs.items():
                if hasattr(user, key) and key not in ('id', 'username', 'email', 'hashed_password', 'role', 'created_at'):
                    setattr(user, key, value)
            user.updated_at = datetime.now(timezone.utc)
            return user
        return None


# 全局用户存储实例
user_store = UserStore()


# ============== 密码处理函数 ==============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


# ============== JWT Token 函数 ==============

def create_access_token(
    user_id: str,
    username: str,
    role: UserRole,
    expires_delta: Optional[timedelta] = None
) -> str:
    """创建 JWT Access Token"""
    if expires_delta is None:
        expires_delta = timedelta(hours=24)  # 默认24小时过期
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    to_encode = {
        "sub": user_id,
        "username": username,
        "role": role.value,
        "exp": expire,
        "type": "access"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def create_refresh_token(
    user_id: str,
    username: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """创建 JWT Refresh Token"""
    if expires_delta is None:
        expires_delta = timedelta(days=7)  # Refresh token 7天过期
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    to_encode = {
        "sub": user_id,
        "username": username,
        "exp": expire,
        "type": "refresh"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """解码并验证 JWT Token"""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role")
        exp: datetime = datetime.fromtimestamp(payload.get("exp"))
        
        if user_id is None or username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的Token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(
            user_id=user_id,
            username=username,
            role=UserRole(role),
            exp=exp
        )
    
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token验证失败: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============== 依赖注入 ==============

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    """获取当前登录用户 - OAuth2 依赖注入"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证用户身份",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token_data = decode_token(token)
        
        # 检查Token是否过期
        if datetime.now(timezone.utc) > token_data.exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token已过期",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = user_store.get_user_by_id(token_data.user_id)
        
        if user is None:
            raise credentials_exception
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    
    except JWTError:
        raise credentials_exception


async def get_current_active_user(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """获取当前活跃用户（可扩展用于检查用户状态）"""
    return current_user


async def get_current_admin(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """获取当前管理员用户"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


# ============== 认证函数 ==============

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """验证用户名和密码"""
    user = user_store.get_user_by_username(username)
    
    if user is None:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


# ============== API 响应格式化 ==============

def format_user_response(user: UserInDB) -> UserResponse:
    """格式化用户响应"""
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


def format_token_response(access_token: str, expires_in: int = 86400) -> Token:
    """格式化 Token 响应"""
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in
    )
