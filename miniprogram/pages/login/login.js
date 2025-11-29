// pages/login/login.js
var app = getApp();

Page({
  data: {
    isLogin: false,
    needSetRoom: false,
    roomNumber: '',
    loading: false
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

  // 微信快捷登录
  onWechatLogin: function() {
    var self = this;
    
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
          url: app.globalData.apiBase + '/miniprogram/login',
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
                      url: '/pages/index/index'
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

    // 验证房间号格式（如：3-1-801）
    var roomRegex = /^\d+-\d+-\d+$/;
    if (!roomRegex.test(roomNumber)) {
      wx.showToast({
        title: '房间号格式不正确',
        icon: 'none'
      });
      return;
    }

    self.setData({ loading: true });

    wx.request({
      url: app.globalData.apiBase + '/set_room_number',
      method: 'POST',
      data: {
        room_number: roomNumber
      },
      header: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      success: function(res) {
        self.setData({ loading: false });
        
        if (res.statusCode === 200 && (res.data.success || res.data.message === 'ok')) {
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
              url: '/pages/index/index'
            });
          }, 1500);
        } else {
          wx.showToast({
            title: res.data.message || '设置失败',
            icon: 'none'
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
    wx.showModal({
      title: '用户协议',
      content: '欢迎使用小区二手市场！本平台仅供小区居民进行闲置物品交易。请遵守平台规则，诚信交易。',
      showCancel: false,
      confirmText: '我知道了'
    });
  },

  // 隐私政策
  onPrivacyPolicy: function() {
    wx.showModal({
      title: '隐私政策',
      content: '我们重视您的隐私安全。您的个人信息仅用于平台交易功能，不会泄露给第三方。',
      showCancel: false,
      confirmText: '我知道了'
    });
  }
});
