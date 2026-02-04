"""
NoteTrial Backend - 数据分析引擎
提供全面的数据分析功能，支持数据概览、趋势分析、TOP分析、转化漏斗和用户画像
"""
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.orm import Session

from app.models.mcp_models import PostHistory, UserAccount


@dataclass
class DateRange:
    """日期范围"""
    start_date: datetime
    end_date: datetime


class AnalyticsEngine:
    """
    数据分析引擎
    
    功能：
    1. 数据概览 - 总发布数、总互动、互动率、环比变化、爆款率
    2. 趋势分析 - 按日/周/月聚合、趋势方向、异常检测
    3. TOP分析 - TOP10笔记、话题、风格
    4. 转化漏斗 - 曝光→点击→互动、转化率、流失分析
    5. 用户画像 - 受众、活跃时间、偏好分析
    """
    
    def __init__(self, db_session: Session, user_id: str):
        self.db = db_session
        self.user_id = user_id
    
    def _ensure_table_exists(self):
        """确保表存在（用于单元测试）"""
        try:
            PostHistory.__table__.exists(self.db.bind)
        except:
            pass
    
    def _parse_date(self, date_str: Optional[str] = None, days: Optional[int] = None) -> DateRange:
        """解析日期范围"""
        if days:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            return DateRange(start_date, end_date)
        
        if date_str:
            start_date = datetime.strptime(date_str, "%Y-%m-%d")
            end_date = start_date + timedelta(days=1)
            return DateRange(start_date, end_date)
        
        # 默认最近30天
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        return DateRange(start_date, end_date)
    
    def _to_chart_friendly(self, data: Any) -> Any:
        """转换为图表友好的格式"""
        if isinstance(data, datetime):
            return data.isoformat()
        if isinstance(data, Decimal):
            return float(data)
        if isinstance(data, dict):
            return {k: self._to_chart_friendly(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._to_chart_friendly(item) for item in data]
        return data
    
    # ==================== 1. 数据概览 ====================
    
    def get_overview(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: Optional[int] = 30
    ) -> Dict[str, Any]:
        """
        获取数据概览
        
        返回：
        - 总发布数、总互动、互动率
        - 环比变化（上周/本周）
        - 爆款率计算
        """
        date_range = self._parse_date(start_date, days)
        
        # 当前周期数据
        current_stats = self.db.query(
            func.count(PostHistory.id).label('total_posts'),
            func.sum(PostHistory.like_count).label('total_likes'),
            func.sum(PostHistory.collect_count).label('total_collects'),
            func.sum(PostHistory.comment_count).label('total_comments'),
            func.sum(PostHistory.view_count).label('total_views'),
        ).filter(
            and_(
                PostHistory.user_id == self.user_id,
                PostHistory.published_at >= date_range.start_date,
                PostHistory.published_at < date_range.end_date,
                PostHistory.status == 'published'
            )
        ).first()
        
        current_posts = current_stats.total_posts or 0
        current_likes = current_stats.total_likes or 0
        current_collects = current_stats.total_collects or 0
        current_comments = current_stats.total_comments or 0
        current_views = current_stats.total_views or 0
        
        total_interactions = current_likes + current_collects + current_comments
        interaction_rate = (total_interactions / current_views * 100) if current_views > 0 else 0
        
        # 上一周期数据（用于环比）
        prev_start = date_range.start_date - (date_range.end_date - date_range.start_date)
        prev_stats = self.db.query(
            func.count(PostHistory.id).label('total_posts'),
            func.sum(PostHistory.like_count).label('total_likes'),
            func.sum(PostHistory.collect_count).label('total_collects'),
            func.sum(PostHistory.comment_count).label('total_comments'),
            func.sum(PostHistory.view_count).label('total_views'),
        ).filter(
            and_(
                PostHistory.user_id == self.user_id,
                PostHistory.published_at >= prev_start,
                PostHistory.published_at < date_range.start_date,
                PostHistory.status == 'published'
            )
        ).first()
        
        prev_posts = prev_stats.total_posts or 0
        prev_likes = prev_stats.total_likes or 0
        prev_collects = prev_stats.total_collects or 0
        prev_comments = prev_stats.total_comments or 0
        prev_views = prev_stats.total_views or 0
        
        prev_total_interactions = prev_likes + prev_collects + prev_comments
        prev_interaction_rate = (prev_total_interactions / prev_views * 100) if prev_views > 0 else 0
        
        # 爆款率计算（互动量超过平均值的2倍视为爆款）
        if current_posts > 0:
            avg_interactions = total_interactions / current_posts
            viral_posts = self.db.query(func.count(PostHistory.id)).filter(
                and_(
                    PostHistory.user_id == self.user_id,
                    PostHistory.published_at >= date_range.start_date,
                    PostHistory.published_at < date_range.end_date,
                    PostHistory.status == 'published',
                    PostHistory.like_count + PostHistory.collect_count + PostHistory.comment_count > avg_interactions * 2
                )
            ).scalar() or 0
            viral_rate = (viral_posts / current_posts * 100)
        else:
            viral_rate = 0
            viral_posts = 0
        
        # 计算环比变化
        def calc_change(current: float, previous: float) -> Dict[str, Any]:
            if previous == 0:
                return {"value": current, "change": None, "direction": "new"}
            change = ((current - previous) / previous * 100)
            return {
                "value": current,
                "previous": previous,
                "change": round(change, 2),
                "direction": "up" if change > 0 else "down" if change < 0 else "stable"
            }
        
        overview = {
            "period": {
                "start": date_range.start_date.isoformat(),
                "end": date_range.end_date.isoformat(),
                "days": (date_range.end_date - date_range.start_date).days
            },
            "publishing": calc_change(current_posts, prev_posts),
            "views": calc_change(current_views, prev_views),
            "interactions": {
                "total": calc_change(total_interactions, prev_total_interactions),
                "likes": current_likes,
                "collects": current_collects,
                "comments": current_comments,
                "breakdown": {
                    "likes": calc_change(current_likes, prev_likes),
                    "collects": calc_change(current_collects, prev_collects),
                    "comments": calc_change(current_comments, prev_comments)
                }
            },
            "interaction_rate": {
                "value": round(interaction_rate, 2),
                "previous": round(prev_interaction_rate, 2),
                "change": round(interaction_rate - prev_interaction_rate, 2),
                "direction": "up" if interaction_rate > prev_interaction_rate else "down" if interaction_rate < prev_interaction_rate else "stable"
            },
            "viral": {
                "count": viral_posts,
                "rate": round(viral_rate, 2),
                "threshold": "2x average"
            }
        }
        
        return self._to_chart_friendly(overview)
    
    # ==================== 2. 趋势分析 ====================
    
    def get_trends(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: Optional[int] = 30,
        granularity: str = "day"
    ) -> Dict[str, Any]:
        """
        获取趋势分析
        
        返回：
        - 按日/周/月聚合数据
        - 趋势方向（上/下/稳定）
        - 异常检测（数据暴跌/暴涨）
        """
        date_range = self._parse_date(start_date, days)
        
        # 根据粒度确定分组字段
        if granularity == "week":
            date_trunc = func.date_trunc('week', PostHistory.published_at)
        elif granularity == "month":
            date_trunc = func.date_trunc('month', PostHistory.published_at)
        else:
            date_trunc = func.date_trunc('day', PostHistory.published_at)
        
        # 按时间聚合数据
        trend_data = self.db.query(
            date_trunc.label('period'),
            func.count(PostHistory.id).label('posts'),
            func.sum(PostHistory.view_count).label('views'),
            func.sum(PostHistory.like_count).label('likes'),
            func.sum(PostHistory.collect_count).label('collects'),
            func.sum(PostHistory.comment_count).label('comments'),
        ).filter(
            and_(
                PostHistory.user_id == self.user_id,
                PostHistory.published_at >= date_range.start_date,
                PostHistory.published_at < date_range.end_date,
                PostHistory.status == 'published'
            )
        ).group_by('period').order_by('period').all()
        
        # 转换为列表格式
        trends = []
        for row in trend_data:
            interactions = (row.likes or 0) + (row.collects or 0) + (row.comments or 0)
            views = row.views or 0
            trends.append({
                "date": row.period.isoformat() if row.period else None,
                "posts": row.posts or 0,
                "views": views,
                "interactions": interactions,
                "interaction_rate": round((interactions / views * 100), 2) if views > 0 else 0
            })
        
        # 计算趋势方向
        def calculate_trend(data: List[Dict], key: str) -> Dict[str, Any]:
            if len(data) < 2:
                return {"direction": "insufficient_data", "strength": 0}
            
            values = [d.get(key, 0) for d in data if d.get(key, 0) is not None]
            if len(values) < 2:
                return {"direction": "insufficient_data", "strength": 0}
            
            n = len(values)
            if n < 2:
                return {"direction": "insufficient_data", "strength": 0}
            
            avg = sum(values) / n
            if avg == 0:
                return {"direction": "stable", "strength": 0}
            
            x_mean = (n - 1) / 2
            numerator = sum((i - x_mean) * (values[i] - avg) for i in range(n))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            
            if denominator == 0:
                slope = 0
            else:
                slope = numerator / denominator
            
            normalized_slope = (slope / avg * 100) if avg > 0 else 0
            
            threshold = 5
            if abs(normalized_slope) < threshold:
                direction = "stable"
                strength = round(abs(normalized_slope) / threshold * 50)
            elif normalized_slope > 0:
                direction = "up"
                strength = min(100, round(normalized_slope / threshold * 50))
            else:
                direction = "down"
                strength = min(100, round(abs(normalized_slope) / threshold * 50))
            
            return {
                "direction": direction,
                "strength": strength,
                "slope": round(normalized_slope, 2)
            }
        
        # 异常检测
        def detect_anomalies(data: List[Dict], key: str) -> List[Dict]:
            if len(data) < 3:
                return []
            
            values = [d.get(key, 0) for d in data if d.get(key, 0) is not None]
            if len(values) < 3:
                return []
            
            mean_val = sum(values) / len(values)
            std_val = (sum((v - mean_val) ** 2 for v in values) / len(values)) ** 0.5
            
            if std_val == 0:
                return []
            
            anomalies = []
            for i, d in enumerate(data):
                val = d.get(key, 0)
                if val is None:
                    continue
                
                z_score = abs((val - mean_val) / std_val)
                if z_score > 2:
                    anomaly_type = "spike" if val > mean_val else "drop"
                    anomalies.append({
                        "date": d["date"],
                        "type": anomaly_type,
                        "value": val,
                        "mean": round(mean_val, 2),
                        "z_score": round(z_score, 2),
                        "severity": "high" if z_score > 3 else "medium"
                    })
            
            return anomalies
        
        trend_analysis = {
            "period": {
                "start": date_range.start_date.isoformat(),
                "end": date_range.end_date.isoformat(),
                "granularity": granularity
            },
            "trends": trends,
            "analysis": {
                "publishing_trend": calculate_trend(trends, "posts"),
                "views_trend": calculate_trend(trends, "views"),
                "interaction_trend": calculate_trend(trends, "interactions"),
                "interaction_rate_trend": calculate_trend(trends, "interaction_rate")
            },
            "anomalies": {
                "views": detect_anomalies(trends, "views"),
                "interactions": detect_anomalies(trends, "interactions"),
                "posts": detect_anomalies(trends, "posts")
            }
        }
        
        return self._to_chart_friendly(trend_analysis)
    
    # ==================== 3. TOP分析 ====================
    
    def get_top_posts(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: Optional[int] = 30,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        获取TOP分析
        
        返回：
        - TOP 10 笔记（按互动排序）
        - TOP 话题（按发布数排序）
        - TOP 风格（按转化率排序）
        """
        date_range = self._parse_date(start_date, days)
        
        # TOP 笔记（按互动排序）
        top_posts = self.db.query(PostHistory).filter(
            and_(
                PostHistory.user_id == self.user_id,
                PostHistory.published_at >= date_range.start_date,
                PostHistory.published_at < date_range.end_date,
                PostHistory.status == 'published'
            )
        ).order_by(
            desc(PostHistory.like_count + PostHistory.collect_count + PostHistory.comment_count)
        ).limit(limit).all()
        
        posts_data = []
        for post in top_posts:
            interactions = post.like_count + post.collect_count + post.comment_count
            views = post.view_count or 1
            posts_data.append({
                "rank": len(posts_data) + 1,
                "post_id": post.post_id,
                "title": post.title,
                "published_at": post.published_at.isoformat() if post.published_at else None,
                "stats": {
                    "views": post.view_count,
                    "likes": post.like_count,
                    "collects": post.collect_count,
                    "comments": post.comment_count,
                    "interactions": interactions,
                    "interaction_rate": round(interactions / views * 100, 2)
                },
                "tags": post.tags or [],
                "heat_trend": post.heat_trend
            })
        
        # TOP 话题（按发布数排序）
        tag_counts = {}
        for post in top_posts:
            tags = post.tags or []
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        topics_data = [{"tag": tag, "count": count, "rank": i + 1} for i, (tag, count) in enumerate(top_tags)]
        
        # TOP 风格分析
        style_performance = {}
        for post in top_posts:
            title = post.title or ""
            if '?' in title or '？' in title or '吗' in title:
                style = "疑问句"
            elif '!' in title or '！' in title or '绝了' in title:
                style = "感叹句"
            elif any(c.isdigit() for c in title):
                style = "清单式"
            elif '如何' in title or '怎么' in title or '攻略' in title:
                style = "教程式"
            else:
                style = "陈述句"
            
            if style not in style_performance:
                style_performance[style] = {"posts": 0, "total_interactions": 0, "total_views": 0}
            
            style_performance[style]["posts"] += 1
            interactions = post.like_count + post.collect_count + post.comment_count
            views = post.view_count or 1
            style_performance[style]["total_interactions"] += interactions
            style_performance[style]["total_views"] += views
        
        styles_data = []
        for style, data in style_performance.items():
            avg_interactions = data["total_interactions"] / data["posts"] if data["posts"] > 0 else 0
            avg_views = data["total_views"] / data["posts"] if data["posts"] > 0 else 0
            conversion_rate = (avg_interactions / avg_views * 100) if avg_views > 0 else 0
            styles_data.append({
                "style": style,
                "posts": data["posts"],
                "avg_interactions": round(avg_interactions, 2),
                "avg_views": round(avg_views, 2),
                "conversion_rate": round(conversion_rate, 2)
            })
        
        styles_data.sort(key=lambda x: x["conversion_rate"], reverse=True)
        for i, style in enumerate(styles_data):
            style["rank"] = i + 1
        
        top_analysis = {
            "period": {
                "start": date_range.start_date.isoformat(),
                "end": date_range.end_date.isoformat()
            },
            "top_posts": posts_data,
            "top_topics": topics_data,
            "top_styles": styles_data
        }
        
        return self._to_chart_friendly(top_analysis)
    
    # ==================== 4. 转化漏斗 ====================
    
    def get_conversion_funnel(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: Optional[int] = 30
    ) -> Dict[str, Any]:
        """
        获取转化漏斗分析
        
        返回：
        - 曝光 → 点击 → 互动
        - 各环节转化率
        - 流失分析
        """
        date_range = self._parse_date(start_date, days)
        
        posts = self.db.query(PostHistory).filter(
            and_(
                PostHistory.user_id == self.user_id,
                PostHistory.published_at >= date_range.start_date,
                PostHistory.published_at < date_range.end_date,
                PostHistory.status == 'published'
            )
        ).all()
        
        if not posts:
            return {
                "period": {
                    "start": date_range.start_date.isoformat(),
                    "end": date_range.end_date.isoformat()
                },
                "funnel": [],
                "conversion_rates": {},
                "drop_off": {},
                "message": "No published posts in this period"
            }
        
        total_views = sum(p.view_count or 0 for p in posts)
        total_likes = sum(p.like_count for p in posts)
        total_collects = sum(p.collect_count for p in posts)
        total_comments = sum(p.comment_count for p in posts)
        total_interactions = total_likes + total_collects + total_comments
        
        # 漏斗数据
        funnel_data = [
            {
                "stage": "exposure",
                "name": "曝光",
                "count": total_views,
                "percentage": 100.0
            },
            {
                "stage": "engagement",
                "name": "互动",
                "count": total_interactions,
                "percentage": round(total_interactions / total_views * 100, 2) if total_views > 0 else 0
            }
        ]
        
        # 各环节转化率
        ctr = round(total_interactions / total_views * 100, 2) if total_views > 0 else 0
        overall_conversion = ctr
        
        conversion_rates = {
            "exposure_to_engagement": {
                "name": "曝光→互动转化率",
                "rate": ctr,
                "benchmark": "1-3% 为良好",
                "status": "good" if ctr >= 3 else "average" if ctr >= 1 else "needs_improvement"
            },
            "overall_conversion": {
                "name": "总体转化率",
                "rate": overall_conversion,
                "benchmark": "0.1-0.5% 为良好",
                "status": "good" if overall_conversion >= 0.5 else "average" if overall_conversion >= 0.1 else "needs_improvement"
            }
        }
        
        # 流失分析
        exposure_to_engagement_lost = total_views - total_interactions
        lost_rate = round(exposure_to_engagement_lost / total_views * 100, 2) if total_views > 0 else 0
        
        drop_off = {
            "exposure_to_engagement": {
                "from": "曝光",
                "to": "互动",
                "lost_count": exposure_to_engagement_lost,
                "lost_rate": lost_rate,
                "suggestion": "优化标题和封面，提高点击和互动率"
            }
        }
        
        # 互动类型分布
        interaction_breakdown = {
            "likes": {
                "count": total_likes,
                "percentage": round(total_likes / total_interactions * 100, 2) if total_interactions > 0 else 0
            },
            "collects": {
                "count": total_collects,
                "percentage": round(total_collects / total_interactions * 100, 2) if total_interactions > 0 else 0
            },
            "comments": {
                "count": total_comments,
                "percentage": round(total_comments / total_interactions * 100, 2) if total_interactions > 0 else 0
            }
        }
        
        funnel_analysis = {
            "period": {
                "start": date_range.start_date.isoformat(),
                "end": date_range.end_date.isoformat()
            },
            "funnel": funnel_data,
            "conversion_rates": conversion_rates,
            "drop_off": drop_off,
            "interaction_breakdown": interaction_breakdown
        }
        
        return self._to_chart_friendly(funnel_analysis)
    
    # ==================== 5. 用户画像 ====================
    
    def get_audience_analysis(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: Optional[int] = 30
    ) -> Dict[str, Any]:
        """
        获取用户画像分析
        
        返回：
        - 受众分析
        - 活跃时间分析
        - 偏好分析
        """
        date_range = self._parse_date(start_date, days)
        
        posts = self.db.query(PostHistory).filter(
            and_(
                PostHistory.user_id == self.user_id,
                PostHistory.published_at >= date_range.start_date,
                PostHistory.published_at < date_range.end_date,
                PostHistory.status == 'published'
            )
        ).all()
        
        if not posts:
            return {
                "period": {
                    "start": date_range.start_date.isoformat(),
                    "end": date_range.end_date.isoformat()
                },
                "audience": {
                    "total_reach": 0,
                    "engagement_pattern": "insufficient_data"
                },
                "active_hours": {},
                "preferences": {},
                "message": "No published posts in this period"
            }
        
        # 活跃时间分析
        hourly_activity = {}
        hourly_engagement = {}
        daily_activity = {}
        
        for post in posts:
            if post.published_at:
                hour = post.published_at.hour
                day = post.published_at.strftime("%A")
                
                hourly_activity[hour] = hourly_activity.get(hour, 0) + 1
                
                interactions = post.like_count + post.collect_count + post.comment_count
                if hour not in hourly_engagement:
                    hourly_engagement[hour] = {"total_interactions": 0, "post_count": 0}
                hourly_engagement[hour]["total_interactions"] += interactions
                hourly_engagement[hour]["post_count"] += 1
                
                daily_activity[day] = daily_activity.get(day, 0) + 1
        
        hourly_avg_engagement = {}
        for hour, data in hourly_engagement.items():
            avg = data["total_interactions"] / data["post_count"] if data["post_count"] > 0 else 0
            hourly_avg_engagement[hour] = round(avg, 2)
        
        best_hours = sorted(hourly_avg_engagement.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # 偏好分析
        tag_performance = {}
        for post in posts:
            tags = post.tags or []
            interactions = post.like_count + post.collect_count + post.comment_count
            views = post.view_count or 1
            
            for tag in tags:
                if tag not in tag_performance:
                    tag_performance[tag] = {"posts": 0, "total_interactions": 0, "total_views": 0}
                tag_performance[tag]["posts"] += 1
                tag_performance[tag]["total_interactions"] += interactions
                tag_performance[tag]["total_views"] += views
        
        tag_analysis = []
        for tag, data in tag_performance.items():
            avg_interactions = data["total_interactions"] / data["posts"]
            avg_views = data["total_views"] / data["posts"]
            conversion_rate = (avg_interactions / avg_views * 100) if avg_views > 0 else 0
            tag_analysis.append({
                "tag": tag,
                "posts": data["posts"],
                "avg_interactions": round(avg_interactions, 2),
                "avg_views": round(avg_views, 2),
                "conversion_rate": round(conversion_rate, 2)
            })
        
        tag_analysis.sort(key=lambda x: x["conversion_rate"], reverse=True)
        top_tags = tag_analysis[:10]
        
        # 风格偏好
        style_performance = {}
        for post in posts:
            title = post.title or ""
            if '?' in title or '？' in title or '吗' in title:
                style = "疑问句"
            elif '!' in title or '！' in title or '绝了' in title:
                style = "感叹句"
            elif any(c.isdigit() for c in title):
                style = "清单式"
            elif '如何' in title or '怎么' in title or '攻略' in title:
                style = "教程式"
            else:
                style = "陈述句"
            
            interactions = post.like_count + post.collect_count + post.comment_count
            views = post.view_count or 1
            
            if style not in style_performance:
                style_performance[style] = {"posts": 0, "total_interactions": 0, "total_views": 0}
            style_performance[style]["posts"] += 1
            style_performance[style]["total_interactions"] += interactions
            style_performance[style]["total_views"] += views
        
        style_analysis = []
        for style, data in style_performance.items():
            avg_interactions = data["total_interactions"] / data["posts"]
            avg_views = data["total_views"] / data["posts"]
            conversion_rate = (avg_interactions / avg_views * 100) if avg_views > 0 else 0
            style_analysis.append({
                "style": style,
                "posts": data["posts"],
                "avg_interactions": round(avg_interactions, 2),
                "avg_views": round(avg_views, 2),
                "conversion_rate": round(conversion_rate, 2)
            })
        
        style_analysis.sort(key=lambda x: x["conversion_rate"], reverse=True)
        
        total_views = sum(p.view_count or 0 for p in posts)
        total_interactions = sum(p.like_count + p.collect_count + p.comment_count for p in posts)
        
        audience_analysis = {
            "period": {
                "start": date_range.start_date.isoformat(),
                "end": date_range.end_date.isoformat()
            },
            "audience": {
                "estimated_reach": total_views,
                "total_interactions": total_interactions,
                "avg_interactions_per_post": round(total_interactions / len(posts), 2) if posts else 0,
                "engagement_rate": round(total_interactions / total_views * 100, 2) if total_views > 0 else 0
            },
            "active_hours": {
                "distribution": {f"{h:02d}:00": count for h, count in sorted(hourly_activity.items())},
                "avg_engagement_by_hour": {f"{h:02d}:00": score for h, score in sorted(hourly_avg_engagement.items())},
                "best_publishing_hours": [f"{h:02d}:00" for h, _ in best_hours],
                "best_days": sorted(daily_activity.items(), key=lambda x: x[1], reverse=True)[:3]
            },
            "preferences": {
                "top_tags": top_tags,
                "content_styles": style_analysis,
                "summary": {
                    "most_effective_tag": top_tags[0]["tag"] if top_tags else None,
                    "most_effective_style": style_analysis[0]["style"] if style_analysis else None
                }
            },
            "insights": self._generate_audience_insights(
                best_hours, top_tags, style_analysis, daily_activity
            )
        }
        
        return self._to_chart_friendly(audience_analysis)
    
    def _generate_audience_insights(
        self,
        best_hours: List[tuple],
        top_tags: List[Dict],
        style_analysis: List[Dict],
        daily_activity: Dict
    ) -> List[str]:
        """生成受众洞察建议"""
        insights = []
        
        if best_hours:
            best_hour = best_hours[0][0]
            insights.append(f"最佳发布时间: {best_hour:02d}:00，此时用户互动最活跃")
        
        if top_tags and top_tags[0].get("conversion_rate", 0) > 0:
            insights.append(f"效果最好的标签是「{top_tags[0]['tag']}」，转化率 {top_tags[0]['conversion_rate']}%")
        
        if style_analysis:
            best_style = style_analysis[0]
            insights.append(f"「{best_style['style']}」风格的内容表现最好，平均互动 {best_style['avg_interactions']} 次")
        
        if daily_activity:
            best_day = max(daily_activity.items(), key=lambda x: x[1])
            insights.append(f"你最常在 {best_day[0]} 发布内容")
        
        return insights


# ==================== API 端点注册 ====================

def register_analytics_routes(app):
    """注册分析引擎相关路由"""
    from fastapi import APIRouter, Query
    from typing import Optional
    
    router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])
    
    @router.get("/overview")
    async def get_overview(
        start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
        end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
        days: Optional[int] = Query(30, description="天数（默认30天）")
    ):
        """获取数据概览"""
        from app.main import get_db
        db = next(get_db())
        engine = AnalyticsEngine(db, "current_user")
        return engine.get_overview(start_date, end_date, days)
    
    @router.get("/trends")
    async def get_trends(
        start_date: Optional[str] = Query(None),
        end_date: Optional[str] = Query(None),
        days: Optional[int] = Query(30),
        granularity: str = Query("day", regex="^(day|week|month)$")
    ):
        """获取趋势分析"""
        from app.main import get_db
        db = next(get_db())
        engine = AnalyticsEngine(db, "current_user")
        return engine.get_trends(start_date, end_date, days, granularity)
    
    @router.get("/top-posts")
    async def get_top_posts(
        start_date: Optional[str] = Query(None),
        end_date: Optional[str] = Query(None),
        days: Optional[int] = Query(30),
        limit: int = Query(10, ge=1, le=100)
    ):
        """获取TOP分析"""
        from app.main import get_db
        db = next(get_db())
        engine = AnalyticsEngine(db, "current_user")
        return engine.get_top_posts(start_date, end_date, days, limit)
    
    @router.get("/conversion-funnel")
    async def get_conversion_funnel(
        start_date: Optional[str] = Query(None),
        end_date: Optional[str] = Query(None),
        days: Optional[int] = Query(30)
    ):
        """获取转化漏斗"""
        from app.main import get_db
        db = next(get_db())
        engine = AnalyticsEngine(db, "current_user")
        return engine.get_conversion_funnel(start_date, end_date, days)
    
    @router.get("/audience")
    async def get_audience(
        start_date: Optional[str] = Query(None),
        end_date: Optional[str] = Query(None),
        days: Optional[int] = Query(30)
    ):
        """获取用户画像"""
        from app.main import get_db
        db = next(get_db())
        engine = AnalyticsEngine(db, "current_user")
        return engine.get_audience_analysis(start_date, end_date, days)
    
    app.include_router(router)
    return router
