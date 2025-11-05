# 漫画下载管理器

一个完整的漫画下载和管理系统，包含前端和后端。

## 功能特性

- 📚 自动同步收藏夹（按作者分类）
- ⬇️ 下载漫画并打包为CBZ格式
- 🖼️ 自动保存封面图片
- 📊 使用PostgreSQL存储漫画信息
- 🔄 最近更新功能（显示收藏作者的更新）
- ⭐ 收藏新漫画功能
- 🐳 Docker一键部署

## 项目结构

```
manga/
├── frontend/          # Next.js前端
├── backend/           # Python FastAPI后端
└── docker-compose.yml # Docker编排文件
```

## 快速开始

### 使用Docker（推荐）

1. 克隆项目
2. 配置环境变量（可选，使用默认值）
3. 启动服务：
```bash
docker-compose up -d
```

访问：
- 前端：http://localhost:3000
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

### 手动安装

#### 后端

1. 进入backend目录
2. 安装依赖：
```bash
pip install -r requirements.txt
```
3. 配置环境变量（复制`.env.example`为`.env`）
4. 确保PostgreSQL正在运行
5. 启动服务：
```bash
uvicorn app.main:app --reload
```

#### 前端

1. 进入frontend目录
2. 安装依赖：
```bash
npm install
# 或
pnpm install
```
3. 启动开发服务器：
```bash
npm run dev
```

## 配置说明

### 环境变量

- `MANGA_USERNAME`: 漫画网站用户名
- `MANGA_PASSWORD`: 漫画网站密码
- `PUBLISH_PAGE_URL`: 发布页地址（默认：https://wn01.link）
- `DATABASE_URL`: PostgreSQL连接字符串

### 数据库

系统会自动创建所需的表。首次运行前请确保PostgreSQL已启动。

## API接口

- `GET /api/mangas` - 获取所有漫画
- `POST /api/sync` - 同步收藏夹
- `POST /api/download/{manga_id}` - 下载单个漫画
- `POST /api/download/batch` - 批量下载
- `GET /api/recent-updates` - 获取最近更新
- `POST /api/add-to-collection` - 添加漫画到收藏夹
- `DELETE /api/manga/{manga_id}` - 删除漫画

详细API文档：http://localhost:8000/docs

## 注意事项

1. 首次使用时需要点击"同步收藏夹"按钮来获取收藏列表
2. 下载的漫画保存在`backend/downloads`目录
3. 封面图片保存在`backend/covers`目录
4. 请遵守网站使用条款，合理使用爬虫功能
5. 建议设置适当的请求间隔，避免过度爬取

## 技术栈

- **前端**: Next.js 16, React 19, TypeScript, Tailwind CSS
- **后端**: Python 3.11, FastAPI, SQLAlchemy, Selenium
- **数据库**: PostgreSQL 15
- **容器化**: Docker, Docker Compose

## 许可证

MIT
