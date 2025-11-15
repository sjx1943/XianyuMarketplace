// pages/login/login.js
const app = getApp()

Page({
  data: {
    currentTab: 0, // 0: 登录, 1: 注册
    loginForm: {
      username: '',
      password: ''
    },
    registerForm: {
      username: '',
      password: '',
      confirmPassword: '',
      email: ''
    },
    loading: false,
    showPassword: false,
    showConfirmPassword: false
  },

  onLoad(options) {
    // 检查是否已登录
    if (app.globalData.isLogin) {
      wx.navigateBack()
    }
    
    // 如果从注册页面跳转过来，切换到注册tab
    if (options.tab === 'register') {
      this.setData({ currentTab: 1 })
    }
  },

  // 切换tab
  switchTab(e) {
    const { tab } = e.currentTarget.dataset
    this.setData({
      currentTab: parseInt(tab)
    })
  },

  // 登录表单输入
  onLoginInput(e) {
    const { field } = e.currentTarget.dataset
    const { value } = e.detail
    this.setData({
      [`loginForm.${field}`]: value
    })
  },

  // 注册表单输入
  onRegisterInput(e) {
    const { field } = e.currentTarget.dataset
    const { value } = e.detail
    this.setData({
      [`registerForm.${field}`]: value
    })
  },

  // 切换密码显示
  togglePassword(e) {
    const { type } = e.currentTarget.dataset
    if (type === 'login') {
      this.setData({
        showPassword: !this.data.showPassword
      })
    } else {
      this.setData({
        showConfirmPassword: !this.data.showConfirmPassword
      })
    }
  },

  // 登录
  async onLogin() {
    const { loginForm } = this.data
    
    // 验证表单
    if (!this.validateLoginForm(loginForm)) {
      return
    }
    
    this.setData({ loading: true })
    
    try {
      const res = await wx.request({
        url: app.globalData.apiBase.replace('/api', '') + '/login',
        method: 'POST',
        data: {
          username: loginForm.username,
          password: loginForm.password
        },
        header: {
          'content-type': 'application/x-www-form-urlencoded'
        }
      })
      
      if (res.statusCode === 200) {
        if (res.data.success) {
          // 存储登录信息
          wx.setStorageSync('token', res.data.token)
          wx.setStorageSync('userInfo', res.data.user)
          
          // 更新全局状态
          app.login(res.data.user)
          
          app.showToast('登录成功', 'success')
          
          // 延迟跳转，让用户看到成功提示
          setTimeout(() => {
            wx.navigateBack()
          }, 1500)
        } else {
          app.showToast(res.data.message || '登录失败')
        }
      } else {
        app.showToast('登录失败，请重试')
      }
    } catch (error) {
      console.error('登录失败:', error)
      app.showToast('网络错误，请重试')
    } finally {
      this.setData({ loading: false })
    }
  },

  // 注册
  async onRegister() {
    const { registerForm } = this.data
    
    // 验证表单
    if (!this.validateRegisterForm(registerForm)) {
      return
    }
    
    this.setData({ loading: true })
    
    try {
      const res = await wx.request({
        url: app.globalData.apiBase.replace('/api', '') + '/register',
        method: 'POST',
        data: {
          username: registerForm.username,
          password: registerForm.password,
          email: registerForm.email
        },
        header: {
          'content-type': 'application/x-www-form-urlencoded'
        }
      })
      
      if (res.statusCode === 200) {
        if (res.data.success) {
          app.showToast('注册成功，请登录', 'success')
          
          // 切换到登录tab
          this.setData({
            currentTab: 0,
            loginForm: {
              username: registerForm.username,
              password: ''
            }
          })
        } else {
          app.showToast(res.data.message || '注册失败')
        }
      } else {
        app.showToast('注册失败，请重试')
      }
    } catch (error) {
      console.error('注册失败:', error)
      app.showToast('网络错误，请重试')
    } finally {
      this.setData({ loading: false })
    }
  },

  // 微信快速登录
  async onWechatLogin() {
    try {
      // 获取微信登录code
      const loginRes = await wx.login()
      
      if (!loginRes.code) {
        app.showToast('微信登录失败')
        return
      }
      
      // 获取用户信息
      const userRes = await wx.getUserProfile({
        desc: '用于完善用户资料'
      })
      
      this.setData({ loading: true })
      
      // 发送到服务器进行登录
      const res = await wx.request({
        url: app.globalData.apiBase + '/wechat_login',
        method: 'POST',
        data: {
          code: loginRes.code,
          userInfo: userRes.userInfo
        }
      })
      
      if (res.statusCode === 200 && res.data.success) {
        // 存储登录信息
        wx.setStorageSync('token', res.data.token)
        wx.setStorageSync('userInfo', res.data.user)
        
        // 更新全局状态
        app.login(res.data.user)
        
        app.showToast('登录成功', 'success')
        
        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        app.showToast(res.data.message || '微信登录失败')
      }
    } catch (error) {
      console.error('微信登录失败:', error)
      if (error.errMsg && error.errMsg.includes('getUserProfile')) {
        app.showToast('需要授权才能使用微信登录')
      } else {
        app.showToast('微信登录失败')
      }
    } finally {
      this.setData({ loading: false })
    }
  },

  // 忘记密码
  onForgotPassword() {
    wx.navigateTo({
      url: '/pages/forgot-password/forgot-password'
    })
  },

  // 验证登录表单
  validateLoginForm(form) {
    if (!form.username.trim()) {
      app.showToast('请输入用户名')
      return false
    }
    
    if (!form.password.trim()) {
      app.showToast('请输入密码')
      return false
    }
    
    if (form.password.length < 6) {
      app.showToast('密码至少6位')
      return false
    }
    
    return true
  },

  // 验证注册表单
  validateRegisterForm(form) {
    if (!form.username.trim()) {
      app.showToast('请输入用户名')
      return false
    }
    
    if (form.username.length < 3) {
      app.showToast('用户名至少3位')
      return false
    }
    
    if (!form.email.trim()) {
      app.showToast('请输入邮箱')
      return false
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(form.email)) {
      app.showToast('邮箱格式不正确')
      return false
    }
    
    if (!form.password.trim()) {
      app.showToast('请输入密码')
      return false
    }
    
    if (form.password.length < 6) {
      app.showToast('密码至少6位')
      return false
    }
    
    if (form.password !== form.confirmPassword) {
      app.showToast('两次密码不一致')
      return false
    }
    
    return true
  }
})
