"""同步相关路由"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from app.database import get_db
from app.schemas import TaskCreateResponse
from app.utils.logger import logger
from app.services.task_manager import TaskManager
from app.services.sync_singleton import sync_singleton
from app.services.sync_service import SyncService

router = APIRouter(prefix="/api", tags=["sync"])


class VerifyResponse(BaseModel):
    success: bool
    message: str
    verified_count: int
    fixed_count: int
    missing_files: List[str]


@router.post("/verify-files", response_model=VerifyResponse)
def verify_files(db: Session = Depends(get_db)):
    """
    手动验证本地文件完整性
    
    检查所有标记为"已下载"的漫画，验证其CBZ文件是否真实存在。
    如果文件丢失，自动重置下载状态，允许重新下载。
    
    返回：
    - verified_count: 验证通过的数量
    - fixed_count: 已修复（重置）的数量
    - missing_files: 丢失文件的漫画标题列表
    """
    try:
        verified_count, fixed_count, missing_files = SyncService.verify_local_files(db)
        
        if fixed_count > 0:
            message = f"发现 {fixed_count} 个文件丢失，已重置下载状态。{verified_count} 个文件完整。"
        else:
            message = f"所有 {verified_count} 个已下载漫画的文件都完整。"
        
        return VerifyResponse(
            success=True,
            message=message,
            verified_count=verified_count,
            fixed_count=fixed_count,
            missing_files=missing_files
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件验证失败: {str(e)}")


@router.post("/sync", response_model=TaskCreateResponse)
def sync_collection(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """同步收藏夹（异步任务模式，单例模式）"""
    # 使用单例管理器检查是否有正在运行的任务
    if sync_singleton.is_running():
        running_task_id = sync_singleton.get_running_task_id()
        raise HTTPException(status_code=409, detail=f"已有同步任务正在运行: {running_task_id}")
    
    # 创建任务
    task = TaskManager.create_task(db, task_type="sync")
    
    # 在后台执行同步任务
    background_tasks.add_task(SyncService.execute_sync_task, task.id, db)
    
    return TaskCreateResponse(
        success=True,
        task_id=task.id,
        message="同步任务已创建，正在后台执行"
    )

