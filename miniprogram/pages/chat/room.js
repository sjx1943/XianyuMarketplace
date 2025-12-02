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
    this.hasSentInitialMessage = false
    this.loadChatHistory().then((historyCount) => {
      // 加载完历史消息后，检查是否需要发送初始消息
      // 传入历史消息数量，避免setData异步问题
      this.checkAndSendInitialMessage(historyCount)
    })
    this.connectWebSocket()
    this.startPolling()
    this.markAsRead()
  },
  
  // 检查并发送关于商品的初始消息
  // historyCount: loadChatHistory返回的历史消息数量
  async checkAndSendInitialMessage(historyCount) {
    const { productId, friendId } = this.data
    
    // 如果没有商品ID或已处理过，不发送初始消息
    if (!productId || this.hasSentInitialMessage) return
    
    // 使用本地存储记录已发送初始消息的商品，防止重复发送
    // 注意：使用productId_friendId组合作为key，确保每个商品只发一次初始消息
    // 即使与该卖家有其他商品的聊天记录，也能为新商品发送初始消息
    const sentKey = `initial_msg_sent_${productId}_${friendId}`
    const alreadySent = wx.getStorageSync(sentKey)
    if (alreadySent) {
      console.log(`已向该卖家发送过【商品${productId}】的初始消息`)
      this.hasSentInitialMessage = true
      return
    }
    
    try {
      // 获取商品详情
      const productData = await api.getProductDetail(productId)
      const product = productData.product || productData
      
      if (!product || !product.name) {
        console.log('商品信息不完整，不发送初始消息')
        return
      }
      
      // 构建初始消息
      const initialMessage = `我对【${product.name}】感兴趣，想了解更多信息～`
      
      // 在发送前标记已处理，防止重复发送
      this.hasSentInitialMessage = true
      
      // 发送初始消息
      const data = await api.sendMessage({
        friend_id: friendId,
        message: initialMessage,
        type: 'text'
      })
      
      if (data.success) {
        // 记录已向该卖家发送过初始消息，防止以后再次发送
        wx.setStorageSync(sentKey, Date.now())
        
        const messageData = data.data || {}
        this.addMessage({
          id: data.message_id || messageData.id,
          sender_id: this.data.currentUserId,
          from_user_id: this.data.currentUserId,
          content: initialMessage,
          message: initialMessage,
          type: 'text',
          time: messageData.time || '刚刚',
          timestamp: messageData.timestamp || Date.now()
        })
        console.log('初始消息发送成功')
      } else {
        // 发送失败，重置标记，允许重试
        this.hasSentInitialMessage = false
      }
    } catch (error) {
      console.error('发送初始消息失败:', error)
      // 发送失败，重置标记，允许重试
      this.hasSentInitialMessage = false
    }
  },

  onUnload() {
    this.stopPolling()
    this.closeWebSocket()
    this.closeAllWebSocketListeners()
  },

  onHide() {
    this.stopPolling()
    this.closeWebSocket()
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
      
      // 使用_id或id作为主键（与WebSocket和addMessage保持一致）
      const currentMsgIds = new Set(this.data.messages.map(m => m._id || m.id))
      let hasNewMessages = false
      
      const allBackendMessages = data.messages.map(msg => {
        // 后端返回UTC时间戳，需要加8小时转换为北京时间
        let timestamp
        if (msg.timestamp_ms && typeof msg.timestamp_ms === 'number') {
          timestamp = msg.timestamp_ms + 8 * 60 * 60 * 1000
        } else {
          timestamp = this.parseTimestamp(msg.timestamp)
        }
        // 前端统一计算time字段（确保显示UTC+8北京时间）
        const date = new Date(timestamp)
        const hours = String(date.getUTCHours()).padStart(2, '0')
        const mins = String(date.getUTCMinutes()).padStart(2, '0')
        const time = `${hours}:${mins}`
        return {
          ...msg,
          _id: msg._id || msg.id,
          timestamp: timestamp,
          time: time
        }
      })
      
      const newMessages = allBackendMessages.filter(msg => {
        const msgId = msg._id || msg.id
        const isNew = !currentMsgIds.has(msgId)
        if (isNew) hasNewMessages = true
        return isNew
      })
      
      if (hasNewMessages && newMessages.length > 0) {
        const mergedMessages = [...this.data.messages, ...newMessages]
        
        const deduplicatedMessages = []
        const seenIds = new Set()
        for (const m of mergedMessages) {
          const msgId = m._id || m.id
          if (!seenIds.has(msgId)) {
            seenIds.add(msgId)
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
            // 优先使用_id作为唯一标识（与WebSocket和addMessage保持一致）
            const msgId = msg._id || msg.id || `${msg.from_user_id}_${msg.timestamp_ms || msg.timestamp}`
            this.messageIdSet.add(msgId)
            // 后端返回UTC时间戳，需要加8小时转换为北京时间
            let timestamp
            if (msg.timestamp_ms && typeof msg.timestamp_ms === 'number') {
              timestamp = msg.timestamp_ms + 8 * 60 * 60 * 1000
            } else {
              timestamp = this.parseTimestamp(msg.timestamp)
            }
            // 前端统一计算time字段（确保显示UTC+8北京时间）
            const date = new Date(timestamp)
            const hours = String(date.getUTCHours()).padStart(2, '0')
            const mins = String(date.getUTCMinutes()).padStart(2, '0')
            const time = `${hours}:${mins}`
            return {
              ...msg,
              _id: msg._id || msg.id,
              timestamp: timestamp,
              time: time
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
        
        // 返回历史消息数量
        return messages.length
      } else {
        this.setData({ loading: false })
        return 0
      }
    } catch (error) {
      console.error('加载聊天记录失败:', error)
      this.setData({ loading: false })
      return 0
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
    
    // 先关闭之前的连接，避免快速切换时出现"未完成的操作"错误
    this.closeWebSocket()
    
    // 延迟建立新连接，确保旧连接完全关闭
    setTimeout(() => {
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
          if (!this.data || !this.data.friendId) return
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
    }, 100)
  },

  closeWebSocket() {
    try {
      wx.closeSocket({
        code: 1000,
        reason: '用户离开页面',
        success: () => {
          console.log('WebSocket已主动关闭')
        },
        fail: (err) => {
          // 连接不存在或已关闭，不报错
          if (err.errMsg && err.errMsg.indexOf('已关闭') === -1) {
            console.warn('WebSocket关闭失败:', err)
          }
        }
      })
    } catch (err) {
      console.warn('WebSocket关闭异常:', err)
    }
  },

  closeAllWebSocketListeners() {
    // 注：WebSocket事件监听器在页面卸载时会自动清理
    // 不需要手动调用off方法（某些WeChat版本不支持）
    console.log('WebSocket监听器将在页面卸载时自动清理')
  },

  parseTimestamp(ts) {
    if (!ts) return Date.now()
    if (typeof ts === 'number') return ts
    if (typeof ts === 'string') {
      // 后端返回UTC时间字符串 (格式: "2025-12-02 01:39:00")
      // 需要转换为UTC+8北京时间的毫秒时间戳
      try {
        // 解析为UTC时间
        const date = new Date(ts.replace(' ', 'T') + 'Z')
        // 加8小时转换为北京时间
        return date.getTime() + 8 * 60 * 60 * 1000
      } catch (e) {
        return Date.now()
      }
    }
    return Date.now()
  },

  addMessage(message) {
    // 后端返回UTC时间戳，需要转换为UTC+8北京时间
    if (message.timestamp_ms && typeof message.timestamp_ms === 'number') {
      // 后端返回UTC毫秒时间戳，加8小时转换为北京时间
      message.timestamp = message.timestamp_ms + 8 * 60 * 60 * 1000
    } else {
      // 字符串格式由parseTimestamp处理（已包含UTC+8转换）
      message.timestamp = this.parseTimestamp(message.timestamp)
    }
    
    // 前端统一计算time字段（确保显示UTC+8北京时间）
    const date = new Date(message.timestamp)
    const hours = String(date.getUTCHours()).padStart(2, '0')
    const mins = String(date.getUTCMinutes()).padStart(2, '0')
    message.time = `${hours}:${mins}`
    
    // 优先使用MongoDB的_id或id作为唯一标识（关键修复：防止重复）
    const msgId = message._id || message.id || `${message.from_user_id || message.sender_id}_${message.timestamp}`
    
    if (this.messageIdSet.has(msgId)) {
      console.log('消息已存在(Set检查)，跳过:', msgId)
      return
    }
    
    // 二次检查：相同内容+发送者+时间范围（1秒内）的消息
    const existingMsgs = this.data.messages
    const msgContent = message.content || message.message
    const msgSender = message.sender_id || message.from_user_id
    for (const m of existingMsgs) {
      const existingContent = m.content || m.message
      const existingSender = m.sender_id || m.from_user_id
      const timeDiff = Math.abs((m.timestamp || 0) - (message.timestamp || 0))
      if (existingContent === msgContent && existingSender === msgSender && timeDiff < 1000) {
        console.log('消息已存在(内容+发送者+时间范围检查)，跳过')
        return
      }
    }
    
    this.messageIdSet.add(msgId)
    
    // 统一消息格式
    message.content = message.content || message.message
    message.sender_id = message.sender_id || message.from_user_id
    
    const updatedMessages = [
      ...this.data.messages,
      message
    ].sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0))
    
    console.log('添加消息:', message.content, 'ID:', msgId, '时间戳:', message.timestamp, '总计:', updatedMessages.length, '条')
    
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
      
      // 标记已读后，刷新消息未读计数
      app.getUnreadChatCount()
    } catch (error) {
      console.error('标记已读失败:', error)
    }
  },

  onMessageLongPress(e) {
    const { messageId, index } = e.currentTarget.dataset
    const message = this.data.messages[index]
    
    if (!message || !messageId) return
    
    wx.showActionSheet({
      itemList: ['删除消息', '取消'],
      success: (res) => {
        if (res.tapIndex === 0) {
          this.deleteMessage(messageId, index)
        }
      },
      fail: () => {
        // 用户取消，不处理
      }
    })
  },

  async deleteMessage(messageId, index) {
    try {
      wx.showLoading({ title: '删除中...' })
      
      const result = await api.deleteMessage(messageId, this.data.friendId)
      
      wx.hideLoading()
      
      if (result.status === 'success') {
        const messages = this.data.messages
        messages.splice(index, 1)
        this.setData({ messages })
        
        wx.showToast({
          title: '消息已删除',
          icon: 'success',
          duration: 1500
        })
      } else {
        wx.showToast({
          title: result.error || '删除失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.hideLoading()
      console.error('删除消息失败:', error)
      wx.showToast({
        title: '删除失败',
        icon: 'none'
      })
    }
  }
})
