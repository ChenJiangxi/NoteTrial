"""
MCP 集成服务
多用户 cookies 管理、账号绑定、内容发布、帖子列表、热度追踪
"""
import json
import hashlib
import hmac
import base64
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from functools import wraps
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from .models.mcp_models import (
    UserAccount, PostHistory, SyncTask,
    AccountBindRequest, AccountBindResponse,
    PostCreateRequest, PostCreateResponse,
    PostListRequest, PostListResponse,
    HeatTrendRequest, HeatTrendResponse,
    SyncConfig, SyncResult, ErrorNotification,
    AccountStatus, SyncStatus, TaskStatus
)
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ============ 加密工具 ============

def encrypt_cookies(cookies: str, key: str = settings.secret_key) -> str:
    """加密Cookies"""
    if not key:
        return base64.b64encode(cookies.encode()).decode()
    encrypted = hmac.new(
        key.encode(), 
        cookies.encode(), 
        hashlib.sha256
    ).hexdigest()
    return f"{encrypted}:{base64.b64encode(cookies.encode()).decode()}"


def decrypt_cookies(encrypted: str, key: str = settings.secret_key) -> str:
    """解密Cookies"""
    try:
        if ':' not in encrypted:
            return base64.b64decode(encrypted.encode()).decode()
        _, b64_data = encrypted.split(':', 1)
        return base64.b64decode(b64_data.encode()).decode()
    except Exception as e:
        logger.error(f"Cookie decryption failed: {e}")
        raise ValueError("Invalid encrypted cookies")


# ============ 错误重试装饰器 ============

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """错误重试装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            raise last_exception
        return wrapper
    return decorator


# ============ MCP 客户端 ============

class MCPClient:
    """MCP协议客户端"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.xiaohongshu_mcp_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """发送MCP请求"""
        url = f"{self.base_url}/{endpoint}"
        response = await self.client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    # 账号相关
    async def verify_cookies(self, cookies: str) -> Dict:
        """验证Cookies有效性"""
        return await self.request("POST", "api/account/verify", json={"cookies": cookies})
    
    async def get_account_info(self, cookies: str) -> Dict:
        """获取账号信息"""
        return await self.request("POST", "api/account/info", json={"cookies": cookies})
    
    # 内容相关
    async def publish_note(self, cookies: str, title: str, content: str, 
                          images: List[str] = None, tags: List[str] = None) -> Dict:
        """发布笔记"""
        return await self.request("POST", "api/note/publish", json={
            "cookies": cookies,
            "title": title,
            "content": content,
            "images": images or [],
            "tags": tags or []
        })
    
    async def get_notes_list(self, cookies: str, page: int = 1, limit: int = 20) -> Dict:
        """获取笔记列表"""
        return await self.request("POST", "api/notes/list", json={
            "cookies": cookies,
            "page": page,
            "limit": limit
        })
    
    async def get_note_detail(self, cookies: str, note_id: str) -> Dict:
        """获取笔记详情"""
        return await self.request("POST", "api/note/detail", json={
            "cookies": cookies,
            "note_id": note_id
        })
    
    async def get_note_stats(self, cookies: str, note_id: str) -> Dict:
        """获取笔记热度数据"""
        return await self.request("POST", "api/note/stats", json={
            "cookies": cookies,
            "note_id": note_id
        })


# ============ MCP 服务 ============

class MCPService:
    """MCP集成服务 - 主服务类"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.mcp_client = MCPClient()
        self._user_cache: Dict[str, Dict] = {}  # 用户会话缓存
    
    async def close(self):
        await self.mcp_client.close()
    
    # ============ 账号管理 ============
    
    async def bind_account(self, request: AccountBindRequest) -> AccountBindResponse:
        """绑定用户账号"""
        try:
            # 验证Cookies有效性
            verify_result = await self.mcp_client.verify_cookies(request.cookies)
            if not verify_result.get("valid"):
                return AccountBindResponse(
                    success=False,
                    message="Cookies已失效，请重新登录"
                )
            
            # 加密存储
            encrypted_cookies = encrypt_cookies(request.cookies)
            
            # 获取账号信息
            account_info = await self.mcp_client.get_account_info(request.cookies)
            
            # 检查是否已存在该用户的相同账号
            existing = self.db.query(UserAccount).filter(
                and_(
                    UserAccount.user_id == request.user_id,
                    UserAccount.platform == request.platform
                )
            ).first()
            
            if existing:
                # 更新现有账号
                existing.cookies = encrypted_cookies
                existing.cookie_expires_at = datetime.utcnow() + timedelta(days=30)
                existing.last_login_at = datetime.utcnow()
                existing.status = AccountStatus.ACTIVE
                self.db.commit()
                account_id = existing.id
                message = "账号信息已更新"
            else:
                # 创建新账号
                account = UserAccount(
                    user_id=request.user_id,
                    platform=request.platform,
                    account_name=request.account_name or account_info.get("nickname", "未命名"),
                    cookies=encrypted_cookies,
                    cookie_expires_at=datetime.utcnow() + timedelta(days=30),
                    last_login_at=datetime.utcnow(),
                    status=AccountStatus.ACTIVE
                )
                self.db.add(account)
                self.db.commit()
                account_id = account.id
                message = "账号绑定成功"
            
            return AccountBindResponse(
                success=True,
                account_id=account_id,
                message=message,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            
        except Exception as e:
            logger.error(f"Account binding failed: {e}")
            return AccountBindResponse(
                success=False,
                message=f"绑定失败: {str(e)}"
            )
    
    def get_user_accounts(self, user_id: str) -> List[Dict]:
        """获取用户的账号列表"""
        accounts = self.db.query(UserAccount).filter(
            UserAccount.user_id == user_id
        ).all()
        
        return [
            {
                "id": acc.id,
                "platform": acc.platform,
                "account_name": acc.account_name,
                "status": acc.status,
                "total_posts": acc.total_posts,
                "success_rate": acc.success_rate,
                "last_login_at": acc.last_login_at.isoformat() if acc.last_login_at else None
            }
            for acc in accounts
        ]
    
    def unbind_account(self, user_id: str, account_id: int) -> bool:
        """解绑账号"""
        account = self.db.query(UserAccount).filter(
            and_(
                UserAccount.id == account_id,
                UserAccount.user_id == user_id
            )
        ).first()
        
        if not account:
            return False
        
        self.db.delete(account)
        self.db.commit()
        return True
    
    # ============ 内容发布 ============
    
    @retry_on_failure(max_retries=3, delay=2.0)
    async def publish_content(self, request: PostCreateRequest) -> PostCreateResponse:
        """发布内容"""
        try:
            # 获取账号
            account = self.db.query(UserAccount).filter(
                and_(
                    UserAccount.id == request.account_id,
                    UserAccount.user_id == request.user_id
                )
            ).first()
            
            if not account:
                return PostCreateResponse(
                    success=False,
                    message="账号不存在或无权限"
                )
            
            if account.status != AccountStatus.ACTIVE:
                return PostCreateResponse(
                    success=False,
                    message=f"账号状态异常: {account.status}"
                )
            
            # 解密Cookies
            cookies = decrypt_cookies(account.cookies)
            
            # 发布笔记
            result = await self.mcp_client.publish_note(
                cookies=cookies,
                title=request.title,
                content=request.content,
                images=request.images,
                tags=request.tags
            )
            
            if result.get("success"):
                # 创建帖子记录
                post = PostHistory(
                    user_id=request.user_id,
                    account_id=request.account_id,
                    post_id=result.get("note_id"),
                    title=request.title,
                    content=request.content,
                    images=request.images or [],
                    tags=request.tags or [],
                    status="published",
                    published_at=datetime.utcnow()
                )
                self.db.add(post)
                
                # 更新账号统计
                account.total_posts += 1
                self.db.commit()
                
                return PostCreateResponse(
                    success=True,
                    post_id=result.get("note_id"),
                    message="发布成功",
                    task_id=result.get("task_id")
                )
            else:
                return PostCreateResponse(
                    success=False,
                    message=result.get("message", "发布失败")
                )
                
        except Exception as e:
            logger.error(f"Publish failed: {e}")
            # 记录失败
            self._log_error(
                user_id=request.user_id,
                account_id=request.account_id,
                error_type="publish_failed",
                message=str(e)
            )
            raise
    
    # ============ 帖子列表 ============
    
    @retry_on_failure(max_retries=2)
    async def get_posts_list(self, request: PostListRequest) -> PostListResponse:
        """获取帖子列表"""
        try:
            # 构建查询
            query = self.db.query(PostHistory).filter(
                PostHistory.user_id == request.user_id
            )
            
            if request.account_id:
                query = query.filter(PostHistory.account_id == request.account_id)
            
            if request.status:
                query = query.filter(PostHistory.status == request.status)
            
            # 统计总数
            total = query.count()
            
            # 分页
            offset = (request.page - 1) * request.page_size
            posts = query.order_by(PostHistory.created_at.desc()).offset(offset).limit(request.page_size).all()
            
            return PostListResponse(
                posts=[
                    {
                        "id": p.id,
                        "post_id": p.post_id,
                        "title": p.title,
                        "status": p.status,
                        "like_count": p.like_count,
                        "collect_count": p.collect_count,
                        "comment_count": p.comment_count,
                        "share_count": p.share_count,
                        "view_count": p.view_count,
                        "published_at": p.published_at.isoformat() if p.published_at else None,
                        "created_at": p.created_at.isoformat()
                    }
                    for p in posts
                ],
                total=total,
                page=request.page,
                page_size=request.page_size
            )
            
        except Exception as e:
            logger.error(f"Get posts list failed: {e}")
            return PostListResponse(
                posts=[],
                total=0,
                page=request.page,
                page_size=request.page_size
            )
    
    async def refresh_posts_from_platform(self, user_id: str, account_id: int) -> SyncResult:
        """从平台刷新帖子列表"""
        try:
            account = self.db.query(UserAccount).filter(
                and_(
                    UserAccount.id == account_id,
                    UserAccount.user_id == user_id
                )
            ).first()
            
            if not account:
                return SyncResult(success=False, errors=["账号不存在"])
            
            cookies = decrypt_cookies(account.cookies)
            page = 1
            posts_synced = 0
            errors = []
            
            while True:
                try:
                    result = await self.mcp_client.get_notes_list(cookies, page=page, limit=50)
                    notes = result.get("notes", [])
                    
                    if not notes:
                        break
                    
                    for note in notes:
                        # 检查是否已存在
                        existing = self.db.query(PostHistory).filter(
                            PostHistory.post_id == note.get("note_id")
                        ).first()
                        
                        if existing:
                            # 更新本地记录
                            existing.like_count = note.get("like_count", 0)
                            existing.collect_count = note.get("collect_count", 0)
                            existing.comment_count = note.get("comment_count", 0)
                            existing.share_count = note.get("share_count", 0)
                            existing.view_count = note.get("view_count", 0)
                        else:
                            # 创建新记录
                            post = PostHistory(
                                user_id=user_id,
                                account_id=account_id,
                                post_id=note.get("note_id"),
                                title=note.get("title", ""),
                                content=note.get("content", ""),
                                images=note.get("images", []),
                                tags=note.get("tags", []),
                                status=note.get("status", "published"),
                                published_at=datetime.fromisoformat(note.get("time")) if note.get("time") else datetime.utcnow(),
                                like_count=note.get("like_count", 0),
                                collect_count=note.get("collect_count", 0),
                                comment_count=note.get("comment_count", 0),
                                share_count=note.get("share_count", 0),
                                view_count=note.get("view_count", 0)
                            )
                            self.db.add(post)
                        
                        posts_synced += 1
                    
                    self.db.commit()
                    page += 1
                    
                except Exception as e:
                    errors.append(f"Page {page} failed: {str(e)}")
                    break
            
            return SyncResult(
                success=len(errors) == 0,
                posts_synced=posts_synced,
                errors=errors,
                duration_seconds=0.0
            )
            
        except Exception as e:
            logger.error(f"Refresh posts failed: {e}")
            return SyncResult(success=False, posts_synced=0, errors=[str(e)])
    
    # ============ 热度追踪 ============
    
    async def track_heat_trends(self, request: HeatTrendRequest) -> HeatTrendResponse:
        """追踪帖子热度"""
        trends = {}
        updated_at = datetime.utcnow()
        
        for post_id in request.post_ids:
            try:
                # 获取本地记录
                post = self.db.query(PostHistory).filter(
                    PostHistory.post_id == post_id
                ).first()
                
                if not post:
                    trends[post_id] = {"error": "Post not found"}
                    continue
                
                # 获取账号
                account = self.db.query(UserAccount).get(post.account_id)
                if not account:
                    trends[post_id] = {"error": "Account not found"}
                    continue
                
                cookies = decrypt_cookies(account.cookies)
                
                # 获取最新热度数据
                stats = await self.mcp_client.get_note_stats(cookies, post_id)
                
                # 记录历史趋势
                old_like = post.like_count
                old_collect = post.collect_count
                old_comment = post.comment_count
                old_share = post.share_count
                
                # 更新数据
                post.like_count = stats.get("like_count", 0)
                post.collect_count = stats.get("collect_count", 0)
                post.comment_count = stats.get("comment_count", 0)
                post.share_count = stats.get("share_count", 0)
                post.view_count = stats.get("view_count", 0)
                post.last_tracked_at = datetime.utcnow()
                
                # 计算趋势
                total_change = (
                    (post.like_count - old_like) +
                    (post.collect_count - old_collect) +
                    (post.comment_count - old_comment) +
                    (post.share_count - old_share)
                )
                
                if total_change > 0:
                    trend = "rising"
                elif total_change < 0:
                    trend = "falling"
                else:
                    trend = "stable"
                
                post.heat_trend = trend
                
                trends[post_id] = {
                    "like_count": post.like_count,
                    "collect_count": post.collect_count,
                    "comment_count": post.comment_count,
                    "share_count": post.share_count,
                    "view_count": post.view_count,
                    "trend": trend,
                    "last_tracked_at": post.last_tracked_at.isoformat()
                }
                
                if request.include_history:
                    trends[post_id]["history"] = self._get_post_history(post_id)
                
                self.db.commit()
                
            except Exception as e:
                logger.error(f"Track heat for {post_id} failed: {e}")
                trends[post_id] = {"error": str(e)}
        
        return HeatTrendResponse(trends=trends, updated_at=updated_at)
    
    def _get_post_history(self, post_id: str) -> List[Dict]:
        """获取帖子历史记录（简化为返回最近追踪记录）"""
        # 实际实现可以从单独的history表获取
        post = self.db.query(PostHistory).filter(
            PostHistory.post_id == post_id
        ).first()
        
        if not post:
            return []
        
        return [{
            "tracked_at": post.created_at.isoformat(),
            "like_count": post.like_count,
            "collect_count": post.collect_count
        }]
    
    # ============ 异常处理 ============
    
    def _log_error(self, user_id: str, error_type: str, message: str,
                   task_id: int = None, account_id: int = None):
        """记录异常"""
        error = ErrorNotification(
            user_id=user_id,
            error_type=error_type,
            message=message,
            task_id=task_id,
            account_id=account_id
        )
        self.db.add(error)
        self.db.commit()
        
        # 可以集成通知服务发送告警
        self._send_error_notification(error)
    
    def _send_error_notification(self, error: ErrorNotification):
        """发送异常通知（可集成邮件/短信/Webhook等）"""
        logger.warning(
            f"Error notification: [{error.error_type}] {error.message} "
            f"(user={error.user_id}, task={error.task_id})"
        )
        # TODO: 集成通知渠道
        # await notify_service.send_alert(error)
    
    def get_error_notifications(self, user_id: str, resolved: bool = False) -> List[Dict]:
        """获取异常通知列表"""
        notifications = self.db.query(ErrorNotification).filter(
            and_(
                ErrorNotification.user_id == user_id,
                ErrorNotification.resolved == resolved
            )
        ).order_by(ErrorNotification.occurred_at.desc()).limit(50).all()
        
        return [
            {
                "id": n.id,
                "error_type": n.error_type,
                "message": n.message,
                "task_id": n.task_id,
                "account_id": n.account_id,
                "occurred_at": n.occurred_at.isoformat(),
                "resolved": n.resolved
            }
            for n in notifications
        ]


# ============ 服务工厂 ============

def get_mcp_service(db_session: Session) -> MCPService:
    """获取MCP服务实例"""
    return MCPService(db_session)
