# 自定义域名配置指南 (okashii.top)

## 问题诊断

您的域名 `okashii.top` DNS Record检查未通过，可能的原因：

### 常见问题
1. **DNS传播未完成** - DNS记录更改需要几分钟到48小时传播
2. **A记录配置错误** - 未正确添加Replit提供的A记录
3. **TXT记录缺失** - 验证所有权需要的TXT记录未添加
4. **Cloudflare代理问题** - 如果使用Cloudflare，代理模式会导致问题
5. **多个A记录冲突** - 同一域名指向多个IP地址
6. **AAAA记录冲突** - Replit只支持A记录（IPv4），不支持AAAA记录（IPv6）

---

## 解决步骤

### 第一步：获取Replit的DNS记录

1. 登录Replit，打开您的项目
2. 点击右上角**"Deploy"**按钮
3. 进入**"Deployments"**标签
4. 找到**"Custom Domains"**部分
5. 点击**"Add domain"**或查看现有域名
6. Replit会显示需要添加的记录，类似：

```
Type: A
Name: @
Value: 34.160.111.145

Type: TXT
Name: _replit-challenge
Value: xxxxxxxxxxxxx
```

**重要：** 记录下这些准确的值（IP地址和challenge值因项目而异）

---

### 第二步：在域名注册商配置DNS

以常见注册商为例：

#### 如果使用Cloudflare

1. 登录Cloudflare控制台
2. 选择域名 `okashii.top`
3. 进入**"DNS"**设置
4. 添加以下记录：

**A记录：**
- Type: `A`
- Name: `@` （表示根域名 okashii.top）
- IPv4 address: `34.160.111.145`（**替换为Replit提供的IP**）
- Proxy status: **🔴 DNS only**（关闭代理，非常重要！）
- TTL: Auto

**TXT记录：**
- Type: `TXT`
- Name: `_replit-challenge`
- Content: `xxxxxxxxx`（**替换为Replit提供的值**）
- Proxy status: DNS only
- TTL: Auto

**关键步骤：** 确保A记录的"Proxy status"显示灰色云朵（DNS only），而非橙色云朵（Proxied）。

**删除冲突记录：**
- 删除所有其他指向`@`的A记录
- 删除所有AAAA记录（IPv6）
- 删除所有CNAME记录（如果有）

#### 如果使用阿里云万网

1. 登录阿里云控制台
2. 进入**"域名"** → **"域名列表"**
3. 点击`okashii.top`后的**"解析"**
4. 添加记录：

**A记录：**
- 记录类型: `A`
- 主机记录: `@`
- 解析线路: 默认
- 记录值: `34.160.111.145`（**替换为Replit提供的IP**）
- TTL: 10分钟

**TXT记录：**
- 记录类型: `TXT`
- 主机记录: `_replit-challenge`
- 解析线路: 默认
- 记录值: `xxxxxxxxx`（**替换为Replit提供的值**）
- TTL: 10分钟

#### 如果使用腾讯云DNSPod

1. 登录DNSPod控制台
2. 进入域名解析
3. 添加记录：

**A记录：**
- 主机记录: `@`
- 记录类型: `A`
- 线路类型: 默认
- 记录值: `34.160.111.145`（**替换为Replit提供的IP**）
- TTL: 600

**TXT记录：**
- 主机记录: `_replit-challenge`
- 记录类型: `TXT`
- 线路类型: 默认
- 记录值: `xxxxxxxxx`（**替换为Replit提供的值**）
- TTL: 600

#### 如果使用GoDaddy

1. 登录GoDaddy账户
2. 进入**"My Products"** → **"DNS"**
3. 找到`okashii.top`，点击**"Manage"**

**A记录：**
- Type: `A`
- Host: `@`
- Points to: `34.160.111.145`（**替换为Replit提供的IP**）
- TTL: 600 seconds

**TXT记录：**
- Type: `TXT`
- Host: `_replit-challenge`
- TXT Value: `xxxxxxxxx`（**替换为Replit提供的值**）
- TTL: 600 seconds

---

### 第三步：验证DNS配置

**使用命令行工具：**

```bash
# 检查A记录（Windows/Mac/Linux）
nslookup okashii.top

# 或使用dig（Mac/Linux）
dig okashii.top A

# 检查TXT记录
dig _replit-challenge.okashii.top TXT
```

**在线工具：**
- https://dnschecker.org - 全球DNS传播检查
- https://www.whatsmydns.net - 查看DNS记录

**期望结果：**
```
okashii.top.  600  IN  A  34.160.111.145
_replit-challenge.okashii.top.  600  IN  TXT  "xxxxxxxxxxxx"
```

---

### 第四步：等待DNS传播

DNS记录更改后需要时间传播：

- **最快：** 5-10分钟
- **通常：** 1-2小时
- **最慢：** 48小时

**加速传播技巧：**
1. 将TTL设置为最小值（如600秒）
2. 删除所有冲突的旧记录
3. 使用DNS刷新工具清除本地缓存：
   ```bash
   # Windows
   ipconfig /flushdns
   
   # Mac
   sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
   
   # Linux
   sudo systemd-resolve --flush-caches
   ```

---

### 第五步：在Replit验证域名

1. 回到Replit项目的**"Deployments"**页面
2. 检查域名状态：
   - 🟢 **Verified** - DNS配置成功
   - 🟡 **Pending** - 正在验证中
   - 🔴 **Failed** - DNS配置有问题

3. 如果状态为**Pending**，点击**"Refresh"**或**"Verify"**按钮

4. 成功后，Replit会自动配置SSL证书（Let's Encrypt）

---

## 常见错误排查

### 错误1："DNS records not found"

**原因：** DNS记录未正确添加或未传播

**解决：**
1. 再次检查A记录和TXT记录是否正确
2. 确认主机记录为`@`而非`www`或其他
3. 等待DNS传播（使用dnschecker.org确认）

### 错误2："Multiple A records detected"

**原因：** 同一域名有多个A记录

**解决：**
1. 删除所有指向`@`的旧A记录
2. 只保留Replit提供的一条A记录
3. 等待5-10分钟后重试

### 错误3："AAAA record conflict"

**原因：** 存在IPv6 AAAA记录，Replit不支持

**解决：**
1. 删除所有AAAA记录
2. 只使用A记录（IPv4）
3. 刷新DNS缓存

### 错误4："TXT record verification failed"

**原因：** TXT记录值不正确

**解决：**
1. 完整复制Replit提供的challenge值（包括引号内的所有字符）
2. 确认主机记录为`_replit-challenge`
3. 使用`dig`工具验证TXT记录

### 错误5："SSL certificate failed"

**原因：** 域名未验证或Cloudflare代理问题

**解决：**
1. 确保域名状态为"Verified"
2. 如使用Cloudflare，关闭代理（DNS only）
3. 等待几分钟让Replit重新生成证书

---

## 子域名配置（可选）

如果要使用子域名如`www.okashii.top`或`api.okashii.top`：

**CNAME记录（推荐）：**
```
Type: CNAME
Name: www
Target: okashii.top
TTL: 600
```

**或A记录：**
```
Type: A
Name: www
Value: 34.160.111.145（Replit提供的IP）
TTL: 600
```

---

## 验证清单

在Replit尝试验证前，确保：

- [ ] A记录已添加，主机记录为`@`，指向Replit提供的IP
- [ ] TXT记录已添加，主机记录为`_replit-challenge`
- [ ] 删除了所有其他A记录
- [ ] 删除了所有AAAA记录
- [ ] 如使用Cloudflare，已关闭代理（灰色云朵）
- [ ] DNS传播已完成（使用dnschecker.org确认）
- [ ] 清除了本地DNS缓存

---

## 完成后效果

配置成功后：

✅ `https://okashii.top` - 自动跳转到您的应用
✅ 自动HTTPS加密（SSL证书）
✅ 微信小程序可使用此域名作为合法域名

**微信小程序配置：**

在小程序后台添加服务器域名：
- request合法域名：`https://okashii.top`
- socket合法域名：`wss://okashii.top`
- uploadFile合法域名：`https://okashii.top`

同时更新小程序配置文件：
```javascript
// miniprogram/utils/config.js
const config = {
  API_BASE: 'https://okashii.top',
  WS_BASE: 'wss://okashii.top',
  // ...
}
```

---

## 需要帮助？

如果按照以上步骤仍无法解决：

1. **联系域名注册商支持**
   - 确认DNS记录已正确添加
   - 询问是否有特殊限制或防火墙规则

2. **联系Replit支持**
   - 访问：https://replit.com/support
   - 提供域名和项目信息

3. **社区帮助**
   - Replit Ask论坛：https://ask.replit.com

---

**祝您配置成功！** 🎉

配置完成后，您的小程序将可以使用`okashii.top`作为正式域名，提供更专业的用户体验。
