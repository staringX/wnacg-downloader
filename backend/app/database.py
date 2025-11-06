from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,  # 连接前检查可用性
    pool_size=10,  # 连接池大小
    max_overflow=20  # 最大溢出连接数
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
