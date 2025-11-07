from pydantic_settings import BaseSettings
from typing import List
import json
from pydantic import field_validator


class Settings(BaseSettings):
    # 数据库配置 - PostgreSQL
    database_url: str = "postgresql://manga_user:manga_pass@db:5432/manga_db"
    
    # 漫画网站账号（必须通过环境变量配置）
    manga_username: str = ""
    manga_password: str = ""
    
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
    
    # 最近更新搜索时排除的分类/作者名（环境变量可以是JSON数组或逗号分隔的字符串）
    excluded_categories: List[str] = [
        "优秀", "全部", "管理分類", "書架", "书架", "我的書架",
        "一般", "真人", "同人"
    ]
    
    @field_validator('excluded_categories', mode='before')
    @classmethod
    def parse_excluded_categories(cls, v):
        """解析排除分类配置（支持JSON数组或逗号分隔的字符串）"""
        if isinstance(v, str):
            # 尝试解析为JSON数组
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            # 尝试解析为逗号分隔的字符串
            if ',' in v:
                return [item.strip() for item in v.split(',') if item.strip()]
            # 单个字符串
            return [v.strip()] if v.strip() else []
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 验证必填字段
        if not self.manga_username:
            raise ValueError(
                "MANGA_USERNAME 环境变量未设置。请创建 .env 文件并设置 MANGA_USERNAME。"
                "可以参考 .env.example 文件。"
            )
        if not self.manga_password:
            raise ValueError(
                "MANGA_PASSWORD 环境变量未设置。请创建 .env 文件并设置 MANGA_PASSWORD。"
                "可以参考 .env.example 文件。"
            )


settings = Settings()
