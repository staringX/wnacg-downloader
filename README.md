# 漫画下载管理器

一个完整的漫画下载和管理系统，包含前端和后端。支持自动同步收藏夹、下载漫画、实时任务状态更新等功能。

## ✨ 功能特性

### 核心功能
- 📚 **自动同步收藏夹**：按作者分类，支持分页爬取
- ⬇️ **智能下载队列**：支持单个和批量下载，自动排队执行
- 🔄 **最近更新**：自动检测收藏作者的新作品
- 🖼️ **封面管理**：自动保存和显示封面图片
- 📦 **CBZ打包**：自动将下载的图片打包为CBZ格式

### 高级功能
- 🔒 **单例模式**：同步任务使用单例模式，防止重复执行
- 📋 **下载队列**：下载任务自动排队，不会拒绝用户请求
- 📡 **实时状态更新**：使用SSE（Server-Sent Events）实时推送任务状态
- 💾 **断点续传**：下载中断后可以自动恢复
- 🔍 **文件验证**：自动验证本地文件完整性
- 📊 **任务管理**：完整的任务状态跟踪和查询系统
- 📝 **日志系统**：使用loguru进行结构化日志记录

## 🏗️ 项目结构

```
manga/
├── frontend/              # Next.js前端应用
│   ├── app/              # Next.js App Router
│   ├── components/       # React组件
│   ├── hooks/            # 自定义Hooks（任务状态、SSE等）
│   └── lib/              # 工具函数和API客户端
├── backend/              # Python FastAPI后端
│   ├── app/
│   │   ├── crawler/      # 爬虫模块
│   │   │   ├── base.py           # 爬虫基类
│   │   │   ├── browser.py        # 浏览器管理和登录
│   │   │   ├── collection.py     # 收藏夹爬取
│   │   │   ├── manga_details.py  # 漫画详情和图片获取
│   │   │   └── search.py         # 作者搜索
│   │   ├── routers/      # API路由
│   │   │   ├── manga.py          # 漫画CRUD
│   │   │   ├── sync.py           # 同步收藏夹
│   │   │   ├── download.py       # 下载管理
│   │   │   ├── recent_updates.py # 最近更新
│   │   │   └── tasks.py          # 任务状态和SSE
│   │   ├── services/     # 业务服务
│   │   │   ├── task_manager.py      # 任务管理器
│   │   │   ├── singleton_manager.py # 单例管理器
│   │   │   └── download_queue.py    # 下载队列管理器
│   │   ├── utils/        # 工具模块
│   │   │   ├── downloader.py    # 下载器
│   │   │   └── logger.py        # 日志配置
│   │   ├── models.py     # 数据库模型
│   │   ├── schemas.py    # Pydantic模式
│   │   └── main.py       # FastAPI应用入口
│   └── Dockerfile
├── docs/                 # 文档
│   ├── 单例模式和下载队列方案分析.md
│   ├── 队列持久化方案分析.md
│   └── 单例模式和下载队列实现总结.md
└── docker-compose.yml    # Docker编排文件
```

## 🚀 快速开始

### 使用Docker（推荐）

1. **克隆项目**
```bash
git clone <repository-url>
cd manga
```

2. **配置环境变量**（可选）
创建 `.env` 文件或使用默认值：
```env
MANGA_USERNAME=your_username
MANGA_PASSWORD=your_password
PUBLISH_PAGE_URL=https://wn01.link
DATABASE_URL=postgresql://manga_user:manga_pass@db:5432/manga_db
CORS_ORIGINS=["http://localhost:3000"]
# 最近更新搜索时排除的分类/作者名（JSON数组格式或逗号分隔）
EXCLUDED_CATEGORIES=["优秀","全部","管理分類","書架","书架","我的書架","一般","真人","同人"]
```

**环境变量说明：**
- `EXCLUDED_CATEGORIES`: 在搜索最近更新时排除的分类或作者名。支持两种格式：
  - JSON数组格式：`["优秀","全部","一般","真人","同人"]`
  - 逗号分隔格式：`优秀,全部,一般,真人,同人`

3. **启动服务**
```bash
docker-compose up -d
```

4. **访问应用**
- 前端：http://localhost:3000
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

### 手动安装

#### 后端

1. **安装依赖**
```bash
cd backend
pip install -r requirements.txt
```

2. **配置环境变量**
```bash
# 确保PostgreSQL正在运行
export DATABASE_URL=postgresql://manga_user:manga_pass@localhost:5432/manga_db
export MANGA_USERNAME=your_username
export MANGA_PASSWORD=your_password
```

3. **启动服务**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端

1. **安装依赖**
```bash
cd frontend
pnpm install
```

2. **启动开发服务器**
```bash
pnpm dev
```

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | PostgreSQL数据库连接字符串 | `postgresql://manga_user:manga_pass@db:5432/manga_db` |
| `MANGA_USERNAME` | 漫画网站用户名 | `lilifan456` |
| `MANGA_PASSWORD` | 漫画网站密码 | `a2658208` |
| `PUBLISH_PAGE_URL` | 发布页地址 | `https://wn01.link` |
| `DOWNLOAD_DIR` | 下载目录 | `/app/downloads` |
| `COVER_DIR` | 封面目录 | `/app/covers` |
| `CORS_ORIGINS` | CORS允许的来源（JSON数组） | `["http://localhost:3000"]` |

### 数据库

系统使用 **PostgreSQL 15** 作为数据库，支持：
- 自动创建表结构
- 数据持久化存储
- 事务支持
- 索引优化

**Docker部署**：数据存储在 `postgres_data` volume 中，重启不丢失。

## 📡 API接口

### 漫画管理
- `GET /api/mangas` - 获取所有漫画
- `DELETE /api/manga/{manga_id}` - 删除漫画
- `POST /api/add-to-collection` - 添加漫画到收藏夹

### 同步功能
- `POST /api/sync` - 同步收藏夹（单例模式，如果正在执行则拒绝）
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

详细API文档：http://localhost:8000/docs

## 🎯 核心特性说明

### 单例模式

**同步收藏**和**同步最近更新**使用单例模式：
- 如果任务正在执行，新的请求会被拒绝（返回409错误）
- 防止资源冲突和数据不一致
- 两个任务可以并行执行（使用不同的资源）

### 下载队列

**下载功能**使用队列模式：
- 下载请求不会拒绝，而是加入队列等待执行
- 单例执行器按顺序处理队列中的任务
- 前端可以显示队列状态（哪些漫画在等待下载）

### 实时状态更新

使用 **SSE（Server-Sent Events）** 实现实时状态更新：
- 前端通过 `/api/events` 连接SSE流
- 任务状态变化时自动推送到前端
- 支持页面刷新后恢复任务状态

### 断点续传

下载支持断点续传：
- 下载中断后，重新下载会跳过已下载的页面
- 每页下载完成后立即保存
- 支持批量下载，每本独立处理

## 🛠️ 技术栈

### 前端
- **框架**: Next.js 16 (App Router)
- **UI库**: React 19, TypeScript
- **样式**: Tailwind CSS
- **组件**: Radix UI
- **状态管理**: React Hooks (useState, useEffect, useMemo)
- **实时通信**: Server-Sent Events (SSE)

### 后端
- **框架**: FastAPI (Python 3.11)
- **ORM**: SQLAlchemy 2.0
- **数据库**: PostgreSQL 15
- **爬虫**: Selenium WebDriver
- **日志**: loguru
- **任务管理**: 自定义任务管理系统 + SSE

### 基础设施
- **容器化**: Docker, Docker Compose
- **数据库**: PostgreSQL 15 (Alpine)
- **浏览器**: Chromium (Docker内)

## 📁 数据存储

### 目录结构
```
backend/
├── downloads/        # 下载的漫画（按作者分类）
│   └── 作者名/
│       └── 漫画标题.cbz
├── covers/          # 封面图片
├── logs/            # 日志文件
│   ├── manga_YYYY-MM-DD.log      # 详细日志
│   ├── error_YYYY-MM-DD.log      # 错误日志
│   └── crawler_YYYY-MM-DD.log    # 爬虫日志
└── data/            # 其他数据文件
```

### 数据库表
- `mangas`: 漫画信息表
- `recent_updates`: 最近更新表
- `tasks`: 任务状态表

## 🔍 日志系统

使用 `loguru` 进行结构化日志记录：
- **控制台输出**：彩色格式，DEBUG级别
- **详细日志文件**：包含所有级别，按天轮转
- **错误日志文件**：仅ERROR和CRITICAL，保留90天
- **爬虫日志文件**：INFO级别，保留15天

日志位置：`backend/logs/`

## 🚨 注意事项

1. **首次使用**：需要点击"同步收藏夹"按钮来获取收藏列表
2. **下载目录**：下载的漫画保存在 `backend/downloads` 目录（按作者分类）
3. **封面图片**：封面保存在 `backend/covers` 目录
4. **合理使用**：请遵守网站使用条款，合理使用爬虫功能
5. **任务状态**：长时间运行的任务可以通过任务管理API查询状态
6. **队列管理**：下载队列中的任务会按顺序执行，不会丢失

## 📚 文档

- [单例模式和下载队列方案分析](docs/单例模式和下载队列方案分析.md)
- [队列持久化方案分析](docs/队列持久化方案分析.md)
- [单例模式和下载队列实现总结](docs/单例模式和下载队列实现总结.md)
- [Docker部署文档](README.Docker.md)（如果存在）
- [群晖NAS部署指南](DEPLOY_SYNOLOGY.md)

## 🔧 开发

### 代码结构

- **爬虫模块**：模块化设计，每个功能独立文件
- **路由模块**：按功能分类，清晰的API组织
- **服务模块**：业务逻辑封装，可复用
- **工具模块**：通用工具函数

### 测试

```bash
# 测试单例模式
curl -X POST http://localhost:8000/api/sync
curl -X POST http://localhost:8000/api/sync  # 应该返回409

# 测试下载队列
curl -X POST http://localhost:8000/api/download/{manga_id}
curl http://localhost:8000/api/download/queue  # 查看队列

# 测试任务状态
curl http://localhost:8000/api/tasks/running/list?task_type=download
```

## 📝 更新日志

### v2.0.0
- ✅ 实现单例模式和下载队列
- ✅ 添加SSE实时状态更新
- ✅ 迁移到PostgreSQL数据库
- ✅ 优化日志系统
- ✅ 改进错误处理

### v1.0.0
- ✅ 基础功能实现
- ✅ Docker部署支持

## 📄 许可证

MIT
