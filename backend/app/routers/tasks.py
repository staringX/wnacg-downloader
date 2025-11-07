"""任务状态相关路由"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import asyncio
import json
from app.database import get_db
from app.models import Task
from app.schemas import TaskResponse, TaskCreateResponse
from app.services.task_manager import TaskManager, sse_manager
from app.utils.logger import logger

router = APIRouter(prefix="/api", tags=["tasks"])


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    """获取任务状态（用于页面刷新后恢复状态）"""
    task = TaskManager.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskResponse.model_validate(task)


@router.get("/tasks", response_model=list[TaskResponse])
def get_tasks(
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取任务列表"""
    query = db.query(Task)
    
    if task_type:
        query = query.filter(Task.task_type == task_type)
    if status:
        query = query.filter(Task.status == status)
    
    tasks = query.order_by(Task.created_at.desc()).limit(limit).all()
    return [TaskResponse.model_validate(task) for task in tasks]


@router.get("/tasks/running/list", response_model=list[TaskResponse])
def get_running_tasks(task_type: Optional[str] = None, db: Session = Depends(get_db)):
    """获取正在运行的任务列表"""
    tasks = TaskManager.get_running_tasks(db, task_type)
    return [TaskResponse.model_validate(task) for task in tasks]


@router.get("/tasks/latest/{task_type}", response_model=Optional[TaskResponse])
def get_latest_task(task_type: str, db: Session = Depends(get_db)):
    """获取指定类型的最新任务"""
    task = TaskManager.get_latest_task(db, task_type)
    if not task:
        return None
    return TaskResponse.model_validate(task)


@router.post("/tasks/cleanup")
def cleanup_stale_tasks(db: Session = Depends(get_db)):
    """手动清理过期的任务（用于调试或手动触发）"""
    try:
        cleaned_count = TaskManager.cleanup_stale_tasks(db, cleanup_all_on_startup=True)
        return {
            "success": True,
            "message": f"已清理 {cleaned_count} 个中断的任务",
            "cleaned_count": cleaned_count
        }
    except Exception as e:
        logger.error(f"清理任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理任务失败: {str(e)}")


@router.get("/events")
async def stream_events():
    """
    Server-Sent Events (SSE) 端点
    用于实时推送任务状态更新
    """
    async def event_generator():
        # 创建消息队列
        queue = asyncio.Queue()
        
        # 添加到SSE管理器
        await sse_manager.add_connection(queue)
        
        try:
            # 发送初始连接消息
            yield "event: connected\ndata: {\"message\": \"SSE连接已建立\"}\n\n"
            
            # 持续监听消息
            while True:
                try:
                    # 从队列获取消息（带超时，用于心跳检测）
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield message
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    yield ": heartbeat\n\n"
                except Exception as e:
                    logger.error(f"SSE事件生成器错误: {e}")
                    break
        finally:
            # 移除连接
            await sse_manager.remove_connection(queue)
            logger.info("SSE连接已关闭")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
        }
    )

