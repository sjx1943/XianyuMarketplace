// pages/chat/list.js
const api = require('../../utils/api.js')
const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')
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

      // 后端返回的数据格式可能是数组或对象
      const rawChatList = Array.isArray(data) ? data : (data.conversations || data.chats || [])
      // 处理每个聊天的头像URL
      const chatList = rawChatList.map(chat => ({
        ...chat,
        avatar: chat.avatar ? getImageUrl(chat.avatar) : getDefaultAvatarUrl()
      }))

      this.setData({
        chatList: chatList,
        loading: false
      })

      // 更新未读消息数
      if (chatList.length > 0) {
        const unreadCount = chatList.reduce((sum, chat) => sum + (chat.unread_count || 0), 0)
        if (app.updateUnreadCount) {
          app.updateUnreadCount(unreadCount)
        }
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
