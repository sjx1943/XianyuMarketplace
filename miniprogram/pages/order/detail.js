const api = require('../../utils/api.js')

Page({
  data: {
    order: null,
    loading: true
  },

  onLoad(options) {
    if (options.id) {
      this.loadOrderDetail(options.id)
    }
  },

  loadOrderDetail(orderId) {
    this.setData({ loading: true })
    
    api.getOrderDetail(orderId).then(res => {
      const order = res.order || res
      const { getImageUrl } = require('../../utils/config.js')
      const productImage = order.product_image || order.image
      const imageUrl = productImage ? getImageUrl(productImage) : ''
      
      this.setData({
        order: order,
        productImage: imageUrl,
        loading: false
      })
    }).catch(err => {
      console.error('加载订单详情失败:', err)
      this.setData({ loading: false })
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      })
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

  contactSeller() {
    const sellerId = this.data.order.seller_id
    wx.navigateTo({
      url: `/pages/chat/room?userId=${sellerId}`
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
