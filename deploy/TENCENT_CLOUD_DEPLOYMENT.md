# 腾讯云主机部署指南

## 📋 部署前准备

### 1. 购买腾讯云主机
- **推荐配置**：2核2GB内存 + 50GB系统盘（初期），可根据业务量升级
- **操作系统**：Ubuntu 20.04 LTS 或 22.04 LTS
- **带宽**：1-5Mbps（国内访问）
- **地域**：选择靠近用户地区（北京、上海、广州等）

### 2. 域名配置
- 购买域名并在腾讯云DNS解析中配置：
  ```
  A记录: your-domain.com -> 主机公网IP
  CNAME记录: www -> your-domain.com
  ```

### 3. SSL证书
- 腾讯云提供免费SSL证书（有效期1年）
- 购买地址：腾讯云SSL证书控制台
- 下载证书，放置在：`/etc/nginx/ssl/`

### 4. 准备环境变量
创建 `.env.prod.tencent` 文件：
```bash
# 服务配置
ENV=production
PORT=8000
BIND_ADDRESS=127.0.0.1

# 数据库配置
DATABASE_URL=postgresql://username:password@localhost:5432/secondhand_platform
MONGODB_URI=mongodb://localhost:27017/chat_db
REDIS_URL=redis://localhost:6379/0

# 微信相关
WECHAT_APP_ID=your_wechat_app_id
WECHAT_APP_SECRET=your_wechat_app_secret
WECHAT_REDIRECT_URI=https://your-domain.com/wechat/callback

WECHAT_MINIPROGRAM_APP_ID=your_miniprogram_app_id
WECHAT_MINIPROGRAM_APP_SECRET=your_miniprogram_app_secret

# 阿里云短信服务（可选）
ALIYUN_ACCESS_KEY_ID=your_aliyun_key
ALIYUN_ACCESS_KEY_SECRET=your_aliyun_secret
ALIYUN_SMS_SIGN_NAME=your_sms_sign
ALIYUN_SMS_TEMPLATE_CODE=your_template_code

# 邮件服务
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your_email@qq.com
SMTP_PASSWORD=your_smtp_password
SMTP_USE_SSL=True

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/var/log/secondhand-platform/app.log
```

## 🚀 部署步骤

### 第一步：连接主机并更新系统

```bash
# 1. SSH连接到腾讯云主机
ssh ubuntu@your-cloud-ip

# 2. 更新系统
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y curl wget git vim htop net-tools ca-certificates

# 3. 配置时区（改为北京时间）
sudo timedatectl set-timezone Asia/Shanghai
```

### 第二步：一键部署

```bash
# 1. 克隆项目代码
cd /home/ubuntu
git clone https://github.com/yourusername/secondhand-platform.git
cd secondhand-platform

# 2. 运行部署脚本（自动安装Docker、PostgreSQL、MongoDB等）
sudo bash deploy/vps-install.sh --provider tencent

# 3. 等待脚本完成（约5-10分钟）
```

### 第三步：配置证书并启动服务

```bash
# 1. 创建SSL证书目录
sudo mkdir -p /etc/nginx/ssl
cd /etc/nginx/ssl

# 2. 上传腾讯云下载的证书
# 将 your-domain.com.crt 和 your-domain.com.key 上传到此目录
# 或使用SCP命令：
# scp your-domain.com.crt ubuntu@your-cloud-ip:/tmp/
# scp your-domain.com.key ubuntu@your-cloud-ip:/tmp/
# sudo mv /tmp/your-domain.com.* /etc/nginx/ssl/

# 3. 修改nginx配置中的域名
sudo sed -i 's/your-domain.com/your-actual-domain.com/g' /etc/nginx/nginx.conf

# 4. 启动服务
cd /opt/secondhand-platform
sudo docker compose -f docker-compose-prod.yml up -d

# 5. 验证服务
sudo docker ps
curl http://localhost:8000/health
```

### 第四步：验证部署

```bash
# 1. 检查容器状态
docker ps

# 2. 查看应用日志
docker logs -f secondhand-app

# 3. 测试API
curl https://your-domain.com/health

# 4. 检查数据库连接
docker exec secondhand-db psql -U postgres -c "SELECT 1"
```

## 🔧 容器端口映射配置

### docker-compose-prod.yml 配置说明

```yaml
version: '3.8'

services:
  app:
    ports:
      - "127.0.0.1:8000:5000"  # 仅本地访问，通过Nginx反向代理
  
  nginx:
    ports:
      - "0.0.0.0:80:80"        # 公网HTTP访问
      - "0.0.0.0:443:443"      # 公网HTTPS访问
  
  postgres:
    ports:
      - "127.0.0.1:5432:5432"  # 仅本地访问
  
  mongodb:
    ports:
      - "127.0.0.1:27017:27017" # 仅本地访问
  
  redis:
    ports:
      - "127.0.0.1:6379:6379"  # 仅本地访问
```

## 🌐 Nginx配置重点

### 反向代理设置
- **上游服务器**：`http://127.0.0.1:8000`（容器内部Tornado应用）
- **SSL证书**：从腾讯云SSL证书管理下载的证书
- **Http/Https重定向**：自动将HTTP请求重定向到HTTPS

### 性能优化
```nginx
# 连接超时
proxy_connect_timeout 60s;
proxy_send_timeout 60s;
proxy_read_timeout 60s;

# 缓存静态资源
location /static/ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# WebSocket支持（用于实时聊天）
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

## 📊 监控和维护

### 常用命令

```bash
# 查看应用日志
docker logs -f secondhand-app --tail=100

# 查看Nginx日志
docker exec secondhand-nginx tail -f /var/log/nginx/access.log

# 查看数据库大小
docker exec secondhand-db du -sh /var/lib/postgresql/

# 备份数据库
docker exec secondhand-db pg_dump -U postgres secondhand_platform > backup.sql

# 查看内存和CPU使用
docker stats --no-stream

# 重启服务
docker compose -f docker-compose-prod.yml restart

# 停止服务
docker compose -f docker-compose-prod.yml down

# 更新代码并重启
cd /opt/secondhand-platform
git pull origin main
docker compose -f docker-compose-prod.yml up -d --force-recreate
```

### 防火墙配置

```bash
# 如果启用了腾讯云安全组，需要配置以下规则：
# 1. 入站规则
#    - 端口 80 (HTTP) 允许所有IP
#    - 端口 443 (HTTPS) 允许所有IP
#    - 端口 22 (SSH) 仅允许管理员IP

# 使用iptables（如无安全组）
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

## 🔐 安全建议

1. **定期更新**: 每月检查Docker镜像和系统更新
2. **密钥管理**: 使用腾讯云密钥管理服务(KMS)存储敏感信息
3. **备份策略**: 每日自动备份数据库到腾讯云COS
4. **监控告警**: 配置腾讯云监控，CPU/内存/磁盘超过阈值时告警
5. **日志审计**: 定期审查Nginx和应用日志

## ❓ 常见问题

### Q: 部署后无法访问HTTPS
**A**: 检查SSL证书是否正确上传到 `/etc/nginx/ssl/` 并且文件权限正确

### Q: WebSocket连接失败
**A**: 确保nginx配置中包含了 `Upgrade` 和 `Connection` 头部

### Q: 数据库连接超时
**A**: 检查docker容器网络 `docker network ls` 和 `docker network inspect`

### Q: 磁盘空间不足
**A**: 执行 `docker system prune` 清理未使用的镜像和容器

## 📈 性能调优

### 应用层优化
```bash
# 增加Tornado worker数量
# 修改docker-compose-prod.yml中的WORKERS变量
WORKERS=4  # 根据CPU核数调整
```

### 数据库优化
```bash
# PostgreSQL连接池
# 在应用中使用pgBouncer或SQLAlchemy连接池
SQLALCHEMY_POOL_SIZE=20
SQLALCHEMY_POOL_RECYCLE=3600
```

### Redis缓存
```bash
# 启用Redis缓存
REDIS_URL=redis://127.0.0.1:6379/0

# 缓存配置
CACHE_TTL=3600  # 1小时缓存
```
