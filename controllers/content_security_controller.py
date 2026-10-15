#coding=utf-8
"""
内容安全检测控制器
- 文本检测: 微信 msgSecCheck (Security 2.0)
- 图片检测: 腾讯云 IMS (同步接口，替代微信 mediaCheckAsync)
"""

import tornado.web
import json
import os
import logging
import time
import requests
import hashlib
import base64
from functools import lru_cache
from sqlalchemy.orm import sessionmaker
from base.base import engine

ContentSecuritySession = sessionmaker(bind=engine)

WX_MINIPROGRAM_APP_ID = os.environ.get('WX_MINIPROGRAM_APP_ID', '').strip()
WX_MINIPROGRAM_APP_SECRET = os.environ.get('WX_MINIPROGRAM_APP_SECRET',
                                           '').strip()
WECHAT_CALLBACK_TOKEN = os.environ.get('WECHAT_CALLBACK_TOKEN', '').strip()

TENCENT_SECRET_ID = os.environ.get('TENCENT_SECRET_ID', '').strip()
TENCENT_SECRET_KEY = os.environ.get('TENCENT_SECRET_KEY', '').strip()
TENCENT_IMS_BIZ_TYPE = 'photo_upload'

_access_token_cache = {'token': None, 'expires_at': 0}


def invalidate_access_token():
    """清除缓存的 access_token"""
    global _access_token_cache
    _access_token_cache['token'] = None
    _access_token_cache['expires_at'] = 0
    logging.warning("已清除缓存的微信 access_token")


def get_wechat_access_token(force_refresh=False):
    """
    获取微信小程序的 access_token (带缓存)
    有效期7200秒，提前5分钟刷新
    """
    global _access_token_cache

    current_time = time.time()
    if not force_refresh and _access_token_cache[
            'token'] and current_time < _access_token_cache['expires_at'] - 300:
        return _access_token_cache['token']

    if not WX_MINIPROGRAM_APP_ID or not WX_MINIPROGRAM_APP_SECRET:
        logging.error("微信小程序 AppID 或 AppSecret 未配置")
        return None

    try:
        url = 'https://api.weixin.qq.com/cgi-bin/token'
        params = {
            'grant_type': 'client_credential',
            'appid': WX_MINIPROGRAM_APP_ID,
            'secret': WX_MINIPROGRAM_APP_SECRET
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if 'access_token' in data:
            _access_token_cache['token'] = data['access_token']
            _access_token_cache['expires_at'] = current_time + data.get(
                'expires_in', 7200)
            logging.info("获取微信 access_token 成功")
            return data['access_token']
        else:
            logging.error(f"获取微信 access_token 失败: {data}")
            return None
    except Exception as e:
        logging.error(f"获取微信 access_token 异常: {e}")
        return None


def check_text_security(content, openid, scene=1, retry=True):
    """
    检查文本内容安全 (本地敏感词 + msgSecCheck v2.0)
    
    参数:
        content: 需要检测的文本内容 (最大2500字)
        openid: 用户的openid
        scene: 场景值 (1=资料, 2=评论, 3=论坛, 4=社交日志)
        retry: 是否在auth错误时重试
    
    返回:
        dict: {
            'safe': True/False,
            'label': 标签枚举值,
            'suggest': 'pass'/'risky'/'review'
        }
    """
    try:
        from utils.keyword_filter import check_text as local_check
        local_result = local_check(content)
        if not local_result['safe']:
            logging.warning(
                f"[SECURITY] 本地敏感词检测拦截: {local_result['matched_keywords']}")
            return {
                'safe': False,
                'label': 20000,
                'suggest': 'risky',
                'local_filter': True,
                'matched_keywords': local_result['matched_keywords']
            }
    except Exception as e:
        logging.warning(f"[SECURITY] 本地敏感词检测异常: {e}")

    access_token = get_wechat_access_token()
    if not access_token:
        logging.warning("无法获取 access_token，跳过文本安全检测")
        return {'safe': True, 'label': 100, 'suggest': 'pass', 'skipped': True}

    try:
        url = f'https://api.weixin.qq.com/wxa/msg_sec_check?access_token={access_token}'
        payload = {
            'openid': openid,
            'scene': scene,
            'version': 2,
            'content': content[:2500]
        }

        response = requests.post(url, json=payload, timeout=10)
        data = response.json()

        logging.info(
            f"[SECURITY] msgSecCheck 请求: content='{content[:50]}', openid={openid}, scene={scene}"
        )
        logging.info(f"[SECURITY] msgSecCheck 完整响应: {data}")

        errcode = data.get('errcode')

        if errcode == 0:
            result = data.get('result', {})
            suggest = result.get('suggest', 'pass')
            label = result.get('label', 100)

            return {
                'safe': suggest == 'pass',
                'label': label,
                'suggest': suggest,
                'trace_id': data.get('trace_id')
            }
        elif errcode in [40001, 40014, 42001] and retry:
            logging.warning(f"access_token 失效(errcode={errcode})，刷新后重试")
            invalidate_access_token()
            return check_text_security(content, openid, scene, retry=False)
        else:
            logging.error(f"msgSecCheck 失败: {data}")
            if errcode == 61010:
                return {
                    'safe': True,
                    'label': 100,
                    'suggest': 'pass',
                    'skipped': True,
                    'reason': 'user_inactive'
                }
            return {
                'safe': True,
                'label': 100,
                'suggest': 'pass',
                'skipped': True,
                'error': data
            }

    except Exception as e:
        logging.error(f"msgSecCheck 异常: {e}")
        return {
            'safe': True,
            'label': 100,
            'suggest': 'pass',
            'skipped': True,
            'error': str(e)
        }


def check_image_with_tencent_ims(image_url=None, image_base64=None):
    """
    使用腾讯云 IMS 同步检测图片内容安全
    
    参数:
        image_url: 图片URL (公网可访问)
        image_base64: 图片Base64编码 (不含 data:image/xxx;base64, 前缀)
    
    返回:
        dict: {
            'safe': True/False,
            'suggestion': 'Pass'/'Block'/'Review',
            'label': 违规标签,
            'sub_label': 子标签,
            'reason': 拦截原因描述
        }
    """
    if not TENCENT_SECRET_ID or not TENCENT_SECRET_KEY:
        logging.warning("[IMS] 腾讯云密钥未配置，跳过图片检测")
        return {'safe': True, 'skipped': True, 'reason': 'no_credentials'}

    try:
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.ims.v20201229 import ims_client, models

        cred = credential.Credential(TENCENT_SECRET_ID, TENCENT_SECRET_KEY)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "ims.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = ims_client.ImsClient(cred, "ap-shanghai", clientProfile)

        req = models.ImageModerationRequest()

        if image_url:
            req.FileUrl = image_url
        elif image_base64:
            req.FileContent = image_base64
        else:
            return {'safe': True, 'skipped': True, 'reason': 'no_image'}

        req.BizType = TENCENT_IMS_BIZ_TYPE

        resp = client.ImageModeration(req)

        suggestion = resp.Suggestion
        label = resp.Label
        sub_label = getattr(resp, 'SubLabel', '')

        logging.info(
            f"[IMS] 检测结果: Suggestion={suggestion}, Label={label}, SubLabel={sub_label}"
        )

        if suggestion == 'Pass':
            return {'safe': True, 'suggestion': suggestion, 'label': label}
        else:
            reason = f"图片含有违规内容({label})"
            if sub_label:
                reason += f" - {sub_label}"
            logging.warning(f"[IMS] 图片被拦截: {reason}")
            return {
                'safe': False,
                'suggestion': suggestion,
                'label': label,
                'sub_label': sub_label,
                'reason': reason
            }

    except Exception as e:
        logging.error(f"[IMS] 腾讯云IMS调用异常: {e}")
        import traceback
        traceback.print_exc()
        return {
            'safe': False,
            'skipped': False,
            'error': str(e),
            'reason': '安全检测服务暂时不可用'
        }


def check_media_security_async(media_url,
                               openid,
                               media_type=2,
                               scene=1,
                               retry=True):
    """
    图片安全检测 - 使用腾讯云 IMS 同步接口
    
    注意: 此函数名保留 'async' 是为了向后兼容，但实际已改为同步检测
    
    参数:
        media_url: 图片URL (必须是可公网访问的URL)
        openid: 用户的openid (保留参数，兼容旧调用)
        media_type: 1=音频, 2=图片
        scene: 场景值 (保留参数，兼容旧调用)
        retry: 是否重试 (保留参数)
    
    返回:
        dict: {
            'success': True/False,
            'safe': True/False,
            'suggestion': 'Pass'/'Block'/'Review',
            'label': 违规标签,
            'reason': 拦截原因
        }
    """
    if media_type != 2:
        logging.warning(f"[IMS] 暂不支持音频检测 (media_type={media_type})")
        return {
            'success': True,
            'safe': True,
            'skipped': True,
            'reason': 'audio_not_supported'
        }

    result = check_image_with_tencent_ims(image_url=media_url)

    return {
        'success': True,
        'safe': result.get('safe', True),
        'suggestion': result.get('suggestion', 'Pass'),
        'label': result.get('label', ''),
        'sub_label': result.get('sub_label', ''),
        'reason': result.get('reason', ''),
        'skipped': result.get('skipped', False)
    }


class TextSecurityCheckHandler(tornado.web.RequestHandler):
    """文本内容安全检测 API"""

    def check_xsrf_cookie(self):
        pass

    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    def post(self):
        try:
            data = json.loads(self.request.body)
            content = data.get('content', '')
            openid = data.get('openid', '')
            scene = data.get('scene', 1)

            if not content:
                self.write(json.dumps({'success': False, 'error': '缺少检测内容'}))
                return

            if not openid:
                auth_header = self.request.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    token = auth_header[7:]
                    if '_' in token:
                        try:
                            user_id = int(token.split('_')[-1])
                            from models.user import User
                            session = ContentSecuritySession()
                            try:
                                user = session.query(User).filter(
                                    User.id == user_id).first()
                                if user and user.wechat_openid:
                                    openid = user.wechat_openid
                            finally:
                                session.close()
                        except (ValueError, IndexError):
                            pass

            if not openid:
                self.write(
                    json.dumps({
                        'success': True,
                        'safe': True,
                        'skipped': True,
                        'reason': 'no_openid'
                    }))
                return

            result = check_text_security(content, openid, scene)

            self.write(
                json.dumps({
                    'success': True,
                    'safe': result.get('safe', True),
                    'label': result.get('label', 100),
                    'suggest': result.get('suggest', 'pass'),
                    'skipped': result.get('skipped', False)
                }))

        except Exception as e:
            logging.error(f"文本安全检测异常: {e}")
            self.write(
                json.dumps({
                    'success': True,
                    'safe': True,
                    'skipped': True,
                    'error': str(e)
                }))


class MediaSecurityCheckHandler(tornado.web.RequestHandler):
    """图片内容安全检测 API (腾讯云 IMS 同步检测)"""

    def check_xsrf_cookie(self):
        pass

    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    def post(self):
        try:
            logging.info("[IMS] ===== 收到图片安全检测请求 =====")

            # 方式1: multipart 文件直传 (小程序 wx.uploadFile，跨平台最可靠)
            uploaded = (self.request.files.get('media')
                        or self.request.files.get('image'))
            if uploaded:
                file_content = uploaded[0]['body']
                logging.info(
                    f"[IMS] 使用文件直传方式检测 (大小: {len(file_content)} bytes)")
                file_base64 = base64.b64encode(file_content).decode('utf-8')
                result = check_image_with_tencent_ims(
                    image_base64=file_base64)
                self.write(
                    json.dumps({
                        'success': True,
                        'safe': result.get('safe', True),
                        'suggestion': result.get('suggestion', 'Pass'),
                        'label': result.get('label', ''),
                        'reason': result.get('reason', ''),
                        'skipped': result.get('skipped', False)
                    }))
                return

            # 方式2: JSON body (media_url 或 image_base64，保留兼容旧客户端)
            data = json.loads(self.request.body)
            media_url = data.get('media_url', '')
            media_type = data.get('media_type', 2)
            image_base64 = data.get('image_base64', '')

            if media_type != 2:
                logging.warning(f"[IMS] 暂不支持音频检测 (media_type={media_type})")
                self.write(
                    json.dumps({
                        'success': True,
                        'safe': True,
                        'skipped': True,
                        'reason': 'audio_not_supported'
                    }))
                return

            result = None

            if image_base64:
                logging.info(f"[IMS] 使用 Base64 方式检测 (长度: {len(image_base64)})")
                result = check_image_with_tencent_ims(
                    image_base64=image_base64)
            elif media_url:
                if media_url.startswith('/images/'):
                    local_path = os.path.join(
                        os.path.dirname(os.path.dirname(__file__)), 'static',
                        media_url.lstrip('/'))
                    logging.info(f"[IMS] 本地文件路径: {local_path}")

                    if os.path.exists(local_path):
                        try:
                            with open(local_path, 'rb') as f:
                                file_content = f.read()
                            file_base64 = base64.b64encode(
                                file_content).decode('utf-8')
                            logging.info(
                                f"[IMS] 成功读取本地文件并转 Base64 (长度: {len(file_base64)})"
                            )
                            result = check_image_with_tencent_ims(
                                image_base64=file_base64)
                        except Exception as e:
                            logging.error(f"[IMS] 读取本地文件失败: {e}")
                            result = {
                                'safe': True,
                                'skipped': True,
                                'reason': f'file_read_error: {e}'
                            }
                    else:
                        logging.warning(f"[IMS] 本地文件不存在: {local_path}")
                        result = {
                            'safe': True,
                            'skipped': True,
                            'reason': 'file_not_found'
                        }

                elif media_url.startswith('cloud://'):
                    logging.warning(f"[IMS] cloud:// URL 需要前端传 Base64")
                    result = {
                        'safe': True,
                        'skipped': True,
                        'reason': 'cloud_url_requires_base64'
                    }

                else:
                    logging.info(f"[IMS] 尝试使用 URL 方式检测: {media_url[:100]}")
                    result = check_image_with_tencent_ims(image_url=media_url)

                    if result.get('error') and 'ImageDownloadError' in str(
                            result.get('error', '')):
                        logging.warning(f"[IMS] URL 方式失败，尝试下载后转 Base64")
                        try:
                            resp = requests.get(media_url, timeout=10)
                            if resp.status_code == 200:
                                file_base64 = base64.b64encode(
                                    resp.content).decode('utf-8')
                                result = check_image_with_tencent_ims(
                                    image_base64=file_base64)
                        except Exception as e:
                            logging.error(f"[IMS] 下载图片失败: {e}")
            else:
                result = {
                    'safe': True,
                    'skipped': True,
                    'reason': 'no_media_provided'
                }

            if result is None:
                result = {
                    'safe': True,
                    'skipped': True,
                    'reason': 'unknown_error'
                }

            self.write(
                json.dumps({
                    'success': True,
                    'safe': result.get('safe', True),
                    'suggestion': result.get('suggestion', 'Pass'),
                    'label': result.get('label', ''),
                    'reason': result.get('reason', ''),
                    'skipped': result.get('skipped', False)
                }))

        except Exception as e:
            logging.error(f"媒体安全检测异常: {e}")
            self.write(
                json.dumps({
                    'success': True,
                    'skipped': True,
                    'error': str(e)
                }))


def verify_wechat_signature(signature, timestamp, nonce, token):
    """
    验证微信服务器的签名
    
    微信验签规则:
    1. 将 token, timestamp, nonce 转为字符串
    2. 按 ASCII 字典序排序
    3. 拼接成一个字符串
    4. 进行 sha1 计算，与 signature 对比
    
    参数:
        signature: 微信发来的签名
        timestamp: 时间戳
        nonce: 随机数
        token: 配置的Token
    
    返回:
        True 如果签名有效，False 否则
    """
    try:
        params = [str(token), str(timestamp), str(nonce)]
        params.sort()
        sha1_str = ''.join(params)
        calculated_signature = hashlib.sha1(
            sha1_str.encode('utf-8')).hexdigest()
        logging.debug(
            f"[SIGNATURE] params={params}, sha1_str={sha1_str}, calculated={calculated_signature}, received={signature}"
        )
        return calculated_signature == signature
    except Exception as e:
        logging.error(f"签名验证异常: {e}")
        return False


class MediaSecurityCallbackHandler(tornado.web.RequestHandler):
    """微信媒体安全检测结果回调 (接收微信推送)"""

    def check_xsrf_cookie(self):
        pass

    def set_default_headers(self):
        pass

    def get(self):
        """
        微信 URL 验证请求 (配置消息推送时使用)
        """
        try:
            signature = self.get_argument('signature', '')
            timestamp = self.get_argument('timestamp', '')
            nonce = self.get_argument('nonce', '')
            echostr = self.get_argument('echostr', '')

            logging.info(
                f"[CALLBACK-GET] 收到微信验证请求: signature={signature}, timestamp={timestamp}, nonce={nonce}, echostr={echostr}"
            )

            if not all([signature, timestamp, nonce, echostr]):
                logging.warning(f"[CALLBACK-GET] 缺少参数")
                self.write("missing parameters")
                return

            if not WECHAT_CALLBACK_TOKEN:
                logging.error(f"[CALLBACK-GET] 未配置 WECHAT_CALLBACK_TOKEN")
                self.write("token not configured")
                return

            if verify_wechat_signature(signature, timestamp, nonce, WECHAT_CALLBACK_TOKEN):
                logging.info(f"[CALLBACK-GET] 验证通过，返回: {echostr}")
                self.set_header("Content-Type", "text/plain")
                self.write(echostr)
            else:
                logging.warning(f"[CALLBACK-GET] 验证失败")
                self.write("fail")
        except Exception as e:
            logging.error(f"[CALLBACK-GET] 异常: {e}")
            self.write("error")

    def post(self):
        """接收微信服务器的异步检测结果推送 (XML 格式)"""
        try:
            # 记录原始请求体以便调试
            body_bytes = self.request.body
            logging.info(f"[CALLBACK] 收到 POST 请求，长度: {len(body_bytes)}")

            # 微信推送可能是 XML 或 JSON
            data = {}
            if body_bytes.startswith(b'<'):
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(body_bytes)
                    data = {child.tag: child.text for child in root}
                    logging.info(f"[CALLBACK] XML 解析成功")
                except Exception as e:
                    logging.error(f"[CALLBACK] XML 解析失败: {e}")
            else:
                try:
                    data = json.loads(body_bytes)
                    logging.info(f"[CALLBACK] JSON 解析成功")
                except Exception as e:
                    logging.error(f"[CALLBACK] JSON 解析失败: {e}")

            # 微信验证过程有时会发送 POST echostr
            if 'echostr' in data:
                logging.info(f"[CALLBACK-POST] 收到验证 echostr")
                self.write(data['echostr'])
                return

            # 微信标签可能是 trace_id (小写) 或 TraceId (大写)
            trace_id = data.get('trace_id') or data.get('TraceId')
            
            # 如果是内容安全通知，可能嵌套在 detail 中
            if not trace_id and 'detail' in data:
                # 这种情况下 data 已经是平铺的了，但在之前的 XML 解析中可能没有深层解析
                pass 

            if not trace_id:
                # 再次尝试从原始 XML 深层查找 (针对内容安全通知)
                if body_bytes.startswith(b'<'):
                    import xml.etree.ElementTree as ET
                    try:
                        root = ET.fromstring(body_bytes)
                        trace_id_elem = root.find('.//trace_id')
                        if trace_id_elem is None:
                            trace_id_elem = root.find('.//TraceId')
                        if trace_id_elem is not None:
                            trace_id = trace_id_elem.text
                    except:
                        pass

            if not trace_id:
                logging.info(f"[CALLBACK] 未找到 trace_id，可能是验证请求或非业务通知，返回 success")
                self.write("success")
                return

            logging.info(f"[CALLBACK] 开始处理 trace_id={trace_id}")
            # ... 后续逻辑保持不变 ...

            from models.image_verification import ImageVerification
            from models.user import User
            from utils.wechat_cloud_storage import delete_cloud_files
            from datetime import datetime

            session = ContentSecuritySession()
            try:
                verification = session.query(ImageVerification).filter(
                    ImageVerification.trace_id == trace_id).first()

                if not verification:
                    logging.warning(
                        f"[CALLBACK] 未找到 trace_id={trace_id} 的验证记录")
                    self.write(
                        json.dumps({
                            'success': True,
                            'message': 'record not found'
                        }))
                    return

                if errcode == 0:
                    is_safe = suggest == 'pass'
                    new_status = 'approved' if is_safe else 'rejected'

                    verification.status = new_status
                    verification.wechat_suggest = suggest
                    verification.reason_label = label
                    verification.reviewed_at = datetime.utcnow()

                    logging.info(
                        f"[CALLBACK] 更新验证记录 id={verification.id}: status={new_status}"
                    )

                    if verification.biz_type == 'avatar':
                        user = session.query(User).filter(
                            User.id == verification.owner_user_id).first()

                        if user:
                            user.avatar_security_status = new_status
                            if not is_safe:
                                logging.warning(
                                    f"[CALLBACK] 用户 {user.id} 头像违规，重置为默认")
                                try:
                                    old_avatar = user.wechat_avatar
                                    if old_avatar:
                                        if old_avatar.startswith('cloud://'):
                                            delete_cloud_files([old_avatar])
                                            logging.info(
                                                f"[CALLBACK] 已删除云端违规头像: {old_avatar}"
                                            )
                                        elif old_avatar.startswith(
                                                '/images/avatars/'):
                                            avatar_path = os.path.join(
                                                os.path.dirname(
                                                    os.path.dirname(__file__)),
                                                'mystatics',
                                                old_avatar.lstrip('/'))
                                            if os.path.exists(avatar_path):
                                                os.remove(avatar_path)
                                                logging.info(
                                                    f"[CALLBACK] 已删除本地违规头像: {avatar_path}"
                                                )
                                except Exception as del_err:
                                    logging.error(
                                        f"[CALLBACK] 删除头像文件失败: {del_err}")

                                user.wechat_avatar = None
                            logging.info(
                                f"[CALLBACK] 用户 {user.id} 头像状态更新为: {new_status}"
                            )

                    session.commit()
                else:
                    logging.error(
                        f"[CALLBACK] 媒体检测失败 trace_id={trace_id}: errcode={errcode}"
                    )

            finally:
                session.close()

            self.write(json.dumps({'success': True}))

        except Exception as e:
            logging.error(f"[CALLBACK] 处理媒体安全检测回调异常: {e}")
            import traceback
            traceback.print_exc()
            self.write(json.dumps({'success': False, 'error': str(e)}))


class VerificationStatusHandler(tornado.web.RequestHandler):
    """查询图片验证记录的状态"""

    def check_xsrf_cookie(self):
        pass

    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    def post(self):
        try:
            from models.image_verification import ImageVerification

            data = json.loads(self.request.body)
            trace_id = data.get('trace_id', '')

            if not trace_id:
                self.write(
                    json.dumps({
                        'success': False,
                        'error': '缺少trace_id'
                    }))
                return

            session = ContentSecuritySession()
            try:
                verification = session.query(ImageVerification).filter(
                    ImageVerification.trace_id == trace_id).first()

                if not verification:
                    self.write(
                        json.dumps({
                            'success': False,
                            'error': f'未找到trace_id={trace_id}的验证记录'
                        }))
                    return

                self.write(
                    json.dumps({
                        'success':
                        True,
                        'status':
                        verification.status,
                        'suggest':
                        verification.wechat_suggest,
                        'label':
                        verification.reason_label,
                        'reviewed_at':
                        verification.reviewed_at.isoformat()
                        if verification.reviewed_at else None
                    }))
            finally:
                session.close()
        except Exception as e:
            logging.error(f"查询验证状态异常: {e}")
            self.write(json.dumps({'success': False, 'error': str(e)}))


TEST_CALLBACK_SECRET = os.environ.get('TEST_CALLBACK_SECRET', '')


class MediaSecurityTestCallbackHandler(tornado.web.RequestHandler):
    """开发环境测试：手动模拟微信回调 (需要密钥验证)"""

    def check_xsrf_cookie(self):
        pass

    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    def post(self):
        """模拟微信回调，用于开发环境测试 - 需要 TEST_CALLBACK_SECRET 环境变量"""
        try:
            if not TEST_CALLBACK_SECRET:
                self.set_status(403)
                self.write(
                    json.dumps({
                        'success':
                        False,
                        'error':
                        'Test callback disabled - TEST_CALLBACK_SECRET not configured'
                    }))
                return

            data = json.loads(self.request.body)

            provided_secret = data.get('secret', '')
            if provided_secret != TEST_CALLBACK_SECRET:
                self.set_status(403)
                self.write(
                    json.dumps({
                        'success': False,
                        'error': 'Invalid secret'
                    }))
                return

            trace_id = data.get('trace_id')
            suggest = data.get('suggest', 'risky')
            label = data.get('label', 20001)

            if not trace_id:
                self.write(
                    json.dumps({
                        'success': False,
                        'error': 'missing trace_id'
                    }))
                return

            mock_callback = {
                'errcode': 0,
                'errmsg': 'ok',
                'trace_id': trace_id,
                'result': {
                    'suggest': suggest,
                    'label': label
                }
            }

            logging.warning(f"[TEST] 模拟微信回调: {mock_callback}")

            from models.image_verification import ImageVerification
            from models.user import User
            from utils.wechat_cloud_storage import delete_cloud_files
            from datetime import datetime

            session = ContentSecuritySession()
            try:
                verification = session.query(ImageVerification).filter(
                    ImageVerification.trace_id == trace_id).first()

                if not verification:
                    self.write(
                        json.dumps({
                            'success': False,
                            'error': f'未找到 trace_id={trace_id} 的验证记录'
                        }))
                    return

                is_safe = suggest == 'pass'
                new_status = 'approved' if is_safe else 'rejected'

                verification.status = new_status
                verification.wechat_suggest = suggest
                verification.reason_label = label
                verification.reviewed_at = datetime.utcnow()

                if verification.biz_type == 'avatar':
                    user = session.query(User).filter(
                        User.id == verification.owner_user_id).first()

                    if user:
                        user.avatar_security_status = new_status
                        if not is_safe:
                            old_avatar = user.wechat_avatar
                            if old_avatar:
                                if old_avatar.startswith('cloud://'):
                                    delete_cloud_files([old_avatar])
                                elif old_avatar.startswith('/images/avatars/'):
                                    avatar_path = os.path.join(
                                        os.path.dirname(
                                            os.path.dirname(__file__)),
                                        'mystatics', old_avatar.lstrip('/'))
                                    if os.path.exists(avatar_path):
                                        os.remove(avatar_path)
                            user.wechat_avatar = None
                            logging.warning(f"[TEST] 用户 {user.id} 头像违规已重置")

                session.commit()

                self.write(
                    json.dumps({
                        'success': True,
                        'message': f'验证记录已更新为 {new_status}',
                        'verification_id': verification.id,
                        'user_id': verification.owner_user_id
                    }))

            finally:
                session.close()

        except Exception as e:
            logging.error(f"[TEST] 模拟回调异常: {e}")
            self.write(json.dumps({'success': False, 'error': str(e)}))
