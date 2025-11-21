// pages/profile/profile.js
const api = require('../../utils/api.js')
const app = getApp()

Page({
  data: {
    userInfo: {},
    stats: {
      selling: 0,
      sold: 0,
      favorites: 0
    },
    unreadCount: 0
  },

  onLoad() {
    this.loadUserData()
  },

  onShow() {
    this.loadUserData()
    
    if (this.getTabBar()) {
      this.getTabBar().setData({ selected: 4 })
    }

    // 获取未读消息数
    this.loadUnreadCount()
  },

  onPullDownRefresh() {
    this.loadUserData().then(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadUserData() {
    if (!app.globalData.isLogin) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      })
      setTimeout(() => {
        wx.navigateTo({
          url: '/pages/login/login'
        })
      }, 1500)
      return
    }

    try {
      const userInfo = wx.getStorageSync('userInfo')
      if (userInfo) {
        this.setData({ userInfo })
      }

      // 加载统计数据（从商品列表计算）
      const products = await api.getProductList({ user_id: userInfo.id })
      
      if (products && products.products) {
        const selling = products.products.filter(p => p.status === 'available').length
        const sold = products.products.filter(p => p.status === 'sold').length
        
        this.setData({
          stats: {
            selling: selling,
            sold: sold,
            favorites: 0  // 需要后端支持收藏功能
          }
        })
      }
    } catch (error) {
      console.error('加载用户数据失败:', error)
    }
  },

  async loadUnreadCount() {
    try {
      const data = await api.getUnreadCount()
      if (data.success) {
        this.setData({
          unreadCount: data.count || 0
        })
      }
    } catch (error) {
      console.error('加载未读消息数失败:', error)
    }
  },

  // 订阅消息
  async onSubscribe() {
    try {
      const result = await wx.requestSubscribeMessage({
        tmplIds: [
          // 这里需要替换为您的模板ID
          'xxxxxxxxxxxxxxx'  // 订单状态变更通知
        ]
      })

      console.log('订阅结果:', result)

      if (result.errMsg === 'requestSubscribeMessage:ok') {
        wx.showToast({
          title: '订阅成功',
          icon: 'success'
        })
      }
    } catch (error) {
      console.error('订阅失败:', error)
      if (error.errMsg !== 'requestSubscribeMessage:fail user reject') {
        wx.showToast({
          title: '订阅失败',
          icon: 'none'
        })
      }
    }
  },

  // 退出登录
  onLogout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          app.logout()
        }
      }
    })
  },

  // 分享小程序
  onShareAppMessage() {
    return {
      title: '小区二手市场 - 邻里闲置交易平台',
      path: '/pages/index/index',
      imageUrl: '/images/share-banner.jpg'
    }
  },

  onShareTimeline() {
    return {
      title: '小区二手市场 - 发现你身边的闲置好物',
      query: '',
      imageUrl: '/images/share-banner.jpg'
    }
  }
})
