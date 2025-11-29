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
      
      // 后端返回 {success: true, product: {...}} 格式
      const product = data.product || data
      if (product && product.id) {
        // 处理图片数据：将图片对象数组转换为完整的服务器URL
        const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')
        const images = (product.images || []).map(img => {
          const filename = typeof img === 'string' ? img : img.filename
          return getImageUrl(filename)
        })
        
        // 处理卖家信息字段映射
        const sellerAvatar = product.seller?.avatar ? getImageUrl(product.seller.avatar) : getDefaultAvatarUrl()
        const productData = {
          ...product,
          images: images,
          seller_avatar: sellerAvatar,
          seller_name: product.seller?.username || product.seller_name || '未知卖家',
          seller_room: product.seller?.room_number || product.seller_room || '未设置',
          created_at: product.upload_time || product.created_at || '',
          seller_id: product.seller?.id || product.seller_id
        }
        
        this.setData({
          product: productData,
          loading: false
        })
      } else {
        wx.showToast({
          title: '商品不存在',
          icon: 'none'
        })
        setTimeout(() => wx.navigateBack(), 1500)
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

  // 收藏/取消收藏（暂未实现后端API，本地模拟）
  async onFavorite() {
    if (!app.globalData.isLogin) {
      wx.navigateTo({
        url: '/pages/login/login'
      })
      return
    }

    try {
      const { product } = this.data
      
      // TODO: 后端需要添加收藏功能API `/api/product/favorite`
      // 暂时只做本地状态切换
      this.setData({
        'product.is_favorited': !product.is_favorited
      })
      
      wx.showToast({
        title: product.is_favorited ? '收藏成功' : '已取消收藏',
        icon: 'success'
      })
      
      // 保存到本地存储
      const favorites = wx.getStorageSync('favorites') || []
      if (product.is_favorited) {
        favorites.push(product.id)
      } else {
        const index = favorites.indexOf(product.id)
        if (index > -1) favorites.splice(index, 1)
      }
      wx.setStorageSync('favorites', favorites)
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
