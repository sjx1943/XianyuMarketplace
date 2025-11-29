// pages/index/index.js
const app = getApp()

Page({
  data: {
    userInfo: null,
    hasUserInfo: false,
    canIUse: wx.canIUse('button.open-type.getUserInfo'),
    canIUseGetUserProfile: false,
    searchValue: '',
    categories: [
      { id: 1, name: '全部', icon: '🔥' },
      { id: 2, name: '数码', icon: '📱' },
      { id: 3, name: '家电', icon: '🏠' },
      { id: 4, name: '服装', icon: '👕' },
      { id: 5, name: '图书', icon: '📚' },
      { id: 6, name: '运动', icon: '⚽' },
      { id: 7, name: '美妆', icon: '💄' },
      { id: 8, name: '其他', icon: '📦' }
    ],
    banners: [
      {
        id: 1,
        icon: '🔥',
        color: 'linear-gradient(135deg, #ff6b35, #f7931e)',
        title: '热门商品推荐'
      },
      {
        id: 2,
        icon: '🆕',
        color: 'linear-gradient(135deg, #667eea, #764ba2)',
        title: '新品上架'
      },
      {
        id: 3,
        icon: '💰',
        color: 'linear-gradient(135deg, #11998e, #38ef7d)',
        title: '超值好物'
      }
    ],
    hotProducts: [],
    recentProducts: [],
    loading: false,
    refreshing: false
  },

  onLoad() {
    if (wx.getUserProfile) {
      this.setData({
        canIUseGetUserProfile: true
      })
    }
    
    this.checkLoginStatus()
    this.loadData()
  },

  onShow() {
    this.checkLoginStatus()
    this.getTabBar() && this.getTabBar().setData({
      selected: 0
    })
  },

  onPullDownRefresh() {
    this.setData({ refreshing: true })
    this.loadData().then(() => {
      wx.stopPullDownRefresh()
      this.setData({ refreshing: false })
    })
  },

  onReachBottom() {
    this.loadMoreProducts()
  },

  checkLoginStatus() {
    this.setData({
      userInfo: app.globalData.userInfo,
      hasUserInfo: app.globalData.isLogin
    })
  },

  async loadData() {
    this.setData({ loading: true })
    
    try {
      await Promise.all([
        this.loadHotProducts(),
        this.loadRecentProducts()
      ])
    } catch (error) {
      console.error('加载数据失败:', error)
      app.showToast('加载失败，请重试')
    } finally {
      this.setData({ loading: false })
    }
  },

  async loadHotProducts() {
    try {
      const res = await app.request({
        url: '/product_list',
        data: {
          limit: 6,
          sort: 'hot'
        }
      })
      
      if (res.statusCode === 200) {
        this.setData({
          hotProducts: res.data.slice(0, 6)
        })
      }
    } catch (error) {
      console.error('加载热门商品失败:', error)
    }
  },

  async loadRecentProducts() {
    try {
      const res = await app.request({
        url: '/product_list',
        data: {
          limit: 10,
          sort: 'recent'
        }
      })
      
      if (res.statusCode === 200) {
        this.setData({
          recentProducts: res.data
        })
      }
    } catch (error) {
      console.error('加载最新商品失败:', error)
    }
  },

  async loadMoreProducts() {
    if (this.data.loading) return
    
    this.setData({ loading: true })
    
    try {
      const res = await app.request({
        url: '/product_list',
        data: {
          offset: this.data.recentProducts.length,
          limit: 10,
          sort: 'recent'
        }
      })
      
      if (res.statusCode === 200 && res.data.length > 0) {
        this.setData({
          recentProducts: [...this.data.recentProducts, ...res.data]
        })
      }
    } catch (error) {
      console.error('加载更多商品失败:', error)
    } finally {
      this.setData({ loading: false })
    }
  },

  onSearchInput(e) {
    this.setData({
      searchValue: e.detail.value
    })
  },

  onSearch() {
    const { searchValue } = this.data
    if (!searchValue.trim()) {
      app.showToast('请输入搜索关键词')
      return
    }
    
    wx.navigateTo({
      url: `/pages/product/list?search=${encodeURIComponent(searchValue.trim())}`
    })
  },

  onCategoryTap(e) {
    const { category } = e.currentTarget.dataset
    const url = category.id === 1 
      ? '/pages/product/list'
      : `/pages/product/list?category=${encodeURIComponent(category.name)}`
    
    wx.navigateTo({ url })
  },

  onBannerTap(e) {
    const { banner } = e.currentTarget.dataset
    console.log('点击轮播图:', banner)
    // 可以跳转到相应的活动页面
  },

  onProductTap(e) {
    const { product } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/product/detail?id=${product.id}`
    })
  },

  onPublishTap() {
    if (!app.globalData.isLogin) {
      wx.navigateTo({
        url: '/pages/login/login'
      })
      return
    }
    
    wx.navigateTo({
      url: '/pages/product/publish'
    })
  },

  getUserProfile() {
    wx.getUserProfile({
      desc: '用于完善用户资料',
      success: (res) => {
        this.setData({
          userInfo: res.userInfo,
          hasUserInfo: true
        })
        
        // 这里可以将用户信息发送到服务器
        this.updateUserProfile(res.userInfo)
      },
      fail: (err) => {
        console.error('获取用户信息失败:', err)
      }
    })
  },

  async updateUserProfile(userInfo) {
    try {
      await app.request({
        url: '/api/miniprogram/update_profile',
        method: 'POST',
        data: {
          avatar: userInfo.avatarUrl,
          nickname: userInfo.nickName
        }
      })
    } catch (error) {
      console.error('更新用户资料失败:', error)
    }
  },

  getUserInfo(e) {
    console.log(e)
    app.globalData.userInfo = e.detail.userInfo
    this.setData({
      userInfo: e.detail.userInfo,
      hasUserInfo: true
    })
  }
})
