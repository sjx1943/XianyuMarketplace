基于您提供的 GitHub 源码结构以及反馈的错误日志，我对 `miniprogram` 目录下的代码进行了全面的逻辑审查。

核心问题在于：**小程序无法像 Web 端那样自动处理 Cookie 和相对路径，且 UI 组件（如 Picker、Swiper）的数据绑定逻辑与 HTML `<select>` 不同。**

以下是针对性的**代码修复方案**，请按模块逐一修改：

-----

### 1\. 核心基础设施修复 (Global & Utils)

**解决问题：** API 403 鉴权失败、图片不显示 (Issue 6, 7, 8)

#### 1.1 修改 `app.js` (配置全局变量)

需要在全局定义后端地址，方便拼接图片路径。

```javascript
// app.js
App({
  globalData: {
    userInfo: null,
    baseUrl: 'https://okashii.top', // 基础域名，用于拼接图片
    apiUrl: 'https://okashii.top/api' // API 地址
  },
  onLaunch: function () {
    // 可以在这里检查登录状态
  }
})
```

#### 1.2 重写 `utils/api.js` (统一请求封装)

这是最关键的一步。必须手动在 Header 中注入 Token，并处理 401/403 跳转。

```javascript
// utils/api.js
const app = getApp();

const request = (url, method, data) => {
  const token = wx.getStorageSync('token'); // 从缓存获取 Token

  return new Promise((resolve, reject) => {
    wx.request({
      url: app.globalData.apiUrl + url, // 自动拼接 /api
      method: method,
      data: data,
      header: {
        'content-type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '' // 手动添加 Bearer Token
      },
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data);
        } else if (res.statusCode === 401 || res.statusCode === 403) {
          // Token 过期或未登录
          wx.showToast({ title: '请先登录', icon: 'none' });
          wx.removeStorageSync('token');
          wx.removeStorageSync('user');
          setTimeout(() => {
            wx.navigateTo({ url: '/pages/login/login' });
          }, 1000);
          reject('Unauthorized');
        } else {
          wx.showToast({ title: res.data.message || '请求失败', icon: 'none' });
          reject(res);
        }
      },
      fail: (err) => {
        wx.showToast({ title: '网络连接异常', icon: 'none' });
        reject(err);
      }
    });
  });
};

// 导出具体 API 方法
module.exports = {
  login: (data) => request('/login', 'POST', data),
  getProducts: (data) => request('/products', 'GET', data),
  getProductDetail: (id) => request(`/products/${id}`, 'GET'),
  uploadImage: (filePath) => {
    // 图片上传需要单独处理，因为是 wx.uploadFile 不是 wx.request
    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url: app.globalData.apiUrl + '/upload_image',
        filePath: filePath,
        name: 'file',
        header: {
          'Authorization': `Bearer ${wx.getStorageSync('token')}`
        },
        success: (res) => {
           // uploadFile 返回的 data 是字符串，需要 parse
           const data = JSON.parse(res.data);
           resolve(data);
        },
        fail: reject
      });
    });
  },
  // ... 其他接口保持一致，使用 request 封装
  markMessagesRead: (roomId) => request('/mark_messages_read', 'POST', { room_id: roomId }),
};
```

-----

### 2\. 发布商品页修复 (Publish)

**解决问题：** 分类报错 `undefined`、多图上传失败 (Issue 5, 9)

**文件：** `pages/publish/publish.js`

```javascript
const api = require('../../utils/api.js');
const app = getApp();

Page({
  data: {
    // 这里的顺序必须与后端 Enum 或数据库一致
    categories: ['数码产品', '生活用品', '图书教材', '美妆护肤', '票务娱乐', '其他'],
    categoryIndex: null, // 初始为空
    images: [], // 存储本地临时路径，用于预览
    form: {
      title: '',
      description: '',
      price: '',
      category: '',
      images: [] // 存储上传成功后的后端路径
    }
  },

  // 修复分类选择逻辑
  bindCategoryChange: function(e) {
    const index = e.detail.value;
    this.setData({
      categoryIndex: index,
      'form.category': this.data.categories[index] // 将索引映射回字符串
    });
  },

  // 选择图片
  chooseImage: function() {
    wx.chooseImage({
      count: 9 - this.data.images.length,
      success: (res) => {
        this.setData({
          images: this.data.images.concat(res.tempFilePaths)
        });
      }
    });
  },

  // 核心修复：多图上传 + 表单提交
  submitForm: async function() {
    if (!this.data.form.category) {
      return wx.showToast({ title: '请选择分类', icon: 'none' });
    }

    wx.showLoading({ title: '发布中...' });

    try {
      const uploadedUrls = [];
      // 串行或并行上传图片
      for (let path of this.data.images) {
        const res = await api.uploadImage(path);
        // 假设后端返回 { url: '/static/img/xxx.jpg' }
        uploadedUrls.push(res.url); 
      }

      const productData = {
        ...this.data.form,
        images: uploadedUrls // 替换为服务端路径
      };

      await api.createProduct(productData); // 需在 api.js 定义 createProduct

      wx.hideLoading();
      wx.showToast({ title: '发布成功' });

      // 延迟返回首页
      setTimeout(() => {
        wx.switchTab({ url: '/pages/index/index' });
      }, 1000);

    } catch (err) {
      wx.hideLoading();
      console.error(err);
      wx.showToast({ title: '发布失败', icon: 'none' });
    }
  }
});
```

-----

### 3\. 商品详情页修复 (Detail)

**解决问题：** 轮播图不显示、买卖双方逻辑混乱 (Issue 7, 10)

**文件：** `pages/detail/detail.js`

```javascript
const app = getApp();
const api = require('../../utils/api.js');

Page({
  data: {
    product: {},
    isSeller: false,
    swiperImages: [] // 专门用于轮播图的数据
  },

  onLoad: function (options) {
    this.loadProduct(options.id);
  },

  loadProduct: async function (id) {
    try {
      const res = await api.getProductDetail(id);
      const product = res; // 假设 api.js 已经处理了 res.data

      // 1. 处理图片路径（拼接完整 URL）
      const processedImages = (product.images || []).map(img => {
        return img.startsWith('http') ? img : app.globalData.baseUrl + img;
      });

      // 2. 身份判断逻辑（强制类型转换）
      const user = wx.getStorageSync('user');
      const currentUserId = user ? String(user.id) : '';
      const sellerId = String(product.seller_id);

      this.setData({
        product: product,
        swiperImages: processedImages,
        isSeller: (currentUserId === sellerId)
      });

    } catch (err) {
      console.error(err);
    }
  },

  // 修复：联系卖家
  contactSeller: function () {
    // 检查是否登录
    if (!wx.getStorageSync('token')) {
        return wx.navigateTo({ url: '/pages/login/login' });
    }
    // 创建或获取聊天室 ID 后跳转
    api.createChatRoom(this.data.product.id).then(res => {
        wx.navigateTo({
            url: `/pages/message/room?roomId=${res.room_id}&title=${this.data.product.name}`
        });
    });
  }
});
```

**文件：** `pages/detail/detail.wxml` (轮播图部分)

```html
<swiper indicator-dots="true" autoplay="true" style="height: 300px;">
  <block wx:for="{{swiperImages}}" wx:key="*this">
    <swiper-item>
      <image src="{{item}}" mode="aspectFill" style="width:100%; height:100%;"></image>
    </swiper-item>
  </block>
</swiper>
```

-----

### 4\. 消息/聊天页修复 (Message)

**解决问题：** WebSocket 无法连接、死循环跳转 (Issue 8)

**文件：** `pages/message/room.js`

```javascript
const app = getApp();

Page({
  data: {
    messages: [],
    socketOpen: false
  },

  onLoad: function(options) {
    this.roomId = options.roomId;

    if (!wx.getStorageSync('token')) {
        wx.redirectTo({ url: '/pages/login/login' });
        return;
    }

    this.connectSocket();
    this.loadHistoryMessages();
  },

  onUnload: function() {
    if (this.socketOpen) {
      wx.closeSocket();
    }
  },

  connectSocket: function() {
    const token = wx.getStorageSync('token');
    // 修复 WS 地址：去除多余 /ws，添加 token 参数
    const wsUrl = `wss://okashii.top/ws/chat_room/${this.roomId}?token=${token}`;

    wx.connectSocket({
      url: wsUrl
    });

    wx.onSocketOpen(() => {
      console.log('WS Connected');
      this.setData({ socketOpen: true });
    });

    wx.onSocketMessage((res) => {
      const msg = JSON.parse(res.data);
      // 将新消息追加到列表
      const messages = this.data.messages;
      messages.push(msg);
      this.setData({ messages });
      // 滚动到底部
      this.scrollToBottom();
    });

    wx.onSocketError((err) => {
      console.error('WS Error', err);
      // 不要在这里写死循环跳转登录，仅提示网络错误
      wx.showToast({ title: '聊天连接断开', icon: 'none' });
    });

    wx.onSocketClose(() => {
        this.setData({ socketOpen: false });
    });
  },

  // 发送消息
  sendMessage: function(e) {
      const content = e.detail.value;
      if (this.data.socketOpen && content) {
          wx.sendSocketMessage({
              data: JSON.stringify({ message: content })
          });
      }
  }
});
```

-----

### 5\. 个人中心页修复 (Me)

**解决问题：** 页面跳转失效 (Issue 4)

**文件：** `pages/me/me.js`

我们需要区分页面类型。如果 `my-products` (我的发布) 是普通页面，用 `MapsTo`；如果用户未登录，先引导登录。

```javascript
Page({
  data: {
    userInfo: null
  },

  onShow: function() {
    // 每次显示页面时刷新用户信息
    this.setData({
      userInfo: wx.getStorageSync('user') || null
    });
  },

  handleLogin: function() {
    wx.navigateTo({ url: '/pages/login/login' });
  },

  // 导航通用处理器
  navigateToPage: function(e) {
    const target = e.currentTarget.dataset.url;

    if (!this.data.userInfo) {
      return wx.showToast({ title: '请先登录', icon: 'none' });
    }

    wx.navigateTo({
      url: target,
      fail: (err) => {
        console.error('Navigation failed:', err);
        // 如果是 TabBar 页面，尝试 switchTab
        wx.switchTab({ url: target });
      }
    });
  },

  // 绑定 wxml 中的 bindtap
  goToMyProducts: function() {
    this.navigateToPage({ currentTarget: { dataset: { url: '/pages/my-products/my-products' } } });
  },

  goToMyOrders: function() {
    this.navigateToPage({ currentTarget: { dataset: { url: '/pages/orders/orders' } } });
  }
});
```

-----

### 6\. 订单列表/详情图片修复

**解决问题：** 订单商品图片不显示 (Issue 6)

在 **`pages/orders/orders.js`** 中，获取订单列表后，同样需要遍历数据，给 `image` 字段添加 `baseUrl` 前缀。

```javascript
// 在 setData 之前
const orders = res.data.map(order => {
    // 假设 order.product_image 是相对路径
    if (order.product_image && !order.product_image.startsWith('http')) {
        order.product_image = app.globalData.baseUrl + order.product_image;
    }
    return order;
});
this.setData({ orders });
```

-----

### 总结与执行建议

1.  **优先级**：先修改 `app.js` 和 `utils/api.js`。没有正确的 API 封装和 Base URL，其他页面都无法正常工作。
2.  **图片资源**：请检查 `miniprogram/images/` 目录下是否有缺失的图标（如默认头像），并在 WXML 中处理图片加载失败的 `binderror` 事件，显示默认图。
3.  **开发者工具配置**：在微信开发者工具中，点击右上角“详情” -\> “本地设置”，**勾选“不校验合法域名、web-view（业务域名）、TLS版本以及HTTPS证书”**。这在开发阶段非常重要，可以避免因 SSL 证书或域名配置未生效导致的连接错误。
4.  **真机调试**：WebSocket 在模拟器和真机上表现可能不一致，确保手机和电脑在同一局域网（如果用局域网 IP），或确保 `okashii.top` 的 SSL 证书是有效的（Let's Encrypt 即可）。

请按照上述步骤更新代码，然后重新编译项目。如有新的报错，请提供具体的控制台 Error 信息。