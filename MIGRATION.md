# 数据库迁移指南

## PostgreSQL → SQLite 迁移说明

本项目已从 PostgreSQL 切换到 SQLite，以简化部署和维护。

### 🎯 切换优势

- ✅ **简化部署**：无需额外的数据库容器
- ✅ **降低资源占用**：SQLite 轻量级
- ✅ **方便备份**：单个文件即可备份整个数据库
- ✅ **更快启动**：无需等待数据库服务健康检查

### 📦 新用户

如果您是新用户，无需任何操作，直接使用即可：

```bash
# Docker 部署
docker-compose up -d

# 或本地开发
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 🔄 从 PostgreSQL 迁移

如果您之前使用 PostgreSQL 版本并有数据需要迁移：

#### 方案1：重新同步（推荐）

最简单的方式是重新同步收藏夹，这样可以确保数据的完整性：

```bash
# 1. 停止旧容器
docker-compose down

# 2. 删除旧的 volume（如果不需要保留 PostgreSQL 数据）
docker volume rm manga_postgres_data

# 3. 拉取最新代码
git pull

# 4. 重新构建并启动
docker-compose up -d --build

# 5. 访问前端，点击"同步收藏夹"按钮
```

#### 方案2：手动迁移数据

如果您有重要的自定义数据（如下载记录），可以手动迁移：

1. **导出 PostgreSQL 数据**：
```bash
# 连接到 PostgreSQL
docker exec -it manga_db_1 psql -U manga_user -d manga_db

# 导出数据
\copy mangas TO '/tmp/mangas.csv' CSV HEADER;
```

2. **启动新的 SQLite 系统**：
```bash
docker-compose up -d --build
```

3. **导入数据到 SQLite**：
```python
# 创建脚本 import_data.py
import sqlite3
import csv

conn = sqlite3.connect('backend/manga.db')
cursor = conn.cursor()

with open('mangas.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cursor.execute('''
            INSERT INTO mangas (id, title, author, manga_url, page_count, updated_at, cover_image_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (row['id'], row['title'], row['author'], row['manga_url'], 
              row['page_count'], row['updated_at'], row['cover_image_url'], row['created_at']))

conn.commit()
conn.close()
```

### 🔍 验证迁移

访问以下地址确认系统正常运行：

- 前端：http://localhost:3000
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

检查数据是否正确：
```bash
# 进入 backend 容器
docker exec -it manga_backend_1 sh

# 查看数据库
sqlite3 /app/data/manga.db
sqlite> SELECT COUNT(*) FROM mangas;
sqlite> .quit
```

### 🗄️ 数据库备份

SQLite 数据库备份非常简单：

```bash
# Docker 部署 - 备份 volume
docker run --rm -v manga_sqlite_data:/data -v $(pwd):/backup alpine tar czf /backup/manga_backup.tar.gz /data

# 本地开发 - 直接复制文件
cp backend/manga.db backend/manga.db.backup
```

### ⚠️ 注意事项

1. SQLite 不支持高并发写入，但对于本项目的使用场景完全足够
2. 如果需要在生产环境支持高并发，可以随时切换回 PostgreSQL
3. 数据库文件位置：
   - Docker：`/app/data/manga.db`（挂载到 `sqlite_data` volume）
   - 本地：`backend/manga.db`

### 🔙 回滚到 PostgreSQL

如果需要回滚到 PostgreSQL：

```bash
# 切换到旧版本
git checkout <postgresql-commit-hash>

# 重新构建
docker-compose down -v
docker-compose up -d --build
```

## 常见问题

**Q: 为什么切换到 SQLite？**
A: 简化部署，降低资源占用，对于个人使用的漫画管理系统来说完全够用。

**Q: SQLite 性能够吗？**
A: 对于本项目的使用场景（个人使用，偶尔同步和下载）完全足够。SQLite 的读取性能非常好。

**Q: 如何备份数据？**
A: 只需要备份 `manga.db` 这一个文件即可。

**Q: 可以同时使用多个客户端吗？**
A: 可以，SQLite 支持多个读取连接和一个写入连接。

## 需要帮助？

如有问题，请在 GitHub Issues 中反馈。

