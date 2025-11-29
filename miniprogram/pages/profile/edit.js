const api = require('../../utils/api.js')

Page({
  data: {
    userInfo: null,
    roomNumber: '',
    loading: true,
    saving: false
  },

  onLoad() {
    this.loadUserInfo()
  },

  loadUserInfo() {
    this.setData({ loading: true })
    
    api.getUserInfo().then(res => {
      const userInfo = res.user || res
      this.setData({
        userInfo: userInfo,
        roomNumber: userInfo.room_number || '',
        loading: false
      })
    }).catch(err => {
      console.error('加载用户信息失败:', err)
      this.setData({ loading: false })
    })
  },

  onRoomNumberInput(e) {
    this.setData({ roomNumber: e.detail.value })
  },

  saveProfile() {
    const { roomNumber } = this.data
    
    if (!roomNumber.trim()) {
      wx.showToast({
        title: '请输入房间号',
        icon: 'none'
      })
      return
    }

    const roomPattern = /^\d{1,2}-\d{1,2}-\d{1,4}$/
    if (!roomPattern.test(roomNumber)) {
      wx.showToast({
        title: '房间号格式：楼栋-单元-房号',
        icon: 'none'
      })
      return
    }

    this.setData({ saving: true })

    api.updateUserInfo({
      room_number: roomNumber
    }).then(() => {
      wx.showToast({
        title: '保存成功',
        icon: 'success'
      })
      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
    }).catch(err => {
      wx.showToast({
        title: err.message || '保存失败',
        icon: 'none'
      })
    }).finally(() => {
      this.setData({ saving: false })
    })
  }
})
