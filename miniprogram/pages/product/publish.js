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
      condition: '九成新',
      description: '',
      tags: []
    },
    categories: ['数码产品', '家用电器', '服装鞋包', '图书音像', '运动户外', '美妆个护', '家居用品', '其他'],
    categoryIndex: -1,
    conditions: ['全新', '九成新', '八成新', '七成新', '六成新', '五成新', '四成新', '三成新', '二成新', '一成新', '很旧'],
    conditionIndex: 1,
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
    const index = e.detail.value
    this.setData({
      conditionIndex: index,
      'form.condition': this.data.conditions[index]
    })
  },

  // 标签切换（功能已移除）
  onTagToggle(e) {
    // 标签功能已移除
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
      wx.showLoading({ title: '发布中...' })

      const { images, form } = this.data
      const token = wx.getStorageSync('token') || ''
      let productId = null

      for (let i = 0; i < images.length; i++) {
        const isFirst = i === 0
        
        const formData = isFirst ? {
          name: form.name,
          description: form.description || '',
          price: String(form.price),
          quantity: '1',
          tag: form.category,
          condition: form.condition
        } : {
          product_id: String(productId)
        }

        wx.showLoading({ title: `上传中 ${i + 1}/${images.length}` })

        const result = await new Promise((resolve, reject) => {
          wx.uploadFile({
            url: api.baseURL + '/api/miniprogram/product/upload',
            filePath: images[i],
            name: 'images',
            formData: formData,
            header: {
              'Authorization': 'Bearer ' + token
            },
            success: (res) => {
              console.log('上传响应:', res.statusCode, res.data)
              if (res.statusCode === 200) {
                try {
                  const data = JSON.parse(res.data)
                  if (data.success) {
                    resolve(data)
                  } else {
                    reject(new Error(data.error || '上传失败'))
                  }
                } catch (e) {
                  reject(new Error('解析响应失败'))
                }
              } else if (res.statusCode === 401) {
                reject(new Error('请先登录'))
              } else {
                try {
                  const errorData = JSON.parse(res.data)
                  reject(new Error(errorData.error || '上传失败'))
                } catch (e) {
                  reject(new Error(`上传失败 (${res.statusCode})`))
                }
              }
            },
            fail: (err) => {
              console.error('上传网络错误:', err)
              reject(new Error('网络错误，请检查网络连接'))
            }
          })
        })

        if (isFirst && result.product_id) {
          productId = result.product_id
        }
      }

      wx.hideLoading()
      
      wx.showToast({
        title: '发布成功',
        icon: 'success'
      })

      setTimeout(() => {
        wx.switchTab({
          url: '/pages/product/list'
        })
      }, 1500)
    } catch (error) {
      wx.hideLoading()
      console.error('发布失败:', error)
      wx.showToast({
        title: error.message || '发布失败，请重试',
        icon: 'none'
      })
    } finally {
      this.setData({ submitting: false })
    }
  }
})
