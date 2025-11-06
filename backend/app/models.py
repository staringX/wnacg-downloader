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
