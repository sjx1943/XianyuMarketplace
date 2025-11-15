# 微信小程序部署指南

本文档详细介绍如何将闲鱼二手交易平台的Web版本转换并部署为微信小程序。

## 前期准备

### 1. 注册微信小程序账号
1. 访问 [微信公众平台](https://mp.weixin.qq.com/)
2. 选择"立即注册" → "小程序"
3. 按提示完成注册流程
4. 获取小程序的AppID

### 2. 下载开发工具
1. 下载 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 安装并登录开发者工具

### 3. 配置后端域名
1. 在微信公众平台 → 开发 → 开发设置中配置：
   - request合法域名：`https://your-domain.com`
   - socket合法域名：`wss://your-domain.com`
   - uploadFile合法域名：`https://your-domain.com`
   - downloadFile合法域名：`https://your-domain.com`

## 项目结构说明

```
miniprogram/
├── app.js              # 小程序主逻辑
├── app.json            # 小程序配置
├── app.wxss            # 全局样式
├── pages/              # 页面目录
│   ├── index/          # 首页
│   │   ├── index.js
│   │   ├── index.wxml
│   │   ├── index.wxss
│   │   └── index.json
│   ├── product/        # 商品相关页面
│   │   ├── list.js     # 商品列表
│   │   ├── detail.js   # 商品详情
│   │   └── publish.js  # 发布商品
│   ├── chat/          # 聊天相关页面
│   │   ├── list.js     # 聊天列表
│   │   └── room.js     # 聊天室
│   ├── order/         # 订单相关页面
│   │   ├── list.js     # 订单列表
│   │   ├── detail.js   # 订单详情
│   │   └── create.js   # 创建订单
│   ├── profile/       # 个人中心
│   │   ├── profile.js
│   │   └── edit.js
│   └── login/         # 登录页面
│       └── login.js
├── components/        # 组件目录
├── utils/            # 工具函数
└── images/          # 图片资源
```

## 部署步骤

### 1. 配置小程序

编辑 `miniprogram/app.js`，修改API地址：

```javascript
globalData: {
  apiBase: 'https://your-domain.com/api',  // 替换为实际API域名
  wsBase: 'wss://your-domain.com/ws',      // 替换为实际WebSocket域名
}
```

### 2. 导入项目

1. 打开微信开发者工具
2. 选择"导入项目"
3. 选择 `miniprogram` 目录
4. 输入小程序AppID
5. 点击"确定"

### 3. 配置项目

#### 修改 `project.config.json`：
```json
{
  "description": "闲鱼二手交易小程序",
  "packOptions": {
    "ignore": []
  },
  "setting": {
    "urlCheck": true,
    "es6": true,
    "enhance": true,
    "postcss": true,
    "preloadBackgroundData": false,
    "minified": true,
    "newFeature": false,
    "coverView": true,
    "nodeModules": false,
    "autoAudits": false,
    "showShadowRootInWxmlPanel": true,
    "scopeDataCheck": false,
    "uglifyFileName": false,
    "checkInvalidKey": true,
    "checkSiteMap": true,
    "uploadWithSourceMap": true,
    "compileHotReLoad": false,
    "babelSetting": {
      "ignore": [],
      "disablePlugins": [],
      "outputPath": ""
    },
    "useIsolateContext": true,
    "useCompilerModule": true,
    "userConfirmedUseCompilerModuleSwitch": false
  },
  "compileType": "miniprogram",
  "libVersion": "2.19.4",
  "appid": "your-appid",
  "projectname": "xianyu-miniprogram",
  "debugOptions": {
    "hidedInDevtools": []
  },
  "scripts": {},
  "isGameTourist": false,
  "simulatorType": "wechat",
  "simulatorPluginLibVersion": {},
  "condition": {
    "search": {
      "current": -1,
      "list": []
    },
    "conversation": {
      "current": -1,
      "list": []
    },
    "game": {
      "current": -1,
      "list": []
    },
    "plugin": {
      "current": -1,
      "list": []
    },
    "gamePlugin": {
      "current": -1,
      "list": []
    },
    "miniprogram": {
      "current": -1,
      "list": []
    }
  }
}
```

### 4. 完善页面代码

由于篇幅限制，需要完善其他页面的代码。主要包括：

#### 商品列表页面 (`pages/product/list.js`)
```javascript
Page({
  data: {
    products: [],
    loading: false,
    searchValue: '',
    currentCategory: '',
    page: 1,
    hasMore: true
  },

  onLoad(options) {
    if (options.search) {
      this.setData({ searchValue: options.search })
    }
    if (options.category) {
      this.setData({ currentCategory: options.category })
    }
    this.loadProducts()
  },

  async loadProducts() {
    // 实现商品加载逻辑
  }
})
```

#### 商品详情页面 (`pages/product/detail.js`)
```javascript
Page({
  data: {
    product: null,
    seller: null,
    comments: [],
    loading: false
  },

  onLoad(options) {
    if (options.id) {
      this.loadProduct(options.id)
    }
  },

  async loadProduct(id) {
    // 实现商品详情加载逻辑
  }
})
```

### 5. 实现核心功能

#### WebSocket聊天功能
```javascript
// utils/websocket.js
class WebSocketManager {
  constructor() {
    this.socket = null
    this.isConnected = false
    this.messageHandlers = new Set()
  }

  connect(userId) {
    const app = getApp()
    this.socket = wx.connectSocket({
      url: `${app.globalData.wsBase}/chat_room?user_id=${userId}`,
      success: () => {
        console.log('WebSocket连接成功')
      }
    })

    this.socket.onOpen(() => {
      this.isConnected = true
      console.log('WebSocket连接已打开')
    })

    this.socket.onMessage((res) => {
      const data = JSON.parse(res.data)
      this.messageHandlers.forEach(handler => handler(data))
    })

    this.socket.onClose(() => {
      this.isConnected = false
      console.log('WebSocket连接已关闭')
    })

    this.socket.onError((error) => {
      console.error('WebSocket错误:', error)
    })
  }

  sendMessage(message) {
    if (this.isConnected && this.socket) {
      this.socket.send({
        data: JSON.stringify(message)
      })
    }
  }

  addMessageHandler(handler) {
    this.messageHandlers.add(handler)
  }

  removeMessageHandler(handler) {
    this.messageHandlers.delete(handler)
  }

  disconnect() {
    if (this.socket) {
      this.socket.close()
    }
  }
}

export default new WebSocketManager()
```

#### 图片上传功能
```javascript
// utils/upload.js
export function uploadImage() {
  return new Promise((resolve, reject) => {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFilePaths[0]
        
        wx.uploadFile({
          url: getApp().globalData.apiBase + '/upload',
          filePath: tempFilePath,
          name: 'file',
          header: {
            'Authorization': 'Bearer ' + wx.getStorageSync('token')
          },
          success: (uploadRes) => {
            const data = JSON.parse(uploadRes.data)
            if (data.success) {
              resolve(data.filename)
            } else {
              reject(new Error(data.message))
            }
          },
          fail: reject
        })
      },
      fail: reject
    })
  })
}
```

### 6. 测试和调试

1. **本地测试**
   - 在开发者工具中测试各项功能
   - 检查网络请求是否正常
   - 测试WebSocket连接

2. **真机测试**
   - 使用开发者工具生成体验版二维码
   - 在真机上测试所有功能

### 7. 发布上线

1. **代码审核**
   - 检查代码质量和性能
   - 确保符合微信小程序规范

2. **提交审核**
   - 在开发者工具中点击"上传"
   - 在微信公众平台提交审核
   - 填写版本描述和更新内容

3. **发布**
   - 审核通过后点击"发布"
   - 小程序正式上线

## 关键技术点

### 1. 用户登录
使用微信登录替代用户名密码登录：
```javascript
// 微信登录
wx.login({
  success: (res) => {
    // 获取code，发送到后端换取session_key和openid
    // 后端验证后返回自定义token
  }
})
```

### 2. 支付功能（可选）
如需要支付功能，需申请微信支付：
```javascript
wx.requestPayment({
  timeStamp: '',
  nonceStr: '',
  package: '',
  signType: 'MD5',
  paySign: '',
  success: (res) => {
    // 支付成功
  }
})
```

### 3. 分享功能
```javascript
// 页面中添加分享配置
onShareAppMessage() {
  return {
    title: '闲鱼二手交易',
    path: '/pages/index/index'
  }
}
```

## 注意事项

1. **网络请求限制**
   - 小程序只支持HTTPS请求
   - 域名需要在后台配置白名单

2. **文件大小限制**
   - 小程序包大小不能超过2MB
   - 可使用分包加载优化

3. **API兼容性**
   - 部分Web API在小程序中不可用
   - 需要使用小程序专用API

4. **审核要求**
   - 遵守微信小程序运营规范
   - 不能包含违规内容

## 性能优化

1. **图片优化**
   - 使用WebP格式
   - 启用图片懒加载

2. **代码优化**
   - 使用分包加载
   - 避免频繁的setData操作

3. **网络优化**
   - 合并网络请求
   - 使用缓存机制

## 后续维护

1. **版本更新**
   - 定期更新小程序版本
   - 修复bug和添加新功能

2. **数据统计**
   - 接入微信小程序数据助手
   - 分析用户行为数据

3. **用户反馈**
   - 建立用户反馈渠道
   - 及时处理用户问题

---

完成以上步骤后，您的闲鱼二手交易平台就可以在微信小程序中正常运行了。如有问题，请参考微信小程序官方文档或联系技术支持。
