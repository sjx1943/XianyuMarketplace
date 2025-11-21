// pages/product/detail.js
const api = require('../../utils/api.js')
const app = getApp()

Page({
  data: {
    product: {},
    loading: true
  },

  onLoad(options) {
    const { id } = options
    if (id) {
      this.loadProductDetail(id)
    } else {
      wx.showToast({
        title: '商品不存在',
        icon: 'none'
      })
      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
    }
  },

  // 加载商品详情
  async loadProductDetail(id) {
    try {
      wx.showLoading({ title: '加载中...' })
      
      const data = await api.getProductDetail(id)
      
      if (data.success) {
        this.setData({
          product: data.product,
          loading: false
        })
      } else {
        wx.showToast({
          title: data.error || '加载失败',
          icon: 'none'
        })
      }
    } catch (error) {
      console.error('加载商品详情失败:', error)
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      })
    } finally {
      wx.hideLoading()
    }
  },

  // 预览图片
  previewImage(e) {
    const { url } = e.currentTarget.dataset
    wx.previewImage({
      current: url,
      urls: this.data.product.images
    })
  },

  // 查看卖家资料
  viewSellerProfile() {
    wx.navigateTo({
      url: `/pages/user/profile?id=${this.data.product.seller_id}`
    })
  },

  // 收藏/取消收藏
  async onFavorite() {
    if (!app.globalData.isLogin) {
      wx.navigateTo({
        url: '/pages/login/login'
      })
      return
    }

    try {
      const { product } = this.data
      const data = await api.request({
        url: '/api/product/favorite',
        method: 'POST',
        data: {
          product_id: product.id,
          action: product.is_favorited ? 'remove' : 'add'
        }
      })

      if (data.success) {
        this.setData({
          'product.is_favorited': !product.is_favorited
        })
        wx.showToast({
          title: product.is_favorited ? '已取消收藏' : '收藏成功',
          icon: 'success'
        })
      }
    } catch (error) {
      console.error('收藏失败:', error)
    }
  },

  // 联系卖家
  onChat() {
    if (!app.globalData.isLogin) {
      wx.navigateTo({
        url: '/pages/login/login'
      })
      return
    }

    const { product } = this.data
    wx.navigateTo({
      url: `/pages/chat/room?friendId=${product.seller_id}&productId=${product.id}`
    })
  },

  // 立即购买
  onBuy() {
    if (!app.globalData.isLogin) {
      wx.navigateTo({
        url: '/pages/login/login'
      })
      return
    }

    const { product } = this.data
    wx.navigateTo({
      url: `/pages/order/create?productId=${product.id}`
    })
  },

  // 分享功能
  onShareAppMessage() {
    const { product } = this.data
    return {
      title: product.name,
      path: `/pages/product/detail?id=${product.id}`,
      imageUrl: product.images && product.images[0]
    }
  },

  onShareTimeline() {
    const { product } = this.data
    return {
      title: `【闲置】${product.name} - 仅售¥${product.price}`,
      query: `id=${product.id}`,
      imageUrl: product.images && product.images[0]
    }
  }
})
