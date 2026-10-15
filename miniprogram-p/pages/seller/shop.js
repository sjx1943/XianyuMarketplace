// pages/seller/shop.js
const api = require('../../utils/api.js')
const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')
const app = getApp()

const API_TIMEOUT = 5000

Page({
  data: {
    sellerId: null,
    seller: {},
    products: [],
    loading: false,
    isMe: false,
    showActionMenu: false
  },

  onLoad(options) {
    const { id, room } = options
    
    if (id) {
      this.setData({ sellerId: id })
      this.loadSellerData(id)
    } else if (room) {
      wx.setNavigationBarTitle({ title: `房间号: ${room}` })
    }
    
    const userInfo = wx.getStorageSync('userInfo')
    if (userInfo && userInfo.id) {
      this.setData({ isMe: String(userInfo.id) === String(id) })
    }
  },

  onShow() {
    if (this.data.sellerId) {
      this.loadSellerData(this.data.sellerId)
    }
  },

  onPullDownRefresh() {
    if (this.data.sellerId) {
      this.loadSellerData(this.data.sellerId).finally(() => {
        wx.stopPullDownRefresh()
      })
    } else {
      wx.stopPullDownRefresh()
    }
  },

  async loadSellerData(sellerId) {
    try {
      this.setData({ loading: true })
      
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('请求超时')), API_TIMEOUT)
      )
      
      const [sellerRes, productsRes] = await Promise.all([
        Promise.race([api.getSellerInfo(sellerId), timeoutPromise]),
        Promise.race([api.getSellerProducts(sellerId), timeoutPromise])
      ])
      
      if (sellerRes && sellerRes.success) {
        const seller = sellerRes.seller
        seller.avatarUrl = seller.wechat_avatar ? getImageUrl(seller.wechat_avatar) : getDefaultAvatarUrl()
        this.setData({ seller })
        
        wx.setNavigationBarTitle({ 
          title: seller.wechat_nickname || seller.username || 'TA的主页'
        })
      }
      
      if (productsRes && productsRes.success) {
        const products = productsRes.products.map(p => ({
          ...p,
          imageUrl: p.image ? getImageUrl(p.image) : ''
        }))
        this.setData({ products })
      }
      
      this.setData({ loading: false })
    } catch (error) {
      console.error('加载邻居数据失败:', error)
      this.setData({ loading: false })
      if (error.message === '请求超时') {
        wx.showToast({
          title: '加载超时，请重试',
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

  onChat() {
    if (!app.globalData.isLogin) {
      wx.navigateTo({ url: '/pages/login/login' })
      return
    }
    
    const { seller } = this.data
    const roomNumber = encodeURIComponent(seller.room_number || '未设置')
    const friendName = encodeURIComponent(seller.wechat_nickname || seller.username || '')
    
    wx.navigateTo({
      url: `/pages/chat/room?friendId=${seller.id}&roomNumber=${roomNumber}&friendName=${friendName}`
    })
  },

  showActionSheet() {
    this.setData({ showActionMenu: true })
  },

  hideActionSheet() {
    this.setData({ showActionMenu: false })
  },

  onBlockUser() {
    this.hideActionSheet()
    
    wx.showModal({
      title: '加入黑名单',
      content: '加入黑名单后，将不再看到对方的物品和消息。确定要加入吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.addToBlacklist(this.data.sellerId)
            wx.showToast({
              title: '已加入黑名单',
              icon: 'success'
            })
            // 清除商品列表缓存，确保拉黑用户的物品不再显示
            wx.removeStorageSync('products_cache')
            wx.removeStorageSync('products_version')
            setTimeout(() => {
              wx.navigateBack()
            }, 1500)
          } catch (error) {
            wx.showToast({
              title: error.message || '操作失败',
              icon: 'none'
            })
          }
        }
      }
    })
  },

  onAvatarError() {
    this.setData({
      'seller.avatarUrl': getDefaultAvatarUrl()
    })
  }
})
