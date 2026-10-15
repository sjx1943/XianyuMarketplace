// 缓存工具类
const config = require('./config.js')

class Cache {
  constructor() {
    this.prefix = 'miniapp_cache_'
    this.ttl = config.config.cache.ttl
  }

  // 设置缓存
  set(key, value, ttl = this.ttl) {
    if (!config.config.cache.enabled) return

    try {
      const data = {
        value: value,
        timestamp: Date.now(),
        ttl: ttl
      }
      wx.setStorageSync(this.prefix + key, data)
    } catch (e) {
      console.error('缓存设置失败:', e)
    }
  }

  // 获取缓存
  get(key) {
    if (!config.config.cache.enabled) return null

    try {
      const data = wx.getStorageSync(this.prefix + key)
      
      if (!data) return null
      
      // 检查缓存是否过期
      const now = Date.now()
      if (now - data.timestamp > data.ttl) {
        this.remove(key)
        return null
      }
      
      return data.value
    } catch (e) {
      console.error('缓存获取失败:', e)
      return null
    }
  }

  // 移除缓存
  remove(key) {
    try {
      wx.removeStorageSync(this.prefix + key)
    } catch (e) {
      console.error('缓存移除失败:', e)
    }
  }

  // 清空所有缓存
  clear() {
    try {
      const allKeys = wx.getStorageInfoSync().keys || []
      allKeys.forEach(key => {
        if (key.startsWith(this.prefix)) {
          wx.removeStorageSync(key)
        }
      })
    } catch (e) {
      console.error('缓存清空失败:', e)
    }
  }

  // 获取缓存大小
  getSize() {
    try {
      return wx.getStorageInfoSync().currentSize
    } catch (e) {
      return 0
    }
  }
}

module.exports = new Cache()
