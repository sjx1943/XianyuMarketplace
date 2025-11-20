#coding=utf-8

"""
微信OAuth登录控制器
支持微信扫码登录和微信浏览器内授权登录
"""

import tornado.web
import requests
import json
import os
import hashlib
import logging
from urllib.parse import urlencode
from sqlalchemy.orm import sessionmaker
from models.user import User
from base.base import engine

Session = sessionmaker(bind=engine)

# 微信OAuth配置（从环境变量获取）
WECHAT_APP_ID = os.environ.get('WECHAT_APP_ID', '')
WECHAT_APP_SECRET = os.environ.get('WECHAT_APP_SECRET', '')
WECHAT_REDIRECT_URI = os.environ.get('WECHAT_REDIRECT_URI', '')

# 微信OAuth API端点
WECHAT_AUTHORIZE_URL = 'https://open.weixin.qq.com/connect/oauth2/authorize'
WECHAT_QRCONNECT_URL = 'https://open.weixin.qq.com/connect/qrconnect'
WECHAT_ACCESS_TOKEN_URL = 'https://api.weixin.qq.com/sns/oauth2/access_token'
WECHAT_USER_INFO_URL = 'https://api.weixin.qq.com/sns/userinfo'


class WeChatLoginHandler(tornado.web.RequestHandler):
    """微信登录入口页面"""
    
    def get(self):
        """显示微信登录页面"""
        # 检查是否配置了微信OAuth
        if not WECHAT_APP_ID or not WECHAT_APP_SECRET:
            self.render("wechat_login_config.html", 
                       error="微信OAuth未配置，请设置环境变量：WECHAT_APP_ID, WECHAT_APP_SECRET, WECHAT_REDIRECT_URI")
            return
        
        # 生成state参数（防CSRF攻击）
        state = hashlib.md5(f"{tornado.escape.native_str(self.request.remote_ip)}{os.urandom(16).hex()}".encode()).hexdigest()
        self.set_secure_cookie("wechat_state", state, expires_days=0.01)  # 15分钟过期
        
        # 判断是否在微信浏览器内
        user_agent = self.request.headers.get("User-Agent", "")
        is_wechat_browser = "MicroMessenger" in user_agent
        
        if is_wechat_browser:
            # 微信浏览器内：直接重定向授权
            auth_url = self._build_wechat_auth_url(state, scope='snsapi_userinfo')
            self.redirect(auth_url)
        else:
            # PC/其他浏览器：显示二维码扫描登录页面
            qr_url = self._build_qr_connect_url(state)
            self.render("wechat_qr_login.html", qr_url=qr_url)
    
    def _build_wechat_auth_url(self, state, scope='snsapi_base'):
        """构建微信授权URL（微信浏览器内）"""
        params = {
            'appid': WECHAT_APP_ID,
            'redirect_uri': WECHAT_REDIRECT_URI,
            'response_type': 'code',
            'scope': scope,  # snsapi_base或snsapi_userinfo
            'state': state
        }
        return f"{WECHAT_AUTHORIZE_URL}?{urlencode(params)}#wechat_redirect"
    
    def _build_qr_connect_url(self, state):
        """构建微信扫码登录URL（PC端）"""
        params = {
            'appid': WECHAT_APP_ID,
            'redirect_uri': WECHAT_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'snsapi_login',  # PC扫码登录固定使用snsapi_login
            'state': state
        }
        return f"{WECHAT_QRCONNECT_URL}?{urlencode(params)}#wechat_redirect"


class WeChatCallbackHandler(tornado.web.RequestHandler):
    """微信OAuth回调处理器"""
    
    def initialize(self):
        self.session = Session()
    
    def get(self):
        """处理微信OAuth回调"""
        try:
            code = self.get_argument("code", None)
            state = self.get_argument("state", None)
            
            # 验证state参数（防CSRF）
            saved_state = self.get_secure_cookie("wechat_state")
            if not saved_state:
                logging.error("微信OAuth回调：未找到state cookie")
                self.render("wechat_login_error.html", error="安全验证失败，会话已过期，请重新登录")
                return
            
            # 安全解码cookie
            try:
                saved_state_str = saved_state.decode('utf-8')
            except (AttributeError, UnicodeDecodeError) as e:
                logging.error(f"微信OAuth回调：state cookie解码失败: {e}")
                self.render("wechat_login_error.html", error="安全验证失败，请重新登录")
                return
            
            if saved_state_str != state:
                logging.error(f"微信OAuth回调：state不匹配 saved={saved_state_str}, received={state}")
                self.render("wechat_login_error.html", error="安全验证失败，请重新登录")
                return
            
            # 清理已使用的state cookie
            self.clear_cookie("wechat_state")
            
            if not code:
                self.render("wechat_login_error.html", error="授权失败，未获取到授权码")
                return
            
            # 交换access_token
            token_data = self._get_access_token(code)
            if not token_data or 'access_token' not in token_data:
                logging.error(f"获取access_token失败: {token_data}")
                self.render("wechat_login_error.html", error="获取访问令牌失败")
                return
            
            access_token = token_data['access_token']
            openid = token_data['openid']
            
            # 获取用户信息
            user_info = self._get_user_info(access_token, openid)
            if not user_info or 'openid' not in user_info:
                logging.error(f"获取用户信息失败: {user_info}")
                self.render("wechat_login_error.html", error="获取用户信息失败")
                return
            
            # 查找或创建用户
            user = self._find_or_create_user(user_info)
            if not user:
                self.render("wechat_login_error.html", error="创建用户失败")
                return
            
            # 设置登录cookie
            self.set_secure_cookie("user_id", str(user.id))
            self.set_secure_cookie("username", user.username)
            
            # 检查是否需要设置房间号
            if not user.username or user.username.startswith('wx_'):
                # 微信用户首次登录，需要设置房间号
                self.redirect("/set_room_number?source=wechat")
            else:
                # 已有房间号，直接跳转主页
                self.redirect("/main?message=微信登录成功")
            
        except Exception as e:
            logging.error(f"微信OAuth回调处理异常: {e}")
            self.render("wechat_login_error.html", error=f"登录处理失败: {str(e)}")
    
    def _get_access_token(self, code):
        """通过code获取access_token"""
        try:
            params = {
                'appid': WECHAT_APP_ID,
                'secret': WECHAT_APP_SECRET,
                'code': code,
                'grant_type': 'authorization_code'
            }
            
            response = requests.get(WECHAT_ACCESS_TOKEN_URL, params=params, timeout=10)
            response.raise_for_status()  # 检查HTTP错误
            data = response.json()
            
            if 'errcode' in data and data['errcode'] != 0:
                logging.error(f"微信access_token API错误: errcode={data.get('errcode')}, errmsg={data.get('errmsg')}")
                return None
            
            return data
        except requests.exceptions.Timeout as e:
            logging.error(f"请求access_token超时: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"请求access_token网络异常: {e}")
            return None
        except (ValueError, KeyError) as e:
            logging.error(f"解析access_token响应失败: {e}")
            return None
        except Exception as e:
            logging.error(f"请求access_token未知异常: {e}")
            return None
    
    def _get_user_info(self, access_token, openid):
        """获取微信用户信息"""
        try:
            params = {
                'access_token': access_token,
                'openid': openid,
                'lang': 'zh_CN'
            }
            
            response = requests.get(WECHAT_USER_INFO_URL, params=params, timeout=10)
            response.raise_for_status()  # 检查HTTP错误
            data = response.json()
            
            if 'errcode' in data and data['errcode'] != 0:
                logging.error(f"微信用户信息API错误: errcode={data.get('errcode')}, errmsg={data.get('errmsg')}")
                return None
            
            return data
        except requests.exceptions.Timeout as e:
            logging.error(f"请求用户信息超时: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"请求用户信息网络异常: {e}")
            return None
        except (ValueError, KeyError) as e:
            logging.error(f"解析用户信息响应失败: {e}")
            return None
        except Exception as e:
            logging.error(f"请求用户信息未知异常: {e}")
            return None
    
    def _find_or_create_user(self, wechat_user_info):
        """查找或创建用户"""
        try:
            openid = wechat_user_info['openid']
            nickname = wechat_user_info.get('nickname', f'wx_user_{openid[:8]}')
            headimgurl = wechat_user_info.get('headimgurl', '')
            
            # 查找是否已存在该微信用户
            user = self.session.query(User).filter_by(wechat_openid=openid).first()
            
            if user:
                # 用户已存在，更新微信信息
                user.wechat_nickname = nickname
                user.wechat_avatar = headimgurl
                self.session.commit()
                return user
            
            # 创建新用户
            # 生成临时用户名（后续需要用户设置房间号）
            temp_username = f"wx_{openid[:12]}"
            
            # 检查用户名是否已存在
            existing_user = self.session.query(User).filter_by(username=temp_username).first()
            if existing_user:
                # 添加随机后缀
                import random
                temp_username = f"wx_{openid[:8]}_{random.randint(1000, 9999)}"
            
            new_user = User(
                username=temp_username,
                password=hashlib.md5(f"{openid}{os.urandom(16).hex()}".encode()).hexdigest(),  # 随机密码
                email=f"{openid}@wechat.oauth",  # 占位邮箱
                wechat_openid=openid,
                wechat_nickname=nickname,
                wechat_avatar=headimgurl
            )
            
            self.session.add(new_user)
            self.session.commit()
            
            logging.info(f"创建微信用户成功: {temp_username}")
            return new_user
            
        except Exception as e:
            self.session.rollback()
            logging.error(f"创建微信用户失败: {e}")
            return None
    
    def on_finish(self):
        self.session.close()


class WeChatUnbindHandler(tornado.web.RequestHandler):
    """微信解绑处理器"""
    
    def initialize(self):
        self.session = Session()
    
    def post(self):
        """解绑微信账号"""
        try:
            user_id = self.get_secure_cookie("user_id")
            if not user_id:
                self.write(json.dumps({'success': False, 'error': '请先登录'}))
                return
            
            user = self.session.query(User).filter_by(id=int(user_id)).first()
            if not user:
                self.write(json.dumps({'success': False, 'error': '用户不存在'}))
                return
            
            # 检查是否绑定了微信
            if not user.wechat_openid:
                self.write(json.dumps({'success': False, 'error': '未绑定微信账号'}))
                return
            
            # 解绑微信
            user.wechat_openid = None
            user.wechat_nickname = None
            user.wechat_avatar = None
            self.session.commit()
            
            self.write(json.dumps({'success': True, 'message': '微信账号已解绑'}))
            
        except Exception as e:
            self.session.rollback()
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def on_finish(self):
        self.session.close()
