# 使用官方 Python 3.10 slim 镜像，体积小，与 Vagrant VM 版本一致
FROM python:3.10-slim

# 不生成 .pyc 文件；日志实时输出，不在容器内缓冲
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 安装系统依赖：
#   build-essential / pkg-config        — 编译 C 扩展（mysqlclient）所需
#   default-libmysqlclient-dev          — mysqlclient 的 MySQL 客户端头文件
#   netcat-openbsd                      — entrypoint 脚本用于探测服务端口是否就绪
#   libmagic1                           — python-magic 的运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    netcat-openbsd \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# 先只拷贝依赖清单并安装。为什么单独这一步？
# Docker 是分层缓存的：只要 requirements 没变，
# 这一层就会被缓存，以后改代码重新 build 时不必重装所有依赖，快很多
COPY requirements-docker.txt .
RUN pip install --upgrade pip 'setuptools<80' && \
    pip install --no-cache-dir --no-deps -r requirements-docker.txt

# 再拷贝项目其余代码
COPY . .

# 声明 Django 端口（仅作文档说明，真正的端口映射在 docker-compose 里做）
EXPOSE 8000

# 默认启动命令（compose 里会覆盖它，这里给个兜底）
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
