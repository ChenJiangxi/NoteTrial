"""
MCP 调度服务
Celery定时任务：定时同步用户帖子数据、异常数据通知
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from celery import Celery, shared_task
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from .models.mcp_models import (
    UserAccount, PostHistory, SyncTask,
    SyncConfig, SyncResult, ErrorNotification,
    TaskStatus, AccountStatus
)
from .mcp_service import get_mcp_service, MCPService, decrypt_cookies
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ============ Celery 配置 ============

# 创建Celery应用
celery_app = Celery(
    "mcp_tasks",
    broker=settings.celery_broker_url or "redis://localhost:6379/1",
    backend=settings.celery_result_url or "redis://localhost:6379/2"
)

# Celery配置
celery_app.conf.update(
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    beat_schedule={
        "sync-user-posts-every-hour": {
            "task": "services.scheduler.sync_user_posts",
            "schedule": 3600.0,  # 每小时
            "options": {"queue": "mcp_sync"}
        },
        "track-heat-trends-every-30-min": {
            "task": "services.scheduler.track_heat_trends",
            "schedule": 1800.0,  # 每30分钟
            "options": {"queue": "mcp_heat"}
        },
        "check-expired-cookies-daily": {
            "task": "services.scheduler.check_expired_cookies",
            "schedule": 86400.0,  # 每天
            "options": {"queue": "mcp_maintenance"}
        },
        "cleanup-failed-tasks-daily": {
            "task": "services.scheduler.cleanup_failed_tasks",
            "schedule": 86400.0,  # 每天
            "options": {"queue": "mcp_maintenance"}
        },
    },
    task_routes={
        "services.scheduler.sync_*": {"queue": "mcp_sync"},
        "services.scheduler.track_*": {"queue": "mcp_heat"},
        "services.scheduler.check_*": {"queue": "mcp_maintenance"},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)


# ============ 定时任务 ============

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    name="services.scheduler.sync_user_posts"
)
def sync_user_posts_task(self, user_id: str, account_ids: List[int] = None):
    """
    同步用户帖子数据任务
    """
    from .database import get_db  # 假设有数据库依赖注入
    
    sync_result = {
        "success": True,
        "user_id": user_id,
        "posts_synced": 0,
        "accounts_processed": 0,
        "errors": [],
        "started_at": datetime.utcnow().isoformat()
    }
    
    try:
        # 获取数据库会话
        db = get_db()
        
        # 创建同步任务记录
        sync_task = SyncTask(
            user_id=user_id,
            task_type="sync_posts",
            status=TaskStatus.RUNNING,
            account_ids=account_ids,
            celery_task_id=self.request.id,
            started_at=datetime.utcnow()
        )
        db.add(sync_task)
        db.commit()
        
        # 获取账号列表
        query = db.query(UserAccount).filter(
            UserAccount.user_id == user_id,
            UserAccount.status == AccountStatus.ACTIVE
        )
        
        if account_ids:
            query = query.filter(UserAccount.id.in_(account_ids))
        
        accounts = query.all()
        
        for account in accounts:
            try:
                # 创建MCP服务实例
                service = get_mcp_service(db)
                
                # 刷新帖子
                result = asyncio.run(
                    service.refresh_posts_from_platform(user_id, account.id)
                )
                
                if result.success:
                    sync_result["posts_synced"] += result.posts_synced
                    sync_result["accounts_processed"] += 1
                else:
                    sync_result["errors"].extend(
                        [f"Account {account.id}: {e}" for e in result.errors]
                    )
                    
            except Exception as e:
                error_msg = f"Account {account.id} sync failed: {str(e)}"
                sync_result["errors"].append(error_msg)
                logger.error(error_msg)
        
        sync_task.status = TaskStatus.COMPLETED if sync_result["success"] else TaskStatus.FAILED
        sync_task.completed_at = datetime.utcnow()
        sync_task.result_summary = {
            "posts_synced": sync_result["posts_synced"],
            "accounts_processed": sync_result["accounts_processed"],
            "errors": sync_result["errors"]
        }
        db.commit()
        
    except Exception as e:
        sync_result["success"] = False
        sync_result["errors"].append(str(e))
        logger.error(f"Sync task failed: {e}")
        
        # 更新任务状态
        try:
            db = get_db()
            sync_task = db.query(SyncTask).filter(
                SyncTask.celery_task_id == self.request.id
            ).first()
            if sync_task:
                sync_task.status = TaskStatus.FAILED
                sync_task.error_message = str(e)
                sync_task.retry_count += 1
                db.commit()
        except Exception:
            pass
        
        raise
    
    return sync_result


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    name="services.scheduler.track_heat_trends"
)
def track_heat_trends_task(self, user_id: str, post_ids: List[str] = None):
    """
    追踪帖子热度数据任务
    """
    from .database import get_db
    
    track_result = {
        "success": True,
        "user_id": user_id,
        "posts_tracked": 0,
        "trends": {},
        "errors": [],
        "started_at": datetime.utcnow().isoformat()
    }
    
    try:
        db = get_db()
        
        # 如果没有指定post_ids，获取用户所有已发布的帖子
        if not post_ids:
            posts = db.query(PostHistory).filter(
                and_(
                    PostHistory.user_id == user_id,
                    PostHistory.status == "published"
                )
            ).all()
            post_ids = [p.post_id for p in posts]
        
        # 创建同步任务
        sync_task = SyncTask(
            user_id=user_id,
            task_type="track_heat",
            status=TaskStatus.RUNNING,
            config={"post_ids": post_ids},
            celery_task_id=self.request.id,
            started_at=datetime.utcnow()
        )
        db.add(sync_task)
        db.commit()
        
        service = get_mcp_service(db)
        
        # 分批处理，每批50个
        batch_size = 50
        for i in range(0, len(post_ids), batch_size):
            batch = post_ids[i:i + batch_size]
            
            try:
                result = asyncio.run(
                    service.track_heat_trends(
                        HeatTrendRequest(user_id=user_id, post_ids=batch)
                    )
                )
                
                for post_id, data in result.trends.items():
                    if "error" not in data:
                        track_result["posts_tracked"] += 1
                    track_result["trends"][post_id] = data
                    
            except Exception as e:
                error_msg = f"Batch {i//batch_size + 1} tracking failed: {str(e)}"
                track_result["errors"].append(error_msg)
        
        sync_task.status = TaskStatus.COMPLETED
        sync_task.completed_at = datetime.utcnow()
        sync_task.result_summary = {
            "posts_tracked": track_result["posts_tracked"],
            "trends": track_result["trends"],
            "errors": track_result["errors"]
        }
        db.commit()
        
    except Exception as e:
        track_result["success"] = False
        track_result["errors"].append(str(e))
        logger.error(f"Heat tracking failed: {e}")
        
        try:
            db = get_db()
            sync_task = db.query(SyncTask).filter(
                SyncTask.celery_task_id == self.request.id
            ).first()
            if sync_task:
                sync_task.status = TaskStatus.FAILED
                sync_task.error_message = str(e)
                sync_task.retry_count += 1
                db.commit()
        except Exception:
            pass
        
        raise
    
    return track_result


@shared_task(
    bind=True,
    max_retries=1,
    name="services.scheduler.check_expired_cookies"
)
def check_expired_cookies_task(self):
    """
    检查并通知过期Cookies任务
    """
    from .database import get_db
    
    check_result = {
        "accounts_checked": 0,
        "expired": [],
        "expiring_soon": [],
        "notifications_sent": 0
    }
    
    try:
        db = get_db()
        threshold = datetime.utcnow() + timedelta(days=7)  # 7天内过期
        
        # 检查过期账号
        expired_accounts = db.query(UserAccount).filter(
            and_(
                UserAccount.cookie_expires_at < datetime.utcnow(),
                UserAccount.status == AccountStatus.ACTIVE
            )
        ).all()
        
        for account in expired_accounts:
            account.status = AccountStatus.EXPIRED
            
            # 发送通知
            notification = ErrorNotification(
                user_id=account.user_id,
                error_type="cookie_expired",
                message=f"账号 {account.account_name} 的登录已过期，请重新绑定",
                account_id=account.id
            )
            db.add(notification)
            check_result["expired"].append({
                "account_id": account.id,
                "account_name": account.account_name,
                "user_id": account.user_id
            })
            check_result["notifications_sent"] += 1
        
        # 检查即将过期账号
        expiring_accounts = db.query(UserAccount).filter(
            and_(
                UserAccount.cookie_expires_at <= threshold,
                UserAccount.cookie_expires_at > datetime.utcnow(),
                UserAccount.status == AccountStatus.ACTIVE
            )
        ).all()
        
        for account in expiring_accounts:
            notification = ErrorNotification(
                user_id=account.user_id,
                error_type="cookie_expiring_soon",
                message=f"账号 {account.account_name} 将在7天内过期，请及时处理",
                account_id=account.id
            )
            db.add(notification)
            check_result["expiring_soon"].append({
                "account_id": account.id,
                "account_name": account.account_name,
                "expires_at": account.cookie_expires_at.isoformat()
            })
            check_result["notifications_sent"] += 1
        
        check_result["accounts_checked"] = (
            len(expired_accounts) + len(expiring_accounts)
        )
        
        db.commit()
        logger.info(f"Cookie check completed: {check_result}")
        
    except Exception as e:
        logger.error(f"Cookie check failed: {e}")
        raise
    
    return check_result


@shared_task(
    bind=True,
    name="services.scheduler.cleanup_failed_tasks"
)
def cleanup_failed_tasks_task(self, days: int = 7):
    """
    清理失败的同步任务
    """
    from .database import get_db
    
    cleanup_result = {
        "tasks_cleaned": 0,
        "oldest_date": None
    }
    
    try:
        db = get_db()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 删除或归档旧的任务
        old_tasks = db.query(SyncTask).filter(
            and_(
                SyncTask.status == TaskStatus.FAILED,
                SyncTask.created_at < cutoff_date
            )
        ).all()
        
        for task in old_tasks:
            # 软删除：标记为已清理
            task.status = TaskStatus.FAILED
            task.error_message = f"[CLEANUP] {task.error_message or ''}"
        
        cleanup_result["tasks_cleaned"] = len(old_tasks)
        cleanup_result["oldest_date"] = cutoff_date.isoformat()
        
        db.commit()
        logger.info(f"Cleanup completed: {cleanup_result}")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise
    
    return cleanup_result


# ============ 便捷调度函数 ============

def schedule_user_sync(user_id: str, account_ids: List[int] = None, 
                       sync_posts: bool = True, track_heat: bool = True):
    """
    为用户安排同步任务
    """
    tasks = []
    
    if sync_posts:
        task = sync_user_posts_task.delay(user_id, account_ids)
        tasks.append({
            "type": "sync_posts",
            "task_id": task.id,
            "status": "queued"
        })
    
    if track_heat:
        task = track_heat_trends_task.delay(user_id)
        tasks.append({
            "type": "track_heat",
            "task_id": task.id,
            "status": "queued"
        })
    
    return tasks


def schedule_periodic_sync(config: SyncConfig):
    """
    安排周期性同步（通过Celery Beat）
    """
    # Celery Beat会自动按配置的间隔执行任务
    # 这里可以返回配置信息供前端展示
    return {
        "user_id": config.user_id,
        "sync_interval": config.sync_interval_minutes,
        "heat_check_interval": config.heat_check_interval_minutes,
        "enabled_accounts": config.account_ids
    }


def get_task_status(task_ids: List[str]) -> Dict[str, Dict]:
    """
    获取任务状态
    """
    from .database import get_db
    
    db = get_db()
    results = {}
    
    for task_id in task_ids:
        try:
            async_result = celery_app.AsyncResult(task_id)
            results[task_id] = {
                "status": async_result.status,
                "result": async_result.result if async_result.ready() else None,
                "info": str(async_result.info) if async_result.info else None
            }
        except Exception as e:
            results[task_id] = {
                "status": "error",
                "error": str(e)
            }
    
    return results


# ============ 异常通知处理 ============

def send_alert_notification(user_id: str, alert_type: str, 
                           message: str, severity: str = "warning"):
    """
    发送告警通知
    """
    from .database import get_db
    
    db = get_db()
    
    notification = ErrorNotification(
        user_id=user_id,
        error_type=alert_type,
        message=message
    )
    db.add(notification)
    db.commit()
    
    # TODO: 集成实际的通知渠道
    # - 邮件通知
    # - Webhook回调
    # - 站内消息
    # - 短信/电话（严重级别）
    
    logger.warning(
        f"Alert sent: [{severity}] {alert_type} to user {user_id}: {message}"
    )
    
    return notification.id


# ============ 任务日志查询 ============

def get_sync_task_history(db: Session, user_id: str, 
                          limit: int = 50) -> List[Dict]:
    """
    获取用户的同步任务历史
    """
    tasks = db.query(SyncTask).filter(
        SyncTask.user_id == user_id
    ).order_by(SyncTask.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": t.id,
            "task_type": t.task_type,
            "status": t.status,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "retry_count": t.retry_count,
            "result_summary": t.result_summary
        }
        for t in tasks
    ]


# ============ Beat Schedule 管理 ============

def get_beat_schedule() -> Dict:
    """
    获取当前Celery Beat调度配置
    """
    inspect = celery_app.control.inspect()
    schedule = inspect.scheduled()
    stats = inspect.stats()
    
    return {
        "scheduled": schedule or {},
        "active": stats or {}
    }
