Page({
  data: {
    version: '2.2.1'
  },

  onLoad() {
    console.log('关于我们页面加载')
  },

  onShareAppMessage() {
    return {
      title: '翠友雅集 - 小区闲置物品交易平台',
      path: '/pages/product/list'
    }
  }
})
