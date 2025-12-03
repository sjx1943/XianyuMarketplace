const api = require('../../utils/api.js')
const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')

Page({
  data: {
    userInfo: null,
    username: '',
    phone: '',
    phoneDisplay: '',
    roomNumber: '',
    avatar: '',
    defaultAvatar: getDefaultAvatarUrl(),
    loading: true,
    saving: false,
    avatarChanged: false,
    
    newPhone: '',
    verifyCode: '',
    showCodeInput: false,
    countdown: 0,
    sendingCode: false,
    binding: false
  },

  countdownTimer: null,

  onLoad() {
    this.loadUserInfo()
  },

  onUnload() {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer)
    }
  },

  loadUserInfo() {
    this.setData({ loading: true })
    
    api.getUserInfo().then(res => {
      const userInfo = res.user || res
      const avatarUrl = userInfo.wechat_avatar ? getImageUrl(userInfo.wechat_avatar) : getDefaultAvatarUrl()
      const phone = userInfo.phone || ''
      
      this.setData({
        userInfo: userInfo,
        username: userInfo.username || '',
        phone: phone,
        phoneDisplay: phone ? this.maskPhone(phone) : '',
        roomNumber: userInfo.room_number || '',
        avatar: avatarUrl,
        loading: false
      })
    }).catch(err => {
      console.error('加载用户信息失败:', err)
      this.setData({ loading: false })
    })
  },

  maskPhone(phone) {
    if (!phone || phone.length !== 11) return phone
    return phone.substring(0, 3) + '****' + phone.substring(7)
  },

  chooseAvatar() {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const filePath = res.tempFilePaths[0]
        console.log('选择头像成功:', filePath)
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

  onRoomNumberInput(e) {
    this.setData({ roomNumber: e.detail.value })
  },

  onNewPhoneInput(e) {
    this.setData({ newPhone: e.detail.value })
  },

  onCodeInput(e) {
    this.setData({ verifyCode: e.detail.value })
  },

  onStartBind() {
    const { newPhone } = this.data
    if (!newPhone || newPhone.length !== 11) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' })
      return
    }
    
    this.setData({ showCodeInput: true })
    this.onSendCode()
  },

  async onSendCode() {
    const { newPhone, countdown, sendingCode } = this.data
    
    if (countdown > 0 || sendingCode) return
    
    if (!newPhone || newPhone.length !== 11) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' })
      return
    }

    this.setData({ sendingCode: true })
    
    try {
      const res = await api.sendPhoneBindCode(newPhone)
      
      if (res.success) {
        wx.showToast({ title: '验证码已发送', icon: 'success' })
        
        if (res.dev_code) {
          console.log('开发模式验证码:', res.dev_code)
        }
        
        this.startCountdown()
      } else {
        wx.showToast({ title: res.error || '发送失败', icon: 'none' })
      }
    } catch (err) {
      console.error('发送验证码失败:', err)
      wx.showToast({ title: '发送失败，请重试', icon: 'none' })
    } finally {
      this.setData({ sendingCode: false })
    }
  },

  startCountdown() {
    this.setData({ countdown: 60 })
    
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer)
    }
    
    this.countdownTimer = setInterval(() => {
      const { countdown } = this.data
      if (countdown <= 1) {
        clearInterval(this.countdownTimer)
        this.countdownTimer = null
        this.setData({ countdown: 0 })
      } else {
        this.setData({ countdown: countdown - 1 })
      }
    }, 1000)
  },

  async onBindPhone() {
    const { newPhone, verifyCode, binding } = this.data
    
    if (binding) return
    
    if (!newPhone || newPhone.length !== 11) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' })
      return
    }
    
    if (!verifyCode || verifyCode.length !== 6) {
      wx.showToast({ title: '请输入6位验证码', icon: 'none' })
      return
    }

    this.setData({ binding: true })
    
    try {
      const res = await api.bindPhone(newPhone, verifyCode)
      
      if (res.success) {
        wx.showToast({ title: '绑定成功', icon: 'success' })
        
        const userInfo = wx.getStorageSync('userInfo') || {}
        userInfo.phone = newPhone
        wx.setStorageSync('userInfo', userInfo)
        
        this.setData({
          phone: newPhone,
          phoneDisplay: this.maskPhone(newPhone),
          newPhone: '',
          verifyCode: '',
          showCodeInput: false,
          countdown: 0
        })
        
        if (this.countdownTimer) {
          clearInterval(this.countdownTimer)
          this.countdownTimer = null
        }
      } else {
        wx.showToast({ title: res.error || '绑定失败', icon: 'none' })
      }
    } catch (err) {
      console.error('绑定手机号失败:', err)
      wx.showToast({ title: '绑定失败，请重试', icon: 'none' })
    } finally {
      this.setData({ binding: false })
    }
  },

  onUnbindPhone() {
    wx.showModal({
      title: '确认解绑',
      content: '解绑后将无法使用该手机号在网页端登录，确定要解绑吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            const result = await api.unbindPhone()
            
            if (result.success) {
              wx.showToast({ title: '已解绑', icon: 'success' })
              
              const userInfo = wx.getStorageSync('userInfo') || {}
              userInfo.phone = ''
              wx.setStorageSync('userInfo', userInfo)
              
              this.setData({
                phone: '',
                phoneDisplay: ''
              })
            } else {
              wx.showToast({ title: result.error || '解绑失败', icon: 'none' })
            }
          } catch (err) {
            console.error('解绑手机号失败:', err)
            wx.showToast({ title: '解绑失败，请重试', icon: 'none' })
          }
        }
      }
    })
  },

  saveProfile() {
    const { username, roomNumber, avatar, avatarChanged, defaultAvatar } = this.data
    
    if (!username.trim()) {
      wx.showToast({
        title: '请输入用户名',
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

    if (avatarChanged && avatar) {
      const isLocalFile = avatar.startsWith('wxfile://') || avatar.startsWith('http://tmp/') || avatar.startsWith('/tmp/')
      
      if (isLocalFile) {
        this.uploadAvatarAndSave(username, roomNumber)
      } else if (avatar === defaultAvatar) {
        this.saveProfileData(username, roomNumber, defaultAvatar)
      } else {
        this.saveProfileData(username, roomNumber, null)
      }
    } else {
      this.saveProfileData(username, roomNumber, null)
    }
  },

  uploadAvatarAndSave(username, roomNumber) {
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
              this.saveProfileData(username, roomNumber, data.avatar_url)
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
        console.error('上传请求失败:', err)
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        })
        this.setData({ saving: false })
      }
    })
  },

  saveProfileData(username, roomNumber, avatarUrl) {
    const originalData = {
      username: this.data.userInfo?.username || '',
      roomNumber: this.data.userInfo?.room_number || '',
      avatar: this.data.userInfo?.wechat_avatar || this.data.defaultAvatar
    }

    const updateData = {
      username: username.trim()
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
      if (roomNumber) userInfo.room_number = roomNumber
      if (avatarUrl) userInfo.wechat_avatar = avatarUrl
      wx.setStorageSync('userInfo', userInfo)
      
      wx.showToast({
        title: '保存成功',
        icon: 'success'
      })
      this.setData({ saving: false })
      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
    }).catch(err => {
      console.error('保存失败:', err)
      this.setData({
        username: originalData.username,
        roomNumber: originalData.roomNumber,
        avatar: originalData.avatar,
        saving: false
      })
      wx.showToast({
        title: err.message || '保存失败',
        icon: 'none'
      })
    })
  }
})
