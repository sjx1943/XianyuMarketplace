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
    const index = e.detail.value
    this.setData({
      conditionIndex: index,
      'form.condition': this.data.conditions[index]
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
      wx.showLoading({ title: '发布中...' })

      // 后端期望一次性提交所有数据（表单+图片）
      // 使用wx.uploadFile一次上传，但小程序限制只能传一个文件
      // 因此需要多次请求或者合并为一个multipart请求
      
      // 方案：依次上传图片，然后提交商品信息
      const { images, form } = this.data
      
      // 使用多次上传（因为小程序API限制）
      let uploadedCount = 0
      let productId = null

      for (let i = 0; i < images.length; i++) {
        const isFirst = i === 0
        
        const formData = isFirst ? {
          name: form.name,
          description: form.description,
          price: form.price,
          quantity: '1',  // 默认数量为1
          tag: form.category,
          condition: form.condition
        } : {}

        try {
          const result = await new Promise((resolve, reject) => {
            wx.uploadFile({
              url: api.baseURL + '/product/upload',
              filePath: images[i],
              name: 'images',
              formData: formData,
              success: (res) => {
                if (res.statusCode === 200) {
                  try {
                    const data = JSON.parse(res.data)
                    resolve(data)
                  } catch (e) {
                    resolve({ success: true })
                  }
                } else {
                  reject(new Error('上传失败'))
                }
              },
              fail: reject
            })
          })

          uploadedCount++
          if (isFirst && result.product_id) {
            productId = result.product_id
          }

          wx.showLoading({ title: `上传中 ${uploadedCount}/${images.length}` })
        } catch (error) {
          console.error('图片上传失败:', error)
          throw error
        }
      }

      wx.hideLoading()
      
      wx.showToast({
        title: '发布成功',
        icon: 'success'
      })

      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
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
  }
})
