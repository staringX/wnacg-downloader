"""下载相关路由"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.database import get_db
from app.models import Manga
from app.schemas import BatchDownloadResponse, TaskCreateResponse
from app.utils.logger import logger
from app.services.download_queue import download_queue_manager
from app.services.download_service import DownloadService

router = APIRouter(prefix="/api", tags=["download"])


class BatchDownloadRequest(BaseModel):
    manga_ids: List[str]


@router.post("/download/{manga_id}", response_model=TaskCreateResponse)
def download_manga(manga_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    下载单个漫画（队列模式，支持断点续传）
    
    功能：
    - 如果已完全下载，直接返回
    - 如果不在队列中，加入下载队列
    - 如果已在队列中或正在下载，返回现有任务ID
    - 边下载边保存，实时更新进度
    - 通过任务ID查询状态
    """
    # 使用下载队列管理器添加任务
    task = download_queue_manager.add_to_queue(db, manga_id)
    
    if not task:
        # 漫画不存在或已下载
        manga = db.query(Manga).filter(Manga.id == manga_id).first()
        if not manga:
            raise HTTPException(status_code=404, detail="漫画不存在")
        
        # 已下载
        return TaskCreateResponse(
            success=True,
            task_id="",
            message="漫画已下载"
        )
    
    # 如果任务状态是pending，说明是新加入队列的，需要启动执行器
    if task.status == "pending":
        # 启动下载执行器（如果还没有运行）
        background_tasks.add_task(DownloadService.download_executor, db)
    
    return TaskCreateResponse(
        success=True,
        task_id=task.id,
        message="下载任务已加入队列" if task.status == "pending" else "下载任务正在执行"
    )


@router.get("/download/queue", response_model=List[str])
def get_download_queue(db: Session = Depends(get_db)):
    """获取下载队列中的漫画ID列表（用于前端显示）"""
    return download_queue_manager.get_queued_manga_ids(db)


@router.post("/download/batch", response_model=BatchDownloadResponse)
def download_batch(request: BatchDownloadRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    批量下载漫画（队列模式）
    
    功能：
    - 将所有漫画加入下载队列
    - 队列按顺序执行
    - 中途中断不影响已下载的漫画
    - 支持断点续传（每本漫画独立）
    """
    success_count = 0
    failed_count = 0
    failed_titles = []
    
    logger.info(f"\n{'='*60}")
    logger.info(f"开始批量下载: {len(request.manga_ids)} 本漫画")
    logger.info(f"{'='*60}\n")
    
    # 将所有漫画加入下载队列
    for idx, manga_id in enumerate(request.manga_ids, 1):
        try:
            manga = db.query(Manga).filter(Manga.id == manga_id).first()
            if not manga:
                logger.warning(f"[{idx}/{len(request.manga_ids)}] ✗ 跳过: 漫画ID {manga_id} 不存在")
                failed_count += 1
                continue
            
            logger.info(f"\n[{idx}/{len(request.manga_ids)}] 加入队列: {manga.title}")
            
            # 如果已经下载完成，跳过
            if manga.download_status == "completed" and manga.is_downloaded:
                logger.info(f"  ⏭️  已下载，跳过")
                success_count += 1
                continue
            
            # 加入下载队列
            try:
                task = download_queue_manager.add_to_queue(db, manga_id)
                if task:
                    success_count += 1
                    logger.info(f"  ✅ 已加入队列 (任务ID: {task.id})")
                else:
                    # 可能已下载或已在队列中
                    success_count += 1
                    logger.info(f"  ⏭️  已在队列中或已下载")
            except Exception as e:
                failed_count += 1
                failed_titles.append(manga.title)
                logger.error(f"  ❌ 失败: {str(e)}")
                continue
                
        except Exception as e:
            logger.error(f"[{idx}/{len(request.manga_ids)}] ✗ 处理失败: {e}")
            failed_count += 1
            continue
    
    # 启动下载执行器（如果还没有运行）
    if success_count > 0:
        background_tasks.add_task(DownloadService.download_executor, db)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"批量下载完成")
    logger.info(f"成功: {success_count} 本")
    logger.info(f"失败: {failed_count} 本")
    if failed_titles:
        logger.info(f"失败列表: {', '.join(failed_titles[:5])}" + ("..." if len(failed_titles) > 5 else ""))
    logger.info(f"{'='*60}\n")
    
    message = f"批量下载完成：成功 {success_count}，失败 {failed_count}"
    if failed_titles and len(failed_titles) <= 3:
        message += f"。失败: {', '.join(failed_titles)}"
    
    return BatchDownloadResponse(
        success=True,
        message=message,
        total=len(request.manga_ids),
        success_count=success_count,
        failed_count=failed_count
    )

