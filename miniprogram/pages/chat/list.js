// pages/chat/list.js
const api = require('../../utils/api.js')
const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')
const app = getApp()

// API 请求超时时间（毫秒）
const API_TIMEOUT = 5000
// 轮询间隔（毫秒）- 从 10 秒改为 20 秒减少请求频率
const POLL_INTERVAL = 20000

Page({
  data: {
    chatList: [],
    broadcasts: [],
    loading: false,  // 初始值改为 false，避免页面打开时显示加载中
    broadcastLoading: false
  },

  pollTimer: null,
  touchStartX: 0,
  touchEndX: 0,
  slideDeleteVisibleId: null,
  // 防止重复加载
  isLoading: false,
  isSilentLoading: false,  // 单独的静默加载标记
  lastLoadTime: 0,

  onLoad() {
    this.checkLoginAndLoad()
  },

  onShow() {
    // 智能加载：距离上次加载超过 2 秒才重新加载
    const now = Date.now()
    if (now - this.lastLoadTime > 2000) {
      this.checkLoginAndLoad()
    }
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
    }, POLL_INTERVAL)
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
    // 防止与正在进行的加载冲突（包括静默加载和正常加载）
    if (this.isLoading || this.isSilentLoading) return
    this.isSilentLoading = true
    
    try {
      // 添加超时机制
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('请求超时')), API_TIMEOUT)
      )
      
      const data = await Promise.race([
        api.getChatList(),
        timeoutPromise
      ])
      
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
    } finally {
      this.isSilentLoading = false
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

    // 并行加载聊天列表和广播，但使用 Promise.all 优化
    Promise.all([
      this.loadChatList(),
      this.loadBroadcasts()
    ]).catch(err => console.error('加载数据失败:', err))
  },

  async loadChatList() {
    // 防止重复加载
    if (this.isLoading) return
    this.isLoading = true
    this.lastLoadTime = Date.now()
    
    try {
      this.setData({ loading: true })

      // 添加超时机制
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('请求超时')), API_TIMEOUT)
      )
      
      const data = await Promise.race([
        api.getChatList(),
        timeoutPromise
      ])

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
      // 超时提示
      if (error.message === '请求超时') {
        wx.showToast({
          title: '加载超时，请下拉刷新',
          icon: 'none'
        })
      }
    } finally {
      this.isLoading = false
    }
  },

  async loadBroadcasts() {
    try {
      this.setData({ broadcastLoading: true })

      // 添加超时机制
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('请求超时')), API_TIMEOUT)
      )
      
      const data = await Promise.race([
        api.request({
          url: '/api/miniprogram/broadcasts',
          method: 'GET'
        }),
        timeoutPromise
      ])

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
