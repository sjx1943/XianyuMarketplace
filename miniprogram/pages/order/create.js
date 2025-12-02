const api = require('../../utils/api.js')
const { getImageUrl } = require('../../utils/config.js')

Page({
  data: {
    product: null,
    productImage: '',
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
      
      // 使用getImageUrl处理图片路径，确保是完整的服务器URL
      const imageFilename = product.image || (product.images && product.images[0])
      const productImage = imageFilename ? getImageUrl(imageFilename) : ''
      
      // 检查库存是否充足
      if (product.quantity <= 0 || product.status === '已售完') {
        wx.showToast({
          title: '商品已售完',
          icon: 'none'
        })
        setTimeout(() => wx.navigateBack(), 1500)
        return
      }
      
      this.setData({
        product: product,
        productImage: productImage,
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
    const { product } = this.data
    if (product && product.user_id) {
      const roomNumber = encodeURIComponent(product.seller_room || product.room_number || '未设置')
      const friendName = encodeURIComponent(product.seller_name || product.username || '')
      wx.navigateTo({
        url: `/pages/chat/room?friendId=${product.user_id}&productId=${product.id}&roomNumber=${roomNumber}&friendName=${friendName}`
      })
    } else {
      wx.showToast({
        title: '无法联系卖家',
        icon: 'none'
      })
    }
  }
})
