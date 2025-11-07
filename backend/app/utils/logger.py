"""
日志配置模块 - 使用 loguru
"""
import sys
from pathlib import Path
from loguru import logger


def get_error_message(exception: Exception) -> str:
    """提取异常的错误消息，避免打印完整的堆栈跟踪
    
    Args:
        exception: 异常对象
        
    Returns:
        错误消息的第一行（通常是主要错误信息）
    """
    error_str = str(exception)
    # 如果包含换行符，只取第一行
    if '\n' in error_str:
        return error_str.split('\n')[0]
    return error_str

# 创建日志目录
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 移除默认的控制台处理器
logger.remove()

# 添加控制台输出（彩色，简洁格式）
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="DEBUG"  # 临时改为DEBUG以便调试分页问题
)

# 添加详细日志文件（包含所有级别）
logger.add(
    LOG_DIR / "manga_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # 每天午夜轮转
    retention="30 days",  # 保留30天
    compression="zip",  # 压缩旧日志
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"
)

# 添加错误日志文件（仅ERROR和CRITICAL）
logger.add(
    LOG_DIR / "error_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="90 days",  # 错误日志保留更久
    compression="zip",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
    level="ERROR"
)

# 添加爬虫专用日志文件
logger.add(
    LOG_DIR / "crawler_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="15 days",
    compression="zip",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO",
    filter=lambda record: "crawler" in record["name"].lower()
)

# 导出配置好的logger和辅助函数
__all__ = ["logger", "get_error_message"]

