// app.js - 小程序主应用文件
App({
  onLaunch() {
    // 初始化日志
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)

    // 初始化网络状态监听
    this.initNetworkListener()
    
    // 检查登录状态
    this.checkLoginStatus()
    
    // 初始化其他配置
    this.initConfig()
  },

  onShow() {
    // 应用被重新激活时检查登录状态
    this.checkLoginStatus()
    
    // 刷新未读消息计数
    this.getUnreadCount()
  },

  globalData: {
    userInfo: null,
    apiBase: this.getApiBase(),
    wsBase: this.getWsBase(),
    isLogin: false,
    currentUserId: null,
    unreadCount: 0,
    networkConnected: true,
    networkType: 'unknown',
    retryCount: 0,
    maxRetries: 3,
    requestTimeout: 10000
  },

  // 获取API基础URL（根据环境配置）
  getApiBase() {
    // 使用 config.js 中的配置
    const configModule = require('./utils/config.js')
    return configModule.API_BASE
  },

  // 获取WebSocket基础URL
  getWsBase() {
    // 使用 config.js 中的配置
    const configModule = require('./utils/config.js')
    return configModule.WS_BASE
  },

  // 初始化配置
  initConfig() {
    // 检查小程序更新
    if (wx.canIUse('getUpdateManager')) {
      const updateManager = wx.getUpdateManager()
      
      updateManager.onCheckForUpdate((res) => {
        if (res.hasUpdate) {
          updateManager.onUpdateReady(() => {
            wx.showModal({
              title: '更新提示',
              content: '新版本已下载，是否立即重启应用？',
              success: (res) => {
                if (res.confirm) {
                  updateManager.applyUpdate()
                }
              }
            })
          })

          updateManager.onUpdateFailed(() => {
            wx.showToast({
              title: '新版本下载失败',
              icon: 'none'
            })
          })
        }
      })
    }
  },

  // 初始化网络状态监听
  initNetworkListener() {
    wx.onNetworkStatusChange((res) => {
      this.globalData.networkConnected = res.isConnected
      this.globalData.networkType = res.networkType
      
      if (!res.isConnected) {
        this.showToast('网络连接已断开，请检查网络设置', 'none')
      } else {
        // 网络恢复时，重新验证token
        this.checkLoginStatus()
      }
    })

    // 获取初始网络状态
    wx.getNetworkType({
      success: (res) => {
        this.globalData.networkConnected = res.networkType !== 'none'
        this.globalData.networkType = res.networkType
      }
    })
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

  // 验证token有效性（带重试机制）
  validateToken(retry = 0) {
    if (!this.globalData.isLogin) return

    wx.request({
      url: this.globalData.apiBase + '/miniprogram/user/info',
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token'),
        'Content-Type': 'application/json'
      },
      timeout: this.globalData.requestTimeout,
      success: (res) => {
        if (res.statusCode === 200) {
          // token有效
          if (res.data && res.data.id) {
            this.globalData.userInfo = res.data
            wx.setStorageSync('userInfo', res.data)
          }
        } else if (res.statusCode === 401 || res.statusCode === 403) {
          // token过期或无效
          this.logout()
        }
      },
      fail: (err) => {
        // 网络错误时的重试机制
        if (retry < this.globalData.maxRetries) {
          setTimeout(() => {
            this.validateToken(retry + 1)
          }, 1000 * (retry + 1))
        }
      }
    })
  },

  // 登录
  login(userInfo, token) {
    this.globalData.isLogin = true
    this.globalData.userInfo = userInfo
    this.globalData.currentUserId = userInfo.id
    
    // 保存用户信息和token
    wx.setStorageSync('userInfo', userInfo)
    if (token) {
      wx.setStorageSync('token', token)
    }
    
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
    
    // 显示提示后跳转到登录页
    this.showToast('登录已过期，请重新登录', 'none')
    setTimeout(() => {
      wx.reLaunch({
        url: '/pages/login/login'
      })
    }, 1500)
  },

  // 获取未读消息数量
  getUnreadCount() {
    if (!this.globalData.isLogin) return
    
    wx.request({
      url: this.globalData.apiBase + '/unread_count',
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token'),
        'Content-Type': 'application/json'
      },
      timeout: this.globalData.requestTimeout,
      success: (res) => {
        if (res.statusCode === 200) {
          const count = res.data.count || res.data.unread_count || 0
          this.updateUnreadCount(count)
        }
      },
      fail: (err) => {
        console.error('获取未读消息失败:', err)
      }
    })
  },

  // 更新未读消息数量
  updateUnreadCount(count) {
    this.globalData.unreadCount = count
    
    if (count > 0) {
      try {
        wx.setTabBarBadge({
          index: 2, // 消息tab的索引
          text: count > 99 ? '99+' : count.toString()
        })
      } catch (err) {
        console.error('设置tabBar徽标失败:', err)
      }
    } else {
      try {
        wx.removeTabBarBadge({
          index: 2
        })
      } catch (err) {
        console.error('移除tabBar徽标失败:', err)
      }
    }
  },

  // 通用请求方法（与web端保持一致）
  request(options) {
    const token = wx.getStorageSync('token')
    
    return new Promise((resolve, reject) => {
      // 检查网络连接
      if (!this.globalData.networkConnected) {
        this.showToast('网络连接断开，请检查网络设置', 'none')
        reject(new Error('网络连接断开'))
        return
      }

      const defaultHeader = {
        'Content-Type': 'application/json',
        'User-Agent': 'MiniProgram'
      }

      if (token) {
        defaultHeader['Authorization'] = 'Bearer ' + token
      }

      wx.request({
        url: this.globalData.apiBase + (options.url.startsWith('/') ? options.url : '/' + options.url),
        method: options.method || 'GET',
        data: options.data || {},
        header: {
          ...defaultHeader,
          ...options.header
        },
        timeout: options.timeout || this.globalData.requestTimeout,
        success: (res) => {
          if (res.statusCode === 401 || res.statusCode === 403) {
            // token过期
            this.logout()
            reject(new Error('登录已过期'))
          } else if (res.statusCode === 200) {
            resolve(res.data || res)
          } else {
            const errorMsg = res.data?.message || res.data?.error || '请求失败'
            this.showToast(errorMsg, 'none')
            reject(new Error(errorMsg))
          }
        },
        fail: (err) => {
          console.error('请求失败:', err)
          this.showToast('网络请求失败，请重试', 'none')
          reject(err)
        }
      })
    })
  },

  // 文件上传
  uploadFile(options) {
    const token = wx.getStorageSync('token')
    
    return new Promise((resolve, reject) => {
      if (!this.globalData.networkConnected) {
        this.showToast('网络连接断开', 'none')
        reject(new Error('网络连接断开'))
        return
      }

      const header = {
        'Authorization': token ? 'Bearer ' + token : ''
      }

      wx.uploadFile({
        url: this.globalData.apiBase + (options.url.startsWith('/') ? options.url : '/' + options.url),
        filePath: options.filePath,
        name: options.name || 'file',
        formData: options.formData || {},
        header: header,
        timeout: options.timeout || 30000,
        success: (res) => {
          if (res.statusCode === 200) {
            try {
              const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
              resolve(data)
            } catch (e) {
              resolve(res.data)
            }
          } else if (res.statusCode === 401 || res.statusCode === 403) {
            this.logout()
            reject(new Error('登录已过期'))
          } else {
            const errorMsg = res.data?.message || '上传失败'
            this.showToast(errorMsg, 'none')
            reject(new Error(errorMsg))
          }
        },
        fail: (err) => {
          console.error('上传失败:', err)
          this.showToast('上传失败，请重试', 'none')
          reject(err)
        }
      })
    })
  },

  // 显示加载提示
  showLoading(title = '加载中...') {
    wx.showLoading({
      title: title,
      mask: true
    })
  },

  // 隐藏加载提示
  hideLoading() {
    wx.hideLoading()
  },

  // 显示消息提示
  showToast(title, icon = 'none') {
    wx.showToast({
      title: title,
      icon: icon,
      duration: 2000
    })
  },

  // 显示模态对话框
  showModal(options) {
    return new Promise((resolve, reject) => {
      wx.showModal({
        title: options.title || '提示',
        content: options.content || '',
        confirmText: options.confirmText || '确定',
        cancelText: options.cancelText || '取消',
        success: (res) => {
          resolve(res)
        },
        fail: (err) => {
          reject(err)
        }
      })
    })
  },

  // 页面路由导航
  navigateTo(url) {
    return wx.navigateTo({
      url: url
    })
  },

  navigateBack(delta = 1) {
    return wx.navigateBack({
      delta: delta
    })
  },

  reLaunch(url) {
    return wx.reLaunch({
      url: url
    })
  },

  // 获取用户信息
  getUserInfo() {
    return this.globalData.userInfo
  },

  // 检查用户是否已登录
  isUserLogin() {
    return this.globalData.isLogin
  },

  // 获取当前用户ID
  getCurrentUserId() {
    return this.globalData.currentUserId
  },

  // 检查网络连接
  isNetworkConnected() {
    return this.globalData.networkConnected
  }
})
