const api = require('../../utils/api.js')
const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')

Page({
  data: {
    userInfo: null,
    username: '',
    phone: '',
    roomNumber: '',
    avatar: '',
    defaultAvatar: getDefaultAvatarUrl(),
    loading: true,
    saving: false,
    avatarChanged: false
  },

  onLoad() {
    this.loadUserInfo()
  },

  loadUserInfo() {
    this.setData({ loading: true })
    
    api.getUserInfo().then(res => {
      const userInfo = res.user || res
      const avatarUrl = userInfo.wechat_avatar ? getImageUrl(userInfo.wechat_avatar) : getDefaultAvatarUrl()
      this.setData({
        userInfo: userInfo,
        username: userInfo.username || '',
        phone: userInfo.phone || '',
        roomNumber: userInfo.room_number || '',
        avatar: avatarUrl,
        loading: false
      })
    }).catch(err => {
      console.error('加载用户信息失败:', err)
      this.setData({ loading: false })
    })
  },

  chooseAvatar() {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const filePath = res.tempFilePaths[0]
        this.setData({
          avatar: filePath,
          avatarChanged: true
        })
        wx.showToast({
          title: '已选择头像',
          icon: 'success'
        })
      }
    })
  },

  useDefaultAvatar() {
    this.setData({
      avatar: this.data.defaultAvatar,
      avatarChanged: true
    })
    wx.showToast({
      title: '已选择默认头像',
      icon: 'success'
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
    const { username, phone, roomNumber, avatar, avatarChanged } = this.data
    
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

    // 如果头像有变化，先上传头像
    if (avatarChanged && avatar && avatar.startsWith('wxfile://')) {
      this.uploadAvatarAndSave(username, phone, roomNumber)
    } else {
      this.saveProfileData(username, phone, roomNumber, null)
    }
  },

  uploadAvatarAndSave(username, phone, roomNumber) {
    const { avatar } = this.data
    const token = wx.getStorageSync('token') || ''

    wx.uploadFile({
      url: api.baseURL + '/api/miniprogram/user/upload-avatar',
      filePath: avatar,
      name: 'avatar',
      header: {
        'Authorization': 'Bearer ' + token
      },
      success: (res) => {
        if (res.statusCode === 200) {
          try {
            const data = JSON.parse(res.data)
            if (data.success) {
              this.saveProfileData(username, phone, roomNumber, data.avatar_url)
            } else {
              wx.showToast({
                title: data.error || '头像上传失败',
                icon: 'none'
              })
              this.setData({ saving: false })
            }
          } catch (e) {
            wx.showToast({
              title: '头像上传失败',
              icon: 'none'
            })
            this.setData({ saving: false })
          }
        } else {
          wx.showToast({
            title: '头像上传失败',
            icon: 'none'
          })
          this.setData({ saving: false })
        }
      },
      fail: (err) => {
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        })
        this.setData({ saving: false })
      }
    })
  },

  saveProfileData(username, phone, roomNumber, avatarUrl) {
    const updateData = {
      username: username.trim()
    }
    
    if (phone) {
      updateData.phone = phone
    }
    
    if (roomNumber) {
      updateData.room_number = roomNumber
    }

    if (avatarUrl) {
      updateData.wechat_avatar = avatarUrl
    }

    api.updateUserInfo(updateData).then(() => {
      const userInfo = wx.getStorageSync('userInfo') || {}
      userInfo.username = username.trim()
      if (phone) userInfo.phone = phone
      if (roomNumber) userInfo.room_number = roomNumber
      if (avatarUrl) userInfo.wechat_avatar = avatarUrl
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
      this.setData({ saving: false })
    })
  }
})
