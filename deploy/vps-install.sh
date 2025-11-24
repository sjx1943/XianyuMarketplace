#!/bin/bash

# VPS 一键部署脚本 (适配腾讯云/阿里云/AWS等云服务商)
# 用法: sudo bash vps-install.sh [--provider tencent|aliyun|aws|generic]
# 示例: sudo bash vps-install.sh --provider tencent

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

APP_DIR="/opt/secondhand-platform"
DATA_DIR="/var/lib/secondhand-platform"
CURRENT_USER=${SUDO_USER:-root}

# 解析命令行参数
PROVIDER="generic"
while [[ $# -gt 0 ]]; do
    case $1 in
        --provider)
            PROVIDER="$2"
            shift 2
            ;;
        *)
            echo "未知参数: $1"
            shift
            ;;
    esac
done

echo -e "${GREEN}=== 开始部署 ===${NC}"
echo -e "${BLUE}云服务商: $PROVIDER${NC}"
echo -e "${BLUE}应用目录: $APP_DIR${NC}"
echo -e "${BLUE}数据目录: $DATA_DIR${NC}"

# 1. 检查 Root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}请使用 sudo 运行此脚本${NC}"
   exit 1
fi

# 2. 根据云服务商配置镜像源
echo -e "\n${YELLOW}[1/7] 配置系统镜像源...${NC}"

case $PROVIDER in
    tencent)
        echo -e "${BLUE}使用腾讯云镜像源...${NC}"
        cat > /etc/apt/sources.list << EOF
deb http://mirrors.tencentyun.com/ubuntu $(lsb_release -cs) main restricted universe multiverse
deb http://mirrors.tencentyun.com/ubuntu $(lsb_release -cs)-updates main restricted universe multiverse
deb http://mirrors.tencentyun.com/ubuntu $(lsb_release -cs)-security main restricted universe multiverse
EOF
        ;;
    aliyun)
        echo -e "${BLUE}使用阿里云镜像源...${NC}"
        cat > /etc/apt/sources.list << EOF
deb http://mirrors.aliyun.com/ubuntu $(lsb_release -cs) main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu $(lsb_release -cs)-updates main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu $(lsb_release -cs)-security main restricted universe multiverse
EOF
        ;;
    aws)
        echo -e "${BLUE}使用默认AWS镜像源...${NC}"
        ;;
    *)
        echo -e "${BLUE}使用默认系统镜像源...${NC}"
        ;;
esac

echo -e "\n${YELLOW}[2/7] 更新系统基础软件...${NC}"
apt-get update && apt-get upgrade -y
apt-get install -y curl wget git vim htop net-tools ca-certificates gnupg lsb-release

# 3. 安装 Docker
echo -e "\n${YELLOW}[3/7] 安装 Docker Engine...${NC}"
if ! command -v docker &> /dev/null; then
    mkdir -p /etc/apt/keyrings
    
    # 根据云服务商选择Docker镜像源
    case $PROVIDER in
        tencent)
            echo -e "${BLUE}使用腾讯云 Docker 镜像源...${NC}"
            curl -fsSL https://mirrors.tencentyun.com/docker-ce/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.tencentyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            ;;
        aliyun)
            echo -e "${BLUE}使用阿里云 Docker 镜像源...${NC}"
            curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            ;;
        *)
            echo -e "${BLUE}使用官方 Docker 镜像源...${NC}"
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            ;;
    esac

    apt-get update
    # 安装完整的 Docker CE 和 Compose 插件
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    # 配置 Docker 镜像加速
    mkdir -p /etc/docker
    
    case $PROVIDER in
        tencent)
            echo -e "${BLUE}配置腾讯云 Docker 镜像加速...${NC}"
            cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://mirror.tencentyun.com"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m"
  },
  "storage-driver": "overlay2"
}
EOF
            ;;
        aliyun)
            echo -e "${BLUE}配置阿里云 Docker 镜像加速...${NC}"
            cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://registry.docker-cn.com",
    "https://docker.mirrors.aliyuncs.com"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m"
  },
  "storage-driver": "overlay2"
}
EOF
            ;;
        *)
            echo -e "${BLUE}配置通用 Docker 镜像加速...${NC}"
            cat > /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m"
  },
  "storage-driver": "overlay2"
}
EOF
            ;;
    esac
    systemctl enable docker
    systemctl restart docker
    echo -e "${GREEN}Docker 安装完成${NC}"
else
    echo "Docker 已安装，跳过..."
fi

# 4. 准备目录
echo -e "\n${YELLOW}[4/7] 创建数据目录...${NC}"
mkdir -p "$APP_DIR"
# 创建 Docker 挂载所需的目录，防止 Permission Denied
mkdir -p "$DATA_DIR/postgres" "$DATA_DIR/mongo" "$DATA_DIR/redis" "$DATA_DIR/uploads" "$APP_DIR/logs/nginx"
chmod -R 755 "$DATA_DIR"

# 5. 拉取代码
echo -e "\n${YELLOW}[5/7] 拉取项目代码...${NC}"
# 注意：如果是私有仓库，需要配置 SSH Key 或 Token。
# 建议：由于国内连 GitHub 慢，你可以先手动上传代码，或者使用 Gitee 镜像。
if [ ! -d "$APP_DIR/.git" ]; then
    echo -e "${YELLOW}目录为空，正在克隆... (如果 GitHub 很慢，请考虑使用 Gitee)${NC}"
    git clone https://github.com/yourusername/secondhand-platform.git "$APP_DIR"
else
    cd "$APP_DIR"
    echo "更新代码..."
    git pull origin main
fi

# 6. 环境配置
echo -e "\n${YELLOW}[6/7] 检查环境配置文件...${NC}"
cd "$APP_DIR"
if [ ! -f ".env.prod" ]; then
    if [ -f "deploy/.env.example" ]; then
        cp deploy/.env.example .env.prod
        echo -e "${GREEN}已生成 .env.prod，请稍后手动编辑填入敏感信息！${NC}"
    else
        echo -e "${RED}警告：未找到 .env.example 模板文件${NC}"
    fi
fi

# 7. Nginx配置
echo -e "\n${YELLOW}[7/7] 配置 Nginx...${NC}"
if [ ! -f "$APP_DIR/deploy/nginx-${PROVIDER}.conf" ]; then
    echo -e "${YELLOW}Nginx配置文件: nginx-${PROVIDER}.conf${NC}"
    cp $APP_DIR/deploy/nginx-tencent.conf $APP_DIR/nginx.conf
else
    cp $APP_DIR/deploy/nginx-${PROVIDER}.conf $APP_DIR/nginx.conf
fi

echo -e "\n${GREEN}=== 部署完成 ===${NC}"
echo -e "${BLUE}后续步骤:${NC}"
echo -e "1. 编辑环境变量文件: nano $APP_DIR/.env.prod"
echo -e "2. 配置SSL证书: sudo mkdir -p /etc/nginx/ssl && sudo cp your-cert.crt /etc/nginx/ssl/"
echo -e "3. 启动服务: cd $APP_DIR && docker compose -f docker-compose-prod.yml up -d"
echo -e "4. 验证服务: curl http://localhost:8000/health"
echo -e "\n${YELLOW}详见: $APP_DIR/deploy/TENCENT_CLOUD_DEPLOYMENT.md${NC}"