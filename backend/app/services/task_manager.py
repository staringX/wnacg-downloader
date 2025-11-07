"""任务管理服务 - 管理任务状态和SSE推送"""
import json
import asyncio
from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Task
from app.utils.logger import logger

# SSE连接管理器
class SSEManager:
    """Server-Sent Events 连接管理器"""
    
    def __init__(self):
        self.connections: List[asyncio.Queue] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def _get_loop(self):
        """获取或创建事件循环"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
            return loop
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop
    
    async def add_connection(self, queue: asyncio.Queue):
        """添加SSE连接"""
        self.connections.append(queue)
        logger.info(f"SSE连接已添加，当前连接数: {len(self.connections)}")
    
    async def remove_connection(self, queue: asyncio.Queue):
        """移除SSE连接"""
        if queue in self.connections:
            self.connections.remove(queue)
            logger.info(f"SSE连接已移除，当前连接数: {len(self.connections)}")
    
    async def broadcast(self, event_type: str, data: Dict):
        """广播消息到所有连接的客户端"""
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # 转换为SSE格式
        sse_message = f"event: {event_type}\ndata: {json.dumps(message, ensure_ascii=False)}\n\n"
        
        # 发送到所有连接
        disconnected = []
        for queue in self.connections:
            try:
                await queue.put(sse_message)
            except Exception as e:
                logger.warning(f"发送SSE消息失败: {e}")
                disconnected.append(queue)
        
        # 清理断开的连接
        for queue in disconnected:
            await self.remove_connection(queue)
    
    def broadcast_sync(self, event_type: str, data: Dict):
        """同步方式广播消息（用于后台任务）"""
        try:
            loop = self._get_loop()
            if loop.is_running():
                # 如果事件循环正在运行，创建任务
                asyncio.create_task(self.broadcast(event_type, data))
            else:
                # 如果事件循环未运行，运行它
                loop.run_until_complete(self.broadcast(event_type, data))
        except Exception as e:
            logger.error(f"同步广播消息失败: {e}")


# 全局SSE管理器
sse_manager = SSEManager()


class TaskManager:
    """任务管理器 - 管理任务状态"""
    
    @staticmethod
    def create_task(
        db: Session,
        task_type: str,
        manga_id: Optional[str] = None,
        manga_ids: Optional[List[str]] = None,
        total_items: Optional[int] = None
    ) -> Task:
        """创建新任务"""
        task = Task(
            task_type=task_type,
            status="pending",
            progress=0,
            total_items=total_items,
            completed_items=0,
            manga_id=manga_id,
            manga_ids=json.dumps(manga_ids) if manga_ids else None,
            message="任务已创建，等待执行..."
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        logger.info(f"创建任务: {task.id} ({task_type})")
        
        # 广播任务创建事件（同步方式，因为这是从同步函数调用的）
        sse_manager.broadcast_sync("task_created", {
            "task_id": task.id,
            "task_type": task_type,
            "status": task.status
        })
        
        return task
    
    @staticmethod
    def update_task(
        db: Session,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        total_items: Optional[int] = None,
        completed_items: Optional[int] = None,
        message: Optional[str] = None,
        error_message: Optional[str] = None,
        result_data: Optional[Dict] = None
    ) -> Optional[Task]:
        """更新任务状态"""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None
        
        if status:
            task.status = status
        if progress is not None:
            task.progress = progress
        if total_items is not None:
            task.total_items = total_items
        if completed_items is not None:
            task.completed_items = completed_items
        if message:
            task.message = message
        if error_message:
            task.error_message = error_message
        if result_data:
            task.result_data = json.dumps(result_data, ensure_ascii=False)
        
        if status in ["completed", "failed"]:
            task.completed_at = datetime.now()
        
        task.updated_at = datetime.now()
        db.commit()
        db.refresh(task)
        
        # 广播任务更新事件（同步方式，因为这是从同步函数调用的）
        sse_manager.broadcast_sync("task_updated", {
            "task_id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "progress": task.progress,
            "completed_items": task.completed_items,
            "total_items": task.total_items,
            "message": task.message,
            "error_message": task.error_message
        })
        
        return task
    
    @staticmethod
    def get_task(db: Session, task_id: str) -> Optional[Task]:
        """获取任务"""
        return db.query(Task).filter(Task.id == task_id).first()
    
    @staticmethod
    def get_running_tasks(db: Session, task_type: Optional[str] = None) -> List[Task]:
        """获取正在运行的任务"""
        query = db.query(Task).filter(Task.status.in_(["pending", "running"]))
        if task_type:
            query = query.filter(Task.task_type == task_type)
        return query.order_by(Task.created_at.desc()).all()
    
    @staticmethod
    def get_latest_task(db: Session, task_type: str) -> Optional[Task]:
        """获取指定类型的最新任务"""
        return db.query(Task).filter(
            Task.task_type == task_type
        ).order_by(Task.created_at.desc()).first()
    
    @staticmethod
    def cleanup_stale_tasks(db: Session, timeout_minutes: int = 60, cleanup_all_on_startup: bool = False):
        """
        清理过期的任务（长时间没有更新的运行中任务）
        通常在应用启动时调用，用于清理因Docker重启等原因中断的任务
        
        Args:
            db: 数据库会话
            timeout_minutes: 超时时间（分钟），默认60分钟
            cleanup_all_on_startup: 如果为True，清理所有pending/running任务（用于Docker重启场景）
        """
        from datetime import timedelta
        
        if cleanup_all_on_startup:
            # 启动时清理所有pending/running任务（因为重启后这些任务肯定都中断了）
            stale_tasks = db.query(Task).filter(
                Task.status.in_(["pending", "running"])
            ).all()
            logger.info(f"启动清理模式：查找所有pending/running状态的任务")
        else:
            timeout_threshold = datetime.now() - timedelta(minutes=timeout_minutes)
            # 查找所有状态为pending或running，但更新时间超过阈值的任务
            stale_tasks = db.query(Task).filter(
                Task.status.in_(["pending", "running"]),
                Task.updated_at < timeout_threshold
            ).all()
        
        if stale_tasks:
            logger.info(f"发现 {len(stale_tasks)} 个过期任务，正在清理...")
            
            for task in stale_tasks:
                old_status = task.status
                task.status = "failed"
                task.error_message = f"任务因系统重启或超时（超过{timeout_minutes}分钟未更新）而中断"
                task.completed_at = datetime.now()
                task.updated_at = datetime.now()
                
                logger.warning(
                    f"清理过期任务: {task.id} ({task.task_type}), "
                    f"原状态: {old_status}, 创建时间: {task.created_at}, "
                    f"最后更新: {task.updated_at}"
                )
            
            db.commit()
            
            # 广播任务更新事件
            for task in stale_tasks:
                sse_manager.broadcast_sync("task_updated", {
                    "task_id": task.id,
                    "task_type": task.task_type,
                    "status": "failed",
                    "error_message": task.error_message
                })
            
            logger.info(f"已清理 {len(stale_tasks)} 个过期任务")
        else:
            logger.debug("未发现过期任务")
        
        return len(stale_tasks)

