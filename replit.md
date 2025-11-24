# 小区二手商品交易平台

## Overview
This project is a community-based second-hand goods trading platform built with the Tornado framework, adapted for deployment on Replit. It facilitates the exchange of idle items among residents, focusing on ease of use, security, and a rich user experience. Key features include robust user authentication (password, phone number + SMS, and WeChat OAuth), a real-time chat system, comprehensive product listings with image uploads, and an administrative dashboard for platform management. The platform includes a **WeChat Mini Program** frontend (`miniprogram/` folder) that provides a native mobile experience sharing the same backend API. The platform aims to create a streamlined and trustworthy environment for local community trading.

## User Preferences
I prefer iterative development with clear, concise explanations for each step. Please prioritize core functionality and user experience. I value clean code and robust error handling. For any significant changes or architectural decisions, please ask for my approval first. Ensure all user-facing features are mobile-responsive and accessible. Do not make changes to folder `base/`. Do not make changes to file `config.ini`.

## System Architecture
The platform is built on Python 3.11 with the Tornado 6.4.2 web framework.

### 开发与生产环境分离

#### 开发环境 (Replit)
-   **用途**: 代码开发、测试、迭代优化
-   **数据库**: Replit提供的PostgreSQL和MongoDB
-   **运行方式**: `python app.py --port=5000` (直接运行)
-   **部署**: 自动热重载，无需容器化
-   **推荐**: 功能开发、Bug修复、新特性测试在Replit中完成

#### 生产环境 (VPS)
-   **用途**: 提供稳定的线上服务
-   **服务器**: RackNerd VPS
-   **容器化**: Containerd + Docker Compose (轻量化)
-   **数据库**: 自部署PostgreSQL + MongoDB
-   **运行方式**: `docker-compose -f docker-compose-prod.yml up -d`
-   **部署脚本**: 一键部署和自动更新

### 核心技术栈
-   **Backend**: Python 3.11 + Tornado 6.4.2
-   **ORM**: SQLAlchemy 2.0.28
-   **关系数据库**: PostgreSQL 15 (Replit开发 / VPS生产)
-   **NoSQL数据库**: MongoDB 7 (聊天消息)
-   **缓存**: Redis 7 (可选)
-   **容器引擎**: Containerd (生产环境)
-   **Web服务器**: Nginx (生产环境反向代理)
-   **Frontend**: 
    -   **Web**: HTML, CSS, JavaScript, and WebSockets for dynamic interactions.
    -   **WeChat Mini Program**: Native mini program built with WXML, WXSS, and JavaScript (located in `miniprogram/` folder).
-   **UI/UX**: Modern, responsive design with a focus on intuitive navigation. Features like inline error messages, dynamic navigation bars, mobile-friendly button sizing, and responsive chat layouts enhance usability.
-   **Authentication**: Supports multiple login methods:
    -   Web: username/room number + password, phone number + SMS verification, WeChat OAuth (QR code for PC, in-browser for mobile)
    -   Mini Program: WeChat login via `wx.login()` API with automatic user creation/linking
-   **Session Management**: Employs a per-handler session pattern to prevent cross-request session pollution.
-   **Chat System**: Real-time messaging with unread notifications, message search, and a draggable, responsive sidebar.
-   **Product Management**: Features include product listing with instant image preview, multi-tag selection, and an optimized search function supporting multiple fields.
-   **Order Workflow**: Simplified states: `pending`, `shipped`, `completed`. Includes seller-side unread order notifications.
-   **Admin Dashboard**: A comprehensive administrative interface for user, product, and order management, including statistics and pagination, secured by `is_admin` flag.
-   **Core Concepts**:
    -   **Room Number Identity**: Users are identified by a mandatory "room number" (e.g., '3-1-801') for all transactions and communications.
    -   **Time Handling**: All timestamps are standardized to Beijing time (UTC+8), with client-side relative time display and automatic refresh.
    -   **Security**: CSRF protection for OAuth, unique constraints on identifiers (phone, OpenID), and secure handling of sensitive data.

## External Dependencies
-   **PostgreSQL**: Primary relational database for user data, products, orders.
-   **MongoDB**: NoSQL database specifically used for storing chat messages.
-   **Redis**: Optional caching layer.
-   **阿里云短信服务 (Alibaba Cloud SMS)**: Used for sending SMS verification codes during phone number login and password reset. Requires `ALIYUN_ACCESS_KEY_ID`, `ALIYUN_ACCESS_KEY_SECRET`, `ALIYUN_SMS_SIGN_NAME`, `ALIYUN_SMS_TEMPLATE_CODE`.
-   **SMTP (Email Service)**: Used for password reset emails, supporting SSL/TLS. Configurable via `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_SSL`. Defaults configured for QQ Mail.
-   **WeChat Open Platform OAuth**: Integrated for WeChat login (web version), requiring `WECHAT_APP_ID`, `WECHAT_APP_SECRET`, `WECHAT_REDIRECT_URI`.
-   **WeChat Mini Program**: Requires separate registration and AppID/AppSecret from WeChat Mini Program platform (mp.weixin.qq.com). Environment variables: `WX_MINIPROGRAM_APP_ID`, `WX_MINIPROGRAM_APP_SECRET`.

## Recent Changes (Nov 24, 2025 - Final Update)

### 自动化测试修复 - 所有17个测试通过 ✅
-   **修复1: 超长商品描述返回500错误**
    -   问题: ProductUploadHandler未验证描述长度
    -   解决: 添加5000字符限制，超长返回400而不是500
    -   代码: `controllers/product_controller.py` 第76-80行

-   **修复2: 未读消息API响应字段缺失**
    -   问题: UnreadCountHandler返回'total_count'但测试期望'total_unread'
    -   解决: 添加'total_unread'字段作为别名
    -   代码: `controllers/chat_controller.py` 第572行

-   **修复3: 零数量订单允许创建**
    -   问题: CreateOrderHandler未验证quantity > 0
    -   解决: 添加数量验证，拒绝0或负数订单
    -   代码: `controllers/order_controller.py` 第189-192行

-   **测试覆盖**: 17/17 测试通过 (100%)
    -   5个订单边界场景测试
    -   2个用户边界场景测试
    -   4个产品边界场景测试
    -   2个认证边界场景测试
    -   2个API安全测试
    -   2个未读通知测试

## Recent Changes (Nov 24, 2025 - Updated)

### 紧急修复 - 解决关键Bug和文件清理
-   **AsyncIOMainLoop Sleep错误修复** ✅
    -   问题: `await IOLoop.current().sleep()` 在Tornado中不存在
    -   解决: 改用 `IOLoop.current().call_later()` + callback方式
    -   代码位置: `controllers/order_controller.py` 行437-474
    -   改进: 使用 `sys.stderr.write()` 避免reentrant print错误
    -   验证: 应用正常启动，订单自动完成调度器成功初始化

-   **pytest命令行工具** ✅
    -   安装版本: pytest 9.0.1
    -   使用: `pytest tests/test_boundary_scenarios.py -v`

-   **部署文件结构清理** ✅
    -   删除6个多余文件: nginx.conf, default.conf, VPS_DEPLOYMENT_GUIDE.md等
    -   保留仅腾讯云相关: nginx-tencent.conf, TENCENT_CLOUD_DEPLOYMENT.md
    -   多云部署脚本: vps-install.sh (支持腾讯云/阿里云/AWS)

## Recent Changes (Nov 24, 2025)

### 功能修复与测试
-   **订单交易流程完善**：
    -   ✅ 实现24小时自动确认收货：后台任务（`start_order_auto_completion_scheduler`）每15分钟检查发货超过24小时的订单，自动完成
    -   ✅ 买家可手动点击"确认收货"提前完成交易（`ConfirmTransactionHandler`）
    -   ✅ 在app.py启动时初始化订单自动完成调度器
    -   ✅ 订单模型支持 `shipped_at` 和 `completed_at` 时间戳追踪

-   **用户体验改进**：
    -   ✅ 邮箱密码重置：添加5-10分钟延迟提醒和垃圾箱检查提示
    -   ✅ 改善忘记密码流程的用户友好度（`ForgotPasswordHandler`）

-   **自动化测试增强**：
    -   ✅ 完善边界场景测试 (`tests/test_boundary_scenarios.py`)
    -   ✅ 覆盖订单、商品、认证、安全、通知等5大类功能模块
    -   ✅ 修复测试中的变量引用bug，增强异常处理

-   **腾讯云部署支持**：
    -   ✅ 创建 `deploy/nginx-tencent.conf`：支持HTTP/HTTPS、WebSocket、静态资源缓存、SSL证书配置
    -   ✅ 创建 `deploy/TENCENT_CLOUD_DEPLOYMENT.md`：完整的腾讯云部署指南（购买、域名、证书、部署步骤、监控、安全建议）
    -   ✅ 升级 `deploy/vps-install.sh`：支持腾讯云/阿里云/AWS多云部署（--provider参数）
    -   ✅ 自动检测云服务商并配置对应的镜像源（腾讯云/阿里云）和Docker加速

### 项目结构清理 (Nov 23, 2025)
-   **删除重复代码**: 清理了过时的 `mytornado/xianyu/agent_mvc/` 重复项目目录
    -   ✅ 删除了旧版 app.py（该版本缺少手机号登录、微信OAuth、小程序支持、管理员功能）
    -   ✅ 保留根目录的主应用 (`app.py`) - 包含所有最新功能
    -   ✅ 删除了 `templates/publish_product.html.backup` 备份文件
    -   ✅ 删除了过时的测试结果文件 (`test_results_*.txt`)
    -   ✅ 项目结构已规范化，便于维护和开发

-   **生产环境迁移**: 创建完整的Replit → VPS迁移方案
    -   ✅ VPS一键部署脚本 (`deploy/vps-install.sh`)
    -   ✅ 数据库迁移脚本 (`deploy/migrate-db.sh`) 
    -   ✅ 生产环境Docker Compose配置 (`docker-compose-prod.yml`)
    -   ✅ 自动化部署脚本 (`deploy/auto-update.sh`) - 支持Git自动拉取和应用更新
    -   ✅ PostgreSQL和MongoDB初始化脚本
    -   ✅ 轻量化Dockerfile（基于python:3.11-slim）
    -   ✅ Nginx反向代理配置
    -   ✅ 环境变量管理模板 (`.env.example`)

## 部署指南

### 从Replit迁移到VPS - 4个步骤

#### 步骤1: 在VPS上执行一键安装脚本
```bash
sudo bash deploy/vps-install.sh
# 自动安装: Containerd, Docker Compose, PostgreSQL, MongoDB, Nginx, 应用代码
```

#### 步骤2: 迁移数据库
```bash
# 在Replit开发环境执行
export REPLIT_DATABASE_URL='...'  # Replit的PostgreSQL连接字符串
export REPLIT_MONGODB_URI='...'   # Replit的MongoDB连接字符串
export VPS_DATABASE_URL='...'     # VPS的PostgreSQL连接字符串
export VPS_MONGODB_URI='...'      # VPS的MongoDB连接字符串
bash deploy/migrate-db.sh
```

#### 步骤3: 配置环境变量
```bash
# 在VPS上编辑
nano /opt/secondhand-platform/.env.prod
# 设置: 微信AppID、阿里云短信、SMTP邮件等敏感信息
```

#### 步骤4: 启动应用
```bash
cd /opt/secondhand-platform
sudo docker-compose -f docker-compose-prod.yml up -d
```

### 自动化更新流程

每次在Replit上完成开发后，推送到GitHub，VPS自动更新：

```bash
# 手动更新（或配置GitHub Actions自动触发）
sudo bash /opt/secondhand-platform/deploy/auto-update.sh update
```

### 常用命令

```bash
# 检查状态
sudo bash deploy/auto-update.sh status

# 查看日志
sudo bash deploy/auto-update.sh logs app

# 重启服务
sudo bash deploy/auto-update.sh restart

# 备份数据库
sudo bash deploy/auto-update.sh backup

# 更新应用
sudo bash deploy/auto-update.sh update
```

## 文件结构

```
deploy/
├── vps-install.sh          # VPS一键安装脚本
├── migrate-db.sh           # 数据库迁移脚本
├── auto-update.sh          # 自动化部署脚本
├── docker-compose-prod.yml # 生产环境Compose配置
├── .env.example            # 环境变量模板
├── init-db.sql             # PostgreSQL初始化
└── init-mongo.js           # MongoDB初始化
Dockerfile.prod             # 生产环境镜像定义
```