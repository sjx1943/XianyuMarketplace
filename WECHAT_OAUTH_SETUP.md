# 微信OAuth登录配置指南

## 概述
本项目支持微信扫码登录和微信浏览器内授权登录，实现小区居民通过微信账号快速登录。

## 前置要求

### 1. 注册微信开放平台账号
- 访问：[https://open.weixin.qq.com](https://open.weixin.qq.com)
- 点击"注册"，选择"网站应用"类型
- 完成企业/个人开发者认证（需要提供营业执照或身份证）
- **费用**：企业认证费用约300元/年

### 2. 创建网站应用
1. 登录微信开放平台
2. 进入"管理中心" -> "网站应用"
3. 点击"创建应用"
4. 填写应用信息：
   - **应用名称**：小区二手交易平台
   - **应用简介**：社区居民二手闲置物品交易
   - **应用官网**：您的Replit应用URL（如 https://your-app.replit.app）
   - **授权回调域**：your-app.replit.app
5. 提交审核（通常1-3个工作日）

### 3. 获取AppID和AppSecret
审核通过后：
1. 进入"管理中心" -> "网站应用"
2. 点击您的应用
3. 记录**AppID**和**AppSecret**（妥善保管，不要泄露）

---

## 配置步骤

### Step 1: 设置环境变量
在Replit项目中添加以下环境变量（Secrets）：

```bash
WECHAT_APP_ID=wx1234567890abcdef        # 替换为您的AppID
WECHAT_APP_SECRET=your_secret_here      # 替换为您的AppSecret
WECHAT_REDIRECT_URI=https://your-app.replit.app/wechat/callback  # 回调URL
```

**重要提示**：
- `WECHAT_REDIRECT_URI` 必须与微信开放平台注册的回调域一致
- 建议使用Replit Secrets功能存储敏感信息

### Step 2: 数据库迁移
运行迁移脚本添加微信字段：

```bash
python migrate_wechat_fields.py
```

该脚本会为`xu_user`表添加以下字段：
- `wechat_openid` - 微信用户唯一标识（UNIQUE）
- `wechat_nickname` - 微信昵称
- `wechat_avatar` - 微信头像URL

### Step 3: 更新应用路由
在`app.py`中已添加微信登录路由：

```python
(r"/wechat/login", WeChatLoginHandler),
(r"/wechat/callback", WeChatCallbackHandler),
(r"/api/wechat/unbind", WeChatUnbindHandler),
```

### Step 4: 重启应用
```bash
# Replit会自动重启，或手动重启
python app.py --port=5000
```

---

## 使用方式

### PC端登录流程
1. 用户访问 `/wechat/login`
2. 显示微信二维码扫码页面
3. 用户使用微信扫码
4. 微信授权后跳转回应用
5. 首次登录需要设置房间号（如 3-1-801）
6. 后续可直接微信扫码登录

### 微信浏览器内登录流程
1. 用户在微信内访问 `/wechat/login`
2. 自动跳转微信授权页面
3. 用户点击"确认授权"
4. 返回应用并自动登录
5. 首次登录设置房间号

### 解绑微信账号
用户可在账户设置页面解绑微信：
```javascript
// 发送POST请求到 /api/wechat/unbind
fetch('/api/wechat/unbind', {
    method: 'POST',
    headers: { 'X-XSRFToken': getCookie('_xsrf') }
})
```

---

## 登录页面集成

### 在登录页面添加微信登录按钮
编辑 `templates/login.html`，添加：

```html
<div class="wechat-login-section">
    <p style="text-align: center; margin: 20px 0; color: #666;">或</p>
    <a href="/wechat/login" class="wechat-login-btn">
        <img src="/static/images/wechat-icon.png" alt="微信" style="width: 24px; vertical-align: middle; margin-right: 8px;">
        微信登录
    </a>
</div>

<style>
.wechat-login-btn {
    display: block;
    width: 100%;
    padding: 12px;
    margin-top: 15px;
    background: #07C160;
    color: white;
    text-align: center;
    border-radius: 5px;
    text-decoration: none;
    font-weight: 500;
    transition: background 0.3s;
}

.wechat-login-btn:hover {
    background: #06AD56;
}
</style>
```

---

## API接口

### 1. 微信登录入口
**GET** `/wechat/login`

**行为**：
- PC端：显示二维码扫描页面
- 微信浏览器：直接跳转授权

### 2. 微信OAuth回调
**GET** `/wechat/callback?code=xxx&state=xxx`

**参数**：
- `code` - 微信授权码
- `state` - 防CSRF状态码

**响应**：
- 成功：重定向到主页或房间号设置页面
- 失败：显示错误页面

### 3. 解绑微信
**POST** `/api/wechat/unbind`

**响应**：
```json
{
    "success": true,
    "message": "微信账号已解绑"
}
```

---

## 安全机制

### 1. CSRF防护
- 使用`state`参数防止CSRF攻击
- `state`值存储在secure cookie中，15分钟过期

### 2. OpenID唯一性
- `wechat_openid`设置为UNIQUE约束
- 防止同一微信账号重复注册

### 3. 密码随机化
- 微信登录用户生成随机密码
- 使用MD5+随机盐加密

### 4. Session管理
- 使用Tornado secure cookie
- Cookie设置httponly和secure标志

---

## 测试

### 开发环境测试
1. **测试账号申请**：
   - 微信公众平台提供沙箱测试环境
   - 访问：https://mp.weixin.qq.com/debug/cgi-bin/sandbox
   - 获取测试AppID和AppSecret

2. **本地测试**：
   - 使用ngrok等工具暴露本地端口
   - 配置回调URL为ngrok地址

### 生产环境测试
1. 确保应用部署到HTTPS域名
2. 配置微信开放平台回调域
3. 使用真实AppID/AppSecret
4. 测试扫码登录和浏览器内登录

---

## 故障排查

### 问题1：redirect_uri参数错误
**原因**：回调URL与微信平台配置不一致

**解决方案**：
- 检查`WECHAT_REDIRECT_URI`环境变量
- 确保与微信平台注册的回调域完全一致
- 注意：路径、协议(http/https)必须匹配

### 问题2：invalid appid
**原因**：AppID错误或未审核通过

**解决方案**：
- 检查`WECHAT_APP_ID`环境变量
- 确认应用已通过审核
- 区分测试AppID和正式AppID

### 问题3：获取access_token失败
**原因**：AppSecret错误或code已过期

**解决方案**：
- 检查`WECHAT_APP_SECRET`环境变量
- 确保code在5分钟内使用
- 不要重复使用同一个code

### 问题4：二维码不显示
**原因**：前端页面未正确渲染iframe

**解决方案**：
- 检查模板`wechat_qr_login.html`
- 确保QR URL正确生成
- 检查浏览器控制台错误

---

## 微信官方文档

- **开放平台文档**：https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html
- **OAuth 2.0指南**：https://developers.weixin.qq.com/doc/oplatform/Mobile_App/WeChat_Login/Development_Guide.html
- **错误码说明**：https://developers.weixin.qq.com/doc/oplatform/Return_codes/Return_code_descriptions_new.html

---

## 注意事项

1. **回调域白名单**：
   - 微信只允许回调到注册的域名
   - 开发环境建议使用沙箱测试账号

2. **用户数据隐私**：
   - 仅存储必要的微信信息（openid, nickname, avatar）
   - 遵守《个人信息保护法》要求
   - 提供用户解绑功能

3. **Token刷新**：
   - access_token有效期2小时
   - 如需长期使用，需实现refresh_token机制
   - 当前实现仅用于登录，不需要刷新

4. **多账号绑定**：
   - 当前一个微信只能绑定一个平台账号
   - 如需支持多账号，需修改数据库约束

---

## 后续扩展

### 1. 微信支付集成
- 开通微信商户号
- 集成微信支付API
- 支持小程序支付

### 2. 微信消息推送
- 使用微信模板消息
- 推送订单通知、交易提醒

### 3. 微信分享
- 集成微信JS-SDK
- 支持分享商品到朋友圈

---

如有问题，请查看日志文件或联系技术支持。
