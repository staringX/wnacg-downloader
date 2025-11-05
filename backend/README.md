# 漫画下载管理器后端

这是一个用于爬取和管理漫画的Python后端服务。

## 功能特性

- 自动从发布页获取漫画网站地址
- 登录并同步收藏夹（按作者分类）
- 下载漫画并打包为CBZ格式
- 保存封面图片
- 使用PostgreSQL存储漫画信息
- 提供最近更新功能
- 支持收藏新漫画

## 环境要求

- Python 3.11+
- PostgreSQL 15+
- Chrome浏览器（用于Selenium）
- ChromeDriver

## 安装

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置环境变量（复制`.env.example`为`.env`并修改）：
```bash
cp .env.example .env
```

3. 初始化数据库：
```bash
# 确保PostgreSQL正在运行
# 数据库会自动创建表
```

## 运行

### 开发模式
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 使用Docker
```bash
docker-compose up -d
```

## API接口

- `GET /api/mangas` - 获取所有漫画
- `POST /api/sync` - 同步收藏夹
- `POST /api/download/{manga_id}` - 下载单个漫画
- `POST /api/download/batch` - 批量下载漫画
- `GET /api/recent-updates` - 获取最近更新
- `POST /api/add-to-collection` - 添加漫画到收藏夹
- `DELETE /api/manga/{manga_id}` - 删除漫画

## 注意事项

1. 首次运行需要确保Chrome和ChromeDriver已正确安装
2. 下载的漫画文件保存在`downloads`目录
3. 封面图片保存在`covers`目录
4. 请遵守网站的使用条款，不要过度爬取
