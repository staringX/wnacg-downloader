"""下载相关路由"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.models import Manga
from app.schemas import DownloadResponse, BatchDownloadResponse, TaskCreateResponse
from app.crawler.base import MangaCrawler
from app.utils.downloader import MangaDownloader
from app.config import settings
from app.utils.logger import logger
from app.services.task_manager import TaskManager

router = APIRouter(prefix="/api", tags=["download"])


class BatchDownloadRequest(BaseModel):
    manga_ids: List[str]


def _execute_download_task(task_id: str, manga_id: str, db: Session):
    """执行下载任务（后台任务）"""
    from app.database import SessionLocal
    
    if not db:
        db = SessionLocal()
    
    try:
        manga = db.query(Manga).filter(Manga.id == manga_id).first()
        if not manga:
            TaskManager.update_task(db, task_id, status="failed", error_message="漫画不存在")
            return
        
        # 检查是否已完全下载
        if manga.download_status == "completed" and manga.is_downloaded:
            TaskManager.update_task(
                db, task_id,
                status="completed",
                progress=100,
                message="漫画已下载",
                result_data=f'{{"file_path": "{manga.cbz_file_path}"}}'
            )
            return
        
        TaskManager.update_task(db, task_id, status="running", message=f"开始下载: {manga.title}")
        
        crawler = MangaCrawler()
        downloader = MangaDownloader()
        
        try:
            # 登录
            if not crawler.login(settings.manga_username, settings.manga_password):
                TaskManager.update_task(db, task_id, status="failed", error_message="登录失败")
                return
            
            # 标记为下载中
            manga.download_status = "downloading"
            manga.downloaded_pages = manga.downloaded_pages or 0
            db.commit()
            
            # 获取漫画详情
            if not manga.page_count or not manga.cover_image_url:
                TaskManager.update_task(db, task_id, message="获取漫画详情...")
                details = crawler.get_manga_details(manga.manga_url)
                if details:
                    if details.get('page_count'):
                        manga.page_count = details['page_count']
                    if details.get('updated_at'):
                        manga.updated_at = details['updated_at']
                    if details.get('cover_image_url'):
                        manga.cover_image_url = details['cover_image_url']
                    db.commit()
            
            # 获取图片列表
            TaskManager.update_task(db, task_id, message="获取图片列表...")
            images = crawler.get_manga_images(manga.manga_url)
            
            if not images:
                manga.download_status = "failed"
                db.commit()
                TaskManager.update_task(db, task_id, status="failed", error_message="无法获取图片列表")
                return
            
            total_images = len(images)
            TaskManager.update_task(
                db, task_id,
                total_items=total_images,
                message=f"开始下载 {total_images} 张图片..."
            )
            
            cbz_path = None
            cover_path = None
            
            for progress in downloader.download_manga_stream(manga.title, images, author=manga.author, resume=True):
                status = progress.get('status')
                
                # 更新下载进度
                if 'downloaded_count' in progress:
                    downloaded_count = progress['downloaded_count']
                    manga.downloaded_pages = downloaded_count
                    db.commit()
                    
                    # 更新任务进度
                    progress_percent = int((downloaded_count / total_images) * 90)  # 90%用于下载，10%用于打包
                    TaskManager.update_task(
                        db, task_id,
                        progress=progress_percent,
                        completed_items=downloaded_count,
                        message=f"已下载 {downloaded_count}/{total_images} 张图片"
                    )
                
                # 下载完成
                if status == 'completed':
                    cbz_path = progress.get('cbz_path')
                    cover_path = progress.get('cover_path')
                    file_size = progress.get('file_size', 0)
                    
                    # 更新数据库
                    manga.is_downloaded = True
                    manga.download_status = "completed"
                    manga.downloaded_at = datetime.now()
                    manga.cbz_file_path = cbz_path
                    manga.cover_image_path = cover_path
                    manga.file_size = file_size
                    manga.downloaded_pages = total_images
                    db.commit()
                    
                    TaskManager.update_task(
                        db, task_id,
                        status="completed",
                        progress=100,
                        message=f"下载完成: {manga.title}",
                        result_data=f'{{"file_path": "{cbz_path}", "file_size": {file_size}}}'
                    )
                    
                    logger.info(f"✅ 下载完成: {manga.title}")
                
                # 下载失败
                elif status == 'error':
                    manga.download_status = "failed"
                    db.commit()
                    TaskManager.update_task(
                        db, task_id,
                        status="failed",
                        error_message=progress.get('message', '下载失败')
                    )
                    return
            
            if not cbz_path:
                manga.download_status = "failed"
                db.commit()
                TaskManager.update_task(db, task_id, status="failed", error_message="下载失败")
                
        except Exception as e:
            logger.error(f"下载任务失败: {e}")
            manga.download_status = "failed"
            db.commit()
            TaskManager.update_task(db, task_id, status="failed", error_message=str(e))
        finally:
            crawler.close()
    finally:
        if db:
            db.close()


@router.post("/download/{manga_id}", response_model=TaskCreateResponse)
def download_manga(manga_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    下载单个漫画（异步任务模式，支持断点续传）
    
    功能：
    - 如果已完全下载，直接返回
    - 如果下载中断，自动恢复（跳过已下载的页）
    - 边下载边保存，实时更新进度
    - 通过任务ID查询状态
    """
    manga = db.query(Manga).filter(Manga.id == manga_id).first()
    if not manga:
        raise HTTPException(status_code=404, detail="漫画不存在")
    
    # 检查是否已有正在运行的下载任务
    running_tasks = TaskManager.get_running_tasks(db, "download")
    for task in running_tasks:
        if task.manga_id == manga_id:
            raise HTTPException(status_code=409, detail=f"该漫画已有下载任务正在运行: {task.id}")
    
    # 检查是否已完全下载
    if manga.download_status == "completed" and manga.is_downloaded:
        # 返回已完成的任务信息
        return TaskCreateResponse(
            success=True,
            task_id="",
            message="漫画已下载"
        )
    
    # 创建任务
    task = TaskManager.create_task(db, task_type="download", manga_id=manga_id)
    
    # 在后台执行下载任务
    background_tasks.add_task(_execute_download_task, task.id, manga_id, db)
    
    return TaskCreateResponse(
        success=True,
        task_id=task.id,
        message="下载任务已创建，正在后台执行"
    )


@router.post("/download/batch", response_model=BatchDownloadResponse)
def download_batch(request: BatchDownloadRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    批量下载漫画（逐个处理，实时保存）
    
    功能：
    - 每下载完一本，立即保存数据库
    - 中途中断不影响已下载的漫画
    - 支持断点续传（每本漫画独立）
    """
    success_count = 0
    failed_count = 0
    failed_titles = []
    
    logger.info(f"\n{'='*60}")
    logger.info(f"开始批量下载: {len(request.manga_ids)} 本漫画")
    logger.info(f"{'='*60}\n")
    
    # 逐个下载，每完成一个立即保存
    for idx, manga_id in enumerate(request.manga_ids, 1):
        try:
            manga = db.query(Manga).filter(Manga.id == manga_id).first()
            if not manga:
                logger.warning(f"[{idx}/{len(request.manga_ids)}] ✗ 跳过: 漫画ID {manga_id} 不存在")
                failed_count += 1
                continue
            
            logger.info(f"\n[{idx}/{len(request.manga_ids)}] 处理: {manga.title}")
            
            # 如果已经下载完成，跳过
            if manga.download_status == "completed" and manga.is_downloaded:
                logger.info(f"  ⏭️  已下载，跳过")
                success_count += 1
                continue
            
            # 调用单本下载（支持断点续传）
            try:
                result = download_manga(manga_id, background_tasks, db)
                if result.success:
                    success_count += 1
                    logger.info(f"  ✅ 成功")
                else:
                    failed_count += 1
                    failed_titles.append(manga.title)
                    logger.error(f"  ❌ 失败")
            except Exception as e:
                failed_count += 1
                failed_titles.append(manga.title)
                logger.error(f"  ❌ 失败: {str(e)}")
                # 单本失败不影响其他漫画，继续处理下一本
                continue
                
        except Exception as e:
            logger.error(f"[{idx}/{len(request.manga_ids)}] ✗ 处理失败: {e}")
            failed_count += 1
            continue
    
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

