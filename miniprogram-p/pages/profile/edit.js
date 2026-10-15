const api = require('../../utils/api.js')
const { getImageUrl, getDefaultAvatarUrl } = require('../../utils/config.js')
const contentSecurity = require('../../utils/contentSecurity.js')

Page({
  data: {
    userInfo: null,
    username: '',
    phone: '',
    phoneDisplay: '',
    roomNumber: '',
    avatar: '',
    pendingAvatarPath: '',
    defaultAvatar: getDefaultAvatarUrl(),
    loading: true,
    saving: false,
    avatarChanged: false,
    avatarSecurityStatus: 'approved',
    avatarChecking: false,
    
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
    if (this.avatarPollingTimer) {
      clearInterval(this.avatarPollingTimer)
    }
  },

  loadUserInfo() {
    this.setData({ loading: true })
    
    api.getUserInfo().then(res => {
      const userInfo = res.user || res
      const securityStatus = userInfo.avatar_security_status || 'approved'
      const avatarUrl = (securityStatus === 'approved' && userInfo.wechat_avatar) 
        ? getImageUrl(userInfo.wechat_avatar) 
        : getDefaultAvatarUrl()
      const phone = userInfo.phone || ''
      
      this.setData({
        userInfo: userInfo,
        username: userInfo.username || '',
        phone: phone,
        phoneDisplay: phone ? this.maskPhone(phone) : '',
        roomNumber: userInfo.room_number || '',
        avatar: avatarUrl,
        avatarSecurityStatus: securityStatus,
        loading: false
      })
      
      if (securityStatus === 'pending') {
        this.startPollingAvatarStatus()
      }
    }).catch(err => {
      console.error('加载用户信息失败:', err)
      this.setData({ loading: false })
    })
  },
  
  avatarPollingTimer: null,
  verificationPollingTimer: null,

  pollVerificationStatus(traceId, attempts = 0) {
    if (attempts > 30) {
      console.log('[Profile] 轮询超时，停止查询验证状态')
      return
    }
    
    this.verificationPollingTimer = setTimeout(async () => {
      try {
        const result = await contentSecurity.queryVerificationStatus(traceId)
        console.log('[Profile] 验证状态查询结果:', result)
        
        if (result.success && result.status === 'pending') {
          this.pollVerificationStatus(traceId, attempts + 1)
        } else if (result.success && result.status) {
          console.log('[Profile] 验证完成，状态:', result.status)
          if (result.suggest === 'pass') {
            wx.showToast({
              title: '图片已通过安全检测',
              icon: 'success'
            })
          } else {
            wx.showToast({
              title: '图片未通过安全检测',
              icon: 'none'
            })
          }
        }
      } catch (err) {
        console.warn('[Profile] 查询验证状态失败:', err)
        this.pollVerificationStatus(traceId, attempts + 1)
      }
    }, 2000)
  },
  
  startPollingAvatarStatus() {
    if (this.avatarPollingTimer) {
      clearInterval(this.avatarPollingTimer)
    }
    
    let pollCount = 0
    const maxPolls = 30
    
    this.avatarPollingTimer = setInterval(() => {
      pollCount++
      if (pollCount > maxPolls) {
        clearInterval(this.avatarPollingTimer)
        this.avatarPollingTimer = null
        return
      }
      
      api.getUserInfo().then(res => {
        const userInfo = res.user || res
        const newStatus = userInfo.avatar_security_status || 'approved'
        
        if (newStatus !== 'pending') {
          clearInterval(this.avatarPollingTimer)
          this.avatarPollingTimer = null
          
          if (newStatus === 'approved' && userInfo.wechat_avatar) {
            this.setData({
              avatar: getImageUrl(userInfo.wechat_avatar),
              avatarSecurityStatus: newStatus
            })
          } else if (newStatus === 'rejected') {
            this.setData({
              avatar: getDefaultAvatarUrl(),
              avatarSecurityStatus: newStatus
            })
            wx.showToast({
              title: '头像含有违规内容',
              icon: 'none'
            })
          }
        }
      }).catch(err => {
        console.warn('轮询头像状态失败:', err)
      })
    }, 2000)
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
      success: async (res) => {
        const filePath = res.tempFilePaths[0]
        console.log('[Profile] 选择头像，开始安全检测:', filePath)
        
        this.setData({
          avatarChecking: true,
          pendingAvatarPath: filePath
        })
        
        wx.showLoading({
          title: '检测中...',
          mask: true
        })
        
        try {
          const mediaCheckResult = await contentSecurity.checkImageWithBase64(filePath, 1)
          console.log('[Profile] 头像安全检测结果:', mediaCheckResult)
          
          wx.hideLoading()
          
          if (mediaCheckResult.safe || mediaCheckResult.skipped) {
            console.log('[Profile] 头像安全检测通过，显示预览')
            this.setData({
              avatar: filePath,
              avatarChanged: true,
              avatarChecking: false,
              pendingAvatarPath: ''
            })
            wx.showToast({
              title: '已选择头像',
              icon: 'success'
            })
          } else {
            console.log('[Profile] 头像安全检测失败:', mediaCheckResult.reason)
            this.setData({
              avatarChecking: false,
              pendingAvatarPath: ''
            })
            wx.showToast({
              title: mediaCheckResult.reason || '图片含有违规内容',
              icon: 'none',
              duration: 3000
            })
          }
        } catch (err) {
          console.error('[Profile] 头像安全检测异常:', err)
          wx.hideLoading()
          this.setData({
            avatarChecking: false,
            pendingAvatarPath: ''
          })
          wx.showToast({
            title: '检测失败，请重试',
            icon: 'none'
          })
        }
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

  async saveProfile() {
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

    const isValid = await contentSecurity.validateProfile({
      username: username,
      roomNumber: roomNumber
    })
    
    if (!isValid) {
      this.setData({ saving: false })
      return
    }

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

  async uploadAvatarAndSave(username, roomNumber) {
    const { avatar } = this.data
    const token = wx.getStorageSync('token') || ''

    try {
      console.log('[Profile] 头像已通过安全检测，直接上传...')
      
      const uploadResult = await new Promise((resolve, reject) => {
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
                  resolve(data)
                } else {
                  reject(new Error(data.error || '头像上传失败'))
                }
              } catch (e) {
                reject(new Error('头像上传失败'))
              }
            } else {
              reject(new Error('头像上传失败'))
            }
          },
          fail: (err) => {
            reject(err)
          }
        })
      })
      
      const avatarUrl = uploadResult.avatar_url
      console.log('[Profile] 头像上传成功:', avatarUrl)
      
      this.setData({
        avatarSecurityStatus: 'approved',
        avatar: getImageUrl(avatarUrl)
      })
      
      this.saveProfileData(username, roomNumber, avatarUrl)
      
    } catch (err) {
      console.error('上传请求失败:', err)
      wx.showToast({
        title: err.message || '网络错误，请重试',
        icon: 'none'
      })
      this.setData({ saving: false })
    }
  },

  async saveProfileData(username, roomNumber, avatarUrl) {
    const originalData = {
      username: this.data.userInfo?.username || '',
      roomNumber: this.data.userInfo?.room_number || '',
      avatar: this.data.userInfo?.wechat_avatar || this.data.defaultAvatar
    }

    try {
      const usernameToCheck = username.trim()
      
      const textCheckResult = await contentSecurity.checkText(usernameToCheck, 1)
      if (!textCheckResult.safe) {
        wx.showToast({
          title: '昵称含有违规信息',
          icon: 'none'
        })
        this.setData({ saving: false })
        return
      }

      const updateData = {
        username: usernameToCheck
      }
      
      if (roomNumber) {
        updateData.room_number = roomNumber
      }

      if (avatarUrl) {
        updateData.wechat_avatar = avatarUrl
      }

      const result = await api.updateUserInfo(updateData)
      
      const userInfo = wx.getStorageSync('userInfo') || {}
      userInfo.username = usernameToCheck
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
    } catch (err) {
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
    }
  }
})
