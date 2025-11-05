from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel
import os
import time
from selenium.webdriver.common.by import By
from app.database import get_db
from app.models import Manga
from app.schemas import (
    MangaResponse, SyncResponse, DownloadResponse, 
    BatchDownloadResponse, MangaUpdate
)
from app.crawler.base import MangaCrawler
from app.utils.downloader import MangaDownloader
from app.config import settings

router = APIRouter(prefix="/api", tags=["manga"])


@router.get("/mangas", response_model=List[MangaResponse])
def get_mangas(db: Session = Depends(get_db)):
    """获取所有漫画"""
    mangas = db.query(Manga).all()
    return mangas


@router.post("/sync", response_model=SyncResponse)
def sync_collection(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """同步收藏夹"""
    crawler = MangaCrawler()
    
    try:
        # 登录
        if not crawler.login(settings.manga_username, settings.manga_password):
            raise HTTPException(status_code=401, detail="登录失败")
        
        # 获取收藏夹
        collection = crawler.get_collection()
        
        added_count = 0
        updated_count = 0
        
        for item in collection:
            # 检查是否已存在
            existing = db.query(Manga).filter(Manga.manga_url == item['manga_url']).first()
            
            if existing:
                # 更新信息
                if item.get('page_count'):
                    existing.page_count = item['page_count']
                updated_count += 1
            else:
                # 创建新记录
                manga = Manga(
                    title=item['title'],
                    author=item['author'],
                    manga_url=item['manga_url'],
                    page_count=item.get('page_count')
                )
                db.add(manga)
                added_count += 1
        
        db.commit()
        
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
    """下载单个漫画"""
    manga = db.query(Manga).filter(Manga.id == manga_id).first()
    if not manga:
        raise HTTPException(status_code=404, detail="漫画不存在")
    
    if manga.is_downloaded:
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
        
        # 获取图片列表
        images = crawler.get_manga_images(manga.manga_url)
        
        if not images:
            raise HTTPException(status_code=500, detail="无法获取图片列表")
        
        # 下载并打包
        cbz_path, cover_path = downloader.download_manga(manga.title, images)
        
        if not cbz_path:
            raise HTTPException(status_code=500, detail="下载失败")
        
        # 更新数据库
        manga.is_downloaded = True
        manga.downloaded_at = datetime.now()
        manga.cbz_file_path = cbz_path
        manga.cover_image_path = cover_path
        manga.file_size = downloader.get_file_size(cbz_path)
        
        db.commit()
        
        return DownloadResponse(
            success=True,
            message="下载成功",
            manga_id=manga_id,
            file_path=cbz_path
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        crawler.close()


class BatchDownloadRequest(BaseModel):
    manga_ids: List[str]


@router.post("/download/batch", response_model=BatchDownloadResponse)
def download_batch(request: BatchDownloadRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """批量下载漫画"""
    success_count = 0
    failed_count = 0
    
    for manga_id in request.manga_ids:
        try:
            download_manga(manga_id, background_tasks, db)
            success_count += 1
        except:
            failed_count += 1
    
    return BatchDownloadResponse(
        success=True,
        message=f"批量下载完成：成功 {success_count}，失败 {failed_count}",
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
                    details = crawler.get_manga_details(manga_url)
                    
                    if details:
                        latest_date = author_latest_dates.get(author)
                        if latest_date and details.get('updated_at'):
                            if details['updated_at'] > latest_date:
                                # 检查是否已在收藏夹中
                                existing = db.query(Manga).filter(
                                    Manga.manga_url == manga_url
                                ).first()
                                
                                if not existing:
                                    recent_updates.append(details)
                except:
                    continue
    except Exception as e:
        print(f"获取最近更新失败: {e}")
    finally:
        crawler.close()
    
    return recent_updates


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
