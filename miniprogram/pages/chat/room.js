// pages/chat/room.js - 聊天室页面（只显示与特定卖家的聊天）
const api = require('../../utils/api.js')
const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')
const app = getApp()

Page({
  data: {
    friendId: null,
    productId: null,
    orderId: null,
    friendRoomNumber: '',
    friendName: '',
    messages: [],
    inputText: '',
    scrollToView: '',
    currentUserId: null,
    myAvatar: '',
    friendAvatar: '',
    loading: false,
    socketConnected: false
  },

  pollTimer: null,
  lastMessageTimestamp: 0,
  messageIdSet: new Set(),

  onLoad(options) {
    const friendId = options.friendId || options.friend_id
    const productId = options.productId || options.product_id
    const orderId = options.orderId || options.order_id
    const roomNumber = options.roomNumber ? decodeURIComponent(options.roomNumber) : ''
    const friendName = options.friendName ? decodeURIComponent(options.friendName) : ''
    
    if (!friendId) {
      wx.showToast({
        title: '参数错误',
        icon: 'none'
      })
      setTimeout(() => wx.navigateBack(), 1500)
      return
    }

    const userInfo = wx.getStorageSync('userInfo')
    if (!userInfo) {
      wx.navigateTo({
        url: '/pages/login/login'
      })
      return
    }

    this.setData({
      friendId: parseInt(friendId),
      productId: productId ? parseInt(productId) : null,
      orderId: orderId ? parseInt(orderId) : null,
      friendRoomNumber: roomNumber,
      friendName: friendName,
      currentUserId: userInfo.id,
      myAvatar: userInfo.wechat_avatar ? getImageUrl(userInfo.wechat_avatar) : getDefaultAvatarUrl()
    })

    if (roomNumber) {
      wx.setNavigationBarTitle({
        title: roomNumber
      })
    }

    this.messageIdSet = new Set()
    this.lastMessageTimestamp = 0
    this.loadChatHistory()
    this.connectWebSocket()
    this.startPolling()
    this.markAsRead()
  },

  onUnload() {
    this.stopPolling()
    this.closeWebSocket()
  },

  onHide() {
    this.stopPolling()
  },

  onShow() {
    this.startPolling()
    this.pollNewMessages()
  },

  startPolling() {
    this.stopPolling()
    this.pollTimer = setInterval(() => {
      this.pollNewMessages()
    }, 10000)
  },

  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer)
      this.pollTimer = null
    }
  },

  async pollNewMessages() {
    if (this.data.loading || !this.data.messages || this.data.messages.length === 0) return
    
    try {
      const data = await api.request({
        url: '/api/miniprogram/messages',
        method: 'GET',
        data: {
          friend_id: this.data.friendId,
          limit: 100
        }
      })

      if (!data || !data.messages) return
      
      const currentMsgIds = new Set(this.data.messages.map(m => m.id))
      let hasNewMessages = false
      
      const allBackendMessages = data.messages.map(msg => {
        const timestamp = this.parseTimestamp(msg.timestamp)
        return {
          ...msg,
          timestamp: timestamp,
          time: msg.time || ''
        }
      })
      
      const newMessages = allBackendMessages.filter(msg => {
        const isNew = !currentMsgIds.has(msg.id)
        if (isNew) hasNewMessages = true
        return isNew
      })
      
      if (hasNewMessages && newMessages.length > 0) {
        const mergedMessages = [...this.data.messages, ...newMessages]
        
        const deduplicatedMessages = []
        const seenIds = new Set()
        for (const m of mergedMessages) {
          if (!seenIds.has(m.id)) {
            seenIds.add(m.id)
            deduplicatedMessages.push(m)
          }
        }
        
        const sortedMessages = deduplicatedMessages.sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0))
        
        console.log('轮询新消息数:', newMessages.length, '总计:', sortedMessages.length)
        
        this.setData({ messages: sortedMessages }, () => {
          this.scrollToBottom()
        })
        
        this.markAsRead()
      }
    } catch (error) {
      console.error('轮询新消息失败:', error)
    }
  },

  async loadChatHistory() {
    try {
      this.setData({ loading: true })

      const data = await api.request({
        url: '/api/miniprogram/messages',
        method: 'GET',
        data: {
          friend_id: this.data.friendId,
          limit: 50
        }
      })

      if (data && data.messages) {
        this.messageIdSet = new Set()
        
        const messages = (data.messages || [])
          .map(msg => {
            const msgId = msg.id || `${msg.from_user_id}_${msg.timestamp}`
            this.messageIdSet.add(msgId)
            return {
              ...msg,
              timestamp: this.parseTimestamp(msg.timestamp),
              time: msg.time || ''
            }
          })
          .sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0))
        
        if (messages.length > 0) {
          this.lastMessageTimestamp = messages[messages.length - 1].timestamp
        }
        
        const friendInfo = data.friend || {}
        const friendRoomNumber = friendInfo.room_number || this.data.friendRoomNumber || '未设置'
        
        this.setData({
          messages: messages,
          friendAvatar: friendInfo.avatar ? getImageUrl(friendInfo.avatar) : getDefaultAvatarUrl(),
          friendRoomNumber: friendRoomNumber,
          friendName: friendInfo.username || this.data.friendName || '',
          loading: false
        })

        if (friendRoomNumber && friendRoomNumber !== '未设置') {
          wx.setNavigationBarTitle({
            title: friendRoomNumber
          })
        }

        this.scrollToBottom()
      } else {
        this.setData({ loading: false })
      }
    } catch (error) {
      console.error('加载聊天记录失败:', error)
      this.setData({ loading: false })
    }
  },

  connectWebSocket() {
    const config = require('../../utils/config.js')
    const token = wx.getStorageSync('token')
    
    const friendId = this.data.friendId
    if (!friendId || !token) {
      console.error('WebSocket连接失败: 好友ID或Token不存在')
      return
    }
    
    const socketUrl = `${config.WS_BASE}/chat_room/${friendId}?token=${encodeURIComponent(token)}`
    console.log('WebSocket连接地址:', socketUrl)
    
    wx.connectSocket({
      url: socketUrl,
      success: () => {
        console.log('WebSocket连接中...')
      },
      fail: (err) => {
        console.error('WebSocket连接失败:', err)
        console.log('WebSocket连接可能受平台限制，聊天功能将使用HTTP轮询')
      }
    })

    wx.onSocketOpen(() => {
      console.log('WebSocket已连接')
      this.setData({ socketConnected: true })
    })

    wx.onSocketMessage((res) => {
      try {
        const message = JSON.parse(res.data)
        console.log('收到WebSocket消息:', message)
        
        // 判断消息是否来自当前聊天对象（兼容两种字段名）
        const fromUserId = message.sender_id || message.from_user_id
        if (fromUserId === this.data.friendId) {
          // 确保消息格式统一
          message.sender_id = fromUserId
          message.content = message.content || message.message || ''
          this.addMessage(message)
          this.markAsRead()
        }
      } catch (error) {
        console.error('解析消息失败:', error)
      }
    })

    wx.onSocketError((err) => {
      console.error('WebSocket错误:', err)
      this.setData({ socketConnected: false })
    })

    wx.onSocketClose(() => {
      console.log('WebSocket已关闭')
      this.setData({ socketConnected: false })
    })
  },

  closeWebSocket() {
    wx.closeSocket()
  },

  parseTimestamp(ts) {
    if (!ts) return Date.now()
    if (typeof ts === 'number') return ts
    if (typeof ts === 'string') {
      // 尝试解析字符串时间戳 (格式: "2025-12-02 09:39:00")
      try {
        const date = new Date(ts.replace(' ', 'T') + '+08:00')
        return date.getTime()
      } catch (e) {
        return Date.now()
      }
    }
    return Date.now()
  },

  addMessage(message) {
    message.timestamp = this.parseTimestamp(message.timestamp)
    
    if (!message.time) {
      const now = new Date()
      message.time = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
    
    const msgId = message.id || `${message.from_user_id || message.sender_id}_${message.timestamp}`
    
    if (this.messageIdSet.has(msgId)) {
      console.log('消息已存在(Set检查)，跳过:', msgId)
      return
    }
    
    const existingTimestamps = this.data.messages.map(m => m.timestamp)
    if (existingTimestamps.includes(message.timestamp)) {
      const sameTimestampMsgs = this.data.messages.filter(m => m.timestamp === message.timestamp)
      for (const m of sameTimestampMsgs) {
        if (m.content === message.content && m.sender_id === message.sender_id) {
          console.log('消息已存在(内容+时间戳检查)，跳过')
          return
        }
      }
    }
    
    this.messageIdSet.add(msgId)
    
    const updatedMessages = [
      ...this.data.messages,
      message
    ].sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0))
    
    console.log('添加消息:', message.content, '时间戳:', message.timestamp, '总计:', updatedMessages.length, '条')
    
    this.setData({ 
      messages: updatedMessages 
    }, () => {
      this.scrollToBottom()
    })
  },

  onAvatarError(e) {
    console.warn('头像加载失败:', e)
  },

  onInputChange(e) {
    this.setData({
      inputText: e.detail.value
    })
  },

  async sendMessage() {
    const content = this.data.inputText.trim()
    
    if (!content) {
      return
    }

    // 先清空输入框，提升用户体验
    this.setData({ inputText: '' })

    try {
      const data = await api.sendMessage({
        friend_id: this.data.friendId,
        message: content,
        type: 'text'
      })

      if (data.success) {
        // 使用后端返回的完整消息数据
        const messageData = data.data || {}
        this.addMessage({
          id: data.message_id || messageData.id,
          sender_id: this.data.currentUserId,
          from_user_id: this.data.currentUserId,
          content: content,
          message: content,
          type: 'text',
          time: messageData.time || '刚刚',
          timestamp: messageData.timestamp || Date.now()
        })
      } else {
        // 发送失败，恢复输入框内容
        this.setData({ inputText: content })
        wx.showToast({
          title: data.error || '发送失败',
          icon: 'none'
        })
      }
    } catch (error) {
      console.error('发送消息失败:', error)
      // 发送失败，恢复输入框内容
      this.setData({ inputText: content })
      wx.showToast({
        title: '发送失败',
        icon: 'none'
      })
    }
  },

  viewProduct(e) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/product/detail?id=${id}`
    })
  },

  scrollToBottom() {
    this.setData({
      scrollToView: 'bottom-anchor'
    })
  },

  async markAsRead() {
    try {
      await api.markMessagesRead(this.data.friendId)
      
      const unreadData = await api.getUnreadCount()
      if (unreadData.success) {
        app.updateUnreadCount(unreadData.count || 0)
      }
    } catch (error) {
      console.error('标记已读失败:', error)
    }
  }
})
