// API请求封装 - 修复版
const config = require('./config.js')

class API {
  constructor() {
    this.baseURL = config.API_BASE
    this.header = {
      'content-type': 'application/json'
    }
  }

  // 通用请求方法 - 核心修复：手动注入 Token，处理 401/403
  request(options) {
    const app = getApp()
    const token = wx.getStorageSync('token') || ''
    
    return new Promise((resolve, reject) => {
      if (options.loadingText !== false) {
        wx.showLoading({
          title: options.loadingText || '加载中...',
          mask: true
        })
      }

      wx.request({
        url: this.baseURL + options.url,
        method: options.method || 'GET',
        data: options.data || {},
        header: {
          'content-type': 'application/json',
          'Authorization': token ? 'Bearer ' + token : '',
          ...options.header
        },
        success: (res) => {
          if (options.loadingText !== false) {
            wx.hideLoading()
          }
          
          console.log('API 响应:', options.url, 'Status:', res.statusCode, 'Data:', res.data)
          
          if (res.statusCode === 200) {
            resolve(res.data)
          } else if (res.statusCode === 401) {
            // 只在明确是 401 未认证时才清除登录状态
            console.warn('API 401 未认证，清除登录状态:', options.url)
            wx.showToast({
              title: '登录已过期，请重新登录',
              icon: 'none'
            })
            
            wx.removeStorageSync('token')
            wx.removeStorageSync('userInfo')
            
            setTimeout(() => {
              wx.reLaunch({
                url: '/pages/login/login'
              })
            }, 1500)
            
            reject(new Error('未认证'))
          } else if (res.statusCode === 403) {
            // 403 禁止访问 - 通常是权限问题，而非登录问题
            console.warn('API 403 禁止访问:', options.url, res.data)
            const errorMsg = (res.data && res.data.error) || '无权限访问此资源'
            wx.showToast({
              title: errorMsg,
              icon: 'none'
            })
            reject(new Error(errorMsg))
          } else {
            const errorMsg = (res.data && res.data.message) || (res.data && res.data.error) || `请求失败 (${res.statusCode})`
            
            // 对于DELETE 404请求，静默处理（图片已被删除）
            if (res.statusCode === 404 && options.method === 'DELETE') {
              console.warn('API 请求返回404，图片已不存在:', options.url)
              reject(new Error(errorMsg))
            } else {
              console.error('API 请求失败:', options.url, res.statusCode, errorMsg)
              wx.showToast({
                title: errorMsg,
                icon: 'none'
              })
              reject(new Error(errorMsg))
            }
          }
        },
        fail: (err) => {
          if (options.loadingText !== false) {
            wx.hideLoading()
          }
          wx.showToast({
            title: '网络错误',
            icon: 'none'
          })
          reject(err)
        }
      })
    })
  }

  // 上传文件
  uploadFile(options) {
    const token = wx.getStorageSync('token') || ''
    
    return new Promise((resolve, reject) => {
      wx.showLoading({
        title: '上传中...',
        mask: true
      })

      wx.uploadFile({
        url: this.baseURL + options.url,
        filePath: options.filePath,
        name: options.name || 'file',
        formData: options.formData || {},
        header: {
          'Authorization': token ? 'Bearer ' + token : ''
        },
        success: (res) => {
          wx.hideLoading()
          
          if (res.statusCode === 200) {
            try {
              const data = JSON.parse(res.data)
              resolve(data)
            } catch (e) {
              resolve(res.data)
            }
          } else {
            wx.showToast({
              title: '上传失败',
              icon: 'none'
            })
            reject(new Error('上传失败'))
          }
        },
        fail: (err) => {
          wx.hideLoading()
          wx.showToast({
            title: '网络错误',
            icon: 'none'
          })
          reject(err)
        }
      })
    })
  }

  // ========== 用户相关API ==========
  
  // 微信登录
  wechatLogin(code) {
    return this.request({
      url: '/api/miniprogram/login',
      method: 'POST',
      data: { code },
      loadingText: '登录中...'
    })
  }

  // 设置房间号（小程序专用API）
  setRoomNumber(roomNumber) {
    return this.request({
      url: '/api/miniprogram/set_room_number',
      method: 'POST',
      data: { room_number: roomNumber }
    })
  }

  // 获取用户信息（小程序专用API）
  getUserInfo() {
    return this.request({
      url: '/api/miniprogram/user/info',
      method: 'GET'
    })
  }

  // 更新用户资料（小程序专用API）
  updateProfile(data) {
    return this.request({
      url: '/api/miniprogram/update_profile',
      method: 'POST',
      data: data
    })
  }

  // 更新用户信息（别名，与edit.js兼容）
  updateUserInfo(data) {
    return this.updateProfile(data)
  }

  // ========== 商品相关API ==========
  
  // 获取商品列表
  getProductList(params = {}) {
    return this.request({
      url: '/api/miniprogram/products',
      method: 'GET',
      data: params
    })
  }

  // 获取商品列表（别名）
  getProducts(params = {}) {
    return this.getProductList(params)
  }

  // 获取商品详情
  getProductDetail(id) {
    return this.request({
      url: `/api/miniprogram/product/${id}`,
      method: 'GET'
    })
  }

  // 发布商品
  publishProduct(data) {
    return this.request({
      url: '/api/miniprogram/product/upload',
      method: 'POST',
      data: data,
      loadingText: '发布中...'
    })
  }

  // 上传商品图片
  uploadProductImage(filePath) {
    return this.uploadFile({
      url: '/api/miniprogram/product/upload',
      filePath: filePath,
      name: 'images'
    })
  }

  // 删除商品
  deleteProduct(id) {
    return this.request({
      url: `/api/miniprogram/product/${id}/delete`,
      method: 'POST'
    })
  }

  // 删除商品图片
  deleteProductImage(productId, imageId) {
    return this.request({
      url: `/api/miniprogram/product/${productId}/image/${imageId}/delete`,
      method: 'POST'
    })
  }

  // 搜索商品
  searchProducts(keyword) {
    return this.request({
      url: '/api/search',
      method: 'GET',
      data: { q: keyword }
    })
  }

  // ========== 订单相关API ==========
  
  // 获取订单列表
  getOrderList(type = 'all') {
    return this.request({
      url: '/api/miniprogram/orders',
      method: 'GET',
      data: { type }
    })
  }

  // 获取订单详情
  getOrderDetail(orderId) {
    return this.request({
      url: `/api/miniprogram/order/${orderId}`,
      method: 'GET'
    })
  }

  // 创建订单
  createOrder(data) {
    return this.request({
      url: '/api/miniprogram/orders',
      method: 'POST',
      data: data,
      loadingText: '创建订单中...'
    })
  }

  // 确认收货（买家）
  confirmOrder(orderId) {
    return this.request({
      url: `/api/miniprogram/order/${orderId}/confirm`,
      method: 'POST'
    })
  }

  // 发货（卖家）
  shipOrder(orderId) {
    return this.request({
      url: `/api/miniprogram/order/${orderId}/ship`,
      method: 'POST'
    })
  }

  // 取消订单
  cancelOrder(orderId) {
    return this.request({
      url: `/api/miniprogram/order/${orderId}/cancel`,
      method: 'POST'
    })
  }

  // 获取未读订单数量（卖家）
  getUnreadOrdersCount() {
    return this.request({
      url: '/api/miniprogram/unread_count',
      method: 'GET'
    })
  }

  // 获取我的商品列表
  getMyProducts(status = 'all') {
    return this.request({
      url: '/api/miniprogram/my_products',
      method: 'GET',
      data: { status }
    })
  }

  // ========== 聊天相关API ==========
  
  // 获取未读消息数量
  getUnreadCount() {
    return this.request({
      url: '/api/miniprogram/unread_count',
      method: 'GET'
    })
  }

  // 获取聊天列表
  getChatList() {
    return this.request({
      url: '/api/miniprogram/chat/list',
      method: 'GET'
    })
  }

  // 发送消息
  sendMessage(data) {
    return this.request({
      url: '/api/miniprogram/messages',
      method: 'POST',
      data: data
    })
  }

  // 标记消息已读（使用小程序专用API）
  markMessagesRead(friendId) {
    return this.request({
      url: '/api/miniprogram/messages/mark_read',
      method: 'POST',
      data: { friend_id: friendId }
    })
  }

  // 删除消息
  deleteMessages(friendId) {
    return this.request({
      url: '/api/delete_messages',
      method: 'POST',
      data: { friend_id: friendId }
    })
  }

  // ========== 评论相关API ==========
  
  // 获取商品评论
  getComments(productId) {
    return this.request({
      url: `/api/comments/${productId}`,
      method: 'GET'
    })
  }

  // 发布评论
  postComment(data) {
    return this.request({
      url: '/api/comments',
      method: 'POST',
      data: data
    })
  }
}

module.exports = new API()
