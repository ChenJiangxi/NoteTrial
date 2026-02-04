"""
NoteTrial API - 数据分析模块
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid

from .auth import get_current_user
from .schemas import PaginatedResponse, StandardResponse

router = APIRouter(prefix="/analytics", tags=["数据分析"])

# 模拟数据存储


class DateRange(str, Enum):
    """日期范围"""
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    CUSTOM = "custom"


class AnalyticsOverviewResponse(BaseModel):
    """概览数据响应"""
    total_posts: int
    total_likes: int
    total_collects: int
    total_comments: int
    total_shares: int
    avg_engagement_rate: float
    top_performing_content: Optional[Dict[str, Any]]
    period: Dict[str, str]


class ContentAnalyticsRequest(BaseModel):
    """内容分析请求"""
    content_id: str


class TrendDataResponse(BaseModel):
    """趋势数据响应"""
    metric: str
    data_points: List[Dict[str, Any]]
    trend: str
    change_percent: float


class ComparisonRequest(BaseModel):
    """对比分析请求"""
    content_ids: List[str]
    metrics: List[str]


class TopContentResponse(BaseModel):
    """热门内容响应"""
    by_likes: List[Dict[str, Any]]
    by_collects: List[Dict[str, Any]]
    by_comments: List[Dict[str, Any]]


@router.get("/overview", response_model=StandardResponse[AnalyticsOverviewResponse])
async def get_overview(
    date_range: DateRange = DateRange.WEEK,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[AnalyticsOverviewResponse]:
    """获取数据分析概览"""
    # 计算日期范围
    end = datetime.utcnow()
    if date_range == DateRange.TODAY:
        start = end - timedelta(days=1)
    elif date_range == DateRange.WEEK:
        start = end - timedelta(days=7)
    elif date_range == DateRange.MONTH:
        start = end - timedelta(days=30)
    elif date_range == DateRange.QUARTER:
        start = end - timedelta(days=90)
    elif date_range == DateRange.YEAR:
        start = end - timedelta(days=365)
    elif date_range == DateRange.CUSTOM and start_date and end_date:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    else:
        start = end - timedelta(days=7)
    
    # 模拟数据
    response = AnalyticsOverviewResponse(
        total_posts=45,
        total_likes=12500,
        total_collects=3800,
        total_comments=520,
        total_shares=180,
        avg_engagement_rate=8.5,
        top_performing_content={
            "id": "top_content_1",
            "title": "爆款笔记标题",
            "likes": 2500,
            "collects": 1200
        },
        period={
            "start": start.isoformat(),
            "end": end.isoformat(),
            "range": date_range.value
        }
    )
    
    return StandardResponse(data=response)


@router.get("/trends/{metric}", response_model=StandardResponse[TrendDataResponse])
async def get_trends(
    metric: str,
    date_range: DateRange = DateRange.WEEK,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[TrendDataResponse]:
    """获取指定指标的趋势数据"""
    valid_metrics = ["likes", "collects", "comments", "shares", "engagement_rate"]
    if metric not in valid_metrics:
        raise HTTPException(status_code=400, detail=f"无效指标，可选: {valid_metrics}")
    
    # 模拟趋势数据
    data_points = []
    for i in range(7):
        data_points.append({
            "date": (datetime.utcnow() - timedelta(days=6-i)).strftime("%Y-%m-%d"),
            "value": 100 + i * 20 + (i % 3) * 50
        })
    
    response = TrendDataResponse(
        metric=metric,
        data_points=data_points,
        trend="up",
        change_percent=12.5
    )
    
    return StandardResponse(data=response)


@router.get("/top-content", response_model=StandardResponse[TopContentResponse])
async def get_top_content(
    limit: int = Query(10, ge=1, le=50),
    date_range: DateRange = DateRange.WEEK,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[TopContentResponse]:
    """获取热门内容排行"""
    # 模拟数据
    top_content = []
    for i in range(limit):
        top_content.append({
            "id": f"content_{i}",
            "title": f"热门内容 #{i+1}",
            "likes": 1000 - i * 50,
            "collects": 500 - i * 20,
            "comments": 100 - i * 5,
            "engagement_rate": 10.5 - i * 0.3
        })
    
    response = TopContentResponse(
        by_likes=top_content[:limit],
        by_collects=sorted(top_content, key=lambda x: x["collects"], reverse=True)[:limit],
        by_comments=sorted(top_content, key=lambda x: x["comments"], reverse=True)[:limit]
    )
    
    return StandardResponse(data=response)


@router.post("/compare", response_model=StandardResponse)
async def compare_content(
    request: ComparisonRequest,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """对比分析多个内容"""
    if len(request.content_ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要两个内容进行对比")
    
    if len(request.content_ids) > 10:
        raise HTTPException(status_code=400, detail="最多支持10个内容对比")
    
    # 模拟对比数据
    comparison = {
        "contents": [],
        "metrics": {}
    }
    
    for cid in request.content_ids:
        comparison["contents"].append({
            "id": cid,
            "title": f"内容 {cid[:8]}",
            "metrics": {m: 100 + hash(cid + m) % 500 for m in request.metrics}
        })
    
    # 计算平均值
    for metric in request.metrics:
        values = [c["metrics"].get(metric, 0) for c in comparison["contents"]]
        comparison["metrics"][metric] = {
            "avg": sum(values) / len(values),
            "max": max(values),
            "min": min(values)
        }
    
    return StandardResponse(data=comparison)


@router.get("/content/{content_id}", response_model=StandardResponse)
async def get_content_analytics(
    content_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """获取单个内容的详细分析"""
    # 模拟数据
    analytics = {
        "content_id": content_id,
        "title": "内容标题",
        "published_at": datetime.utcnow().isoformat(),
        "metrics": {
            "likes": 1250,
            "collects": 380,
            "comments": 85,
            "shares": 45
        },
        "engagement_rate": 12.5,
        "performance_score": 85,
        "rank_in_period": 3,
        "vs_avg": {
            "likes": "+25%",
            "collects": "+18%",
            "engagement": "+15%"
        }
    }
    
    return StandardResponse(data=analytics)


@router.get("/audience", response_model=StandardResponse)
async def get_audience_analytics(
    date_range: DateRange = DateRange.MONTH,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """获取受众分析"""
    analytics = {
        "demographics": {
            "age_groups": {
                "18-24": 25,
                "25-30": 40,
                "31-35": 25,
                "36+": 10
            },
            "genders": {
                "female": 75,
                "male": 25
            }
        },
        "interests": ["美妆", "护肤", "穿搭", "生活", "美食"],
        "top_regions": ["上海", "北京", "杭州", "深圳", "广州"],
        "active_hours": ["10:00", "12:00", "20:00", "22:00"],
        "engagement_patterns": {
            "best_days": ["周五", "周六", "周日"],
            "best_time": "20:00-22:00"
        }
    }
    
    return StandardResponse(data=analytics)


@router.get("/topics", response_model=StandardResponse)
async def get_topic_analytics(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """获取话题分析"""
    topics = []
    for i in range(limit):
        topics.append({
            "topic": f"话题{i+1}",
            "post_count": 100 - i * 5,
            "total_engagement": 5000 - i * 200,
            "avg_engagement": 50 - i * 2,
            "trend": "up" if i < 3 else "stable"
        })
    
    return StandardResponse(data={"topics": topics})


@router.get("/export", response_model=StandardResponse)
async def export_analytics(
    date_range: DateRange = DateRange.WEEK,
    format: str = Query("json", regex="^(json|csv)$"),
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """导出分析数据"""
    export_data = {
        "export_date": datetime.utcnow().isoformat(),
        "date_range": date_range.value,
        "contents": [
            {
                "id": "content_1",
                "title": "示例内容",
                "likes": 100,
                "collects": 50,
                "comments": 20,
                "shares": 10
            }
        ],
        "summary": {
            "total_posts": 10,
            "total_likes": 1000,
            "total_collects": 500
        }
    }
    
    return StandardResponse(
        data=export_data,
        message=f"数据已导出为 {format.upper()} 格式"
    )


@router.get("/performance-breakdown", response_model=StandardResponse)
async def get_performance_breakdown(
    date_range: DateRange = DateRange.MONTH,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """获取性能分解分析"""
    breakdown = {
        "by_content_type": {
            "图文": {"count": 20, "avg_engagement": 8.5},
            "视频": {"count": 5, "avg_engagement": 12.3},
            "合集": {"count": 3, "avg_engagement": 10.2}
        },
        "by_post_time": {
            "上午 (6-12)": {"count": 8, "avg_engagement": 7.2},
            "下午 (12-18)": {"count": 10, "avg_engagement": 9.1},
            "晚上 (18-24)": {"count": 10, "avg_engagement": 11.5}
        },
        "by_length": {
            "短 (<100字)": {"count": 5, "avg_engagement": 6.8},
            "中 (100-500字)": {"count": 15, "avg_engagement": 9.2},
            "长 (>500字)": {"count": 8, "avg_engagement": 10.5}
        }
    }
    
    return StandardResponse(data=breakdown)
