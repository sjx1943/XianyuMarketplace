/**
 * 微信云托管对象存储工具模块
 * 
 * 使用前需要在 app.js 中初始化云托管：
 * wx.cloud.init({ env: 'your-env-id' })
 * 
 * 或使用 initCloudStorage() 初始化
 */

let cloudInitialized = false

/**
 * 初始化云托管
 * @param {Object} options 配置项
 * @param {string} options.resourceAppid 环境所属账号 AppID（可选，默认当前小程序）
 * @param {string} options.resourceEnv 云托管环境 ID
 */
function initCloudStorage(options = {}) {
  if (cloudInitialized) return
  
  try {
    if (options.resourceAppid && options.resourceEnv) {
      const cloud = new wx.cloud.Cloud({
        resourceAppid: options.resourceAppid,
        resourceEnv: options.resourceEnv
      })
      cloud.init()
      getApp().cloudStorage = cloud
    } else if (options.resourceEnv) {
      wx.cloud.init({ env: options.resourceEnv })
    }
    cloudInitialized = true
    console.log('[CloudStorage] 初始化成功')
  } catch (err) {
    console.error('[CloudStorage] 初始化失败:', err)
  }
}

/**
 * 获取云对象（优先使用自定义实例）
 */
function getCloudInstance() {
  const app = getApp()
  return app.cloudStorage || wx.cloud
}

/**
 * 上传图片到云存储
 * @param {string} filePath 本地临时文件路径
 * @param {string} prefix 云端目录前缀（如 'products', 'avatars'）
 * @param {Object} options 选项
 * @param {boolean} options.showLoading 是否显示loading（默认true，批量上传时设为false）
 * @returns {Promise<{fileID: string, tempUrl: string}>}
 */
function uploadImage(filePath, prefix = 'images', options = {}) {
  const showLoading = options.showLoading !== false
  
  return new Promise((resolve, reject) => {
    const timestamp = Date.now()
    const randomStr = Math.random().toString(36).substring(2, 8)
    const ext = filePath.split('.').pop() || 'jpg'
    const cloudPath = `${prefix}/${timestamp}_${randomStr}.${ext}`
    
    const cloud = getCloudInstance()
    
    if (showLoading) {
      wx.showLoading({ title: '上传中...', mask: true })
    }
    
    const uploadTask = cloud.uploadFile({
      cloudPath: cloudPath,
      filePath: filePath,
      success: async (res) => {
        console.log('[CloudStorage] 上传成功:', res.fileID)
        
        resolve({
          fileID: res.fileID,
          tempUrl: '',
          cloudPath: cloudPath
        })
      },
      fail: (err) => {
        console.error('[CloudStorage] 上传失败:', err)
        reject(err)
      },
      complete: () => {
        if (showLoading) {
          wx.hideLoading()
        }
      }
    })
  })
}

/**
 * 批量上传图片
 * @param {string[]} filePaths 本地临时文件路径数组
 * @param {string} prefix 云端目录前缀
 * @returns {Promise<Array<{fileID: string, tempUrl: string}>>}
 */
async function uploadImages(filePaths, prefix = 'images') {
  if (!filePaths || filePaths.length === 0) return []
  
  const total = filePaths.length
  wx.showLoading({ title: `上传中 1/${total}`, mask: true })
  
  const results = []
  
  for (let i = 0; i < filePaths.length; i++) {
    try {
      const result = await uploadImage(filePaths[i], prefix, { showLoading: false })
      results.push(result)
    } catch (err) {
      console.error(`[CloudStorage] 第${i + 1}张上传失败:`, err)
      results.push({ fileID: '', tempUrl: '', error: err })
    }
  }
  
  wx.hideLoading()
  
  const fileIDs = results.filter(r => r.fileID).map(r => r.fileID)
  if (fileIDs.length > 0) {
    try {
      const tempUrls = await getTempFileURL(fileIDs)
      let idx = 0
      for (let i = 0; i < results.length; i++) {
        if (results[i].fileID) {
          results[i].tempUrl = tempUrls[idx++] || ''
        }
      }
    } catch (err) {
      console.error('[CloudStorage] 获取临时链接失败:', err)
    }
  }
  
  return results
}

/**
 * 获取临时访问链接
 * @param {string|string[]} fileIDs 单个或多个 fileID
 * @returns {Promise<string|string[]>} 临时 HTTPS URL
 */
function getTempFileURL(fileIDs) {
  return new Promise((resolve, reject) => {
    const isArray = Array.isArray(fileIDs)
    const fileList = isArray ? fileIDs : [fileIDs]
    
    if (fileList.length === 0) {
      resolve(isArray ? [] : '')
      return
    }
    
    const cloud = getCloudInstance()
    
    const fileListObjects = fileList.map(id => ({ fileID: id }))
    
    cloud.getTempFileURL({
      fileList: fileListObjects,
      success: (res) => {
        const urls = res.fileList.map(item => item.tempFileURL || '')
        resolve(isArray ? urls : urls[0])
      },
      fail: (err) => {
        console.error('[CloudStorage] 获取临时链接失败:', err)
        reject(err)
      }
    })
  })
}

/**
 * 删除云端文件
 * @param {string|string[]} fileIDs 单个或多个 fileID
 * @returns {Promise<boolean>}
 */
function deleteFile(fileIDs) {
  return new Promise((resolve, reject) => {
    const fileList = Array.isArray(fileIDs) ? fileIDs : [fileIDs]
    
    if (fileList.length === 0) {
      resolve(true)
      return
    }
    
    const cloud = getCloudInstance()
    
    cloud.deleteFile({
      fileList: fileList,
      success: (res) => {
        console.log('[CloudStorage] 删除成功:', res)
        resolve(true)
      },
      fail: (err) => {
        console.error('[CloudStorage] 删除失败:', err)
        reject(err)
      }
    })
  })
}

/**
 * 检查是否为云存储 fileID
 * @param {string} url 
 * @returns {boolean}
 */
function isCloudFileID(url) {
  return url && url.startsWith('cloud://')
}

/**
 * 获取可显示的图片 URL
 * 如果是 cloud:// 开头的 fileID，需要转换为临时链接
 * 如果是普通 URL，直接返回
 * @param {string} url 
 * @returns {Promise<string>}
 */
async function getDisplayUrl(url) {
  if (!url) return ''
  
  if (isCloudFileID(url)) {
    try {
      return await getTempFileURL(url)
    } catch (err) {
      console.error('[CloudStorage] 获取显示链接失败:', err)
      return ''
    }
  }
  
  return url
}

/**
 * 批量获取可显示的图片 URL
 * @param {string[]} urls 
 * @returns {Promise<string[]>}
 */
async function getDisplayUrls(urls) {
  if (!urls || urls.length === 0) return []
  
  const cloudFileIDs = []
  const cloudIndexes = []
  const results = [...urls]
  
  urls.forEach((url, index) => {
    if (isCloudFileID(url)) {
      cloudFileIDs.push(url)
      cloudIndexes.push(index)
    }
  })
  
  if (cloudFileIDs.length > 0) {
    try {
      const tempUrls = await getTempFileURL(cloudFileIDs)
      cloudIndexes.forEach((originalIndex, i) => {
        results[originalIndex] = tempUrls[i] || ''
      })
    } catch (err) {
      console.error('[CloudStorage] 批量获取显示链接失败:', err)
    }
  }
  
  return results
}

module.exports = {
  initCloudStorage,
  uploadImage,
  uploadImages,
  getTempFileURL,
  deleteFile,
  isCloudFileID,
  getDisplayUrl,
  getDisplayUrls
}
