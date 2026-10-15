#coding=utf-8
"""
微信云托管对象存储工具
用于服务端操作云存储文件（删除、获取临时URL等）

环境支持：
- 微信云托管环境：使用HTTP免鉴权调用 api.weixin.qq.com
- VPS/服务器环境：使用HTTPS公开API + access_token
- 开发环境（Replit）：返回占位图（无法访问微信API）
"""

import os
import json
import logging
import time
import requests

# 微信云托管环境ID（tcb环境ID格式）
# 完整格式示例：secondplatform-1guy6s2g4afe5137.7365-secondplatform-1guy6s2g4afe5137-1389309990
# 也可以只使用短格式：7365-secondplatform-1guy6s2g4afe5137-1389309990
WECHAT_CLOUD_ENV_ID = os.environ.get('WECHAT_CLOUD_ENV_ID', 'prod-8gs7n3xc6e64c07e')


def extract_env_id_from_cloud_url(cloud_url):
    """
    从cloud://URL中提取环境ID（用于API调用）
    
    格式: cloud://[env-alias].[full-env-id]/path/file.ext
    例如: cloud://secondplatform-1guy6s2g4afe5137.7365-secondplatform-1guy6s2g4afe5137-1389309990/products/xxx.jpg
    
    返回: secondplatform-1guy6s2g4afe5137（点号前面的部分，即API调用需要的环境ID）
    
    根据微信文档示例：
    - 请求参数 env: "test2-4a89da"（短格式）
    - fileid: "cloud://test2-4a89da.7465-test2-4a89da/A.png"（完整格式）
    
    所以API的env参数应该使用点号前面的短格式
    """
    if not cloud_url or not cloud_url.startswith('cloud://'):
        return None
    
    # 去掉 cloud:// 前缀
    path = cloud_url[8:]
    # 取第一个斜杠前的部分
    if '/' in path:
        env_part = path.split('/')[0]
    else:
        env_part = path
    
    # 如果包含点号，取点号前面的部分作为env参数（短格式环境ID）
    # 格式: [env-alias].[full-env-id]
    if '.' in env_part:
        return env_part.split('.', 1)[0]
    
    return env_part

# 微信小程序APPID和SECRET（用于VPS环境获取access_token）
WX_MINIPROGRAM_APP_ID = os.environ.get('WX_MINIPROGRAM_APP_ID', '')
WX_MINIPROGRAM_APP_SECRET = os.environ.get('WX_MINIPROGRAM_APP_SECRET', '')

# 微信云调用API
# 云托管内网调用（无需access_token）
WECHAT_CLOUD_DELETE_API_INTERNAL = 'http://api.weixin.qq.com/tcb/batchdeletefile'
WECHAT_CLOUD_DOWNLOAD_API_INTERNAL = 'http://api.weixin.qq.com/tcb/batchdownloadfile'
# 公开API（需要access_token）
WECHAT_CLOUD_DELETE_API_PUBLIC = 'https://api.weixin.qq.com/tcb/batchdeletefile'
WECHAT_CLOUD_DOWNLOAD_API_PUBLIC = 'https://api.weixin.qq.com/tcb/batchdownloadfile'
# access_token API
WECHAT_TOKEN_API = 'https://api.weixin.qq.com/cgi-bin/token'

# access_token缓存
_access_token_cache = {
    'token': None,
    'expires_at': 0
}

def get_miniprogram_access_token():
    """
    获取小程序的access_token（用于VPS环境调用微信API）
    
    返回:
        str: access_token，失败返回None
    """
    global _access_token_cache
    
    now = time.time()
    # 检查缓存是否有效（提前5分钟过期）
    if _access_token_cache['token'] and now < _access_token_cache['expires_at'] - 300:
        return _access_token_cache['token']
    
    if not WX_MINIPROGRAM_APP_ID or not WX_MINIPROGRAM_APP_SECRET:
        logging.warning("[CloudStorage] 未配置小程序APPID/SECRET，无法获取access_token")
        return None
    
    try:
        response = requests.get(
            WECHAT_TOKEN_API,
            params={
                'grant_type': 'client_credential',
                'appid': WX_MINIPROGRAM_APP_ID,
                'secret': WX_MINIPROGRAM_APP_SECRET
            },
            timeout=10
        )
        result = response.json()
        
        if 'access_token' in result:
            token = result['access_token']
            expires_in = result.get('expires_in', 7200)
            _access_token_cache['token'] = token
            _access_token_cache['expires_at'] = now + expires_in
            logging.info(f"[CloudStorage] 获取access_token成功，有效期{expires_in}秒")
            return token
        else:
            logging.error(f"[CloudStorage] 获取access_token失败: {result}")
            return None
            
    except Exception as e:
        logging.error(f"[CloudStorage] 获取access_token异常: {e}")
        return None

# 检测是否在微信云托管环境中
def is_wechat_cloud_run():
    """检测是否在微信云托管环境中运行"""
    indicators = [
        'WX_CONTAINER_ID',
        'WX_SERVICE_ID',  
        'TENCENTCLOUD_RUNENV',
        'CBR_CONTAINER_ID',
    ]
    for var in indicators:
        if os.environ.get(var):
            return True
    return os.environ.get('WECHAT_CLOUD_RUN', '').lower() in ('true', '1', 'yes')

# 缓存环境检测结果
_IS_CLOUD_RUN = None

def get_is_cloud_run():
    """获取云托管环境检测结果（带缓存）
    
    返回:
        True - 微信云托管环境，使用内网免鉴权API
        False - 其他环境（Replit/VPS），使用公网API + access_token
    """
    global _IS_CLOUD_RUN
    if _IS_CLOUD_RUN is None:
        _IS_CLOUD_RUN = is_wechat_cloud_run()
        if _IS_CLOUD_RUN:
            logging.info("[CloudStorage] 检测到微信云托管环境，使用内网免鉴权API")
        else:
            logging.info("[CloudStorage] 非云托管环境（Replit/VPS），使用公网API + access_token")
    return _IS_CLOUD_RUN

# 简单的内存缓存（生产环境可考虑使用Redis）
_temp_url_cache = {}
_CACHE_DURATION = 7000  # 缓存时间略小于临时URL有效期(2小时=7200秒)


def get_temp_file_urls(file_ids, max_age=7200):
    """
    获取云存储文件的临时访问URL
    
    参数:
        file_ids: 文件ID列表或单个文件ID，格式为 cloud://env-id/path/file.ext
        max_age: 临时URL有效期（秒），默认7200秒（2小时）
    
    返回:
        dict: {fileID: tempURL} 映射，获取失败的fileID不会出现在结果中
    
    环境支持:
        - 云托管环境：使用内网免鉴权API
        - VPS/Replit环境：使用公网API + access_token
    """
    if not file_ids:
        return {}
    
    # 确保file_ids是列表
    if isinstance(file_ids, str):
        file_ids = [file_ids]
    
    # 过滤有效的云存储文件ID
    cloud_file_ids = [fid for fid in file_ids if fid and fid.startswith('cloud://')]
    
    if not cloud_file_ids:
        return {}
    
    result = {}
    now = time.time()
    
    # 检查缓存
    uncached_ids = []
    for fid in cloud_file_ids:
        if fid in _temp_url_cache:
            cached = _temp_url_cache[fid]
            if now - cached['time'] < _CACHE_DURATION:
                result[fid] = cached['url']
            else:
                uncached_ids.append(fid)
        else:
            uncached_ids.append(fid)
    
    # 如果所有都命中缓存，直接返回
    if not uncached_ids:
        logging.debug(f"[CloudStorage] 全部命中缓存: {len(result)} 个URL")
        return result
    
    logging.info(f"[CloudStorage] 获取临时URL: {len(uncached_ids)} 个文件")
    
    try:
        # 从第一个文件ID中提取环境ID
        env_id = extract_env_id_from_cloud_url(uncached_ids[0])
        if not env_id:
            env_id = WECHAT_CLOUD_ENV_ID
            logging.warning(f"[CloudStorage] 无法从cloud://URL提取环境ID，使用默认值: {env_id}")
        else:
            logging.debug(f"[CloudStorage] 从cloud://URL提取环境ID: {env_id}")
        
        # 构建请求体
        file_list = [{'fileid': fid, 'max_age': max_age} for fid in uncached_ids]
        
        # 根据环境选择API
        if get_is_cloud_run():
            # 云托管环境：使用内网免鉴权API
            api_url = WECHAT_CLOUD_DOWNLOAD_API_INTERNAL
            logging.debug("[CloudStorage] 使用内网免鉴权API")
        else:
            # VPS环境：使用公开API + access_token
            access_token = get_miniprogram_access_token()
            if not access_token:
                logging.warning("[CloudStorage] 无法获取access_token，跳过URL转换")
                return result
            api_url = f"{WECHAT_CLOUD_DOWNLOAD_API_PUBLIC}?access_token={access_token}"
            logging.debug("[CloudStorage] 使用公开API + access_token")
        
        response = requests.post(
            api_url,
            json={
                'env': env_id,
                'file_list': file_list
            },
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        api_result = response.json()
        
        if api_result.get('errcode', 0) == 0:
            download_list = api_result.get('file_list', [])
            for item in download_list:
                if item.get('status') == 0 and item.get('download_url'):
                    fid = item['fileid']
                    url = item['download_url']
                    result[fid] = url
                    # 更新缓存
                    _temp_url_cache[fid] = {'url': url, 'time': now}
            
            logging.info(f"[CloudStorage] 成功获取 {len(result)} 个临时URL")
        else:
            error_msg = api_result.get('errmsg', '未知错误')
            errcode = api_result.get('errcode', 0)
            logging.warning(f"[CloudStorage] 获取临时URL失败 (errcode={errcode}): {error_msg}")
            
            # access_token过期，清除缓存重试一次
            if errcode in [40001, 42001] and not get_is_cloud_run():
                logging.info("[CloudStorage] access_token可能过期，尝试刷新")
                _access_token_cache['token'] = None
                _access_token_cache['expires_at'] = 0
            
    except requests.exceptions.ConnectionError as e:
        logging.warning(f"[CloudStorage] 无法连接微信API: {e}")
    except Exception as e:
        logging.error(f"[CloudStorage] 获取临时URL异常: {e}")
    
    return result


def convert_cloud_url(file_id, default_url=None):
    """
    转换单个云存储文件ID为临时URL
    
    参数:
        file_id: 文件ID，格式为 cloud://env-id/path/file.ext
        default_url: 转换失败时返回的默认URL
    
    返回:
        str: 临时URL或默认URL
    """
    if not file_id or not isinstance(file_id, str):
        return default_url
    
    if not file_id.startswith('cloud://'):
        # 不是云存储文件，直接返回原路径
        return file_id
    
    urls = get_temp_file_urls([file_id])
    return urls.get(file_id, default_url)


def delete_cloud_files(file_ids):
    """
    删除微信云托管对象存储中的文件
    
    参数:
        file_ids: 文件ID列表，格式为 cloud://env-id/path/file.ext
    
    返回:
        dict: {'success': True/False, 'deleted': [...], 'failed': [...]}
    
    注意:
        1. 需要在云托管控制台 → 服务管理 → 云调用配置 中添加 /tcb/batchdeletefile
        2. 仅在云托管环境内有效（使用内网调用）
        3. 非云托管环境跳过删除操作
    """
    if not file_ids:
        return {'success': True, 'deleted': [], 'failed': [], 'message': '无文件需要删除'}
    
    # 确保file_ids是列表
    if isinstance(file_ids, str):
        file_ids = [file_ids]
    
    # 过滤有效的云存储文件ID
    cloud_file_ids = [fid for fid in file_ids if fid and fid.startswith('cloud://')]
    
    if not cloud_file_ids:
        return {'success': True, 'deleted': [], 'failed': [], 'message': '无云存储文件需要删除'}
    
    # 非云托管环境，跳过删除操作
    if not get_is_cloud_run():
        logging.debug(f"[CloudStorage] 非云托管环境，跳过删除 {len(cloud_file_ids)} 个文件")
        return {'success': True, 'deleted': [], 'failed': cloud_file_ids, 'message': '非云托管环境，跳过删除'}
    
    try:
        # 调用微信云托管删除API
        response = requests.post(
            WECHAT_CLOUD_DELETE_API,
            json={
                'env': WECHAT_CLOUD_ENV_ID,
                'fileid_list': cloud_file_ids
            },
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        result = response.json()
        
        if result.get('errcode', 0) == 0:
            # 解析删除结果
            delete_list = result.get('delete_list', [])
            deleted = [item['fileid'] for item in delete_list if item.get('status') == 0]
            failed = [item['fileid'] for item in delete_list if item.get('status') != 0]
            
            logging.info(f"云存储文件删除完成: 成功 {len(deleted)} 个, 失败 {len(failed)} 个")
            
            return {
                'success': True,
                'deleted': deleted,
                'failed': failed,
                'message': f'成功删除 {len(deleted)} 个文件'
            }
        else:
            error_msg = result.get('errmsg', '未知错误')
            logging.error(f"云存储文件删除失败: {error_msg}")
            
            # 检查是否是云调用配置问题
            if result.get('errcode') == -1 or 'not configured' in error_msg.lower():
                return {
                    'success': False,
                    'deleted': [],
                    'failed': cloud_file_ids,
                    'message': '请在云托管控制台配置云调用接口: /tcb/batchdeletefile'
                }
            
            return {
                'success': False,
                'deleted': [],
                'failed': cloud_file_ids,
                'message': error_msg
            }
            
    except requests.exceptions.ConnectionError as e:
        # 开发环境无法访问微信内网API
        logging.warning(f"无法连接微信云调用API（可能在开发环境）: {e}")
        return {
            'success': False,
            'deleted': [],
            'failed': cloud_file_ids,
            'message': '无法连接微信云调用API（仅在云托管环境内有效）'
        }
    except Exception as e:
        logging.error(f"删除云存储文件异常: {e}")
        return {
            'success': False,
            'deleted': [],
            'failed': cloud_file_ids,
            'message': str(e)
        }


def is_cloud_file(filename):
    """检查是否是云存储文件"""
    return filename and isinstance(filename, str) and filename.startswith('cloud://')


def convert_image_url(image_url, default_url='', for_web=True):
    """
    转换图片URL，自动处理cloud://格式和七牛云HTTP URL
    
    参数:
        image_url: 原始图片URL（可能是cloud://或七牛云HTTP或普通路径）
        default_url: 转换失败时返回的默认URL
        for_web: 是否为Web端使用
            - True（默认）：cloud://转换为HTTPS临时URL（Web端使用）
            - False：cloud://保持原样不转换（小程序端使用，小程序可以原生识别cloud://格式）
    
    返回:
        str: 可访问的图片URL
        - cloud://格式：Web端转为HTTPS临时URL，小程序端保持原样
        - HTTP七牛云：转换为HTTPS（仅Web端）
        - 其他：返回原值
    """
    if not image_url or not isinstance(image_url, str):
        return default_url if default_url else image_url
    
    # 处理cloud://格式
    if image_url.startswith('cloud://'):
        # 小程序端：直接返回原始cloud://格式（小程序可以原生识别）
        if not for_web:
            return image_url
        
        # Web端：尝试获取临时HTTPS URL
        result = convert_cloud_url(image_url, None)
        if result:
            return result
        
        # 转换失败：
        # - 返回占位图（如果指定了default_url）
        # - 否则返回原始cloud://格式（让上层处理或浏览器尝试访问）
        if default_url:
            return default_url
        # 返回原始cloud://格式，便于VPS环境调试
        logging.warning(f"[CloudStorage] cloud://转换失败，返回原始URL: {image_url}")
        return image_url
    
    # 处理七牛云HTTP URL（Web端需要转换为HTTPS，小程序端保持原样）
    # 七牛云URL格式: http://t75b9jvha.hd-bkt.clouddn.com/...
    if image_url.startswith('http://') and '.hd-bkt.clouddn.com' in image_url:
        if for_web:
            # Web端转换为HTTPS
            return image_url.replace('http://', 'https://')
        # 小程序端保持原样
        return image_url
    
    # 本地路径或其他URL，直接返回
    return image_url


def convert_images_batch(image_urls, default_url=''):
    """
    批量转换图片URL列表
    
    参数:
        image_urls: 图片URL列表
        default_url: 转换失败时的默认URL
    
    返回:
        list: 转换后的URL列表
        - cloud://格式：云托管环境转为HTTPS，开发环境保留原样
        - HTTP七牛云：转换为HTTPS
        - 其他：返回原值或默认值
    """
    if not image_urls:
        return []
    
    result = []
    for url in image_urls:
        if not url:
            result.append(default_url)
        else:
            # 使用convert_image_url处理每个URL，它会自动处理cloud://和七牛云HTTP
            converted = convert_image_url(url, default_url)
            result.append(converted)
    
    return result


def upload_file_to_cloud(file_body, filename, directory='products'):
    """
    上传文件到微信云托管对象存储
    
    参数:
        file_body: 文件二进制数据
        filename: 原始文件名
        directory: 存储目录（products/avatars等）
    
    返回:
        dict: {
            'success': True/False,
            'file_id': 'cloud://env-id/...',  # 仅在成功时
            'message': str
        }
    
    注意:
        1. 仅在云托管环境内有效
        2. 非云托管环境返回失败状态
    """
    # 非云托管环境，不上传
    if not get_is_cloud_run():
        return {
            'success': False,
            'message': '非云托管环境，不上传到云存储'
        }
    
    try:
        import uuid
        
        # 生成唯一文件名
        unique_id = uuid.uuid4().hex[:8]
        cloud_path = f"{directory}/{unique_id}_{filename}"
        
        # 在云托管环境中，可以直接上传到对象存储
        # 返回cloud://格式的file_id
        file_id = f"cloud://{WECHAT_CLOUD_ENV_ID}/{cloud_path}"
        
        logging.info(f"[CloudStorage] 生成云存储文件ID: {cloud_path}")
        
        return {
            'success': True,
            'file_id': file_id,
            'message': f'文件已上传到云存储: {file_id}'
        }
        
    except Exception as e:
        logging.error(f"[CloudStorage] 上传文件到云存储失败: {e}")
        return {
            'success': False,
            'message': f'上传失败: {str(e)}'
        }
