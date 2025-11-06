"""同步相关路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
from pydantic import BaseModel
from typing import List
from app.database import get_db
from app.models import Manga
from app.schemas import SyncResponse
from app.crawler.base import MangaCrawler
from app.config import settings
from app.utils.logger import logger

router = APIRouter(prefix="/api", tags=["sync"])


class VerifyResponse(BaseModel):
    success: bool
    message: str
    verified_count: int
    fixed_count: int
    missing_files: List[str]


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
def sync_collection(db: Session = Depends(get_db)):
    """同步收藏夹"""
    try:
        from selenium.webdriver.common.by import By
        SELENIUM_AVAILABLE = True
    except ImportError:
        SELENIUM_AVAILABLE = False
    
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

