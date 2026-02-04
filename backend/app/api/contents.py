"""
NoteTrial API - 内容管理模块
内容 CRUD + AI 生成
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from .auth import get_current_user
from .schemas import Content, ContentCreate, ContentUpdate, PaginatedResponse, StandardResponse

router = APIRouter(prefix="/contents", tags=["内容管理"])

# 模拟数据存储（生产环境应使用数据库）
contents_db: Dict[str, Content] = {}


class ContentGenerationRequest(BaseModel):
    """内容生成请求"""
    topic: str = Field(..., description="创作话题")
    goals: List[str] = Field(default=["maximize_save"], description="优化目标")
    audience: str = Field(default="小红书用户", description="目标受众")
    tone: List[str] = Field(default_factory=lambda: ["真实", "口语化"], description="语气约束")
    reference_count: int = Field(default=10, ge=1, le=20, description="参考内容数量")


class ContentGenerationResponse(BaseModel):
    """内容生成响应"""
    content: Dict[str, Any]
    reference_count: int
    generated_at: datetime


class BulkCreateRequest(BaseModel):
    """批量创建请求"""
    contents: List[ContentCreate]


@router.get("", response_model=PaginatedResponse[Content])
async def list_contents(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    topic: Optional[str] = Query(None, description="话题筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    current_user: dict = Depends(get_current_user)
) -> PaginatedResponse[Content]:
    """获取内容列表（分页）"""
    filtered = list(contents_db.values())
    
    # 筛选
    if topic:
        filtered = [c for c in filtered if topic.lower() in c.topic.lower()]
    if status:
        filtered = [c for c in filtered if c.status == status]
    
    # 排序（按更新时间降序）
    filtered.sort(key=lambda x: x.updated_at, reverse=True)
    
    # 分页
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


@router.get("/{content_id}", response_model=StandardResponse[Content])
async def get_content(
    content_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[Content]:
    """获取单个内容详情"""
    if content_id not in contents_db:
        raise HTTPException(status_code=404, detail="内容不存在")
    
    return StandardResponse(data=contents_db[content_id])


@router.post("", response_model=StandardResponse[Content])
async def create_content(
    content_data: ContentCreate,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[Content]:
    """创建新内容"""
    content_id = str(uuid.uuid4())
    
    content = Content(
        id=content_id,
        **content_data.model_dump(),
        created_by=current_user.get("user_id", "anonymous"),
        status="draft"
    )
    
    contents_db[content_id] = content
    
    return StandardResponse(
        data=content,
        message="内容创建成功"
    )


@router.put("/{content_id}", response_model=StandardResponse[Content])
async def update_content(
    content_id: str,
    update_data: ContentUpdate,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[Content]:
    """更新内容"""
    if content_id not in contents_db:
        raise HTTPException(status_code=404, detail="内容不存在")
    
    existing = contents_db[content_id]
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for key, value in update_dict.items():
        setattr(existing, key, value)
    
    existing.updated_at = datetime.utcnow()
    
    return StandardResponse(
        data=existing,
        message="内容更新成功"
    )


@router.delete("/{content_id}", response_model=StandardResponse)
async def delete_content(
    content_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """删除内容"""
    if content_id not in contents_db:
        raise HTTPException(status_code=404, detail="内容不存在")
    
    del contents_db[content_id]
    
    return StandardResponse(message="内容删除成功")


@router.post("/generate", response_model=StandardResponse[ContentGenerationResponse])
async def generate_content(
    request: ContentGenerationRequest,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[ContentGenerationResponse]:
    """AI 生成内容"""
    # TODO: 集成 ContentGenerator 服务
    generated_content = {
        "title": f"关于{request.topic}的爆款笔记",
        "body": f"这是基于{request.topic}生成的正文内容...",
        "tags": [request.topic, "干货分享", "推荐"]
    }
    
    response = ContentGenerationResponse(
        content=generated_content,
        reference_count=request.reference_count,
        generated_at=datetime.utcnow()
    )
    
    return StandardResponse(
        data=response,
        message="内容生成成功"
    )


@router.post("/bulk", response_model=StandardResponse)
async def bulk_create_contents(
    request: BulkCreateRequest,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """批量创建内容"""
    created_ids = []
    
    for item in request.contents:
        content_id = str(uuid.uuid4())
        content = Content(
            id=content_id,
            **item.model_dump(),
            created_by=current_user.get("user_id", "anonymous"),
            status="draft"
        )
        contents_db[content_id] = content
        created_ids.append(content_id)
    
    return StandardResponse(
        data={"created_ids": created_ids},
        message=f"成功创建 {len(created_ids)} 条内容"
    )


@router.post("/{content_id}/duplicate", response_model=StandardResponse[Content])
async def duplicate_content(
    content_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[Content]:
    """复制内容"""
    if content_id not in contents_db:
        raise HTTPException(status_code=404, detail="原内容不存在")
    
    original = contents_db[content_id]
    new_id = str(uuid.uuid4())
    
    new_content = Content(
        id=new_id,
        title=f"{original.title} (副本)",
        body=original.body,
        topic=original.topic,
        tags=original.tags,
        cover_image=original.cover_image,
        created_by=current_user.get("user_id", "anonymous"),
        status="draft"
    )
    
    contents_db[new_id] = new_content
    
    return StandardResponse(
        data=new_content,
        message="内容复制成功"
    )


@router.post("/{content_id}/status", response_model=StandardResponse[Content])
async def update_content_status(
    content_id: str,
    status: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[Content]:
    """更新内容状态"""
    if content_id not in contents_db:
        raise HTTPException(status_code=404, detail="内容不存在")
    
    valid_statuses = ["draft", "review", "published", "archived"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"无效状态，可选: {valid_statuses}")
    
    content = contents_db[content_id]
    content.status = status
    content.updated_at = datetime.utcnow()
    
    return StandardResponse(
        data=content,
        message=f"状态更新为 {status}"
    )
