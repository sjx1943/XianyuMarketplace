// pages/order/list.js
const api = require('../../utils/api.js')
const app = getApp()

Page({
  data: {
    activeTab: 0,
    tabs: [
      { name: '我买到的', badge: 0 },
      { name: '我卖出的', badge: 0 }
    ],
    orderList: [],
    loading: true
  },

  onLoad(options) {
    const { tab } = options
    if (tab) {
      this.setData({ activeTab: parseInt(tab) })
    }

    this.checkLoginAndLoad()
  },

  onShow() {
    this.checkLoginAndLoad()
    
    if (this.getTabBar()) {
      this.getTabBar().setData({ selected: 3 })
    }
  },

  onPullDownRefresh() {
    this.loadOrders().then(() => {
      wx.stopPullDownRefresh()
    })
  },

  checkLoginAndLoad() {
    if (!app.globalData.isLogin) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      })
      setTimeout(() => {
        wx.reLaunch({
          url: '/pages/login/login'
        })
      }, 1500)
      return
    }

    this.loadOrders()
  },

  switchTab(e) {
    const { index } = e.currentTarget.dataset
    this.setData({
      activeTab: index
    })
    this.loadOrders()
  },

  async loadOrders() {
    try {
      this.setData({ loading: true })

      const data = await api.getOrderList()

      // 后端返回的数据可能是数组或对象
      const orderList = Array.isArray(data) ? data : (data.orders || [])
      
      // 根据tab过滤：0=买家，1=卖家
      const filteredOrders = orderList.filter(order => {
        if (this.data.activeTab === 0) {
          return order.buyer_id === app.globalData.userInfo?.id
        } else {
          return order.seller_id === app.globalData.userInfo?.id
        }
      })

      this.setData({
        orderList: filteredOrders,
        loading: false
      })

      // 更新未读订单数量
      const unreadCount = filteredOrders.filter(o => o.unread).length
      if (unreadCount > 0) {
        const tabs = this.data.tabs
        tabs[this.data.activeTab].badge = unreadCount
        this.setData({ tabs })
      }
    } catch (error) {
      console.error('加载订单失败:', error)
      this.setData({ loading: false })
    }
  },

  viewOrderDetail(e) {
    const { order } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/order/detail?id=${order.id}`
    })
  },

  async cancelOrder(e) {
    const { order } = e.currentTarget.dataset

    const result = await wx.showModal({
      title: '确认取消',
      content: '确定要取消这个订单吗？'
    })

    if (!result.confirm) return

    try {
      const data = await api.cancelOrder(order.id)

      if (data.success) {
        wx.showToast({
          title: '订单已取消',
          icon: 'success'
        })
        this.loadOrders()
      } else {
        wx.showToast({
          title: data.error || '取消失败',
          icon: 'none'
        })
      }
    } catch (error) {
      console.error('取消订单失败:', error)
      wx.showToast({
        title: '操作失败',
        icon: 'none'
      })
    }
  },

  async confirmOrder(e) {
    const { order } = e.currentTarget.dataset
    const action = order.status === 'pending' ? '发货' : '收货'

    const result = await wx.showModal({
      title: `确认${action}`,
      content: `确定要确认${action}吗？`
    })

    if (!result.confirm) return

    try {
      const data = await api.confirmOrder(order.id)

      if (data.success) {
        wx.showToast({
          title: `已确认${action}`,
          icon: 'success'
        })
        this.loadOrders()
      } else {
        wx.showToast({
          title: data.error || '操作失败',
          icon: 'none'
        })
      }
    } catch (error) {
      console.error('确认订单失败:', error)
      wx.showToast({
        title: '操作失败',
        icon: 'none'
      })
    }
  },

  contactUser(e) {
    const { order } = e.currentTarget.dataset
    const userId = this.data.activeTab === 0 ? order.seller_id : order.buyer_id

    wx.navigateTo({
      url: `/pages/chat/room?friendId=${userId}&orderId=${order.id}`
    })
  },

  goShopping() {
    wx.switchTab({
      url: '/pages/index/index'
    })
  }
})
