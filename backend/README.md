# 漫画下载管理器后端

Python FastAPI后端服务，提供漫画爬取、下载、管理等功能。

## 功能特性

### 核心功能
- 🔐 **自动登录**：从发布页获取网站地址并自动登录
- 📚 **收藏夹同步**：按作者分类，支持分页爬取
- ⬇️ **智能下载**：支持单个和批量下载，自动排队执行
- 🔄 **最近更新**：自动检测收藏作者的新作品
- 🖼️ **封面管理**：自动保存封面图片

### 高级功能
- 🔒 **单例模式**：同步任务使用单例模式，防止重复执行
- 📋 **下载队列**：下载任务自动排队，不会拒绝用户请求
- 📡 **实时状态更新**：使用SSE（Server-Sent Events）实时推送任务状态
- 💾 **断点续传**：下载中断后可以自动恢复
- 🔍 **文件验证**：自动验证本地文件完整性
- 📊 **任务管理**：完整的任务状态跟踪和查询系统
- 📝 **日志系统**：使用loguru进行结构化日志记录

## 环境要求

- Python 3.11+
- PostgreSQL 15+
- Chromium浏览器（用于Selenium）
- Chromium Driver

## 安装

### 使用Docker（推荐）

```bash
# 在项目根目录
docker-compose up -d
```

### 手动安装

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **配置环境变量**
```bash
export DATABASE_URL=postgresql://manga_user:manga_pass@localhost:5432/manga_db
export MANGA_USERNAME=your_username
export MANGA_PASSWORD=your_password
export PUBLISH_PAGE_URL=https://wn01.link
```

3. **初始化数据库**
数据库表会在首次启动时自动创建。

## 运行

### 开发模式
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 生产模式
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 项目结构

```
backend/
├── app/
│   ├── crawler/          # 爬虫模块
│   │   ├── base.py           # 爬虫基类
│   │   ├── browser.py        # 浏览器管理和登录
│   │   ├── collection.py     # 收藏夹爬取
│   │   ├── manga_details.py  # 漫画详情和图片获取
│   │   └── search.py         # 作者搜索
│   ├── routers/          # API路由
│   │   ├── manga.py          # 漫画CRUD
│   │   ├── sync.py           # 同步收藏夹
│   │   ├── download.py       # 下载管理
│   │   ├── recent_updates.py # 最近更新
│   │   └── tasks.py          # 任务状态和SSE
│   ├── services/         # 业务服务
│   │   ├── task_manager.py           # 任务管理器
│   │   ├── sync_singleton.py         # 同步收藏夹单例管理器
│   │   ├── recent_updates_singleton.py # 最近更新单例管理器
│   │   ├── download_queue.py         # 下载队列管理器
│   │   ├── sync_service.py           # 同步收藏夹业务逻辑
│   │   ├── recent_updates_service.py # 最近更新业务逻辑
│   │   └── download_service.py       # 下载业务逻辑
│   ├── utils/            # 工具模块
│   │   ├── comic_info.py    # ComicInfo.xml 生成工具
│   │   └── logger.py        # 日志配置
│   ├── models.py          # 数据库模型
│   ├── schemas.py         # Pydantic模式
│   ├── config.py          # 配置管理
│   ├── database.py        # 数据库连接
│   └── main.py            # FastAPI应用入口
├── requirements.txt       # Python依赖
└── Dockerfile            # Docker构建文件
```

## API接口

### 漫画管理
- `GET /api/mangas` - 获取所有漫画
- `DELETE /api/manga/{manga_id}` - 删除漫画
- `POST /api/add-to-collection` - 添加漫画到收藏夹

### 同步功能
- `POST /api/sync` - 同步收藏夹（单例模式）
- `POST /api/sync-recent-updates` - 同步最近更新（单例模式）
- `POST /api/verify-files` - 验证本地文件完整性

### 下载功能
- `POST /api/download/{manga_id}` - 下载单个漫画（加入队列）
- `POST /api/download/batch` - 批量下载（加入队列）
- `GET /api/download/queue` - 获取下载队列中的漫画ID列表

### 最近更新
- `GET /api/recent-updates` - 获取最近更新列表

### 任务管理
- `GET /api/tasks/{task_id}` - 获取任务状态
- `GET /api/tasks/running/list` - 获取正在运行的任务列表
- `GET /api/events` - SSE事件流（实时任务状态更新）
- `POST /api/tasks/cleanup` - 手动清理过期任务

详细API文档（FastAPI自动生成）：http://localhost:18000/docs

## 核心模块说明

### 爬虫模块 (crawler/)

- **base.py**: 爬虫基类，整合各个爬虫模块
- **browser.py**: 浏览器管理、登录、获取网站地址
- **collection.py**: 收藏夹爬取，支持分页
- **manga_details.py**: 漫画详情和图片获取，支持分页
- **search.py**: 作者搜索，获取最近更新

### 服务模块 (services/)

- **task_manager.py**: 任务管理器，管理任务状态和SSE推送
- **sync_singleton.py**: 同步收藏夹单例管理器，防止重复执行
- **recent_updates_singleton.py**: 最近更新单例管理器，防止重复执行
- **download_queue.py**: 下载队列管理器，管理下载任务的队列执行
- **sync_service.py**: 同步收藏夹业务逻辑
- **recent_updates_service.py**: 最近更新业务逻辑
- **download_service.py**: 下载业务逻辑，包含 ComicInfo.xml 生成

### 工具模块 (utils/)

- **comic_info.py**: ComicInfo.xml 生成工具，自动生成漫画元数据文件
- **logger.py**: 日志配置，使用loguru进行结构化日志记录

## 配置说明

### 环境变量

| 变量名 | 说明 | 是否必填 | 示例 |
|--------|------|---------|------|
| `DATABASE_URL` | PostgreSQL数据库连接字符串 | 是 | `postgresql://manga_user:manga_pass@db:5432/manga_db` |
| `MANGA_USERNAME` | 漫画网站用户名 | 是 | `your_username` |
| `MANGA_PASSWORD` | 漫画网站密码 | 是 | `your_password` |
| `PUBLISH_PAGE_URL` | 发布页地址 | 否 | `https://wn01.link` |
| `DOWNLOAD_DIR` | 下载目录 | 否 | `/app/downloads` |
| `COVER_DIR` | 封面目录 | 否 | `/app/covers` |
| `EXCLUDED_CATEGORIES` | 最近更新搜索时排除的分类（逗号分隔或JSON数组） | 否 | `优秀,一般,真人,同人` |

### 数据库

使用 **PostgreSQL 15** 作为数据库：
- 自动创建表结构
- 支持事务
- 索引优化

## 日志系统

使用 `loguru` 进行结构化日志记录：

- **控制台输出**：彩色格式，DEBUG级别
- **详细日志文件**：`logs/manga_YYYY-MM-DD.log`，包含所有级别，按天轮转
- **错误日志文件**：`logs/error_YYYY-MM-DD.log`，仅ERROR和CRITICAL，保留90天
- **爬虫日志文件**：`logs/crawler_YYYY-MM-DD.log`，INFO级别，保留15天

## 注意事项

1. **首次运行**：需要确保Chromium和ChromiumDriver已正确安装（Docker中已包含）
2. **下载目录**：下载的漫画文件保存在 `downloads` 目录（按作者分类），CBZ 文件自动包含 ComicInfo.xml 元数据
3. **封面图片**：封面图片保存在 `covers` 目录
4. **ComicInfo.xml**：自动从网页提取漫画信息（分类、标签、上传者、简介等）并生成标准格式的元数据文件
5. **合理使用**：请遵守网站的使用条款，不要过度爬取
6. **任务管理**：长时间运行的任务可以通过任务管理API查询状态
7. **队列管理**：下载队列中的任务会按顺序执行，不会丢失

## 开发

### 代码规范

- 使用类型提示（Type Hints）
- 使用Pydantic进行数据验证
- 使用loguru进行日志记录
- 异常处理使用 `get_error_message` 避免冗长的堆栈跟踪

### 测试

```bash
# 测试单例模式
curl -X POST http://localhost:18000/api/sync
curl -X POST http://localhost:18000/api/sync  # 应该返回409

# 测试下载队列
curl -X POST http://localhost:18000/api/download/{manga_id}
curl http://localhost:18000/api/download/queue  # 查看队列

# 测试任务状态
curl http://localhost:18000/api/tasks/running/list?task_type=download
```

## 依赖

主要依赖：
- `fastapi`: Web框架
- `sqlalchemy`: ORM
- `psycopg2-binary`: PostgreSQL驱动
- `selenium`: 浏览器自动化
- `loguru`: 日志记录
- `pydantic`: 数据验证
- `requests`: HTTP请求
- `beautifulsoup4`: HTML解析

完整依赖列表见 `requirements.txt`
