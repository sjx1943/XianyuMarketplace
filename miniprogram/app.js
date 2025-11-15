// app.js
App({
  onLaunch() {
    // 展示本地存储能力
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)

    // 检查登录状态
    this.checkLoginStatus()
  },

  onShow() {
    // 应用被重新激活时检查登录状态
    this.checkLoginStatus()
  },

  globalData: {
    userInfo: null,
    apiBase: 'https://your-domain.com/api',  // 替换为你的API域名
    wsBase: 'wss://your-domain.com/ws',      // 替换为你的WebSocket域名
    isLogin: false,
    currentUserId: null,
    unreadCount: 0
  },

  // 检查登录状态
  checkLoginStatus() {
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    
    if (token && userInfo) {
      this.globalData.isLogin = true
      this.globalData.userInfo = userInfo
      this.globalData.currentUserId = userInfo.id
      
      // 验证token有效性
      this.validateToken()
    } else {
      this.globalData.isLogin = false
      this.globalData.userInfo = null
      this.globalData.currentUserId = null
    }
  },

  // 验证token有效性
  validateToken() {
    wx.request({
      url: this.globalData.apiBase + '/validate_token',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      success: (res) => {
        if (res.statusCode !== 200) {
          this.logout()
        }
      },
      fail: () => {
        this.logout()
      }
    })
  },

  // 登录
  login(userInfo) {
    this.globalData.isLogin = true
    this.globalData.userInfo = userInfo
    this.globalData.currentUserId = userInfo.id
    
    wx.setStorageSync('userInfo', userInfo)
    
    // 获取未读消息数量
    this.getUnreadCount()
  },

  // 登出
  logout() {
    this.globalData.isLogin = false
    this.globalData.userInfo = null
    this.globalData.currentUserId = null
    this.globalData.unreadCount = 0
    
    wx.removeStorageSync('token')
    wx.removeStorageSync('userInfo')
    
    // 跳转到登录页
    wx.reLaunch({
      url: '/pages/login/login'
    })
  },

  // 获取未读消息数量
  getUnreadCount() {
    if (!this.globalData.isLogin) return
    
    wx.request({
      url: this.globalData.apiBase + '/unread_count',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.success) {
          this.globalData.unreadCount = res.data.count
          
          // 设置tabBar徽标
          if (res.data.count > 0) {
            wx.setTabBarBadge({
              index: 2, // 消息tab的索引
              text: res.data.count.toString()
            })
          } else {
            wx.removeTabBarBadge({
              index: 2
            })
          }
        }
      }
    })
  },

  // 更新未读消息数量
  updateUnreadCount(count) {
    this.globalData.unreadCount = count
    
    if (count > 0) {
      wx.setTabBarBadge({
        index: 2,
        text: count.toString()
      })
    } else {
      wx.removeTabBarBadge({
        index: 2
      })
    }
  },

  // 通用请求方法
  request(options) {
    const token = wx.getStorageSync('token')
    
    return new Promise((resolve, reject) => {
      wx.request({
        url: this.globalData.apiBase + options.url,
        method: options.method || 'GET',
        data: options.data || {},
        header: {
          'content-type': 'application/json',
          'Authorization': token ? 'Bearer ' + token : '',
          ...options.header
        },
        success: (res) => {
          if (res.statusCode === 401) {
            // token过期，重新登录
            this.logout()
            reject(new Error('登录已过期'))
          } else {
            resolve(res)
          }
        },
        fail: (err) => {
          reject(err)
        }
      })
    })
  },

  // 显示loading
  showLoading(title = '加载中...') {
    wx.showLoading({
      title: title,
      mask: true
    })
  },

  // 隐藏loading
  hideLoading() {
    wx.hideLoading()
  },

  // 显示提示
  showToast(title, icon = 'none') {
    wx.showToast({
      title: title,
      icon: icon,
      duration: 2000
    })
  }
})
