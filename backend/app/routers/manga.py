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

router = APIRouter(prefix="/api", tags=["manga"])


@router.get("/mangas", response_model=List[MangaResponse])
def get_mangas(db: Session = Depends(get_db)):
    """获取所有漫画"""
    mangas = db.query(Manga).all()
    return [MangaResponse.from_orm(manga) for manga in mangas]


@router.post("/sync", response_model=SyncResponse)
def sync_collection(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """同步收藏夹"""
    if not SELENIUM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Selenium未安装，无法使用爬虫功能")
    
    crawler = MangaCrawler()
    
    try:
        # 登录
        if not crawler.login(settings.manga_username, settings.manga_password):
            raise HTTPException(status_code=401, detail="登录失败")
        
        # 获取收藏夹
        collection = crawler.get_collection()
        
        print(f"收藏夹获取完成，共 {len(collection)} 个漫画")
        if len(collection) == 0:
            print("警告：收藏夹为空，可能是无法访问书架页面或账号没有收藏")
        
        added_count = 0
        updated_count = 0
        
        print(f"\n开始实时同步处理...")
        
        # 实时处理：边爬取边保存，每个漫画处理完立即提交
        for idx, item in enumerate(collection, 1):
            try:
                # 检查是否已存在
                existing = db.query(Manga).filter(Manga.manga_url == item['manga_url']).first()
                
                if existing:
                    # 已存在，仅更新基本信息（如果需要）
                    if item.get('page_count') and not existing.page_count:
                        existing.page_count = item['page_count']
                        db.commit()
                    updated_count += 1
                    print(f"  [{idx}/{len(collection)}] ⟳ 已存在: {item['title'][:50]}")
                else:
                    # 新漫画，创建记录并立即保存
                    print(f"  [{idx}/{len(collection)}] ✚ 新增: {item['title'][:50]}")
                    
                    manga = Manga(
                        title=item['title'],
                        author=item['author'],
                        manga_url=item['manga_url'],
                        page_count=item.get('page_count')
                    )
                    db.add(manga)
                    db.commit()  # 立即提交基本信息，用户可以看到
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
                            db.commit()  # 立即提交详细信息
                            print(f"       ✓ 详情: 页数={manga.page_count}, 更新={str(manga.updated_at)[:10] if manga.updated_at else 'N/A'}")
                        else:
                            print(f"       ⚠ 无法获取详细信息")
                            
                    except Exception as detail_error:
                        print(f"       ⚠ 获取详情失败: {detail_error}")
                        # 详情获取失败不影响基本记录的保存，继续处理下一个
                    
            except Exception as e:
                print(f"  [{idx}/{len(collection)}] ✗ 处理失败: {item.get('title', 'Unknown')[:50]} - {e}")
                db.rollback()  # 回滚当前失败的事务
                continue
        
        print(f"\n同步完成：新增 {added_count} 个，更新 {updated_count} 个")
        
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
