#!/bin/bash

# 闲鱼二手交易平台部署脚本
# 作者: MiniMax Agent
# 日期: 2025-08-04

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "请使用root用户运行此脚本"
        exit 1
    fi
}

# 检查系统类型
check_system() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        print_info "检测到系统: $OS"
    else
        print_error "无法识别系统类型"
        exit 1
    fi
}

# 安装Docker和Docker Compose
install_docker() {
    print_info "安装Docker和Docker Compose..."
    
    # 更新包管理器
    apt-get update
    
    # 安装依赖
    apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # 添加Docker官方GPG密钥
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # 添加Docker仓库
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # 安装Docker
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io
    
    # 安装Docker Compose
    curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    # 启动Docker服务
    systemctl enable docker
    systemctl start docker
    
    print_success "Docker和Docker Compose安装完成"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_warning "Docker未安装，开始安装..."
        install_docker
    else
        print_success "Docker已安装"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_warning "Docker Compose未安装，开始安装..."
        install_docker
    else
        print_success "Docker Compose已安装"
    fi
}

# 配置防火墙
configure_firewall() {
    print_info "配置防火墙..."
    
    # 安装ufw
    apt-get install -y ufw
    
    # 配置基本规则
    ufw --force enable
    ufw default deny incoming
    ufw default allow outgoing
    
    # 允许SSH
    ufw allow ssh
    
    # 允许HTTP和HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # 允许应用端口
    ufw allow 8000/tcp
    
    print_success "防火墙配置完成"
}

# 创建项目目录
create_directories() {
    print_info "创建项目目录..."
    
    PROJECT_DIR="/opt/xianyu"
    
    mkdir -p $PROJECT_DIR
    mkdir -p $PROJECT_DIR/logs
    mkdir -p $PROJECT_DIR/data/mysql
    mkdir -p $PROJECT_DIR/data/mongodb
    mkdir -p $PROJECT_DIR/data/redis
    mkdir -p $PROJECT_DIR/ssl
    
    print_success "项目目录创建完成: $PROJECT_DIR"
}

# 生成配置文件
generate_config() {
    print_info "生成配置文件..."
    
    # 生成随机密码
    MYSQL_PASSWORD=$(openssl rand -base64 32)
    MONGO_PASSWORD=$(openssl rand -base64 32)
    SECRET_KEY=$(openssl rand -base64 64)
    
    # 生成.env文件
    cat > $PROJECT_DIR/.env << EOF
# 数据库配置
MYSQL_ROOT_PASSWORD=$MYSQL_PASSWORD
MYSQL_PASSWORD=$MYSQL_PASSWORD
MONGO_PASSWORD=$MONGO_PASSWORD

# 应用配置
SECRET_KEY=$SECRET_KEY
DEBUG=false
DOMAIN=localhost

# 邮件配置（请修改为实际配置）
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EOF
    
    print_success "配置文件生成完成"
    print_warning "请编辑 $PROJECT_DIR/.env 文件，修改邮件等配置"
}

# 复制项目文件
copy_project_files() {
    print_info "复制项目文件..."
    
    # 假设脚本在项目根目录
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    cp -r $SCRIPT_DIR/* $PROJECT_DIR/
    
    # 设置权限
    chmod +x $PROJECT_DIR/start.sh
    chmod +x $PROJECT_DIR/deploy.sh
    
    print_success "项目文件复制完成"
}

# 启动服务
start_services() {
    print_info "启动服务..."
    
    cd $PROJECT_DIR
    
    # 构建并启动容器
    docker-compose up -d --build
    
    # 等待服务启动
    print_info "等待服务启动..."
    sleep 30
    
    # 检查服务状态
    docker-compose ps
    
    print_success "服务启动完成"
}

# 安装SSL证书（可选）
install_ssl() {
    print_info "是否安装SSL证书？(y/N)"
    read -r response
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_info "请将SSL证书文件放在 $PROJECT_DIR/ssl/ 目录下"
        print_info "证书文件名: certificate.crt"
        print_info "私钥文件名: private.key"
        print_warning "配置SSL后需要重启Nginx容器: docker-compose restart nginx"
    fi
}

# 显示部署信息
show_deployment_info() {
    print_success "部署完成！"
    echo
    print_info "访问地址: http://$(hostname -I | awk '{print $1}')"
    print_info "项目目录: $PROJECT_DIR"
    print_info "日志目录: $PROJECT_DIR/logs"
    echo
    print_info "常用命令:"
    echo "  查看服务状态: cd $PROJECT_DIR && docker-compose ps"
    echo "  查看日志: cd $PROJECT_DIR && docker-compose logs -f"
    echo "  重启服务: cd $PROJECT_DIR && docker-compose restart"
    echo "  停止服务: cd $PROJECT_DIR && docker-compose down"
    echo "  更新代码: cd $PROJECT_DIR && git pull && docker-compose up -d --build"
    echo
    print_warning "请记住以下信息:"
    echo "  MySQL密码: $(grep MYSQL_PASSWORD $PROJECT_DIR/.env | cut -d'=' -f2)"
    echo "  MongoDB密码: $(grep MONGO_PASSWORD $PROJECT_DIR/.env | cut -d'=' -f2)"
}

# 主函数
main() {
    print_info "开始部署闲鱼二手交易平台..."
    
    check_root
    check_system
    check_docker
    configure_firewall
    create_directories
    generate_config
    copy_project_files
    start_services
    install_ssl
    show_deployment_info
    
    print_success "部署完成！"
}

# 运行主函数
main "$@"
