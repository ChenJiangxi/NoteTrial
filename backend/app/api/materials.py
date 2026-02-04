"""
NoteTrial API - 素材库管理模块
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
import base64

from .auth import get_current_user
from .schemas import (
    MaterialImage, MaterialText, 
    PaginatedResponse, StandardResponse
)

router = APIRouter(prefix="/materials", tags=["素材库"])

# 模拟数据存储
images_db: Dict[str, MaterialImage] = {}
texts_db: Dict[str, MaterialText] = {}


class ImageUploadRequest(BaseModel):
    """图片上传请求"""
    image_data: str = Field(..., description="Base64 图片数据")
    filename: Optional[str] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    source: Optional[str] = None


class TextAddRequest(BaseModel):
    """添加文案请求"""
    content: str
    text_type: str = Field(default="copy", description="copy/title/tag/hook")
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    source: Optional[str] = None
    performance: Optional[Dict[str, Any]] = None


class MaterialSearchRequest(BaseModel):
    """素材搜索请求"""
    query: str
    material_type: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = 20


@router.get("/images", response_model=PaginatedResponse[MaterialImage])
async def list_images(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tags: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
) -> PaginatedResponse[MaterialImage]:
    """获取图片素材列表"""
    filtered = list(images_db.values())
    
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        filtered = [img for img in filtered if any(t in img.tags for t in tag_list)]
    if source:
        filtered = [img for img in filtered if img.source == source]
    
    filtered.sort(key=lambda x: x.created_at, reverse=True)
    
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


@router.get("/images/{image_id}", response_model=StandardResponse[MaterialImage])
async def get_image(
    image_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[MaterialImage]:
    """获取图片素材详情"""
    if image_id not in images_db:
        raise HTTPException(status_code=404, detail="图片素材不存在")
    
    return StandardResponse(data=images_db[image_id])


@router.post("/images", response_model=StandardResponse[MaterialImage])
async def add_image(
    request: ImageUploadRequest,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[MaterialImage]:
    """添加图片素材"""
    image_id = str(uuid.uuid4())
    
    try:
        if "," in request.image_data:
            base64_data = request.image_data.split(",")[1]
        else:
            base64_data = request.image_data
        base64.b64decode(base64_data)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 Base64 图片数据")
    
    image = MaterialImage(
        id=image_id,
        image_data=request.image_data,
        filename=request.filename,
        tags=request.tags or [],
        description=request.description,
        source=request.source,
        created_by=current_user.get("user_id", "anonymous")
    )
    
    images_db[image_id] = image
    
    return StandardResponse(
        data=image,
        message="图片素材添加成功"
    )


@router.delete("/images/{image_id}", response_model=StandardResponse)
async def delete_image(
    image_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """删除图片素材"""
    if image_id not in images_db:
        raise HTTPException(status_code=404, detail="图片素材不存在")
    
    del images_db[image_id]
    
    return StandardResponse(message="图片素材删除成功")


@router.get("/texts", response_model=PaginatedResponse[MaterialText])
async def list_texts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    text_type: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
) -> PaginatedResponse[MaterialText]:
    """获取文案素材列表"""
    filtered = list(texts_db.values())
    
    if text_type:
        filtered = [t for t in filtered if t.text_type == text_type]
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        filtered = [t for t in filtered if any(tag in t.tags for tag in tag_list)]
    
    filtered.sort(key=lambda x: x.created_at, reverse=True)
    
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


@router.get("/texts/{text_id}", response_model=StandardResponse[MaterialText])
async def get_text(
    text_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[MaterialText]:
    """获取文案素材详情"""
    if text_id not in texts_db:
        raise HTTPException(status_code=404, detail="文案素材不存在")
    
    return StandardResponse(data=texts_db[text_id])


@router.post("/texts", response_model=StandardResponse[MaterialText])
async def add_text(
    request: TextAddRequest,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[MaterialText]:
    """添加文案素材"""
    text_id = str(uuid.uuid4())
    
    text = MaterialText(
        id=text_id,
        content=request.content,
        text_type=request.text_type,
        tags=request.tags or [],
        description=request.description,
        source=request.source,
        performance=request.performance,
        created_by=current_user.get("user_id", "anonymous")
    )
    
    texts_db[text_id] = text
    
    return StandardResponse(
        data=text,
        message="文案素材添加成功"
    )


@router.delete("/texts/{text_id}", response_model=StandardResponse)
async def delete_text(
    text_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """删除文案素材"""
    if text_id not in texts_db:
        raise HTTPException(status_code=404, detail="文案素材不存在")
    
    del texts_db[text_id]
    
    return StandardResponse(message="文案素材删除成功")


@router.post("/search", response_model=StandardResponse)
async def search_materials(
    request: MaterialSearchRequest,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """搜索素材"""
    results = {"images": [], "texts": []}
    
    # 搜索图片
    if request.material_type is None or request.material_type == "image":
        for img in images_db.values():
            if request.query.lower() in (img.description or "").lower():
                results["images"].append(img)
    
    # 搜索文案
    if request.material_type is None or request.material_type == "text":
        for txt in texts_db.values():
            if request.query.lower() in (txt.content or "").lower():
                results["texts"].append(txt)
    
    # 限制数量
    results["images"] = results["images"][:request.limit]
    results["texts"] = results["texts"][:request.limit]
    
    return StandardResponse(data=results)


@router.get("/stats", response_model=StandardResponse)
async def get_stats(
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """获取素材库统计"""
    stats = {
        "images": {
            "total": len(images_db),
            "by_tag": {},
            "by_source": {}
        },
        "texts": {
            "total": len(texts_db),
            "by_type": {},
            "by_tag": {}
        }
    }
    
    # 统计图片
    for img in images_db.values():
        for tag in img.tags:
            stats["images"]["by_tag"][tag] = stats["images"]["by_tag"].get(tag, 0) + 1
        source = img.source or "unknown"
        stats["images"]["by_source"][source] = stats["images"]["by_source"].get(source, 0) + 1
    
    # 统计文案
    for txt in texts_db.values():
        stats["texts"]["by_type"][txt.text_type] = stats["texts"]["by_type"].get(txt.text_type, 0) + 1
        for tag in txt.tags:
            stats["texts"]["by_tag"][tag] = stats["texts"]["by_tag"].get(tag, 0) + 1
    
    return StandardResponse(data=stats)


@router.get("/relevant", response_model=StandardResponse)
async def get_relevant_materials(
    topic: str,
    max_images: int = 5,
    max_texts: int = 10,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """获取与话题相关的素材"""
    relevant = {"images": [], "texts": []}
    
    # 查找相关图片
    for img in images_db.values():
        if any(topic.lower() in tag.lower() for tag in img.tags):
            relevant["images"].append(img)
    
    # 查找相关文案
    for txt in texts_db.values():
        if topic.lower() in (txt.content or "").lower():
            relevant["texts"].append(txt)
    
    relevant["images"] = relevant["images"][:max_images]
    relevant["texts"] = relevant["texts"][:max_texts]
    
    return StandardResponse(data=relevant)
