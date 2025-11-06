from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import manga, sync, download, recent_updates
from app.database import Base, engine
from app.utils.logger import logger
from app import models  # 🔥 必须导入models，否则Base.metadata找不到表

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="漫画下载管理器API", version="1.0.0")

# 启动日志
logger.info("=" * 60)
logger.info("漫画下载管理器 API 启动")
logger.info(f"数据库: {settings.database_url}")
logger.info("=" * 60)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(manga.router)
app.include_router(sync.router)
app.include_router(download.router)
app.include_router(recent_updates.router)


@app.get("/")
def root():
    return {"message": "漫画下载管理器API"}


@app.get("/health")
def health():
    return {"status": "ok"}
