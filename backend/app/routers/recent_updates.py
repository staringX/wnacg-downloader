"""最近更新相关路由"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import RecentUpdate, Manga
from app.schemas import MangaResponse, TaskCreateResponse
from app.services.task_manager import TaskManager
from app.services.recent_updates_singleton import recent_updates_singleton
from app.services.recent_updates_service import RecentUpdatesService
from app.services.download_queue import download_queue_manager
from app.services.download_service import DownloadService
from app.services.concurrency import is_any_sync_running, has_active_downloads
from app.utils.logger import logger

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
    对每个已收藏的作者：
    1. 删除RecentUpdate中早于「收藏夹最新作更新日」的记录（掃除）
    2. 以「RecentUpdate侧该作者最新作更新日」（无则用收藏夹最新作）为截止日，
       爬取该作者，仅追加更新日更晚的作品，遇到更旧的作品即停止翻页
    """
    # 相互排他：他の同期が実行中なら拒否
    if is_any_sync_running():
        raise HTTPException(status_code=409, detail="已有更新任务正在运行，请稍后再试")
    # 相互排他：ダウンロード中は更新不可
    if has_active_downloads(db):
        raise HTTPException(status_code=409, detail="下载进行中，无法检索新作")

    # 创建任务
    task = TaskManager.create_task(db, task_type="sync_recent_updates")
    
    # 在后台执行同步任务
    background_tasks.add_task(RecentUpdatesService.execute_sync_recent_updates_task, task.id, db)
    
    return TaskCreateResponse(
        success=True,
        task_id=task.id,
        message="同步最近更新任务已创建，正在后台执行"
    )


@router.post("/download-from-update/{update_id}", response_model=TaskCreateResponse)
def download_from_update(update_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    从最近更新下载漫画
    
    功能：
    1. 从RecentUpdate表查找漫画
    2. 如果Manga表中不存在，则添加到Manga表，标记为is_favorited=false
    3. 将漫画加入下载队列
    4. 执行下载
    """
    # 相互排他：更新进行中はダウンロード不可
    if is_any_sync_running():
        raise HTTPException(status_code=409, detail="更新进行中，无法下载")

    # 查找最近更新记录
    recent_update = db.query(RecentUpdate).filter(RecentUpdate.id == update_id).first()
    if not recent_update:
        raise HTTPException(status_code=404, detail="最近更新记录不存在")
    
    # 检查Manga表中是否已存在（通过manga_url）
    existing_manga = db.query(Manga).filter(Manga.manga_url == recent_update.manga_url).first()
    
    if existing_manga:
        # 已存在，直接使用现有的manga_id
        manga_id = existing_manga.id
        logger.info(f"漫画已存在于Manga表，使用现有记录: {existing_manga.title}")
    else:
        # 不存在，添加到Manga表，标记为is_favorited=false
        try:
            new_manga = Manga(
                title=recent_update.title,
                author=recent_update.author,
                manga_url=recent_update.manga_url,
                page_count=recent_update.page_count,
                updated_at=recent_update.updated_at,
                cover_image_url=recent_update.cover_image_url,
                is_favorited=False  # 标记为未收藏到网站
            )
            db.add(new_manga)
            db.commit()
            db.refresh(new_manga)
            manga_id = new_manga.id
            logger.info(f"已将最近更新添加到Manga表: {new_manga.title} (is_favorited=False)")
        except Exception as e:
            db.rollback()
            # 处理可能的唯一约束冲突（并发情况下可能发生）
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                # 重新查询
                existing_manga = db.query(Manga).filter(Manga.manga_url == recent_update.manga_url).first()
                if existing_manga:
                    manga_id = existing_manga.id
                    logger.info(f"并发冲突，使用现有记录: {existing_manga.title}")
                else:
                    raise HTTPException(status_code=500, detail="添加漫画到Manga表失败")
            else:
                raise HTTPException(status_code=500, detail=f"添加漫画到Manga表失败: {str(e)}")
    
    # 将漫画加入下载队列
    task = download_queue_manager.add_to_queue(db, manga_id)
    
    if not task:
        # 漫画已下载
        manga = db.query(Manga).filter(Manga.id == manga_id).first()
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


@router.post("/add-update-to-favorite/{update_id}")
def add_update_to_favorite(update_id: str, db: Session = Depends(get_db)):
    """将最近更新的漫画收藏到网站（对应作者文件夹）

    与 /api/add-to-favorite 的区别：本接口以 RecentUpdate 表的 id 为入参，
    因为最近更新条目通常尚未进入 Manga 表（拥有独立的 uuid）。
    收藏成功后会同步更新 RecentUpdate.is_favorited，以及（若存在）
    通过 manga_url 匹配到的 Manga 行的 is_favorited。
    """
    recent_update = db.query(RecentUpdate).filter(RecentUpdate.id == update_id).first()
    if not recent_update:
        raise HTTPException(status_code=404, detail="最近更新记录不存在")

    # 已收藏则直接返回
    if recent_update.is_favorited:
        return {"success": True, "message": "漫画已收藏到网站"}

    from app.services.favorite_service import FavoriteService
    favorite_service = FavoriteService()
    try:
        success = favorite_service.add_to_favorite(recent_update.manga_url, recent_update.author)
        if not success:
            raise HTTPException(status_code=500, detail="收藏失败，请检查日志")

        # 更新最近更新记录
        recent_update.is_favorited = True

        # 同步更新 Manga 表中的对应记录（如果已存在）
        existing_manga = db.query(Manga).filter(Manga.manga_url == recent_update.manga_url).first()
        if existing_manga and not existing_manga.is_favorited:
            existing_manga.is_favorited = True

        db.commit()
        return {"success": True, "message": "已成功收藏到网站"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"收藏最近更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"收藏失败: {str(e)}")
    finally:
        favorite_service.close()

