"""最近更新相关路由"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import RecentUpdate
from app.schemas import MangaResponse, TaskCreateResponse
from app.services.task_manager import TaskManager
from app.services.recent_updates_singleton import recent_updates_singleton
from app.services.recent_updates_service import RecentUpdatesService

router = APIRouter(prefix="/api", tags=["recent-updates"])


@router.get("/recent-updates", response_model=List[MangaResponse])
def get_recent_updates(db: Session = Depends(get_db)):
    """获取最近更新（从RecentUpdate表读取）"""
    recent_updates = db.query(RecentUpdate).order_by(RecentUpdate.updated_at.desc()).all()
    return [MangaResponse.from_orm(update) for update in recent_updates]


@router.post("/sync-recent-updates", response_model=TaskCreateResponse)
def sync_recent_updates(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    同步最近更新（异步任务模式，单例模式）
    1. 获取所有已收藏的作者
    2. 对每个作者，找到收藏夹中最新的漫画的更新时间
    3. 搜索该作者，获取晚于该时间的所有漫画
    4. 保存新更新到RecentUpdate表
    5. 删除早于该时间的记录（仅从RecentUpdate表删除）
    """
    # 使用单例管理器检查是否有正在运行的任务
    if recent_updates_singleton.is_running():
        running_task_id = recent_updates_singleton.get_running_task_id()
        raise HTTPException(status_code=409, detail=f"已有同步最近更新任务正在运行: {running_task_id}")
    
    # 创建任务
    task = TaskManager.create_task(db, task_type="sync_recent_updates")
    
    # 在后台执行同步任务
    background_tasks.add_task(RecentUpdatesService.execute_sync_recent_updates_task, task.id, db)
    
    return TaskCreateResponse(
        success=True,
        task_id=task.id,
        message="同步最近更新任务已创建，正在后台执行"
    )

