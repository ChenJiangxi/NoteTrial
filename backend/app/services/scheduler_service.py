"""
定时发布服务
定时发布内容、任务管理、发布通知
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from uuid import uuid4
import httpx

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from .config import get_settings
from .mcp_service import MCPService, get_mcp_service

logger = logging.getLogger(__name__)
settings = get_settings()


class ScheduledPostStatus(str, Enum):
    """定时发布状态"""
    PENDING = "pending"      # 待发布
    SCHEDULED = "scheduled"  # 已安排
    PROCESSING = "processing" # 处理中
    PUBLISHED = "published"  # 已发布
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消


class SchedulerTaskStatus(str, Enum):
    """调度任务状态"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============ Models ============

class ScheduledPost:
    """定时发布记录"""
    def __init__(self, content_id: str, scheduled_at: datetime, status: str = "pending", 
                 task_id: str = None, account_id: int = None, user_id: str = None):
        self.id = str(uuid4())
        self.content_id = content_id
        self.scheduled_at = scheduled_at
        self.status = status
        self.task_id = task_id
        self.account_id = account_id
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.published_at = None
        self.result = None
        self.error_message = None


class SchedulerTask:
    """调度任务"""
    def __init__(self, task_type: str, run_at: datetime, status: str = "pending", 
                 payload: Dict = None):
        self.id = str(uuid4())
        self.task_type = task_type
        self.run_at = run_at
        self.status = status
        self.payload = payload or {}
        self.result = None
        self.error = None
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None


# ============ 存储管理 ============

class SchedulerStorage:
    """调度任务存储（内存实现，可替换为数据库）"""
    
    def __init__(self):
        self._posts: Dict[str, ScheduledPost] = {}
        self._tasks: Dict[str, SchedulerTask] = {}
    
    def create_post(self, post: ScheduledPost) -> ScheduledPost:
        """创建定时发布记录"""
        self._posts[post.id] = post
        return post
    
    def get_post(self, post_id: str) -> Optional[ScheduledPost]:
        """获取定时发布记录"""
        return self._posts.get(post_id)
    
    def update_post(self, post_id: str, **kwargs) -> Optional[ScheduledPost]:
        """更新定时发布记录"""
        post = self._posts.get(post_id)
        if post:
            for key, value in kwargs.items():
                setattr(post, key, value)
            post.updated_at = datetime.utcnow()
        return post
    
    def delete_post(self, post_id: str) -> bool:
        """删除定时发布记录"""
        if post_id in self._posts:
            del self._posts[post_id]
            return True
        return False
    
    def list_posts(self, user_id: str = None, status: str = None) -> List[ScheduledPost]:
        """列出定时发布记录"""
        posts = list(self._posts.values())
        if user_id:
            posts = [p for p in posts if p.user_id == user_id]
        if status:
            posts = [p for p in posts if p.status == status]
        return sorted(posts, key=lambda x: x.scheduled_at)
    
    def create_task(self, task: SchedulerTask) -> SchedulerTask:
        """创建调度任务"""
        self._tasks[task.id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[SchedulerTask]:
        """获取调度任务"""
        return self._tasks.get(task_id)
    
    def update_task(self, task_id: str, **kwargs) -> Optional[SchedulerTask]:
        """更新调度任务"""
        task = self._tasks.get(task_id)
        if task:
            for key, value in kwargs.items():
                setattr(task, key, value)
            if kwargs.get("status") == "running" and not task.started_at:
                task.started_at = datetime.utcnow()
            if kwargs.get("status") in ["completed", "failed"]:
                task.completed_at = datetime.utcnow()
        return task
    
    def list_tasks(self, status: str = None, task_type: str = None) -> List[SchedulerTask]:
        """列出调度任务"""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        return sorted(tasks, key=lambda x: x.run_at)
    
    def delete_task(self, task_id: str) -> bool:
        """删除调度任务"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False


# ============ Celery 任务定义 ============

# Celery 应用配置
try:
    from celery import Celery
    
    celery_app = Celery(
        'scheduler',
        broker=settings.celery_broker_url or 'redis://localhost:6379/0',
        backend=settings.celery_result_backend or 'redis://localhost:6379/0'
    )
    
    celery_app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Asia/Shanghai',
        enable_utc=True,
        beat_schedule={}
    )
    
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logger.warning("Celery not available, using mock implementation")


# ============ Celery 任务函数 ============

if CELERY_AVAILABLE:
    
    @celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
    def execute_scheduled_publish(self, post_id: str, content_id: str, 
                                   account_id: int, user_id: str):
        """执行定时发布 Celery 任务"""
        from .scheduler_service import scheduler_service
        
        try:
            logger.info(f"Executing scheduled publish: post_id={post_id}")
            
            # 异步执行发布
            result = asyncio.run(
                scheduler_service._execute_publish(
                    post_id=post_id,
                    content_id=content_id,
                    account_id=account_id,
                    user_id=user_id
                )
            )
            
            return {"success": True, "result": result}
            
        except Exception as e:
            logger.error(f"Scheduled publish failed: {e}")
            self.retry(exc=e)
    
    @celery_app.task(bind=True)
    def send_notification_task(self, notification_type: str, user_id: str, 
                               data: Dict, channel: str = "telegram"):
        """发送通知 Celery 任务"""
        from .scheduler_service import scheduler_service
        
        try:
            asyncio.run(
                scheduler_service._send_notification(
                    notification_type, user_id, data, channel
                )
            )
            return {"success": True}
        except Exception as e:
            logger.error(f"Notification failed: {e}")
            return {"success": False, "error": str(e)}


# ============ 通知服务 ============

class NotificationService:
    """通知服务"""
    
    async def send_success_notification(self, user_id: str, post_id: str, 
                                        platform: str = "telegram") -> bool:
        """发送发布成功通知"""
        message = f"✅ 内容发布成功！\n\nPost ID: {post_id}"
        return await self._send_to_channel(user_id, message, channel)
    
    async def send_failure_notification(self, user_id: str, post_id: str, 
                                        error: str, platform: str = "telegram") -> bool:
        """发送发布失败通知"""
        message = f"❌ 内容发布失败！\n\nPost ID: {post_id}\n错误: {error}"
        return await self._send_to_channel(user_id, message, channel)
    
    async def send_reminder_notification(self, user_id: str, post_id: str,
                                          scheduled_at: datetime, 
                                          platform: str = "telegram") -> bool:
        """发送即将发布提醒"""
        time_str = scheduled_at.strftime("%Y-%m-%d %H:%M:%S")
        message = f"⏰ 发布提醒\n\n您的内容将在 {time_str} 发布\n\nPost ID: {post_id}"
        return await self._send_to_channel(user_id, message, channel)
    
    async def _send_to_channel(self, user_id: str, message: str, 
                                channel: str = "telegram") -> bool:
        """发送到指定渠道"""
        try:
            # TODO: 集成实际的通知渠道
            # 使用消息服务发送
            if channel == "telegram":
                # 调用Telegram服务
                logger.info(f"Sending telegram notification to {user_id}: {message}")
                return True
            elif channel == "email":
                # 调用邮件服务
                logger.info(f"Sending email notification to {user_id}")
                return True
            else:
                logger.warning(f"Unknown notification channel: {channel}")
                return False
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False


# ============ SchedulerService 主服务 ============

class SchedulerService:
    """定时发布服务"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.storage = SchedulerStorage()
        self.notification_service = NotificationService()
        self._mcp_service: Optional[MCPService] = None
        self._task_scheduler_lock = asyncio.Lock()
        self._scheduler_task: Optional[asyncio.Task] = None
    
    def _get_mcp_service(self) -> MCPService:
        """获取MCP服务实例"""
        if self._mcp_service is None:
            self._mcp_service = get_mcp_service(self.db)
        return self._mcp_service
    
    # ============ 定时发布管理 ============
    
    async def schedule_post(self, user_id: str, content_id: str, 
                           scheduled_at: datetime, account_id: int,
                           publish_data: Dict) -> Dict:
        """
        安排定时发布
        
        Args:
            user_id: 用户ID
            content_id: 内容ID
            scheduled_at: 计划发布时间
            account_id: 账号ID
            publish_data: 发布数据（标题、内容、图片等）
        
        Returns:
            Dict: 任务状态
        """
        now = datetime.utcnow()
        min_time = now + timedelta(hours=1)
        max_time = now + timedelta(days=14)
        
        # 验证发布时间
        if scheduled_at < min_time:
            return {
                "success": False,
                "error": "发布时间必须至少在1小时之后"
            }
        
        if scheduled_at > max_time:
            return {
                "success": False,
                "error": "发布时间不能超过14天"
            }
        
        # 创建定时发布记录
        post = ScheduledPost(
            content_id=content_id,
            scheduled_at=scheduled_at,
            status=ScheduledPostStatus.SCHEDULED.value,
            account_id=account_id,
            user_id=user_id
        )
        
        # 创建调度任务
        task = SchedulerTask(
            task_type="publish",
            run_at=scheduled_at,
            status=SchedulerTaskStatus.SCHEDULED.value,
            payload={
                "post_id": post.id,
                "content_id": content_id,
                "account_id": account_id,
                "user_id": user_id,
                "publish_data": publish_data
            }
        )
        
        post.task_id = task.id
        
        # 保存到存储
        self.storage.create_post(post)
        self.storage.create_task(task)
        
        # 创建Celery定时任务
        if CELERY_AVAILABLE:
            self._schedule_celery_task(task)
        
        # 设置内部调度器
        await self._schedule_internal_task(task)
        
        # 发送确认通知
        await self.notification_service.send_reminder_notification(
            user_id, post.id, scheduled_at
        )
        
        return {
            "success": True,
            "post_id": post.id,
            "task_id": task.id,
            "scheduled_at": scheduled_at.isoformat(),
            "status": post.status,
            "message": "定时发布已安排"
        }
    
    def _schedule_celery_task(self, task: SchedulerTask):
        """安排Celery任务"""
        try:
            delay_seconds = (task.run_at - datetime.utcnow()).total_seconds()
            if delay_seconds > 0:
                execute_scheduled_publish.apply_async(
                    args=[
                        task.payload.get("post_id"),
                        task.payload.get("content_id"),
                        task.payload.get("account_id"),
                        task.payload.get("user_id")
                    ],
                    countdown=delay_seconds
                )
                logger.info(f"Celery task scheduled: {task.id}")
        except Exception as e:
            logger.error(f"Failed to schedule Celery task: {e}")
    
    async def _schedule_internal_task(self, task: SchedulerTask):
        """安排内部异步任务（Celery不可用时的备选）"""
        async with self._task_scheduler_lock:
            if self._scheduler_task is None or self._scheduler_task.done():
                self._scheduler_task = asyncio.create_task(self._run_scheduler())
    
    async def _run_scheduler(self):
        """运行调度器"""
        logger.info("Scheduler task started")
        while True:
            try:
                now = datetime.utcnow()
                
                # 检查待执行任务
                tasks = self.storage.list_tasks(status=SchedulerTaskStatus.SCHEDULED.value)
                
                for task in tasks:
                    if task.run_at <= now:
                        await self._execute_task(task)
                
                # 发送即将执行任务的提醒
                await self._send_upcoming_reminders()
                
                await asyncio.sleep(10)  # 每10秒检查一次
                
            except asyncio.CancelledError:
                logger.info("Scheduler task cancelled")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)  # 出错后等待60秒
    
    async def _execute_task(self, task: SchedulerTask):
        """执行任务"""
        self.storage.update_task(task.id, status=SchedulerTaskStatus.RUNNING.value)
        
        try:
            if task.task_type == "publish":
                await self._execute_publish(
                    post_id=task.payload.get("post_id"),
                    content_id=task.payload.get("content_id"),
                    account_id=task.payload.get("account_id"),
                    user_id=task.payload.get("user_id"),
                    publish_data=task.payload.get("publish_data")
                )
            
            self.storage.update_task(task.id, status=SchedulerTaskStatus.COMPLETED.value)
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            self.storage.update_task(task.id, status=SchedulerTaskStatus.FAILED.value, error=str(e))
            
            # 发送失败通知
            await self.notification_service.send_failure_notification(
                task.payload.get("user_id"),
                task.payload.get("post_id"),
                str(e)
            )
    
    async def _execute_publish(self, post_id: str, content_id: str,
                               account_id: int, user_id: str,
                               publish_data: Dict = None) -> Dict:
        """执行发布"""
        post = self.storage.get_post(post_id)
        if not post:
            raise ValueError(f"Post not found: {post_id}")
        
        # 更新状态
        self.storage.update_post(post_id, status=ScheduledPostStatus.PROCESSING.value)
        
        try:
            mcp_service = self._get_mcp_service()
            
            # 调用MCP服务发布内容
            result = await mcp_service.publish_content(
                request=type('PostCreateRequest', (), {
                    'user_id': user_id,
                    'account_id': account_id,
                    'title': publish_data.get('title', ''),
                    'content': publish_data.get('content', ''),
                    'images': publish_data.get('images', []),
                    'tags': publish_data.get('tags', [])
                })()
            )
            
            if result.success:
                self.storage.update_post(
                    post_id,
                    status=ScheduledPostStatus.PUBLISHED.value,
                    published_at=datetime.utcnow(),
                    result=result.to_dict() if hasattr(result, 'to_dict') else {"post_id": result.post_id}
                )
                
                # 发送成功通知
                await self.notification_service.send_success_notification(
                    user_id, post_id
                )
                
                return {"success": True, "post_id": result.post_id}
            else:
                raise Exception(result.message or "发布失败")
                
        except Exception as e:
            logger.error(f"Publish execution failed: {e}")
            self.storage.update_post(
                post_id,
                status=ScheduledPostStatus.FAILED.value,
                error_message=str(e)
            )
            raise
    
    async def _send_upcoming_reminders(self):
        """发送即将发布提醒（提前1小时）"""
        now = datetime.utcnow()
        reminder_time = now + timedelta(minutes=55)  # 提前55分钟发送
        
        posts = self.storage.list_posts(status=ScheduledPostStatus.SCHEDULED.value)
        
        for post in posts:
            if post.scheduled_at <= reminder_time and post.scheduled_at > now:
                # 避免重复发送提醒
                if not getattr(post, 'reminder_sent', False):
                    await self.notification_service.send_reminder_notification(
                        post.user_id, post.id, post.scheduled_at
                    )
                    self.storage.update_post(post.id, reminder_sent=True)
    
    # ============ 任务管理 ============
    
    def list_tasks(self, user_id: str = None, status: str = None) -> List[Dict]:
        """查询任务列表"""
        posts = self.storage.list_posts(user_id=user_id, status=status)
        
        return [
            {
                "post_id": p.id,
                "content_id": p.content_id,
                "scheduled_at": p.scheduled_at.isoformat(),
                "status": p.status,
                "task_id": p.task_id,
                "account_id": p.account_id,
                "user_id": p.user_id,
                "created_at": p.created_at.isoformat(),
                "published_at": p.published_at.isoformat() if p.published_at else None,
                "result": p.result,
                "error_message": p.error_message
            }
            for p in posts
        ]
    
    def get_task(self, post_id: str) -> Optional[Dict]:
        """获取任务详情"""
        post = self.storage.get_post(post_id)
        if not post:
            return None
        
        return {
            "post_id": post.id,
            "content_id": post.content_id,
            "scheduled_at": post.scheduled_at.isoformat(),
            "status": post.status,
            "task_id": post.task_id,
            "account_id": post.account_id,
            "user_id": post.user_id,
            "created_at": post.created_at.isoformat(),
            "published_at": post.published_at.isoformat() if post.published_at else None,
            "result": post.result,
            "error_message": post.error_message
        }
    
    async def cancel_task(self, post_id: str) -> Dict:
        """取消任务"""
        post = self.storage.get_post(post_id)
        if not post:
            return {"success": False, "error": "任务不存在"}
        
        if post.status in [ScheduledPostStatus.PUBLISHED.value, 
                          ScheduledPostStatus.CANCELLED.value]:
            return {"success": False, "error": f"任务状态不允许取消: {post.status}"}
        
        # 取消Celery任务
        if CELERY_AVAILABLE and post.task_id:
            try:
                celery_app.control.revoke(post.task_id, terminate=True)
            except Exception as e:
                logger.warning(f"Failed to revoke Celery task: {e}")
        
        # 更新状态
        self.storage.update_post(post_id, status=ScheduledPostStatus.CANCELLED.value)
        
        if post.task_id:
            self.storage.update_task(post.task_id, status=SchedulerTaskStatus.CANCELLED.value)
        
        return {
            "success": True,
            "message": "任务已取消",
            "post_id": post_id
        }
    
    async def reschedule_task(self, post_id: str, new_scheduled_at: datetime) -> Dict:
        """修改发布时间"""
        post = self.storage.get_post(post_id)
        if not post:
            return {"success": False, "error": "任务不存在"}
        
        if post.status not in [ScheduledPostStatus.SCHEDULED.value, 
                             ScheduledPostStatus.PENDING.value]:
            return {"success": False, "error": f"任务状态不允许修改: {post.status}"}
        
        now = datetime.utcnow()
        min_time = now + timedelta(hours=1)
        max_time = now + timedelta(days=14)
        
        # 验证新发布时间
        if new_scheduled_at < min_time:
            return {
                "success": False,
                "error": "发布时间必须至少在1小时之后"
            }
        
        if new_scheduled_at > max_time:
            return {
                "success": False,
                "error": "发布时间不能超过14天"
            }
        
        # 更新任务
        self.storage.update_post(post_id, scheduled_at=new_scheduled_at)
        
        if post.task_id:
            self.storage.update_task(post.task_id, run_at=new_scheduled_at)
            
            # 重新安排Celery任务
            if CELERY_AVAILABLE:
                self._schedule_celery_task(
                    self.storage.get_task(post.task_id)
                )
        
        return {
            "success": True,
            "message": "发布时间已更新",
            "post_id": post_id,
            "new_scheduled_at": new_scheduled_at.isoformat()
        }
    
    def delete_task(self, post_id: str) -> Dict:
        """删除任务"""
        post = self.storage.get_post(post_id)
        if not post:
            return {"success": False, "error": "任务不存在"}
        
        if post.status == ScheduledPostStatus.PUBLISHED.value:
            return {"success": False, "error": "已发布的任务不能删除"}
        
        # 删除Celery任务
        if CELERY_AVAILABLE and post.task_id:
            try:
                celery_app.control.revoke(post.task_id, terminate=True)
            except Exception as e:
                logger.warning(f"Failed to revoke Celery task: {e}")
        
        # 删除任务
        self.storage.delete_post(post_id)
        if post.task_id:
            self.storage.delete_task(post.task_id)
        
        return {
            "success": True,
            "message": "任务已删除",
            "post_id": post_id
        }
    
    # ============ 通知功能 ============
    
    async def _send_notification(self, notification_type: str, user_id: str,
                                  data: Dict, channel: str = "telegram"):
        """发送通知"""
        if notification_type == "success":
            await self.notification_service.send_success_notification(
                user_id, data.get("post_id", ""), channel
            )
        elif notification_type == "failure":
            await self.notification_service.send_failure_notification(
                user_id, data.get("post_id", ""), data.get("error", ""), channel
            )
        elif notification_type == "reminder":
            await self.notification_service.send_reminder_notification(
                user_id, data.get("post_id", ""), 
                datetime.fromisoformat(data.get("scheduled_at")), channel
            )
    
    async def send_custom_notification(self, user_id: str, message: str,
                                      channel: str = "telegram") -> bool:
        """发送自定义通知"""
        return await self.notification_service._send_to_channel(
            user_id, message, channel
        )
    
    # ============ 统计信息 ============
    
    def get_statistics(self, user_id: str = None) -> Dict:
        """获取统计信息"""
        posts = self.storage.list_posts(user_id=user_id)
        
        stats = {
            "total": len(posts),
            "pending": 0,
            "scheduled": 0,
            "processing": 0,
            "published": 0,
            "failed": 0,
            "cancelled": 0
        }
        
        for post in posts:
            status_key = post.status
            if status_key in stats:
                stats[status_key] += 1
        
        stats["success_rate"] = (
            stats["published"] / stats["total"] * 100 
            if stats["total"] > 0 else 0
        )
        
        return stats
    
    def shutdown(self):
        """关闭服务"""
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
        if self._mcp_service:
            asyncio.run(self._mcp_service.close())


# ============ API 端点 ============

# FastAPI 路由定义（需要配合 main.py 使用）

def setup_scheduler_routes(app):
    """设置调度器路由"""
    from fastapi import APIRouter, HTTPException, Depends
    
    router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])
    
    def get_db():
        from .database import get_db
        db = next(get_db())
        try:
            yield db
        finally:
            db.close()
    
    def get_scheduler(db=Depends(get_db)):
        return SchedulerService(db)
    
    @router.post("/schedule")
    async def schedule_post_endpoint(
        request: dict,
        scheduler: SchedulerService = Depends(get_scheduler)
    ):
        """
        POST /api/v1/scheduler/schedule
        
        请求体:
        {
            "user_id": "用户ID",
            "content_id": "内容ID",
            "scheduled_at": "2024-01-01T12:00:00Z",
            "account_id": 1,
            "publish_data": {
                "title": "标题",
                "content": "内容",
                "images": ["url1", "url2"],
                "tags": ["标签1", "标签2"]
            }
        }
        """
        from datetime import datetime
        
        scheduled_at = datetime.fromisoformat(request["scheduled_at"].replace("Z", "+00:00"))
        
        result = await scheduler.schedule_post(
            user_id=request["user_id"],
            content_id=request["content_id"],
            scheduled_at=scheduled_at,
            account_id=request["account_id"],
            publish_data=request.get("publish_data", {})
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result)
        
        return result
    
    @router.get("/tasks")
    def list_tasks_endpoint(
        user_id: str = None,
        status: str = None,
        scheduler: SchedulerService = Depends(get_scheduler)
    ):
        """
        GET /api/v1/scheduler/tasks
        
        查询参数:
        - user_id: 用户ID（可选）
        - status: 状态筛选（可选）
        """
        return {
            "tasks": scheduler.list_tasks(user_id=user_id, status=status),
            "total": len(scheduler.list_tasks(user_id=user_id, status=status))
        }
    
    @router.delete("/tasks/{post_id}")
    async def delete_task_endpoint(
        post_id: str,
        scheduler: SchedulerService = Depends(get_scheduler)
    ):
        """
        DELETE /api/v1/scheduler/tasks/{post_id}
        """
        result = scheduler.delete_task(post_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    
    @router.post("/tasks/{post_id}/cancel")
    async def cancel_task_endpoint(
        post_id: str,
        scheduler: SchedulerService = Depends(get_scheduler)
    ):
        """
        POST /api/v1/scheduler/tasks/{post_id}/cancel
        """
        result = await scheduler.cancel_task(post_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    
    @router.put("/tasks/{post_id}/reschedule")
    async def reschedule_task_endpoint(
        post_id: str,
        request: dict,
        scheduler: SchedulerService = Depends(get_scheduler)
    ):
        """
        PUT /api/v1/scheduler/tasks/{post_id}/reschedule
        
        请求体:
        {
            "scheduled_at": "2024-01-01T15:00:00Z"
        }
        """
        from datetime import datetime
        
        new_scheduled_at = datetime.fromisoformat(
            request["scheduled_at"].replace("Z", "+00:00")
        )
        
        result = await scheduler.reschedule_task(post_id, new_scheduled_at)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    
    @router.get("/tasks/{post_id}")
    def get_task_endpoint(
        post_id: str,
        scheduler: SchedulerService = Depends(get_scheduler)
    ):
        """
        GET /api/v1/scheduler/tasks/{post_id}
        """
        task = scheduler.get_task(post_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return task
    
    @router.get("/statistics")
    def get_statistics_endpoint(
        user_id: str = None,
        scheduler: SchedulerService = Depends(get_scheduler)
    ):
        """
        GET /api/v1/scheduler/statistics
        """
        return scheduler.get_statistics(user_id=user_id)
    
    app.include_router(router)
    
    return router


# ============ 服务工厂 ============

_scheduler_service_instance: Optional[SchedulerService] = None

def get_scheduler_service(db_session: Session) -> SchedulerService:
    """获取调度服务实例"""
    global _scheduler_service_instance
    if _scheduler_service_instance is None:
        _scheduler_service_instance = SchedulerService(db_session)
    return _scheduler_service_instance


# 全局服务实例（用于Celery任务）
scheduler_service: Optional[SchedulerService] = None

def init_scheduler_service(db_session: Session):
    """初始化全局调度服务实例"""
    global scheduler_service
    scheduler_service = SchedulerService(db_session)
    return scheduler_service
