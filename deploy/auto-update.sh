#!/bin/bash

# 自动化部署脚本 - VPS自动更新应用和重启服务
# 配合GitHub Actions或定时任务使用
# 用法: bash auto-update.sh [start|stop|restart|update|logs|status]

set -e

# 配置
APP_DIR="/opt/secondhand-platform"
DOCKER_COMPOSE="docker-compose -f docker-compose-prod.yml"
LOG_FILE="/var/log/secondhand-platform/deploy.log"
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"
EMAIL_TO="${DEPLOY_NOTIFICATION_EMAIL:-}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

notify_slack() {
    if [ ! -z "$SLACK_WEBHOOK" ]; then
        curl -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"$1\"}" \
            2>/dev/null || true
    fi
}

notify_email() {
    if [ ! -z "$EMAIL_TO" ]; then
        echo "$1" | mail -s "VPS部署通知" "$EMAIL_TO" 2>/dev/null || true
    fi
}

check_status() {
    log "🔍 检查服务状态..."
    
    echo -e "\n${BLUE}容器状态:${NC}"
    cd "$APP_DIR"
    $DOCKER_COMPOSE ps
    
    echo -e "\n${BLUE}应用健康检查:${NC}"
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 应用运行正常${NC}"
    else
        echo -e "${RED}❌ 应用无法访问${NC}"
    fi
    
    echo -e "\n${BLUE}磁盘空间:${NC}"
    df -h "$APP_DIR"
    
    echo -e "\n${BLUE}数据库连接:${NC}"
    cd "$APP_DIR"
    $DOCKER_COMPOSE exec -T postgres pg_isready -U secondhand_user || true
}

start_services() {
    log "🚀 启动服务..."
    
    cd "$APP_DIR"
    $DOCKER_COMPOSE up -d
    
    # 等待服务启动
    sleep 10
    
    # 检查健康状态
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "✅ 服务启动成功"
        notify_slack "✅ VPS应用已启动"
    else
        log "❌ 服务启动失败"
        notify_slack "❌ VPS应用启动失败，请检查日志"
        exit 1
    fi
}

stop_services() {
    log "⛔ 停止服务..."
    
    cd "$APP_DIR"
    $DOCKER_COMPOSE down
    
    log "✅ 服务已停止"
}

restart_services() {
    log "🔄 重启服务..."
    
    cd "$APP_DIR"
    $DOCKER_COMPOSE restart
    
    # 等待服务重启
    sleep 10
    
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "✅ 服务重启成功"
        notify_slack "✅ VPS应用已重启"
    else
        log "❌ 服务重启失败"
        notify_slack "❌ VPS应用重启失败"
        exit 1
    fi
}

update_app() {
    log "📦 更新应用代码..."
    
    cd "$APP_DIR"
    
    # 检查git状态
    if [ ! -d ".git" ]; then
        log "❌ 不是Git仓库"
        exit 1
    fi
    
    # 获取当前分支
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    log "当前分支: $CURRENT_BRANCH"
    
    # 获取最新代码
    log "拉取最新代码..."
    git fetch origin "$CURRENT_BRANCH"
    
    # 检查是否有新更新
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse "origin/$CURRENT_BRANCH")
    
    if [ "$LOCAL" = "$REMOTE" ]; then
        log "✅ 应用已是最新版本 ($LOCAL)"
        return 0
    fi
    
    log "发现新版本，从 $LOCAL 更新到 $REMOTE"
    
    # 创建备份
    log "创建备份..."
    BACKUP_DIR="/opt/secondhand-platform-backup-$(date +%Y%m%d_%H%M%S)"
    cp -r "$APP_DIR" "$BACKUP_DIR"
    log "备份位置: $BACKUP_DIR"
    
    # 更新代码
    git reset --hard "origin/$CURRENT_BRANCH"
    
    # 更新依赖
    log "更新Python依赖..."
    $DOCKER_COMPOSE exec -T app pip install -r requirements.txt --no-cache-dir
    
    # 重建镜像（如果Dockerfile有变化）
    log "重建应用镜像..."
    $DOCKER_COMPOSE build --no-cache app
    
    # 重启服务
    log "重启应用服务..."
    $DOCKER_COMPOSE up -d app
    
    sleep 10
    
    # 验证更新
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "✅ 应用更新成功 (版本: $REMOTE)"
        notify_slack "✅ VPS应用已更新至 $REMOTE"
    else
        log "❌ 应用更新失败，正在恢复..."
        rm -rf "$APP_DIR"
        mv "$BACKUP_DIR" "$APP_DIR"
        $DOCKER_COMPOSE restart app
        notify_slack "❌ 应用更新失败，已回滚至前一版本"
        exit 1
    fi
}

show_logs() {
    log "📋 显示应用日志..."
    
    cd "$APP_DIR"
    
    if [ ! -z "$1" ]; then
        # 显示特定服务的日志
        $DOCKER_COMPOSE logs -f --tail 100 "$1"
    else
        # 显示所有日志
        $DOCKER_COMPOSE logs -f --tail 100
    fi
}

backup_database() {
    log "💾 备份数据库..."
    
    BACKUP_DIR="/var/backups/secondhand-platform"
    mkdir -p "$BACKUP_DIR"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    
    cd "$APP_DIR"
    
    # 备份PostgreSQL
    log "备份PostgreSQL..."
    $DOCKER_COMPOSE exec -T postgres pg_dump \
        -U secondhand_user \
        -d secondhand_db \
        > "$BACKUP_DIR/postgres_backup_$TIMESTAMP.sql"
    
    # 备份MongoDB
    log "备份MongoDB..."
    $DOCKER_COMPOSE exec -T mongo mongodump \
        --username mongo_admin \
        --password change_me \
        --authenticationDatabase admin \
        --out "$BACKUP_DIR/mongo_backup_$TIMESTAMP"
    
    # 压缩备份
    log "压缩备份文件..."
    tar -czf "$BACKUP_DIR/backup_$TIMESTAMP.tar.gz" \
        "$BACKUP_DIR/postgres_backup_$TIMESTAMP.sql" \
        "$BACKUP_DIR/mongo_backup_$TIMESTAMP"
    
    # 删除原始备份文件
    rm -f "$BACKUP_DIR/postgres_backup_$TIMESTAMP.sql"
    rm -rf "$BACKUP_DIR/mongo_backup_$TIMESTAMP"
    
    # 删除30天前的备份
    find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +30 -delete
    
    log "✅ 备份完成: $BACKUP_DIR/backup_$TIMESTAMP.tar.gz"
}

# 清理日志
cleanup_logs() {
    log "🧹 清理过期日志..."
    
    # 删除30天前的日志
    find /var/log/secondhand-platform -name "*.log" -mtime +30 -delete
    find "$APP_DIR/logs" -name "*.log" -mtime +30 -delete
    
    log "✅ 日志清理完成"
}

# 主函数
main() {
    mkdir -p "$(dirname "$LOG_FILE")"
    
    case "${1:-status}" in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        update)
            update_app
            restart_services
            ;;
        logs)
            show_logs "$2"
            ;;
        status)
            check_status
            ;;
        backup)
            backup_database
            cleanup_logs
            ;;
        *)
            echo -e "${YELLOW}用法: $0 {start|stop|restart|update|logs|status|backup} [service_name]${NC}"
            echo ""
            echo "命令说明:"
            echo "  start     - 启动所有服务"
            echo "  stop      - 停止所有服务"
            echo "  restart   - 重启所有服务"
            echo "  update    - 从Git拉取最新代码并更新应用"
            echo "  logs      - 显示应用日志（可指定服务）"
            echo "  status    - 检查服务状态"
            echo "  backup    - 备份数据库"
            echo ""
            echo "示例:"
            echo "  $0 status              # 检查状态"
            echo "  $0 logs app            # 查看应用日志"
            echo "  $0 update              # 更新应用并重启"
            echo "  $0 backup              # 备份数据库"
            exit 1
            ;;
    esac
}

main "$@"
