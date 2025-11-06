#!/bin/bash
# 群晖NAS自动从GitHub初始化项目脚本
# 使用方法: ./init-from-github.sh

set -e

# 配置
PROJECT_DIR="/volume1/docker/wnacg-downloader"
GITHUB_REPO="https://github.com/staringX/wnacg-downloader.git"
BRANCH="main"

echo "=========================================="
echo "群晖NAS自动部署脚本"
echo "=========================================="
echo ""

# 检查目录是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo "📁 创建项目目录: $PROJECT_DIR"
    mkdir -p "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# 检查是否已有代码
if [ -d ".git" ]; then
    echo "✅ 检测到已有Git仓库"
    echo "🔄 更新代码..."
    git pull origin "$BRANCH" || {
        echo "⚠️  更新失败，使用现有代码"
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
        echo "⚠️  请编辑 .env 文件，修改NAS_IP等配置"
    else
        echo "⚠️  未找到 .env.example，请手动创建 .env 文件"
    fi
else
    echo "✅ .env 文件已存在"
fi

echo ""
echo "=========================================="
echo "✅ 初始化完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 编辑 .env 文件，修改NAS_IP等配置"
echo "2. 运行: docker-compose -f docker-compose.synology.auto.yml up -d"
echo ""

