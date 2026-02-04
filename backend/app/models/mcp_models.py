"""
MCP 数据模型定义
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


class AccountStatus(str, Enum):
    """账号状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    ERROR = "error"


class SyncStatus(str, Enum):
    """同步状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(str, Enum):
    """任务状态"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UserAccount(Base):
    """用户账号模型 - 多用户隔离"""
    __tablename__ = "mcp_user_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False, comment="所属用户ID")
    platform = Column(String(32), default="xiaohongshu", comment="平台名称")
    account_name = Column(String(128), comment="账号名称")
    cookies = Column(Text, nullable=False, comment="加密后的Cookies")
    cookie_expires_at = Column(DateTime, comment="Cookie过期时间")
    status = Column(String(16), default=AccountStatus.ACTIVE, comment="账号状态")
    last_login_at = Column(DateTime, comment="最后登录时间")
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 性能指标
    total_posts = Column(Integer, default=0, comment="总发布数")
    success_rate = Column(Integer, default=100, comment="成功率%")
    
    def __repr__(self):
        return f"<UserAccount(id={self.id}, user_id={self.user_id}, account={self.account_name})>"


class PostHistory(Base):
    """帖子历史记录模型"""
    __tablename__ = "mcp_post_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False, comment="所属用户ID")
    account_id = Column(Integer, ForeignKey("mcp_user_accounts.id"), comment="关联账号")
    
    # 帖子信息
    post_id = Column(String(128), unique=True, index=True, comment="平台帖子ID")
    title = Column(String(256), comment="标题")
    content = Column(Text, comment="正文内容")
    images = Column(JSON, comment="图片URL列表")
    tags = Column(JSON, comment="标签列表")
    
    # 发布状态
    status = Column(String(16), default="draft", comment="发布状态: draft/published/failed")
    published_at = Column(DateTime, comment="发布时间")
    
    # 热度数据
    like_count = Column(Integer, default=0, comment="点赞数")
    collect_count = Column(Integer, default=0, comment="收藏数")
    comment_count = Column(Integer, default=0, comment="评论数")
    share_count = Column(Integer, default=0, comment="分享数")
    view_count = Column(Integer, default=0, comment="浏览数")
    
    # 热度追踪
    last_tracked_at = Column(DateTime, comment="最后追踪时间")
    heat_trend = Column(String(16), comment="热度趋势: rising/stable/falling")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PostHistory(id={self.id}, post_id={self.post_id}, title={self.title[:20]}...)>"


class SyncTask(Base):
    """同步任务模型"""
    __tablename__ = "mcp_sync_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False, comment="所属用户ID")
    task_type = Column(String(32), comment="任务类型: sync_posts/track_heat/publish")
    status = Column(String(16), default=TaskStatus.QUEUED, comment="任务状态")
    
    # 任务配置
    account_ids = Column(JSON, comment="涉及账号ID列表")
    config = Column(JSON, comment="任务配置参数")
    
    # 执行信息
    celery_task_id = Column(String(128), comment="Celery任务ID")
    started_at = Column(DateTime, comment="开始时间")
    completed_at = Column(DateTime, comment="完成时间")
    error_message = Column(Text, comment="错误信息")
    retry_count = Column(Integer, default=0, comment="重试次数")
    max_retries = Column(Integer, default=3, comment="最大重试次数")
    
    # 结果
    result_summary = Column(JSON, comment="结果摘要")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SyncTask(id={self.id}, type={self.task_type}, status={self.status})>"


# Pydantic Models (API层使用)
class AccountBindRequest(BaseModel):
    """账号绑定请求"""
    user_id: str
    platform: str = "xiaohongshu"
    cookies: str
    account_name: Optional[str] = None


class AccountBindResponse(BaseModel):
    """账号绑定响应"""
    success: bool
    account_id: Optional[int] = None
    message: str
    expires_at: Optional[datetime] = None


class PostCreateRequest(BaseModel):
    """发布内容请求"""
    user_id: str
    account_id: int
    title: str
    content: str
    images: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    auto_tracking: bool = True


class PostCreateResponse(BaseModel):
    """发布内容响应"""
    success: bool
    post_id: Optional[str] = None
    message: str
    task_id: Optional[str] = None


class PostListRequest(BaseModel):
    """获取帖子列表请求"""
    user_id: str
    account_id: Optional[int] = None
    status: Optional[str] = None
    page: int = 1
    page_size: int = 20


class PostListResponse(BaseModel):
    """帖子列表响应"""
    posts: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


class HeatTrendRequest(BaseModel):
    """热度追踪请求"""
    user_id: str
    post_ids: List[str]
    include_history: bool = False


class HeatTrendResponse(BaseModel):
    """热度数据响应"""
    trends: Dict[str, Dict[str, Any]]
    updated_at: datetime


class SyncConfig(BaseModel):
    """同步配置"""
    user_id: str
    account_ids: Optional[List[int]] = None
    sync_posts: bool = True
    track_heat: bool = True
    sync_interval_minutes: int = 60
    heat_check_interval_minutes: int = 30


class SyncResult(BaseModel):
    """同步结果"""
    success: bool
    posts_synced: int = 0
    errors: List[str] = []
    duration_seconds: float = 0.0


class ErrorNotification(BaseModel):
    """异常通知"""
    user_id: str
    error_type: str
    message: str
    task_id: Optional[int] = None
    account_id: Optional[int] = None
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
