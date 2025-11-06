# 日志系统说明

## 概述

本项目使用 [loguru](https://github.com/Delgan/loguru) 作为日志库，提供统一、简洁、强大的日志记录功能。

## 日志配置

所有日志配置在 `app/utils/logger.py` 中，包含以下日志输出：

### 1. 控制台输出
- **格式**: 彩色简洁格式
- **级别**: INFO 及以上
- **示例**: `14:23:45 | INFO     | app.main:main - 服务启动`

### 2. 详细日志文件
- **文件名**: `logs/manga_YYYY-MM-DD.log`
- **级别**: DEBUG 及以上（包含所有日志）
- **轮转**: 每天午夜自动轮转
- **保留**: 30天
- **压缩**: 自动压缩旧日志为 `.zip`

### 3. 错误日志文件
- **文件名**: `logs/error_YYYY-MM-DD.log`
- **级别**: ERROR 和 CRITICAL
- **轮转**: 每天午夜自动轮转
- **保留**: 90天（错误日志保留更久）
- **压缩**: 自动压缩旧日志为 `.zip`

### 4. 爬虫专用日志
- **文件名**: `logs/crawler_YYYY-MM-DD.log`
- **级别**: INFO 及以上
- **过滤**: 仅记录 `crawler` 相关模块的日志
- **轮转**: 每天午夜自动轮转
- **保留**: 15天

## 使用方法

### 基本用法

```python
from app.utils.logger import logger

# 调试信息（开发阶段使用）
logger.debug("这是调试信息")

# 常规信息（记录正常流程）
logger.info("用户登录成功")

# 警告信息（需要注意但不影响运行）
logger.warning("配置文件缺少可选参数")

# 错误信息（影响功能但不致命）
logger.error("数据库连接失败")

# 严重错误（系统级错误）
logger.critical("服务崩溃")
```

### 带变量的日志

```python
# 推荐：使用 f-string
logger.info(f"处理漫画: {manga_title}, 页数: {page_count}")

# 或使用 .format()
logger.info("处理漫画: {}, 页数: {}", manga_title, page_count)
```

### 带异常信息的日志

```python
try:
    # 某些操作
    risky_operation()
except Exception as e:
    # 自动记录异常堆栈
    logger.exception("操作失败")
    # 或
    logger.error(f"操作失败: {e}", exc_info=True)
```

### 结构化日志

```python
# 绑定上下文信息
context_logger = logger.bind(user_id=123, request_id="abc")
context_logger.info("用户操作")
# 输出: ... | user_id=123 request_id=abc | 用户操作
```

## 日志级别使用规范

### DEBUG
- **用途**: 详细的调试信息
- **场景**: 
  - 函数参数和返回值
  - 中间计算结果
  - 详细的步骤信息
- **示例**: `logger.debug(f"解析参数: {params}")`

### INFO
- **用途**: 关键流程和正常状态
- **场景**:
  - 服务启动/停止
  - 同步/下载开始/完成
  - 重要操作成功
- **示例**: `logger.info("同步完成：新增 10 个漫画")`

### WARNING
- **用途**: 值得注意但不影响运行
- **场景**:
  - 文件丢失（可重新下载）
  - 无法获取可选信息
  - 配置缺失使用默认值
- **示例**: `logger.warning("封面下载失败，使用默认封面")`

### ERROR
- **用途**: 影响功能但不致命
- **场景**:
  - 爬取单个漫画失败（其他继续）
  - 数据库操作失败（可重试）
  - 文件写入失败
- **示例**: `logger.error(f"处理漫画失败: {title} - {error}")`

### CRITICAL
- **用途**: 系统级严重错误
- **场景**:
  - 数据库连接失败
  - 关键配置缺失
  - 服务无法启动
- **示例**: `logger.critical("数据库初始化失败，服务无法启动")`

## 日志文件位置

### 开发环境
- 路径: `backend/logs/`
- 示例:
  ```
  backend/logs/
  ├── manga_2025-11-06.log
  ├── manga_2025-11-05.log.zip
  ├── error_2025-11-06.log
  ├── crawler_2025-11-06.log
  └── ...
  ```

### Docker 环境
- 路径: `/app/logs/`（容器内）
- 建议挂载到宿主机: 在 `docker-compose.yml` 中添加
  ```yaml
  volumes:
    - ./logs:/app/logs
  ```

## 查看日志

### 实时查看控制台日志
```bash
# 开发环境
cd backend
python -m uvicorn app.main:app --reload

# Docker环境
docker-compose logs -f backend
```

### 查看文件日志
```bash
# 查看今天的完整日志
tail -f backend/logs/manga_$(date +%Y-%m-%d).log

# 查看今天的错误日志
tail -f backend/logs/error_$(date +%Y-%m--%d).log

# 查看爬虫日志
tail -f backend/logs/crawler_$(date +%Y-%m-%d).log

# 搜索特定内容
grep "同步完成" backend/logs/manga_*.log
```

## 日志维护

### 自动维护
- ✅ 每天午夜自动轮转（创建新文件）
- ✅ 自动压缩旧日志（节省空间）
- ✅ 自动删除过期日志
  - 详细日志: 保留30天
  - 错误日志: 保留90天
  - 爬虫日志: 保留15天

### 手动清理
```bash
# 删除所有日志文件
rm -rf backend/logs/*

# 删除压缩的旧日志
rm backend/logs/*.zip

# 删除特定日期的日志
rm backend/logs/*2025-10-*.log*
```

## 性能考虑

- loguru 默认是**异步写入**，不会阻塞主线程
- 日志文件使用 **缓冲写入**，性能优异
- 自动**压缩**旧日志，节省磁盘空间
- 建议生产环境将详细日志级别调整为 `INFO`

## 故障排查

### 问题：日志文件没有创建
```bash
# 检查目录权限
ls -la backend/logs

# 手动创建目录
mkdir -p backend/logs
chmod 755 backend/logs
```

### 问题：日志文件太大
```bash
# 检查当前日志文件大小
du -sh backend/logs/*

# 解决方案：调整轮转策略
# 在 app/utils/logger.py 中修改
rotation="100 MB"  # 按大小轮转
# 或
rotation="1 day"   # 每天轮转
```

### 问题：控制台无彩色输出
```bash
# 检查终端是否支持彩色
echo $TERM

# 强制启用彩色
export TERM=xterm-256color
```

## 示例

### 完整示例：同步日志
```python
from app.utils.logger import logger

def sync_collection():
    logger.info("=" * 60)
    logger.info("开始同步收藏夹")
    logger.info("=" * 60)
    
    try:
        manga_list = fetch_collection()
        logger.info(f"获取到 {len(manga_list)} 个漫画")
        
        for idx, manga in enumerate(manga_list, 1):
            try:
                save_to_db(manga)
                logger.info(f"[{idx}/{len(manga_list)}] ✓ {manga.title}")
            except Exception as e:
                logger.error(f"[{idx}/{len(manga_list)}] ✗ {manga.title} - {e}")
                continue
        
        logger.info(f"同步完成！成功 {success_count} 个")
        
    except Exception as e:
        logger.exception("同步失败")
        raise
```

## 更多资源

- loguru 官方文档: https://loguru.readthedocs.io/
- loguru GitHub: https://github.com/Delgan/loguru

