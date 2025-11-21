// pages/product/publish.js
const api = require('../../utils/api.js')
const app = getApp()

Page({
  data: {
    images: [],
    form: {
      name: '',
      price: '',
      category: '',
      condition: '',
      description: '',
      tags: []
    },
    categories: ['数码产品', '家用电器', '服装鞋包', '图书音像', '运动户外', '美妆个护', '家居用品', '其他'],
    categoryIndex: -1,
    availableTags: ['包邮', '可议价', '急转', '自提', '全新未拆', '保修期内', '配件齐全', '支持退换'],
    submitting: false
  },

  onLoad(options) {
    // 检查登录状态
    if (!app.globalData.isLogin) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      })
      setTimeout(() => {
        wx.navigateTo({
          url: '/pages/login/login'
        })
      }, 1500)
      return
    }

    // 检查是否有房间号
    const userInfo = wx.getStorageSync('userInfo')
    if (!userInfo || !userInfo.room_number) {
      wx.showModal({
        title: '提示',
        content: '发布商品前需要先设置房间号',
        confirmText: '去设置',
        success: (res) => {
          if (res.confirm) {
            wx.navigateTo({
              url: '/pages/profile/edit'
            })
          } else {
            wx.navigateBack()
          }
        }
      })
    }
  },

  // 选择图片
  chooseImage() {
    const maxCount = 9 - this.data.images.length
    
    wx.chooseImage({
      count: maxCount,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const newImages = res.tempFilePaths
        this.setData({
          images: [...this.data.images, ...newImages]
        })
      }
    })
  },

  // 删除图片
  deleteImage(e) {
    const { index } = e.currentTarget.dataset
    const images = this.data.images
    images.splice(index, 1)
    this.setData({ images })
  },

  // 输入变化
  onInputChange(e) {
    const { field } = e.currentTarget.dataset
    const { value } = e.detail
    this.setData({
      [`form.${field}`]: value
    })
  },

  // 分类选择
  onCategoryChange(e) {
    const index = e.detail.value
    this.setData({
      categoryIndex: index,
      'form.category': this.data.categories[index]
    })
  },

  // 成色选择
  onConditionChange(e) {
    const { condition } = e.currentTarget.dataset
    this.setData({
      'form.condition': condition
    })
  },

  // 标签切换
  onTagToggle(e) {
    const { tag } = e.currentTarget.dataset
    const tags = this.data.form.tags
    const index = tags.indexOf(tag)
    
    if (index > -1) {
      tags.splice(index, 1)
    } else {
      if (tags.length < 5) {
        tags.push(tag)
      } else {
        wx.showToast({
          title: '最多选择5个标签',
          icon: 'none'
        })
        return
      }
    }
    
    this.setData({
      'form.tags': tags
    })
  },

  // 表单验证
  validateForm() {
    const { form, images } = this.data

    if (images.length === 0) {
      wx.showToast({
        title: '请上传商品图片',
        icon: 'none'
      })
      return false
    }

    if (!form.name.trim()) {
      wx.showToast({
        title: '请输入商品名称',
        icon: 'none'
      })
      return false
    }

    if (!form.price || parseFloat(form.price) <= 0) {
      wx.showToast({
        title: '请输入正确的价格',
        icon: 'none'
      })
      return false
    }

    if (!form.category) {
      wx.showToast({
        title: '请选择商品分类',
        icon: 'none'
      })
      return false
    }

    if (!form.condition) {
      wx.showToast({
        title: '请选择商品成色',
        icon: 'none'
      })
      return false
    }

    return true
  },

  // 提交表单
  async onSubmit() {
    if (!this.validateForm()) {
      return
    }

    this.setData({ submitting: true })

    try {
      // 1. 上传图片
      wx.showLoading({ title: '上传图片中...' })
      const imageUrls = await this.uploadImages()

      // 2. 提交商品信息
      wx.showLoading({ title: '发布中...' })
      const data = await api.publishProduct({
        name: this.data.form.name,
        price: parseFloat(this.data.form.price),
        category: this.data.form.category,
        condition: this.data.form.condition,
        description: this.data.form.description,
        tags: this.data.form.tags.join(','),
        images: imageUrls
      })

      wx.hideLoading()

      if (data.success) {
        wx.showToast({
          title: '发布成功',
          icon: 'success'
        })

        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        wx.showToast({
          title: data.error || '发布失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.hideLoading()
      console.error('发布失败:', error)
      wx.showToast({
        title: '发布失败，请重试',
        icon: 'none'
      })
    } finally {
      this.setData({ submitting: false })
    }
  },

  // 上传图片
  async uploadImages() {
    const { images } = this.data
    const imageUrls = []

    // 后端通过multipart表单上传，每次上传一张图片
    for (const filePath of images) {
      try {
        const result = await api.uploadFile({
          url: '/product/upload',
          filePath: filePath,
          name: 'images',
          formData: {}
        })
        
        // 后端返回的格式可能是 { image_url: "..." } 或直接是URL
        const url = result.image_url || result.url || filePath
        imageUrls.push(url)
      } catch (error) {
        console.error('图片上传失败:', error)
        throw new Error('图片上传失败')
      }
    }

    return imageUrls
  }
})
