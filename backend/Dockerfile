FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖和Chromium（支持ARM架构）
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# 创建符号链接，使Selenium可以找到chromium
RUN ln -s /usr/bin/chromium /usr/bin/chromium-browser || true \
    && ln -s /usr/bin/chromedriver /usr/local/bin/chromedriver || true

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p downloads covers data

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
