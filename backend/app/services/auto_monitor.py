"""
NoteTrial Backend - 自动监控服务
发布后自动获取效果数据并反馈到学习引擎
"""
import asyncio
import httpx
from typing import Optional, Dict, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import os


@dataclass
class MonitorTask:
    """监控任务"""
    content_id: str
    note_id: str  # 小红书笔记ID
    created_at: datetime
    last_check: Optional[datetime] = None
    check_count: int = 0
    status: str = "pending"  # pending, monitoring, completed, failed
    final_stats: Optional[dict] = None


class AutoMonitor:
    """
    自动监控服务
    
    核心功能：
    1. 任务队列：管理待监控的笔记
    2. 定时检查：周期性获取效果数据
    3. 回调通知：达到条件后通知学习引擎
    """
    
    # 监控策略：在发布后的不同时间点检查
    CHECK_INTERVALS = [
        timedelta(minutes=30),    # 30分钟后首次检查
        timedelta(hours=2),       # 2小时后
        timedelta(hours=6),       # 6小时后
        timedelta(hours=24),      # 24小时后
        timedelta(hours=48),      # 48小时后（最终数据）
    ]
    
    def __init__(
        self, 
        mcp_base_url: str = "http://localhost:18060",
        storage_path: str = "data/monitor_tasks.json"
    ):
        self.mcp_base_url = mcp_base_url
        self.storage_path = storage_path
        self.tasks: Dict[str, MonitorTask] = {}
        self.callbacks: List[Callable] = []
        self._running = False
        self._load_tasks()
    
    def _load_tasks(self):
        """加载任务列表"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_data in data.get('tasks', []):
                        task = MonitorTask(
                            content_id=task_data['content_id'],
                            note_id=task_data['note_id'],
                            created_at=datetime.fromisoformat(task_data['created_at']),
                            last_check=datetime.fromisoformat(task_data['last_check']) if task_data.get('last_check') else None,
                            check_count=task_data.get('check_count', 0),
                            status=task_data.get('status', 'pending'),
                            final_stats=task_data.get('final_stats')
                        )
                        if task.status in ('pending', 'monitoring'):
                            self.tasks[task.content_id] = task
            except Exception as e:
                print(f"[AutoMonitor] 加载任务失败: {e}")
    
    def _save_tasks(self):
        """保存任务列表"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        try:
            tasks_data = []
            for task in self.tasks.values():
                tasks_data.append({
                    'content_id': task.content_id,
                    'note_id': task.note_id,
                    'created_at': task.created_at.isoformat(),
                    'last_check': task.last_check.isoformat() if task.last_check else None,
                    'check_count': task.check_count,
                    'status': task.status,
                    'final_stats': task.final_stats
                })
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({'tasks': tasks_data}, ensure_ascii=False, indent=2, fp=f)
        except Exception as e:
            print(f"[AutoMonitor] 保存任务失败: {e}")
    
    def add_callback(self, callback: Callable):
        """添加效果数据回调"""
        self.callbacks.append(callback)
    
    def add_task(self, content_id: str, note_id: str) -> MonitorTask:
        """添加监控任务"""
        task = MonitorTask(
            content_id=content_id,
            note_id=note_id,
            created_at=datetime.now(),
            status="pending"
        )
        self.tasks[content_id] = task
        self._save_tasks()
        print(f"[AutoMonitor] 添加监控任务: {content_id} -> {note_id}")
        return task
    
    async def check_note_stats(self, note_id: str) -> Optional[dict]:
        """
        通过MCP获取笔记效果数据
        
        Returns:
            {
                'likes': int,
                'collects': int, 
                'comments': int,
                'shares': int,
                'views': int,  # 如果有的话
            }
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 调用小红书MCP获取笔记详情
                response = await client.post(
                    f"{self.mcp_base_url}/tools/get_note_detail",
                    json={"note_id": note_id}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    note_info = data.get('result', {})
                    
                    return {
                        'likes': note_info.get('liked_count', 0),
                        'collects': note_info.get('collected_count', 0),
                        'comments': note_info.get('comment_count', 0),
                        'shares': note_info.get('share_count', 0),
                        'views': note_info.get('view_count', 0),
                    }
                else:
                    print(f"[AutoMonitor] 获取笔记数据失败: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"[AutoMonitor] 获取笔记数据异常: {e}")
            return None
    
    async def process_task(self, task: MonitorTask) -> bool:
        """
        处理单个监控任务
        
        Returns:
            是否完成监控
        """
        now = datetime.now()
        elapsed = now - task.created_at
        
        # 确定当前应该处于哪个检查点
        target_check_index = 0
        for i, interval in enumerate(self.CHECK_INTERVALS):
            if elapsed >= interval:
                target_check_index = i + 1
        
        # 如果已经检查到这个点了，跳过
        if task.check_count >= target_check_index:
            return task.check_count >= len(self.CHECK_INTERVALS)
        
        # 执行检查
        task.status = "monitoring"
        stats = await self.check_note_stats(task.note_id)
        
        if stats:
            task.last_check = now
            task.check_count = target_check_index
            task.final_stats = stats
            
            # 通知回调
            for callback in self.callbacks:
                try:
                    await callback(task.content_id, stats, task.check_count)
                except Exception as e:
                    print(f"[AutoMonitor] 回调执行失败: {e}")
            
            print(f"[AutoMonitor] 检查完成 [{task.check_count}/{len(self.CHECK_INTERVALS)}]: "
                  f"{task.content_id} - 点赞:{stats['likes']}, 收藏:{stats['collects']}")
        
        # 检查是否完成所有监控
        if task.check_count >= len(self.CHECK_INTERVALS):
            task.status = "completed"
            return True
        
        self._save_tasks()
        return False
    
    async def run_once(self):
        """执行一次检查循环"""
        completed = []
        
        for content_id, task in list(self.tasks.items()):
            if task.status in ('pending', 'monitoring'):
                is_done = await self.process_task(task)
                if is_done:
                    completed.append(content_id)
        
        # 清理已完成的任务
        for content_id in completed:
            del self.tasks[content_id]
        
        if completed:
            self._save_tasks()
        
        return len(completed)
    
    async def start_background(self, check_interval: int = 300):
        """
        启动后台监控循环
        
        Args:
            check_interval: 检查间隔（秒），默认5分钟
        """
        self._running = True
        print(f"[AutoMonitor] 启动后台监控，检查间隔: {check_interval}秒")
        
        while self._running:
            try:
                completed = await self.run_once()
                if completed:
                    print(f"[AutoMonitor] 本轮完成 {completed} 个任务")
            except Exception as e:
                print(f"[AutoMonitor] 监控循环异常: {e}")
            
            await asyncio.sleep(check_interval)
    
    def stop(self):
        """停止后台监控"""
        self._running = False
        print("[AutoMonitor] 停止后台监控")
    
    def get_pending_count(self) -> int:
        """获取待处理任务数"""
        return len([t for t in self.tasks.values() if t.status in ('pending', 'monitoring')])
    
    def get_all_tasks(self) -> List[dict]:
        """获取所有任务状态"""
        return [
            {
                'content_id': t.content_id,
                'note_id': t.note_id,
                'status': t.status,
                'check_count': t.check_count,
                'total_checks': len(self.CHECK_INTERVALS),
                'created_at': t.created_at.isoformat(),
                'last_check': t.last_check.isoformat() if t.last_check else None,
                'stats': t.final_stats
            }
            for t in self.tasks.values()
        ]


# 模拟MCP响应（用于测试）
class MockMCPMonitor(AutoMonitor):
    """
    模拟版本的监控器（当MCP不可用时使用）
    """
    
    async def check_note_stats(self, note_id: str) -> Optional[dict]:
        """返回模拟数据"""
        import random
        
        # 模拟真实的数据增长
        base = random.randint(10, 100)
        
        return {
            'likes': base + random.randint(0, 50),
            'collects': int(base * 0.3) + random.randint(0, 20),
            'comments': int(base * 0.1) + random.randint(0, 10),
            'shares': int(base * 0.05) + random.randint(0, 5),
            'views': base * 10 + random.randint(0, 500),
        }
