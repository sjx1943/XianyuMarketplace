# 🚀 VPS部署快速启动 (5分钟)

## 🎯 目标

将后端从Replit迁移到VPS，使用轻量化Containerd容器化部署。

---

## ⚡ 5分钟快速部署

### 第1步: 在VPS上一键安装 (3分钟)

```bash
# 1. 以root身份连接到VPS
ssh root@your.vps.ip

# 2. 下载并执行部署脚本
curl -fsSL https://raw.githubusercontent.com/yourusername/secondhand-platform/main/deploy/vps-install.sh | sudo bash

# ✅ 脚本会自动：
# - 安装Containerd和Docker Compose
# - 创建应用目录 (/opt/secondhand-platform)
# - 配置Nginx反向代理
# - 拉取应用代码
# - 生成环境变量模板
```

### 第2步: 迁移数据库 (1分钟)

```bash
# 在Replit环境中执行
# 1. 获取连接字符串
echo "Replit PostgreSQL:" && echo $DATABASE_URL
echo "Replit MongoDB:" && echo $MONGODB_URI

# 2. 在VPS中获取新的连接字符串（需要先启动数据库容器）
cd /opt/secondhand-platform
sudo docker-compose -f docker-compose-prod.yml up -d postgres mongo
sleep 10

# 3. 执行迁移脚本
export REPLIT_DATABASE_URL='postgres://...'        # 从Replit复制
export REPLIT_MONGODB_URI='mongodb://...'          # 从Replit复制
export VPS_DATABASE_URL='postgresql://secondhand_user:change_me@localhost:5432/secondhand_db'
export VPS_MONGODB_URI='mongodb://mongo_admin:change_me@localhost:27017/chat_db?authSource=admin'

bash deploy/migrate-db.sh
```

### 第3步: 配置环境变量 (1分钟)

```bash
# 在VPS上编辑
sudo nano /opt/secondhand-platform/.env.prod

# 需要修改的关键变量：
DATABASE_URL=postgresql://secondhand_user:your_secure_password@postgres:5432/secondhand_db
MONGODB_URI=mongodb://mongo_admin:your_secure_password@mongo:27017/chat_db?authSource=admin
WX_MINIPROGRAM_APP_ID=wxXXXXXXXXXX
WX_MINIPROGRAM_APP_SECRET=xxxxxxxxxxxxxxxx
ALIYUN_ACCESS_KEY_ID=LTAI5t...
ALIYUN_ACCESS_KEY_SECRET=...

# Ctrl+X → Y → Enter 保存退出
```

### 第4步: 启动应用 (自动)

```bash
# 一切就绪，启动所有服务
cd /opt/secondhand-platform
sudo docker-compose -f docker-compose-prod.yml up -d

# 等待服务启动
sleep 30

# 验证
curl http://localhost:8000/health
# 预期响应: {"status":"ok"}
```

---

## 📚 详细文档

- **完整部署指南**: [VPS_DEPLOYMENT_GUIDE.md](./VPS_DEPLOYMENT_GUIDE.md)
- **脚本文档**: 见 `deploy/` 文件夹
  - `vps-install.sh` - VPS一键安装
  - `migrate-db.sh` - 数据库迁移
  - `auto-update.sh` - 自动化更新

---

## 🔄 后续更新流程

### 方案A: 自动化更新 (推荐)

```bash
# 1. 在本地开发并推送到GitHub
git add .
git commit -m "feature: xxx"
git push origin main

# 2. GitHub Actions自动部署到VPS
#    （需要在GitHub Secrets中配置VPS_SSH_KEY等）

# 3. VPS应用自动更新并重启
```

### 方案B: 手动更新

```bash
# 在VPS上执行
cd /opt/secondhand-platform
sudo bash deploy/auto-update.sh update

# 等效于：
# git pull
# docker-compose build
# docker-compose restart
```

---

## ✅ 验证清单

运行以下命令检查部署是否成功：

```bash
# ✅ 1. 容器运行正常
sudo docker-compose -f docker-compose-prod.yml ps
# 应该看到: postgres, mongo, app, nginx, redis 都是 Up

# ✅ 2. 应用健康检查
curl http://localhost:8000/health
# 响应: {"status":"ok"}

# ✅ 3. 数据库连接
sudo docker-compose -f docker-compose-prod.yml exec postgres \
  psql -U secondhand_user -d secondhand_db -c "SELECT COUNT(*) FROM users;"

# ✅ 4. MongoDB连接
sudo docker-compose -f docker-compose-prod.yml exec mongo \
  mongosh --eval 'db.chat_messages.countDocuments()'

# ✅ 5. Nginx反向代理
curl -I http://your.vps.ip/
# 应该看到: HTTP/1.1 200 或 301 (如果有重定向)

# ✅ 6. WebSocket连接
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://localhost:8000/ws/chat_room
```

---

## 📊 部署架构

```
┌─────────────────────────────────────┐
│    开发环境 (Replit)                 │
│  - 代码编辑和功能开发                │
│  - 使用Replit PostgreSQL/MongoDB    │
│  - python app.py --port=5000        │
└──────────────┬──────────────────────┘
               │ git push
               ↓
┌──────────────────────────────────────┐
│    版本控制 (GitHub)                  │
│  - 代码仓库                          │
│  - CI/CD流程 (GitHub Actions)       │
└──────────────┬──────────────────────┘
               │ auto deploy
               ↓
┌──────────────────────────────────────┐
│    生产环境 (VPS @ RackNerd)          │
│  ┌─────────────────────────────────┐ │
│  │  Docker Compose               │ │
│  │  ├─ PostgreSQL 15             │ │
│  │  ├─ MongoDB 7                 │ │
│  │  ├─ Tornado App               │ │
│  │  ├─ Redis 7                   │ │
│  │  └─ Nginx (反向代理)          │ │
│  └─────────────────────────────────┘ │
│  - 自动备份 (每天凌晨2点)            │
│  - 自动更新 (git pull + restart)     │
└──────────────────────────────────────┘
               ↑
               │ wss://okashii.top
               │
       ┌───────────────┐
       │  微信小程序   │
       │  + Web用户    │
       └───────────────┘
```

---

## 🛠️ 常见操作

```bash
# 查看日志
sudo docker-compose -f docker-compose-prod.yml logs -f app

# 重启应用
sudo docker-compose -f docker-compose-prod.yml restart app

# 停止所有服务
sudo docker-compose -f docker-compose-prod.yml down

# 启动所有服务
sudo docker-compose -f docker-compose-prod.yml up -d

# 备份数据库
sudo bash deploy/auto-update.sh backup

# 查看备份
ls -lh /var/backups/secondhand-platform/

# 更新应用
sudo bash deploy/auto-update.sh update
```

---

## ⚠️ 重要提醒

1. **环境变量安全**
   ```bash
   # 确保.env.prod文件权限为600（仅所有者可读）
   sudo chmod 600 /opt/secondhand-platform/.env.prod
   
   # 不要将.env.prod提交到GitHub
   # 已在.gitignore中配置
   ```

2. **备份重要**
   ```bash
   # 定期备份数据库
   0 2 * * * /opt/secondhand-platform/deploy/auto-update.sh backup
   ```

3. **监控日志**
   ```bash
   # 定期检查错误日志
   sudo tail -f /var/log/nginx/app_error.log
   ```

4. **HTTPS配置** (可选但推荐)
   ```bash
   sudo certbot certonly --nginx -d okashii.top
   # 然后编辑 /etc/nginx/sites-available/secondhand-platform
   ```

---

## 🆘 故障排查

| 问题 | 解决方案 |
|------|--------|
| 应用无法启动 | `docker-compose logs app` 查看错误 |
| 数据库连接失败 | 检查 DATABASE_URL 和 MONGODB_URI |
| Nginx 502错误 | `systemctl restart nginx` 或检查应用是否运行 |
| WebSocket断连 | 检查 proxy_upgrade_connection 配置 |
| 磁盘满了 | `df -h` 查看，删除旧备份或日志 |

详见: [VPS_DEPLOYMENT_GUIDE.md#-故障排查](./VPS_DEPLOYMENT_GUIDE.md#-故障排查)

---

**现在就开始吧！** 👉 [完整部署指南](./VPS_DEPLOYMENT_GUIDE.md)
