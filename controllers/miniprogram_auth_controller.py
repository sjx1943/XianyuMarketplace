#coding=utf-8

"""
微信小程序登录控制器
处理小程序wx.login()的code换取session_key和openid
"""

import tornado.web
import requests
import json
import os
import bcrypt
import logging
from sqlalchemy.orm import sessionmaker
from models.user import User
from base.base import engine

Session = sessionmaker(bind=engine)

# 微信小程序配置（从环境变量获取）
WX_MINIPROGRAM_APP_ID = os.environ.get('WX_MINIPROGRAM_APP_ID', '')
WX_MINIPROGRAM_APP_SECRET = os.environ.get('WX_MINIPROGRAM_APP_SECRET', '')

# 微信小程序登录API
WX_LOGIN_URL = 'https://api.weixin.qq.com/sns/jscode2session'


class MiniprogramLoginHandler(tornado.web.RequestHandler):
    """小程序微信登录处理器"""
    
    def check_xsrf_cookie(self):
        """禁用XSRF检查（小程序无法携带XSRF token）"""
        pass
    
    def initialize(self):
        self.session = Session()
    
    def post(self):
        """处理小程序登录请求"""
        try:
            # 获取前端传来的code
            data = json.loads(self.request.body)
            code = data.get('code')
            
            if not code:
                self.write(json.dumps({
                    'success': False,
                    'error': '缺少code参数'
                }))
                return
            
            # 检查小程序配置
            if not WX_MINIPROGRAM_APP_ID or not WX_MINIPROGRAM_APP_SECRET:
                logging.error("小程序AppID或AppSecret未配置")
                self.write(json.dumps({
                    'success': False,
                    'error': '小程序配置错误，请联系管理员'
                }))
                return
            
            # 向微信服务器换取session_key和openid
            wx_response = self._get_wx_session(code)
            
            if not wx_response or 'openid' not in wx_response:
                logging.error(f"微信登录失败: {wx_response}")
                self.write(json.dumps({
                    'success': False,
                    'error': '微信登录失败，请重试'
                }))
                return
            
            openid = wx_response['openid']
            session_key = wx_response.get('session_key', '')
            
            # 查找或创建用户
            user = self._find_or_create_user(openid)
            
            if not user:
                self.write(json.dumps({
                    'success': False,
                    'error': '创建用户失败'
                }))
                return
            
            # 设置登录Cookie
            self.set_secure_cookie("user_id", str(user.id))
            self.set_secure_cookie("username", user.username or "")
            
            # 生成简单token（用户ID加密）用于小程序Authorization验证
            import hashlib
            import time
            token_base = f"{user.id}:{openid}:{int(time.time())}"
            token = hashlib.sha256(token_base.encode()).hexdigest()[:32] + f"_{user.id}"
            
            # 返回用户信息
            self.write(json.dumps({
                'success': True,
                'token': token,  # 返回token供小程序存储
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'room_number': user.room_number,
                    'wechat_openid': user.wechat_openid,
                    'wechat_nickname': user.wechat_nickname,
                    'wechat_avatar': user.wechat_avatar
                },
                'session_key': session_key
            }))
            
        except Exception as e:
            logging.error(f"小程序登录异常: {e}")
            self.write(json.dumps({
                'success': False,
                'error': f'登录处理失败: {str(e)}'
            }))
    
    def _get_wx_session(self, code):
        """通过code获取session_key和openid"""
        try:
            params = {
                'appid': WX_MINIPROGRAM_APP_ID,
                'secret': WX_MINIPROGRAM_APP_SECRET,
                'js_code': code,
                'grant_type': 'authorization_code'
            }
            
            response = requests.get(WX_LOGIN_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'errcode' in data and data['errcode'] != 0:
                logging.error(f"微信登录API错误: errcode={data.get('errcode')}, errmsg={data.get('errmsg')}")
                return None
            
            return data
            
        except requests.exceptions.Timeout as e:
            logging.error(f"请求微信登录API超时: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"请求微信登录API网络异常: {e}")
            return None
        except (ValueError, KeyError) as e:
            logging.error(f"解析微信登录API响应失败: {e}")
            return None
        except Exception as e:
            logging.error(f"获取微信session未知异常: {e}")
            return None
    
    def _find_or_create_user(self, openid):
        """查找或创建用户"""
        try:
            # 查找是否已存在该微信用户
            user = self.session.query(User).filter_by(wechat_openid=openid).first()
            
            if user:
                logging.info(f"用户已存在: {user.username}")
                return user
            
            # 创建新用户
            # 生成临时用户名（用户需要后续设置房间号）
            temp_username = f"mp_{openid[:12]}"
            
            # 检查用户名是否已存在
            existing_user = self.session.query(User).filter_by(username=temp_username).first()
            if existing_user:
                # 添加随机后缀
                import random
                temp_username = f"mp_{openid[:8]}_{random.randint(1000, 9999)}"
            
            # 生成安全的随机密码（bcrypt，与标准注册流程保持一致）
            random_password = f"{openid}{os.urandom(16).hex()}"
            password_bytes = random_password.encode('utf-8')
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
            
            new_user = User(
                username=temp_username,
                password=hashed_password,  # bcrypt加密的随机密码（与auth_controller一致）
                email=f"{openid}@miniprogram.wx",  # 占位邮箱
                wechat_openid=openid
            )
            
            self.session.add(new_user)
            self.session.commit()
            
            logging.info(f"创建小程序用户成功: {temp_username}")
            return new_user
            
        except Exception as e:
            self.session.rollback()
            logging.error(f"创建小程序用户失败: {e}")
            return None
    
    def on_finish(self):
        self.session.close()


class MiniprogramUserInfoHandler(tornado.web.RequestHandler):
    """小程序获取用户信息接口"""
    
    def check_xsrf_cookie(self):
        """禁用XSRF检查（小程序无法携带XSRF token）"""
        pass
    
    def initialize(self):
        self.session = Session()
    
    def _get_user_id(self):
        """从Cookie或Authorization头获取用户ID"""
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return user_id.decode('utf-8') if isinstance(user_id, bytes) else user_id
        
        auth_header = self.request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if '_' in token:
                try:
                    user_id = token.split('_')[-1]
                    return user_id
                except:
                    pass
        return None
    
    def get(self):
        """获取当前登录用户信息"""
        try:
            user_id = self._get_user_id()
            
            if not user_id:
                self.write(json.dumps({
                    'success': False,
                    'error': '未登录'
                }))
                return
            
            user = self.session.query(User).filter_by(id=int(user_id)).first()
            
            if not user:
                self.write(json.dumps({
                    'success': False,
                    'error': '用户不存在'
                }))
                return
            
            self.write(json.dumps({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'room_number': user.room_number,
                    'phone': user.phone,
                    'email': user.email,
                    'wechat_openid': user.wechat_openid,
                    'wechat_nickname': user.wechat_nickname,
                    'wechat_avatar': user.wechat_avatar,
                    'is_admin': user.is_admin
                }
            }))
            
        except Exception as e:
            logging.error(f"获取用户信息异常: {e}")
            self.write(json.dumps({
                'success': False,
                'error': str(e)
            }))
    
    def on_finish(self):
        self.session.close()


class MiniprogramSetRoomNumberHandler(tornado.web.RequestHandler):
    """小程序设置房间号接口"""
    
    def check_xsrf_cookie(self):
        """禁用XSRF检查（小程序无法携带XSRF token）"""
        pass
    
    def initialize(self):
        self.session = Session()
    
    def _get_user_id(self):
        """从Cookie或Authorization头获取用户ID"""
        # 优先从Cookie获取
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return user_id.decode('utf-8') if isinstance(user_id, bytes) else user_id
        
        # 从Authorization头获取（格式：Bearer token_userId）
        auth_header = self.request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # 去掉 'Bearer ' 前缀
            # token格式：hash_userId
            if '_' in token:
                try:
                    user_id = token.split('_')[-1]
                    return user_id
                except:
                    pass
        return None
    
    def post(self):
        """设置用户房间号"""
        import re
        try:
            user_id = self._get_user_id()
            
            if not user_id:
                self.set_status(401)
                self.write(json.dumps({
                    'success': False,
                    'error': '未登录'
                }))
                return
            
            data = json.loads(self.request.body)
            room_number = data.get('room_number', '').strip()
            
            if not room_number:
                self.write(json.dumps({
                    'success': False,
                    'error': '房间号不能为空'
                }))
                return
            
            # 验证房间号格式：楼号-单元号-房间号（如'3-1-801'）
            pattern = r'^\d{1,3}-\d{1,2}-\d{1,4}$'
            if not re.match(pattern, room_number):
                self.write(json.dumps({
                    'success': False,
                    'error': '房间号格式不正确，请按照"楼号-单元号-房间号"格式输入，例如：3-1-801'
                }))
                return
            
            # 检查房间号是否已被使用
            existing_room = self.session.query(User).filter_by(room_number=room_number).first()
            if existing_room and existing_room.id != int(user_id):
                self.write(json.dumps({
                    'success': False,
                    'error': '该房间号已被占用，如有疑问请联系管理员'
                }))
                return
            
            # 更新用户房间号
            user = self.session.query(User).filter_by(id=int(user_id)).first()
            if user:
                user.room_number = room_number
                self.session.commit()
                
                # 更新cookie
                self.set_secure_cookie("username", room_number, expires_days=7)
                
                self.write(json.dumps({
                    'success': True,
                    'message': '房间号设置成功',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'room_number': user.room_number
                    }
                }))
            else:
                self.write(json.dumps({
                    'success': False,
                    'error': '用户不存在'
                }))
                
        except Exception as e:
            self.session.rollback()
            logging.error(f"设置房间号异常: {e}")
            self.write(json.dumps({
                'success': False,
                'error': str(e)
            }))
    
    def on_finish(self):
        self.session.close()


class MiniprogramUpdateProfileHandler(tornado.web.RequestHandler):
    """小程序更新用户资料接口"""
    
    def check_xsrf_cookie(self):
        """禁用XSRF检查（小程序无法携带XSRF token）"""
        pass
    
    def initialize(self):
        self.session = Session()
    
    def _get_user_id(self):
        """从Cookie或Authorization头获取用户ID"""
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return user_id.decode('utf-8') if isinstance(user_id, bytes) else user_id
        
        auth_header = self.request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if '_' in token:
                try:
                    user_id = token.split('_')[-1]
                    return user_id
                except:
                    pass
        return None
    
    def post(self):
        """更新用户资料（昵称、头像等）"""
        try:
            user_id = self._get_user_id()
            
            if not user_id:
                self.set_status(401)
                self.write(json.dumps({
                    'success': False,
                    'error': '未登录'
                }))
                return
            
            data = json.loads(self.request.body)
            nickname = data.get('nickname', '')
            avatar = data.get('avatar', '')
            
            user = self.session.query(User).filter_by(id=int(user_id)).first()
            if user:
                if nickname:
                    user.wechat_nickname = nickname
                if avatar:
                    user.wechat_avatar = avatar
                
                self.session.commit()
                
                self.write(json.dumps({
                    'success': True,
                    'message': '资料更新成功',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'room_number': user.room_number,
                        'wechat_nickname': user.wechat_nickname,
                        'wechat_avatar': user.wechat_avatar
                    }
                }))
            else:
                self.write(json.dumps({
                    'success': False,
                    'error': '用户不存在'
                }))
                
        except Exception as e:
            self.session.rollback()
            logging.error(f"更新用户资料异常: {e}")
            self.write(json.dumps({
                'success': False,
                'error': str(e)
            }))
    
    def on_finish(self):
        self.session.close()


class MiniprogramUnreadCountHandler(tornado.web.RequestHandler):
    """小程序获取未读消息数量接口"""
    
    def check_xsrf_cookie(self):
        pass
    
    def initialize(self):
        self.session = Session()
    
    def _get_user_id(self):
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return user_id.decode('utf-8') if isinstance(user_id, bytes) else user_id
        
        auth_header = self.request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if '_' in token:
                try:
                    return token.split('_')[-1]
                except:
                    pass
        return None
    
    def get(self):
        """获取未读消息和订单数量"""
        try:
            user_id = self._get_user_id()
            
            if not user_id:
                self.write(json.dumps({'count': 0, 'unread_count': 0}))
                return
            
            from models.order import Order
            
            pending_orders = self.session.query(Order).filter_by(
                seller_id=int(user_id),
                status='pending'
            ).count()
            
            self.write(json.dumps({
                'success': True,
                'count': pending_orders,
                'unread_count': pending_orders
            }))
            
        except Exception as e:
            logging.error(f"获取未读数量异常: {e}")
            self.write(json.dumps({'count': 0, 'unread_count': 0}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramProductUploadHandler(tornado.web.RequestHandler):
    """小程序商品发布接口"""
    
    def check_xsrf_cookie(self):
        pass
    
    def initialize(self, app_settings=None):
        self.app_settings = app_settings or {}
        self.session = Session()
    
    def _get_user_id(self):
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return user_id.decode('utf-8') if isinstance(user_id, bytes) else user_id
        
        auth_header = self.request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if '_' in token:
                try:
                    return token.split('_')[-1]
                except:
                    pass
        return None
    
    def post(self):
        """发布商品（支持图片上传）"""
        import os
        from models.product import Product, ProductImage
        
        user_id = self._get_user_id()
        
        if not user_id:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        try:
            name = self.get_argument("name", "")
            description = self.get_argument("description", "")
            price = float(self.get_argument("price", 0))
            quantity = int(self.get_argument("quantity", 1))
            tag = self.get_argument("tag", "其他")
            condition = self.get_argument("condition", "九成新")
            images = self.request.files.get("images", [])
            
            if not name:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '商品名称不能为空'}))
                return
            
            if not images:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '请至少上传一张图片'}))
                return
            
            if len(images) > 9:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '最多只能上传9张图片'}))
                return
            
            if len(description) > 5000:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '商品描述过长，最多5000字符'}))
                return
            
            new_product = Product(
                name=name,
                description=description,
                price=price,
                user_id=int(user_id),
                tag=tag,
                image="",
                quantity=quantity,
                status="在售",
                condition=condition
            )
            self.session.add(new_product)
            self.session.flush()
            
            image_filenames = []
            upload_path = self.app_settings.get("upload_path", "static/images")
            
            for i, image in enumerate(images):
                filename = f"{new_product.id}_{i}_{image['filename']}"
                filepath = os.path.join(upload_path, filename)
                
                os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else upload_path, exist_ok=True)
                
                with open(filepath, "wb") as f:
                    f.write(image["body"])
                
                product_image = ProductImage(filename=filename, product_id=new_product.id)
                self.session.add(product_image)
                image_filenames.append(filename)
            
            if image_filenames:
                new_product.image = image_filenames[0]
            
            self.session.commit()
            
            self.write(json.dumps({
                'success': True,
                'message': '商品发布成功',
                'product_id': new_product.id,
                'product': {
                    'id': new_product.id,
                    'name': new_product.name,
                    'price': float(new_product.price),
                    'image': new_product.image
                }
            }))
            
        except ValueError as e:
            self.session.rollback()
            self.set_status(400)
            self.write(json.dumps({'success': False, 'error': '价格或数量格式不正确'}))
        except Exception as e:
            self.session.rollback()
            logging.error(f"商品发布异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': f'发布失败: {str(e)}'}))
    
    def on_finish(self):
        self.session.close()
