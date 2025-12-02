// pages/product/my-list.js
const api = require('../../utils/api.js')
const { getImageUrl } = require('../../utils/config.js')
const app = getApp()

// API 请求超时时间（毫秒）
const API_TIMEOUT = 5000

Page({
  data: {
    products: [],
    loading: false,  // 初始值改为 false
    currentTab: 'all',
    tabs: [
      { key: 'all', name: '全部' },
      { key: '在售', name: '在售' },
      { key: '已售完', name: '已售' }
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
      this.setData({ currentTab: '在售' })
    } else if (type === 'sold') {
      this.setData({ currentTab: '已售完' })
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
      
      const data = await fetchWithTimeout(api.getMyProducts(this.data.currentTab))
      
      if (data && data.success && data.products) {
        const products = data.products.map(p => ({
          ...p,
          imageUrl: p.image ? getImageUrl(p.image) : (p.images && p.images[0] ? getImageUrl(p.images[0]) : ''),
          priceText: `¥${p.price}`
        }))
        
        // 使用缓存避免重复请求全部商品
        let allProducts = this.cachedAllProducts
        if (!allProducts) {
          const allData = await fetchWithTimeout(api.getMyProducts('all'))
          allProducts = allData.success ? allData.products : []
          this.cachedAllProducts = allProducts
        }
        
        const sellingCount = allProducts.filter(p => p.status === '在售').length
        const soldCount = allProducts.filter(p => p.status === '已售完').length
        
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
      console.error('加载我的商品失败:', error)
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
      content: `确定要删除商品"${name}"吗？删除后无法恢复。`,
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
