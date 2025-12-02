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

    this.loadChatHistory()
    this.connectWebSocket()
    this.markAsRead()
  },

  onUnload() {
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
        // 根据时间戳排序消息（按时间升序）
        const messages = (data.messages || [])
          .map(msg => ({
            ...msg,
            timestamp: msg.timestamp || new Date(msg.created_at).getTime() || Date.now(),
            time: msg.time || new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
          }))
          .sort((a, b) => a.timestamp - b.timestamp)
        
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
        
        if (message.sender_id === this.data.friendId) {
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

  addMessage(message) {
    const now = new Date()
    message.timestamp = message.timestamp || Date.now()
    message.time = message.time || now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    
    // 创建新消息数组并排序，确保UI更新
    const updatedMessages = [
      ...this.data.messages,
      message
    ].sort((a, b) => {
      const timeA = a.timestamp || 0
      const timeB = b.timestamp || 0
      return timeA - timeB
    })
    
    this.setData({ messages: updatedMessages }, () => {
      console.log('消息已更新，总计:', updatedMessages.length, '条')
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

    try {
      const data = await api.sendMessage({
        friend_id: this.data.friendId,
        message: content,
        type: 'text'
      })

      if (data.success) {
        this.addMessage({
          id: data.message_id,
          sender_id: this.data.currentUserId,
          content: content,
          type: 'text',
          time: '刚刚'
        })

        this.setData({
          inputText: ''
        })

        if (this.data.socketConnected) {
          wx.sendSocketMessage({
            data: JSON.stringify({
              type: 'text',
              receiver_id: this.data.friendId,
              content: content
            })
          })
        }
      } else {
        wx.showToast({
          title: data.error || '发送失败',
          icon: 'none'
        })
      }
    } catch (error) {
      console.error('发送消息失败:', error)
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
