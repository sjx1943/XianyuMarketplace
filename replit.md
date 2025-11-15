# 小区二手商品交易平台 - Replit 部署版本

## 项目概述
基于 Tornado 框架的二手闲置物品交易平台，已适配到 Replit 环境运行。

## 技术栈
- **后端**: Python 3.11 + Tornado 6.4.2
- **数据库**: PostgreSQL (Replit提供) + MongoDB (聊天消息)
- **ORM**: SQLAlchemy 2.0.28
- **缓存**: Redis (可选)
- **前端**: HTML + CSS + JavaScript + WebSocket

## 当前完成的工作

### 已修复的问题
1. ✅ 修复用户注册路由404问题 - 添加了 `/regist` 路由别名
2. ✅ 修复密码重置路由404问题 - 添加了 `/forgot` 路由别名
3. ✅ 优化注册页面UI - 全新现代化设计，响应式布局
4. ✅ 数据库迁移 - 从MySQL成功迁移到PostgreSQL
5. ✅ 环境配置 - 安装所有依赖并配置Replit工作流
6. ✅ 用户登出功能 - 实现完整的登出逻辑，包括清除cookies、重定向和成功消息显示
7. ✅ 订单页面NoneType错误修复 - 实现order-snapshot策略，添加seller_id快照字段，支持已删除商品的订单管理
8. ✅ 强制用户名（房间号）设置 - 登录后必须设置楼号-单元号-房间号格式的用户名（如'3-1-801'），后续交易均使用此标识

### 环境变量
项目使用以下环境变量（由Replit自动配置）:
- `DATABASE_URL` - PostgreSQL连接字符串
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - 数据库详细配置

### MongoDB配置
聊天功能使用MongoDB存储消息。配置方式：
- 默认连接: `mongodb://localhost:27017/chat_db`
- 可通过环境变量覆盖: `MONGODB_HOST`, `MONGODB_PORT`, `MONGODB_DATABASE`

### 用户名（房间号）设置规则
为了便于小区内部管理，所有用户登录后必须设置房间号：
- **格式要求**: 楼号-单元号-房间号（例如：3-1-801，代表3幢1单元801室）
- **唯一性**: 每个房间号全局唯一，一经设置即作为用户唯一标识
- **强制性**: 首次登录后必须设置，否则无法访问其他功能
- **显示规则**: 所有买卖交易、聊天消息显示的用户名均为房间号

## 待完成的任务

### 高优先级
- [ ] 实现商品图片上传的即时预览和删除功能
- [ ] 修复订单页面 NoneType 错误
- [ ] 完善订单创建和发货流程
- [ ] 在商品详情页添加编辑按钮

### 中优先级
- [ ] 实现卖家消息通知系统
- [ ] 优化聊天室UI布局
- [ ] 完善消息时间戳显示
- [ ] 修复右键菜单位置问题

### 低优先级
- [ ] 实现用户登出功能
- [ ] 添加游客模式浏览
- [ ] 移动端响应式优化

## 启动命令
```bash
# 初始化数据库表
python init_db.py

# 可选：迁移现有订单数据（添加seller_id快照）
python migrate_orders_seller_id.py

# 启动服务器
python app.py --port=5000
```

## 项目结构
```
.
├── app.py                  # 主应用入口
├── init_db.py             # 数据库初始化脚本
├── config.ini             # 配置文件
├── base/                  # 数据库基础配置
├── models/                # 数据模型
├── controllers/           # 业务控制器
├── templates/             # HTML模板
├── mystatics/            # 静态资源
└── utils/                # 工具函数
```

## 最后更新
2025-11-15 - 初始Replit部署和基础问题修复
