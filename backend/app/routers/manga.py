from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel
import os
import time
import uuid
from app.database import get_db

# 可选的Selenium导入
try:
    from selenium.webdriver.common.by import By
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("警告: Selenium未安装，爬虫功能将不可用")
from app.models import Manga
from app.schemas import (
    MangaResponse, SyncResponse, DownloadResponse, 
    BatchDownloadResponse, MangaUpdate
)
from app.crawler.base import MangaCrawler
from app.utils.downloader import MangaDownloader
from app.config import settings
from app.utils.logger import logger

router = APIRouter(prefix="/api", tags=["manga"])


@router.get("/mangas", response_model=List[MangaResponse])
def get_mangas(db: Session = Depends(get_db)):
    """获取所有漫画"""
    mangas = db.query(Manga).all()
    return [MangaResponse.from_orm(manga) for manga in mangas]


def verify_local_files(db: Session):
    """
    验证本地文件与数据库状态的一致性
    检查标记为"已下载"的漫画，其CBZ文件是否真实存在
    
    Returns:
        tuple: (verified_count, fixed_count, missing_files)
    """
    logger.info("=" * 60)
    logger.info("开始验证本地文件完整性...")
    logger.info("=" * 60)
    
    from pathlib import Path
    
    # 查询所有标记为已下载的漫画
    downloaded_mangas = db.query(Manga).filter(
        Manga.is_downloaded == True
    ).all()
    
    if not downloaded_mangas:
        logger.info("没有已下载的漫画需要验证")
        return 0, 0, []
    
    logger.info(f"找到 {len(downloaded_mangas)} 个已下载的漫画记录")
    
    verified_count = 0
    fixed_count = 0
    missing_files = []
    
    for manga in downloaded_mangas:
        cbz_path = manga.cbz_file_path
        cover_path = manga.cover_image_path
        
        cbz_exists = False
        cover_exists = False
        
        # 检查CBZ文件是否存在
        if cbz_path:
            cbz_file = Path(cbz_path)
            cbz_exists = cbz_file.exists() and cbz_file.is_file()
        
        # 检查封面文件是否存在
        if cover_path:
            cover_file = Path(cover_path)
            cover_exists = cover_file.exists() and cover_file.is_file()
        
        # 如果CBZ文件不存在，重置下载状态
        if not cbz_exists:
            logger.warning(f"文件丢失: {manga.title[:50]} - 路径: {cbz_path}")
            
            # 重置下载状态
            manga.is_downloaded = False
            manga.download_status = "not_started"
            manga.downloaded_pages = 0
            manga.cbz_file_path = None
            manga.downloaded_at = None
            manga.file_size = None
            
            # 如果封面也不存在，清除封面路径
            if not cover_exists:
                manga.cover_image_path = None
            
            fixed_count += 1
            missing_files.append(manga.title)
        else:
            verified_count += 1
            logger.debug(f"验证通过: {manga.title[:50]}")
    
    # 提交所有更改
    if fixed_count > 0:
        db.commit()
        logger.warning(f"已重置 {fixed_count} 个丢失文件的下载状态")
    
    logger.info("=" * 60)
    logger.info(f"验证完成: {verified_count} 个完整, {fixed_count} 个需要重新下载")
    logger.info("=" * 60)
    
    return verified_count, fixed_count, missing_files


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
        verified_count, fixed_count, missing_files = verify_local_files(db)
        
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


@router.post("/sync", response_model=SyncResponse)
def sync_collection(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """同步收藏夹"""
    if not SELENIUM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Selenium未安装，无法使用爬虫功能")
    
    # 🔍 第一步：验证本地文件完整性
    try:
        verified_count, fixed_count, missing_files = verify_local_files(db)
    except Exception as e:
        logger.warning(f"文件验证失败: {e}")
        # 验证失败不影响同步，继续执行
    
    crawler = MangaCrawler()
    
    try:
        # 登录
        if not crawler.login(settings.manga_username, settings.manga_password):
            raise HTTPException(status_code=401, detail="登录失败")
        
        # 🚀 使用生成器：边爬取边保存，真正的实时同步！
        logger.info("=" * 60)
        logger.info("开始实时同步（生成器模式）")
        logger.info("提示：每爬取到一个漫画就会立即保存，刷新页面即可看到最新数据")
        logger.info("=" * 60)
        
        added_count = 0
        updated_count = 0
        processed_count = 0
        
        # 生成器：每yield一个漫画，立即处理并保存
        for item in crawler.get_collection_stream():
            processed_count += 1
            
            try:
                # 检查是否已存在
                existing = db.query(Manga).filter(Manga.manga_url == item['manga_url']).first()
                
                if existing:
                    # 已存在，仅更新基本信息（如果需要）
                    if item.get('page_count') and not existing.page_count:
                        existing.page_count = item['page_count']
                        db.commit()
                    updated_count += 1
                    logger.info(f"[{processed_count}] ⟳ 已存在: {item['title'][:50]}")
                else:
                    # 新漫画，创建记录并立即保存
                    logger.info(f"[{processed_count}] ✚ 新增: {item['title'][:50]}")
                    
                    manga = Manga(
                        title=item['title'],
                        author=item['author'],
                        manga_url=item['manga_url'],
                        page_count=item.get('page_count')
                    )
                    db.add(manga)
                    db.commit()  # 🔥 立即提交！用户刷新页面就能看到
                    db.refresh(manga)  # 刷新对象以获取ID
                    
                    added_count += 1
                    
                    # 立即获取详细信息（页数、更新日期、封面）
                    try:
                        details = crawler.get_manga_details(manga.manga_url)
                        
                        if details:
                            # 更新详细信息
                            if details.get('page_count'):
                                manga.page_count = details['page_count']
                            if details.get('updated_at'):
                                manga.updated_at = details['updated_at']
                            if details.get('cover_image_url'):
                                manga.cover_image_url = details['cover_image_url']
                            db.commit()  # 🔥 再次提交详情！
                            logger.debug(f"     ✓ 详情: 页数={manga.page_count}, 更新={str(manga.updated_at)[:10] if manga.updated_at else 'N/A'}")
                        else:
                            logger.warning(f"     ⚠ 无法获取详细信息: {manga.title[:30]}")
                            
                    except Exception as detail_error:
                        logger.warning(f"     ⚠ 获取详情失败: {detail_error}")
                        # 详情获取失败不影响基本记录的保存，继续处理下一个
                    
            except Exception as e:
                logger.error(f"[{processed_count}] ✗ 处理失败: {item.get('title', 'Unknown')[:50]} - {e}")
                db.rollback()  # 回滚当前失败的事务
                continue
        
        logger.info(f"同步完成：新增 {added_count} 个，更新 {updated_count} 个")
        
        return SyncResponse(
            success=True,
            message=f"同步完成：新增 {added_count} 个，更新 {updated_count} 个",
            added_count=added_count,
            updated_count=updated_count
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        crawler.close()


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
        
        print(f"\n{'='*60}")
        print(f"开始下载: {manga.title}")
        if manga.downloaded_pages > 0:
            print(f"断点续传: 已下载 {manga.downloaded_pages} 页")
        print(f"{'='*60}\n")
        
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
        
        for progress in downloader.download_manga_stream(manga.title, images, resume=True):
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
                
                print(f"\n{'='*60}")
                print(f"✅ 下载完成: {manga.title}")
                print(f"文件大小: {file_size / 1024 / 1024:.2f} MB")
                print(f"{'='*60}\n")
            
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


class BatchDownloadRequest(BaseModel):
    manga_ids: List[str]


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
    
    print(f"\n{'='*60}")
    print(f"开始批量下载: {len(request.manga_ids)} 本漫画")
    print(f"{'='*60}\n")
    
    # 逐个下载，每完成一个立即保存
    for idx, manga_id in enumerate(request.manga_ids, 1):
        try:
            manga = db.query(Manga).filter(Manga.id == manga_id).first()
            if not manga:
                print(f"[{idx}/{len(request.manga_ids)}] ✗ 跳过: 漫画ID {manga_id} 不存在")
                failed_count += 1
                continue
            
            print(f"\n[{idx}/{len(request.manga_ids)}] 处理: {manga.title}")
            
            # 如果已经下载完成，跳过
            if manga.download_status == "completed" and manga.is_downloaded:
                print(f"  ⏭️  已下载，跳过")
                success_count += 1
                continue
            
            # 调用单本下载（支持断点续传）
            try:
                result = download_manga(manga_id, background_tasks, db)
                if result.success:
                    success_count += 1
                    print(f"  ✅ 成功")
                else:
                    failed_count += 1
                    failed_titles.append(manga.title)
                    print(f"  ❌ 失败")
            except Exception as e:
                failed_count += 1
                failed_titles.append(manga.title)
                print(f"  ❌ 失败: {str(e)}")
                # 单本失败不影响其他漫画，继续处理下一本
                continue
                
        except Exception as e:
            print(f"[{idx}/{len(request.manga_ids)}] ✗ 处理失败: {e}")
            failed_count += 1
            continue
    
    print(f"\n{'='*60}")
    print(f"批量下载完成")
    print(f"成功: {success_count} 本")
    print(f"失败: {failed_count} 本")
    if failed_titles:
        print(f"失败列表: {', '.join(failed_titles[:5])}" + ("..." if len(failed_titles) > 5 else ""))
    print(f"{'='*60}\n")
    
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


@router.get("/recent-updates", response_model=List[MangaResponse])
def get_recent_updates(db: Session = Depends(get_db)):
    """获取最近更新（收藏作者的最近更新）"""
    # 获取所有已收藏的作者
    authors = db.query(Manga.author).distinct().all()
    author_list = [a[0] for a in authors]
    
    if not author_list:
        return []
    
    # 获取每个作者收藏夹中最新的漫画的更新日期
    author_latest_dates = {}
    for author in author_list:
        latest_manga = db.query(Manga).filter(
            Manga.author == author
        ).order_by(Manga.updated_at.desc()).first()
        
        if latest_manga and latest_manga.updated_at:
            author_latest_dates[author] = latest_manga.updated_at
    
    # 搜索每个作者，获取更新日期晚于收藏夹最新漫画的所有漫画
    crawler = MangaCrawler()
    recent_updates = []
    
    try:
        if not crawler.login(settings.manga_username, settings.manga_password):
            return []
        
        for author in author_list:
            # 搜索作者
            search_url = f"{crawler.base_url}/search-index.html?keywords={author}"
            crawler.driver.get(search_url)
            time.sleep(2)
            
            # 获取搜索结果
            manga_items = crawler.driver.find_elements(By.CSS_SELECTOR, "a[href*='photos-index']")
            
            for item in manga_items:
                try:
                    manga_url = item.get_attribute('href')
                    if not manga_url:
                        continue
                    
                    # 检查是否已在收藏夹中
                    existing = db.query(Manga).filter(
                        Manga.manga_url == manga_url
                    ).first()
                    
                    if existing:
                        continue  # 已在收藏夹中，跳过
                    
                    details = crawler.get_manga_details(manga_url)
                    
                    if details:
                        latest_date = author_latest_dates.get(author)
                        if latest_date and details.get('updated_at'):
                            if details['updated_at'] > latest_date:
                                # 创建临时Manga对象用于返回
                                temp_manga = Manga(
                                    id=str(uuid.uuid4()),
                                    title=details['title'],
                                    author=author,
                                    manga_url=manga_url,
                                    page_count=details.get('page_count'),
                                    updated_at=details.get('updated_at'),
                                    cover_image_url=details.get('cover_image_url'),
                                    is_downloaded=False
                                )
                                recent_updates.append(temp_manga)
                except Exception as e:
                    print(f"处理搜索结果项失败: {e}")
                    continue
    except Exception as e:
        print(f"获取最近更新失败: {e}")
    finally:
        crawler.close()
    
    # 转换为响应格式
    return [MangaResponse.from_orm(manga) for manga in recent_updates]


class AddToCollectionRequest(BaseModel):
    manga_url: str
    author: str


@router.post("/add-to-collection")
def add_to_collection(request: AddToCollectionRequest, db: Session = Depends(get_db)):
    """添加漫画到收藏夹（对应作者分类）"""
    crawler = MangaCrawler()
    
    try:
        if not crawler.login(settings.manga_username, settings.manga_password):
            raise HTTPException(status_code=401, detail="登录失败")
        
        # 导航到漫画页面
        crawler.driver.get(request.manga_url)
        time.sleep(2)
        
        # 查找"加入書架"按钮
        add_button = crawler.driver.find_element(By.XPATH, "//*[contains(text(), '加入書架')]")
        add_button.click()
        time.sleep(1)
        
        # 选择作者分类
        # 这里需要根据实际网站UI来实现
        # 可能需要打开下拉菜单选择分类
        
        # 添加到数据库
        details = crawler.get_manga_details(request.manga_url)
        if details:
            manga = Manga(
                title=details['title'],
                author=request.author,
                manga_url=request.manga_url,
                page_count=details.get('page_count'),
                updated_at=details.get('updated_at'),
                cover_image_url=details.get('cover_image_url')
            )
            db.add(manga)
            db.commit()
            
            return {"success": True, "message": "已添加到收藏夹"}
        else:
            raise HTTPException(status_code=500, detail="无法获取漫画详情")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        crawler.close()


@router.delete("/manga/{manga_id}")
def delete_manga(manga_id: str, db: Session = Depends(get_db)):
    """删除漫画"""
    manga = db.query(Manga).filter(Manga.id == manga_id).first()
    if not manga:
        raise HTTPException(status_code=404, detail="漫画不存在")
    
    # 删除文件
    if manga.cbz_file_path and os.path.exists(manga.cbz_file_path):
        os.remove(manga.cbz_file_path)
    if manga.cover_image_path and os.path.exists(manga.cover_image_path):
        os.remove(manga.cover_image_path)
    
    db.delete(manga)
    db.commit()
    
    return {"success": True, "message": "删除成功"}
