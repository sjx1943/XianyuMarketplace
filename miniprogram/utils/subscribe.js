// 订阅消息工具类
const TEMPLATE_IDS = {
  ORDER_STATUS: 'xxxxxxxxxxxxxxx',  // 订单状态变更通知
  NEW_MESSAGE: 'yyyyyyyyyyyyyyy',   // 新消息提醒
  PRODUCT_SOLD: 'zzzzzzzzzzzzzzz'   // 商品售出通知
}

/**
 * 请求订阅消息
 * @param {Array} types - 订阅类型数组，如 ['ORDER_STATUS', 'NEW_MESSAGE']
 * @returns {Promise}
 */
function requestSubscribe(types = []) {
  const tmplIds = types.map(type => TEMPLATE_IDS[type]).filter(id => id)
  
  if (tmplIds.length === 0) {
    return Promise.reject(new Error('无效的订阅类型'))
  }

  return new Promise((resolve, reject) => {
    wx.requestSubscribeMessage({
      tmplIds: tmplIds,
      success: (res) => {
        console.log('订阅成功:', res)
        
        // 检查每个模板的订阅结果
        const results = tmplIds.map(id => ({
          templateId: id,
          accepted: res[id] === 'accept'
        }))
        
        resolve(results)
      },
      fail: (err) => {
        console.error('订阅失败:', err)
        reject(err)
      }
    })
  })
}

/**
 * 订阅订单状态通知
 */
function subscribeOrderStatus() {
  return requestSubscribe(['ORDER_STATUS'])
}

/**
 * 订阅新消息提醒
 */
function subscribeNewMessage() {
  return requestSubscribe(['NEW_MESSAGE'])
}

/**
 * 订阅商品售出通知
 */
function subscribeProductSold() {
  return requestSubscribe(['PRODUCT_SOLD'])
}

/**
 * 一次性订阅所有类型
 */
function subscribeAll() {
  return requestSubscribe(['ORDER_STATUS', 'NEW_MESSAGE', 'PRODUCT_SOLD'])
}

module.exports = {
  TEMPLATE_IDS,
  requestSubscribe,
  subscribeOrderStatus,
  subscribeNewMessage,
  subscribeProductSold,
  subscribeAll
}
