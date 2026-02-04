"""
NoteTrial API - 发布记录模块
发布记录 + MCP 追踪
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from .auth import get_current_user
from .schemas import Post, PostCreate, PaginatedResponse, StandardResponse

router = APIRouter(prefix="/posts", tags=["发布记录"])

# 模拟数据存储
posts_db: Dict[str, Post] = {}


class MCPPublishRequest(BaseModel):
    """MCP 发布请求"""
    content_id: str
    platform: str = Field(default="xiaohongshu", description="发布平台")


class MCPStatusResponse(BaseModel):
    """MCP 状态响应"""
    connected: bool
    last_check: Optional[datetime]
    available_tools: List[str]


class PublishResultRequest(BaseModel):
    """更新发布结果请求"""
    note_id: str
    xsec_token: Optional[str] = None
    success: bool
    error_message: Optional[str] = None


class SyncFromPlatformRequest(BaseModel):
    """从平台同步请求"""
    platform: str = "xiaohongshu"
    keyword: str
    limit: int = Field(default=20, ge=1, le=100)


class PostStatsRequest(BaseModel):
    """更新帖子统计请求"""
    note_id: str
    stats: Dict[str, int] = Field(..., description="点赞、收藏、评论、分享数据")


@router.get("", response_model=PaginatedResponse[Post])
async def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
) -> PaginatedResponse[Post]:
    """获取发布记录列表"""
    filtered = list(posts_db.values())
    
    if platform:
        filtered = [p for p in filtered if p.platform == platform]
    if status:
        filtered = [p for p in filtered if p.status == status]
    
    filtered.sort(key=lambda x: x.posted_at, reverse=True)
    
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/{post_id}", response_model=StandardResponse[Post])
async def get_post(
    post_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[Post]:
    """获取发布记录详情"""
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    
    return StandardResponse(data=posts_db[post_id])


@router.post("", response_model=StandardResponse[Post])
async def create_post(
    post_data: PostCreate,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[Post]:
    """创建发布记录"""
    post_id = str(uuid.uuid4())
    
    post = Post(
        id=post_id,
        **post_data.model_dump(),
        created_by=current_user.get("user_id", "anonymous")
    )
    
    posts_db[post_id] = post
    
    return StandardResponse(
        data=post,
        message="发布记录创建成功"
    )


@router.delete("/{post_id}", response_model=StandardResponse)
async def delete_post(
    post_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """删除发布记录"""
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    
    del posts_db[post_id]
    
    return StandardResponse(message="发布记录删除成功")


@router.post("/publish", response_model=StandardResponse)
async def publish_via_mcp(
    request: MCPPublishRequest,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """通过 MCP 发布内容"""
    # TODO: 集成 MCP 发布服务
    result = {
        "success": True,
        "note_id": f"note_{uuid.uuid4().hex[:12]}",
        "xsec_token": f"xsec_{uuid.uuid4().hex[:16]}",
        "platform": request.platform,
        "published_at": datetime.utcnow().isoformat()
    }
    
    return StandardResponse(
        data=result,
        message="发布成功"
    )


@router.get("/mcp/status", response_model=StandardResponse[MCPStatusResponse])
async def get_mcp_status(
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[MCPStatusResponse]:
    """获取 MCP 连接状态"""
    # TODO: 实际检查 MCP 连接
    response = MCPStatusResponse(
        connected=True,
        last_check=datetime.utcnow(),
        available_tools=[
            "publish_content",
            "check_login_status",
            "search_feeds",
            "get_feed_detail",
            "list_feeds"
        ]
    )
    
    return StandardResponse(data=response)


@router.post("/{post_id}/result", response_model=StandardResponse[Post])
async def update_publish_result(
    post_id: str,
    request: PublishResultRequest,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[Post]:
    """更新发布结果"""
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    
    post = posts_db[post_id]
    post.note_id = request.note_id
    post.xsec_token = request.xsec_token
    post.status = "published" if request.success else "failed"
    post.updated_at = datetime.utcnow()
    
    if not request.success and request.error_message:
        post.metadata = post.metadata or {}
        post.metadata["error"] = request.error_message
    
    return StandardResponse(
        data=post,
        message="发布结果已更新"
    )


@router.post("/sync", response_model=StandardResponse)
async def sync_from_platform(
    request: SyncFromPlatformRequest,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """从平台同步发布记录"""
    # TODO: 集成 MCP sync 功能
    synced_posts = [
        {
            "note_id": f"synced_{uuid.uuid4().hex[:8]}",
            "title": f"同步的笔记 - {request.keyword}",
            "platform": request.platform,
            "posted_at": datetime.utcnow().isoformat(),
            "stats": {"likes": 100, "collects": 50, "comments": 20}
        }
    ]
    
    return StandardResponse(
        data={"synced_posts": synced_posts, "count": len(synced_posts)},
        message=f"成功同步 {len(synced_posts)} 条记录"
    )


@router.post("/{post_id}/stats", response_model=StandardResponse[Post])
async def update_post_stats(
    post_id: str,
    request: PostStatsRequest,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[Post]:
    """更新帖子互动数据"""
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    
    post = posts_db[post_id]
    post.stats = request.stats
    post.updated_at = datetime.utcnow()
    
    return StandardResponse(
        data=post,
        message="统计数据已更新"
    )


@router.get("/{post_id}/stats/history", response_model=StandardResponse)
async def get_stats_history(
    post_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """获取统计数据历史"""
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="发布记录不存在")
    
    # 模拟历史数据
    history = [
        {"timestamp": "2024-01-01T00:00:00", "likes": 10, "collects": 5, "comments": 2},
        {"timestamp": "2024-01-02T00:00:00", "likes": 25, "collects": 12, "comments": 8},
        {"timestamp": "2024-01-03T00:00:00", "likes": 45, "collects": 22, "comments": 15}
    ]
    
    return StandardResponse(data={"history": history})


@router.get("/platforms", response_model=StandardResponse)
async def list_platforms(
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """获取支持的发布平台"""
    platforms = [
        {"id": "xiaohongshu", "name": "小红书", "enabled": True},
        {"id": "wechat", "name": "微信公众号", "enabled": False},
        {"id": "douyin", "name": "抖音", "enabled": False}
    ]
    
    return StandardResponse(data={"platforms": platforms})
