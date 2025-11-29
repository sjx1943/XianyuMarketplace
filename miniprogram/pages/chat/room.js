// pages/chat/room.js
const api = require('../../utils/api.js')
const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')
const app = getApp()

Page({
  data: {
    friendId: null,
    productId: null,
    orderId: null,
    messages: [],
    broadcasts: [],
    inputText: '',
    scrollToView: '',
    currentUserId: null,
    myAvatar: '',
    friendAvatar: '',
    loading: false,
    socketConnected: false
  },

  onLoad(options) {
    // 处理参数：驼峰或蛇形都支持
    const friendId = options.friendId || options.friend_id
    const productId = options.productId || options.product_id
    const orderId = options.orderId || options.order_id
    
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
      currentUserId: userInfo.id,
      myAvatar: userInfo.wechat_avatar ? getImageUrl(userInfo.wechat_avatar) : getDefaultAvatarUrl()
    })

    this.loadBroadcasts()
    this.loadChatHistory()
    this.connectWebSocket()
    
    // 标记消息为已读
    this.markAsRead()
  },

  onUnload() {
    // 不关闭WebSocket - 保持连接持久化，支持实时消息接收
    // 只在app.onHide时关闭，确保应用级别的连接管理
  },

  // 加载系统广播
  async loadBroadcasts() {
    try {
      const data = await api.request({
        url: '/api/miniprogram/broadcasts',
        method: 'GET'
      })

      if (data && data.broadcasts) {
        this.setData({
          broadcasts: data.broadcasts || []
        })
      }
    } catch (error) {
      console.error('加载广播失败:', error)
    }
  },

  // 加载聊天记录
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
        // 处理消息，确保头像URL正确
        const messages = (data.messages || []).map(msg => ({
          ...msg,
          // 如果时间为空，使用当前时间
          time: msg.time || new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
        }))
        
        this.setData({
          messages: messages,
          friendAvatar: data.friend?.avatar ? getImageUrl(data.friend.avatar) : getDefaultAvatarUrl(),
          loading: false
        })

        // 滚动到底部
        this.scrollToBottom()
      } else {
        this.setData({ loading: false })
      }
    } catch (error) {
      console.error('加载聊天记录失败:', error)
      this.setData({ loading: false })
    }
  },

  // 连接WebSocket
  connectWebSocket() {
    const config = require('../../utils/config.js')
    
    // 后端WebSocket路由是 /ws/chat_room，需要传递user_id参数
    const userId = this.data.currentUserId
    if (!userId) {
      console.error('WebSocket连接失败: 用户ID不存在')
      return
    }
    
    // 构建WebSocket URL，包含user_id参数
    const socketUrl = `${config.WS_BASE}/chat_room?user_id=${userId}`
    console.log('WebSocket连接地址:', socketUrl)
    
    wx.connectSocket({
      url: socketUrl,
      success: () => {
        console.log('WebSocket连接中...')
      },
      fail: (err) => {
        console.error('WebSocket连接失败:', err)
        // 不显示Toast，因为可能是平台限制（如微信开发者工具）
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
        
        // 只接收来自当前好友的消息
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

  // 关闭WebSocket
  closeWebSocket() {
    wx.closeSocket()
  },

  // 添加消息到列表
  addMessage(message) {
    const messages = this.data.messages
    // 确保消息有时间戳
    const now = new Date()
    message.time = message.time || now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    message.timestamp = message.timestamp || now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    messages.push(message)
    this.setData({ messages })
    this.scrollToBottom()
  },

  // 头像加载失败处理
  onAvatarError(e) {
    console.warn('头像加载失败:', e)
  },

  // 输入变化
  onInputChange(e) {
    this.setData({
      inputText: e.detail.value
    })
  },

  // 发送消息
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
        // 添加消息到列表
        this.addMessage({
          id: data.message_id,
          sender_id: this.data.currentUserId,
          content: content,
          type: 'text',
          time: '刚刚'
        })

        // 清空输入框
        this.setData({
          inputText: ''
        })

        // 通过WebSocket发送
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

  // 选择图片
  chooseImage() {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFilePaths[0]
        this.sendImageMessage(tempFilePath)
      }
    })
  },

  // 发送图片消息
  async sendImageMessage(filePath) {
    try {
      wx.showLoading({ title: '发送中...' })

      // 上传图片
      const uploadData = await api.uploadFile({
        url: '/api/upload/image',
        filePath: filePath,
        name: 'image'
      })

      const imageUrl = uploadData.url || uploadData.path

      // 发送图片消息
      const data = await api.sendMessage({
        receiver_id: this.data.friendId,
        content: imageUrl,
        type: 'image'
      })

      wx.hideLoading()

      if (data.success) {
        this.addMessage({
          id: data.message_id,
          sender_id: this.data.currentUserId,
          content: imageUrl,
          type: 'image',
          time: '刚刚'
        })
      } else {
        wx.showToast({
          title: '发送失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.hideLoading()
      console.error('发送图片失败:', error)
      wx.showToast({
        title: '发送失败',
        icon: 'none'
      })
    }
  },

  // 预览图片
  previewImage(e) {
    const { url } = e.currentTarget.dataset
    const images = this.data.messages
      .filter(msg => msg.type === 'image')
      .map(msg => msg.content)

    wx.previewImage({
      current: url,
      urls: images
    })
  },

  // 查看商品
  viewProduct(e) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/product/detail?id=${id}`
    })
  },

  // 滚动到底部
  scrollToBottom() {
    this.setData({
      scrollToView: 'bottom-anchor'
    })
  },

  // 标记为已读
  async markAsRead() {
    try {
      await api.markMessagesRead(this.data.friendId)
      
      // 更新全局未读数
      const unreadData = await api.getUnreadCount()
      if (unreadData.success) {
        app.updateUnreadCount(unreadData.count || 0)
      }
    } catch (error) {
      console.error('标记已读失败:', error)
    }
  },

  // 点击广播进入商品详情
  onBroadcastTap(e) {
    const { productId } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/product/detail?id=${productId}`
    })
  }
})
