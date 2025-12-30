from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import manga, sync, download, recent_updates, tasks
from app.routers.settings import router
from app.database import Base, engine, SessionLocal
from app.utils.logger import logger
from app import models  # 🔥 必须导入models，否则Base.metadata找不到表
from app.services.task_manager import TaskManager
from app.utils.migration import run_migrations

# 启动日志
logger.info("=" * 60)
logger.info("漫画下载管理器 API 启动")
logger.info(f"数据库: {settings.database_url}")
logger.info("=" * 60)


def init_on_startup():
    """启动时初始化操作"""
    logger.info("执行启动初始化...")
    
    # 1. 首先运行数据库自动迁移（类似于 JPA 的自动迁移）
    run_migrations()
    
    # 2. 清理过期的任务（因Docker重启等原因中断的任务）
    # 启动时清理所有pending/running任务，因为重启后这些任务肯定都中断了
    db = SessionLocal()
    try:
        cleaned_count = TaskManager.cleanup_stale_tasks(db, cleanup_all_on_startup=True)
        if cleaned_count > 0:
            logger.info(f"启动时清理了 {cleaned_count} 个中断的任务")
        else:
            logger.info("未发现需要清理的任务")
    except Exception as e:
        logger.error(f"清理过期任务时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()
    
    logger.info("启动初始化完成")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时的初始化操作
    init_on_startup()
    
    yield  # 应用运行
    
    # 关闭时的清理操作（如果需要）
    logger.info("应用正在关闭...")


app = FastAPI(
    title="漫画下载管理器API",
    version="1.0.0",
    lifespan=lifespan
)

# 如果lifespan没有执行，使用startup事件作为备用
@app.on_event("startup")
async def startup_event():
    """启动事件（备用方案）"""
    init_on_startup()

# CORS配置 - 允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(manga.router)
app.include_router(sync.router)
app.include_router(download.router)
app.include_router(recent_updates.router)
app.include_router(tasks.router)
app.include_router(router)


@app.get("/")
def root():
    return {"message": "漫画下载管理器API"}


@app.get("/health")
def health():
    return {"status": "ok"}
