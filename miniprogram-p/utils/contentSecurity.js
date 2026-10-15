const api = require('./api.js')

const ContentSecurity = {
  checkText: async function(content, scene = 1) {
    console.log('[ContentSecurity] checkText 被调用, content:', content, 'scene:', scene)
    
    if (!content || content.trim().length === 0) {
      console.log('[ContentSecurity] 内容为空，跳过检测')
      return { safe: true, skipped: true }
    }
    
    try {
      const userInfo = wx.getStorageSync('userInfo') || {}
      const openid = userInfo.openid || ''
      
      console.log('[ContentSecurity] 准备调用API, baseURL:', api.baseURL)
      console.log('[ContentSecurity] 请求URL:', api.baseURL + '/api/miniprogram/security/text-check')
      
      const result = await api.post('/api/miniprogram/security/text-check', {
        content: content,
        openid: openid,
        scene: scene
      })
      
      console.log('[ContentSecurity] API返回结果:', result)
      
      if (result.success) {
        return {
          safe: result.safe !== false,
          label: result.label || 100,
          suggest: result.suggest || 'pass',
          skipped: result.skipped || false
        }
      }
      
      return { safe: true, skipped: true }
      
    } catch (error) {
      console.error('文本安全检测失败:', error)
      return { safe: true, skipped: true, error: error.message }
    }
  },

  checkMedia: async function(mediaUrl, mediaType = 2, scene = 1) {
    if (!mediaUrl) {
      return { success: true, safe: true, skipped: true }
    }
    
    try {
      const result = await api.post('/api/miniprogram/security/media-check', {
        media_url: mediaUrl,
        media_type: mediaType,
        scene: scene
      })
      
      console.log('[ContentSecurity] 图片检测结果:', result)
      
      return {
        success: result.success !== false,
        safe: result.safe !== false,
        suggestion: result.suggestion || 'Pass',
        label: result.label || '',
        reason: result.reason || '',
        skipped: result.skipped || false
      }
      
    } catch (error) {
      console.error('媒体安全检测失败:', error)
      return { success: false, safe: false, skipped: false, error: error.message }
    }
  },

  // 图片安全检测：将本地临时文件直传后端检测
  // 使用 wx.uploadFile 直传，天然兼容真机(wxfile://)和开发者工具(http://tmp/)的临时路径，
  // 无需 readFileSync / Base64 编码（历史函数名保留，避免破坏调用方）
  checkImageWithBase64: async function(tempFilePath, scene = 1) {
    if (!tempFilePath) {
      return { success: true, safe: true, skipped: true }
    }
    
    try {
      console.log('[ContentSecurity] 图片文件直传检测:', tempFilePath)
      
      const token = wx.getStorageSync('token') || ''
      
      const result = await new Promise((resolve, reject) => {
        wx.uploadFile({
          url: api.baseURL + '/api/miniprogram/security/media-check',
          filePath: tempFilePath,
          name: 'media',
          formData: {
            media_type: '2',
            scene: String(scene)
          },
          header: {
            'Authorization': token ? 'Bearer ' + token : ''
          },
          success: function(res) {
            if (res.statusCode !== 200) {
              reject(new Error('检测服务响应异常: ' + res.statusCode))
              return
            }
            try {
              resolve(JSON.parse(res.data))
            } catch (e) {
              reject(new Error('检测结果解析失败'))
            }
          },
          fail: reject
        })
      })
      
      console.log('[ContentSecurity] 图片检测结果:', result)
      
      return {
        success: result.success !== false,
        safe: result.safe !== false,
        suggestion: result.suggestion || 'Pass',
        label: result.label || '',
        reason: result.reason || '',
        skipped: result.skipped || false
      }
      
    } catch (error) {
      // 技术性失败（网络/服务异常）按"跳过"处理，与文本检测策略一致；
      // 上传后仍有服务端异步复检兜底，不因工具链问题误伤正常用户
      console.error('图片安全检测失败(技术原因，跳过):', error)
      return { success: false, safe: true, skipped: true, error: error.message }
    }
  },

  queryVerificationStatus: async function(traceId) {
    if (!traceId) {
      return { success: false, error: '缺少trace_id' }
    }
    
    try {
      const result = await api.post('/api/miniprogram/security/verification-status', {
        trace_id: traceId
      })
      
      return {
        success: result.success !== false,
        status: result.status,
        suggest: result.suggest,
        label: result.label,
        reviewed_at: result.reviewed_at
      }
      
    } catch (error) {
      console.error('查询验证状态失败:', error)
      return { success: false, error: error.message }
    }
  },

  checkImage: function(imageUrl, scene = 1) {
    // 注意：这是异步检测（mediaCheckAsync），仅提交检测请求
    // WeChat会在后台检测，结果通过回调返回，不能用来阻止上传
    return this.checkMedia(imageUrl, 2, scene)
  },

  checkAudio: function(audioUrl, scene = 1) {
    // 注意：这是异步检测（mediaCheckAsync），仅提交检测请求
    // WeChat会在后台检测，结果通过回调返回，不能用来阻止上传
    return this.checkMedia(audioUrl, 1, scene)
  },

  showViolationTip: function(customMessage) {
    wx.showToast({
      title: customMessage || '发布内容含违规信息！',
      icon: 'none',
      duration: 2500
    })
  },

  validateAndAlert: async function(content, scene = 1) {
    const result = await this.checkText(content, scene)
    
    if (!result.safe) {
      this.showViolationTip()
      return false
    }
    
    return true
  },

  validateMediaAndAlert: async function(mediaUrl, mediaType = 2, scene = 1) {
    const result = await this.checkMedia(mediaUrl, mediaType, scene)
    
    if (!result.success && !result.skipped) {
      this.showViolationTip()
      return false
    }
    
    return true
  },

  validateProfile: async function(profileData) {
    const { username, nickname, signature, roomNumber } = profileData
    
    const textsToCheck = [username, nickname, signature, roomNumber].filter(t => t && t.trim())
    
    for (const text of textsToCheck) {
      const result = await this.checkText(text, 1)
      if (!result.safe) {
        this.showViolationTip()
        return false
      }
    }
    
    return true
  },

  validateComment: async function(commentContent) {
    return this.validateAndAlert(commentContent, 2)
  },

  validateProductContent: async function(productData) {
    const { name, description } = productData
    
    if (name) {
      const nameResult = await this.checkText(name, 3)
      if (!nameResult.safe) {
        this.showViolationTip()
        return false
      }
    }
    
    if (description) {
      const descResult = await this.checkText(description, 3)
      if (!descResult.safe) {
        this.showViolationTip()
        return false
      }
    }
    
    return true
  },

  validateChatMessage: async function(messageContent) {
    return this.validateAndAlert(messageContent, 4)
  }
}

module.exports = ContentSecurity
