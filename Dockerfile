# ============================================================
# 方案B：FastAPI 集约配信
# ① Node 阶段构建 Vite 前端 → dist/
# ② Python 阶段构建后端镜像，并将 dist/ 复制到 app/static
# 构建上下文需为仓库根目录（同时包含 frontend/ 与 backend/）。
# ============================================================

# ---- ① 前端构建 ----
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend

# 先装依赖（利用层缓存）
# 注意：使用 npm install 而非 npm ci —— lockfile 在 macOS 生成，
# 缺少 Linux 平台的原生可选依赖（@tailwindcss/oxide → @emnapi/runtime），
# npm ci 的严格校验会失败；npm install 会按当前平台补齐。
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --no-audit --no-fund

# 再拷贝源码并构建
COPY frontend/ ./
RUN npm run build


# ---- ② 后端镜像（含前端静态产物）----
FROM python:3.11-slim

WORKDIR /app

# 系统依赖（Chromium 已移除：爬虫改用 requests + BeautifulSoup）
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 后端代码
COPY backend/ .

# 前端构建产物 → app/static（由 app/main.py 挂载）
COPY --from=frontend-builder /frontend/dist ./app/static

# 必要目录
RUN mkdir -p downloads covers data migrations/versions

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
