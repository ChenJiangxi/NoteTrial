"""
NoteTrial Backend - Pydantic Schemas for API
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

from models import Platform, ABTestStatus, SubscriptionStatus


# ============ User Schemas ============

class UserBase(BaseModel):
    """用户基础 Schema"""
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)


class UserCreate(UserBase):
    """创建用户"""
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    """更新用户"""
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    is_premium: Optional[bool] = None


class UserResponse(UserBase):
    """用户响应"""
    id: int
    is_active: bool
    is_premium: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Content Schemas ============

class ContentBase(BaseModel):
    """内容基础 Schema"""
    title: str = Field(..., max_length=100)
    body: str = Field(..., max_length=10000)
    cover_image: Optional[str] = None
    tags: Optional[List[str]] = None
    content_type: str = Field(default="post", max_length=50)
    platform: Platform = Platform.XIAOHONGSHU
    version: str = Field(default="A", max_length=10)


class ContentCreate(ContentBase):
    """创建内容"""
    user_id: int
    ab_test_id: Optional[int] = None


class ContentUpdate(BaseModel):
    """更新内容"""
    title: Optional[str] = Field(None, max_length=100)
    body: Optional[str] = Field(None, max_length=10000)
    cover_image: Optional[str] = None
    tags: Optional[List[str]] = None


class ContentResponse(ContentBase):
    """内容响应"""
    id: int
    user_id: int
    ab_test_id: Optional[int] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ ABTest Schemas ============

class ABTestBase(BaseModel):
    """A/B测试基础 Schema"""
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    platform: Platform = Platform.XIAOHONGSHU
    goals: Optional[List[str]] = None
    audience_tags: Optional[List[str]] = None
    max_users: int = Field(default=20, ge=5, le=100)


class ABTestCreate(ABTestBase):
    """创建 A/B 测试"""
    user_id: int


class ABTestUpdate(BaseModel):
    """更新 A/B 测试"""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: Optional[ABTestStatus] = None
    goals: Optional[List[str]] = None


class ABTestResponse(ABTestBase):
    """A/B 测试响应"""
    id: int
    user_id: int
    status: ABTestStatus
    results: Optional[dict] = None
    winner: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ABTestWithContents(ABTestResponse):
    """A/B 测试响应（含内容）"""
    contents: List[ContentResponse] = []


# ============ Post Schemas ============

class PostBase(BaseModel):
    """发布记录基础 Schema"""
    platform: Platform
    content_id: int
    scheduled_at: Optional[datetime] = None


class PostCreate(PostBase):
    """创建发布记录"""
    user_id: int
    ab_test_id: Optional[int] = None


class PostUpdate(BaseModel):
    """更新发布记录"""
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    external_post_id: Optional[str] = None
    published_at: Optional[datetime] = None


class PostResponse(PostBase):
    """发布记录响应"""
    id: int
    user_id: int
    ab_test_id: Optional[int] = None
    status: str
    external_post_id: Optional[str] = None
    published_at: Optional[datetime] = None
    like_count: int = 0
    save_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Material Schemas ============

class MaterialBase(BaseModel):
    """素材基础 Schema"""
    file_name: str = Field(..., max_length=255)
    file_type: str = Field(..., max_length=50)
    mime_type: str = Field(..., max_length=100)
    file_size: int
    material_type: str = Field(default="cover", max_length=50)


class MaterialCreate(MaterialBase):
    """创建素材"""
    content_id: int
    file_path: str


class MaterialUpdate(BaseModel):
    """更新素材"""
    uploaded: Optional[bool] = None
    external_url: Optional[str] = None
    metadata: Optional[dict] = None


class MaterialResponse(MaterialBase):
    """素材响应"""
    id: int
    content_id: int
    file_path: str
    uploaded: bool
    external_url: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Subscription Schemas ============

class SubscriptionBase(BaseModel):
    """订阅基础 Schema"""
    plan_type: str = Field(default="free", max_length=50)
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class SubscriptionCreate(SubscriptionBase):
    """创建订阅"""
    user_id: int


class SubscriptionUpdate(BaseModel):
    """更新订阅"""
    plan_type: Optional[str] = Field(None, max_length=50)
    status: Optional[SubscriptionStatus] = None
    expires_at: Optional[datetime] = None


class SubscriptionResponse(SubscriptionBase):
    """订阅响应"""
    id: int
    user_id: int
    status: SubscriptionStatus
    monthly_ab_tests: int
    used_ab_tests: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Combined Schemas ============

class ContentWithMaterials(ContentResponse):
    """内容响应（含素材）"""
    materials: List[MaterialResponse] = []


class UserWithContents(UserResponse):
    """用户响应（含内容）"""
    contents: List[ContentResponse] = []
