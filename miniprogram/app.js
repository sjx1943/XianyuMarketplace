// app.js - 小程序主应用文件
App({
  globalData: {
    userInfo: null,
    apiBase: '',
    wsBase: '',
    isLogin: false,
    currentUserId: null,
    unreadCount: 0,
    networkConnected: true,
    networkType: 'unknown',
    retryCount: 0,
    maxRetries: 3,
    requestTimeout: 10000
  },

  onLaunch: function() {
    var self = this;
    
    // 初始化配置
    var configModule = require('./utils/config.js');
    self.globalData.apiBase = configModule.API_BASE;
    self.globalData.wsBase = configModule.WS_BASE;

    // 初始化日志
    var logs = wx.getStorageSync('logs') || [];
    logs.unshift(Date.now());
    wx.setStorageSync('logs', logs);

    // 初始化网络状态监听
    self.initNetworkListener();
    
    // 检查登录状态
    self.checkLoginStatus();
    
    // 初始化其他配置
    self.initConfig();
  },

  onShow: function() {
    // 应用被重新激活时检查登录状态
    this.checkLoginStatus();
    
    // 刷新未读消息计数
    this.getUnreadCount();
  },

  // 获取API基础URL
  getApiBase: function() {
    return this.globalData.apiBase;
  },

  // 获取WebSocket基础URL
  getWsBase: function() {
    return this.globalData.wsBase;
  },

  // 初始化配置
  initConfig: function() {
    var self = this;
    // 检查小程序更新
    if (wx.canIUse('getUpdateManager')) {
      var updateManager = wx.getUpdateManager();
      
      updateManager.onCheckForUpdate(function(res) {
        if (res.hasUpdate) {
          updateManager.onUpdateReady(function() {
            wx.showModal({
              title: '更新提示',
              content: '新版本已下载，是否立即重启应用？',
              success: function(res) {
                if (res.confirm) {
                  updateManager.applyUpdate();
                }
              }
            });
          });

          updateManager.onUpdateFailed(function() {
            wx.showToast({
              title: '新版本下载失败',
              icon: 'none'
            });
          });
        }
      });
    }
  },

  // 初始化网络状态监听
  initNetworkListener: function() {
    var self = this;
    wx.onNetworkStatusChange(function(res) {
      self.globalData.networkConnected = res.isConnected;
      self.globalData.networkType = res.networkType;
      
      if (!res.isConnected) {
        self.showToast('网络连接已断开，请检查网络设置', 'none');
      } else {
        self.checkLoginStatus();
      }
    });

    wx.getNetworkType({
      success: function(res) {
        self.globalData.networkConnected = res.networkType !== 'none';
        self.globalData.networkType = res.networkType;
      }
    });
  },

  // 检查登录状态
  checkLoginStatus: function() {
    var token = wx.getStorageSync('token');
    var userInfo = wx.getStorageSync('userInfo');
    
    if (token && userInfo) {
      this.globalData.isLogin = true;
      this.globalData.userInfo = userInfo;
      this.globalData.currentUserId = userInfo.id;
      this.validateToken();
    } else {
      this.globalData.isLogin = false;
      this.globalData.userInfo = null;
      this.globalData.currentUserId = null;
    }
  },

  // 验证token有效性
  validateToken: function(retry) {
    var self = this;
    retry = retry || 0;
    if (!self.globalData.isLogin) return;

    wx.request({
      url: self.globalData.apiBase + '/miniprogram/user/info',
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token'),
        'Content-Type': 'application/json'
      },
      timeout: self.globalData.requestTimeout,
      success: function(res) {
        if (res.statusCode === 200) {
          if (res.data && res.data.id) {
            self.globalData.userInfo = res.data;
            wx.setStorageSync('userInfo', res.data);
          }
        } else if (res.statusCode === 401 || res.statusCode === 403) {
          self.logout();
        }
      },
      fail: function(err) {
        if (retry < self.globalData.maxRetries) {
          setTimeout(function() {
            self.validateToken(retry + 1);
          }, 1000 * (retry + 1));
        }
      }
    });
  },

  // 登录
  login: function(userInfo, token) {
    this.globalData.isLogin = true;
    this.globalData.userInfo = userInfo;
    this.globalData.currentUserId = userInfo.id;
    
    wx.setStorageSync('userInfo', userInfo);
    if (token) {
      wx.setStorageSync('token', token);
    }
    
    this.getUnreadCount();
  },

  // 登出
  logout: function() {
    this.globalData.isLogin = false;
    this.globalData.userInfo = null;
    this.globalData.currentUserId = null;
    this.globalData.unreadCount = 0;
    
    wx.removeStorageSync('token');
    wx.removeStorageSync('userInfo');
    
    this.showToast('登录已过期，请重新登录', 'none');
    setTimeout(function() {
      wx.reLaunch({
        url: '/pages/login/login'
      });
    }, 1500);
  },

  // 获取未读消息数量
  getUnreadCount: function() {
    var self = this;
    if (!self.globalData.isLogin) return;
    
    wx.request({
      url: self.globalData.apiBase + '/unread_count',
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token'),
        'Content-Type': 'application/json'
      },
      timeout: self.globalData.requestTimeout,
      success: function(res) {
        if (res.statusCode === 200) {
          var count = res.data.count || res.data.unread_count || 0;
          self.updateUnreadCount(count);
        }
      },
      fail: function(err) {
        console.error('获取未读消息失败:', err);
      }
    });
  },

  // 更新未读消息数量
  updateUnreadCount: function(count) {
    this.globalData.unreadCount = count;
    
    if (count > 0) {
      try {
        wx.setTabBarBadge({
          index: 2,
          text: count > 99 ? '99+' : count.toString()
        });
      } catch (err) {
        console.error('设置tabBar徽标失败:', err);
      }
    } else {
      try {
        wx.removeTabBarBadge({
          index: 2
        });
      } catch (err) {
        console.error('移除tabBar徽标失败:', err);
      }
    }
  },

  // 通用请求方法
  request: function(options) {
    var self = this;
    var token = wx.getStorageSync('token');
    
    return new Promise(function(resolve, reject) {
      if (!self.globalData.networkConnected) {
        self.showToast('网络连接断开，请检查网络设置', 'none');
        reject(new Error('网络连接断开'));
        return;
      }

      var defaultHeader = {
        'Content-Type': 'application/json',
        'User-Agent': 'MiniProgram'
      };

      if (token) {
        defaultHeader['Authorization'] = 'Bearer ' + token;
      }

      var header = {};
      for (var key in defaultHeader) {
        header[key] = defaultHeader[key];
      }
      if (options.header) {
        for (var key in options.header) {
          header[key] = options.header[key];
        }
      }

      var url = options.url.indexOf('/') === 0 ? options.url : '/' + options.url;

      wx.request({
        url: self.globalData.apiBase + url,
        method: options.method || 'GET',
        data: options.data || {},
        header: header,
        timeout: options.timeout || self.globalData.requestTimeout,
        success: function(res) {
          if (res.statusCode === 401 || res.statusCode === 403) {
            self.logout();
            reject(new Error('登录已过期'));
          } else if (res.statusCode === 200) {
            resolve(res.data || res);
          } else {
            var errorMsg = (res.data && res.data.message) || (res.data && res.data.error) || '请求失败';
            self.showToast(errorMsg, 'none');
            reject(new Error(errorMsg));
          }
        },
        fail: function(err) {
          console.error('请求失败:', err);
          self.showToast('网络请求失败，请重试', 'none');
          reject(err);
        }
      });
    });
  },

  // 文件上传
  uploadFile: function(options) {
    var self = this;
    var token = wx.getStorageSync('token');
    
    return new Promise(function(resolve, reject) {
      if (!self.globalData.networkConnected) {
        self.showToast('网络连接断开', 'none');
        reject(new Error('网络连接断开'));
        return;
      }

      var header = {
        'Authorization': token ? 'Bearer ' + token : ''
      };

      var url = options.url.indexOf('/') === 0 ? options.url : '/' + options.url;

      wx.uploadFile({
        url: self.globalData.apiBase + url,
        filePath: options.filePath,
        name: options.name || 'file',
        formData: options.formData || {},
        header: header,
        timeout: options.timeout || 30000,
        success: function(res) {
          if (res.statusCode === 200) {
            try {
              var data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
              resolve(data);
            } catch (e) {
              resolve(res.data);
            }
          } else if (res.statusCode === 401 || res.statusCode === 403) {
            self.logout();
            reject(new Error('登录已过期'));
          } else {
            var errorMsg = (res.data && res.data.message) || '上传失败';
            self.showToast(errorMsg, 'none');
            reject(new Error(errorMsg));
          }
        },
        fail: function(err) {
          console.error('上传失败:', err);
          self.showToast('上传失败，请重试', 'none');
          reject(err);
        }
      });
    });
  },

  // 显示加载提示
  showLoading: function(title) {
    wx.showLoading({
      title: title || '加载中...',
      mask: true
    });
  },

  // 隐藏加载提示
  hideLoading: function() {
    wx.hideLoading();
  },

  // 显示消息提示
  showToast: function(title, icon) {
    wx.showToast({
      title: title,
      icon: icon || 'none',
      duration: 2000
    });
  },

  // 显示模态对话框
  showModal: function(options) {
    return new Promise(function(resolve, reject) {
      wx.showModal({
        title: options.title || '提示',
        content: options.content || '',
        confirmText: options.confirmText || '确定',
        cancelText: options.cancelText || '取消',
        success: function(res) {
          resolve(res);
        },
        fail: function(err) {
          reject(err);
        }
      });
    });
  },

  // 页面路由导航
  navigateTo: function(url) {
    return wx.navigateTo({ url: url });
  },

  navigateBack: function(delta) {
    return wx.navigateBack({ delta: delta || 1 });
  },

  reLaunch: function(url) {
    return wx.reLaunch({ url: url });
  },

  // 获取用户信息
  getUserInfo: function() {
    return this.globalData.userInfo;
  },

  // 检查用户是否已登录
  isUserLogin: function() {
    return this.globalData.isLogin;
  },

  // 获取当前用户ID
  getCurrentUserId: function() {
    return this.globalData.currentUserId;
  },

  // 检查网络连接
  isNetworkConnected: function() {
    return this.globalData.networkConnected;
  }
});
