// 配置文件
// ⚠️ 部署前必须修改 production.host 为您的实际后端域名
const isDev = false // 生产环境设为 false，开发调试设为 true

// API配置
const config = {
  isDev: isDev,
  
  // API域名配置
  api: {
    // 生产环境 - ⚠️ 必须修改为您的实际域名
    production: {
      host: 'https://okashii.top',  // ← 修改为您的 Replit 域名
      apiBase: '',  // 后端路由不需要 /api 前缀
      wsBase: '/ws'
    },
    // 开发环境（本地调试用）
    development: {
      host: 'http://localhost:5000',
      apiBase: '',  // 后端路由不需要 /api 前缀
      wsBase: '/ws'
    }
  },

  // 应用配置
  app: {
    name: '翠友雅集S',
    version: '1.1.0',
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

// 导出 API_BASE 供 api.js 使用
const API_BASE = getApiBase()
const WS_BASE = getWsBase()

// 获取图片完整URL（用于小程序 image 标签）
function getImageUrl(filename) {
  if (!filename) return ''
  // 如果已经是完整URL，直接返回
  if (filename.startsWith('http://') || filename.startsWith('https://')) {
    return filename
  }
  // 否则拼接完整URL
  const env = isDev ? 'development' : 'production'
  const host = config.api[env].host
  return `${host}/static/images/${filename}`
}

// 获取默认头像URL
function getDefaultAvatarUrl() {
  const env = isDev ? 'development' : 'production'
  const host = config.api[env].host
  return `${host}/static/images/default-avatar.png`
}

module.exports = {
  config,
  getApiBase,
  getWsBase,
  getImageUrl,
  getDefaultAvatarUrl,
  isDev,
  API_BASE,
  WS_BASE
}
