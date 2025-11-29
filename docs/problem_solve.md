针对您反馈的 7 个具体问题（编号4-10），通过分析错误日志和常见的小程序开发逻辑，以下是逐一的修复方案和代码实现。

请确保您在 `miniprogram` 目录下操作。

-----

### 4\. 个人中心页跳转异常 (修复 `pages/me/me.js`)

**问题分析：** 小程序中跳转到 TabBar 页面必须使用 `wx.switchTab`，跳转普通页面使用 `wx.navigateTo`。如果路径写错或方法用错，点击无反应。

**修复代码：**
打开 `miniprogram/pages/me/me.js`，找到对应的跳转函数，修改如下：

```javascript
Page({
  // ... 其他代码

  // 跳转到我的发布 (假设这是一个普通页面)
  goToMyProducts: function() {
    wx.navigateTo({
      url: '/pages/my-products/my-products',
      fail: (err) => { console.error("跳转失败，请检查路径是否正确", err); }
    });
  },

  // 跳转到我的订单 (假设这是一个普通页面)
  goToMyOrders: function() {
    wx.navigateTo({
      url: '/pages/orders/orders',
      fail: (err) => { console.error("跳转失败", err); }
    });
  },

  // 跳转到消息中心 (假设这是一个普通页面)
  goToMyMessages: function() {
    wx.navigateTo({
      url: '/pages/messages/messages',
      fail: (err) => { console.error("跳转失败", err); }
    });
  },

  // 注意：如果上述某个页面是在 app.json 的 tabBar.list 中定义的，
  // 必须将 wx.navigateTo 换成 wx.switchTab
});
```

-----

### 5\. 商品分类标签不匹配 & `undefined` 报错 (修复 `pages/index/index.js` 和 `pages/publish/publish.js`)

**问题分析：** 前端显示的文本（"电子数码"）与后端数据库存储的值（"数码产品"）不一致。发布时通过索引取值，如果数组不对应会导致 `undefined`。

**修复步骤：**

1.  **统一分类列表：** 确保发布页和后端接收的枚举值一致。
2.  **修复发布页 (`pages/publish/publish.js`)：**

<!-- end list -->

```javascript
Page({
  data: {
    // 确保这里的列表与后端数据库的实际 tag 字符串完全一致
    categories: ['数码产品', '生活用品', '图书教材', '美妆护肤', '票务娱乐', '其他'], 
    categoryIndex: -1,
    form: {
      category: '' 
    }
  },

  // 分类选择器改变事件
  onCategoryChange: function(e) {
    const index = e.detail.value;
    const selectedCategory = this.data.categories[index];

    this.setData({
      categoryIndex: index,
      'form.category': selectedCategory // 直接存入字符串，避免 undefined
    });
  }
});
```

3.  **修复首页筛选 (`pages/index/index.js`)：** 确保点击标签传给后端的参数正确。

-----

### 6 & 7. 图片无法显示/轮播图异常 (全局修复)

**问题分析：** 后端返回的图片路径通常是相对路径（如 `/static/img/1.jpg`），小程序 `<image>` 标签不支持相对路径，必须拼接完整的 `https://okashii.top` 域名。

**修复方案：**

1.  **在 `app.js` 中定义 baseUrl：**

    ```javascript
    globalData: {
      baseUrl: 'https://okashii.top'
    }
    ```

2.  **在页面中处理图片路径 (以 `pages/detail/detail.js` 为例)：**
    在获取数据后，遍历处理图片 URL。

    ```javascript
    const app = getApp();

    Page({
      // ...
      onLoad: function(options) {
        // 请求详情数据成功后的回调
        // 假设 res.data 是商品对象
        let product = res.data;

        // 处理主图
        if (product.image && !product.image.startsWith('http')) {
            product.image = app.globalData.baseUrl + product.image;
        }

        // 处理轮播图 (假设 images 是数组)
        if (product.images && product.images.length > 0) {
            product.images = product.images.map(img => {
                return img.startsWith('http') ? img : app.globalData.baseUrl + img;
            });
        }

        this.setData({ product: product });
      }
    });
    ```

3.  **在 WXML 中确保轮播图代码正确 (`pages/detail/detail.wxml`)：**

    ```html
    <swiper indicator-dots="true" autoplay="true" interval="3000" duration="500">
      <block wx:for="{{product.images}}" wx:key="*this">
        <swiper-item>
          <image src="{{item}}" mode="aspectFill" class="slide-image"/>
        </swiper-item>
      </block>
    </swiper>
    ```

-----

### 8\. WebSocket 连接失败 & 403 权限错误 (修复 `utils/api.js` 和 `pages/message/room.js`)

**问题分析：**

1.  **403 错误：** `mark_messages_read` 接口调用时未携带 Token。
2.  **WebSocket URL 错误：** 日志显示 `wss://okashii.top/ws/ws/chat_room`，多了一个 `/ws`。
3.  **登录跳转死循环：** 这里的跳转逻辑可能是因为 API 拦截器判断 403 后跳转错误。

**修复步骤 1：修复 API 请求头 (`miniprogram/utils/api.js`)**

```javascript
const baseUrl = 'https://okashii.top/api'; 

function request(url, method, data) {
  const token = wx.getStorageSync('token'); // 获取 Token

  return new Promise((resolve, reject) => {
    wx.request({
      url: baseUrl + url,
      method: method,
      data: data,
      header: {
        'content-type': 'application/json',
        // 关键修复：添加 Authorization 头
        'Authorization': token ? `Bearer ${token}` : '' 
      },
      success: (res) => {
        if (res.statusCode === 401 || res.statusCode === 403) {
            // Token 失效，跳转登录页
            wx.navigateTo({ url: '/pages/login/login' });
            reject('未登录');
        } else {
            resolve(res.data);
        }
      },
      fail: (err) => reject(err)
    });
  });
}

// 确保 markMessagesRead 使用这个 request 函数
export function markMessagesRead(roomId) {
    return request('/mark_messages_read', 'POST', { room_id: roomId });
}
```

**修复步骤 2：修复 WebSocket 连接 (`miniprogram/pages/message/room.js`)**

```javascript
const app = getApp();

Page({
  data: {
    socketOpen: false,
    messages: []
  },

  onLoad: function(options) {
    // 检查登录状态
    const token = wx.getStorageSync('token');
    if (!token) {
        wx.redirectTo({ url: '/pages/login/login' });
        return;
    }

    this.connectWebSocket(options.roomId);
  },

  connectWebSocket: function(roomId) {
    const token = wx.getStorageSync('token');
    // 修复 URL：去掉多余的 /ws，并把 token 作为 query 参数传递（如果是后端要求）
    // 或者部分后端要求 socket 鉴权在 header，但在小程序 wx.connectSocket 一般只能传 url
    // 假设后端路径是 /ws/chat_room/{roomId}
    const wsUrl = `wss://okashii.top/ws/chat_room/${roomId}?token=${token}`;

    this.socketTask = wx.connectSocket({
      url: wsUrl,
      success: () => console.log('WebSocket 连接请求发送成功')
    });

    this.socketTask.onOpen(() => {
      console.log('WebSocket 已连接');
      this.setData({ socketOpen: true });
    });

    this.socketTask.onError((res) => {
      console.error('WebSocket 错误', res);
    });

    this.socketTask.onMessage((res) => {
      const msg = JSON.parse(res.data);
      // 处理新消息逻辑
    });
  }
});
```

-----

### 9\. 发布商品多图上传报错 (修复 `pages/publish/publish.js`)

**问题分析：** `wx.uploadFile` 一次只能上传一个文件。如果用户选择了多张图，需要循环调用。

**修复代码：**

```javascript
// 在提交表单的函数中
submitForm: async function() {
    const { tempImages, form } = this.data; // tempImages 是 wx.chooseImage 返回的本地路径数组

    if (tempImages.length === 0) {
        wx.showToast({ title: '请至少上传一张图片', icon: 'none' });
        return;
    }

    wx.showLoading({ title: '发布中...' });

    try {
        // 1. 循环上传所有图片
        const uploadPromises = tempImages.map(filePath => {
            return new Promise((resolve, reject) => {
                wx.uploadFile({
                    url: 'https://okashii.top/api/upload_image', // 确保后端上传接口正确
                    filePath: filePath,
                    name: 'file', // 后端接收的文件字段名
                    header: {
                        'Authorization': `Bearer ${wx.getStorageSync('token')}`
                    },
                    success: (res) => {
                        const data = JSON.parse(res.data);
                        // 假设后端返回 { url: '/static/xxx.jpg' }
                        resolve(data.url); 
                    },
                    fail: reject
                });
            });
        });

        const uploadedImageUrls = await Promise.all(uploadPromises);

        // 2. 提交商品信息（包含图片URL数组）
        const productData = {
            ...form,
            images: uploadedImageUrls // 将服务器返回的图片路径数组发给后端
        };

        // 调用发布 API
        // ... request('/products', 'POST', productData) ...

        wx.hideLoading();
        wx.showToast({ title: '发布成功' });
        wx.navigateBack();

    } catch (err) {
        wx.hideLoading();
        console.error(err);
        wx.showToast({ title: '发布失败', icon: 'none' });
    }
}
```

-----

### 10\. 买家/卖家身份判断混乱 (修复 `pages/detail/detail.js`)

**问题分析：** JS 中的弱类型比较 (`==`) 或类型转换缺失导致 ID 匹配失败。例如 `currentUser.id` 是数字 1，而 `product.seller_id` 是字符串 "1"。

**修复代码：**

打开 `pages/detail/detail.js`，在设置数据前强制转换类型：

```javascript
onLoad: function(options) {
    const user = wx.getStorageSync('user'); // 获取当前登录用户
    const currentUserId = user ? String(user.id) : null; // 强制转为字符串

    // 获取商品详情
    api.getProductDetail(options.id).then(res => {
        const product = res.data;
        const sellerId = String(product.seller_id); // 强制转为字符串

        const isSeller = (currentUserId === sellerId);

        this.setData({
            product: product,
            isSeller: isSeller, // 在 WXML 中使用这个布尔值判断
            currentUserId: currentUserId
        });
    });
}
```

**修改对应的 WXML (`pages/detail/detail.wxml`)：**

```html
<view class="action-bar">
    <block wx:if="{{isSeller}}">
        <button bindtap="deleteProduct">下架商品</button>
        </block>

    <block wx:else>
        <button bindtap="buyNow">立即购买</button>
        <button bindtap="contactSeller">联系卖家</button>
    </block>
</view>
```

**订单页面的逻辑修正 (`pages/order-detail/order-detail.wxml`)：**

```html
<view wx:if="{{isSeller && order.status === 'paid'}}">
   <button bindtap="shipOrder">确认发货</button>
</view>

<view wx:if="{{!isSeller && order.status === 'paid'}}">
   <button bindtap="cancelOrder">取消订单</button> </view>
```

-----

### 总结下一步操作

1.  请优先修复 **Issue 8 (API Token & WebSocket)**，因为这是通信的基础。
2.  修改 **`app.js`** 添加 `baseUrl`，并修复 **Issue 6 & 7** 的图片路径拼接，这能立即使界面恢复正常。
3.  按顺序实施其余修复。
4.  修改后请重新编译小程序，并在微信开发者工具中清除一次全部缓存（Storage 和 Auth）重新登录测试。