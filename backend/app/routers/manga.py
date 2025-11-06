"""漫画基础CRUD路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import os
import time
from app.database import get_db
from app.models import Manga
from app.schemas import MangaResponse
from app.crawler.base import MangaCrawler
from app.config import settings
from app.utils.logger import logger

router = APIRouter(prefix="/api", tags=["manga"])


@router.get("/mangas", response_model=List[MangaResponse])
def get_mangas(db: Session = Depends(get_db)):
    """获取所有漫画"""
    mangas = db.query(Manga).all()
    return [MangaResponse.from_orm(manga) for manga in mangas]


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


@router.post("/add-to-collection")
def add_to_collection(request, db: Session = Depends(get_db)):
    """添加漫画到收藏夹（对应作者分类）"""
    from pydantic import BaseModel
    
    class AddToCollectionRequest(BaseModel):
        manga_url: str
        author: str
    
    # 确保request是AddToCollectionRequest类型
    if not hasattr(request, 'manga_url') or not hasattr(request, 'author'):
        raise HTTPException(status_code=400, detail="Invalid request format")
    
    crawler = MangaCrawler()
    
    try:
        if not crawler.login(settings.manga_username, settings.manga_password):
            raise HTTPException(status_code=401, detail="登录失败")
        
        # 导航到漫画页面
        crawler.driver.get(request.manga_url)
        time.sleep(2)
        
        # 查找"加入書架"按钮
        from selenium.webdriver.common.by import By
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
