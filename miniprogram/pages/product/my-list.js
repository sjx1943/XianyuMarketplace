// pages/product/my-list.js
const api = require('../../utils/api.js')
const { getImageUrl } = require('../../utils/config.js')
const app = getApp()

Page({
  data: {
    products: [],
    loading: true,
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
    this.loadMyProducts()
  },

  onPullDownRefresh() {
    this.loadMyProducts().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadMyProducts() {
    try {
      this.setData({ loading: true })
      
      const data = await api.getMyProducts(this.data.currentTab)
      
      if (data && data.success && data.products) {
        const products = data.products.map(p => ({
          ...p,
          imageUrl: p.image ? getImageUrl(p.image) : (p.images && p.images[0] ? getImageUrl(p.images[0]) : ''),
          priceText: `¥${p.price}`
        }))
        
        const allData = await api.getMyProducts('all')
        const allProducts = allData.success ? allData.products : []
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
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      })
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
