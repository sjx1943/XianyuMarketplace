// pages/login/login.js
var app = getApp();

Page({
  data: {
    isLogin: false,
    needSetRoom: false,
    roomNumber: '',
    loading: false,
    agreedPrivacy: false
  },

  onLoad: function(options) {
    // 检查是否已登录
    if (app.globalData.isLogin) {
      this.setData({ isLogin: true });
      this.checkRoomNumber();
    }
  },

  onShow: function() {
    // 每次显示页面时检查登录状态
    if (app.globalData.isLogin) {
      this.setData({ isLogin: true });
      this.checkRoomNumber();
    }
  },

  // 切换隐私政策同意状态
  toggleAgreement: function() {
    this.setData({
      agreedPrivacy: !this.data.agreedPrivacy
    });
  },

  // 微信快捷登录
  onWechatLogin: function() {
    var self = this;
    
    // 检查是否已同意隐私政策
    if (!self.data.agreedPrivacy) {
      wx.showToast({
        title: '请先阅读并同意用户协议和隐私政策',
        icon: 'none',
        duration: 2000
      });
      return;
    }
    
    if (self.data.loading) return;
    self.setData({ loading: true });

    // 先获取微信登录code
    wx.login({
      success: function(loginRes) {
        if (!loginRes.code) {
          self.setData({ loading: false });
          wx.showToast({
            title: '登录失败，请重试',
            icon: 'none'
          });
          return;
        }

        // 发送code到服务器进行登录
        wx.request({
          url: app.globalData.apiBase + '/api/miniprogram/login',
          method: 'POST',
          data: {
            code: loginRes.code
          },
          header: {
            'Content-Type': 'application/json'
          },
          success: function(res) {
            self.setData({ loading: false });
            
            if (res.statusCode === 200 && res.data) {
              if (res.data.success || res.data.token) {
                // 登录成功
                var token = res.data.token;
                var userInfo = res.data.user || res.data.userInfo || {};
                
                wx.setStorageSync('token', token);
                wx.setStorageSync('userInfo', userInfo);
                
                app.globalData.isLogin = true;
                app.globalData.userInfo = userInfo;
                app.globalData.currentUserId = userInfo.id;
                
                self.setData({ isLogin: true });
                
                // 检查是否需要设置房间号
                if (!userInfo.room_number) {
                  self.setData({ needSetRoom: true });
                } else {
                  wx.showToast({
                    title: '登录成功',
                    icon: 'success'
                  });
                  
                  setTimeout(function() {
                    wx.switchTab({
                      url: '/pages/product/list'
                    });
                  }, 1500);
                }
              } else {
                wx.showToast({
                  title: res.data.message || '登录失败',
                  icon: 'none'
                });
              }
            } else {
              wx.showToast({
                title: '登录失败，请重试',
                icon: 'none'
              });
            }
          },
          fail: function(err) {
            self.setData({ loading: false });
            console.error('登录请求失败:', err);
            wx.showToast({
              title: '网络错误，请重试',
              icon: 'none'
            });
          }
        });
      },
      fail: function(err) {
        self.setData({ loading: false });
        console.error('wx.login失败:', err);
        wx.showToast({
          title: '微信登录失败',
          icon: 'none'
        });
      }
    });
  },

  // 检查房间号
  checkRoomNumber: function() {
    var userInfo = app.globalData.userInfo;
    if (userInfo && !userInfo.room_number) {
      this.setData({ needSetRoom: true });
    }
  },

  // 房间号输入
  onRoomInput: function(e) {
    this.setData({
      roomNumber: e.detail.value
    });
  },

  // 确认房间号
  onConfirmRoom: function() {
    var self = this;
    var roomNumber = self.data.roomNumber.trim();
    
    if (!roomNumber) {
      wx.showToast({
        title: '请输入房间号',
        icon: 'none'
      });
      return;
    }

    // 验证房间号格式（如：1-2-345）
    var roomRegex = /^\d+-\d+-\d+$/;
    if (!roomRegex.test(roomNumber)) {
      wx.showToast({
        title: '房间号格式不正确',
        icon: 'none'
      });
      return;
    }

    self.setData({ loading: true });

    var token = wx.getStorageSync('token') || '';
    
    wx.request({
      url: app.globalData.apiBase + '/api/miniprogram/set_room_number',
      method: 'POST',
      data: JSON.stringify({
        room_number: roomNumber
      }),
      header: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
      },
      success: function(res) {
        self.setData({ loading: false });
        
        if (res.statusCode === 200 && res.data.success) {
          // 更新本地用户信息
          var userInfo = app.globalData.userInfo || {};
          userInfo.room_number = roomNumber;
          app.globalData.userInfo = userInfo;
          wx.setStorageSync('userInfo', userInfo);
          
          wx.showToast({
            title: '设置成功',
            icon: 'success'
          });
          
          setTimeout(function() {
            wx.switchTab({
              url: '/pages/product/list'
            });
          }, 1500);
        } else {
          // 显示具体的错误信息（如：房间号已被占用）
          wx.showToast({
            title: res.data.error || res.data.message || '设置失败',
            icon: 'none',
            duration: 3000  // 增加显示时间让用户能看清错误信息
          });
        }
      },
      fail: function(err) {
        self.setData({ loading: false });
        console.error('设置房间号失败:', err);
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        });
      }
    });
  },

  // 用户协议
  onUserAgreement: function() {
    wx.navigateTo({
      url: '/pages/settings/agreement'
    });
  },

  // 隐私政策
  onPrivacyPolicy: function() {
    wx.navigateTo({
      url: '/pages/settings/privacy'
    });
  }
});
