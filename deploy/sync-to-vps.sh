#!/bin/bash

# ==========================================
# Replit → VPS 代码同步脚本
# ==========================================
# 功能: 将开发环境代码同步到VPS生产环境
# 用法: bash sync-to-vps.sh [--restart]
# ==========================================

set -e

# 配置
VPS_HOST="happepls.pics"
VPS_USER="root"
VPS_APP_DIR="/opt/secondhand-platform"
SSH_PORT="4222"  # RackNerd VPS使用特殊SSH端口
SSH_KEY=""  # 可选: 指定SSH密钥路径，如 ~/.ssh/id_rsa

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 解析参数
RESTART_APP=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --restart)
            RESTART_APP=true
            shift
            ;;
        --host)
            VPS_HOST="$2"
            shift 2
            ;;
        --port)
            SSH_PORT="$2"
            shift 2
            ;;
        --key)
            SSH_KEY="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            exit 1
            ;;
    esac
done

# SSH选项 (包含端口和密钥)
SSH_OPTS="-p $SSH_PORT"
if [ -n "$SSH_KEY" ]; then
    SSH_OPTS="$SSH_OPTS -i $SSH_KEY"
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Replit → VPS 代码同步${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${BLUE}目标服务器: ${VPS_USER}@${VPS_HOST}${NC}"
echo -e "${BLUE}目标目录: ${VPS_APP_DIR}${NC}"

# 要排除的文件/目录
# 注意: 不排除 mystatics/images，因为VPS使用Docker Volume持久化图片
# 首次部署时需要手动上传已有图片到VPS
EXCLUDE_LIST=(
    ".git"
    ".replit"
    "replit.nix"
    ".env"
    ".env.prod"
    "__pycache__"
    "*.pyc"
    ".pytest_cache"
    "node_modules"
    "miniprogram/node_modules"
    "logs/*.log"
    "*.sql"
    "backup_*.sql"
    ".upm"
    ".cache"
    "venv"
    ".pythonlibs"
)

# 构建rsync排除参数
EXCLUDE_ARGS=""
for item in "${EXCLUDE_LIST[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude=$item"
done

echo -e "\n${YELLOW}[1/4] 检查SSH连接...${NC}"
if ! ssh $SSH_OPTS -o ConnectTimeout=10 -o BatchMode=yes ${VPS_USER}@${VPS_HOST} "echo 'SSH连接成功'" 2>/dev/null; then
    echo -e "${RED}SSH连接失败，请检查:${NC}"
    echo -e "  1. VPS是否在线"
    echo -e "  2. SSH密钥是否已配置"
    echo -e "  3. 防火墙是否允许SSH (端口22)"
    echo -e "\n${YELLOW}提示: 首次连接需要配置SSH密钥${NC}"
    echo -e "  ssh-keygen -t ed25519 -C 'replit-deploy'"
    echo -e "  ssh-copy-id ${VPS_USER}@${VPS_HOST}"
    exit 1
fi
echo -e "${GREEN}SSH连接正常${NC}"

echo -e "\n${YELLOW}[2/4] 同步代码文件...${NC}"

# 使用rsync同步
rsync -avz --progress \
    $EXCLUDE_ARGS \
    -e "ssh $SSH_OPTS" \
    ./ ${VPS_USER}@${VPS_HOST}:${VPS_APP_DIR}/

echo -e "${GREEN}代码同步完成${NC}"

echo -e "\n${YELLOW}[3/4] 同步部署配置...${NC}"

# 确保deploy目录存在并同步
ssh $SSH_OPTS ${VPS_USER}@${VPS_HOST} "mkdir -p ${VPS_APP_DIR}/deploy"
rsync -avz --progress \
    -e "ssh $SSH_OPTS" \
    ./deploy/ ${VPS_USER}@${VPS_HOST}:${VPS_APP_DIR}/deploy/

echo -e "${GREEN}配置同步完成${NC}"

# 可选: 重启应用
if [ "$RESTART_APP" = true ]; then
    echo -e "\n${YELLOW}[4/4] 重启应用容器...${NC}"
    
    ssh $SSH_OPTS ${VPS_USER}@${VPS_HOST} << 'REMOTE_SCRIPT'
        cd /opt/secondhand-platform
        
        echo "重建应用镜像..."
        docker compose -f deploy/docker-compose-vps.yml build app --no-cache
        
        echo "重启应用容器..."
        docker compose -f deploy/docker-compose-vps.yml up -d app
        
        echo "等待应用启动..."
        sleep 10
        
        echo "检查应用状态..."
        if curl -s http://127.0.0.1:8100/health | grep -q "ok"; then
            echo "✅ 应用启动成功"
        else
            echo "❌ 应用启动可能失败，请检查日志:"
            echo "docker compose -f deploy/docker-compose-vps.yml logs app"
        fi
REMOTE_SCRIPT

    echo -e "${GREEN}应用重启完成${NC}"
else
    echo -e "\n${YELLOW}[4/4] 跳过重启 (使用 --restart 参数启用)${NC}"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  同步完成!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}后续操作:${NC}"
if [ "$RESTART_APP" = false ]; then
    echo -e "1. SSH登录VPS: ssh ${VPS_USER}@${VPS_HOST}"
    echo -e "2. 进入目录: cd ${VPS_APP_DIR}"
    echo -e "3. 重建并重启: docker compose -f deploy/docker-compose-vps.yml up -d --build"
fi
echo -e "4. 查看日志: docker compose -f deploy/docker-compose-vps.yml logs -f app"
echo -e "5. 检查状态: curl https://${VPS_HOST}:8543/health"

echo -e "\n${BLUE}图片同步说明:${NC}"
echo -e "VPS使用Docker Volume持久化图片，首次部署如需同步已有图片:"
echo -e "  rsync -avz mystatics/images/ ${VPS_USER}@${VPS_HOST}:/var/lib/docker/volumes/secondhand_app_uploads/_data/"
