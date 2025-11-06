# 群晖NAS部署指南

本指南将帮助您在群晖NAS上部署漫画下载管理器项目。

## 前置要求

1. **群晖NAS**（支持Docker的型号）
2. **Docker套件**已安装
3. **SSH访问权限**（推荐）或使用群晖的Docker GUI

## 部署步骤

### 方式一：使用Docker Compose自动从GitHub拉取（推荐）⭐

使用 `docker-compose.synology.auto.yml`，它包含一个init容器自动从GitHub拉取代码，**无需手动克隆仓库**。

#### 1. SSH连接到群晖NAS

```bash
ssh admin@您的NAS_IP
```

#### 2. 创建项目目录

```bash
# 创建项目目录
mkdir -p /volume1/docker/wnacg-downloader
cd /volume1/docker/wnacg-downloader
```

#### 3. 下载docker-compose配置文件

```bash
# 下载自动拉取配置
curl -O https://raw.githubusercontent.com/staringX/wnacg-downloader/main/docker-compose.synology.auto.yml

# 下载环境变量示例（可选）
curl -O https://raw.githubusercontent.com/staringX/wnacg-downloader/main/.env.example
```

#### 4. 配置环境变量

```bash
# 复制示例文件
cp .env.example .env

# 编辑环境变量
nano .env
```

修改以下配置：
```env
NEXT_PUBLIC_API_URL=http://您的NAS_IP:8000
CORS_ORIGINS=["http://您的NAS_IP:3000","http://localhost:3000"]
MANGA_USERNAME=您的用户名
MANGA_PASSWORD=您的密码
```

#### 5. 启动服务（自动从GitHub拉取代码）

```bash
# 直接运行，init容器会自动从GitHub克隆/更新代码
docker-compose -f docker-compose.synology.auto.yml up -d --build
```

**说明**：
- ✅ 首次运行：init容器会自动从GitHub克隆代码
- ✅ 后续运行：init容器会自动更新代码到最新版本
- ✅ 无需手动克隆：所有操作都在docker-compose中自动完成

#### 更新项目

以后更新代码只需重新运行：
```bash
docker-compose -f docker-compose.synology.auto.yml up -d --build
```

init容器会自动拉取最新代码。

---

### 方式二：手动部署（传统方式）

#### 1. 准备项目文件

在您的电脑上：
```bash
# 克隆或下载项目到本地
git clone https://github.com/staringX/wnacg-downloader.git
cd wnacg-downloader
```

#### 2. 上传项目到群晖NAS

使用以下任一方式上传项目文件到群晖NAS：

**方式A：使用SCP**
```bash
# 将整个项目文件夹上传到群晖NAS
scp -r /path/to/wnacg-downloader admin@您的NAS_IP:/volume1/docker/
```

**方式B：使用File Station**
1. 打开群晖File Station
2. 在 `/docker` 目录下创建 `wnacg-downloader` 文件夹
3. 将项目文件上传到该文件夹

**方式C：使用Git（如果NAS支持）**
```bash
# SSH连接到NAS后
cd /volume1/docker
git clone https://github.com/staringX/wnacg-downloader.git
cd wnacg-downloader
```

#### 3. 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
# 在NAS上编辑
nano .env
```

添加以下内容（根据实际情况修改）：
```env
# 漫画网站账号
MANGA_USERNAME=lilifan456
MANGA_PASSWORD=a2658208

# 发布页地址
PUBLISH_PAGE_URL=https://wn01.link

# 前端API地址（使用NAS的IP地址）
NEXT_PUBLIC_API_URL=http://您的NAS_IP:8000

# CORS配置（允许访问的域名）
CORS_ORIGINS=["http://您的NAS_IP:3000","http://localhost:3000"]
```

#### 4. 修改docker-compose.yml路径映射

群晖NAS的路径通常是 `/volume1/docker/...`，需要修改volume映射：

```yaml
# 将相对路径改为绝对路径
volumes:
  - /volume1/docker/wnacg-downloader/backend/downloads:/app/downloads
  - /volume1/docker/wnacg-downloader/backend/covers:/app/covers
```

#### 5. 创建必要的目录

```bash
# SSH连接到NAS
cd /volume1/docker/wnacg-downloader
mkdir -p backend/downloads backend/covers backend/logs
```

#### 6. 启动服务

```bash
# 进入项目目录
cd /volume1/docker/wnacg-downloader

# 构建并启动所有服务
docker-compose up -d --build

# 查看日志
docker-compose logs -f
```

---

### 方式三：使用群晖Docker GUI部署

#### 1. 准备docker-compose.yml

在群晖File Station中上传项目文件，并修改 `docker-compose.yml` 中的路径。

#### 2. 使用Container Manager

1. 打开 **Container Manager**（或Docker套件）
2. 点击 **项目** -> **创建**
3. 选择 **从docker-compose.yml创建**
4. 选择项目目录中的 `docker-compose.yml` 文件
5. 配置项目名称（如：`wnacg-downloader`）
6. 点击 **下一步** -> **完成**

#### 3. 配置环境变量

在Container Manager中：
1. 选择创建的项目
2. 编辑每个容器
3. 在 **环境** 标签页中添加环境变量

## 配置说明

### 端口映射

默认端口配置：
- **前端**: 3000
- **后端API**: 8000
- **PostgreSQL**: 5432

如果端口冲突，可以在 `docker-compose.yml` 中修改：
```yaml
ports:
  - "3001:3000"  # 前端改为3001
  - "8001:8000"  # 后端改为8001
```

### 数据持久化

- **数据库**: 使用Docker volume `postgres_data`，数据持久化
- **下载文件**: 映射到 `/volume1/docker/wnacg-downloader/backend/downloads`
- **封面图片**: 映射到 `/volume1/docker/wnacg-downloader/backend/covers`
- **日志文件**: 映射到 `/volume1/docker/wnacg-downloader/backend/logs`

### 网络配置

如果前端无法访问后端API，需要修改 `docker-compose.yml`：

```yaml
frontend:
  environment:
    # 使用NAS的IP地址或容器名
    NEXT_PUBLIC_API_URL: http://您的NAS_IP:8000
    # 或者使用Docker内部网络
    # NEXT_PUBLIC_API_URL: http://backend:8000
```

## 访问服务

部署完成后，通过以下地址访问：

- **前端界面**: `http://您的NAS_IP:3000`
- **后端API**: `http://您的NAS_IP:8000`
- **API文档**: `http://您的NAS_IP:8000/docs`

## 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
docker-compose logs backend -f  # 只看后端日志
docker-compose logs frontend -f  # 只看前端日志

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新代码后重新部署
git pull  # 如果使用git
docker-compose up -d --build

# 查看容器资源使用
docker stats
```

## 故障排查

### 1. 前端无法连接后端

**问题**: 前端显示无法连接到API

**解决**:
- 检查 `NEXT_PUBLIC_API_URL` 环境变量是否正确
- 确认后端服务正在运行：`docker-compose ps`
- 检查防火墙设置，确保端口8000和3000已开放

### 2. 数据库连接失败

**问题**: 后端无法连接数据库

**解决**:
- 检查数据库容器是否健康：`docker-compose ps db`
- 查看数据库日志：`docker-compose logs db`
- 确认 `DATABASE_URL` 环境变量正确

### 3. 文件权限问题

**问题**: 无法写入下载文件或封面

**解决**:
```bash
# 修改目录权限
chmod -R 777 /volume1/docker/wnacg-downloader/backend/downloads
chmod -R 777 /volume1/docker/wnacg-downloader/backend/covers
```

### 4. 端口冲突

**问题**: 端口已被占用

**解决**:
- 修改 `docker-compose.yml` 中的端口映射
- 或停止占用端口的其他服务

## 性能优化建议

1. **资源限制**: 在Container Manager中为容器设置CPU和内存限制
2. **存储位置**: 将下载目录放在SSD或高速存储上
3. **定期清理**: 定期清理日志文件和临时文件

## 备份建议

1. **数据库备份**:
```bash
# 导出数据库
docker-compose exec db pg_dump -U manga_user manga_db > backup.sql

# 恢复数据库
docker-compose exec -T db psql -U manga_user manga_db < backup.sql
```

2. **配置文件备份**: 备份 `.env` 和 `docker-compose.yml`

3. **数据备份**: 定期备份 `downloads` 和 `covers` 目录

## 安全建议

1. **修改默认密码**: 修改PostgreSQL的默认密码
2. **使用HTTPS**: 如果通过外网访问，建议配置反向代理（如Nginx）并启用HTTPS
3. **防火墙**: 只开放必要的端口
4. **定期更新**: 定期更新Docker镜像和项目代码

## 反向代理配置（可选）

如果使用群晖的Nginx反向代理：

1. 打开 **控制面板** -> **登录门户** -> **反向代理**
2. 创建反向代理规则：
   - **来源**: `https://您的域名`
   - **目标**: `http://localhost:3000`（前端）
   - **目标**: `http://localhost:8000`（后端API）

## 更新项目

```bash
# SSH连接到NAS
cd /volume1/docker/wnacg-downloader

# 拉取最新代码（如果使用git）
git pull

# 重新构建并启动
docker-compose up -d --build
```

## 技术支持

如遇问题，请查看：
- 项目GitHub: https://github.com/staringX/wnacg-downloader
- 日志文件: `backend/logs/`

