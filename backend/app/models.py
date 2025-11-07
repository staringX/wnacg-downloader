from sqlalchemy import Column, String, Integer, Boolean, DateTime, BigInteger
from sqlalchemy.sql import func
from app.database import Base
import uuid


def generate_id():
    return str(uuid.uuid4())


class Manga(Base):
    __tablename__ = "mangas"

    id = Column(String, primary_key=True, default=generate_id)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    manga_url = Column(String, nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=True)  # 文件大小（字节）
    page_count = Column(Integer, nullable=True)  # 页数
    updated_at = Column(DateTime, nullable=True)  # 更新日期
    is_downloaded = Column(Boolean, default=False, index=True)
    downloaded_at = Column(DateTime, nullable=True)
    cover_image_url = Column(String, nullable=True)  # 封面图片URL
    cover_image_path = Column(String, nullable=True)  # 封面图片本地路径
    cbz_file_path = Column(String, nullable=True)  # CBZ文件路径
    
    # 断点续传支持
    download_status = Column(String, default="not_started", index=True)  # not_started, downloading, completed, failed
    downloaded_pages = Column(Integer, default=0)  # 已下载的页数
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at_db = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RecentUpdate(Base):
    """最近更新表 - 存储收藏作者的新作品"""
    __tablename__ = "recent_updates"

    id = Column(String, primary_key=True, default=generate_id)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    manga_url = Column(String, nullable=False, unique=True)
    page_count = Column(Integer, nullable=True)  # 页数
    updated_at = Column(DateTime, nullable=True, index=True)  # 更新日期（用于筛选）
    cover_image_url = Column(String, nullable=True)  # 封面图片URL
    cover_image_path = Column(String, nullable=True)  # 封面图片本地路径
    
    # 下载相关（可选，如果用户想下载最近更新的作品）
    is_downloaded = Column(Boolean, default=False, index=True)
    downloaded_at = Column(DateTime, nullable=True)
    file_size = Column(BigInteger, nullable=True)
    cbz_file_path = Column(String, nullable=True)
    download_status = Column(String, default="not_started", index=True)
    downloaded_pages = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at_db = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Task(Base):
    """任务状态表 - 存储同步和下载任务的状态"""
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=generate_id)
    task_type = Column(String, nullable=False, index=True)  # sync, download, batch_download
    status = Column(String, nullable=False, index=True)  # pending, running, completed, failed
    progress = Column(Integer, default=0)  # 进度百分比 0-100
    total_items = Column(Integer, nullable=True)  # 总项目数
    completed_items = Column(Integer, default=0)  # 已完成项目数
    message = Column(String, nullable=True)  # 状态消息
    error_message = Column(String, nullable=True)  # 错误消息
    
    # 任务关联的漫画ID（用于download和batch_download）
    manga_id = Column(String, nullable=True, index=True)
    manga_ids = Column(String, nullable=True)  # JSON格式的ID列表（用于batch_download）
    
    # 任务结果数据（JSON格式）
    result_data = Column(String, nullable=True)  # JSON格式的结果数据
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)  # 完成时间
