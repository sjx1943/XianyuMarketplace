// 小程序配置文件
const config = {
  // API基础URL - 替换为您的Replit应用域名
  API_BASE: 'https://your-app.replit.app',
  
  // WebSocket URL（聊天功能）
  WS_BASE: 'wss://your-app.replit.app',
  
  // 微信小程序AppID - 替换为您的小程序AppID
  WX_APP_ID: 'wx1234567890abcdef',
  
  // 请求超时时间（毫秒）
  REQUEST_TIMEOUT: 10000,
  
  // 图片上传大小限制（字节，默认10MB）
  MAX_IMAGE_SIZE: 10 * 1024 * 1024,
  
  // 每次加载商品数量
  PAGE_SIZE: 20,
  
  // 默认商品封面
  DEFAULT_PRODUCT_IMAGE: '/images/default-product.png'
}

module.exports = config
