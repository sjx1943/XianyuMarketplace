// pages/product/edit.js
const api = require('../../utils/api.js')
const app = getApp()

Page({
  data: {
    productId: null,
    images: [],
    imageIds: [],
    originalImageIds: [],
    newImages: [],
    form: {
      name: '',
      price: '',
      category: '',
      condition: '九成新',
      description: ''
    },
    categories: ['电子产品', '书籍', '家具', '服装鞋帽', '食品饮料', '母婴用品', '运动户外', '玩具', '美妆个护', '家电', '日用百货', '其他'],
    categoryIndex: -1,
    conditions: ['全新', '九成新', '八成新', '七成新', '六成新', '五成新', '四成新', '三成新', '二成新', '一成新', '很旧'],
    conditionIndex: 1,
    submitting: false,
    loading: true
  },

  onLoad(options) {
    if (!app.globalData.isLogin) {
      wx.showToast({ title: '请先登录', icon: 'none' })
      setTimeout(() => wx.navigateTo({ url: '/pages/login/login' }), 1500)
      return
    }

    const { id } = options
    if (id) {
      this.setData({ productId: id })
      this.loadProduct(id)
    } else {
      wx.showToast({ title: '商品不存在', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 1500)
    }
  },

  async loadProduct(id) {
    try {
      wx.showLoading({ title: '加载中...' })
      this.setData({ productId: id })

      const data = await api.getProductDetail(id)
      const product = data.product || data

      if (product && product.id) {
        const { getImageUrl } = require('../../utils/config.js')
        const imageIds = []
        const images = (product.images || []).map(img => {
          const filename = typeof img === 'string' ? img : img.filename
          const id = typeof img === 'string' ? null : img.id
          if (id) imageIds.push(id)
          return getImageUrl(filename)
        })

        const categoryIndex = this.data.categories.indexOf(product.tag || '')
        const conditionIndex = this.data.conditions.indexOf(product.condition || '九成新')

        this.setData({
          images,
          imageIds,
          originalImageIds: [...imageIds],
          form: {
            name: product.name || '',
            price: product.price || '',
            category: product.tag || '',
            condition: product.condition || '九成新',
            description: product.description || ''
          },
          categoryIndex: categoryIndex >= 0 ? categoryIndex : -1,
          conditionIndex: conditionIndex >= 0 ? conditionIndex : 1,
          loading: false
        })
      } else {
        wx.showToast({ title: '商品不存在', icon: 'none' })
        setTimeout(() => wx.navigateBack(), 1500)
      }
    } catch (error) {
      console.error('加载商品失败:', error)
      wx.showToast({ title: '加载失败', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 1500)
    } finally {
      wx.hideLoading()
    }
  },

  // 选择新图片
  chooseImage() {
    const maxCount = 9 - this.data.images.length - this.data.newImages.length

    wx.chooseImage({
      count: maxCount,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        this.setData({
          newImages: [...this.data.newImages, ...res.tempFilePaths]
        })
      }
    })
  },

  // 删除已有图片（仅本地更新，不调用API，等提交时统一删除）
  deleteOldImage(e) {
    const { index } = e.currentTarget.dataset
    
    // 只更新本地UI状态，不立即调用后端API
    // 真正的API删除会在onSubmit()时统一处理
    const images = this.data.images
    const imageIds = this.data.imageIds
    images.splice(index, 1)
    imageIds.splice(index, 1)
    this.setData({ images, imageIds })
    
    wx.showToast({ title: '图片已标记删除，提交时生效', icon: 'success' })
  },

  // 删除新上传图片
  deleteNewImage(e) {
    const { index } = e.currentTarget.dataset
    const newImages = this.data.newImages
    newImages.splice(index, 1)
    this.setData({ newImages })
  },

  // 输入变化
  onInputChange(e) {
    const { field } = e.currentTarget.dataset
    const value = e.detail.value
    this.setData({
      [`form.${field}`]: value
    })
  },

  // 分类变化
  onCategoryChange(e) {
    const index = e.detail.value
    this.setData({
      categoryIndex: index,
      [`form.category`]: this.data.categories[index]
    })
  },

  // 商品状态变化
  onConditionChange(e) {
    const index = e.detail.value
    this.setData({
      conditionIndex: index,
      [`form.condition`]: this.data.conditions[index]
    })
  },

  // 验证表单
  validateForm() {
    const { form, categoryIndex } = this.data

    if (!form.name || form.name.trim() === '') {
      wx.showToast({ title: '请输入商品名称', icon: 'none' })
      return false
    }

    if (!form.price || form.price === '') {
      wx.showToast({ title: '请输入商品价格', icon: 'none' })
      return false
    }

    if (categoryIndex < 0) {
      wx.showToast({ title: '请选择商品分类', icon: 'none' })
      return false
    }

    if (this.data.images.length + this.data.newImages.length === 0) {
      wx.showToast({ title: '请至少上传一张商品图片', icon: 'none' })
      return false
    }

    return true
  },

  // 提交编辑
  async onSubmit() {
    if (!this.validateForm()) return

    this.setData({ submitting: true })

    try {
      wx.showLoading({ title: '更新中...' })

      const { productId, form, newImages, imageIds, originalImageIds } = this.data
      const token = wx.getStorageSync('token') || ''

      // 1. 计算被删除的图片ID
      const deletedImageIds = (originalImageIds || []).filter(id => !imageIds.includes(id))
      console.log('原始图片IDs:', originalImageIds)
      console.log('当前图片IDs:', imageIds)
      console.log('需要删除的图片IDs:', deletedImageIds)

      // 2. 先删除被移除的图片（忽略404错误，这些图片可能已不存在）
      for (const imageId of deletedImageIds) {
        try {
          await api.request({
            url: `/api/miniprogram/product/${productId}/image/${imageId}/delete`,
            method: 'DELETE',
            header: { 'Authorization': 'Bearer ' + token }
          })
        } catch (err) {
          // 如果是404错误（图片不存在），则静默忽略；其他错误才记录
          if (err.message && err.message.includes('404')) {
            console.warn(`图片${imageId}已不存在，跳过删除`)
          } else {
            console.error(`删除图片${imageId}失败:`, err)
          }
        }
      }

      // 3. 更新产品信息（不再需要传递image_ids）
      await api.request({
        url: '/api/miniprogram/product/update',
        method: 'POST',
        header: { 'Authorization': 'Bearer ' + token },
        data: {
          product_id: productId,
          name: form.name,
          description: form.description,
          price: String(form.price),
          tag: form.category,
          condition: form.condition
        }
      })

      // 4. 上传新图片
      for (let i = 0; i < newImages.length; i++) {
        await new Promise((resolve, reject) => {
          const filePath = newImages[i]
          let filename = filePath.split('/').pop() || `image_${i}.jpg`
          filename = filename.replace(/[^\w\-\.]/g, '_')
          
          wx.uploadFile({
            url: api.baseURL + '/api/miniprogram/product/upload',
            filePath: newImages[i],
            name: 'images',
            formData: { 
              product_id: String(productId),
              filename: filename
            },
            header: { 'Authorization': 'Bearer ' + token },
            success: (res) => {
              if (res.statusCode === 200) resolve()
              else reject(new Error('上传失败'))
            },
            fail: reject
          })
        })
      }

      wx.hideLoading()
      wx.showToast({ title: '更新成功', icon: 'success' })

      // 5. 使用redirectTo返回detail页面，让它重新加载所有数据（包括主图和图片列表）
      // 这样保证页面一定会重新onLoad并拉取最新数据
      setTimeout(() => {
        wx.redirectTo({
          url: `/pages/product/detail?id=${productId}`
        })
      }, 1500)
    } catch (error) {
      wx.hideLoading()
      console.error('编辑失败:', error)
      wx.showToast({ title: '编辑失败，请重试', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  }
})
