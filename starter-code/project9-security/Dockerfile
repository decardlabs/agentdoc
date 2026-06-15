# ============================================================
# Dockerfile - 智能体工程师培养计划 项目 9
# 用途：构建安全测试 Agent 镜像（与 docker-compose.security.yml 配套）
# ============================================================

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装运行时系统依赖
# curl: 用于健康检查
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 先复制 requirements.txt，利用 Docker 层缓存
COPY requirements.txt .

# 安装 Python 依赖
# --no-cache-dir: 不缓存下载的包，减小镜像大小
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/

# 设置环境变量
ENV TZ=Asia/Shanghai \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO

# 创建日志目录
RUN mkdir -p /app/logs /app/reports

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
