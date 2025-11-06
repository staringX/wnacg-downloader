"""下载相关路由"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.models import Manga
from app.schemas import DownloadResponse, BatchDownloadResponse
from app.crawler.base import MangaCrawler
from app.utils.downloader import MangaDownloader
from app.config import settings
from app.utils.logger import logger

router = APIRouter(prefix="/api", tags=["download"])


class BatchDownloadRequest(BaseModel):
    manga_ids: List[str]


@router.post("/download/{manga_id}", response_model=DownloadResponse)
def download_manga(manga_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    下载单个漫画（支持断点续传）
    
    功能：
    - 如果已完全下载，直接返回
    - 如果下载中断，自动恢复（跳过已下载的页）
    - 边下载边保存，实时更新进度
    """
    manga = db.query(Manga).filter(Manga.id == manga_id).first()
    if not manga:
        raise HTTPException(status_code=404, detail="漫画不存在")
    
    # 检查是否已完全下载
    if manga.download_status == "completed" and manga.is_downloaded:
        return DownloadResponse(
            success=True,
            message="漫画已下载",
            manga_id=manga_id,
            file_path=manga.cbz_file_path
        )
    
    crawler = MangaCrawler()
    downloader = MangaDownloader()
    
    try:
        # 登录
        if not crawler.login(settings.manga_username, settings.manga_password):
            raise HTTPException(status_code=401, detail="登录失败")
        
        # 标记为下载中
        manga.download_status = "downloading"
        manga.downloaded_pages = manga.downloaded_pages or 0
        db.commit()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"开始下载: {manga.title}")
        if manga.downloaded_pages > 0:
            logger.info(f"断点续传: 已下载 {manga.downloaded_pages} 页")
        logger.info(f"{'='*60}\n")
        
        # 获取漫画详情（如果缺失）
        if not manga.page_count or not manga.cover_image_url:
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
        images = crawler.get_manga_images(manga.manga_url)
        
        if not images:
            manga.download_status = "failed"
            db.commit()
            raise HTTPException(status_code=500, detail="无法获取图片列表")
        
        # 🔥 使用生成器下载：边下载边保存，支持断点续传
        cbz_path = None
        cover_path = None
        
        for progress in downloader.download_manga_stream(manga.title, images, author=manga.author, resume=True):
            status = progress.get('status')
            
            # 更新下载进度
            if 'downloaded_count' in progress:
                manga.downloaded_pages = progress['downloaded_count']
                db.commit()  # 🔥 实时保存进度！
            
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
                manga.downloaded_pages = len(images)
                db.commit()
                
                logger.info(f"\n{'='*60}")
                logger.info(f"✅ 下载完成: {manga.title}")
                logger.info(f"文件大小: {file_size / 1024 / 1024:.2f} MB")
                logger.info(f"{'='*60}\n")
            
            # 下载失败
            elif status == 'error':
                manga.download_status = "failed"
                db.commit()
                raise HTTPException(status_code=500, detail=progress.get('message', '下载失败'))
        
        if not cbz_path:
            manga.download_status = "failed"
            db.commit()
            raise HTTPException(status_code=500, detail="下载失败")
        
        return DownloadResponse(
            success=True,
            message="下载成功",
            manga_id=manga_id,
            file_path=cbz_path
        )
    except Exception as e:
        manga.download_status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        crawler.close()


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

