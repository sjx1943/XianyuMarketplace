// 配置文件
const isDev = false // 是否为开发环境

// API配置
const config = {
  isDev: isDev,
  
  // API域名配置
  api: {
    // 生产环境
    production: {
      host: 'https://your-production-domain.com',
      apiBase: '/api',
      wsBase: '/ws'
    },
    // 开发环境
    development: {
      host: 'http://localhost:5000',
      apiBase: '/api',
      wsBase: '/ws'
    }
  },

  // 应用配置
  app: {
    name: '小区二手交易',
    version: '1.0.0',
    platform: 'WeChat MiniProgram'
  },

  // 请求超时配置（毫秒）
  timeout: {
    request: 10000,
    upload: 30000,
    download: 10000
  },

  // 重试配置
  retry: {
    maxAttempts: 3,
    delay: 1000 // 初始延迟时间
  },

  // 缓存配置
  cache: {
    enabled: true,
    ttl: 3600000 // 1小时（毫秒）
  },

  // 分页配置
  pagination: {
    pageSize: 20,
    maxPages: 100
  }
}

// 获取API基础URL
function getApiBase() {
  const env = isDev ? 'development' : 'production'
  const apiConfig = config.api[env]
  return apiConfig.host + apiConfig.apiBase
}

// 获取WebSocket基础URL
function getWsBase() {
  const env = isDev ? 'development' : 'production'
  const apiConfig = config.api[env]
  return apiConfig.host.replace(/^http/, 'ws') + apiConfig.wsBase
}

module.exports = {
  config,
  getApiBase,
  getWsBase,
  isDev
}
