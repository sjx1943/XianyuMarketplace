const api = require('../../utils/api.js')

Page({
  data: {
    product: null,
    quantity: 1,
    note: '',
    loading: true,
    submitting: false,
    totalPrice: '0.00'
  },

  onLoad(options) {
    if (options.productId) {
      this.loadProduct(options.productId)
    }
  },

  loadProduct(productId) {
    this.setData({ loading: true })
    
    api.getProductDetail(productId).then(res => {
      const product = res.product || res
      this.setData({
        product: product,
        loading: false,
        totalPrice: this.calculateTotal(product.price, 1)
      })
    }).catch(err => {
      console.error('加载商品失败:', err)
      this.setData({ loading: false })
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      })
    })
  },

  calculateTotal(price, quantity) {
    const total = (parseFloat(price) || 0) * quantity
    return total.toFixed(2)
  },

  onQuantityChange(e) {
    let quantity = parseInt(e.detail.value) || 1
    const max = this.data.product.quantity || 1
    quantity = Math.max(1, Math.min(quantity, max))
    this.setData({ 
      quantity,
      totalPrice: this.calculateTotal(this.data.product.price, quantity)
    })
  },

  decreaseQuantity() {
    if (this.data.quantity > 1) {
      const newQuantity = this.data.quantity - 1
      this.setData({ 
        quantity: newQuantity,
        totalPrice: this.calculateTotal(this.data.product.price, newQuantity)
      })
    }
  },

  increaseQuantity() {
    const max = this.data.product.quantity || 1
    if (this.data.quantity < max) {
      const newQuantity = this.data.quantity + 1
      this.setData({ 
        quantity: newQuantity,
        totalPrice: this.calculateTotal(this.data.product.price, newQuantity)
      })
    }
  },

  onNoteInput(e) {
    this.setData({ note: e.detail.value })
  },

  submitOrder() {
    if (this.data.submitting) return
    
    const { product, quantity, note } = this.data
    
    if (!product) {
      wx.showToast({
        title: '商品信息错误',
        icon: 'none'
      })
      return
    }

    this.setData({ submitting: true })

    api.createOrder({
      product_id: product.id,
      quantity: quantity,
      order_note: note
    }).then(res => {
      wx.showToast({
        title: '下单成功',
        icon: 'success'
      })
      setTimeout(() => {
        wx.redirectTo({
          url: `/pages/order/detail?id=${res.order_id || res.id}`
        })
      }, 1500)
    }).catch(err => {
      wx.showToast({
        title: err.message || '下单失败',
        icon: 'none'
      })
    }).finally(() => {
      this.setData({ submitting: false })
    })
  },

  contactSeller() {
    if (this.data.product && this.data.product.user_id) {
      wx.navigateTo({
        url: `/pages/chat/room?userId=${this.data.product.user_id}`
      })
    }
  }
})
