# VPS完整部署指南 - Replit → RackNerd VPS

## 🎯 部署概览

本指南将帮助您完成以下操作：
1. 在RackNerd VPS上安装Containerd + Docker Compose
2. 迁移数据库（PostgreSQL + MongoDB）
3. 配置应用环境变量和自动更新流程
4. 设置GitHub Actions自动部署（可选）

**预计耗时**: 30-45分钟

---

## 📋 前置要求

### VPS环境要求
- **操作系统**: Ubuntu 20.04+ 或 Debian 11+
- **最低配置**: 2核4GB内存200GB磁盘（推荐4核8GB）
- **网络**: 公网IP地址
- **SSH访问**: 已配置SSH密钥或密码

### 开发环境要求
- **本地环境**: Ubuntu/Debian/macOS/WSL
- **工具**: curl, wget, git, ssh, pg_dump, mongodump
- **权限**: 能连接到Replit和VPS的SSH

---

## ⚡ 快速开始（5分钟）

### 1️⃣ 准备VPS

```bash
# 连接到VPS
ssh root@your-vps-ip

# 检查系统
lsb_release -a
uname -a
df -h

# 更新系统
apt-get update && apt-get upgrade -y
```

### 2️⃣ 执行一键部署脚本

```bash
# 下载部署脚本
git clone https://github.com/yourusername/secondhand-platform.git /tmp/platform
cd /tmp/platform

# 执行部署脚本（需要root权限）
sudo bash deploy/vps-install.sh

# 脚本会自动：
# ✅ 安装Containerd和Docker Compose
# ✅ 创建应用目录和数据目录
# ✅ 配置Nginx反向代理
# ✅ 拉取应用代码
# ✅ 创建环境文件模板
```

### 3️⃣ 迁移数据库

```bash
# 在Replit开发环境执行以下命令
# 首先导出Replit的数据库连接字符串

# 检查Replit数据库URL
echo $DATABASE_URL
echo $MONGODB_URI

# 导出环境变量（在Replit shell中）
export REPLIT_DATABASE_URL='postgresql://user:pass@host:port/db'
export REPLIT_MONGODB_URI='mongodb://user:pass@host:port/db'
export VPS_DATABASE_URL='postgresql://user:pass@your-vps-ip:5432/db'
export VPS_MONGODB_URI='mongodb://user:pass@your-vps-ip:27017/db'

# 执行迁移脚本
bash deploy/migrate-db.sh
```

### 4️⃣ 配置环境变量

```bash
# 在VPS上编辑环境文件
sudo nano /opt/secondhand-platform/.env.prod

# 需要配置的关键变量：
# DATABASE_URL              - PostgreSQL连接字符串
# MONGODB_URI               - MongoDB连接字符串
# SECRET_KEY                - 应用密钥（随机字符串）
# SESSION_SECRET            - 会话密钥（随机字符串）
# WX_MINIPROGRAM_APP_ID     - 微信小程序AppID
# WX_MINIPROGRAM_APP_SECRET - 微信小程序AppSecret
# WECHAT_APP_ID             - 微信登录AppID
# WECHAT_APP_SECRET         - 微信登录AppSecret
# ALIYUN_ACCESS_KEY_ID      - 阿里云AccessKey
# ALIYUN_ACCESS_KEY_SECRET  - 阿里云Secret

# 保存并退出（Ctrl+X → Y → Enter）
```

### 5️⃣ 启动应用

```bash
# 进入应用目录
cd /opt/secondhand-platform

# 检查环境文件
cat .env.prod | head -20

# 启动服务
sudo docker-compose -f docker-compose-prod.yml up -d

# 等待服务启动（约30秒）
sleep 30

# 检查服务状态
sudo docker-compose -f docker-compose-prod.yml ps

# 查看日志
sudo docker-compose -f docker-compose-prod.yml logs -f app
```

### 6️⃣ 验证部署

```bash
# 检查应用健康状态
curl http://localhost:8000/health
# 预期响应: {"status":"ok"}

# 检查数据库连接
sudo docker-compose -f docker-compose-prod.yml exec postgres \
  pg_isready -U secondhand_user

# 检查MongoDB连接
sudo docker-compose -f docker-compose-prod.yml exec mongo \
  mongosh --eval 'db.adminCommand("ping")'

# 检查Nginx
sudo systemctl status nginx
curl -I http://localhost
```

---

## 🔧 详细配置步骤

### 步骤1: VPS初始化（自动化）

```bash
# vps-install.sh 会自动执行以下操作：

1. 系统更新
   - apt-get update && apt-get upgrade -y

2. 安装依赖
   - gcc, build-essential, curl, wget, git

3. 安装Containerd
   - 添加Docker官方仓库
   - 安装containerd.io
   - 配置systemd cgroup驱动
   - 启用自启动

4. 安装Docker Compose
   - 下载最新版本
   - 配置执行权限

5. 创建应用目录
   - /opt/secondhand-platform (应用代码)
   - /var/lib/secondhand-platform (数据目录)

6. 拉取代码
   - git clone或git pull
   - 检查分支和标签

7. 配置Nginx
   - 创建反向代理配置
   - 启用站点
   - 测试配置
   - 启动Nginx
```

### 步骤2: 数据库迁移

```bash
# migrate-db.sh 执行以下操作：

1. 导出Replit数据
   - PostgreSQL: pg_dump → postgres_backup_TIMESTAMP.sql
   - MongoDB: mongodump → mongo_backup_TIMESTAMP/

2. 备份到本地
   - 位置: ./db_backups/

3. 导入到VPS
   - 清空目标数据库
   - 导入PostgreSQL数据
   - 导入MongoDB数据

4. 验证迁移
   - 检查表数量
   - 验证数据完整性

5. 保留备份
   - db_backups/postgres_backup_TIMESTAMP.sql
   - db_backups/mongo_backup_TIMESTAMP/
```

### 步骤3: 环境隔离

```
Replit开发环境:
├── app.py (直接运行)
├── 使用Replit PostgreSQL
├── 使用Replit MongoDB
└── 配置: config.ini + 系统环境变量

↓ 推送到GitHub ↓

VPS生产环境:
├── docker-compose-prod.yml
├── 使用本地PostgreSQL容器
├── 使用本地MongoDB容器
├── 配置: .env.prod
└── 自动化更新脚本
```

### 步骤4: 自动化更新

```bash
# 1. 配置GitHub Actions（可选）
# 编辑 .github/workflows/deploy.yml
# 添加VPS SSH密钥到GitHub Secrets

# 2. 或者手动更新
cd /opt/secondhand-platform
git pull origin main
sudo docker-compose -f docker-compose-prod.yml build
sudo docker-compose -f docker-compose-prod.yml up -d

# 3. 或者使用自动化脚本
sudo bash deploy/auto-update.sh update
```

---

## 📊 监控和维护

### 查看日志

```bash
# 应用日志
sudo docker-compose -f docker-compose-prod.yml logs -f app

# 数据库日志
sudo docker-compose -f docker-compose-prod.yml logs postgres
sudo docker-compose -f docker-compose-prod.yml logs mongo

# Nginx日志
sudo tail -f /var/log/nginx/app_access.log
sudo tail -f /var/log/nginx/app_error.log

# 系统日志
sudo journalctl -u nginx -f
sudo journalctl -u docker -f
```

### 性能监控

```bash
# 容器资源使用
docker stats

# 磁盘空间
df -h

# 内存使用
free -h

# CPU使用
top

# 网络流量
nethogs
```

### 自动备份

```bash
# 备份数据库
sudo bash deploy/auto-update.sh backup

# 设置定时备份（每天凌晨2点）
# 编辑 crontab
sudo crontab -e

# 添加以下行
0 2 * * * /opt/secondhand-platform/deploy/auto-update.sh backup

# 查看备份
ls -lh /var/backups/secondhand-platform/
```

---

## 🔒 安全配置

### SSL证书配置（HTTPS）

```bash
# 安装Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 申请证书
sudo certbot certonly --nginx -d okashii.top -d www.okashii.top

# 更新Nginx配置
sudo nano /etc/nginx/sites-available/secondhand-platform

# 添加以下内容（在server块中）
listen 443 ssl http2;
listen [::]:443 ssl http2;

ssl_certificate /etc/letsencrypt/live/okashii.top/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/okashii.top/privkey.pem;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;

# HTTP重定向到HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name okashii.top www.okashii.top;
    return 301 https://$server_name$request_uri;
}

# 测试并重启
sudo nginx -t
sudo systemctl restart nginx

# 自动续期
sudo certbot renew --dry-run
```

### 防火墙配置

```bash
# 启用UFW防火墙
sudo ufw enable

# 允许SSH
sudo ufw allow 22/tcp

# 允许HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 检查规则
sudo ufw status verbose

# 限制PostgreSQL访问（仅本地）
sudo ufw allow from 127.0.0.1 to 127.0.0.1 port 5432
```

### 密钥管理

```bash
# 生成强密钥
openssl rand -base64 32  # 用于SECRET_KEY
openssl rand -base64 32  # 用于SESSION_SECRET

# 安全存储密钥
# 不要提交到Git或暴露在日志中
# 使用.env.prod文件，设置权限600
sudo chmod 600 /opt/secondhand-platform/.env.prod

# 定期轮换密钥
# 更新.env.prod中的SECRET_KEY和SESSION_SECRET
# 重启应用以应用新密钥
```

---

## 🐛 故障排查

### 问题1: 应用无法启动

```bash
# 检查日志
sudo docker-compose -f docker-compose-prod.yml logs app

# 常见原因：
# 1. 数据库连接失败
#    - 检查DATABASE_URL是否正确
#    - 检查数据库是否运行: docker-compose ps

# 2. 端口已被占用
#    - 检查: sudo lsof -i :8000

# 3. 依赖安装失败
#    - 重建镜像: docker-compose build --no-cache

# 解决方案
sudo docker-compose -f docker-compose-prod.yml down
sudo docker-compose -f docker-compose-prod.yml up -d
```

### 问题2: 数据库迁移失败

```bash
# 检查源数据库
psql $REPLIT_DATABASE_URL -l

# 检查目标数据库
sudo docker-compose -f docker-compose-prod.yml exec postgres \
  psql -U secondhand_user -d secondhand_db -l

# 重新迁移
# 1. 清空VPS数据库
sudo docker-compose -f docker-compose-prod.yml exec postgres \
  dropdb -U secondhand_user secondhand_db

# 2. 重新创建数据库
sudo docker-compose -f docker-compose-prod.yml exec postgres \
  createdb -U secondhand_user secondhand_db

# 3. 重新导入
bash deploy/migrate-db.sh
```

### 问题3: Nginx返回502错误

```bash
# 检查Nginx日志
sudo tail -f /var/log/nginx/app_error.log

# 常见原因：
# 1. 应用容器未运行
sudo docker-compose -f docker-compose-prod.yml ps

# 2. 应用内部错误
sudo docker-compose -f docker-compose-prod.yml logs app

# 3. Nginx配置错误
sudo nginx -t

# 解决方案
sudo docker-compose -f docker-compose-prod.yml restart app
sudo systemctl restart nginx
```

### 问题4: WebSocket连接失败

```bash
# 检查WebSocket路由
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://localhost:8000/ws/chat_room

# 检查Nginx WebSocket配置
grep -A 10 "location /ws/" /etc/nginx/sites-available/secondhand-platform

# 确保以下配置存在：
# proxy_http_version 1.1;
# proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";

# 重启Nginx
sudo systemctl restart nginx
```

---

## 📚 常用命令速查表

```bash
# 服务管理
sudo docker-compose -f docker-compose-prod.yml up -d      # 启动
sudo docker-compose -f docker-compose-prod.yml down        # 停止
sudo docker-compose -f docker-compose-prod.yml restart     # 重启
sudo docker-compose -f docker-compose-prod.yml ps          # 查看状态

# 日志查看
sudo docker-compose -f docker-compose-prod.yml logs -f     # 实时日志
sudo docker-compose -f docker-compose-prod.yml logs app    # 应用日志

# 数据库备份
sudo bash deploy/auto-update.sh backup

# 应用更新
sudo bash deploy/auto-update.sh update

# 系统更新
sudo apt-get update && sudo apt-get upgrade -y
```

---

## ✅ 部署检查清单

- [ ] VPS SSH访问正常
- [ ] 执行了vps-install.sh脚本
- [ ] 数据库成功迁移
- [ ] .env.prod配置完整
- [ ] 应用启动正常（docker ps显示所有容器）
- [ ] 健康检查通过：curl http://localhost:8000/health
- [ ] Nginx反向代理正常工作
- [ ] WebSocket连接测试通过
- [ ] 数据库备份完成
- [ ] 防火墙规则配置正确
- [ ] 配置了自动更新脚本
- [ ] GitHub Actions（如使用）配置完成

---

## 📞 获取帮助

**遇到问题？**

1. 查看日志: `sudo docker-compose -f docker-compose-prod.yml logs -f`
2. 检查连接: `curl http://localhost:8000/health`
3. 查看本指南的"故障排查"部分
4. 联系VPS提供商技术支持

---

**部署完成！🎉**

您的应用现已运行在VPS上。所有小程序流量现在由VPS提供服务，Replit用于开发环境。

下一步：配置自动化更新流程（GitHub Actions）以实现推送即部署。
