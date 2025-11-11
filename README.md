# WNACG 漫画下载管理器

一个专为 **WNACG（绅士漫画）** 设计的漫画下载和管理系统。通过登录您的 WNACG 账号，自动爬取收藏夹中的漫画并下载到本地。提供完整的 Docker 部署方案，适合在 NAS（如群晖）中部署。项目集成了 **Komga** 漫画阅读器，方便阅读和管理下载的漫画。

## 🎯 项目目的

本项目旨在帮助用户：
- 📥 **自动下载收藏的漫画**：从 WNACG 账号的收藏夹中爬取漫画并下载到本地
- 📦 **自动打包为 CBZ 格式**：下载的漫画自动打包为 CBZ 文件，包含完整的 ComicInfo.xml 元数据
- 📚 **集成 Komga 阅读器**：下载的漫画自动同步到 Komga，提供便捷的阅读体验
- 🏠 **NAS 友好部署**：提供完整的 Docker Compose 配置，适合在群晖等 NAS 设备上部署
- 🔄 **自动同步更新**：自动检测收藏作者的新作品，及时获取更新

## ✨ 功能特性

### 核心功能

#### 📚 收藏夹同步
**目的**：从 WNACG 账号的收藏夹中爬取所有收藏的漫画信息，保存到本地数据库。支持按作者分类，自动处理分页，确保完整获取所有收藏内容。

#### ⬇️ 漫画下载
**目的**：将收藏的漫画从网站爬取并下载到本地，自动打包为 CBZ 格式文件。
- **单本下载**：点击单本漫画的下载按钮，将该漫画加入下载队列
- **批量下载**：点击"下载全部"按钮，将所有未下载的漫画加入下载队列
- **自动排队**：下载任务自动排队执行，不会拒绝用户请求
- **断点续传**：下载中断后可以自动恢复，跳过已下载的页面

#### 🔄 最近更新同步
**目的**：根据收藏夹中保存的作者名，自动搜索这些作者的所有作品，找出更新日期晚于已保存漫画的更新日期的作品，帮助用户及时发现新内容。

#### 📦 CBZ 打包与元数据
**目的**：将下载的图片自动打包为 CBZ 格式（ZIP 压缩包），并在 CBZ 文件中自动添加 ComicInfo.xml 元数据文件，包含标题、作者、页数、发布日期、分类、标签、简介等信息，兼容 Komga 等主流漫画阅读器。

#### 🖼️ 封面管理
**目的**：自动保存和显示漫画封面图片，方便在列表中快速识别漫画。

#### 📚 Komga 集成
**目的**：项目集成了 Komga 漫画阅读器，下载的漫画自动同步到 Komga 的数据目录，用户可以通过前端"Komga"按钮直接访问阅读器，享受便捷的阅读体验。

### 高级功能

#### 🔒 单例模式
**目的**：同步收藏夹和同步最近更新任务使用单例模式，防止同一任务重复执行，避免资源冲突和数据不一致。

#### 📋 下载队列
**目的**：下载任务使用队列模式，所有下载请求都会加入队列等待执行，不会因为任务繁忙而拒绝用户请求，确保所有下载任务都能完成。

#### 📡 实时状态更新
**目的**：使用 SSE（Server-Sent Events）实时推送任务状态到前端，用户无需刷新页面即可看到任务进度和状态变化。

#### 💾 断点续传
**目的**：下载中断后，重新下载会跳过已下载的页面，节省时间和带宽。

#### 🔍 文件验证
**目的**：自动验证本地文件的完整性，确保下载的漫画文件完整可用。

#### 📊 任务管理
**目的**：提供完整的任务状态跟踪和查询系统，用户可以随时查看任务进度和状态。

#### 📝 日志系统
**目的**：使用 loguru 进行结构化日志记录，方便排查问题和监控系统运行状态。

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
│   │   │   ├── task_manager.py           # 任务管理器
│   │   │   ├── sync_singleton.py         # 同步收藏夹单例管理器
│   │   │   ├── recent_updates_singleton.py # 最近更新单例管理器
│   │   │   ├── download_queue.py         # 下载队列管理器
│   │   │   ├── sync_service.py           # 同步收藏夹业务逻辑
│   │   │   ├── recent_updates_service.py # 最近更新业务逻辑
│   │   │   └── download_service.py       # 下载业务逻辑
│   │   ├── utils/        # 工具模块
│   │   │   ├── comic_info.py    # ComicInfo.xml 生成工具
│   │   │   └── logger.py        # 日志配置
│   │   ├── models.py     # 数据库模型
│   │   ├── schemas.py    # Pydantic模式
│   │   └── main.py       # FastAPI应用入口
│   └── Dockerfile
├── docker-compose.yml    # Docker编排文件（本地开发）
└── docker-compose.synology.yml  # Docker编排文件（群晖NAS）
```

## 🚀 快速开始

### 使用Docker（推荐）

1. **克隆项目**
```bash
git clone <repository-url>
cd manga
```

2. **配置环境变量**（必填）

创建 `.env` 文件并填写您的 WNACG 账号信息：
```bash
# 编辑 .env 文件，填写 MANGA_USERNAME 和 MANGA_PASSWORD
```

`.env` 文件示例：
```env
# WNACG 账号信息（必填）
MANGA_USERNAME=your_wnacg_username
MANGA_PASSWORD=your_wnacg_password

# 发布页地址（可选，默认：https://wn01.link）
PUBLISH_PAGE_URL=https://wn01.link

# 数据库配置（Docker 部署时使用默认值即可）
DATABASE_URL=postgresql://manga_user:manga_pass@db:5432/manga_db

# CORS 配置（可选）
CORS_ORIGINS=["http://localhost:13000"]

# 最近更新搜索时排除的分类/作者名（可选）
# 支持 JSON 数组格式或逗号分隔格式
EXCLUDED_CATEGORIES=["优秀","全部","管理分類","書架","书架","我的書架","一般","真人","同人"]
```

**重要提示：**
- `.env` 文件已添加到 `.gitignore`，不会被提交到Git仓库
- `MANGA_USERNAME` 和 `MANGA_PASSWORD` 是必填项，必须填写您的 WNACG 账号信息
- `EXCLUDED_CATEGORIES`: 在搜索最近更新时排除的分类或作者名。支持两种格式：
  - JSON数组格式：`["优秀","全部","一般","真人","同人"]`
  - 逗号分隔格式：`优秀,全部,一般,真人,同人`

3. **启动服务**
```bash
docker-compose up -d
```

4. **访问应用**
- 前端：http://localhost:13000
- 后端API：http://localhost:18000
- API文档（FastAPI自动生成）：http://localhost:18000/docs
- Komga：http://localhost:25601

### 手动安装

#### 后端

1. **安装依赖**
```bash
cd backend
pip install -r requirements.txt
```

2. **配置环境变量**
```bash
# 方式1：使用 .env 文件（推荐）
cp .env.example .env
# 编辑 .env 文件，填写实际值

# 方式2：直接设置环境变量
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

| 变量名 | 说明 | 是否必填 | 示例 |
|--------|------|---------|------|
| `MANGA_USERNAME` | WNACG 账号用户名 | 是 | `your_wnacg_username` |
| `MANGA_PASSWORD` | WNACG 账号密码 | 是 | `your_wnacg_password` |
| `PUBLISH_PAGE_URL` | WNACG 发布页地址 | 否 | `https://wn01.link` |
| `DATABASE_URL` | PostgreSQL数据库连接字符串 | 是（Docker 部署时自动配置） | `postgresql://manga_user:manga_pass@db:5432/manga_db` |
| `DOWNLOAD_DIR` | 下载目录 | 否 | `/app/downloads` |
| `COVER_DIR` | 封面目录 | 否 | `/app/covers` |
| `CORS_ORIGINS` | CORS允许的来源（JSON数组） | 否 | `["http://localhost:13000"]` |
| `EXCLUDED_CATEGORIES` | 最近更新搜索时排除的分类（JSON数组或逗号分隔） | 否 | `["优秀","全部","一般","真人","同人"]` |

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

详细API文档（FastAPI自动生成）：http://localhost:18000/docs

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
- **漫画阅读器**: Komga（可选，已集成）

## 📁 数据存储

### 目录结构
```
backend/
├── downloads/        # 下载的漫画（按作者分类）
│   └── 作者名/
│       └── 漫画标题.cbz  # 包含 ComicInfo.xml 元数据文件
├── covers/          # 封面图片
├── logs/            # 日志文件
│   ├── manga_YYYY-MM-DD.log      # 详细日志
│   ├── error_YYYY-MM-DD.log      # 错误日志
│   └── crawler_YYYY-MM-DD.log    # 爬虫日志
└── data/            # 其他数据文件
```

### ComicInfo.xml 元数据

下载的 CBZ 文件会自动包含 `ComicInfo.xml` 元数据文件，支持以下信息：

- **基本信息**：标题、作者、页数、发布日期
- **分类信息**：流派（从网站分类自动转换）
- **标签**：所有标签（逗号分隔）
- **简介**：漫画简介（如果有）
- **链接**：漫画原始 URL
- **语言**：默认 zh-CN
- **阅读方向**：从右到左（Manga: YesAndRightToLeft）
- **译者/编辑**：根据标签自动识别

这些元数据兼容 **Komga** 等主流漫画阅读器，可以更好地组织和展示漫画信息。

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

## 🚨 使用说明

### 首次使用流程

1. **配置账号**：在 `.env` 文件中填写您的 WNACG 账号信息（`MANGA_USERNAME` 和 `MANGA_PASSWORD`）
2. **启动服务**：运行 `docker-compose up -d` 启动所有服务
3. **同步收藏夹**：在前端界面点击"同步"按钮，系统会自动登录您的 WNACG 账号并爬取收藏夹中的所有漫画信息
4. **下载漫画**：
   - **单本下载**：点击漫画卡片上的下载按钮，将该漫画加入下载队列
   - **批量下载**：点击"下载全部"按钮，将所有未下载的漫画加入下载队列
5. **阅读漫画**：下载完成后，点击"Komga"按钮打开 Komga 阅读器，即可阅读下载的漫画

### 重要提示

- **下载目录**：下载的漫画保存在 `backend/downloads` 目录（按作者分类），CBZ 文件包含 ComicInfo.xml 元数据
- **封面图片**：封面保存在 `backend/covers` 目录
- **Komga 集成**：下载的漫画会自动同步到 Komga 的数据目录，可通过前端"Komga"按钮访问
- **合理使用**：请遵守 WNACG 网站使用条款，合理使用爬虫功能，避免对服务器造成过大压力
- **任务状态**：长时间运行的任务可以通过任务管理API查询状态
- **队列管理**：下载队列中的任务会按顺序执行，不会丢失


## 🔧 开发

### 代码结构

- **爬虫模块**：模块化设计，每个功能独立文件
- **路由模块**：按功能分类，清晰的API组织
- **服务模块**：业务逻辑封装，可复用
- **工具模块**：通用工具函数

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

## 📝 更新日志

### v2.1.0
- ✅ 添加 ComicInfo.xml 自动生成功能
- ✅ 增强漫画详情提取（分类、标签、上传者、简介）
- ✅ 自动填充 ComicInfo.xml 元数据
- ✅ 集成 Komga 漫画阅读器
- ✅ 优化移动端 UI（响应式设计、浮动菜单）
- ✅ 简化按钮文字，优化用户体验
- ✅ 统一端口配置，使用非默认端口

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
