// pages/profile/profile.js
const api = require('../../utils/api.js')
const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')
const app = getApp()

Page({
  data: {
    userInfo: {},
    displayAvatar: '',
    stats: {
      selling: 0,
      sold: 0,
      favorites: 0
    },
    unreadCount: 0
  },

  onLoad() {
    // 先设置默认头像
    this.setData({
      displayAvatar: getDefaultAvatarUrl()
    })
    this.loadUserData()
  },

  onShow() {
    this.loadUserData()
    
    // 更新为第4个tabBar（0:物品, 1:消息, 2:订单, 3:我的）
    if (this.getTabBar()) {
      this.getTabBar().setData({ selected: 3 })
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
        // 处理头像URL - 始终显示正确的头像
        const avatarUrl = userInfo.wechat_avatar ? getImageUrl(userInfo.wechat_avatar) : getDefaultAvatarUrl()
        console.log('Setting avatar:', avatarUrl)
        this.setData({ 
          userInfo: userInfo,
          displayAvatar: avatarUrl
        })
      } else {
        // 没有userInfo时设置默认头像
        this.setData({
          displayAvatar: getDefaultAvatarUrl()
        })
        return
      }

      // 加载统计数据（调用后端API获取统计）
      const statsData = await api.getProductStats()
      if (statsData && statsData.success) {
        this.setData({
          stats: {
            selling: statsData.selling || 0,
            sold: statsData.sold || 0,
            favorites: statsData.favorites || 0
          }
        })
        console.log('✅ 已加载统计数据:', statsData)
      } else {
        console.warn('⚠️ 获取统计数据失败，使用默认值')
      }
    } catch (error) {
      console.error('加载用户数据失败:', error)
    }
  },

  async loadUnreadCount() {
    // 只在用户已登录时才加载未读计数
    if (!app.globalData.isLogin) {
      return
    }
    
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

  // 跳转到我的商品管理页面
  goToMyProducts() {
    wx.navigateTo({
      url: '/pages/product/my-list'
    })
  },

  // 跳转到我的订单页面（订单是tabBar页面）
  goToMyOrders() {
    wx.switchTab({
      url: '/pages/order/list'
    })
  },

  // 跳转到我的消息页面（消息是tabBar页面）
  goToMyMessages() {
    wx.switchTab({
      url: '/pages/chat/list'
    })
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

  // 跳转到编辑资料页
  goToEditProfile() {
    wx.navigateTo({
      url: '/pages/profile/edit'
    })
  },

  // 分享小程序
  onShareAppMessage() {
    return {
      title: '小区二手市场 - 邻里闲置交易平台',
      path: '/pages/product/list',
      imageUrl: getImageUrl('share-banner.jpg')
    }
  },

  onShareTimeline() {
    return {
      title: '小区二手市场 - 发现你身边的闲置好物',
      query: '',
      imageUrl: getImageUrl('share-banner.jpg')
    }
  }
})
