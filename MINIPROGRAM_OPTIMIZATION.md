# 微信小程序快速部署指南 v1.1.0

> 🚀 本指南帮助您在 **30分钟内** 完成小程序部署上线

---

## 📋 当前版本功能清单 (Nov 27, 2025)

### ✅ 核心功能

| 模块 | 功能 | 状态 |
|------|------|------|
| 👤 **用户系统** | 微信小程序OAuth登录 | ✅ 已实现 |
| | 房间号设置 | ✅ 已实现 |
| | 个人资料管理 | ✅ 已实现 |
| 🛍️ **商品系统** | 商品发布（多图上传） | ✅ 已实现 |
| | **商品成色选择**（全新~很旧） | ✅ **新增** |
| | 商品分类标签 | ✅ 已实现 |
| | 商品搜索 | ✅ 已实现 |
| | 商品详情查看 | ✅ 已实现 |
| 💬 **聊天系统** | 实时消息 | ✅ 已实现 |
| | 未读消息徽章 | ✅ 已实现 |
| | 聊天记录 | ✅ 已实现 |
| 📦 **订单系统** | 创建订单 | ✅ 已实现 |
| | 订单状态管理 | ✅ 已实现 |
| | 24小时自动确认 | ✅ 已实现 |
| ⭐ **评价系统** | **评价权限验证**（仅完成交易买家） | ✅ **新增** |
| | 商品评分 | ✅ 已实现 |
| | 评价内容展示 | ✅ 已实现 |

### 🆕 本版本更新 (Nov 27, 2025)

1. **商品成色功能** - 发布商品时可选择成色等级
   - 选项：全新、九成新、八成新、七成新、六成新、五成新、四成新、三成新、二成新、一成新、很旧
   - 详情页显示成色标签
   
2. **评价权限限制** - 只有完成交易的买家才能评价
   - 新增 `/api/product/{id}/can_review` 接口
   - 前端自动检查并显示权限提示

---

## 🎯 快速部署 5 步走

### 第1步：注册小程序账号（5分钟）

1. 访问 [微信公众平台](https://mp.weixin.qq.com)
2. 点击 **立即注册** → 选择 **小程序**
3. 填写邮箱、密码，完成邮箱验证
4. 选择主体类型：
   - **个人**（推荐新手）：免费，功能够用
   - **企业**：300元/年，支持微信支付
5. 完成实名认证

### 第2步：获取 AppID 和配置域名（10分钟）

#### 2.1 获取 AppID 和 AppSecret

1. 登录 [小程序后台](https://mp.weixin.qq.com)
2. 进入 **开发** → **开发管理** → **开发设置**
3. 复制 **AppID**（格式：`wx1234567890abcdef`）
4. 点击 **AppSecret** 的 **生成** 按钮
5. ⚠️ **立即保存 AppSecret**（只显示一次！）

#### 2.2 配置服务器域名

在 **开发设置** → **服务器域名** 中添加：

```
request合法域名:    https://your-app.replit.app
socket合法域名:     wss://your-app.replit.app
uploadFile合法域名: https://your-app.replit.app
downloadFile合法域名: https://your-app.replit.app
```

> 💡 **提示**：将 `your-app` 替换为您 Replit 项目的实际域名

### 第3步：修改小程序配置文件（5分钟）

#### 3.1 修改 `miniprogram/utils/config.js`（⚠️ 必须）

打开文件，**只需修改第12行**的域名配置：

```javascript
// 配置文件
// ⚠️ 部署前必须修改 production.host 为您的实际后端域名
const isDev = false  // 生产环境保持 false

// API配置
const config = {
  isDev: isDev,
  
  api: {
    // 生产环境 - ⚠️ 必须修改为您的实际域名
    production: {
      host: 'https://your-app.replit.app',  // ← 只需修改这一行！
      apiBase: '',   // 保持为空
      wsBase: '/ws'  // 保持不变
    },
    // ... 开发环境配置保持不变
  },
  // ... 其他配置保持不变
}
```

**修改示例**：

假设您的 Replit 项目地址是 `https://my-secondhand-app.replit.app`，则修改为：

```javascript
production: {
  host: 'https://my-secondhand-app.replit.app',  // 您的实际域名
  apiBase: '',
  wsBase: '/ws'
},
```

> 📝 **注意**：`api.js` 和 `app.js` 会自动从 `config.js` 读取配置，无需额外修改！

#### 3.3 在 Replit 添加环境变量

在 Replit 项目中，点击左侧 **Secrets** (🔒)，添加：

| Key | Value |
|-----|-------|
| `WX_MINIPROGRAM_APP_ID` | 您的小程序 AppID |
| `WX_MINIPROGRAM_APP_SECRET` | 您的小程序 AppSecret |

### 第4步：本地测试（5分钟）

#### 4.1 安装微信开发者工具

1. 下载 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 安装并使用微信扫码登录

#### 4.2 导入项目

1. 点击 **+** 创建新项目
2. 配置：
   - **项目名称**：小区二手市场
   - **目录**：选择本项目的 `miniprogram/` 文件夹
   - **AppID**：填入您的小程序 AppID
   - **不使用云服务**

3. 点击 **新建** 完成导入

#### 4.3 开启调试模式

1. 点击顶部 **详情**
2. ✅ 勾选 **不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书**
3. 点击 **编译** 测试

#### 4.4 功能测试清单

**基础功能测试**：
- [ ] 微信登录成功
- [ ] 设置房间号
- [ ] 浏览商品列表
- [ ] 查看商品详情

**新功能测试**：
- [ ] 商品详情页显示成色标签（如"九成新"）
- [ ] 发布商品时可选择成色等级（全新~很旧）
- [ ] 未购买商品时，评价按钮不显示
- [ ] 完成订单后，可以评价商品

**通信功能测试**：
- [ ] 发送聊天消息
- [ ] 接收聊天消息
- [ ] 创建订单成功
- [ ] 订单状态正确显示

### 第5步：提交审核上线（5分钟）

#### 5.1 上传代码

1. 在开发者工具中点击右上角 **上传**
2. 填写版本号：`1.1.0`
3. 填写项目备注：`新增商品成色和评价权限功能`
4. 点击 **上传**

#### 5.2 提交审核

1. 登录 [小程序后台](https://mp.weixin.qq.com)
2. 进入 **版本管理** → **开发版本**
3. 点击 **提交审核**
4. 填写审核信息：
   - 功能页面选择首页
   - 功能介绍简述核心功能
5. 点击 **提交审核**

#### 5.3 发布上线

审核通过后（通常1-3个工作日）：

1. 进入 **版本管理** → **审核版本**
2. 点击 **提交发布**
3. 确认后即可上线 🎉

---

## 📁 关键文件说明

### 项目结构

```
miniprogram/
├── app.js          # 主应用文件（登录、网络、全局方法）
├── app.json        # 小程序配置（页面路由、tabBar、权限）
├── app.wxss        # 全局样式
├── pages/          # 页面文件
│   ├── index/      # 首页（商品列表）
│   ├── product/    # 商品相关
│   │   ├── list.js/wxml/wxss    # 商品列表
│   │   ├── detail.js/wxml/wxss  # 商品详情（含成色展示）
│   │   └── publish.js/wxml/wxss # 发布商品（含成色选择）
│   ├── chat/       # 聊天功能
│   ├── order/      # 订单管理
│   ├── profile/    # 个人中心
│   └── login/      # 登录页面
├── utils/          # 工具类
│   ├── config.js   # ⚠️ 配置文件（必须修改域名）
│   ├── api.js      # API 请求封装
│   └── cache.js    # 缓存管理
├── components/     # 可复用组件
└── images/         # 图片资源
```

### 配置文件详解

#### `miniprogram/utils/config.js`

```javascript
const config = {
  isDev: false,  // 生产环境设为 false，开发调试设为 true
  
  api: {
    production: {
      host: 'https://your-app.replit.app',  // ← 您的后端域名
      apiBase: '',      // API 路径前缀（通常为空）
      wsBase: '/ws'     // WebSocket 路径
    },
    development: {
      host: 'http://localhost:5000',  // 本地开发时使用
      apiBase: '',
      wsBase: '/ws'
    }
  },

  timeout: {
    request: 10000,   // 普通请求超时时间（10秒）
    upload: 30000,    // 文件上传超时时间（30秒）
    download: 10000   // 文件下载超时时间
  },

  pagination: {
    pageSize: 20      // 每页加载商品数量
  }
}
```

#### `miniprogram/app.json`

```json
{
  "pages": [
    "pages/index/index",      // 首页
    "pages/product/list",     // 商品列表
    "pages/product/detail",   // 商品详情
    "pages/product/publish",  // 发布商品
    "pages/chat/list",        // 聊天列表
    "pages/chat/room",        // 聊天室
    "pages/order/list",       // 订单列表
    "pages/order/detail",     // 订单详情
    "pages/order/create",     // 创建订单
    "pages/profile/profile",  // 个人中心
    "pages/profile/edit",     // 编辑资料
    "pages/login/login"       // 登录页面
  ],
  
  "tabBar": {
    "list": [
      { "pagePath": "pages/index/index", "text": "首页" },
      { "pagePath": "pages/product/list", "text": "商品" },
      { "pagePath": "pages/chat/list", "text": "消息" },
      { "pagePath": "pages/order/list", "text": "订单" },
      { "pagePath": "pages/profile/profile", "text": "我的" }
    ]
  }
}
```

---

## ❓ 常见问题速查

### 问题1：request:fail url not in domain list

**原因**：服务器域名未配置或配置错误

**解决方案**：
1. 检查小程序后台 **服务器域名** 配置
2. 确保域名是 HTTPS
3. 开发阶段勾选"不校验合法域名"

### 问题2：登录失败 / code 无效

**原因**：AppID 或 AppSecret 配置错误

**解决方案**：
1. 检查 Replit Secrets 中的 `WX_MINIPROGRAM_APP_ID` 和 `WX_MINIPROGRAM_APP_SECRET`
2. 确保使用的是小程序 AppID（不是公众号的）
3. 重新生成 AppSecret 并更新

### 问题3：图片无法加载

**原因**：downloadFile 域名未配置

**解决方案**：
1. 在小程序后台添加 downloadFile 合法域名
2. 确保图片 URL 是 HTTPS

### 问题4：商品成色不显示

**原因**：后端数据库未添加 condition 字段

**解决方案**：
后端会自动添加该字段。如果问题持续，执行：
```sql
ALTER TABLE products ADD COLUMN condition VARCHAR(32) DEFAULT '九成新';
```

### 问题5：评价按钮不显示

**原因**：需要完成交易才能评价

**解决方案**：
1. 确保订单状态为 "completed"
2. 检查 `/api/product/{id}/can_review` 接口响应
3. 确保当前用户是该订单的买家

### 问题6：WebSocket 连接失败

**原因**：socket 域名未配置

**解决方案**：
1. 在小程序后台添加 `wss://your-app.replit.app` 到 socket 合法域名
2. 确保后端 WebSocket 服务正常运行

### 问题7：config.js 配置后仍无法连接

**原因**：修改了错误的位置或格式错误

**解决方案**：
1. 确保只修改第12行的 `host` 值
2. 保持引号和逗号格式正确
3. 不要修改 `apiBase` 和 `wsBase`
4. 正确格式示例：`host: 'https://my-app.replit.app',`

### 问题8：新功能不生效（成色/评价权限）

**原因**：后端代码未更新或数据库字段缺失

**解决方案**：
1. 确保后端已添加 `condition` 字段到 products 表
2. 确保后端已添加 `/api/product/{id}/can_review` 路由
3. 重启后端服务：`python app.py --port=5000`

---

## ✅ 上线前检查清单

### 必须完成

- [ ] 小程序 AppID 和 AppSecret 已正确配置到 Replit Secrets
- [ ] `config.js` 第12行的域名已修改为您的实际 Replit 域名
- [ ] 服务器域名（request/socket/upload/download）已在小程序后台配置
- [ ] 微信登录功能正常
- [ ] 商品列表加载正常
- [ ] 商品成色在发布和详情页正确显示
- [ ] 评价权限正确（仅完成交易买家可评价）
- [ ] 后端服务稳定运行

### 建议完成

- [ ] 小程序名称、头像、介绍已完善
- [ ] 服务类目已正确选择（推荐"工具-信息查询"）
- [ ] 隐私政策已配置
- [ ] 体验版已邀请测试人员测试
- [ ] 准备好功能截图（审核时每个功能至少1张）
- [ ] WebSocket 聊天功能已测试通过

---

## 🔧 进阶配置

### 自定义商品成色选项

修改 `miniprogram/pages/product/publish.js` 中的 `conditions` 数组：

```javascript
data: {
  conditions: ['全新', '九成新', '八成新', '七成新', '六成新', '五成新', '四成新', '三成新', '二成新', '一成新', '很旧'],
  conditionIndex: 1,  // 默认选中"九成新"
}
```

### 自定义商品分类

修改 `miniprogram/pages/product/publish.js` 中的 `categories` 数组：

```javascript
data: {
  categories: ['数码产品', '家用电器', '服装鞋包', '图书音像', '运动户外', '美妆个护', '家居用品', '其他'],
}
```

---

## 📞 技术支持

- **微信小程序开发文档**：https://developers.weixin.qq.com/miniprogram/dev/framework/
- **微信开放社区**：https://developers.weixin.qq.com/community/
- **项目技术文档**：参阅 `replit.md` 和 `MINIPROGRAM_DEPLOYMENT_GUIDE.md`

---

**最后更新**：2025-11-27  
**版本**：v1.1.0  
**状态**：✅ 已验证可部署
