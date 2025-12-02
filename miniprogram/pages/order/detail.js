const api = require('../../utils/api.js')
const app = getApp()

Page({
  data: {
    order: null,
    loading: true,
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
    
    api.getOrderDetail(orderId).then(res => {
      const order = res.order || res
      const { getImageUrl } = require('../../utils/config.js')
      const productImage = order.product_image || order.image
      const imageUrl = productImage ? getImageUrl(productImage) : ''
      
      // 判断当前用户是买家还是卖家
      const isBuyer = currentUserId === order.user_id || currentUserId === order.buyer_id
      const isSeller = currentUserId === order.seller_id
      
      this.setData({
        order: order,
        productImage: imageUrl,
        isBuyer: isBuyer,
        isSeller: isSeller,
        loading: false
      })
      
      // 如果订单是shipped状态且当前用户是买家，启动倒计时
      if (order.status === 'shipped' && isBuyer && order.shipped_at) {
        this.startAutoConfirmCountdown(orderId, order.shipped_at)
      }
    }).catch(err => {
      console.error('加载订单详情失败:', err)
      this.setData({ loading: false })
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      })
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
      title: '确认收货',
      content: '确认已收到商品？',
      success: (res) => {
        if (res.confirm) {
          api.confirmOrder(orderId).then(() => {
            wx.showToast({
              title: '已确认收货',
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
      title: '确认发货',
      content: '确认商品已发货？',
      success: (res) => {
        if (res.confirm) {
          api.shipOrder(orderId).then(() => {
            wx.showToast({
              title: '已确认发货',
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

  // 取消订单（买家）
  cancelOrder() {
    const orderId = this.data.order.id
    wx.showModal({
      title: '取消订单',
      content: '确定要取消这个订单吗？',
      success: (res) => {
        if (res.confirm) {
          api.cancelOrder(orderId).then(() => {
            wx.showToast({
              title: '订单已取消',
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
  }
})
