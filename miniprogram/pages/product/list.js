const api = require('../../utils/api.js')
const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')

Page({
  data: {
    products: [],
    loading: false,
    page: 1,
    pageSize: 20,
    hasMore: true,
    categories: ['全部'],
    currentCategory: '全部',
    searchKeyword: ''
  },

  onLoad(options) {
    if (options.category) {
      this.setData({ currentCategory: options.category })
    }
    this.loadActiveTags()
    this.loadProducts()
    
    // 初始化定时器引用
    this.unreadCountInterval = null
  },

  onShow() {
    this.setData({ page: 1, products: [], hasMore: true })
    // 并行加载标签和商品，但仅在真正需要时加载
    Promise.all([
      this.loadActiveTags().catch(err => console.error('加载标签失败:', err)),
      this.loadProducts()
    ]).catch(err => console.error('加载失败:', err))
    
    // 只在用户已登录时才启动定时器
    const app = getApp()
    if (app.globalData.isLogin) {
      // 立即刷新一次未读计数（订单+聊天）
      app.getUnreadCount()
      
      // 每30秒刷新一次未读计数
      if (!this.unreadCountInterval) {
        this.unreadCountInterval = setInterval(() => {
          app.getUnreadCount()
        }, 30000)
      }
    }
  },
  
  onHide() {
    // 页面隐藏时清除定时器
    if (this.unreadCountInterval) {
      clearInterval(this.unreadCountInterval)
      this.unreadCountInterval = null
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
    this.setData({ page: 1, products: [], hasMore: true })
    this.loadProducts().then(() => {
      wx.stopPullDownRefresh()
    })
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadProducts()
    }
  },

  loadProducts() {
    if (this.data.loading) return Promise.resolve()
    
    this.setData({ loading: true })
    
    // 添加 5 秒超时，防止 API 卡住
    const timeoutPromise = new Promise((_, reject) => 
      setTimeout(() => reject(new Error('加载超时')), 5000)
    )
    
    const params = {
      page: this.data.page,
      page_size: this.data.pageSize
    }
    
    if (this.data.currentCategory !== '全部') {
      params.tag = this.data.currentCategory
    }
    
    if (this.data.searchKeyword) {
      params.keyword = this.data.searchKeyword
    }

    return Promise.race([
      api.getProducts(params),
      timeoutPromise
    ]).then(res => {
      const rawProducts = res.products || res.data || []
      // 处理每个商品的图片URL为完整路径
      const newProducts = rawProducts.map(item => ({
        ...item,
        image: getImageUrl(item.image)
      }))
      const products = this.data.page === 1 ? newProducts : [...this.data.products, ...newProducts]
      
      this.setData({
        products: products,
        loading: false,
        hasMore: newProducts.length >= this.data.pageSize,
        page: this.data.page + 1
      })
    }).catch(err => {
      console.error('加载商品失败:', err)
      this.setData({ loading: false })
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      })
    })
  },

  onCategoryChange(e) {
    const category = e.currentTarget.dataset.category
    this.setData({
      currentCategory: category,
      page: 1,
      products: [],
      hasMore: true
    })
    this.loadProducts()
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
