"""
数据库自动迁移工具
在应用启动时自动检测并应用数据库迁移，类似于 JPA 的自动迁移功能
"""
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect
from app.config import settings
from app.database import engine, Base
from app.utils.logger import logger
from app import models  # 必须导入所有模型
import os


def run_migrations():
    """
    自动运行数据库迁移
    检测模型变更并自动应用到数据库
    
    工作流程：
    1. 检查是否有待应用的迁移脚本，如果有则应用
    2. 检查数据库结构与模型是否一致，如果不一致则：
       - 如果存在迁移脚本但未应用，则应用迁移
       - 如果不存在迁移脚本，则自动生成并应用（开发模式）
    """
    try:
        # 获取项目根目录（backend 目录）
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
        
        # 设置数据库 URL
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
        
        logger.info("开始检查数据库迁移...")
        
        # 检查迁移脚本目录，如果不存在则创建
        versions_dir = os.path.join(backend_dir, "migrations", "versions")
        if not os.path.exists(versions_dir):
            os.makedirs(versions_dir, exist_ok=True)
            logger.info(f"创建迁移脚本目录: {versions_dir}")
        
        has_migrations = os.path.exists(versions_dir) and len([f for f in os.listdir(versions_dir) if f.endswith('.py') and f != '__init__.py']) > 0
        
        if not has_migrations:
            # 首次使用，检查数据库是否已有表
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            
            if not existing_tables:
                # 数据库为空，创建初始迁移并应用
                logger.info("检测到首次使用（空数据库），创建初始迁移...")
                command.revision(alembic_cfg, autogenerate=True, message="初始迁移")
                logger.info("初始迁移脚本已创建")
            else:
                # 数据库已有表，创建基准迁移（不生成变更，因为表已存在）
                logger.info("检测到已有数据库表，创建基准迁移...")
                # 先创建一个空的迁移作为基准
                command.revision(alembic_cfg, message="基准迁移（表已存在）")
                # 标记为已应用（stamp）
                script = ScriptDirectory.from_config(alembic_cfg)
                head_revision = script.get_current_head()
                if head_revision:
                    command.stamp(alembic_cfg, head_revision)
                    logger.info(f"已标记基准迁移为当前状态: {head_revision}")
        
        # 应用所有待应用的迁移
        try:
            # 先应用已有的迁移
            command.upgrade(alembic_cfg, "head")
            logger.info("已应用所有待应用的迁移")
            
            # 检查是否有未跟踪的模型变更并自动生成迁移
            # 这类似于 JPA 的自动迁移功能
            try:
                # 获取迁移脚本目录中的文件数量（用于判断是否生成了新迁移）
                script = ScriptDirectory.from_config(alembic_cfg)
                initial_files = set()
                if os.path.exists(versions_dir):
                    initial_files = set([f for f in os.listdir(versions_dir) if f.endswith('.py') and f != '__init__.py'])
                
                # 尝试自动生成迁移（如果检测到模型变更）
                command.revision(alembic_cfg, autogenerate=True, message="自动检测的模型变更")
                
                # 检查是否生成了新的迁移文件
                if os.path.exists(versions_dir):
                    new_files = set([f for f in os.listdir(versions_dir) if f.endswith('.py') and f != '__init__.py'])
                    if new_files - initial_files:
                        logger.info("检测到模型变更，已生成新的迁移脚本，正在应用...")
                        command.upgrade(alembic_cfg, "head")
                        logger.info("模型变更已自动应用到数据库")
            except Exception as auto_error:
                # autogenerate 可能因为各种原因失败（如数据库未同步、无变更等）
                # 这些情况是正常的，不需要记录为错误
                error_msg = str(auto_error).lower()
                if "target database is not up to date" in error_msg:
                    # 数据库未同步，先尝试应用迁移
                    logger.info("检测到数据库未同步，尝试应用迁移...")
                    command.upgrade(alembic_cfg, "head")
                elif "can't locate revision" in error_msg or "no such revision" in error_msg:
                    # 迁移脚本问题，记录警告
                    logger.warning("迁移脚本版本问题，可能需要手动处理")
                else:
                    # 其他错误，可能是没有变更（这是正常的）
                    logger.debug(f"检查模型变更: {auto_error}")
            
            logger.info("数据库迁移检查完成")
            
        except Exception as upgrade_error:
            # 如果升级失败，记录错误但不阻止启动
            logger.warning(f"应用迁移时出现错误: {upgrade_error}")
            logger.warning("将继续启动应用，但数据库可能未完全同步")
            import traceback
            logger.debug(traceback.format_exc())
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # 不抛出异常，允许应用继续启动（如果数据库已经是最新的）
        # 如果确实需要迁移，会在后续操作中暴露问题


def create_initial_migration():
    """
    创建初始迁移脚本（仅在需要时手动调用）
    用于首次设置迁移系统
    """
    try:
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
        
        logger.info("创建初始迁移脚本...")
        command.revision(alembic_cfg, autogenerate=True, message="初始迁移")
        logger.info("初始迁移脚本创建完成")
        
    except Exception as e:
        logger.error(f"创建迁移脚本失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

