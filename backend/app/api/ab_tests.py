"""
NoteTrial API - A/B 测试管理模块
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from .auth import get_current_user
from .schemas import ABTest, ABTestCreate, ABTestUpdate, PaginatedResponse, StandardResponse

router = APIRouter(prefix="/ab-tests", tags=["A/B测试"])

# 模拟数据存储
ab_tests_db: Dict[str, ABTest] = {}


class ABTestRunRequest(BaseModel):
    """运行 A/B 测试请求"""
    task_spec: Dict[str, Any]
    content_a: Dict[str, Any]
    content_b: Dict[str, Any]
    max_users: int = Field(default=20, ge=5, le=100)
    audience_tags: Optional[List[str]] = None


class ABTestResultResponse(BaseModel):
    """测试结果响应"""
    test_id: str
    version_a_score: Dict[str, int]
    version_b_score: Dict[str, int]
    winner: str
    confidence: float
    diagnosis: List[str]
    suggestions: List[str]


class ABTestVariantRequest(BaseModel):
    """创建变体请求"""
    base_content_id: str
    variant_type: str = Field(default="alternative", description="alternative/hook/actionable")


@router.get("", response_model=PaginatedResponse[ABTest])
async def list_ab_tests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
) -> PaginatedResponse[ABTest]:
    """获取 A/B 测试列表"""
    filtered = list(ab_tests_db.values())
    
    if status:
        filtered = [t for t in filtered if t.status == status]
    
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


@router.get("/{test_id}", response_model=StandardResponse[ABTest])
async def get_ab_test(
    test_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[ABTest]:
    """获取 A/B 测试详情"""
    if test_id not in ab_tests_db:
        raise HTTPException(status_code=404, detail="测试不存在")
    
    return StandardResponse(data=ab_tests_db[test_id])


@router.post("", response_model=StandardResponse[ABTest])
async def create_ab_test(
    test_data: ABTestCreate,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[ABTest]:
    """创建 A/B 测试"""
    test_id = str(uuid.uuid4())
    
    test = ABTest(
        id=test_id,
        **test_data.model_dump(),
        created_by=current_user.get("user_id", "anonymous"),
        status="pending"
    )
    
    ab_tests_db[test_id] = test
    
    return StandardResponse(
        data=test,
        message="A/B 测试创建成功"
    )


@router.put("/{test_id}", response_model=StandardResponse[ABTest])
async def update_ab_test(
    test_id: str,
    update_data: ABTestUpdate,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[ABTest]:
    """更新 A/B 测试"""
    if test_id not in ab_tests_db:
        raise HTTPException(status_code=404, detail="测试不存在")
    
    existing = ab_tests_db[test_id]
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for key, value in update_dict.items():
        setattr(existing, key, value)
    
    existing.updated_at = datetime.utcnow()
    
    return StandardResponse(
        data=existing,
        message="测试更新成功"
    )


@router.delete("/{test_id}", response_model=StandardResponse)
async def delete_ab_test(
    test_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """删除 A/B 测试"""
    if test_id not in ab_tests_db:
        raise HTTPException(status_code=404, detail="测试不存在")
    
    del ab_tests_db[test_id]
    
    return StandardResponse(message="测试删除成功")


@router.post("/{test_id}/run", response_model=StandardResponse[ABTestResultResponse])
async def run_ab_test(
    test_id: str,
    request: Optional[ABTestRunRequest] = None,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[ABTestResultResponse]:
    """运行 A/B 测试"""
    if test_id not in ab_tests_db:
        raise HTTPException(status_code=404, detail="测试不存在")
    
    test = ab_tests_db[test_id]
    
    # TODO: 集成 CrowdTest 服务
    # 模拟测试结果
    result = ABTestResultResponse(
        test_id=test_id,
        version_a_score={"like": 15, "save": 8, "comment": 5, "share": 2},
        version_b_score={"like": 22, "save": 15, "comment": 8, "share": 4},
        winner="B",
        confidence=87.5,
        diagnosis=[
            "版本B的标题更吸引眼球",
            "版本B的开头更有代入感"
        ],
        suggestions=[
            "建议使用版本B的标题风格",
            "可以在正文中增加更多互动引导"
        ]
    )
    
    # 更新测试状态和结果
    test.status = "completed"
    test.result = result.model_dump()
    test.completed_at = datetime.utcnow()
    
    return StandardResponse(
        data=result,
        message="测试运行完成"
    )


@router.post("/{test_id}/cancel", response_model=StandardResponse[ABTest])
async def cancel_ab_test(
    test_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[ABTest]:
    """取消正在运行的测试"""
    if test_id not in ab_tests_db:
        raise HTTPException(status_code=404, detail="测试不存在")
    
    test = ab_tests_db[test_id]
    
    if test.status == "completed":
        raise HTTPException(status_code=400, detail="已完成的测试无法取消")
    
    test.status = "cancelled"
    test.updated_at = datetime.utcnow()
    
    return StandardResponse(
        data=test,
        message="测试已取消"
    )


@router.post("/variants/generate", response_model=StandardResponse)
async def generate_variant(
    request: ABTestVariantRequest,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """生成内容变体"""
    if request.base_content_id not in ab_tests_db:
        raise HTTPException(status_code=404, detail="原内容不存在")
    
    # TODO: 集成 ContentGenerator 服务
    variant_content = {
        "title": f"变体标题 (基于 {request.base_content_id})",
        "body": f"这是基于 {request.variant_type} 类型生成的变体内容...",
        "tags": ["变体", request.variant_type]
    }
    
    return StandardResponse(
        data={
            "variant_type": request.variant_type,
            "content": variant_content
        },
        message="变体生成成功"
    )


@router.get("/{test_id}/progress", response_model=StandardResponse)
async def get_test_progress(
    test_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """获取测试运行进度"""
    if test_id not in ab_tests_db:
        raise HTTPException(status_code=404, detail="测试不存在")
    
    test = ab_tests_db[test_id]
    
    # 模拟进度
    progress = {
        "status": test.status,
        "progress_percent": 100 if test.status == "completed" else 0,
        "elapsed_seconds": 0,
        "estimated_remaining": 0
    }
    
    return StandardResponse(data=progress)


@router.get("/{test_id}/comparison", response_model=StandardResponse)
async def get_comparison(
    test_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """获取 A/B 版本对比数据"""
    if test_id not in ab_tests_db:
        raise HTTPException(status_code=404, detail="测试不存在")
    
    test = ab_tests_db[test_id]
    
    # 模拟对比数据
    comparison = {
        "test_id": test_id,
        "version_a": {
            "title": test.content_a.get("title", ""),
            "body_preview": test.content_a.get("body", "")[:100] + "...",
            "metrics": test.result.get("version_a_score", {}) if test.result else {}
        },
        "version_b": {
            "title": test.content_b.get("title", ""),
            "body_preview": test.content_b.get("body", "")[:100] + "...",
            "metrics": test.result.get("version_b_score", {}) if test.result else {}
        },
        "winner": test.result.get("winner", "") if test.result else None
    }
    
    return StandardResponse(data=comparison)
