#!/bin/bash
# ============================================================
# 部署脚本 - 智能体工程师培养计划 项目7
# 用途：自动化部署 Agent 应用到生产服务器
# 使用方法：./scripts/deploy.sh [环境]
#   环境：staging（默认）或 production
# ============================================================

set -e  # 遇到错误立即退出

# ============ 配置 ============
ENVIRONMENT=${1:-staging}
PROJECT_NAME="multi-agent"
DOCKER_COMPOSE_FILE="docker-compose.yml"
BACKUP_DIR="/opt/backups/${PROJECT_NAME}"
LOG_FILE="./logs/deploy_$(date +%Y%m%d_%H%M%S).log"

# ============ 颜色输出 ============
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
    echo "[INFO] $1" >> "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "[WARN] $1" >> "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "[ERROR] $1" >> "$LOG_FILE"
}

# ============ 检查依赖 ============
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    log_info "依赖检查通过"
}

# ============ 加载环境变量 ============
load_env() {
    log_info "加载环境变量（环境：${ENVIRONMENT}）..."
    
    if [ "$ENVIRONMENT" = "production" ]; then
        ENV_FILE=".env.production"
    else
        ENV_FILE=".env.staging"
    fi
    
    if [ ! -f "$ENV_FILE" ]; then
        log_warn "$ENV_FILE 不存在，使用 .env.example 作为模板"
        if [ -f ".env.example" ]; then
            cp .env.example "$ENV_FILE"
            log_warn "请编辑 $ENV_FILE 填入真实的配置值"
        else
            log_error ".env.example 不存在，无法继续"
            exit 1
        fi
    fi
    
    # 加载环境变量
    export $(grep -v '^#' "$ENV_FILE" | xargs)
    
    log_info "环境变量加载完成"
}

# ============ 备份当前版本 ============
backup_current() {
    log_info "备份当前版本..."
    
    mkdir -p "$BACKUP_DIR"
    
    # 备份镜像
    BACKUP_TAG=$(date +%Y%m%d_%H%M%S)
    if docker images -q ${PROJECT_NAME}:latest &> /dev/null; then
        docker tag ${PROJECT_NAME}:latest ${PROJECT_NAME}:backup_${BACKUP_TAG}
        log_info "当前版本已备份为 ${PROJECT_NAME}:backup_${BACKUP_TAG}"
    fi
    
    # 备份数据卷（如果存在）
    if docker volume ls | grep -q "${PROJECT_NAME}_redis-data"; then
        log_info "备份 Redis 数据..."
        docker run --rm -v ${PROJECT_NAME}_redis-data:/data -v ${BACKUP_DIR}:/backup \
            alpine tar czf /backup/redis_${BACKUP_TAG}.tar.gz -C /data .
    fi
    
    log_info "备份完成"
}

# ============ 构建镜像 ============
build_image() {
    log_info "构建 Docker 镜像..."
    
    docker compose -f "$DOCKER_COMPOSE_FILE" build --no-cache
    
    if [ $? -eq 0 ]; then
        log_info "镜像构建成功"
    else
        log_error "镜像构建失败"
        exit 1
    fi
}

# ============ 拉取最新镜像 ============
pull_images() {
    log_info "拉取最新镜像..."
    
    docker compose -f "$DOCKER_COMPOSE_FILE" pull
    
    log_info "镜像拉取完成"
}

# ============ 启动服务 ============
start_services() {
    log_info "启动服务..."
    
    # 停止旧服务
    docker compose -f "$DOCKER_COMPOSE_FILE" down || true
    
    # 启动新服务
    docker compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    log_info "服务已启动"
}

# ============ 健康检查 ============
health_check() {
    log_info "执行健康检查..."
    
    MAX_RETRIES=10
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -f http://localhost:${APP_PORT:-8000}/health &> /dev/null; then
            log_info "健康检查通过"
            return 0
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        log_warn "健康检查失败，重试 $RETRY_COUNT/$MAX_RETRIES..."
        sleep 5
    done
    
    log_error "健康检查失败，部署可能失败"
    return 1
}

# ============ 清理旧镜像 ============
cleanup() {
    log_info "清理旧镜像..."
    
    # 删除未使用的镜像
    docker image prune -f
    
    # 删除备份镜像（保留最近 5 个）
    BACKUP_IMAGES=$(docker images -q ${PROJECT_NAME}:backup_* | head -n -5)
    if [ -n "$BACKUP_IMAGES" ]; then
        docker rmi $BACKUP_IMAGES || true
    fi
    
    log_info "清理完成"
}

# ============ 主流程 ============
main() {
    log_info "开始部署到 ${ENVIRONMENT} 环境"
    log_info "日志文件：$LOG_FILE"
    
    # 创建日志目录
    mkdir -p ./logs
    mkdir -p "$BACKUP_DIR"
    
    # 执行部署步骤
    check_dependencies
    load_env
    backup_current
    pull_images
    start_services
    
    # 等待服务启动
    sleep 10
    
    # 健康检查
    if health_check; then
        log_info "部署成功！"
        cleanup
    else
        log_error "部署失败，开始回滚..."
        rollback
        exit 1
    fi
}

# ============ 回滚 ============
rollback() {
    log_warn "开始回滚到上一个版本..."
    
    # 获取最近的备份镜像
    LATEST_BACKUP=$(docker images -q ${PROJECT_NAME}:backup_* | head -n 1)
    
    if [ -n "$LATEST_BACKUP" ]; then
        docker tag $LATEST_BACKUP ${PROJECT_NAME}:latest
        docker compose -f "$DOCKER_COMPOSE_FILE" up -d
        log_info "回滚完成"
    else
        log_error "没有可用的备份镜像，无法回滚"
    fi
}

# ============ 脚本入口 ============
main "$@"
