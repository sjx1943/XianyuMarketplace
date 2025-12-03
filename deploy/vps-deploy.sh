#!/bin/bash

# ==========================================
# 翠友雅集S - VPS一键部署脚本
# ==========================================
# 用法: sudo bash vps-deploy.sh [选项]
# 选项:
#   --init      首次部署，安装Docker并配置环境
#   --update    更新代码并重启应用
#   --restart   仅重启应用容器
#   --logs      查看应用日志
#   --status    查看服务状态
# ==========================================

set -e

# 配置
APP_DIR="/opt/secondhand-platform"
COMPOSE_FILE="deploy/docker-compose-vps.yml"
NGINX_CONF="deploy/nginx_secondhand_8543.conf"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  翠友雅集S - VPS部署管理${NC}"
    echo -e "${GREEN}========================================${NC}"
}

print_usage() {
    echo -e "${YELLOW}用法: sudo bash vps-deploy.sh [选项]${NC}"
    echo -e ""
    echo -e "选项:"
    echo -e "  ${BLUE}--init${NC}      首次部署，安装Docker并配置环境"
    echo -e "  ${BLUE}--update${NC}    更新代码并重启应用"
    echo -e "  ${BLUE}--restart${NC}   仅重启应用容器"
    echo -e "  ${BLUE}--logs${NC}      查看应用日志"
    echo -e "  ${BLUE}--status${NC}    查看服务状态"
    echo -e "  ${BLUE}--backup${NC}    备份数据库"
    echo -e "  ${BLUE}--stop${NC}      停止所有服务"
    echo -e "  ${BLUE}--help${NC}      显示帮助信息"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}请使用 sudo 运行此脚本${NC}"
        exit 1
    fi
}

# 首次部署
init_deploy() {
    print_header
    echo -e "${YELLOW}开始首次部署...${NC}"
    
    # 检查Docker
    echo -e "\n${BLUE}[1/6] 检查Docker环境...${NC}"
    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}Docker未安装，开始安装...${NC}"
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
        echo -e "${GREEN}Docker安装完成${NC}"
    else
        echo -e "${GREEN}Docker已安装${NC}"
    fi
    
    # 检查Docker Compose
    if ! docker compose version &> /dev/null; then
        echo -e "${YELLOW}安装Docker Compose插件...${NC}"
        apt-get update
        apt-get install -y docker-compose-plugin
    fi
    
    # 创建目录
    echo -e "\n${BLUE}[2/6] 创建应用目录...${NC}"
    mkdir -p "$APP_DIR"
    mkdir -p /var/log/nginx
    
    # 检查代码
    echo -e "\n${BLUE}[3/6] 检查项目代码...${NC}"
    if [ ! -f "$APP_DIR/app.py" ]; then
        echo -e "${RED}错误: 项目代码未找到${NC}"
        echo -e "${YELLOW}请先使用sync-to-vps.sh同步代码，或手动上传${NC}"
        exit 1
    fi
    
    # 检查环境配置
    echo -e "\n${BLUE}[4/6] 检查环境配置...${NC}"
    if [ ! -f "$APP_DIR/.env.prod" ]; then
        echo -e "${YELLOW}未找到.env.prod，从模板创建...${NC}"
        if [ -f "$APP_DIR/deploy/.env.prod.template" ]; then
            cp "$APP_DIR/deploy/.env.prod.template" "$APP_DIR/.env.prod"
            chmod 600 "$APP_DIR/.env.prod"
            echo -e "${RED}重要: 请编辑 $APP_DIR/.env.prod 填入实际配置${NC}"
            echo -e "${YELLOW}nano $APP_DIR/.env.prod${NC}"
            exit 1
        else
            echo -e "${RED}错误: 未找到环境变量模板${NC}"
            exit 1
        fi
    fi
    
    # 配置Nginx
    echo -e "\n${BLUE}[5/6] 配置Nginx反向代理...${NC}"
    if [ -f "$APP_DIR/$NGINX_CONF" ]; then
        cp "$APP_DIR/$NGINX_CONF" /etc/nginx/conf.d/secondhand_8543.conf
        
        # 测试Nginx配置
        if nginx -t; then
            systemctl reload nginx
            echo -e "${GREEN}Nginx配置已更新${NC}"
        else
            echo -e "${RED}Nginx配置错误，请检查${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}Nginx配置文件未找到，跳过...${NC}"
    fi
    
    # 启动服务
    echo -e "\n${BLUE}[6/6] 启动Docker服务...${NC}"
    cd "$APP_DIR"
    docker compose -f "$COMPOSE_FILE" up -d --build
    
    # 等待服务启动
    echo -e "\n${YELLOW}等待服务启动 (30秒)...${NC}"
    sleep 30
    
    # 检查状态
    check_status
    
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}  首次部署完成!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "\n${BLUE}服务地址:${NC}"
    echo -e "  HTTPS: https://happepls.pics:8543"
    echo -e "  健康检查: https://happepls.pics:8543/health"
    echo -e "\n${YELLOW}小程序配置:${NC}"
    echo -e "  在微信小程序后台添加服务器域名:"
    echo -e "  request合法域名: https://happepls.pics:8543"
}

# 更新代码
update_deploy() {
    print_header
    echo -e "${YELLOW}更新应用...${NC}"
    
    cd "$APP_DIR"
    
    # 如果是Git仓库，拉取最新代码
    if [ -d ".git" ]; then
        echo -e "\n${BLUE}[1/3] 拉取最新代码...${NC}"
        git fetch origin main
        git reset --hard origin/main
    else
        echo -e "\n${BLUE}[1/3] 跳过Git拉取 (非Git仓库)${NC}"
        echo -e "${YELLOW}请使用sync-to-vps.sh手动同步代码${NC}"
    fi
    
    # 重建镜像
    echo -e "\n${BLUE}[2/3] 重建应用镜像...${NC}"
    docker compose -f "$COMPOSE_FILE" build app --no-cache
    
    # 重启应用
    echo -e "\n${BLUE}[3/3] 重启应用...${NC}"
    docker compose -f "$COMPOSE_FILE" up -d app
    
    sleep 10
    check_status
    
    echo -e "\n${GREEN}更新完成!${NC}"
}

# 重启应用
restart_app() {
    print_header
    echo -e "${YELLOW}重启应用...${NC}"
    
    cd "$APP_DIR"
    docker compose -f "$COMPOSE_FILE" restart app
    
    sleep 10
    check_status
    
    echo -e "\n${GREEN}重启完成!${NC}"
}

# 查看日志
view_logs() {
    cd "$APP_DIR"
    docker compose -f "$COMPOSE_FILE" logs -f --tail=100 app
}

# 检查状态
check_status() {
    print_header
    echo -e "${BLUE}服务状态:${NC}\n"
    
    cd "$APP_DIR"
    docker compose -f "$COMPOSE_FILE" ps
    
    echo -e "\n${BLUE}健康检查:${NC}"
    if curl -s http://127.0.0.1:8100/health | grep -q "ok"; then
        echo -e "  应用 (8100): ${GREEN}✅ 正常${NC}"
    else
        echo -e "  应用 (8100): ${RED}❌ 异常${NC}"
    fi
    
    # 检查HTTPS
    if curl -sk https://127.0.0.1:8543/health 2>/dev/null | grep -q "ok"; then
        echo -e "  HTTPS (8543): ${GREEN}✅ 正常${NC}"
    else
        echo -e "  HTTPS (8543): ${YELLOW}⚠️ 未配置或异常${NC}"
    fi
}

# 备份数据库
backup_database() {
    print_header
    echo -e "${YELLOW}备份PostgreSQL数据库...${NC}"
    
    BACKUP_DIR="/var/backups/secondhand"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/postgres_backup_${TIMESTAMP}.sql"
    
    mkdir -p "$BACKUP_DIR"
    
    cd "$APP_DIR"
    docker compose -f "$COMPOSE_FILE" exec -T postgres \
        pg_dump -U secondhand_user secondhand_db > "$BACKUP_FILE"
    
    gzip "$BACKUP_FILE"
    
    echo -e "${GREEN}备份完成: ${BACKUP_FILE}.gz${NC}"
    
    # 清理30天前的备份
    find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
    echo -e "${BLUE}已清理30天前的旧备份${NC}"
}

# 停止服务
stop_services() {
    print_header
    echo -e "${YELLOW}停止所有服务...${NC}"
    
    cd "$APP_DIR"
    docker compose -f "$COMPOSE_FILE" down
    
    echo -e "${GREEN}服务已停止${NC}"
}

# 主程序
case "$1" in
    --init)
        check_root
        init_deploy
        ;;
    --update)
        check_root
        update_deploy
        ;;
    --restart)
        check_root
        restart_app
        ;;
    --logs)
        view_logs
        ;;
    --status)
        check_status
        ;;
    --backup)
        check_root
        backup_database
        ;;
    --stop)
        check_root
        stop_services
        ;;
    --help|*)
        print_usage
        ;;
esac
