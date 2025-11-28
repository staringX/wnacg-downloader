from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MangaBase(BaseModel):
    title: str
    author: str
    manga_url: str
    page_count: Optional[int] = None
    updated_at: Optional[datetime] = None
    cover_image_url: Optional[str] = None


class MangaCreate(MangaBase):
    pass


class MangaUpdate(BaseModel):
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    updated_at: Optional[datetime] = None
    is_downloaded: Optional[bool] = None
    downloaded_at: Optional[datetime] = None
    cover_image_path: Optional[str] = None
    cbz_file_path: Optional[str] = None


class MangaResponse(MangaBase):
    id: str
    file_size: Optional[int] = None
    is_downloaded: bool = False
    downloaded_at: Optional[datetime] = None
    cover_image_path: Optional[str] = None
    preview_image_url: Optional[str] = None  # 前端期望的字段名
    is_favorited: bool = False  # 是否已收藏到网站
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """自定义ORM转换，确保字段映射正确"""
        # 安全获取 is_favorited 属性（RecentUpdate 模型没有这个字段）
        is_favorited = getattr(obj, 'is_favorited', False) or False
        
        # 兼容Pydantic v2和v1
        try:
            # 尝试使用Pydantic v2的model_validate
            return cls.model_validate({
                'id': obj.id,
                'title': obj.title,
                'author': obj.author,
                'manga_url': obj.manga_url,
                'file_size': getattr(obj, 'file_size', None),
                'page_count': obj.page_count,
                'updated_at': obj.updated_at,
                'is_downloaded': getattr(obj, 'is_downloaded', False) or False,
                'downloaded_at': getattr(obj, 'downloaded_at', None),
                'cover_image_url': obj.cover_image_url,
                'cover_image_path': getattr(obj, 'cover_image_path', None),
                'preview_image_url': obj.cover_image_url,  # 使用cover_image_url作为预览图
                'is_favorited': is_favorited,
            })
        except AttributeError:
            # 回退到直接构造
            return cls(
                id=obj.id,
                title=obj.title,
                author=obj.author,
                manga_url=obj.manga_url,
                file_size=getattr(obj, 'file_size', None),
                page_count=obj.page_count,
                updated_at=obj.updated_at,
                is_downloaded=getattr(obj, 'is_downloaded', False) or False,
                downloaded_at=getattr(obj, 'downloaded_at', None),
                cover_image_url=obj.cover_image_url,
                cover_image_path=getattr(obj, 'cover_image_path', None),
                preview_image_url=obj.cover_image_url,
                is_favorited=is_favorited,
            )


class SyncResponse(BaseModel):
    success: bool
    message: str
    added_count: int = 0
    updated_count: int = 0


class DownloadResponse(BaseModel):
    success: bool
    message: str
    manga_id: str
    file_path: Optional[str] = None


class BatchDownloadResponse(BaseModel):
    success: bool
    message: str
    total: int
    success_count: int
    failed_count: int


class TaskResponse(BaseModel):
    """任务状态响应"""
    id: str
    task_type: str
    status: str  # pending, running, completed, failed
    progress: int
    total_items: Optional[int] = None
    completed_items: int
    message: Optional[str] = None
    error_message: Optional[str] = None
    manga_id: Optional[str] = None
    manga_ids: Optional[str] = None
    result_data: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TaskCreateResponse(BaseModel):
    """创建任务响应"""
    success: bool
    task_id: str
    message: str
