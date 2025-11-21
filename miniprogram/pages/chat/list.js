// pages/chat/list.js
const api = require('../../utils/api.js')
const app = getApp()

Page({
  data: {
    chatList: [],
    loading: true
  },

  onLoad() {
    this.checkLoginAndLoad()
  },

  onShow() {
    this.checkLoginAndLoad()
    
    // 设置tabBar选中状态
    if (this.getTabBar()) {
      this.getTabBar().setData({
        selected: 2
      })
    }
  },

  onPullDownRefresh() {
    this.loadChatList().then(() => {
      wx.stopPullDownRefresh()
    })
  },

  checkLoginAndLoad() {
    if (!app.globalData.isLogin) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      })
      setTimeout(() => {
        wx.reLaunch({
          url: '/pages/login/login'
        })
      }, 1500)
      return
    }

    this.loadChatList()
  },

  async loadChatList() {
    try {
      this.setData({ loading: true })

      const data = await api.getChatList()

      if (data.success) {
        this.setData({
          chatList: data.chats || [],
          loading: false
        })

        // 更新未读消息数
        const unreadCount = data.chats.reduce((sum, chat) => sum + (chat.unread_count || 0), 0)
        app.updateUnreadCount(unreadCount)
      } else {
        this.setData({ loading: false })
      }
    } catch (error) {
      console.error('加载聊天列表失败:', error)
      this.setData({ loading: false })
    }
  },

  openChat(e) {
    const { friend } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/chat/room?friendId=${friend.id}`
    })
  },

  goToProductList() {
    wx.switchTab({
      url: '/pages/product/list'
    })
  }
})
