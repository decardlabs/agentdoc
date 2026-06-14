# ============================================================
# 多阶段 Dockerfile - 智能体工程师培养计划 项目7
# 用途：构建优化的 Agent 应用镜像
# 阶段 1: builder - 构建依赖
# 阶段 2: runtime - 运行时镜像
# ============================================================

# ============================================================
# 阶段 1: 构建依赖 (builder)
# 只安装编译需要的工具，不进入最终镜像
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# 安装编译依赖（gcc 用于编译 C 扩展包如 cryptography、uvloop）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libffi-dev \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 先只复制 requirements.txt，利用 Docker 层缓存
# 只有当依赖变化时才会重新构建这一层
COPY requirements.txt .

# 安装到 /install 目录（不污染系统 Python）
# --no-cache-dir: 不缓存下载的包，减小镜像大小
# --extra-index-url: 如果需要 PyTorch 等大型包，可以从 PyTorch 官方源下载
RUN pip install --prefix=/install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt


# ============================================================
# 阶段 2: 运行时镜像 (runtime)
# 只包含运行需要的最小文件
# ============================================================
FROM python:3.11-slim AS runtime

# 安装运行时系统依赖
# curl: 用于健康检查
# libpq5: PostgreSQL 客户端库
# tini: 轻量级初始化进程，正确处理信号，避免僵尸进程
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# 从 builder 阶段复制已编译的 Python 包
COPY --from=builder /install /usr/local

# 创建非 root 用户（安全实践）
# 避免使用 root 用户运行应用，减少安全风险
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /sbin/nologin appuser

# 复制应用代码
# --chown=appuser:appuser: 设置文件所有者为 appuser
COPY --chown=appuser:appuser src/ ./src/

# 设置环境变量
# TZ: 时区设置为上海
# LANG: 字符集为 UTF-8
# PYTHONUNBUFFERED=1: Python 输出不缓冲，确保日志实时输出
# PYTHONDONTWRITEBYTECODE=1: 不生成 .pyc 文件
# PATH: 确保脚本可在任意目录执行
ENV TZ=Asia/Shanghai \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/usr/local/bin:$PATH

# 创建日志目录并设置权限
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs

# 切换到非 root 用户
USER appuser

# 健康检查：每 30 秒检查一次，超时 10 秒，启动后 40 秒开始
# 确保容器健康后才接收流量
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 使用 tinit 作为 PID 1（正确处理信号，避免僵尸进程）
ENTRYPOINT ["tini", "--"]

# 启动命令
# --host 0.0.0.0: 监听所有网络接口
# --port 8000: 端口
# --workers 2: 2 个 worker 进程
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
