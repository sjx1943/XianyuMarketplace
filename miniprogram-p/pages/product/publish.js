// pages/product/publish.js
const api = require('../../utils/api.js')
const cloudStorage = require('../../utils/cloudStorage.js')
const contentSecurity = require('../../utils/contentSecurity.js')
const app = getApp()

const USE_CLOUD_STORAGE = true

function isCloudStorageAvailable() {
  return USE_CLOUD_STORAGE && app.globalData.cloudInitDone && app.globalData.cloudEnabled
}

Page({
  data: {
    images: [],
    form: {
      name: '',
      price: '',
      quantity: '1',
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

  // 压缩单张图片
  compressImage(filePath) {
    return new Promise((resolve) => {
      wx.compressImage({
        src: filePath,
        quality: 60,
        success: (res) => {
          console.log('图片压缩成功:', filePath, '->', res.tempFilePath)
          resolve(res.tempFilePath)
        },
        fail: (err) => {
          console.warn('图片压缩失败，使用原图:', err)
          resolve(filePath)
        }
      })
    })
  },

  // 上传单张图片
  uploadSingleImage(filePath, formData, token) {
    return new Promise((resolve, reject) => {
      let filename = filePath.split('/').pop() || `image_${Date.now()}.jpg`
      filename = filename.replace(/[^\w\-\.]/g, '_')
      
      wx.uploadFile({
        url: api.baseURL + '/api/miniprogram/product/upload',
        filePath: filePath,
        name: 'images',
        formData: {
          ...formData,
          filename: filename
        },
        header: {
          'Authorization': 'Bearer ' + token
        },
        success: (res) => {
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

    if (form.price !== '' && (isNaN(parseFloat(form.price)) || parseFloat(form.price) < 0)) {
      wx.showToast({
        title: '请输入正确的价格',
        icon: 'none'
      })
      return false
    }

    if (!form.quantity || parseInt(form.quantity) <= 0) {
      wx.showToast({
        title: '请输入正确的商品数量',
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
      const { images, form } = this.data
      const token = wx.getStorageSync('token') || ''
      
      if (!token) {
        wx.showToast({
          title: '登录已过期，请重新登录',
          icon: 'none'
        })
        setTimeout(() => {
          wx.navigateTo({
            url: '/pages/login/login'
          })
        }, 1500)
        this.setData({ submitting: false })
        return
      }
      
      const isValid = await contentSecurity.validateProductContent({
        name: form.name,
        description: form.description
      })
      
      if (!isValid) {
        this.setData({ submitting: false })
        return
      }
      
      // 步骤1: 并行压缩所有图片
      console.log('开始压缩图片...')
      const compressPromises = images.map(img => this.compressImage(img))
      const compressedImages = await Promise.all(compressPromises)
      console.log('图片压缩完成')

      // 步骤2: 先检测所有图片，只有通过的才上传
      console.log('开始检测图片安全性...')
      const securityCheckPromises = compressedImages.map(img => 
        contentSecurity.checkImageWithBase64(img, 3)
      )
      const securityResults = await Promise.all(securityCheckPromises)
      
      // 检查是否有违规图片
      const violationIndex = securityResults.findIndex(result => !result.safe && !result.skipped)
      if (violationIndex !== -1) {
        const violation = securityResults[violationIndex]
        wx.showToast({
          title: violation.reason || '图片含有违规内容，请更换',
          icon: 'none',
          duration: 3000
        })
        this.setData({ submitting: false })
        return
      }
      console.log('所有图片检测通过')

      if (isCloudStorageAvailable()) {
        await this.submitWithCloudStorage(compressedImages, form, token)
      } else {
        await this.submitWithBackendUpload(compressedImages, form, token)
      }

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
      console.error('发布失败:', error)
      wx.showToast({
        title: error.message || '发布失败，请重试',
        icon: 'none'
      })
    } finally {
      this.setData({ submitting: false })
    }
  },

  // 使用云托管存储上传
  async submitWithCloudStorage(compressedImages, form, token) {
    console.log('使用云托管上传...')
    
    // 步骤1: 并行上传所有图片到云存储（uploadImages内部管理loading）
    const uploadResults = await cloudStorage.uploadImages(compressedImages, 'products')
    
    const successUploads = uploadResults.filter(r => r.fileID)
    if (successUploads.length === 0) {
      throw new Error('图片上传失败，请重试')
    }
    
    // 步骤2: 将 fileIDs 发送到后端创建商品
    const imageFileIDs = successUploads.map(r => r.fileID)
    const imageTempUrls = successUploads.map(r => r.tempUrl)
    
    console.log('创建商品，图片数量:', imageFileIDs.length)
    
    const result = await api.post('/api/miniprogram/product/create', {
      name: form.name,
      description: form.description || '',
      price: String(form.price),
      quantity: String(form.quantity),
      tag: form.category,
      condition: form.condition,
      image_urls: imageFileIDs,
      image_temp_urls: imageTempUrls
    })
    
    if (!result.success) {
      throw new Error(result.error || '创建商品失败')
    }
    
    console.log('商品创建成功, ID:', result.product_id)
    
    imageTempUrls.forEach(url => {
      if (url) {
        contentSecurity.checkImage(url, 3).then(res => {
          console.log('商品图片安全检测已提交:', res)
        }).catch(err => {
          console.warn('商品图片安全检测失败:', err)
        })
      }
    })
  },

  // 使用后端上传（原有方式）
  async submitWithBackendUpload(compressedImages, form, token) {
    // 步骤2: 上传第一张图片并创建商品
    const firstFormData = {
      name: form.name,
      description: form.description || '',
      price: String(form.price),
      quantity: String(form.quantity),
      tag: form.category,
      condition: form.condition
    }
    
    console.log('上传第一张图片并创建商品...')
    const firstResult = await this.uploadSingleImage(compressedImages[0], firstFormData, token)
    const productId = firstResult.product_id
    console.log('商品创建成功, ID:', productId)

    // 步骤3: 并行上传剩余图片（如果有）
    if (compressedImages.length > 1) {
      console.log('并行上传剩余图片...')
      const remainingUploads = compressedImages.slice(1).map(img => 
        this.uploadSingleImage(img, { product_id: String(productId) }, token)
      )
      await Promise.all(remainingUploads)
      console.log('所有图片上传完成')
    }
  }
})
