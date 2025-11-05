from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # 数据库配置 - 默认使用SQLite便于本地测试
    database_url: str = "sqlite:///./manga.db"
    
    # 漫画网站账号
    manga_username: str = "lilifan456"
    manga_password: str = "a2658208"
    
    # 发布页地址
    publish_page_url: str = "https://wn01.link"
    
    # 下载目录
    download_dir: str = "./downloads"
    
    # 封面保存目录
    cover_dir: str = "./covers"
    
    # API配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
