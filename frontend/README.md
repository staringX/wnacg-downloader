# 漫画下载管理器

一个用于管理和下载漫画收藏的Web应用。

## 功能特性

- 📚 按作者和作品分组显示漫画收藏
- ⬇️ 单个或批量下载漫画
- ✅ 自动标记已下载和未下载状态
- 🔄 同步收藏夹功能
- ⭐ 显示收藏作者的最近更新
- 📊 统计总计、已下载和待下载数量

## 技术栈

- **框架**: Next.js 16 (App Router)
- **UI**: React + TailwindCSS + shadcn/ui
- **数据库**: Supabase (PostgreSQL)
- **语言**: TypeScript

## 开始使用

### 1. 安装依赖

\`\`\`bash
npm install
\`\`\`

### 2. 配置数据库

数据库表会在后端启动时自动创建（使用SQLAlchemy ORM）。

### 3. 实现爬虫逻辑

你需要根据你的漫画网站实现以下文件中的函数：

#### `lib/scraper.ts`

- `loginToSite()` - 登录到漫画网站
- `scrapeCollection()` - 爬取收藏夹
- `downloadMangaFile()` - 下载单个漫画
- `scrapeRecentUpdates()` - 获取最近更新

#### `lib/download-manager.ts`

- 配置文件存储方式（本地/云存储）

### 4. 运行应用

\`\`\`bash
npm run dev
\`\`\`

访问 `http://localhost:3000`

## 数据库结构

### manga_downloads
存储已下载的漫画记录

- `id`: UUID
- `title`: 漫画标题
- `author`: 作者名
- `work_name`: 作品名
- `manga_url`: 漫画URL（唯一）
- `file_size`: 文件大小（字节）
- `page_count`: 页数
- `updated_at`: 更新时间
- `downloaded_at`: 下载时间
- `file_path`: 文件路径

### manga_updates
存储收藏夹中的所有漫画（包括已下载和未下载）

- 字段与 `manga_downloads` 类似
- `is_downloaded`: 是否已下载

### favorite_authors
存储收藏的作者

- `id`: UUID
- `author_name`: 作者名（唯一）

## API 路由

- `POST /api/manga/sync` - 同步收藏夹
- `POST /api/manga/download` - 下载单个漫画
- `POST /api/manga/download-batch` - 批量下载
- `GET /api/manga/recent-updates` - 获取最近更新

## 注意事项

1. **爬虫实现**: 需要根据目标网站的具体结构实现爬虫逻辑
2. **存储配置**: 需要配置文件存储方式（本地或云存储）
3. **会话管理**: 需要实现网站登录和会话保持
4. **速率限制**: 建议添加请求延迟避免被封禁
5. **错误处理**: 完善错误处理和重试机制

## 待实现功能

- [ ] 实现具体的爬虫逻辑
- [ ] 配置文件存储
- [ ] 添加登录界面
- [ ] 实现下载进度显示
- [ ] 添加搜索和筛选功能
- [ ] 支持多个漫画网站

## 许可

MIT
