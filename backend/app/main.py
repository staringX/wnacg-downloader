import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# 前端静态资源（方案B：FastAPI 集约配信）
# 构建产物（Vite dist）在 Docker 多阶段构建中被复制到 app/static。
# 存在时：挂载静态资源并对非 /api 路径做 SPA 回退到 index.html；
# 不存在时（本地仅跑后端）：回退为 JSON 根路由。
# ---------------------------------------------------------------------------
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIST", Path(__file__).resolve().parent / "static"))
INDEX_HTML = FRONTEND_DIR / "index.html"

if INDEX_HTML.exists():
    # Vite 资源默认输出到 dist/assets
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    def serve_index():
        return FileResponse(str(INDEX_HTML))

    # SPA 回退：非 /api、非 /health 的任意路径都返回 index.html
    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        # 未匹配到的 API 路径不应回退到 HTML，交给框架返回 404
        if full_path.startswith("api/") or full_path == "api":
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = FRONTEND_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(INDEX_HTML))

    logger.info(f"前端静态资源已挂载: {FRONTEND_DIR}")
else:
    @app.get("/")
    def root():
        return {"message": "漫画下载管理器API"}

    logger.info("未找到前端构建产物（开发模式仅提供 API）")
