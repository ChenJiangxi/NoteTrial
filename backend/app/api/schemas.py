"""
NoteTrial API - 数据模型和模式定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime
from enum import Enum


# ============ 通用响应模型 ============

T = TypeVar('T')


class StandardResponse(BaseModel):
    """标准 API 响应"""
    status: str = "success"
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(
        cls, 
        items: List[T], 
        total: int, 
        page: int, 
        page_size: int
    ) -> "PaginatedResponse[T]":
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )


# ============ 内容相关模型 ============

class ContentStatus(str, Enum):
    """内容状态"""
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Content(BaseModel):
    """内容模型"""
    id: str
    title: str
    body: str
    topic: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    cover_image: Optional[str] = None
    status: ContentStatus = ContentStatus.DRAFT
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class ContentCreate(BaseModel):
    """创建内容请求"""
    title: str = Field(..., max_length=100)
    body: str = Field(..., max_length=10000)
    topic: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    cover_image: Optional[str] = None


class ContentUpdate(BaseModel):
    """更新内容请求"""
    title: Optional[str] = Field(None, max_length=100)
    body: Optional[str] = Field(None, max_length=10000)
    topic: Optional[str] = None
    tags: Optional[List[str]] = None
    cover_image: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ============ A/B 测试相关模型 ============

class ABTestStatus(str, Enum):
    """测试状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ABTest(BaseModel):
    """A/B 测试模型"""
    id: str
    name: str
    description: Optional[str] = None
    content_a: Dict[str, Any]
    content_b: Dict[str, Any]
    task_spec: Dict[str, Any]
    status: ABTestStatus = ABTestStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ABTestCreate(BaseModel):
    """创建测试请求"""
    name: str
    description: Optional[str] = None
    content_a: Dict[str, Any]
    content_b: Dict[str, Any]
    task_spec: Dict[str, Any]


class ABTestUpdate(BaseModel):
    """更新测试请求"""
    name: Optional[str] = None
    description: Optional[str] = None


# ============ 发布记录相关模型 ============

class PostStatus(str, Enum):
    """发布状态"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class Post(BaseModel):
    """发布记录模型"""
    id: str
    content_id: str
    note_id: Optional[str] = None
    xsec_token: Optional[str] = None
    title: str
    body: str
    platform: str = "xiaohongshu"
    status: PostStatus = PostStatus.DRAFT
    posted_at: Optional[datetime] = None
    stats: Dict[str, int] = Field(default_factory=dict)
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class PostCreate(BaseModel):
    """创建发布记录请求"""
    content_id: str
    title: str
    body: str
    platform: str = "xiaohongshu"
    scheduled_at: Optional[datetime] = None


# ============ 素材库相关模型 ============

class MaterialImage(BaseModel):
    """图片素材模型"""
    id: str
    image_data: str  # Base64 或 URL
    filename: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    source: Optional[str] = None
    size: Optional[int] = None
    mime_type: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MaterialText(BaseModel):
    """文案素材模型"""
    id: str
    content: str
    text_type: str = "copy"  # copy/title/tag/hook
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    source: Optional[str] = None
    performance: Optional[Dict[str, Any]] = None
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============ 分析相关模型 ============

class AnalyticsMetric(str, Enum):
    """分析指标"""
    LIKES = "likes"
    COLLECTS = "collects"
    COMMENTS = "comments"
    SHARES = "shares"
    ENGAGEMENT = "engagement"


# ============ MCP 相关模型 ============

class MCPTool(BaseModel):
    """MCP 工具"""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]


class MCPPublishResult(BaseModel):
    """MCP 发布结果"""
    success: bool
    note_id: Optional[str] = None
    xsec_token: Optional[str] = None
    error: Optional[str] = None
