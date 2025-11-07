"""下载队列管理器 - 管理下载任务的队列执行"""
import json
from typing import List, Optional, Dict
from threading import Lock
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Task, Manga
from app.utils.logger import logger


class DownloadQueueManager:
    """下载队列管理器
    
    管理下载任务的队列执行：
    - 单例执行器：一次只执行一个下载任务
    - 队列管理：新请求加入队列而不是被拒绝
    - 状态查询：提供队列状态查询接口
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DownloadQueueManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._executor_lock = Lock()
        self._is_executing = False
        self._current_task_id: Optional[str] = None
        self._initialized = True
    
    def is_executing(self) -> bool:
        """检查是否正在执行下载任务"""
        return self._is_executing
    
    def get_current_task_id(self) -> Optional[str]:
        """获取当前正在执行的任务ID"""
        return self._current_task_id
    
    def add_to_queue(self, db: Session, manga_id: str) -> Optional[Task]:
        """将漫画添加到下载队列
        
        Args:
            db: 数据库会话
            manga_id: 漫画ID
            
        Returns:
            Task: 创建的任务对象，如果已存在则返回None
        """
        # 检查漫画是否存在
        manga = db.query(Manga).filter(Manga.id == manga_id).first()
        if not manga:
            logger.error(f"漫画不存在: {manga_id}")
            return None
        
        # 检查是否已完全下载
        if manga.download_status == "completed" and manga.is_downloaded:
            logger.info(f"漫画已下载，跳过: {manga.title}")
            return None
        
        # 检查是否已有该漫画的任务（运行中或队列中）
        existing_task = db.query(Task).filter(
            Task.task_type == "download",
            Task.manga_id == manga_id,
            Task.status.in_(["pending", "running"])
        ).first()
        
        if existing_task:
            logger.info(f"漫画已在队列中或正在下载: {manga.title} (任务ID: {existing_task.id})")
            return existing_task
        
        # 创建新的下载任务（状态为pending，表示在队列中）
        task = Task(
            task_type="download",
            status="pending",  # pending表示在队列中等待
            progress=0,
            manga_id=manga_id,
            message=f"等待下载: {manga.title}"
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        logger.info(f"漫画已加入下载队列: {manga.title} (任务ID: {task.id})")
        return task
    
    def get_queue(self, db: Session) -> List[Task]:
        """获取下载队列中的所有任务（pending状态）
        
        Args:
            db: 数据库会话
            
        Returns:
            List[Task]: 队列中的任务列表
        """
        return db.query(Task).filter(
            Task.task_type == "download",
            Task.status == "pending"
        ).order_by(Task.created_at.asc()).all()
    
    def get_queued_manga_ids(self, db: Session) -> List[str]:
        """获取队列中的漫画ID列表（用于前端显示）
        
        Args:
            db: 数据库会话
            
        Returns:
            List[str]: 队列中的漫画ID列表
        """
        queue_tasks = self.get_queue(db)
        manga_ids = [task.manga_id for task in queue_tasks if task.manga_id]
        
        # 也包括当前正在执行的任务
        if self._current_task_id:
            current_task = db.query(Task).filter(Task.id == self._current_task_id).first()
            if current_task and current_task.manga_id and current_task.manga_id not in manga_ids:
                manga_ids.append(current_task.manga_id)
        
        return manga_ids
    
    def start_execution(self, task_id: str) -> bool:
        """开始执行下载任务（单例模式）
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 如果成功开始执行返回True，如果已有任务在运行返回False
        """
        with self._executor_lock:
            if self._is_executing:
                logger.warning(f"下载执行器正在运行，无法启动新任务: {task_id}")
                return False
            
            self._is_executing = True
            self._current_task_id = task_id
            logger.info(f"下载执行器已启动: {task_id}")
            return True
    
    def finish_execution(self, task_id: str):
        """完成下载任务执行（释放执行器）
        
        Args:
            task_id: 任务ID
        """
        with self._executor_lock:
            if self._current_task_id == task_id:
                self._is_executing = False
                self._current_task_id = None
                logger.info(f"下载执行器已完成: {task_id}")
            else:
                logger.warning(f"下载执行器的任务ID不匹配: 期望 {self._current_task_id}, 实际 {task_id}")
    
    def get_next_task(self, db: Session) -> Optional[Task]:
        """获取队列中的下一个任务
        
        Args:
            db: 数据库会话
            
        Returns:
            Task: 下一个待执行的任务，如果没有则返回None
        """
        return db.query(Task).filter(
            Task.task_type == "download",
            Task.status == "pending"
        ).order_by(Task.created_at.asc()).first()


# 全局下载队列管理器实例
download_queue_manager = DownloadQueueManager()

