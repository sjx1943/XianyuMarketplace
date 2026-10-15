// pages/product/blacklist.js
const api = require('../../utils/api.js')
const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')
const app = getApp()

const API_TIMEOUT = 5000

Page({
  data: {
    blacklist: [],
    loading: false
  },

  onLoad() {
    this.loadBlacklist()
  },

  onShow() {
    this.loadBlacklist()
  },

  onPullDownRefresh() {
    this.loadBlacklist().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadBlacklist() {
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
        api.getBlacklist(),
        timeoutPromise
      ])
      
      if (data && data.success && data.blacklist) {
        const blacklist = data.blacklist.map(user => ({
          ...user,
          avatarUrl: user.wechat_avatar ? getImageUrl(user.wechat_avatar) : getDefaultAvatarUrl()
        }))
        
        this.setData({
          blacklist: blacklist,
          loading: false
        })
        console.log('✅ 已加载黑名单:', blacklist)
      } else {
        this.setData({ blacklist: [], loading: false })
      }
    } catch (error) {
      console.error('加载黑名单失败:', error)
      this.setData({ loading: false })
      if (error.message === '请求超时') {
        wx.showToast({
          title: '加载超时，请下拉刷新',
          icon: 'none'
        })
      }
    }
  },

  unblockUser(e) {
    const { id, name } = e.currentTarget.dataset
    
    wx.showModal({
      title: '取消拉黑',
      content: `确定要取消拉黑"${name}"吗？`,
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.removeFromBlacklist(id)
            wx.showToast({
              title: '已取消拉黑',
              icon: 'success'
            })
            this.loadBlacklist()
          } catch (error) {
            wx.showToast({
              title: '操作失败',
              icon: 'none'
            })
            console.error('取消拉黑失败:', error)
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
