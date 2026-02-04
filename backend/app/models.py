"""
NoteTrial Backend - SQLAlchemy ORM 数据模型
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Boolean, Float, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum
from database import Base


class Platform(str, enum.Enum):
    """支持的平台"""
    XIAOHONGSHU = "xiaohongshu"
    WECHAT = "wechat"
    WEBLOG = "weblog"
    OTHER = "other"


class SubscriptionStatus(str, enum.Enum):
    """订阅状态"""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ABTestStatus(str, enum.Enum):
    """A/B测试状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )

    # 关系
    contents: Mapped[list["Content"]] = relationship("Content", back_populates="user", cascade="all, delete-orphan")
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    subscriptions: Mapped[list["Subscription"]] = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    ab_tests: Mapped[list["ABTest"]] = relationship("ABTest", back_populates="user", cascade="all, delete-orphan")


class Content(Base):
    """内容模型 - 存储生成的内容版本"""
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    cover_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # 存储为 JSON 数组
    
    content_type: Mapped[str] = mapped_column(String(50), default="post")  # post, story, note, etc.
    platform: Mapped[Platform] = mapped_column(SQLEnum(Platform), default=Platform.XIAOHONGSHU)
    
    version: Mapped[str] = mapped_column(String(10), default="A")  # A/B 测试版本标识
    ab_test_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("ab_tests.id"), nullable=True, index=True)
    
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="contents")
    ab_test: Mapped[Optional["ABTest"]] = relationship("ABTest", back_populates="contents")
    materials: Mapped[list["Material"]] = relationship("Material", back_populates="content", cascade="all, delete-orphan")


class ABTest(Base):
    """A/B测试模型"""
    __tablename__ = "ab_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    platform: Mapped[Platform] = mapped_column(SQLEnum(Platform), default=Platform.XIAOHONGSHU)
    
    status: Mapped[ABTestStatus] = mapped_column(SQLEnum(ABTestStatus), default=ABTestStatus.PENDING)
    
    # 测试配置 (JSON)
    goals: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # ["maximize_like", "maximize_save"]
    audience_tags: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    max_users: Mapped[int] = mapped_column(Integer, default=20)
    
    # 测试结果 (JSON)
    results: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    winner: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # "A" or "B"
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="ab_tests")
    contents: Mapped[list["Content"]] = relationship("Content", back_populates="ab_test")
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="ab_test")


class Post(Base):
    """发布记录模型 - 记录内容发布到各平台"""
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ab_test_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("ab_tests.id"), nullable=True, index=True)
    
    platform: Mapped[Platform] = mapped_column(SQLEnum(Platform), nullable=False)
    
    # 发布内容引用
    content_id: Mapped[int] = mapped_column(Integer, ForeignKey("contents.id"), nullable=False, index=True)
    
    # 平台返回的 ID
    external_post_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # 发布状态
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, scheduled, published, failed
    
    # 发布时间
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 统计数据 (从平台获取)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    save_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # 原始响应 (JSON)
    platform_response: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="posts")
    ab_test: Mapped[Optional["ABTest"]] = relationship("ABTest", back_populates="posts")
    content: Mapped["Content"] = relationship("Content")


class Material(Base):
    """素材模型 - 存储图片、视频等素材"""
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(Integer, ForeignKey("contents.id"), nullable=False, index=True)
    
    # 素材信息
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # image, video, etc.
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    
    # 素材类型
    material_type: Mapped[str] = mapped_column(String(50), default="cover")  # cover, image, video, voice
    
    # 是否已上传到平台
    uploaded: Mapped[bool] = mapped_column(Boolean, default=False)
    external_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # 元数据 (JSON)
    metadata: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )

    # 关系
    content: Mapped["Content"] = relationship("Content", back_populates="materials")


class Subscription(Base):
    """订阅模型 - 用户订阅/会员状态"""
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 订阅计划
    plan_type: Mapped[str] = mapped_column(String(50), default="free")  # free, basic, pro, enterprise
    
    # 订阅状态
    status: Mapped[SubscriptionStatus] = mapped_column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    
    # 订阅期限
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 支付信息 (JSON)
    payment_info: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    
    # 使用限制
    monthly_ab_tests: Mapped[int] = mapped_column(Integer, default=5)
    used_ab_tests: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="subscriptions")
