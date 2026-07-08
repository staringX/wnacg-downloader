import os

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings


def _create_engine():
    """データベースエンジンを生成（既定 SQLite、DATABASE_URL で PostgreSQL も可）"""
    url = settings.database_url
    if url.startswith("sqlite"):
        # DB ファイルの親ディレクトリを作成（例: ./data/manga.db）
        db_path = url.split("///", 1)[-1]
        if db_path and db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)) or ".", exist_ok=True)
        # FastAPI + バックグラウンドスレッド（下载执行器・同期）からアクセスするため
        # check_same_thread を無効化。書き込み競合は WAL + busy_timeout で吸収する。
        eng = create_engine(
            url,
            echo=False,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(eng, "connect")
        def _set_sqlite_pragma(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return eng

    # PostgreSQL 等のサーバ型 DB
    return create_engine(
        url,
        echo=False,
        pool_pre_ping=True,  # 连接前检查可用性
        pool_size=10,  # 连接池大小
        max_overflow=20  # 最大溢出连接数
    )


# 创建数据库引擎
engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
