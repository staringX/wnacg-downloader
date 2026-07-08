from pydantic_settings import BaseSettings
from typing import List
import json
from pydantic import field_validator


class Settings(BaseSettings):
    # 数据库配置 - 默认 SQLite（单用户・低写入频度で十分）。
    # PostgreSQL を使う場合は環境変数 DATABASE_URL で指定（例: postgresql://user:pass@db:5432/manga_db）
    database_url: str = "sqlite:///./data/manga.db"
    
    # 漫画网站账号（必须通过环境变量配置）
    manga_username: str = ""
    manga_password: str = ""
    
    # 发布页地址
    publish_page_url: str = "https://wn01.link"
    
    # 下载目录
    download_dir: str = "./downloads"
    
    # 封面保存目录
    cover_dir: str = "./covers"
    
    # 下载线程数（用于并发下载图片）
    download_threads: int = 5
    
    # 获取原图链接的并发线程数（用于并发获取原图URL）
    image_fetch_threads: int = 3

    # 一括ダウンロード（詳細ページの「下載漫畫」→ ZIP 直接取得）を使うか。
    # False にすると従来の 1 ページずつ方式のみで動作する（保険用トグル）。
    # 一括の全線路が失敗した場合は自動的に従来方式へフォールバックする。
    archive_download_enabled: bool = True

    # レート制限（サイト負荷への配慮）。**漫画ダウンロード時のみ**適用。リクエスト間の最小間隔[秒]。0 で無制限。
    # 収藏夹同期・検索などのスキャン動作は軽量なため制限しない（HttpClient は throttle 無し）。
    #   request_min_interval      : DL 時の view ページ取得（サイト本体）への最小間隔
    #   image_request_min_interval: DL 時の画像バイナリ取得（CDN）への最小間隔
    # 並行数に関わらず実効レートは 1/間隔[req/s] に頭打ちになる（既定 0.3s ≈ 3.3 req/s）。
    request_min_interval: float = 0.3
    image_request_min_interval: float = 0.3
    
    # API配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
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
