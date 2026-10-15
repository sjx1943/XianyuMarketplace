// pages/product/favorites.js
const api = require('../../utils/api.js')
const { getImageUrl } = require('../../utils/config.js')
const cloudStorage = require('../../utils/cloudStorage.js')
const app = getApp()

const API_TIMEOUT = 5000

Page({
  data: {
    favorites: [],
    loading: false
  },

  onLoad() {
    this.loadFavorites()
  },

  onShow() {
    this.loadFavorites()
  },

  onPullDownRefresh() {
    this.loadFavorites().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadFavorites() {
    if (!app.globalData.isLogin) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      })
      return
    }

    try {
      this.setData({ loading: true })
      
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('请求超时')), API_TIMEOUT)
      )
      
      const data = await Promise.race([
        api.getFavorites(),
        timeoutPromise
      ])
      
      if (data && data.success && data.favorites) {
        let favorites = data.favorites.map(p => ({
          ...p,
          imageUrl: p.image ? getImageUrl(p.image) : ''
        }))
        
        // 处理云存储图片（cloud:// 格式需要转换为临时 URL）
        const cloudFileIDs = favorites
          .filter(p => p.imageUrl && p.imageUrl.startsWith('cloud://'))
          .map(p => p.imageUrl)
        
        if (cloudFileIDs.length > 0) {
          try {
            const tempUrls = await cloudStorage.getTempFileURL(cloudFileIDs)
            const urlMap = {}
            tempUrls.forEach(item => {
              if (item.fileID && item.tempFileURL) {
                urlMap[item.fileID] = item.tempFileURL
              }
            })
            favorites = favorites.map(p => ({
              ...p,
              imageUrl: (p.imageUrl && urlMap[p.imageUrl]) || p.imageUrl
            }))
          } catch (err) {
            console.error('转换云存储图片URL失败:', err)
          }
        }
        
        this.setData({
          favorites: favorites,
          loading: false
        })
      } else {
        this.setData({ favorites: [], loading: false })
      }
    } catch (error) {
      console.error('加载收藏失败:', error)
      this.setData({ loading: false })
      if (error.message === '请求超时') {
        wx.showToast({
          title: '加载超时，请下拉刷新',
          icon: 'none'
        })
      }
    }
  },

  viewDetail(e) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/product/detail?id=${id}`
    })
  },

  cancelFavorite(e) {
    const { id, name } = e.currentTarget.dataset
    
    wx.showModal({
      title: '取消收藏',
      content: `确定要取消收藏"${name}"吗？`,
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.removeFavorite(id)
            wx.showToast({
              title: '已取消收藏',
              icon: 'success'
            })
            this.loadFavorites()
          } catch (error) {
            wx.showToast({
              title: '操作失败',
              icon: 'none'
            })
          }
        }
      }
    })
  },

  goToList() {
    wx.switchTab({
      url: '/pages/product/list'
    })
  }
})
