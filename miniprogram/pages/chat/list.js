// pages/chat/list.js
const api = require('../../utils/api.js')
const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')
const app = getApp()

Page({
  data: {
    chatList: [],
    broadcasts: [],
    loading: true,
    broadcastLoading: false
  },

  pollTimer: null,

  onLoad() {
    this.checkLoginAndLoad()
  },

  onShow() {
    this.checkLoginAndLoad()
    this.startPolling()
    
    if (this.getTabBar()) {
      this.getTabBar().setData({
        selected: 1
      })
    }
  },

  onHide() {
    this.stopPolling()
  },

  onUnload() {
    this.stopPolling()
  },

  startPolling() {
    this.stopPolling()
    this.pollTimer = setInterval(() => {
      this.loadChatListSilent()
    }, 10000)
  },

  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer)
      this.pollTimer = null
    }
  },

  formatTime(timeStr) {
    // 后端已返回UTC+8北京时间，直接返回无需转换
    return timeStr || ''
  },

  async loadChatListSilent() {
    try {
      const data = await api.getChatList()
      const rawChatList = Array.isArray(data) ? data : (data.conversations || data.chats || [])
      const chatList = rawChatList.map(chat => ({
        ...chat,
        avatar: chat.avatar ? getImageUrl(chat.avatar) : getDefaultAvatarUrl(),
        last_time: this.formatTime(chat.last_time || chat.last_message_time)
      }))

      this.setData({ chatList: chatList })

      if (chatList.length > 0) {
        const unreadCount = chatList.reduce((sum, chat) => sum + (chat.unread_count || 0), 0)
        if (app.updateUnreadCount) {
          app.updateUnreadCount(unreadCount)
        }
      }
    } catch (error) {
      console.error('静默刷新聊天列表失败:', error)
    }
  },

  onPullDownRefresh() {
    Promise.all([
      this.loadChatList(),
      this.loadBroadcasts()
    ]).then(() => {
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
    this.loadBroadcasts()
  },

  async loadChatList() {
    try {
      this.setData({ loading: true })

      const data = await api.getChatList()

      const rawChatList = Array.isArray(data) ? data : (data.conversations || data.chats || [])
      const chatList = rawChatList.map(chat => ({
        ...chat,
        avatar: chat.avatar ? getImageUrl(chat.avatar) : getDefaultAvatarUrl(),
        last_time: this.formatTime(chat.last_time || chat.last_message_time)
      }))

      this.setData({
        chatList: chatList,
        loading: false
      })

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

  async loadBroadcasts() {
    try {
      this.setData({ broadcastLoading: true })

      const data = await api.request({
        url: '/api/miniprogram/broadcasts',
        method: 'GET'
      })

      if (data && data.broadcasts) {
        this.setData({
          broadcasts: data.broadcasts || [],
          broadcastLoading: false
        })
      } else {
        this.setData({ broadcastLoading: false })
      }
    } catch (error) {
      console.error('加载广播失败:', error)
      this.setData({ broadcastLoading: false })
    }
  },

  openChat(e) {
    const { friend } = e.currentTarget.dataset
    const roomNumber = friend.room_number || '未设置'
    const friendName = friend.username || friend.name || ''
    wx.navigateTo({
      url: `/pages/chat/room?friendId=${friend.friend_id || friend.id}&roomNumber=${encodeURIComponent(roomNumber)}&friendName=${encodeURIComponent(friendName)}`
    })
  },

  onBroadcastTap(e) {
    const { productId } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/product/detail?id=${productId}`
    })
  },

  goToProductList() {
    wx.switchTab({
      url: '/pages/product/list'
    })
  }
})
