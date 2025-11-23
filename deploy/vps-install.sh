#!/bin/bash

# VPS 一键部署脚本（containerd + PostgreSQL + MongoDB + Tornado应用）
# 支持 Ubuntu 20.04+ 和 Debian 11+
# 用法: sudo bash vps-install.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}小区二手商品交易平台 VPS 部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查权限
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}此脚本必须以root用户运行${NC}"
   exit 1
fi

# 获取当前用户（用于文件权限）
CURRENT_USER=${SUDO_USER:-root}
APP_DIR="/opt/secondhand-platform"
DATA_DIR="/var/lib/secondhand-platform"

echo -e "\n${YELLOW}[1/7]${NC} 更新系统..."
apt-get update
apt-get upgrade -y

echo -e "\n${YELLOW}[2/7]${NC} 安装基础依赖..."
apt-get install -y \
    curl wget git vim htop net-tools \
    ca-certificates gnupg lsb-release \
    build-essential python3-dev python3-pip \
    libssl-dev libffi-dev

echo -e "\n${YELLOW}[3/7]${NC} 安装 Containerd..."
# 添加Docker官方GPG密钥
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 添加Docker仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y containerd.io

# 配置containerd
mkdir -p /etc/containerd
containerd config default | tee /etc/containerd/config.toml

# 启用systemd cgroup驱动
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

systemctl restart containerd
systemctl enable containerd

echo -e "\n${YELLOW}[4/7]${NC} 安装 Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
docker-compose --version

echo -e "\n${YELLOW}[5/7]${NC} 准备应用目录..."
mkdir -p "$APP_DIR"
mkdir -p "$DATA_DIR"/{postgres,mongo,uploads}
chown -R $CURRENT_USER:$CURRENT_USER "$APP_DIR"
chown -R $CURRENT_USER:$CURRENT_USER "$DATA_DIR"

echo -e "\n${YELLOW}[6/7]${NC} 拉取应用代码..."
cd "$APP_DIR"

# 检查是否已有git仓库
if [ ! -d ".git" ]; then
    echo "初始化git仓库（请配置git SSH密钥或输入GitHub凭证）"
    git init
    git remote add origin https://github.com/yourusername/secondhand-platform.git
fi

git fetch origin main
git checkout origin/main -- .

echo -e "\n${YELLOW}[7/7]${NC} 生成环境文件..."
if [ ! -f ".env.prod" ]; then
    cp deploy/.env.example .env.prod
    echo -e "${YELLOW}请编辑 $APP_DIR/.env.prod 文件，设置正确的值${NC}"
    echo -e "${YELLOW}特别是以下变量：${NC}"
    echo "  - DATABASE_URL (PostgreSQL)"
    echo "  - MONGODB_URI (MongoDB)"
    echo "  - WECHAT_APP_ID / WECHAT_APP_SECRET"
    echo "  - ALIYUN_ACCESS_KEY_ID / ALIYUN_ACCESS_KEY_SECRET"
fi

echo -e "\n${YELLOW}配置Nginx反向代理${NC}"
# 创建nginx配置
cat > /etc/nginx/sites-available/secondhand-platform << 'EOF'
upstream tornado_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name _;
    client_max_body_size 10M;

    location / {
        proxy_pass http://tornado_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    location /ws/ {
        proxy_pass http://tornado_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static/ {
        alias /opt/secondhand-platform/mystatics/;
        expires 30d;
    }
}
EOF

# 启用站点
ln -sf /etc/nginx/sites-available/secondhand-platform /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 测试nginx配置
nginx -t

# 启用和启动nginx
systemctl enable nginx
systemctl start nginx

echo -e "\n${YELLOW}启动应用服务...${NC}"
cd "$APP_DIR"
docker-compose -f docker-compose-prod.yml up -d

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ VPS部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${YELLOW}后续步骤:${NC}"
echo "1. 编辑环境文件: nano $APP_DIR/.env.prod"
echo "2. 启动应用: cd $APP_DIR && docker-compose -f docker-compose-prod.yml up -d"
echo "3. 检查状态: docker-compose -f docker-compose-prod.yml logs -f"
echo "4. 配置SSL证书: certbot certonly --nginx -d yourdomain.com"
echo "5. 启用HTTPS: 编辑/etc/nginx/sites-available/secondhand-platform"
echo -e "\n${YELLOW}重要文件位置:${NC}"
echo "  应用目录: $APP_DIR"
echo "  数据目录: $DATA_DIR"
echo "  环境文件: $APP_DIR/.env.prod"
echo "  Nginx配置: /etc/nginx/sites-available/secondhand-platform"
echo "  Containerd状态: systemctl status containerd"
echo -e "\n${YELLOW}常用命令:${NC}"
echo "  查看日志: docker-compose -f docker-compose-prod.yml logs -f"
echo "  重启服务: docker-compose -f docker-compose-prod.yml restart"
echo "  停止服务: docker-compose -f docker-compose-prod.yml down"
echo "  更新应用: cd $APP_DIR && git pull && docker-compose -f docker-compose-prod.yml up -d"
