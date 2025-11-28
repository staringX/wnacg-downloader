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


@router.post("/add-to-favorite")
def add_to_favorite(request, db: Session = Depends(get_db)):
    """将漫画添加到网站收藏夹（对应作者文件夹）
    
    流程：
    1. 从漫画URL提取aid（漫画ID）
    2. 获取收藏分类列表
    3. 根据作者名匹配对应的分类ID
    4. 提交收藏表单
    5. 更新数据库中的is_favorited字段
    """
    from pydantic import BaseModel
    
    class AddToFavoriteRequest(BaseModel):
        manga_id: str  # Manga表的ID
    
    try:
        # 查找漫画
        manga = db.query(Manga).filter(Manga.id == request.manga_id).first()
        if not manga:
            raise HTTPException(status_code=404, detail="漫画不存在")
        
        # 如果已经收藏，直接返回
        if manga.is_favorited:
            return {"success": True, "message": "漫画已收藏到网站"}
        
        # 使用收藏服务
        from app.services.favorite_service import FavoriteService
        favorite_service = FavoriteService()
        
        try:
            # 执行收藏
            success = favorite_service.add_to_favorite(manga.manga_url, manga.author)
            
            if success:
                # 更新数据库
                manga.is_favorited = True
                db.commit()
                return {"success": True, "message": "已成功收藏到网站"}
            else:
                raise HTTPException(status_code=500, detail="收藏失败，请检查日志")
        finally:
            favorite_service.close()
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"收藏漫画失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"收藏失败: {str(e)}")
