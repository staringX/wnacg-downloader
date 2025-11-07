"""同步收藏夹单例管理器 - 管理同步收藏夹的单例执行"""
from typing import Optional
from threading import Lock
from app.utils.logger import logger


class SyncSingleton:
    """同步收藏夹单例管理器
    
    确保同步收藏夹任务在同一时间只能有一个实例运行。
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SyncSingleton, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._task_lock = Lock()
        self._running_task_id: Optional[str] = None
        self._initialized = True
    
    def is_running(self) -> bool:
        """检查同步收藏夹任务是否正在运行"""
        return self._running_task_id is not None
    
    def get_running_task_id(self) -> Optional[str]:
        """获取正在运行的任务ID"""
        return self._running_task_id
    
    def start_task(self, task_id: str) -> bool:
        """尝试启动任务（单例模式）
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 如果成功启动返回True，如果已有任务在运行返回False
        """
        with self._task_lock:
            if self._running_task_id is not None:
                logger.warning(f"同步收藏夹任务已有实例在运行: {self._running_task_id}")
                return False
            
            self._running_task_id = task_id
            logger.info(f"同步收藏夹任务已启动: {task_id}")
            return True
    
    def finish_task(self, task_id: str):
        """完成任务（释放单例锁）
        
        Args:
            task_id: 任务ID
        """
        with self._task_lock:
            if self._running_task_id == task_id:
                self._running_task_id = None
                logger.info(f"同步收藏夹任务已完成: {task_id}")
            else:
                logger.warning(f"同步收藏夹任务的ID不匹配: 期望 {self._running_task_id}, 实际 {task_id}")


# 全局同步收藏夹单例管理器实例
sync_singleton = SyncSingleton()

