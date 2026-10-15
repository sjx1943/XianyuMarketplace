const TEMPLATE_IDS = {
  ORDER_STATUS: 'k4RD1_bIRofb3DEjFX8hntwUzXnz5RyQ2pr0UGl51VM',
  NEW_MESSAGE: 'rjOrDn_8fVDXDAUGD4gG2ZKAYb9BuKzBW_ajM46hRyw',
  PRODUCT_SOLD: 'vl_2Uka9BE2-qgP9Snbse4IFSO6mUe5rPnQxzjcFEXk'
}

function requestSubscribe(templateTypes) {
  return new Promise((resolve, reject) => {
    const tmplIds = templateTypes.map(type => TEMPLATE_IDS[type]).filter(Boolean)
    
    if (tmplIds.length === 0) {
      reject(new Error('无效的模板类型'))
      return
    }
    
    wx.requestSubscribeMessage({
      tmplIds: tmplIds,
      success: (res) => {
        const results = {}
        let acceptCount = 0
        
        tmplIds.forEach(id => {
          if (res[id] === 'accept') {
            acceptCount++
            results[id] = 'accept'
          } else if (res[id] === 'reject') {
            results[id] = 'reject'
          } else {
            results[id] = res[id] || 'unknown'
          }
        })
        
        resolve({
          success: acceptCount > 0,
          acceptCount,
          totalCount: tmplIds.length,
          results
        })
      },
      fail: (err) => {
        if (err.errCode === 20004) {
          resolve({
            success: false,
            error: '用户关闭了订阅消息功能',
            errCode: 20004
          })
        } else {
          reject(err)
        }
      }
    })
  })
}

function subscribeOrderNotification() {
  return requestSubscribe(['ORDER_STATUS'])
}

function subscribeMessageNotification() {
  return requestSubscribe(['NEW_MESSAGE'])
}

function subscribeProductSoldNotification() {
  return requestSubscribe(['PRODUCT_SOLD'])
}

function subscribeAllNotifications() {
  return requestSubscribe(['ORDER_STATUS', 'NEW_MESSAGE', 'PRODUCT_SOLD'])
}

module.exports = {
  TEMPLATE_IDS,
  requestSubscribe,
  subscribeOrderNotification,
  subscribeMessageNotification,
  subscribeProductSoldNotification,
  subscribeAllNotifications
}
