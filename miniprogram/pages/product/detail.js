// pages/product/detail.js
const api = require('../../utils/api.js')
const app = getApp()

Page({
  data: {
    product: {},
    loading: true,
    isOwner: false,
    currentUserId: null,
    editingImage: false,
    selectedImageId: null,
    imageDetails: []
  },

  onLoad(options) {
    const { id } = options
    
    const userInfo = wx.getStorageSync('userInfo')
    if (userInfo && userInfo.id) {
      this.setData({ currentUserId: userInfo.id })
    }
    
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
        
        // 构建包含 ID 的图片详情数组
        const imageDetails = (product.images || []).map((img, idx) => {
          const filename = typeof img === 'string' ? img : img.filename
          const id = img.id || idx  // 优先使用后端返回的图片 ID，否则使用索引
          return {
            id: id,
            url: getImageUrl(filename),
            filename: filename
          }
        })
        
        // 兼容旧版本：保留原始 images 数组（URL 数组）供分享等功能使用
        const images = imageDetails.map(img => img.url)
        
        // 处理卖家信息字段映射
        const sellerAvatar = product.seller?.avatar ? getImageUrl(product.seller.avatar) : getDefaultAvatarUrl()
        const productData = {
          ...product,
          images: images,
          imageDetails: imageDetails,
          seller_avatar: sellerAvatar,
          seller_name: product.seller?.username || product.seller_name || '未知卖家',
          seller_room: product.seller?.room_number || product.seller_room || '未设置',
          created_at: product.upload_time || product.created_at || '',
          seller_id: product.seller?.id || product.seller_id
        }
        
        const isOwner = this.data.currentUserId && productData.seller_id === this.data.currentUserId
        
        this.setData({
          product: productData,
          imageDetails: imageDetails,
          loading: false,
          isOwner: isOwner
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

  // 进入编辑模式
  enterEditMode() {
    this.setData({ editingImage: true })
  },

  // 退出编辑模式
  exitEditMode() {
    this.setData({ editingImage: false, selectedImageId: null })
  },

  // 选择要删除的图片
  selectImageForDelete(e) {
    const { id, index } = e.currentTarget.dataset
    this.setData({ selectedImageId: { id, index } })
  },

  // 删除图片
  async deleteImage() {
    const { product, selectedImageId, imageDetails } = this.data
    if (!selectedImageId) return

    const { id, index } = selectedImageId
    
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这张图片吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            wx.showLoading({ title: '删除中...' })
            
            console.log('删除图片 - 商品ID:', product.id, '图片ID:', id)
            
            // 调用后端API删除图片（使用实际的图片数据库ID）
            await api.deleteProductImage(product.id, id)
            
            // 更新本地图片列表
            const newImageDetails = imageDetails.filter((_, i) => i !== index)
            const newImages = newImageDetails.map(img => img.url)
            
            this.setData({
              imageDetails: newImageDetails,
              'product.images': newImages,
              'product.imageDetails': newImageDetails,
              selectedImageId: null
            })
            
            wx.hideLoading()
            wx.showToast({
              title: '删除成功',
              icon: 'success'
            })
          } catch (error) {
            wx.hideLoading()
            console.error('删除图片失败:', error)
            wx.showToast({
              title: '删除失败',
              icon: 'none'
            })
          }
        }
      }
    })
  },

  // 查看卖家资料
  viewSellerProfile() {
    wx.navigateTo({
      url: `/pages/user/profile?id=${this.data.product.seller_id}`
    })
  },

  // 头像/图片加载失败处理
  onAvatarError(e) {
    console.warn('图片加载失败:', e)
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
  },

  // 编辑商品（自己的商品）
  onEdit() {
    const { product } = this.data
    wx.navigateTo({
      url: `/pages/product/edit?id=${product.id}`
    })
  },

  // 删除商品（自己的商品）
  onDelete() {
    const { product } = this.data
    
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这个商品吗？删除后无法恢复。',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.deleteProduct(product.id)
            wx.showToast({
              title: '删除成功',
              icon: 'success'
            })
            setTimeout(() => {
              wx.navigateBack()
            }, 1500)
          } catch (error) {
            wx.showToast({
              title: '删除失败',
              icon: 'none'
            })
          }
        }
      }
    })
  }
})
