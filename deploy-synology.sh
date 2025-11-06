#!/bin/bash
# 群晖NAS一键部署脚本
# 自动从GitHub拉取代码并启动服务
# 使用方法: ./deploy-synology.sh

set -e

# 配置
PROJECT_DIR="/volume1/docker/wnacg-downloader"
GITHUB_REPO="https://github.com/staringX/wnacg-downloader.git"
BRANCH="main"
COMPOSE_FILE="docker-compose.synology.auto.yml"

echo "=========================================="
echo "群晖NAS一键部署脚本"
echo "=========================================="
echo ""

# 进入项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo "📁 创建项目目录: $PROJECT_DIR"
    mkdir -p "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# 检查并更新代码
if [ -d ".git" ]; then
    echo "🔄 更新代码..."
    git pull origin "$BRANCH" || {
        echo "⚠️  更新失败，使用现有代码继续部署"
    }
else
    echo "📥 首次部署：从GitHub克隆仓库..."
    git clone -b "$BRANCH" "$GITHUB_REPO" .
    echo "✅ 克隆完成"
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p backend/downloads backend/covers backend/logs
chmod -R 755 backend/downloads backend/covers backend/logs

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo "📝 创建环境变量文件..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ 已从 .env.example 创建 .env 文件"
        echo "⚠️  请编辑 .env 文件，修改NAS_IP等配置后再运行此脚本"
        exit 1
    else
        echo "❌ 未找到 .env.example，请手动创建 .env 文件"
        exit 1
    fi
fi

# 检查compose文件
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ 未找到 $COMPOSE_FILE 文件"
    exit 1
fi

# 停止现有服务（如果存在）
echo "🛑 停止现有服务..."
docker-compose -f "$COMPOSE_FILE" down 2>/dev/null || true

# 启动服务
echo "🚀 启动服务..."
docker-compose -f "$COMPOSE_FILE" up -d --build

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 显示服务状态
echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "📊 服务状态："
docker-compose -f "$COMPOSE_FILE" ps
echo ""
echo "📋 查看日志："
echo "  docker-compose -f $COMPOSE_FILE logs -f"
echo ""
echo "🌐 访问地址（请根据.env中的配置修改）："
echo "  - 前端: http://您的NAS_IP:3000"
echo "  - 后端API: http://您的NAS_IP:8000"
echo ""

