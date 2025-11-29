const api = require('../../utils/api.js')
const config = require('../../utils/config.js')

Page({
  data: {
    products: [],
    loading: false,
    page: 1,
    pageSize: 20,
    hasMore: true,
    categories: ['全部', '电子数码', '生活用品', '服装鞋帽', '图书文具', '运动健身', '母婴用品', '其他'],
    currentCategory: '全部',
    searchKeyword: ''
  },

  onLoad(options) {
    if (options.category) {
      this.setData({ currentCategory: options.category })
    }
    this.loadProducts()
  },

  onShow() {
    this.setData({ page: 1, products: [], hasMore: true })
    this.loadProducts()
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

    return api.getProducts(params).then(res => {
      const newProducts = res.products || res.data || []
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
