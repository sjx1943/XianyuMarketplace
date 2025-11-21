// 分享功能工具类

/**
 * 分享商品
 * @param {Object} product - 商品信息
 * @returns {Object} 分享配置
 */
function shareProduct(product) {
  return {
    title: `【闲置】${product.name} - 仅售¥${product.price}`,
    path: `/pages/product/detail?id=${product.id}`,
    imageUrl: product.images && product.images[0] ? product.images[0] : '/images/default-product.png'
  }
}

/**
 * 分享到朋友圈（商品）
 * @param {Object} product - 商品信息
 * @returns {Object} 朋友圈分享配置
 */
function shareProductToTimeline(product) {
  return {
    title: `【闲置】${product.name} - 仅售¥${product.price}，快来看看！`,
    query: `id=${product.id}`,
    imageUrl: product.images && product.images[0] ? product.images[0] : '/images/default-product.png'
  }
}

/**
 * 分享小程序首页
 * @returns {Object} 分享配置
 */
function shareApp() {
  return {
    title: '小区二手市场 - 邻里闲置交易平台',
    path: '/pages/index/index',
    imageUrl: '/images/share-banner.jpg'
  }
}

/**
 * 分享小程序到朋友圈
 * @returns {Object} 朋友圈分享配置
 */
function shareAppToTimeline() {
  return {
    title: '小区二手市场 - 发现你身边的闲置好物',
    query: '',
    imageUrl: '/images/share-banner.jpg'
  }
}

/**
 * 分享邀请
 * @param {String} userId - 邀请人ID
 * @returns {Object} 分享配置
 */
function shareInvite(userId) {
  return {
    title: '快来加入我们的小区二手市场，闲置物品轻松转让！',
    path: `/pages/index/index?inviter=${userId}`,
    imageUrl: '/images/invite-banner.jpg'
  }
}

/**
 * 生成分享海报（商品）
 * @param {Object} product - 商品信息
 * @returns {Promise} 返回海报图片路径
 */
function generateProductPoster(product) {
  return new Promise((resolve, reject) => {
    wx.showLoading({ title: '生成中...' })

    // 创建canvas绘制海报
    const ctx = wx.createCanvasContext('posterCanvas')
    
    // 绘制背景
    ctx.setFillStyle('#ffffff')
    ctx.fillRect(0, 0, 750, 1200)
    
    // 绘制商品图片
    const imageUrl = product.images && product.images[0] ? product.images[0] : '/images/default-product.png'
    ctx.drawImage(imageUrl, 50, 50, 650, 650)
    
    // 绘制商品名称
    ctx.setFillStyle('#333333')
    ctx.setFontSize(36)
    ctx.fillText(product.name, 50, 750)
    
    // 绘制价格
    ctx.setFillStyle('#ff6b35')
    ctx.setFontSize(48)
    ctx.fillText(`¥${product.price}`, 50, 850)
    
    // 绘制小程序码
    // 注意：实际项目中需要从后端获取小程序码
    ctx.drawImage('/images/qrcode.jpg', 525, 950, 175, 175)
    
    // 绘制提示文字
    ctx.setFillStyle('#999999')
    ctx.setFontSize(24)
    ctx.fillText('长按识别小程序码查看详情', 50, 1050)
    
    ctx.draw(false, () => {
      setTimeout(() => {
        wx.canvasToTempFilePath({
          canvasId: 'posterCanvas',
          success: (res) => {
            wx.hideLoading()
            resolve(res.tempFilePath)
          },
          fail: (err) => {
            wx.hideLoading()
            reject(err)
          }
        })
      }, 500)
    })
  })
}

/**
 * 保存图片到相册
 * @param {String} filePath - 图片路径
 */
function saveImageToAlbum(filePath) {
  return new Promise((resolve, reject) => {
    wx.saveImageToPhotosAlbum({
      filePath: filePath,
      success: () => {
        wx.showToast({
          title: '已保存到相册',
          icon: 'success'
        })
        resolve()
      },
      fail: (err) => {
        if (err.errMsg === 'saveImageToPhotosAlbum:fail auth deny') {
          wx.showModal({
            title: '提示',
            content: '需要您授权保存图片到相册',
            success: (res) => {
              if (res.confirm) {
                wx.openSetting()
              }
            }
          })
        } else {
          wx.showToast({
            title: '保存失败',
            icon: 'none'
          })
        }
        reject(err)
      }
    })
  })
}

module.exports = {
  shareProduct,
  shareProductToTimeline,
  shareApp,
  shareAppToTimeline,
  shareInvite,
  generateProductPoster,
  saveImageToAlbum
}
