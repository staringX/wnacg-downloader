"""最近更新相关路由"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models import Manga, RecentUpdate
from app.schemas import MangaResponse, SyncResponse, TaskCreateResponse
from app.crawler.base import MangaCrawler
from app.config import settings
from app.utils.logger import logger, get_error_message
from app.services.task_manager import TaskManager

router = APIRouter(prefix="/api", tags=["recent-updates"])


@router.get("/recent-updates", response_model=List[MangaResponse])
def get_recent_updates(db: Session = Depends(get_db)):
    """获取最近更新（从RecentUpdate表读取）"""
    recent_updates = db.query(RecentUpdate).order_by(RecentUpdate.updated_at.desc()).all()
    return [MangaResponse.from_orm(update) for update in recent_updates]


def _execute_sync_recent_updates_task(task_id: str, db: Session):
    """执行同步最近更新任务（后台任务）"""
    from app.database import SessionLocal
    
    if not db:
        db = SessionLocal()
    
    try:
        # 检查是否有正在运行的同步最近更新任务
        running_tasks = TaskManager.get_running_tasks(db, "sync_recent_updates")
        if running_tasks and running_tasks[0].id != task_id:
            TaskManager.update_task(db, task_id, status="failed", error_message="已有同步最近更新任务正在运行")
            return
        
        TaskManager.update_task(db, task_id, status="running", message="开始同步最近更新...")
        
        # 获取所有已收藏的作者
        authors = db.query(Manga.author).distinct().all()
        author_list = [a[0] for a in authors]
        
        # 排除用户自定义的分类（如"优秀"），只保留真正的作者名
        excluded_categories = ["优秀", "全部", "管理分類", "書架", "书架", "我的書架"]
        author_list = [author for author in author_list if author not in excluded_categories]
        
        if not author_list:
            TaskManager.update_task(db, task_id, status="completed", message="没有找到已收藏的作者（已排除自定义分类）", progress=100)
            return
        
        total_authors = len(author_list)
        TaskManager.update_task(db, task_id, total_items=total_authors, message=f"找到 {total_authors} 个已收藏的作者，开始搜索更新...")
        
        # 获取每个作者收藏夹中最新的漫画的更新日期
        author_latest_dates = {}
        for author in author_list:
            latest_manga = db.query(Manga).filter(
                Manga.author == author
            ).order_by(Manga.updated_at.desc()).first()
            
            if latest_manga and latest_manga.updated_at:
                author_latest_dates[author] = latest_manga.updated_at
            else:
                author_latest_dates[author] = datetime(2000, 1, 1)
        
        # 初始化爬虫
        crawler = MangaCrawler()
        if not crawler.login(settings.manga_username, settings.manga_password):
            TaskManager.update_task(db, task_id, status="failed", error_message="登录失败")
            return
        
        total_added = 0
        total_deleted = 0
        processed_authors = 0
        
        # 对每个作者进行搜索和更新
        for idx, author in enumerate(author_list, 1):
            try:
                since_date = author_latest_dates.get(author, datetime(2000, 1, 1))
                logger.info(f"搜索作者: {author}, 截止日期: {since_date}")
                
                TaskManager.update_task(
                    db, task_id,
                    completed_items=idx - 1,
                    progress=int((idx - 1) / total_authors * 90),
                    message=f"正在搜索作者 {author} ({idx}/{total_authors})..."
                )
                
                # 搜索作者并获取更新
                new_mangas = crawler.search_author_updates(author, since_date)
                
                if not new_mangas:
                    logger.info(f"  作者 {author} 没有找到新更新")
                    continue
                
                logger.info(f"  作者 {author} 找到 {len(new_mangas)} 个新更新")
                
                # 保存新更新到数据库
                for manga_data in new_mangas:
                    # 检查是否已存在（通过manga_url）
                    existing = db.query(RecentUpdate).filter(
                        RecentUpdate.manga_url == manga_data['manga_url']
                    ).first()
                    
                    if existing:
                        # 更新现有记录
                        existing.title = manga_data['title']
                        existing.updated_at = manga_data['updated_at']
                        existing.page_count = manga_data.get('page_count')
                        existing.cover_image_url = manga_data.get('cover_image_url')
                        total_added += 1
                    else:
                        # 创建新记录
                        try:
                            new_update = RecentUpdate(
                                title=manga_data['title'],
                                author=manga_data['author'],
                                manga_url=manga_data['manga_url'],
                                updated_at=manga_data['updated_at'],
                                page_count=manga_data.get('page_count'),
                                cover_image_url=manga_data.get('cover_image_url'),
                                is_downloaded=False
                            )
                            db.add(new_update)
                            total_added += 1
                        except Exception as e:
                            # 处理可能的唯一约束冲突（并发情况下可能发生）
                            db.rollback()
                            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                                logger.warning(f"  并发冲突，跳过: {manga_data.get('title', 'Unknown')[:50]}")
                                continue
                            else:
                                raise
                
                db.commit()
                
                # 删除早于截止日期的记录（仅限该作者）
                deleted_count = db.query(RecentUpdate).filter(
                    RecentUpdate.author == author,
                    RecentUpdate.updated_at < since_date
                ).delete()
                
                if deleted_count > 0:
                    db.commit()
                    total_deleted += deleted_count
                    logger.info(f"  作者 {author} 删除了 {deleted_count} 条旧记录")
                
                processed_authors += 1
                
            except Exception as e:
                logger.error(f"处理作者 {author} 时出错: {get_error_message(e)}")
                db.rollback()
                continue
        
        crawler.close()
        
        # 任务完成
        TaskManager.update_task(
            db, task_id,
            status="completed",
            progress=100,
            completed_items=total_authors,
            message=f"同步完成: 新增/更新 {total_added} 条，删除 {total_deleted} 条",
            result_data=f'{{"added_count": {total_added}, "deleted_count": {total_deleted}}}'
        )
        
        logger.info(f"同步最近更新任务完成: 新增/更新 {total_added} 条，删除 {total_deleted} 条")
        
    except Exception as e:
        logger.error(f"同步最近更新任务失败: {get_error_message(e)}")
        TaskManager.update_task(db, task_id, status="failed", error_message=get_error_message(e))
    finally:
        if db:
            db.close()


@router.post("/sync-recent-updates", response_model=TaskCreateResponse)
def sync_recent_updates(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    同步最近更新（异步任务模式）
    1. 获取所有已收藏的作者
    2. 对每个作者，找到收藏夹中最新的漫画的更新时间
    3. 搜索该作者，获取晚于该时间的所有漫画
    4. 保存新更新到RecentUpdate表
    5. 删除早于该时间的记录（仅从RecentUpdate表删除）
    """
    # 检查是否有正在运行的同步最近更新任务
    running_tasks = TaskManager.get_running_tasks(db, "sync_recent_updates")
    if running_tasks:
        raise HTTPException(status_code=409, detail=f"已有同步最近更新任务正在运行: {running_tasks[0].id}")
    
    # 创建任务
    task = TaskManager.create_task(db, task_type="sync_recent_updates")
    
    # 在后台执行同步任务
    background_tasks.add_task(_execute_sync_recent_updates_task, task.id, db)
    
    return TaskCreateResponse(
        success=True,
        task_id=task.id,
        message="同步最近更新任务已创建，正在后台执行"
    )

