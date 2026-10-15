// pages/product/my-list.js
const api = require('../../utils/api.js')
const { getImageUrl } = require('../../utils/config.js')
const cloudStorage = require('../../utils/cloudStorage.js')
const app = getApp()

// API 请求超时时间（毫秒）
const API_TIMEOUT = 5000

Page({
  data: {
    products: [],
    loading: false,  // 初始值改为 false
    currentTab: 'all',
    tabs: [
      { key: 'all', name: '全部', apiKey: 'all' },
      { key: 'showing', name: '展示中', apiKey: '在售' },
      { key: 'ended', name: '已结束', apiKey: '已售完' }
    ],
    stats: {
      all: 0,
      selling: 0,
      sold: 0
    }
  },

  // 防止重复加载
  isLoading: false,
  lastLoadTime: 0,
  cachedAllProducts: null,

  onLoad(options) {
    const { type } = options
    if (type === 'selling') {
      this.setData({ currentTab: 'showing' })
    } else if (type === 'sold') {
      this.setData({ currentTab: 'ended' })
    }
    
    this.loadMyProducts()
  },

  onShow() {
    // 智能加载：距离上次加载超过 2 秒才重新加载
    const now = Date.now()
    if (now - this.lastLoadTime > 2000) {
      this.loadMyProducts()
    }
  },

  onPullDownRefresh() {
    // 下拉刷新时强制重新加载
    this.cachedAllProducts = null
    this.loadMyProducts().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadMyProducts() {
    // 防止重复加载
    if (this.isLoading) return Promise.resolve()
    this.isLoading = true
    this.lastLoadTime = Date.now()
    
    try {
      this.setData({ loading: true })
      
      // 创建带超时的 API 请求辅助函数
      const fetchWithTimeout = (promise) => {
        const timeoutPromise = new Promise((_, reject) => 
          setTimeout(() => reject(new Error('请求超时')), API_TIMEOUT)
        )
        return Promise.race([promise, timeoutPromise])
      }
      
      // 将前端显示的tab key转换为后端API需要的key
      const currentTab = this.data.currentTab
      const tabConfig = this.data.tabs.find(t => t.key === currentTab)
      const apiKey = tabConfig ? tabConfig.apiKey : 'all'
      
      const data = await fetchWithTimeout(api.getMyProducts(apiKey))
      
      if (data && data.success && data.products) {
        let products = data.products.map(p => ({
          ...p,
          imageUrl: p.image ? getImageUrl(p.image) : (p.images && p.images[0] ? getImageUrl(p.images[0]) : ''),
          priceText: p.price > 0 ? `出手价 ${p.price}` : (p.price === 0 || p.price === '0' ? '免费' : '面议')
        }))
        
        // 处理云存储图片（cloud:// 格式需要转换为临时 URL）
        const cloudFileIDs = products
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
            products = products.map(p => ({
              ...p,
              imageUrl: (p.imageUrl && urlMap[p.imageUrl]) || p.imageUrl
            }))
          } catch (err) {
            console.error('转换云存储图片URL失败:', err)
          }
        }
        
        // 使用缓存避免重复请求全部商品
        let allProducts = this.cachedAllProducts
        if (!allProducts) {
          const allData = await fetchWithTimeout(api.getMyProducts('all'))
          allProducts = allData.success ? allData.products : []
          this.cachedAllProducts = allProducts
        }
        
        const sellingCount = allProducts.filter(p => p.status === '在售' || p.status === '展示中').length
        const soldCount = allProducts.filter(p => p.status === '已售完' || p.status === '已结束' || p.quantity === 0).length
        
        this.setData({
          products: products,
          loading: false,
          stats: {
            all: allProducts.length,
            selling: sellingCount,
            sold: soldCount
          }
        })
      } else {
        this.setData({ products: [], loading: false })
      }
    } catch (error) {
      console.error('加载我的闲置失败:', error)
      this.setData({ loading: false })
      // 超时提示
      if (error.message === '请求超时') {
        wx.showToast({
          title: '加载超时，请下拉刷新',
          icon: 'none'
        })
      } else {
        wx.showToast({
          title: '加载失败',
          icon: 'none'
        })
      }
    } finally {
      this.isLoading = false
    }
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    if (tab !== this.data.currentTab) {
      this.setData({ currentTab: tab })
      this.loadMyProducts()
    }
  },

  viewDetail(e) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/product/detail?id=${id}`
    })
  },

  editProduct(e) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/product/edit?id=${id}`
    })
  },

  deleteProduct(e) {
    const { id, name } = e.currentTarget.dataset
    
    wx.showModal({
      title: '确认删除',
      content: `确定要删除物品"${name}"吗？删除后无法恢复。`,
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.deleteProduct(id)
            wx.showToast({
              title: '删除成功',
              icon: 'success'
            })
            this.loadMyProducts()
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

  goPublish() {
    wx.navigateTo({
      url: '/pages/product/publish'
    })
  }
})
