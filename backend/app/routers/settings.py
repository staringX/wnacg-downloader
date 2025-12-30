"""设置路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AppConfig
from app.schemas import AppConfigResponse, AppConfigUpdate
from app.utils.logger import logger

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=AppConfigResponse)
def get_settings(db: Session = Depends(get_db)):
    """获取应用配置"""
    config = db.query(AppConfig).filter(AppConfig.id == "singleton").first()
    
    if not config:
        # 如果不存在，创建默认配置
        config = AppConfig(id="singleton")
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return AppConfigResponse.from_orm(config)


@router.put("", response_model=AppConfigResponse)
def update_settings(update: AppConfigUpdate, db: Session = Depends(get_db)):
    """更新应用配置"""
    config = db.query(AppConfig).filter(AppConfig.id == "singleton").first()
    
    if not config:
        # 如果不存在，创建新配置
        config = AppConfig(id="singleton")
        db.add(config)
    
    # 更新配置
    if update.manual_manga_site_url is not None:
        # 验证URL格式
        url = update.manual_manga_site_url.strip()
        if url and not (url.startswith("http://") or url.startswith("https://")):
            raise HTTPException(status_code=400, detail="URL必须以http://或https://开头")
        
        config.manual_manga_site_url = url if url else None
        logger.info(f"更新手动设置的漫画网站链接: {config.manual_manga_site_url}")
    
    db.commit()
    db.refresh(config)
    
    return AppConfigResponse.from_orm(config)

