#!/bin/bash
# 启动后端服务脚本

cd "$(dirname "$0")"

# 激活虚拟环境
source .venv/bin/activate

# 启动服务
echo "🚀 启动后端服务..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
