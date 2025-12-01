const api = require('../../utils/api.js')

Page({
  data: {
    userInfo: null,
    username: '',
    phone: '',
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
        username: userInfo.username || '',
        phone: userInfo.phone || '',
        roomNumber: userInfo.room_number || '',
        loading: false
      })
    }).catch(err => {
      console.error('加载用户信息失败:', err)
      this.setData({ loading: false })
    })
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value })
  },

  onPhoneInput(e) {
    this.setData({ phone: e.detail.value })
  },

  onRoomNumberInput(e) {
    this.setData({ roomNumber: e.detail.value })
  },

  saveProfile() {
    const { username, phone, roomNumber } = this.data
    
    if (!username.trim()) {
      wx.showToast({
        title: '请输入用户名',
        icon: 'none'
      })
      return
    }

    if (phone && !/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({
        title: '请输入正确的手机号',
        icon: 'none'
      })
      return
    }

    if (roomNumber) {
      const roomPattern = /^\d{1,2}-\d{1,2}-\d{1,4}$/
      if (!roomPattern.test(roomNumber)) {
        wx.showToast({
          title: '房间号格式：楼栋-单元-房号',
          icon: 'none'
        })
        return
      }
    }

    this.setData({ saving: true })

    const updateData = {
      username: username.trim()
    }
    
    if (phone) {
      updateData.phone = phone
    }
    
    if (roomNumber) {
      updateData.room_number = roomNumber
    }

    api.updateUserInfo(updateData).then(() => {
      const userInfo = wx.getStorageSync('userInfo') || {}
      userInfo.username = username.trim()
      if (phone) userInfo.phone = phone
      if (roomNumber) userInfo.room_number = roomNumber
      wx.setStorageSync('userInfo', userInfo)
      
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
