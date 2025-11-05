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
    is_downloaded: bool
    downloaded_at: Optional[datetime] = None
    cover_image_path: Optional[str] = None
    
    class Config:
        from_attributes = True


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
