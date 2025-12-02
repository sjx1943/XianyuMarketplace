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
  touchStartX: 0,
  touchEndX: 0,
  slideDeleteVisibleId: null,

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
    if (!timeStr) return ''
    
    try {
      // 后端返回UTC时间字符串 "YYYY-MM-DD HH:MM"，转换为UTC+8北京时间
      if (typeof timeStr === 'string' && timeStr.includes('-')) {
        // 解析为UTC时间
        const date = new Date(timeStr.replace(' ', 'T') + 'Z')
        if (isNaN(date.getTime())) return timeStr
        
        // 转换为北京时间（UTC+8）
        const beijingDate = new Date(date.getTime() + 8 * 60 * 60 * 1000)
        const year = beijingDate.getUTCFullYear()
        const month = String(beijingDate.getUTCMonth() + 1).padStart(2, '0')
        const day = String(beijingDate.getUTCDate()).padStart(2, '0')
        const hours = String(beijingDate.getUTCHours()).padStart(2, '0')
        const mins = String(beijingDate.getUTCMinutes()).padStart(2, '0')
        
        return `${year}-${month}-${day} ${hours}:${mins}`
      }
    } catch (e) {
      console.warn('时间格式转换失败:', timeStr, e)
    }
    
    return timeStr
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

      // 更新消息tab的未读徽章
      const unreadCount = chatList.reduce((sum, chat) => sum + (chat.unread_count || 0), 0)
      if (app.updateUnreadChatCount) {
        app.updateUnreadChatCount(unreadCount)
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

      // 更新消息tab的未读徽章
      const unreadCount = chatList.reduce((sum, chat) => sum + (chat.unread_count || 0), 0)
      if (app.updateUnreadChatCount) {
        app.updateUnreadChatCount(unreadCount)
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

  onTouchStart(e) {
    this.touchStartX = e.touches[0].clientX
    // 点击删除按钮前，先隐藏其他打开的项目
    if (this.slideDeleteVisibleId !== null && 
        this.slideDeleteVisibleId !== (e.currentTarget.dataset.friendId)) {
      const index = this.data.chatList.findIndex(chat => 
        (chat.friend_id || chat.id) === this.slideDeleteVisibleId
      )
      if (index !== -1) {
        const chatList = this.data.chatList
        chatList[index].slideDeleteVisible = false
        this.setData({ chatList })
      }
    }
  },

  onTouchEnd(e) {
    this.touchEndX = e.changedTouches[0].clientX
    const distance = this.touchStartX - this.touchEndX
    
    // 左滑超过80rpx（约40px）才触发
    if (distance > 80) {
      const friendId = e.currentTarget.dataset.friendId
      const index = this.data.chatList.findIndex(chat => 
        (chat.friend_id || chat.id) === friendId
      )
      
      if (index !== -1) {
        const chatList = this.data.chatList
        chatList[index].slideDeleteVisible = true
        this.setData({ chatList })
        this.slideDeleteVisibleId = friendId
      }
    } else if (distance < -80) {
      // 右滑隐藏删除按钮
      const friendId = e.currentTarget.dataset.friendId
      const index = this.data.chatList.findIndex(chat => 
        (chat.friend_id || chat.id) === friendId
      )
      
      if (index !== -1) {
        const chatList = this.data.chatList
        chatList[index].slideDeleteVisible = false
        this.setData({ chatList })
        this.slideDeleteVisibleId = null
      }
    }
  },

  deleteChatRecord(e) {
    const friendId = e.currentTarget.dataset.friendId
    const index = parseInt(e.currentTarget.dataset.index)
    
    if (index < 0 || index >= this.data.chatList.length) return
    
    const friend = this.data.chatList[index]
    wx.showModal({
      title: '删除聊天记录',
      content: `确定要删除与 ${friend.username || friend.name || '未知用户'} 的所有聊天记录吗？`,
      success: (res) => {
        if (res.confirm) {
          this.clearChatHistory(friendId, index)
        } else if (res.cancel) {
          // 隐藏删除按钮
          const chatList = this.data.chatList
          chatList[index].slideDeleteVisible = false
          this.setData({ chatList })
          this.slideDeleteVisibleId = null
        }
      }
    })
  },

  async clearChatHistory(friendId, index) {
    try {
      await api.request({
        url: `/api/miniprogram/clear_chat/${friendId}`,
        method: 'DELETE'
      })
      
      wx.showToast({
        title: '聊天记录已删除',
        icon: 'success'
      })
      
      // 从列表中移除
      const chatList = this.data.chatList
      chatList.splice(index, 1)
      this.setData({ chatList })
      this.slideDeleteVisibleId = null
    } catch (error) {
      console.error('删除聊天记录失败:', error)
      wx.showToast({
        title: '删除失败，请重试',
        icon: 'none'
      })
    }
  },

  onTouchMove(e) {
    // 防止页面滚动干扰滑动
  },

  openChat(e) {
    // 如果删除按钮显示中，先隐藏删除按钮，不打开聊天
    const index = parseInt(e.currentTarget.dataset.index)
    if (index >= 0 && this.data.chatList[index] && this.data.chatList[index].slideDeleteVisible) {
      const chatList = this.data.chatList
      chatList[index].slideDeleteVisible = false
      this.setData({ chatList })
      this.slideDeleteVisibleId = null
      return
    }
    
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
