const api = require('../../utils/api.js')
const { subscribeOrderNotification } = require('../../utils/subscribeMessage.js')
const app = getApp()

// API 请求超时时间（毫秒）
const API_TIMEOUT = 5000

/**
 * 将UTC时间字符串转换为北京时间（UTC+8）显示
 * @param {string} utcTimeStr - UTC时间字符串，格式如 "2026-12-13 03:48:00"
 * @returns {string} 北京时间字符串，格式如 "2026-12-13 11:48"
 */
function formatToBeijingTime(utcTimeStr) {
  if (!utcTimeStr) return ''
  try {
    // 解析为UTC时间（添加Z后缀明确指定UTC）
    const utcDate = new Date(utcTimeStr.replace(' ', 'T') + 'Z')
    // 加8小时转换为北京时间
    const beijingTime = new Date(utcDate.getTime() + 8 * 60 * 60 * 1000)
    // 格式化输出
    const year = beijingTime.getUTCFullYear()
    const month = String(beijingTime.getUTCMonth() + 1).padStart(2, '0')
    const day = String(beijingTime.getUTCDate()).padStart(2, '0')
    const hours = String(beijingTime.getUTCHours()).padStart(2, '0')
    const mins = String(beijingTime.getUTCMinutes()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${mins}`
  } catch (e) {
    console.error('时间格式化失败:', e)
    return utcTimeStr
  }
}

Page({
  data: {
    order: null,
    loading: false,  // 初始值改为 false
    isBuyer: false,
    isSeller: false,
    currentUserId: null,
    countdownText: '',
    countdownTimer: null
  },

  onLoad(options) {
    if (options.id) {
      this.loadOrderDetail(options.id)
    }
  },

  onUnload() {
    // 清除定时器
    if (this.data.countdownTimer) {
      clearInterval(this.data.countdownTimer)
    }
  },

  loadOrderDetail(orderId) {
    this.setData({ loading: true })
    
    // 获取当前用户信息
    const userInfo = wx.getStorageSync('userInfo')
    const currentUserId = userInfo?.id
    this.setData({ currentUserId })
    
    // 添加超时机制
    const timeoutPromise = new Promise((_, reject) => 
      setTimeout(() => reject(new Error('请求超时')), API_TIMEOUT)
    )
    
    Promise.race([
      api.getOrderDetail(orderId),
      timeoutPromise
    ]).then(res => {
      const order = res.order || res
      const { getImageUrl } = require('../../utils/config.js')
      const productImage = order.product_image || order.image
      const imageUrl = productImage ? getImageUrl(productImage) : ''
      
      // 判断当前用户是买家还是卖家
      const isBuyer = currentUserId === order.user_id || currentUserId === order.buyer_id
      const isSeller = currentUserId === order.seller_id
      
      // 将所有时间字段转换为北京时间
      const formattedOrder = {
        ...order,
        created_at: formatToBeijingTime(order.created_at),
        shipped_at: formatToBeijingTime(order.shipped_at),
        completed_at: formatToBeijingTime(order.completed_at)
      }
      
      this.setData({
        order: formattedOrder,
        productImage: imageUrl,
        isBuyer: isBuyer,
        isSeller: isSeller,
        loading: false
      })
      
      // 如果订单是shipped状态且当前用户是买家，启动倒计时
      // 注意：使用原始的order.shipped_at（UTC时间）进行倒计时计算
      if (order.status === 'shipped' && isBuyer && order.shipped_at) {
        this.startAutoConfirmCountdown(orderId, order.shipped_at)
      }
    }).catch(err => {
      console.error('加载记录详情失败:', err)
      this.setData({ loading: false })
      // 超时提示
      if (err.message === '请求超时') {
        wx.showToast({
          title: '加载超时，请重试',
          icon: 'none'
        })
      } else {
        wx.showToast({
          title: '加载失败',
          icon: 'none'
        })
      }
    })
  },

  startAutoConfirmCountdown(orderId, shippedAtStr) {
    // 清除旧的定时器
    if (this.data.countdownTimer) {
      clearInterval(this.data.countdownTimer)
    }

    const updateCountdown = () => {
      const shippedAt = new Date(shippedAtStr)
      const now = new Date()
      const deadline = new Date(shippedAt.getTime() + 24 * 60 * 60 * 1000)
      const remainingMs = deadline.getTime() - now.getTime()

      if (remainingMs <= 0) {
        // 倒计时结束，自动确认收货
        clearInterval(this.data.countdownTimer)
        this.autoConfirmOrder(orderId)
      } else {
        // 计算剩余时间
        const hours = Math.floor(remainingMs / (60 * 60 * 1000))
        const minutes = Math.floor((remainingMs % (60 * 60 * 1000)) / (60 * 1000))
        const seconds = Math.floor((remainingMs % (60 * 1000)) / 1000)
        const countdownText = `自动确认倒计时: ${hours}h${minutes}m${seconds}s`
        this.setData({ countdownText })
      }
    }

    // 立即更新一次
    updateCountdown()

    // 每秒更新一次
    const timer = setInterval(updateCountdown, 1000)
    this.setData({ countdownTimer: timer })
  },

  autoConfirmOrder(orderId) {
    console.log('倒计时结束，自动确认收货')
    api.confirmOrder(orderId).then(() => {
      wx.showToast({
        title: '已自动确认收货',
        icon: 'success'
      })
      this.loadOrderDetail(orderId)
    }).catch(err => {
      console.error('自动确认收货失败:', err)
    })
  },

  confirmOrder() {
    const orderId = this.data.order.id
    wx.showModal({
      title: '确认收到',
      content: '确认已收到物品？',
      success: (res) => {
        if (res.confirm) {
          api.confirmOrder(orderId).then(() => {
            wx.showToast({
              title: '已确认收到',
              icon: 'success'
            })
            // 清除定时器
            if (this.data.countdownTimer) {
              clearInterval(this.data.countdownTimer)
            }
            this.loadOrderDetail(orderId)
          }).catch(err => {
            wx.showToast({
              title: err.message || '操作失败',
              icon: 'none'
            })
          })
        }
      }
    })
  },

  shipOrder() {
    const orderId = this.data.order.id
    wx.showModal({
      title: '确认交付',
      content: '确认物品已交付？',
      success: (res) => {
        if (res.confirm) {
          api.shipOrder(orderId).then(() => {
            wx.showToast({
              title: '已确认交付',
              icon: 'success'
            })
            this.loadOrderDetail(orderId)
          }).catch(err => {
            wx.showToast({
              title: err.message || '操作失败',
              icon: 'none'
            })
          })
        }
      }
    })
  },

  // 取消记录
  cancelOrder() {
    const orderId = this.data.order.id
    wx.showModal({
      title: '取消订单',
      content: '确定要取消该订单吗？',
      success: (res) => {
        if (res.confirm) {
          api.cancelOrder(orderId).then(() => {
            wx.showToast({
              title: '已取消',
              icon: 'success'
            })
            this.loadOrderDetail(orderId)
          }).catch(err => {
            wx.showToast({
              title: err.message || '操作失败',
              icon: 'none'
            })
          })
        }
      }
    })
  },

  contactSeller() {
    const sellerId = this.data.order.seller_id
    wx.navigateTo({
      url: `/pages/chat/room?friendId=${sellerId}`
    })
  },

  contactBuyer() {
    const buyerId = this.data.order.user_id || this.data.order.buyer_id
    wx.navigateTo({
      url: `/pages/chat/room?friendId=${buyerId}`
    })
  },

  goToProduct() {
    const productId = this.data.order.product_id
    wx.navigateTo({
      url: `/pages/product/detail?id=${productId}`
    })
  },

  writeReview() {
    const productId = this.data.order.product_id
    wx.navigateTo({
      url: `/pages/product/detail?id=${productId}&showReview=1`
    })
  },

  async subscribeOrderMessage() {
    try {
      const result = await subscribeOrderNotification()
      if (result.success) {
        wx.showToast({
          title: '订阅成功',
          icon: 'success'
        })
      } else if (result.error) {
        wx.showToast({
          title: result.error,
          icon: 'none'
        })
      } else {
        wx.showToast({
          title: '未订阅通知',
          icon: 'none'
        })
      }
    } catch (err) {
      console.error('订阅消息失败:', err)
      wx.showToast({
        title: '订阅失败',
        icon: 'none'
      })
    }
  }
})
