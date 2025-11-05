from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import manga
from app.database import Base, engine

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="漫画下载管理器API", version="1.0.0")

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


@app.get("/")
def root():
    return {"message": "漫画下载管理器API"}


@app.get("/health")
def health():
    return {"status": "ok"}
