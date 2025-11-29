// API请求封装
const config = require('./config.js')

class API {
  constructor() {
    this.baseURL = config.API_BASE
    this.header = {
      'content-type': 'application/json'
    }
  }

  // 通用请求方法
  request(options) {
    const app = getApp()
    const token = wx.getStorageSync('token') || ''
    
    return new Promise((resolve, reject) => {
      wx.showLoading({
        title: options.loadingText || '加载中...',
        mask: true
      })

      wx.request({
        url: this.baseURL + options.url,
        method: options.method || 'GET',
        data: options.data || {},
        header: {
          ...this.header,
          'Authorization': token ? 'Bearer ' + token : '',
          ...options.header
        },
        success: (res) => {
          wx.hideLoading()
          
          if (res.statusCode === 200) {
            resolve(res.data)
          } else if (res.statusCode === 401 || res.statusCode === 403) {
            // 未登录或会话过期
            wx.showToast({
              title: '请先登录',
              icon: 'none'
            })
            
            setTimeout(() => {
              wx.reLaunch({
                url: '/pages/login/login'
              })
            }, 1500)
            
            reject(new Error('未登录'))
          } else {
            wx.showToast({
              title: res.data.error || '请求失败',
              icon: 'none'
            })
            reject(new Error(res.data.error || '请求失败'))
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

  // ========== 商品相关API ==========
  
  // 获取商品列表
  getProductList(params = {}) {
    return this.request({
      url: '/product_list',
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
      url: `/product/detail/${id}`,
      method: 'GET'
    })
  }

  // 发布商品
  publishProduct(data) {
    return this.request({
      url: '/product/upload',
      method: 'POST',
      data: data,
      loadingText: '发布中...'
    })
  }

  // 上传商品图片
  uploadProductImage(filePath) {
    return this.uploadFile({
      url: '/product/upload',
      filePath: filePath,
      name: 'images'
    })
  }

  // 删除商品
  deleteProduct(id) {
    return this.request({
      url: `/api/product/${id}/delete`,
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
  getOrderList() {
    return this.request({
      url: '/orders',
      method: 'GET'
    })
  }

  // 创建订单
  createOrder(data) {
    return this.request({
      url: '/orders',
      method: 'POST',
      data: data,
      loadingText: '创建订单中...'
    })
  }

  // 确认订单（发货/收货）
  confirmOrder(orderId) {
    return this.request({
      url: `/api/order/${orderId}/confirm`,
      method: 'POST'
    })
  }

  // 取消订单
  cancelOrder(orderId) {
    return this.request({
      url: `/orders/${orderId}`,
      method: 'DELETE'
    })
  }

  // 获取未读订单数量（卖家）
  getUnreadOrdersCount() {
    return this.request({
      url: '/api/unread_orders_count',
      method: 'GET'
    })
  }

  // ========== 聊天相关API ==========
  
  // 获取未读消息数量
  getUnreadCount() {
    return this.request({
      url: '/api/unread_count',
      method: 'GET'
    })
  }

  // 获取聊天列表
  getChatList() {
    return this.request({
      url: '/api/messages',
      method: 'GET'
    })
  }

  // 发送消息
  sendMessage(data) {
    return this.request({
      url: '/api/send_message',
      method: 'POST',
      data: data
    })
  }

  // 标记消息已读
  markMessagesRead(friendId) {
    return this.request({
      url: '/api/mark_messages_read',
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
