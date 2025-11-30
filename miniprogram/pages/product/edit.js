// pages/product/edit.js
const api = require('../../utils/api.js')
const app = getApp()

Page({
  data: {
    productId: null,
    images: [],
    imageIds: [],
    newImages: [],
    form: {
      name: '',
      price: '',
      category: '',
      condition: '九成新',
      description: ''
    },
    categories: ['数码产品', '家用电器', '服装鞋包', '图书音像', '运动户外', '美妆个护', '家居用品', '其他'],
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

  // 删除已有图片
  async deleteOldImage(e) {
    const { index } = e.currentTarget.dataset
    const imageId = this.data.imageIds[index]
    const token = wx.getStorageSync('token') || ''

    try {
      // 调用后端删除API
      if (imageId) {
        await api.request({
          url: `/api/miniprogram/product/${this.data.productId}/image/${imageId}/delete`,
          method: 'DELETE',
          header: { 'Authorization': 'Bearer ' + token }
        })
      }

      // 更新本地状态
      const images = this.data.images
      const imageIds = this.data.imageIds
      images.splice(index, 1)
      imageIds.splice(index, 1)
      this.setData({ images, imageIds })
      
      wx.showToast({ title: '图片已删除', icon: 'success' })
    } catch (error) {
      console.error('删除图片失败:', error)
      wx.showToast({ title: '删除失败，请重试', icon: 'none' })
    }
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

      const { productId, form, newImages, imageIds } = this.data
      const token = wx.getStorageSync('token') || ''

      // 1. 获取原始图片ID列表（从loadProduct时保存的）
      const originalImageIds = this.data.imageIds || []
      const deletedImageIds = originalImageIds.filter(id => !imageIds.includes(id))

      // 2. 先删除被移除的图片
      for (const imageId of deletedImageIds) {
        try {
          await api.request({
            url: `/api/miniprogram/product/${productId}/image/${imageId}/delete`,
            method: 'DELETE',
            header: { 'Authorization': 'Bearer ' + token }
          })
        } catch (err) {
          console.error(`删除图片${imageId}失败:`, err)
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

      // 5. 设置编辑标志，然后返回上一页
      // 这样detail.js的onShow会检测到编辑标志并重新加载数据
      const app = getApp()
      app.globalData.justEditedProductId = productId
      
      setTimeout(() => {
        wx.navigateBack()
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
