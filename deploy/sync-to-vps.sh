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

# SSH选项 (包含端口、密钥和主机密钥验证)
SSH_OPTS="-p $SSH_PORT -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=~/.ssh/known_hosts"
if [ -n "$SSH_KEY" ]; then
    SSH_OPTS="$SSH_OPTS -i $SSH_KEY"
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Replit → VPS 代码同步${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${BLUE}目标服务器: ${VPS_USER}@${VPS_HOST}${NC}"
echo -e "${BLUE}目标目录: ${VPS_APP_DIR}${NC}"

# 使用已有的SSH密钥，如果不存在则从秘钥恢复
if [ ! -f ~/.ssh/id_ed25519 ] && [ -n "$DEPLOY_SSH_KEY" ]; then
    echo -e "\n${YELLOW}SSH密钥不存在，从秘钥环境变量恢复...${NC}"
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    
    # 方法1: 如果是Base64编码（不含BEGIN/END标记），则先解码
    if [[ "$DEPLOY_SSH_KEY" =~ ^[A-Za-z0-9+/]*={0,2}$ ]]; then
        echo "$DEPLOY_SSH_KEY" | base64 -d > ~/.ssh/id_ed25519
    # 方法2: 如果包含BEGIN/END标记，则提取Base64部分后解码
    elif [[ "$DEPLOY_SSH_KEY" =~ BEGIN\ OPENSSH\ PRIVATE\ KEY ]]; then
        base64_content=$(echo "$DEPLOY_SSH_KEY" | sed 's/-----BEGIN OPENSSH PRIVATE KEY----- //g' | sed 's/ -----END OPENSSH PRIVATE KEY-----//g' | tr -d ' ' | tr -d '\n')
        echo "$base64_content" | base64 -d > ~/.ssh/id_ed25519
    # 方法3: 直接使用（假设是PEM格式）
    else
        echo -e "$DEPLOY_SSH_KEY" > ~/.ssh/id_ed25519
    fi
    
    chmod 600 ~/.ssh/id_ed25519
    
    # 验证密钥格式
    if head -1 ~/.ssh/id_ed25519 | grep -q "BEGIN"; then
        echo -e "${GREEN}SSH密钥已恢复 (PEM格式)${NC}"
    elif head -1 ~/.ssh/id_ed25519 | grep -q "openssh-key-v1"; then
        echo -e "${GREEN}SSH密钥已恢复 (OpenSSH格式)${NC}"
    else
        echo -e "${RED}警告: 密钥格式可能不正确${NC}"
    fi
fi

# 设置SSH密钥路径
if [ -z "$SSH_KEY" ] && [ -f ~/.ssh/id_ed25519 ]; then
    SSH_KEY=~/.ssh/id_ed25519
fi

# 要排除的文件/目录
# 注意: 不排除 mystatics/images，因为VPS使用Docker Volume持久化图片
# 首次部署时需要手动上传已有图片到VPS
EXCLUDE_LIST=(
    ".git"
    ".replit"
    "replit.nix"
    "replit.md"
    ".env"
    ".env.prod"
    "__pycache__"
    "*.pyc"
    ".pytest_cache"
    "node_modules"
    "miniprogram/node_modules"
    "logs"
    "*.log"
    "*.sql"
    "backup_*.sql"
    ".upm"
    ".cache"
    "venv"
    ".pythonlibs"
    ".breakpoints"
    ".config"
    "attached_assets"
    "/tmp"
    "*.tmp"
    "*.bak"
    ".nix-*"
    "mystatics/images/avatars"
    "mystatics/images/products"
    "mystatics/images/thumbnails"
    "mystatics/images/medium"
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
    echo -e "  ssh-copy-id -p 4222 ${VPS_USER}@${VPS_HOST}"
    exit 1
fi
echo -e "${GREEN}SSH连接正常${NC}"

echo -e "\n${YELLOW}[2/4] 同步代码文件 (1:1 完全同步，删除远端多余文件)...${NC}"

# 使用rsync同步，添加 --delete 实现1:1完全同步
# --delete: 删除远端存在但本地不存在的文件
# --delete-excluded: 同时删除被排除规则匹配的远端文件
rsync -avz --progress --delete --delete-excluded \
    $EXCLUDE_ARGS \
    -e "ssh $SSH_OPTS" \
    ./ ${VPS_USER}@${VPS_HOST}:${VPS_APP_DIR}/

echo -e "${GREEN}代码同步完成 (远端多余文件已清理)${NC}"

echo -e "\n${YELLOW}[3/4] 同步部署配置...${NC}"

# 确保deploy目录存在并同步
ssh $SSH_OPTS ${VPS_USER}@${VPS_HOST} "mkdir -p ${VPS_APP_DIR}/deploy"
rsync -avz --progress --delete \
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
