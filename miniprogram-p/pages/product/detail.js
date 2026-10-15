// pages/product/detail.js
const api = require('../../utils/api.js')
const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')
const cloudStorage = require('../../utils/cloudStorage.js')
const contentSecurity = require('../../utils/contentSecurity.js')
const app = getApp()

// API 请求超时时间（毫秒）
const API_TIMEOUT = 5000

Page({
  data: {
    product: {},
    productId: null,
    loading: false,  // 初始值改为 false
    isOwner: false,
    currentUserId: null,
    imageDetails: [],
    canReview: false,
    showReviewModal: false,
    reviewRating: 5,
    reviewContent: '',
    comments: [],
    showComments: false
  },

  onLoad(options) {
    const { id, showReview } = options
    
    const userInfo = wx.getStorageSync('userInfo')
    if (userInfo && userInfo.id) {
      this.setData({ currentUserId: userInfo.id })
    }
    
    if (id) {
      this.setData({ productId: id })
      
      // 优先加载商品详情，评论和评价权限可以稍后并行加载
      this.loadProductDetail(id).then(() => {
        // 商品加载完成后，并行加载评论和检查评价权限
        Promise.all([
          this.checkCanReview(id),
          this.loadComments(id)
        ]).catch(err => console.error('加载辅助数据失败:', err))
      })
      
      // 如果从订单详情页跳转来评价，自动打开评价弹框
      if (showReview === '1') {
        setTimeout(() => {
          if (this.data.canReview) {
            this.setData({ showReviewModal: true })
          }
        }, 800)  // 延长等待时间确保数据加载完成
      }
    } else {
      wx.showToast({
        title: '物品不存在',
        icon: 'none'
      })
      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
    }
  },

  onShow() {
    // 检查是否刚刚编辑过产品，如果是则重新加载
    const app = getApp()
    const justEditedId = app.globalData.justEditedProductId
    const currentId = String(this.data.productId)
    
    console.log('onShow - justEditedId:', justEditedId, 'currentId:', currentId)
    
    if (justEditedId && String(justEditedId) === currentId) {
      console.log('检测到商品编辑，重新加载数据')
      app.globalData.justEditedProductId = null
      // 立即重新加载，不等待任何延迟
      this.loadProductDetail(this.data.productId)
    }
  },

  // 加载商品详情
  async loadProductDetail(id) {
    try {
      console.log('loadProductDetail - 开始加载商品:', id)
      
      // 添加超时机制
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('请求超时')), API_TIMEOUT)
      )
      
      const data = await Promise.race([
        api.getProductDetail(id),
        timeoutPromise
      ])
      console.log('loadProductDetail - API返回数据:', data)
      
      // 后端返回 {success: true, product: {...}} 格式
      const product = data.product || data
      if (product && product.id) {
        // 处理图片数据：将图片对象数组转换为完整的服务器URL
        // 构建包含 ID 的图片详情数组
        // filename: 中等尺寸图片（720px，用于详情页展示）
        // original_filename: 原图（用于预览大图）
        let imageDetails = (product.images || []).map((img, idx) => {
          const filename = typeof img === 'string' ? img : img.filename
          const originalFilename = img.original_filename || filename
          const id = img.id || idx
          return {
            id: id,
            url: getImageUrl(filename),
            originalUrl: getImageUrl(originalFilename),
            filename: filename,
            originalFilename: originalFilename
          }
        })
        
        // 处理云存储图片（cloud:// 格式需要转换为临时 URL）
        const cloudFileIDs = []
        imageDetails.forEach(img => {
          if (img.url && img.url.startsWith('cloud://')) cloudFileIDs.push(img.url)
          if (img.originalUrl && img.originalUrl.startsWith('cloud://') && img.originalUrl !== img.url) {
            cloudFileIDs.push(img.originalUrl)
          }
        })
        
        if (cloudFileIDs.length > 0) {
          try {
            const tempUrls = await cloudStorage.getTempFileURL(cloudFileIDs)
            const urlMap = {}
            tempUrls.forEach(item => {
              if (item.fileID && item.tempFileURL) {
                urlMap[item.fileID] = item.tempFileURL
              }
            })
            imageDetails = imageDetails.map(img => ({
              ...img,
              url: urlMap[img.url] || img.url,
              originalUrl: urlMap[img.originalUrl] || img.originalUrl
            }))
          } catch (err) {
            console.error('转换云存储图片URL失败:', err)
          }
        }
        
        // 兼容旧版本：保留原始 images 数组（URL 数组）供分享等功能使用
        const images = imageDetails.map(img => img.url)
        
        // 处理卖家信息字段映射
        let sellerAvatar = product.seller?.avatar ? getImageUrl(product.seller.avatar) : getDefaultAvatarUrl()
        
        // 处理云存储头像
        if (sellerAvatar && sellerAvatar.startsWith('cloud://')) {
          try {
            const avatarTempUrls = await cloudStorage.getTempFileURL([sellerAvatar])
            if (avatarTempUrls[0]?.tempFileURL) {
              sellerAvatar = avatarTempUrls[0].tempFileURL
            }
          } catch (err) {
            console.error('转换头像URL失败:', err)
          }
        }
        
        const productData = {
          ...product,
          images: images,
          imageDetails: imageDetails,
          seller_avatar: sellerAvatar,
          seller_name: product.seller?.username || product.seller_name || '未知邻居',
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
          title: '物品不存在',
          icon: 'none'
        })
        setTimeout(() => wx.navigateBack(), 1500)
      }
    } catch (error) {
      console.error('加载商品详情失败:', error)
      // 超时提示
      if (error.message === '请求超时') {
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
    }
  },

  // 预览图片（使用原图）
  previewImage(e) {
    const { url } = e.currentTarget.dataset
    
    // 使用原图URL进行预览（高清大图）
    const originalImages = (this.data.imageDetails || []).map(img => img.originalUrl).filter(Boolean)
    
    // 找到当前点击图片对应的原图URL
    const currentIndex = this.data.imageDetails.findIndex(img => img.url === url)
    const currentOriginalUrl = currentIndex >= 0 && this.data.imageDetails[currentIndex] 
      ? this.data.imageDetails[currentIndex].originalUrl 
      : url
    
    wx.previewImage({
      current: currentOriginalUrl,
      urls: originalImages.length > 0 ? originalImages : [url]
    })
  },

  // 轮播变化时更新当前显示的图片
  onSwiperChange(e) {
    const { current } = e.detail
    this.setData({ currentImageIndex: current })
  },

  // 删除商品图片
  deleteImage(e) {
    const { imageId, index } = e.currentTarget.dataset
    const { product, imageDetails } = this.data

    wx.showModal({
      title: '删除图片',
      content: '确定要删除这张图片吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.deleteProductImage(product.id, imageId)
            
            // 删除本地数据
            const newImageDetails = imageDetails.filter(img => img.id !== imageId)
            const newImages = newImageDetails.map(img => img.url)
            
            // 如果删除的是主图，更新主图
            let newMainImage = product.image
            if (imageDetails[index].filename === product.image && newImageDetails.length > 0) {
              newMainImage = newImageDetails[0].filename
            }
            
            this.setData({
              imageDetails: newImageDetails,
              'product.images': newImages,
              'product.image': newMainImage
            })
            
            wx.showToast({
              title: '删除成功',
              icon: 'success'
            })
          } catch (error) {
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

  // 设置主图
  async setPrimaryImage(e) {
    const { imageId, filename } = e.currentTarget.dataset
    const { product } = this.data

    try {
      await api.setProductImagePrimary(product.id, imageId)
      
      // 更新本地数据
      this.setData({
        'product.image': filename
      })
      
      wx.showToast({
        title: '主图设置成功',
        icon: 'success'
      })
    } catch (error) {
      console.error('设置主图失败:', error)
      wx.showToast({
        title: '设置失败',
        icon: 'none'
      })
    }
  },


  // 查看卖家资料 - 跳转到卖家店铺
  viewSellerProfile() {
    wx.navigateTo({
      url: `/pages/seller/shop?id=${this.data.product.seller_id}`
    })
  },

  // 跳转到卖家店铺（点击房间号）
  goToSellerShop() {
    wx.navigateTo({
      url: `/pages/seller/shop?id=${this.data.product.seller_id}`
    })
  },

  // 头像/图片加载失败处理
  onAvatarError(e) {
    console.warn('图片加载失败:', e)
  },

  // 卖家头像加载失败时使用默认头像
  onSellerAvatarError(e) {
    console.warn('卖家头像加载失败，使用默认头像')
    const { getDefaultAvatarUrl } = require('../../utils/config.js')
    this.setData({
      'product.seller_avatar': getDefaultAvatarUrl()
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
      const isFavorited = product.is_favorited
      
      if (isFavorited) {
        await api.removeFavorite(product.id)
        this.setData({ 'product.is_favorited': false })
        wx.showToast({ title: '已取消收藏', icon: 'success' })
      } else {
        await api.addFavorite(product.id)
        this.setData({ 'product.is_favorited': true })
        wx.showToast({ title: '收藏成功', icon: 'success' })
      }
    } catch (error) {
      console.error('收藏操作失败:', error)
      wx.showToast({
        title: error.message || '操作失败',
        icon: 'none'
      })
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
    const roomNumber = encodeURIComponent(product.seller_room || '未设置')
    const friendName = encodeURIComponent(product.seller_name || '')
    wx.navigateTo({
      url: `/pages/chat/room?friendId=${product.seller_id}&productId=${product.id}&roomNumber=${roomNumber}&friendName=${friendName}`
    })
  },

  // 我想要（原购买功能 - 创建互动记录）
  onWant() {
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

  // 跳转到我的记录页面
  goToMyRecords() {
    wx.switchTab({
      url: '/pages/order/list'
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
      title: `【闲置】${product.name}`,
      query: `id=${product.id}`,
      imageUrl: product.images && product.images[0]
    }
  },

  // 拉黑卖家
  onBlockSeller() {
    wx.showModal({
      title: '加入黑名单',
      content: '加入黑名单后，将不再看到对方的物品和消息。确定要加入吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.addToBlacklist(this.data.product.seller_id)
            wx.showToast({
              title: '已加入黑名单',
              icon: 'success'
            })
            // 清除商品列表缓存
            wx.removeStorageSync('products_cache')
            wx.removeStorageSync('products_version')
            setTimeout(() => {
              wx.navigateBack()
            }, 1500)
          } catch (error) {
            wx.showToast({
              title: error.message || '操作失败',
              icon: 'none'
            })
          }
        }
      }
    })
  },

  // 编辑商品（自己的商品）
  onEdit() {
    const { product } = this.data
    wx.navigateTo({
      url: `/pages/product/edit?id=${product.id}`
    })
  },

  // 删除物品（自己的物品）
  onDelete() {
    const { product } = this.data
    
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这个物品吗？删除后无法恢复。',
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
  },

  // 前往我的商品列表
  goToMyProducts() {
    wx.reLaunch({
      url: '/pages/product/myProducts'
    })
  },

  // 返回主页
  goToHome() {
    wx.reLaunch({
      url: '/pages/product/list'
    })
  },

  // 检查用户是否可以评价此商品
  async checkCanReview(productId) {
    try {
      // 添加超时机制
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('请求超时')), API_TIMEOUT)
      )
      
      const res = await Promise.race([
        api.canReview(productId),
        timeoutPromise
      ])
      this.setData({ canReview: res.can_review === true })
    } catch (err) {
      console.error('检查评价权限失败:', err)
      this.setData({ canReview: false })
    }
  },

  // 加载商品评论
  async loadComments(productId) {
    try {
      // 添加超时机制
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('请求超时')), API_TIMEOUT)
      )
      
      const res = await Promise.race([
        api.getComments(productId),
        timeoutPromise
      ])
      if (res.success && res.comments) {
        this.setData({ comments: res.comments })
      }
    } catch (err) {
      console.error('加载评论失败:', err)
    }
  },

  // 打开评价弹框
  openReviewModal() {
    if (!this.data.canReview) {
      wx.showToast({
        title: '只有完成交易后才能评价',
        icon: 'none'
      })
      return
    }
    this.setData({ showReviewModal: true })
  },

  // 关闭评价弹框
  closeReviewModal() {
    this.setData({ showReviewModal: false })
  },

  // 设置评分
  setRating(e) {
    const rating = e.currentTarget.dataset.rating
    this.setData({ reviewRating: rating })
  },

  // 评价内容输入
  onReviewInput(e) {
    this.setData({ reviewContent: e.detail.value })
  },

  // 提交评价
  async submitReview() {
    const { reviewRating, reviewContent, productId } = this.data
    
    if (!reviewContent.trim()) {
      wx.showToast({
        title: '请输入评价内容',
        icon: 'none'
      })
      return
    }

    const isValid = await contentSecurity.validateComment(reviewContent)
    if (!isValid) {
      return
    }

    try {
      await api.postComment({
        product_id: productId,
        rating: reviewRating,
        content: reviewContent
      })
      
      wx.showToast({
        title: '评价成功',
        icon: 'success'
      })
      
      this.setData({ 
        showReviewModal: false,
        reviewContent: '',
        reviewRating: 5,
        canReview: false
      })
      
      // 重新加载评论
      this.loadComments(productId)
    } catch (err) {
      wx.showToast({
        title: err.message || '评价失败',
        icon: 'none'
      })
    }
  },

  // 切换显示评论
  toggleComments() {
    this.setData({ showComments: !this.data.showComments })
  }
})
