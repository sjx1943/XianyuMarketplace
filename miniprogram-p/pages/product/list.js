const api = require('../../utils/api.js')
const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')
const cloudStorage = require('../../utils/cloudStorage.js')

const CACHE_KEY = 'products_cache'
const VERSION_KEY = 'products_version'

Page({
  data: {
    products: [],
    loading: false,
    page: 1,
    pageSize: 20,
    hasMore: true,
    categories: ['全部'],
    currentCategory: '全部',
    searchKeyword: '',
    isCheckingVersion: false
  },

  onLoad(options) {
    if (options.category) {
      this.setData({ currentCategory: options.category })
    }
    this.loadActiveTags()
    
    this.unreadCountInterval = null
  },

  onShow() {
    const category = this.data.currentCategory
    const keyword = this.data.searchKeyword
    
    if (keyword) {
      this.setData({ page: 1, products: [], hasMore: true })
      this.loadProducts()
      return
    }
    
    const cacheData = this.loadFromCache(category)
    
    if (cacheData && cacheData.products && cacheData.products.length > 0) {
      this.setData({
        products: cacheData.products,
        page: cacheData.page || 1,
        hasMore: cacheData.hasMore !== false,
        loading: false
      })
      
      this.checkAndRefreshIfNeeded(category)
    } else {
      this.setData({ page: 1, products: [], hasMore: true })
      this.loadProducts()
    }
    
    this.loadActiveTags().catch(err => console.error('加载标签失败:', err))
    
    const app = getApp()
    if (app.globalData.isLogin) {
      app.getUnreadCount()
      
      if (!this.unreadCountInterval) {
        this.unreadCountInterval = setInterval(() => {
          app.getUnreadCount()
        }, 30000)
      }
    }
  },
  
  onHide() {
    if (this.unreadCountInterval) {
      clearInterval(this.unreadCountInterval)
      this.unreadCountInterval = null
    }
  },

  loadFromCache(category) {
    try {
      const allCache = wx.getStorageSync(CACHE_KEY) || {}
      return allCache[category] || null
    } catch (e) {
      console.error('读取缓存失败:', e)
      return null
    }
  },

  saveToCache(category, data) {
    if (this.data.searchKeyword) return
    
    try {
      const allCache = wx.getStorageSync(CACHE_KEY) || {}
      allCache[category] = {
        products: data.products,
        page: data.page,
        hasMore: data.hasMore,
        timestamp: Date.now()
      }
      wx.setStorageSync(CACHE_KEY, allCache)
    } catch (e) {
      console.error('保存缓存失败:', e)
    }
  },

  saveVersionInfo(category, versionInfo) {
    try {
      const allVersion = wx.getStorageSync(VERSION_KEY) || {}
      allVersion[category] = {
        total: versionInfo.total,
        latest_time: versionInfo.latest_time,
        timestamp: Date.now()
      }
      wx.setStorageSync(VERSION_KEY, allVersion)
    } catch (e) {
      console.error('保存版本信息失败:', e)
    }
  },

  getVersionInfo(category) {
    try {
      const allVersion = wx.getStorageSync(VERSION_KEY) || {}
      return allVersion[category] || null
    } catch (e) {
      console.error('读取版本信息失败:', e)
      return null
    }
  },

  async checkAndRefreshIfNeeded(category) {
    if (this.data.isCheckingVersion || this.data.loading) return
    
    this.setData({ isCheckingVersion: true })
    
    try {
      const res = await api.getProductsVersion(category)
      if (!res.success) {
        this.setData({ isCheckingVersion: false })
        return
      }
      
      const serverVersion = {
        total: res.total,
        latest_time: res.latest_time
      }
      
      const localVersion = this.getVersionInfo(category)
      
      const needRefresh = !localVersion || 
        localVersion.total !== serverVersion.total || 
        localVersion.latest_time !== serverVersion.latest_time
      
      if (needRefresh) {
        console.log('📦 检测到商品列表有更新，静默刷新...')
        
        this.setData({ 
          page: 1, 
          hasMore: true,
          loading: false
        })
        
        this._pendingVersionInfo = { category, serverVersion }
        
        await this.loadProducts(true)
        
        this.setData({ isCheckingVersion: false })
      } else {
        console.log('✅ 商品列表无变化，继续使用缓存')
        this.setData({ isCheckingVersion: false })
      }
    } catch (err) {
      console.error('检查版本失败:', err)
      this.setData({ isCheckingVersion: false })
    }
  },

  loadActiveTags() {
    return api.getActiveTags().then(res => {
      if (res.success && res.tags) {
        const categories = ['全部', ...res.tags]
        this.setData({ categories: categories })
        console.log('📌 动态加载标签:', categories)
      }
    }).catch(err => {
      console.error('加载标签失败:', err)
    })
  },

  onPullDownRefresh() {
    this.clearCacheForCategory(this.data.currentCategory)
    this.setData({ page: 1, products: [], hasMore: true, searchKeyword: '' })
    this.loadProducts().then(() => {
      wx.stopPullDownRefresh()
    })
  },

  clearCacheForCategory(category) {
    try {
      const allCache = wx.getStorageSync(CACHE_KEY) || {}
      delete allCache[category]
      wx.setStorageSync(CACHE_KEY, allCache)
      
      const allVersion = wx.getStorageSync(VERSION_KEY) || {}
      delete allVersion[category]
      wx.setStorageSync(VERSION_KEY, allVersion)
    } catch (e) {
      console.error('清除缓存失败:', e)
    }
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadProducts()
    }
  },

  loadProducts(silentRefresh = false) {
    if (this.data.loading) return Promise.resolve()
    
    this.setData({ loading: true })
    
    const timeoutPromise = new Promise((_, reject) => 
      setTimeout(() => reject(new Error('加载超时')), 5000)
    )
    
    const params = {
      page: this.data.page,
      page_size: this.data.pageSize
    }
    
    const category = this.data.currentCategory
    if (category !== '全部') {
      params.tag = category
    }
    
    const keyword = this.data.searchKeyword
    if (keyword) {
      params.keyword = keyword
    }

    return Promise.race([
      api.getProducts(params),
      timeoutPromise
    ]).then(async res => {
      const rawProducts = res.products || res.data || []
      let newProducts = rawProducts.map(item => ({
        ...item,
        image: getImageUrl(item.image)
      }))
      
      // 处理云存储图片（cloud:// 格式需要转换为临时 URL）
      const cloudFileIDs = newProducts
        .filter(p => p.image && p.image.startsWith('cloud://'))
        .map(p => p.image)
      
      if (cloudFileIDs.length > 0) {
        try {
          const tempUrls = await cloudStorage.getTempFileURL(cloudFileIDs)
          const urlMap = {}
          tempUrls.forEach(item => {
            if (item.fileID && item.tempFileURL) {
              urlMap[item.fileID] = item.tempFileURL
            }
          })
          newProducts = newProducts.map(p => ({
            ...p,
            image: (p.image && urlMap[p.image]) || p.image
          }))
        } catch (err) {
          console.error('转换云存储图片URL失败:', err)
        }
      }
      
      const products = this.data.page === 1 ? newProducts : [...this.data.products, ...newProducts]
      const hasMore = newProducts.length >= this.data.pageSize
      const nextPage = this.data.page + 1
      
      this.setData({
        products: products,
        loading: false,
        hasMore: hasMore,
        page: nextPage
      })
      
      if (!keyword && this.data.page <= 2) {
        this.saveToCache(category, {
          products: products,
          page: nextPage,
          hasMore: hasMore
        })
        
        if (this._pendingVersionInfo && this._pendingVersionInfo.category === category) {
          this.saveVersionInfo(category, this._pendingVersionInfo.serverVersion)
          this._pendingVersionInfo = null
        } else {
          api.getProductsVersion(category).then(verRes => {
            if (verRes.success) {
              this.saveVersionInfo(category, {
                total: verRes.total,
                latest_time: verRes.latest_time
              })
            }
          }).catch(() => {})
        }
      }
    }).catch(err => {
      console.error('加载商品失败:', err)
      this.setData({ loading: false })
      if (!silentRefresh) {
        wx.showToast({
          title: '加载失败',
          icon: 'none'
        })
      }
    })
  },

  onCategoryChange(e) {
    const category = e.currentTarget.dataset.category
    
    this.setData({ searchKeyword: '' })
    
    const cacheData = this.loadFromCache(category)
    
    if (cacheData && cacheData.products && cacheData.products.length > 0) {
      this.setData({
        currentCategory: category,
        products: cacheData.products,
        page: cacheData.page || 1,
        hasMore: cacheData.hasMore !== false,
        loading: false
      })
      
      this.checkAndRefreshIfNeeded(category)
    } else {
      this.setData({
        currentCategory: category,
        page: 1,
        products: [],
        hasMore: true
      })
      this.loadProducts()
    }
  },

  onSearchInput(e) {
    this.setData({ searchKeyword: e.detail.value })
  },

  onSearch() {
    this.setData({
      page: 1,
      products: [],
      hasMore: true
    })
    this.loadProducts()
  },

  goToDetail(e) {
    const productId = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/product/detail?id=${productId}`
    })
  },

  goToPublish() {
    wx.navigateTo({
      url: '/pages/product/publish'
    })
  }
})
