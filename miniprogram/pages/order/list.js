// pages/order/list.js
const api = require('../../utils/api.js')
const { getImageUrl } = require('../../utils/config.js')
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
    if (tab !== undefined) {
      this.setData({ activeTab: parseInt(tab) })
      this.hasManualTabSet = true
    }

    this.checkLoginAndLoad()
  },

  onShow() {
    // 检查是否有未读卖家订单，自动跳转到"我卖出的"标签
    // 只在没有通过 onLoad 传入 tab 参数时才自动跳转
    if (!this.hasManualTabSet && app.globalData.unreadCount > 0) {
      this.setData({ activeTab: 1 })
    }
    
    this.checkLoginAndLoad()
    
    // tabBar索引: 0=物品, 1=消息, 2=订单, 3=我的
    if (this.getTabBar()) {
      this.getTabBar().setData({ selected: 2 })
    }
    
    // 刷新未读订单数量
    app.getUnreadCount()
  },

  // 加载完成后检查并自动跳转
  checkAndAutoSwitchTab() {
    const currentUserId = parseInt(app.globalData.userInfo?.id || app.globalData.currentUserId)
    
    if (!currentUserId || this.data.orderList.length === 0) {
      return
    }

    // 统计各类订单
    const buyingOrders = this.data.orderList.filter(o => parseInt(o.buyer_id) === currentUserId)
    const sellingOrders = this.data.orderList.filter(o => parseInt(o.seller_id) === currentUserId)
    const pendingSellingOrders = sellingOrders.filter(o => o.status === 'pending')

    // 自动跳转逻辑：
    // 1. 如果买家没有订单但卖家有待发货订单 -> 自动跳转到"我卖出的"
    // 2. 但保留用户主动切换的选择
    if (this.data.activeTab === 0) {
      if (buyingOrders.length === 0 && pendingSellingOrders.length > 0) {
        // 只在第一次进入时自动跳转
        if (!this.hasAutoSwitched) {
          this.hasAutoSwitched = true
          this.setData({ activeTab: 1 })
        }
      }
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
    this.hasManualTabSet = true
    this.setData({
      activeTab: index
    })
    this.loadOrders()
  },

  async loadOrders() {
    try {
      this.setData({ loading: true })

      // 根据当前tab请求对应类型的订单
      const orderType = this.data.activeTab === 0 ? 'buying' : 'selling'
      const data = await api.getOrderList(orderType)

      // 后端返回的数据可能是数组或对象
      const orderList = Array.isArray(data) ? data : (data.orders || [])
      
      // 获取当前用户ID（确保类型一致）
      const currentUserId = app.globalData.userInfo?.id || app.globalData.currentUserId
      const currentUserIdNum = parseInt(currentUserId)
      
      // 处理每个订单的图片URL和状态显示
      const processedOrders = orderList.map(order => {
        // 处理图片URL
        const productImage = order.product_image || ''
        const imageUrl = getImageUrl(productImage)
        
        // 确定状态文本
        let statusText = '未知'
        switch (order.status) {
          case 'pending': statusText = '待发货'; break
          case 'shipped': statusText = '待收货'; break
          case 'completed': statusText = '已完成'; break
          case 'cancelled': statusText = '已取消'; break
          default: statusText = order.status || '未知'
        }
        
        // 确定用户身份和可执行操作
        const isBuyer = parseInt(order.buyer_id) === currentUserIdNum
        const isSeller = parseInt(order.seller_id) === currentUserIdNum
        
        // 只有已完成或已取消的订单才能删除
        const canDelete = (order.status === 'completed' || order.status === 'cancelled') && (isBuyer || isSeller)
        
        return {
          ...order,
          product_image: imageUrl,
          status_text: statusText,
          can_cancel: order.status === 'pending' && isBuyer,
          can_confirm: (order.status === 'pending' && isSeller) || (order.status === 'shipped' && isBuyer),
          can_contact: true,
          can_delete: canDelete
        }
      })

      this.setData({
        orderList: processedOrders,
        loading: false
      })

      // 加载完成后检查是否需要自动切换标签
      this.checkAndAutoSwitchTab()

      // 更新未读订单数量
      const unreadCount = processedOrders.filter(o => o.unread).length
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
    const currentUserId = app.globalData.userInfo?.id || app.globalData.currentUserId
    const currentUserIdNum = parseInt(currentUserId)
    const isSeller = parseInt(order.seller_id) === currentUserIdNum
    const isBuyer = parseInt(order.buyer_id) === currentUserIdNum
    
    // 判断操作类型：卖家在pending状态发货，买家在shipped状态收货
    const isSelling = order.status === 'pending' && isSeller
    const isBuying = order.status === 'shipped' && isBuyer
    
    if (!isSelling && !isBuying) {
      wx.showToast({
        title: '您无权执行此操作',
        icon: 'none'
      })
      return
    }
    
    const action = isSelling ? '发货' : '收货'

    const result = await wx.showModal({
      title: `确认${action}`,
      content: `确定要确认${action}吗？`
    })

    if (!result.confirm) return

    try {
      // 根据用户身份调用正确的API
      const data = isSelling 
        ? await api.shipOrder(order.id)  // 卖家发货
        : await api.confirmOrder(order.id)  // 买家收货

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

  async deleteOrder(e) {
    const { order } = e.currentTarget.dataset
    
    if (order.status !== 'completed' && order.status !== 'cancelled') {
      wx.showToast({
        title: '只能删除已完成或已取消的订单',
        icon: 'none'
      })
      return
    }

    const result = await wx.showModal({
      title: '确认删除',
      content: '确定要删除这个订单吗？删除后将无法恢复。'
    })

    if (!result.confirm) return

    try {
      const data = await api.request({
        url: `/api/miniprogram/order/${order.id}/delete`,
        method: 'DELETE'
      })

      if (data.success) {
        wx.showToast({
          title: '订单已删除',
          icon: 'success'
        })
        this.loadOrders()
      } else {
        wx.showToast({
          title: data.error || '删除失败',
          icon: 'none'
        })
      }
    } catch (error) {
      console.error('删除订单失败:', error)
      wx.showToast({
        title: '操作失败',
        icon: 'none'
      })
    }
  },

  goShopping() {
    wx.switchTab({
      url: '/pages/product/list'
    })
  }
})
