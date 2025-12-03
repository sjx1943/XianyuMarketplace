# 从Replit开发到VPS生产的完整推送流程

## 📋 总体流程

```
Replit (开发环境)
    ↓
    完成功能开发和测试
    ↓
GitHub (版本控制)
    ↓
    提交代码 + 创建版本标签
    ↓
GitHub Actions (自动测试)
    ↓
    测试通过
    ↓
VPS (生产环境)
    ↓
    自动部署和更新
    ↓
线上服务更新完成
    ↓
用户看到新功能
```

---

## 🎯 分步指导 (共6步)

### 第1步：在Replit上完成功能开发和测试 ✅

**位置**: Replit Web IDE

```
在Replit上：
1. 编写或修改代码
2. 使用workflow自动热重载测试
3. 确保所有功能正常运行
4. 在Web浏览器中测试所有页面
5. 在小程序模拟器中测试 (如有)
```

**检查清单**：
- [ ] 新功能按预期工作
- [ ] 没有JavaScript错误 (浏览器控制台)
- [ ] 没有Python错误 (Replit控制台)
- [ ] 数据库查询正常
- [ ] WebSocket连接正常 (聊天功能)

**示例**：
```bash
# 在Replit terminal中测试API
curl http://localhost:5000/health

# 查看最近的日志
# (Replit console自动显示)
```

---

### 第2步：提交代码到本地Git

**位置**: Replit terminal 或 本地开发机

```bash
# 进入项目目录
cd /home/runner/secondhand-platform

# 检查修改状态
git status

# 查看具体改动
git diff

# 添加所有改动
git add .

# 提交代码 (必须有清晰的提交信息)
git commit -m "feat: 添加功能X的说明

- 具体实现了什么
- 修复了哪个bug
- 更新了哪些API"

# 验证提交
git log --oneline -5
```

**提交信息规范** (重要！):

```
格式: <type>: <subject>

<body>

<footer>

示例:

feat: 添加用户订阅消息功能
  
- 实现订阅通知接口
- 添加消息模板配置
- 修复WebSocket连接断线问题

Closes #123
```

**提交类型说明**:
- `feat`: 新功能
- `fix`: 修复bug
- `refactor`: 代码重构
- `perf`: 性能优化
- `docs`: 文档更新
- `test`: 测试代码
- `chore`: 构建/依赖更新

---

### 第3步：推送代码到GitHub

**位置**: Replit terminal 或 本地开发机

```bash
# 查看远程仓库
git remote -v

# 推送到GitHub (main分支用于生产)
git push origin main

# 验证推送成功
git log --oneline origin/main -5
```

**推送时遇到冲突？**:
```bash
# 1. 拉取远程最新代码
git pull origin main

# 2. 解决冲突 (编辑有冲突的文件)
# (文件中会有 <<<<<<, ======, >>>>>> 标记)

# 3. 标记冲突已解决
git add .

# 4. 提交合并
git commit -m "merge: 解决冲突"

# 5. 再次推送
git push origin main
```

---

### 第4步：创建Release版本标签 (可选但推荐)

**位置**: GitHub网页

这一步帮助您追踪版本历史，便于回滚。

#### 方案A: 在GitHub网页操作

```
1. 打开GitHub仓库
   https://github.com/yourusername/secondhand-platform

2. 点击右侧 "Releases" 标签

3. 点击 "Create a new release"

4. 填写信息:
   Tag version:  v1.0.1
   Release title: 版本 1.0.1 - 订阅消息功能
   Description:
     ## ✨ 新功能
     - 订阅消息通知系统
     - WebSocket断线重连
     
     ## 🐛 修复
     - 修复聊天消息丢失问题
     - 优化图片上传性能
     
     ## 📝 其他
     - 更新文档
     - 代码重构
   
5. 点击 "Publish release"
```

#### 方案B: 命令行操作

```bash
# 创建版本标签
git tag -a v1.0.1 -m "版本 1.0.1: 添加订阅消息功能"

# 推送标签到GitHub
git push origin v1.0.1

# 验证
git tag -l
```

**版本号规范** (语义化版本):
```
v<major>.<minor>.<patch>

v1.0.0  - 主版本 (大功能更新)
v1.0.1  - 修订版 (bug修复)
v1.1.0  - 次版本 (新功能)
v2.0.0  - 主版本 (架构改变)
```

---

### 第5步：GitHub Actions自动测试和构建

**位置**: GitHub Actions 自动执行

创建release版本后，GitHub Actions 会自动执行 `.github/workflows/deploy.yml` 脚本。

#### 监控部署进度：

```
1. 打开GitHub仓库

2. 点击 "Actions" 标签

3. 看到最新的Workflow运行

4. 等待构建完成 (通常1-5分钟)

状态可能是:
✅ Passed   - 部署成功
❌ Failed   - 部署失败，检查日志
⏳ Running  - 部署中，继续等待
```

#### 查看失败原因：

```
1. 点击失败的Workflow
2. 点击 "test" 或 "deploy" 任务
3. 查看详细日志
4. 找到错误信息并修复

常见错误:
- 依赖安装失败 → 检查requirements.txt
- Python语法错误 → 检查代码
- 数据库连接失败 → 检查DATABASE_URL
```

---

### 第6步：VPS自动更新并验证

**位置**: VPS 自动执行

GitHub Actions 成功后，VPS会自动执行部署脚本。

#### VPS上的自动操作：

```bash
# 后台自动执行 (无需手动)：

1. Git拉取最新代码
   cd /opt/secondhand-platform
   git fetch origin main
   git reset --hard origin/main

2. 重建Docker镜像
   docker-compose build --no-cache app

3. 重启应用
   docker-compose restart app

4. 验证健康状态
   curl http://localhost:8000/health

5. 如果出错，自动回滚到前一个版本
```

#### 手动验证部署 (推荐)：

```bash
# SSH连接VPS
ssh root@your.vps.ip

# 检查应用日志
sudo docker-compose -f docker-compose-prod.yml logs -f app

# 确保看到 "Tornado application started"

# 测试API
curl http://localhost:8000/health
# 预期: {"status":"ok"}

# 检查容器状态
sudo docker-compose -f docker-compose-prod.yml ps
# 所有容器应该是 Up 状态

# 检查Web访问
curl -I http://localhost:8000/
# 应该看到 HTTP/1.1 200 或 301
```

---

## ⚠️ 如果部署失败怎么办？

### 问题诊断

```bash
# 1. 查看VPS上的应用日志
ssh root@your.vps.ip
sudo docker-compose -f docker-compose-prod.yml logs app

# 2. 查看GitHub Actions日志
# 打开 https://github.com/yourusername/secondhand-platform/actions

# 3. 常见错误和解决方案
```

### 常见错误

| 错误 | 原因 | 解决方案 |
|------|------|--------|
| `ModuleNotFoundError` | 缺少依赖 | 更新 requirements.txt，重新部署 |
| `DatabaseError` | 数据库迁移失败 | 检查SQL语句，手动修复数据库 |
| `ConnectionRefused` | 应用无法启动 | 查看日志，检查配置文件 |
| `Port already in use` | 端口被占用 | 重启Docker，杀死旧进程 |
| 用户上传图片丢失 | Docker Volume 配置问题 | 参见下方【图片持久化说明】 |

### ⚠️ 重要：图片持久化说明

用户上传的商品图片存储在 `/app/mystatics/images/` 目录中。为防止重新部署后图片丢失，请注意以下几点：

**1. 路径映射关系**

| URL 路径 | 实际存储位置 | Docker Volume |
|---------|-------------|---------------|
| `/static/images/xxx.png` | `mystatics/images/xxx.png` | `app_uploads` |

> `/static/images/` 是 Tornado 框架的 URL 前缀，实际文件存储在 `mystatics/images/` 目录

**2. 正确的 Volume 配置**

```yaml
# docker-compose-prod.yml 中的配置
volumes:
  - app_uploads:/app/mystatics/images  # ✅ 正确：使用 Named Volume
  - app_logs:/app/logs

# ❌ 错误：不要使用整体挂载覆盖
# volumes:
#   - ./:/app                          # 这会导致图片丢失！
#   - app_uploads:/app/mystatics/images
```

**3. 重新部署时保留图片**

```bash
# ✅ 正确：只重建容器，保留 volumes
docker-compose -f docker-compose-prod.yml up -d --build

# ❌ 错误：这会删除所有 volumes（包括图片）！
docker-compose -f docker-compose-prod.yml down -v
```

**4. 备份用户图片**

```bash
# 查看当前图片 volume
docker volume inspect secondhand_app_uploads

# 备份图片到主机
docker cp secondhand-app:/app/mystatics/images ./backup_images

# 从备份恢复图片
docker cp ./backup_images/. secondhand-app:/app/mystatics/images/
```

### 紧急回滚

如果新版本有严重问题，需要立即回滚到前一个版本：

```bash
# SSH连接VPS
ssh root@your.vps.ip

# 回滚到前一个提交
cd /opt/secondhand-platform
git reset --hard HEAD~1

# 重启应用
sudo docker-compose -f docker-compose-prod.yml build
sudo docker-compose -f docker-compose-prod.yml up -d

# 验证
curl http://localhost:8000/health
```

或者使用我们提供的备份恢复：

```bash
# 查看备份
ls -lh /var/backups/secondhand-platform/

# 恢复数据库备份
# (参考 deploy/auto-update.sh 的备份恢复部分)
```

---

## 📊 完整示例：从头到尾的一次发布

### 场景：发布新的聊天功能 (v1.2.0)

#### 第1步：在Replit开发 (1-2天)

```bash
# Replit中编辑文件...
# app.py - 添加新的WebSocket处理器
# controllers/chat_controller.py - 添加消息过滤功能
# miniprogram/pages/chat/room.js - 更新UI

# 在Replit中测试
# 打开小程序模拟器 → 测试聊天 → 验证消息过滤

# 确保所有功能正常
curl http://localhost:5000/health
```

#### 第2步：提交代码 (Replit或本地)

```bash
git status
# 输出: modified: app.py
#       modified: controllers/chat_controller.py
#       modified: miniprogram/pages/chat/room.js

git add .

git commit -m "feat: 添加聊天消息过滤和关键词屏蔽

- 实现关键词黑名单过滤
- 添加消息内容检查接口
- 优化WebSocket消息处理性能
- 更新小程序UI展示过滤提示

Closes #42"

git push origin main
```

#### 第3步：创建Release版本 (GitHub网页)

```
Releases → Create a new release

Tag version: v1.2.0
Release title: 版本 1.2.0 - 聊天消息过滤

Description:
## ✨ 新功能
- 关键词自动过滤
- 消息内容检查

## 📈 改进
- WebSocket性能优化
- UI用户体验改进

## 🔗 相关问题
Closes #42

点击 "Publish release"
```

#### 第4步：等待自动部署 (5-10分钟)

```
GitHub Actions 自动执行:
1. ✅ 代码检查通过
2. ✅ 单元测试通过
3. ✅ Docker镜像构建完成
4. ✅ VPS应用更新成功

监控: https://github.com/yourname/secondhand-platform/actions
```

#### 第5步：验证生产环境 (VPS)

```bash
ssh root@your.vps.ip

# 查看最新日志
sudo docker-compose -f docker-compose-prod.yml logs app | tail -20

# 测试新功能
curl http://localhost:8000/api/messages

# 检查版本
git describe --tags
# 输出: v1.2.0
```

#### 第6步：通知用户更新 (可选)

```
更新日志:
- ✨ 新增聊天消息过滤功能
- 🐛 修复WebSocket连接不稳定问题
- 📈 优化聊天性能

小程序用户会看到更新提示，自动下载新版本。
```

---

## 🔄 日常迭代流程 (快速参考)

```bash
# 1. 完成开发和测试 (在Replit)
# (编辑代码，测试功能)

# 2. 提交并推送
git add .
git commit -m "feat: 描述改动"
git push origin main

# 3. 创建版本 (GitHub)
git tag v1.2.1
git push origin v1.2.1

# 4. 等待自动部署 (GitHub Actions)
# (约5-10分钟)

# 5. 验证上线 (VPS)
ssh root@your.vps.ip
curl http://localhost:8000/health
```

---

## 📱 小程序如何更新？

小程序用户的更新是**自动**的：

1. **微信自动检查更新** (每次启动时)
2. **用户看到"有新版本，立即体验"提示** (可选)
3. **后台自动下载新版本** (约5-10MB)
4. **下次启动时使用新版本**

**什么触发小程序更新？**
- 新版本发布到微信公众平台
- 微信后台需要重新上传小程序代码

**如果您的VPS API更新，小程序如何知道？**
- 不需要！小程序每次都请求最新的API
- VPS API更新后立即对所有小程序生效

---

## ✅ 发布前检查清单

部署前，务必检查：

```
代码质量:
- [ ] 没有console.log调试语句 (JS)
- [ ] 没有print调试语句 (Python)
- [ ] 没有注释掉的大段代码
- [ ] 变量命名清晰，符合规范
- [ ] 错误处理完善

功能测试:
- [ ] 新功能在Replit正常工作
- [ ] 没有浏览器JS错误
- [ ] 没有服务器错误 (500)
- [ ] 小程序能正常通信
- [ ] WebSocket连接正常

数据库:
- [ ] 没有新的未迁移数据库变化
- [ ] 数据库查询有适当索引
- [ ] 没有N+1查询问题

安全性:
- [ ] 没有暴露敏感信息 (API密钥)
- [ ] 输入验证完善
- [ ] SQL注入防护完善
- [ ] 敏感信息在.env.prod中

性能:
- [ ] 页面加载时间 < 3秒
- [ ] API响应时间 < 500ms
- [ ] 没有内存泄漏
- [ ] 没有无限循环

配置:
- [ ] Replit和VPS使用相同的代码库
- [ ] .env.prod已配置所有必要变量
- [ ] 数据库连接字符串正确
- [ ] 日志级别适当
```

---

## 🆘 故障排查快速指南

| 问题 | 检查位置 | 修复方法 |
|------|---------|--------|
| 部署失败 | GitHub Actions日志 | 查看错误，修复代码，重新推送 |
| VPS应用崩溃 | `docker-compose logs app` | 查看错误日志，修复，重启 |
| 数据库连接失败 | .env.prod的DATABASE_URL | 确保连接字符串正确 |
| WebSocket断连 | 浏览器开发者工具 | 检查网络，重启应用 |
| 功能不更新 | 浏览器缓存 | Ctrl+Shift+R 强制刷新 |
| 小程序无法连接 | 小程序日志 | 检查API地址，防火墙规则 |

---

## 🎉 发布成功标志

✅ GitHub Actions显示"All checks passed"  
✅ VPS应用日志显示"Tornado application started"  
✅ `curl http://localhost:8000/health` 返回 `{"status":"ok"}`  
✅ 小程序能正常连接和通信  
✅ Web用户能访问所有功能  
✅ 数据库正常查询  

---

## 📞 快速参考

```bash
# 查看Replit的改动
git status

# 查看提交历史
git log --oneline -10

# 查看当前分支
git branch

# 查看远程分支
git branch -r

# 查看当前版本
git describe --tags

# 强制拉取VPS最新代码
cd /opt/secondhand-platform
git fetch origin main
git reset --hard origin/main

# 查看VPS应用状态
docker-compose ps
docker-compose logs app

# 紧急重启VPS应用
docker-compose restart app

# 查看VPS数据库
docker-compose exec postgres psql -U secondhand_user -d secondhand_db -c "SELECT COUNT(*) FROM users;"
```

---

## 📌 关键要点总结

1. **Replit** = 开发环境，快速迭代和测试
2. **GitHub** = 版本控制和CI/CD触发点
3. **GitHub Actions** = 自动化测试和构建
4. **VPS** = 生产环境，用户访问的真实服务

推送流程：
```
Replit开发 → Git提交 → GitHub推送 → Actions自动测试 → VPS自动更新 → 用户看到新功能
```

一次完整的发布通常只需要：
- **编码**: 1-2天
- **测试和提交**: 5-10分钟
- **自动部署**: 5-10分钟
- **总耗时**: 1-2天（包括开发时间）

您现在已经拥有完全自动化的持续部署流程！

---

## 🖥️ RackNerd VPS 部署指南 (happepls.pics)

### 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    RackNerd VPS                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Nginx (宿主机)                              ││
│  │   端口 8543 (HTTPS) → 反代到 127.0.0.1:8100            ││
│  └─────────────────────────────────────────────────────────┘│
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │            Docker Network: secondhand-network           ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ││
│  │  │   Tornado    │  │  PostgreSQL  │  │    Redis     │  ││
│  │  │   App:8000   │  │   :5432      │  │    :6379     │  ││
│  │  │ (→8100外部) │  │  (→5433外部) │  │  (→6380外部) │  ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘  ││
│  └─────────────────────────────────────────────────────────┘│
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                 MongoDB Atlas (云服务)                   ││
│  │      mongodb+srv://...mongodb.net/chat_db              ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 端口规划 (避免冲突)

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|---------|---------|------|
| Tornado 应用 | 8000 | 8100 | 仅本地访问 |
| PostgreSQL | 5432 | 5433 | 仅本地访问 |
| Redis | 6379 | 6380 | 仅本地访问 |
| Nginx HTTPS | - | 8543 | 公网访问 |
| ~~已占用~~ | - | 8000 | Jitsi Meet |
| ~~已占用~~ | - | 8443 | Jitsi HTTPS |
| ~~已占用~~ | - | 9000/9080 | ASR服务 |

### 首次部署步骤

#### 第1步：上传代码到VPS

```bash
# 方法A: 使用同步脚本 (在Replit Shell中执行)
cd /home/runner/secondhand-platform
bash deploy/sync-to-vps.sh

# 方法B: 手动rsync
rsync -avz --exclude='.git' --exclude='__pycache__' \
    ./ root@happepls.pics:/opt/secondhand-platform/
```

#### 第2步：配置环境变量

```bash
# SSH登录VPS
ssh root@happepls.pics

# 进入项目目录
cd /opt/secondhand-platform

# 从模板创建环境配置
cp deploy/.env.prod.template .env.prod
chmod 600 .env.prod

# 编辑配置，填入实际值
nano .env.prod
```

**需要填入的关键配置:**
- `PGPASSWORD`: PostgreSQL密码 (建议16位以上随机字符)
- `SECRET_KEY`: 应用密钥 (32位随机字符串)
- `SESSION_SECRET`: 会话密钥 (32位随机字符串)
- `MONGODB_URI`: 从Replit Secrets复制MongoDB Atlas连接串
- `WX_MINIPROGRAM_APP_SECRET`: 从Replit Secrets复制
- `ALIYUN_*`: 阿里云SMS配置，从Replit Secrets复制

#### 第3步：迁移数据库数据

```bash
# 在Replit Shell中导出数据
cd /home/runner/secondhand-platform
bash deploy/migrate-replit-to-vps.sh

# 下载生成的 backup_replit_XXXXXX.sql 文件

# 上传到VPS
scp backup_replit_*.sql root@happepls.pics:/opt/secondhand-platform/

# 在VPS上导入数据 (启动容器后)
docker exec -i secondhand-postgres psql -U secondhand_user -d secondhand_db < backup_replit_*.sql
```

#### 第4步：配置Nginx HTTPS

```bash
# 复制Nginx配置
cp deploy/nginx_secondhand_8543.conf /etc/nginx/conf.d/secondhand_8543.conf

# 测试配置
nginx -t

# 重载Nginx
systemctl reload nginx
```

#### 第5步：启动Docker服务

```bash
cd /opt/secondhand-platform

# 首次部署，使用一键脚本
sudo bash deploy/vps-deploy.sh --init

# 或手动启动
docker compose -f deploy/docker-compose-vps.yml up -d --build
```

#### 第6步：验证部署

```bash
# 检查容器状态
docker compose -f deploy/docker-compose-vps.yml ps

# 检查应用日志
docker compose -f deploy/docker-compose-vps.yml logs -f app

# 测试健康检查
curl http://127.0.0.1:8100/health
curl -k https://happepls.pics:8543/health
```

### 配置微信小程序后台

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 进入 **开发管理 → 开发设置 → 服务器域名**
3. 添加以下域名:

| 类型 | 域名 |
|------|------|
| request合法域名 | `https://happepls.pics:8543` |
| socket合法域名 | `wss://happepls.pics:8543` |
| uploadFile合法域名 | `https://happepls.pics:8543` |
| downloadFile合法域名 | `https://happepls.pics:8543` |

### 日常更新流程

```bash
# 方法A: 使用同步脚本 (在Replit Shell中)
bash deploy/sync-to-vps.sh --restart

# 方法B: SSH到VPS手动更新
ssh root@happepls.pics
cd /opt/secondhand-platform
sudo bash deploy/vps-deploy.sh --update
```

### 常用运维命令

```bash
# 查看服务状态
sudo bash deploy/vps-deploy.sh --status

# 查看应用日志
sudo bash deploy/vps-deploy.sh --logs

# 重启应用
sudo bash deploy/vps-deploy.sh --restart

# 备份数据库
sudo bash deploy/vps-deploy.sh --backup

# 停止所有服务
sudo bash deploy/vps-deploy.sh --stop
```

### 部署文件清单

```
deploy/
├── docker-compose-vps.yml      # VPS专用Docker Compose配置
├── nginx_secondhand_8543.conf  # Nginx HTTPS反代配置
├── .env.prod.template          # 生产环境变量模板
├── vps-deploy.sh               # VPS一键部署脚本
├── sync-to-vps.sh              # Replit→VPS代码同步脚本
├── migrate-replit-to-vps.sh    # 数据库迁移脚本
└── init-db.sql                 # 数据库初始化SQL
```

### 切换小程序环境

编辑 `miniprogram/utils/config.js`:

```javascript
// 开发模式 (使用Replit)
const isDev = true

// 生产模式 (使用VPS)
const isDev = false
```

生产环境API地址: `https://happepls.pics:8543`

