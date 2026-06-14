#!/bin/bash
# ============================================================
# 备份脚本 - 智能体工程师培养计划 项目7
# 用途：备份 Docker 卷数据、镜像、配置文件
# 使用方法：./scripts/backup.sh [选项]
#   选项：
#     --full      完整备份（数据 + 镜像 + 配置）
#     --data-only 仅备份数据卷
#     --images    仅备份镜像
# ============================================================

set -e

# ============ 配置 ============
PROJECT_NAME="multi-agent"
BACKUP_ROOT="/opt/backups/${PROJECT_NAME}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
RETENTION_DAYS=7  # 备份保留天数

# ============ 颜色输出 ============
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============ 检查 Docker ============
check_docker() {
    log_info "检查 Docker..."
    
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker 未运行，请先启动 Docker"
        exit 1
    fi
    
    log_info "Docker 运行正常"
}

# ============ 备份数据卷 ============
backup_volumes() {
    log_info "备份数据卷..."
    
    mkdir -p "$BACKUP_DIR/volumes"
    
    # 备份 Redis 数据
    if docker volume ls | grep -q "${PROJECT_NAME}_redis-data"; then
        log_info "备份 Redis 数据..."
        docker run --rm \
            -v ${PROJECT_NAME}_redis-data:/data \
            -v ${BACKUP_DIR}/volumes:/backup \
            alpine tar czf /backup/redis-data.tar.gz -C /data .
    fi
    
    # 备份 Postgres 数据
    if docker volume ls | grep -q "${PROJECT_NAME}_postgres-data"; then
        log_info "备份 Postgres 数据..."
        docker run --rm \
            -v ${PROJECT_NAME}_postgres-data:/data \
            -v ${BACKUP_DIR}/volumes:/backup \
            alpine tar czf /backup/postgres-data.tar.gz -C /data .
    fi
    
    # 备份 Chroma 数据
    if docker volume ls | grep -q "${PROJECT_NAME}_chroma-data"; then
        log_info "备份 Chroma 数据..."
        docker run --rm \
            -v ${PROJECT_NAME}_chroma-data:/data \
            -v ${BACKUP_DIR}/volumes:/backup \
            alpine tar czf /backup/chroma-data.tar.gz -C /data .
    fi
    
    log_info "数据卷备份完成"
}

# ============ 备份镜像 ============
backup_images() {
    log_info "备份 Docker 镜像..."
    
    mkdir -p "$BACKUP_DIR/images"
    
    # 获取所有相关镜像
    IMAGES=$(docker compose images -q | sort -u)
    
    for IMAGE in $IMAGES; do
        IMAGE_NAME=$(docker inspect --format='{{.RepoTags}}' $IMAGE | sed 's/\[//g;s/\]//g;s/:/_/g;s/\//_/g')
        log_info "备份镜像：$IMAGE_NAME"
        docker save $IMAGE -o "$BACKUP_DIR/images/${IMAGE_NAME}.tar"
    done
    
    log_info "镜像备份完成"
}

# ============ 备份配置文件 ============
backup_configs() {
    log_info "备份配置文件..."
    
    mkdir -p "$BACKUP_DIR/config"
    
    # 备份关键配置文件
    cp docker-compose.yml "$BACKUP_DIR/config/" 2>/dev/null || true
    cp .env "$BACKUP_DIR/config/" 2>/dev/null || true
    cp -r nginx/ "$BACKUP_DIR/config/" 2>/dev/null || true
    cp -r prometheus/ "$BACKUP_DIR/config/" 2>/dev/null || true
    cp -r grafana/ "$BACKUP_DIR/config/" 2>/dev/null || true
    
    log_info "配置文件备份完成"
}

# ============ 清理旧备份 ============
cleanup_old_backups() {
    log_info "清理 ${RETENTION_DAYS} 天前的旧备份..."
    
    find "$BACKUP_ROOT" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null || true
    
    log_info "旧备份清理完成"
}

# ============ 生成备份报告 ============
generate_report() {
    log_info "生成备份报告..."
    
    REPORT_FILE="$BACKUP_DIR/backup_report.txt"
    
    cat > "$REPORT_FILE" << EOF
============================================================
备份报告
============================================================

备份时间: $(date)
备份目录: $BACKUP_DIR

数据卷:
$(ls -lh "$BACKUP_DIR/volumes/" 2>/dev/null || echo "  无")

镜像:
$(ls -lh "$BACKUP_DIR/images/" 2>/dev/null || echo "  无")

配置文件:
$(ls -lh "$BACKUP_DIR/config/" 2>/dev/null || echo "  无")

总大小: $(du -sh "$BACKUP_DIR" | cut -f1)
============================================================
EOF
    
    log_info "备份报告已生成：$REPORT_FILE"
}

# ============ 恢复数据卷 ============
restore_volumes() {
    local RESTORE_DIR=$1
    
    log_info "从 $RESTORE_DIR 恢复数据卷..."
    
    # 恢复 Redis 数据
    if [ -f "$RESTORE_DIR/volumes/redis-data.tar.gz" ]; then
        log_info "恢复 Redis 数据..."
        docker run --rm \
            -v ${PROJECT_NAME}_redis-data:/data \
            -v ${RESTORE_DIR}/volumes:/backup \
            alpine tar xzf /backup/redis-data.tar.gz -C /data
    fi
    
    # 恢复 Postgres 数据
    if [ -f "$RESTORE_DIR/volumes/postgres-data.tar.gz" ]; then
        log_info "恢复 Postgres 数据..."
        docker run --rm \
            -v ${PROJECT_NAME}_postgres-data:/data \
            -v ${RESTORE_DIR}/volumes:/backup \
            alpine tar xzf /backup/postgres-data.tar.gz -C /data
    fi
    
    # 恢复 Chroma 数据
    if [ -f "$RESTORE_DIR/volumes/chroma-data.tar.gz" ]; then
        log_info "恢复 Chroma 数据..."
        docker run --rm \
            -v ${PROJECT_NAME}_chroma-data:/data \
            -v ${RESTORE_DIR}/volumes:/backup \
            alpine tar xzf /backup/chroma-data.tar.gz -C /data
    fi
    
    log_info "数据卷恢复完成"
}

# ============ 主流程 ============
main() {
    local MODE=${1:-"--full"}
    
    log_info "开始备份（模式：$MODE）"
    log_info "备份目录：$BACKUP_DIR"
    
    # 创建备份目录
    mkdir -p "$BACKUP_DIR"
    
    # 检查 Docker
    check_docker
    
    # 根据模式执行备份
    case $MODE in
        --full)
            backup_volumes
            backup_images
            backup_configs
            ;;
        --data-only)
            backup_volumes
            ;;
        --images)
            backup_images
            ;;
        --restore)
            if [ -z "$2" ]; then
                log_error "请指定恢复目录：./backup.sh --restore <备份目录>"
                exit 1
            fi
            restore_volumes "$2"
            exit 0
            ;;
        *)
            log_error "未知模式：$MODE"
            log_info "支持的模式：--full, --data-only, --images, --restore"
            exit 1
            ;;
    esac
    
    # 生成报告
    generate_report
    
    # 清理旧备份
    cleanup_old_backups
    
    log_info "备份完成！"
    log_info "备份位置：$BACKUP_DIR"
}

# ============ 脚本入口 ============
main "$@"
