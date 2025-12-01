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
        console.log('📸 选择头像成功:', filePath)
        this.setData({
          avatar: filePath,
          avatarChanged: true
        })
        console.log('✅ avatarChanged已设置为true, 当前avatar:', filePath)
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
    const { username, phone, roomNumber, avatar, avatarChanged, defaultAvatar } = this.data
    
    console.log('💾 保存资料 - 调试信息:')
    console.log('  avatarChanged:', avatarChanged)
    console.log('  avatar:', avatar)
    console.log('  defaultAvatar:', defaultAvatar)
    console.log('  avatar是否以wxfile://开头:', avatar ? avatar.startsWith('wxfile://') : 'avatar为空')
    
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

    // 如果头像有变化，需要处理
    if (avatarChanged && avatar) {
      console.log('🔍 头像已变化，检查处理方式...')
      // 检查是否是本地临时文件（wxfile:// 或 http://tmp/ 等本地路径格式）
      const isLocalFile = avatar.startsWith('wxfile://') || avatar.startsWith('http://tmp/') || avatar.startsWith('/tmp/')
      
      if (isLocalFile) {
        // 新选择的图片 - 需要上传
        console.log('📤 触发上传新头像流程，路径:', avatar)
        this.uploadAvatarAndSave(username, phone, roomNumber)
      } else if (avatar === defaultAvatar) {
        // 选择的是默认头像 - 直接保存，不上传
        console.log('🎨 使用默认头像，直接保存')
        this.saveProfileData(username, phone, roomNumber, defaultAvatar)
      } else {
        // 其他情况（已有头像或网络URL） - 不更改头像
        console.log('⚠️ 其他情况，不改变头像')
        this.saveProfileData(username, phone, roomNumber, null)
      }
    } else {
      // 未改变头像 - 仅保存其他信息
      console.log('📝 头像未改变，仅保存其他信息')
      this.saveProfileData(username, phone, roomNumber, null)
    }
  },

  uploadAvatarAndSave(username, phone, roomNumber) {
    const { avatar } = this.data
    const token = wx.getStorageSync('token') || ''

    console.log('🚀 开始上传头像...')
    console.log('  文件路径:', avatar)
    console.log('  API地址:', api.baseURL + '/api/miniprogram/user/upload-avatar')

    wx.uploadFile({
      url: api.baseURL + '/api/miniprogram/user/upload-avatar',
      filePath: avatar,
      name: 'avatar',
      header: {
        'Authorization': 'Bearer ' + token
      },
      success: (res) => {
        console.log('✅ 上传成功，响应:', res)
        if (res.statusCode === 200) {
          try {
            const data = JSON.parse(res.data)
            console.log('📦 解析后的数据:', data)
            if (data.success) {
              console.log('🎉 头像上传成功，avatar_url:', data.avatar_url)
              this.saveProfileData(username, phone, roomNumber, data.avatar_url)
            } else {
              console.error('❌ 头像上传失败:', data.error)
              wx.showToast({
                title: data.error || '头像上传失败',
                icon: 'none'
              })
              this.setData({ saving: false })
            }
          } catch (e) {
            console.error('❌ 解析响应数据失败:', e)
            wx.showToast({
              title: '头像上传失败',
              icon: 'none'
            })
            this.setData({ saving: false })
          }
        } else {
          console.error('❌ 上传失败，状态码:', res.statusCode)
          wx.showToast({
            title: '头像上传失败',
            icon: 'none'
          })
          this.setData({ saving: false })
        }
      },
      fail: (err) => {
        console.error('❌ 上传请求失败:', err)
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        })
        this.setData({ saving: false })
      }
    })
  },

  saveProfileData(username, phone, roomNumber, avatarUrl) {
    // 保存原始值，用于失败时回滚
    const originalData = {
      username: this.data.userInfo?.username || '',
      phone: this.data.userInfo?.phone || '',
      roomNumber: this.data.userInfo?.room_number || '',
      avatar: this.data.userInfo?.wechat_avatar || this.data.defaultAvatar
    }

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

    console.log('💾 调用updateUserInfo，数据:', updateData)
    console.log('📝 原始数据用于回滚:', originalData)

    api.updateUserInfo(updateData).then(() => {
      const userInfo = wx.getStorageSync('userInfo') || {}
      userInfo.username = username.trim()
      if (phone) userInfo.phone = phone
      if (roomNumber) userInfo.room_number = roomNumber
      if (avatarUrl) userInfo.wechat_avatar = avatarUrl
      wx.setStorageSync('userInfo', userInfo)
      
      console.log('✅ 保存成功，userInfo已更新')
      wx.showToast({
        title: '保存成功',
        icon: 'success'
      })
      this.setData({ saving: false })
      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
    }).catch(err => {
      console.error('❌ 保存失败:', err)
      // 恢复原始值，确保前端数据与数据库一致
      this.setData({
        username: originalData.username,
        phone: originalData.phone,
        roomNumber: originalData.roomNumber,
        avatar: originalData.avatar,
        saving: false
      })
      console.log('🔄 已恢复原始数据:', originalData)
      wx.showToast({
        title: err.message || '保存失败',
        icon: 'none'
      })
    })
  }
})
