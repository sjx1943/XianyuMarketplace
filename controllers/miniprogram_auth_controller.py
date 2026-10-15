#coding=utf-8

"""
微信小程序登录控制器
处理小程序wx.login()的code换取session_key和openid
"""

import tornado.web
import tornado.gen
import requests
import json
import os
import bcrypt
import logging
import datetime
from sqlalchemy.orm import sessionmaker
from models.user import User
from base.base import engine
from motor import motor_tornado
from tornado.ioloop import IOLoop
from utils.wechat_cloud_storage import convert_cloud_url, convert_image_url, convert_images_batch

Session = sessionmaker(bind=engine)

# MongoDB连接配置
mongodb_uri = os.environ.get('MONGODB_URI')
if mongodb_uri:
    mongo_client = motor_tornado.MotorClient(mongodb_uri)
    try:
        mongo_database = mongo_client.get_default_database()
    except Exception:
        mongo_database = mongo_client['chat_db']
else:
    mongo_host = os.getenv('MONGO_HOST', 'localhost')
    mongo_port = int(os.getenv('MONGO_PORT', '27017'))
    mongo_db = os.getenv('MONGO_DB', 'chat_db')
    mongo_client = motor_tornado.MotorClient(f'mongodb://{mongo_host}:{mongo_port}')
    mongo_database = mongo_client[mongo_db]

# 微信小程序配置（从环境变量获取）
WX_MINIPROGRAM_APP_ID = os.environ.get('WX_MINIPROGRAM_APP_ID', '')
WX_MINIPROGRAM_APP_SECRET = os.environ.get('WX_MINIPROGRAM_APP_SECRET', '')

# 微信小程序登录API
WX_LOGIN_URL = 'https://api.weixin.qq.com/sns/jscode2session'

# 默认头像URL
DEFAULT_AVATAR = '/static/images/default-avatar.png'


def convert_avatar_url(avatar_url):
    """
    转换头像URL：如果是云存储格式(cloud://)，转换为临时HTTPS URL
    
    参数:
        avatar_url: 原始头像URL
    
    返回:
        str: 可访问的头像URL
        - 云托管环境：转换为临时HTTPS URL
        - 非云托管环境：保留原始cloud://格式（小程序可直接加载）
    """
    if not avatar_url:
        return DEFAULT_AVATAR
    
    # 如果是云存储格式，尝试转换
    if isinstance(avatar_url, str) and avatar_url.startswith('cloud://'):
        try:
            from utils.wechat_cloud_storage import get_is_cloud_run, convert_cloud_url
            # 非云托管环境，保留原始cloud://格式
            if not get_is_cloud_run():
                return avatar_url
            converted = convert_cloud_url(avatar_url, DEFAULT_AVATAR)
            return converted if converted else DEFAULT_AVATAR
        except Exception as e:
            logging.warning(f"转换云存储头像URL失败: {e}")
            return avatar_url  # 返回原始URL而不是默认值
    
    return avatar_url


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
                    'wechat_avatar': convert_avatar_url(user.wechat_avatar)
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
                    'wechat_avatar': convert_avatar_url(user.wechat_avatar),
                    'avatar_security_status': getattr(user, 'avatar_security_status', 'approved') or 'approved',
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
            
            # 验证房间号格式：楼号-单元号-房间号（如'3-1-901'）
            pattern = r'^\d{1,3}-\d{1,2}-\d{1,4}$'
            if not re.match(pattern, room_number):
                self.write(json.dumps({
                    'success': False,
                    'error': '房间号格式不正确，请按照"楼号-单元号-房间号"格式输入，例如：3-1-901'
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
        """更新用户资料（用户名、手机号、房间号、昵称、头像等）"""
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
            username = data.get('username', '')
            phone = data.get('phone', '')
            room_number = data.get('room_number', '')
            nickname = data.get('nickname', '')
            avatar = data.get('avatar', '') or data.get('wechat_avatar', '')
            
            user = self.session.query(User).filter_by(id=int(user_id)).first()
            if user:
                if username:
                    user.username = username
                if phone:
                    user.phone = phone
                if room_number:
                    user.room_number = room_number
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
                        'phone': user.phone,
                        'room_number': user.room_number,
                        'wechat_nickname': user.wechat_nickname,
                        'wechat_avatar': convert_avatar_url(user.wechat_avatar)
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
                self.write(json.dumps({
                    'success': True,
                    'message_unread_count': 0,
                    'order_unread_count': 0,
                    'count': 0
                }))
                return
            
            from models.order import Order
            
            # 获取待处理订单数量（卖家的pending订单）
            order_unread_count = self.session.query(Order).filter_by(
                seller_id=int(user_id),
                status='pending'
            ).count()
            
            # 获取未读消息数量（从MongoDB）
            try:
                import asyncio
                from utils.mongo_manager import mongo_db
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def get_message_count():
                    try:
                        collection = mongo_db.chat_messages
                        count = await collection.count_documents({
                            "to_user_id": int(user_id),
                            "status": "unread"
                        })
                        return count
                    except:
                        return 0
                
                message_unread_count = loop.run_until_complete(get_message_count())
                loop.close()
            except:
                message_unread_count = 0
            
            self.write(json.dumps({
                'success': True,
                'message_unread_count': message_unread_count,
                'order_unread_count': order_unread_count,
                'count': order_unread_count  # 保持向后兼容
            }))
            
        except Exception as e:
            logging.error(f"获取未读数量异常: {e}")
            self.write(json.dumps({
                'success': True,
                'message_unread_count': 0,
                'order_unread_count': 0,
                'count': 0
            }))
    
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
    
    def _upload_image_to_storage(self, image_body, orig_filename, upload_path):
        """上传图片到存储（腾讯云托管或本地）
        
        优先使用腾讯云托管对象存储（云环境），开发环境使用本地存储
        
        Returns:
            dict: {
                'filename': str,  # 原图文件名/key或cloud://fileID
                'thumb_filename': str,  # 缩略图文件名/key
                'medium_filename': str,  # 中等图文件名/key
                'is_cloud': bool  # 是否使用腾讯云托管
            }
        """
        import re
        import uuid
        from utils.wechat_cloud_storage import upload_file_to_cloud, get_is_cloud_run
        from utils.image_utils import generate_thumbnail, generate_medium_image
        
        # 优先尝试上传到腾讯云托管（云环境）
        if get_is_cloud_run():
            cloud_result = upload_file_to_cloud(image_body, orig_filename, 'products')
            if cloud_result['success']:
                return {
                    'filename': cloud_result['file_id'],
                    'thumb_filename': '',  # 云环境不需要手动生成缩略图
                    'medium_filename': '',  # 云环境不需要手动生成中等图
                    'is_cloud': True
                }
            else:
                logging.warning(f"腾讯云上传失败，回退到本地存储: {cloud_result.get('message')}")
        
        # 开发环境或云上传失败时，使用本地存储
        normalized_filename = re.sub(r'[^\w\-\.]', '_', orig_filename)
        unique_id = uuid.uuid4().hex[:8]
        filename = f"{unique_id}_{normalized_filename}"
        filepath = os.path.join(upload_path, filename)
        
        with open(filepath, "wb") as f:
            f.write(image_body)
        
        thumb_filename = generate_thumbnail(image_body, filename, upload_path)
        medium_filename = generate_medium_image(image_body, filename, upload_path)
        
        return {
            'filename': filename,
            'thumb_filename': thumb_filename,
            'medium_filename': medium_filename,
            'is_cloud': False
        }
    
    def post(self):
        """发布商品（支持图片上传）
        
        支持两种模式：
        1. 首次上传：包含商品信息和图片，创建新商品
        2. 追加上传：只包含product_id和图片，追加图片到已有商品
        
        """
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
            price_str = self.get_argument("price", "0")
            quantity_str = self.get_argument("quantity", "1")
            tag = self.get_argument("tag", "其他")
            condition = self.get_argument("condition", "九成新")
            product_id = self.get_argument("product_id", "")
            images = self.request.files.get("images", [])
            
            upload_path = self.app_settings.get("upload_path", "static/images")
            os.makedirs(upload_path, exist_ok=True)
            
            if product_id:
                product = self.session.query(Product).filter_by(id=int(product_id)).first()
                if not product:
                    self.set_status(404)
                    self.write(json.dumps({'success': False, 'error': '商品不存在'}))
                    return
                
                if product.user_id != int(user_id):
                    self.set_status(403)
                    self.write(json.dumps({'success': False, 'error': '无权操作该商品'}))
                    return
                
                if images:
                    for i, image in enumerate(images):
                        image_body = image["body"]
                        orig_filename = image['filename']
                        
                        storage_result = self._upload_image_to_storage(image_body, orig_filename, upload_path)
                        
                        product_image = ProductImage(
                            filename=storage_result['filename'], 
                            product_id=product.id, 
                            thumb_filename=storage_result['thumb_filename'], 
                            medium_filename=storage_result['medium_filename']
                        )
                        self.session.add(product_image)
                    
                    self.session.commit()
                
                self.write(json.dumps({
                    'success': True,
                    'message': '图片上传成功',
                    'product_id': product.id
                }))
                return
            
            if not name:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '商品名称不能为空'}))
                return
            
            if not images:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '请至少上传一张图片'}))
                return
            
            price = float(price_str)
            quantity = int(quantity_str)
            
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
            
            for i, image in enumerate(images):
                image_body = image["body"]
                orig_filename = image['filename']
                
                storage_result = self._upload_image_to_storage(image_body, orig_filename, upload_path)
                
                product_image = ProductImage(
                    filename=storage_result['filename'], 
                    product_id=new_product.id, 
                    thumb_filename=storage_result['thumb_filename'], 
                    medium_filename=storage_result['medium_filename']
                )
                self.session.add(product_image)
                image_filenames.append(storage_result['filename'])
            
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


class MiniprogramProductCreateHandler(tornado.web.RequestHandler):
    """小程序商品创建接口（支持云存储 fileID）
    
    用于接收小程序端直接上传到微信云托管的图片 fileID
    """
    
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
    
    def post(self):
        """创建商品（接收云存储 fileID）
        
        请求体 JSON:
        {
            "name": "商品名称",
            "description": "描述",
            "price": "100",
            "quantity": "1",
            "tag": "分类",
            "condition": "九成新",
            "image_urls": ["cloud://xxx/xxx.jpg", ...],  # 云存储 fileID 列表
            "image_temp_urls": ["https://...", ...]  # 临时访问 URL（可选）
        }
        """
        from models.product import Product, ProductImage
        
        user_id = self._get_user_id()
        
        if not user_id:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        try:
            data = json.loads(self.request.body.decode('utf-8'))
            
            name = data.get('name', '').strip()
            description = data.get('description', '')
            price_str = data.get('price', '0')
            quantity_str = data.get('quantity', '1')
            tag = data.get('tag', '其他')
            condition = data.get('condition', '九成新')
            image_urls = data.get('image_urls', [])
            image_temp_urls = data.get('image_temp_urls', [])
            
            if not name:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '商品名称不能为空'}))
                return
            
            if not image_urls:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '请至少上传一张图片'}))
                return
            
            price = float(price_str) if price_str and price_str.strip() else None
            quantity = int(quantity_str) if quantity_str and quantity_str.strip() else 1
            
            if quantity < 1:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '商品数量至少为1'}))
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
                image=image_urls[0] if image_urls else "",
                quantity=quantity,
                status="在售",
                condition=condition
            )
            self.session.add(new_product)
            self.session.flush()
            
            for i, url in enumerate(image_urls):
                product_image = ProductImage(
                    filename=url,
                    product_id=new_product.id,
                    thumb_filename=url,
                    medium_filename=url
                )
                self.session.add(product_image)
            
            self.session.commit()
            
            logging.info(f"商品创建成功（云存储）: id={new_product.id}, images={len(image_urls)}")
            
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
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({'success': False, 'error': '请求格式错误'}))
        except Exception as e:
            self.session.rollback()
            logging.error(f"商品创建异常（云存储）: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': f'创建失败: {str(e)}'}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramProductAddCloudImagesHandler(tornado.web.RequestHandler):
    """小程序为现有商品添加云存储图片接口
    
    用于编辑商品时，接收小程序端直接上传到微信云托管的图片 fileID
    """
    
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
    
    def post(self):
        """为现有商品添加云存储图片
        
        请求体 JSON:
        {
            "product_id": 123,
            "image_urls": ["cloud://xxx/xxx.jpg", ...]  # 云存储 fileID 列表
        }
        """
        from models.product import Product, ProductImage
        
        user_id = self._get_user_id()
        
        if not user_id:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        try:
            data = json.loads(self.request.body.decode('utf-8'))
            
            product_id = data.get('product_id')
            image_urls = data.get('image_urls', [])
            
            if not product_id:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '商品ID不能为空'}))
                return
            
            if not image_urls:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '请至少上传一张图片'}))
                return
            
            product = self.session.query(Product).filter_by(id=int(product_id)).first()
            if not product:
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '商品不存在'}))
                return
            
            if product.user_id != int(user_id):
                self.set_status(403)
                self.write(json.dumps({'success': False, 'error': '无权操作该商品'}))
                return
            
            added_count = 0
            for url in image_urls:
                if url and isinstance(url, str):
                    product_image = ProductImage(
                        filename=url,
                        product_id=product.id,
                        thumb_filename=url,
                        medium_filename=url
                    )
                    self.session.add(product_image)
                    added_count += 1
                    
                    if not product.image:
                        product.image = url
            
            self.session.commit()
            
            logging.info(f"商品图片添加成功（云存储）: product_id={product_id}, added={added_count}")
            
            self.write(json.dumps({
                'success': True,
                'message': f'成功添加 {added_count} 张图片',
                'added_count': added_count
            }))
            
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({'success': False, 'error': '请求格式错误'}))
        except Exception as e:
            self.session.rollback()
            logging.error(f"添加商品图片异常（云存储）: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': f'添加失败: {str(e)}'}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramProductDetailHandler(tornado.web.RequestHandler):
    """小程序商品详情接口"""
    
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
    
    def get(self, product_id):
        """获取商品详情"""
        from models.product import Product, ProductImage
        from models.comment import Comment
        
        try:
            product = self.session.query(Product).filter_by(id=product_id).first()
            
            if not product or product.status == '已删除':
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '商品不存在或已被删除'}))
                return
            
            seller = self.session.query(User).filter_by(id=product.user_id).first()
            images = self.session.query(ProductImage).filter_by(product_id=product_id).all()
            
            comments = self.session.query(Comment).filter_by(product_id=product_id).order_by(Comment.id.desc()).limit(10).all()
            
            # 确保主图不为空：如果为空，使用第一张有效图片
            main_image = product.image
            if not main_image and images:
                main_image = images[0].filename
            
            product_data = {
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'price': float(product.price),
                'quantity': product.quantity,
                'status': product.status,
                'condition': product.condition or '九成新',
                'tag': product.tag,
                'image': main_image or '',
                'images': [{'id': img.id, 'filename': img.medium_filename or img.filename, 'original_filename': img.filename} for img in images],
                'upload_time': product.upload_time.strftime('%Y-%m-%d %H:%M') if product.upload_time else '',
                'seller_id': product.user_id,
                'seller': {
                    'id': seller.id,
                    'username': seller.username,
                    'room_number': seller.room_number or '未设置',
                    'avatar': convert_avatar_url(seller.wechat_avatar)
                } if seller else None,
                'comments': [{
                    'id': c.id,
                    'text': c.text,
                    'rating': c.rating,
                    'created_at': c.created_at.strftime('%Y-%m-%d %H:%M') if hasattr(c, 'created_at') and c.created_at else ''
                } for c in comments]
            }
            
            self.write(json.dumps({'success': True, 'product': product_data}))
            
        except Exception as e:
            logging.error(f"获取商品详情异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramProductDeleteHandler(tornado.web.RequestHandler):
    """小程序商品删除接口"""
    
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
    
    def post(self, product_id):
        """删除商品（软删除）- 并自动删除所有关联图片文件"""
        from models.product import Product, ProductImage
        import os
        
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        
        try:
            product = self.session.query(Product).filter_by(id=product_id).first()
            
            if not product:
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '商品不存在'}))
                return
            
            if product.user_id != user_id:
                self.set_status(403)
                self.write(json.dumps({'success': False, 'error': '无权删除此商品'}))
                return
            
            # 删除所有关联的图片文件（自动清理）
            images = self.session.query(ProductImage).filter_by(product_id=product_id).all()
            upload_path = 'mystatics/images'
            
            # 收集云存储文件ID
            cloud_file_ids = []
            logging.info(f"[Product Delete] 开始删除商品 {product_id}，找到 {len(images)} 个图片")
            
            for image in images:
                try:
                    logging.info(f"[Product Delete] 处理图片: {image.filename}")
                    # 检查是否是云存储文件（cloud://开头）
                    if image.filename and image.filename.startswith('cloud://'):
                        cloud_file_ids.append(image.filename)
                        logging.info(f"[Product Delete] ✓ 云存储文件: {image.filename}")
                    else:
                        # 本地文件：删除文件系统中的文件
                        image_path = os.path.join(upload_path, image.filename)
                        if os.path.exists(image_path):
                            os.remove(image_path)
                            logging.info(f"已删除商品图片文件: {image_path}")
                        
                        # 删除缩略图和中等尺寸图（如果存在）
                        for prefix in ['thumb_', 'medium_']:
                            if image.filename:
                                thumb_path = os.path.join(upload_path, f"{prefix}{image.filename}")
                                if os.path.exists(thumb_path):
                                    os.remove(thumb_path)
                                    logging.info(f"已删除图片文件: {thumb_path}")
                except Exception as e:
                    logging.warning(f"删除商品图片文件失败: {e}")
            
            # 批量删除云存储文件
            logging.info(f"[Product Delete] 收集到 {len(cloud_file_ids)} 个云存储文件")
            if cloud_file_ids:
                try:
                    from utils.wechat_cloud_storage import delete_cloud_files
                    result = delete_cloud_files(cloud_file_ids)
                    if result['success']:
                        logging.info(f"[Product Delete] ✓ 云存储文件删除成功: {result['deleted']}")
                    else:
                        logging.warning(f"[Product Delete] ⚠ 云存储文件删除部分失败: {result['message']}")
                except Exception as e:
                    logging.warning(f"[Product Delete] ⚠ 调用云存储删除API失败: {e}")
            else:
                logging.info("[Product Delete] 无云存储文件需要删除（可能都是本地文件）")
            
            # 从数据库删除图片记录
            self.session.query(ProductImage).filter_by(product_id=product_id).delete()
            
            product.status = '已删除'
            self.session.commit()
            
            self.write(json.dumps({'success': True, 'message': '商品删除成功'}))
            
        except Exception as e:
            self.session.rollback()
            logging.error(f"删除商品异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramOrderConfirmHandler(tornado.web.RequestHandler):
    """小程序订单确认收货接口"""
    
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
    
    def post(self, order_id):
        """确认收货"""
        from models.order import Order
        
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        
        try:
            order = self.session.query(Order).filter_by(id=order_id).first()
            
            if not order:
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '订单不存在'}))
                return
            
            if order.user_id != user_id:
                self.set_status(403)
                self.write(json.dumps({'success': False, 'error': '只有买家可以确认收货'}))
                return
            
            if order.status != 'shipped':
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '订单状态不是已发货，无法确认收货'}))
                return
            
            order.status = 'completed'
            order.completed_at = datetime.datetime.now()
            self.session.commit()
            
            # 发送订单状态通知给卖家
            from utils.wechat_subscribe_service import send_order_status_notification
            self._send_order_status_notification(order, '已完成')
            
            self.write(json.dumps({'success': True, 'message': '确认收货成功'}))
            
        except Exception as e:
            self.session.rollback()
            logging.error(f"确认收货异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def _send_order_status_notification(self, order, status_text):
        """发送订单状态通知给卖家"""
        try:
            from models.product import Product
            from utils.wechat_subscribe_service import send_order_status_notification, get_beijing_time_str
            
            # 获取卖家信息
            seller = None
            if order.seller_id:
                seller = self.session.query(User).filter_by(id=order.seller_id).first()
            if not seller:
                product = self.session.query(Product).filter_by(id=order.product_id).first()
                if product:
                    seller = self.session.query(User).filter_by(id=product.user_id).first()
            
            if not seller or not seller.wechat_openid:
                logging.info(f"卖家未设置openid，跳过通知: order_id={order.id}")
                return
            
            # 获取商品名称
            product = self.session.query(Product).filter_by(id=order.product_id).first()
            product_name = product.name if product else '未知商品'
            
            # 发送通知 - 模板字段: character_string2(订单编号), thing7(备注), phrase10(订单状态), thing11(商品名称)
            result = send_order_status_notification(
                openid=seller.wechat_openid,
                order_number=str(order.id),
                product_name=product_name,
                status_text=status_text,
                remark='买家已确认收货',
                page=f'pages/order/detail?id={order.id}'
            )
            
            if result['success']:
                logging.info(f"订单状态通知发送成功: order_id={order.id}, status={status_text}")
            else:
                logging.warning(f"订单状态通知发送失败: {result.get('error')}")
                
        except Exception as e:
            logging.error(f"发送订单状态通知异常: {e}")
    
    def on_finish(self):
        self.session.close()


class MiniprogramMessagesHandler(tornado.web.RequestHandler):
    """小程序聊天消息接口"""
    
    def check_xsrf_cookie(self):
        pass
    
    def initialize(self, mongo):
        self.mongo = mongo
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
    
    @tornado.gen.coroutine
    def get(self):
        """获取与指定好友的聊天记录"""
        from models.friendship import Friendship
        
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        friend_id = self.get_argument('friend_id', None)
        
        if not friend_id or friend_id == 'undefined':
            self.set_status(400)
            self.write(json.dumps({'success': False, 'error': '缺少friend_id参数'}))
            return
        
        try:
            friend_id = int(friend_id)
        except (ValueError, TypeError):
            self.set_status(400)
            self.write(json.dumps({'success': False, 'error': '无效的friend_id参数'}))
            return
        
        try:
            friend = self.session.query(User).filter_by(id=friend_id).first()
            if not friend:
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '用户不存在'}))
                return
            
            messages_cursor = self.mongo.chat_messages.find({
                "$or": [
                    {"from_user_id": user_id, "to_user_id": friend_id},
                    {"from_user_id": friend_id, "to_user_id": user_id}
                ]
            }).sort("timestamp", 1).limit(100)
            
            messages = yield messages_cursor.to_list(length=100)
            
            result = []
            for msg in messages:
                ts = msg.get('timestamp')
                if isinstance(ts, datetime.datetime):
                    # 返回原始UTC时间，前端负责UTC→UTC+8转换
                    if ts.tzinfo is not None:
                        # 有时区信息 - 转换为UTC
                        ts_utc = ts.astimezone(datetime.timezone.utc)
                    else:
                        # naive datetime - MongoDB返回的是UTC时间
                        ts_utc = ts.replace(tzinfo=datetime.timezone.utc)
                    
                    # 返回UTC时间字符串和毫秒时间戳
                    time_str = ts_utc.strftime('%H:%M')
                    timestamp_str = ts_utc.strftime('%Y-%m-%d %H:%M:%S')
                    timestamp_ms = int(ts_utc.timestamp() * 1000)
                elif isinstance(ts, str):
                    # 字符串格式 - 直接返回
                    time_str = ts[-8:-3] if len(ts) >= 8 else ts
                    timestamp_str = ts
                    timestamp_ms = 0
                else:
                    time_str = ''
                    timestamp_str = ''
                    timestamp_ms = 0
                
                result.append({
                    '_id': str(msg.get('_id', '')),
                    'id': str(msg.get('_id', '')),
                    'from_user_id': msg.get('from_user_id'),
                    'to_user_id': msg.get('to_user_id'),
                    'sender_id': msg.get('from_user_id'),
                    'content': msg.get('message', ''),
                    'message': msg.get('message', ''),
                    'type': 'text',
                    'time': time_str,
                    'timestamp': timestamp_str,
                    'timestamp_ms': timestamp_ms,
                    'status': msg.get('status', 'read')
                })
            
            yield self.mongo.chat_messages.update_many(
                {"from_user_id": friend_id, "to_user_id": user_id, "status": "unread"},
                {"$set": {"status": "read"}}
            )
            
            self.write(json.dumps({
                'success': True,
                'messages': result,
                'friend': {
                    'id': friend.id,
                    'username': friend.username,
                    'room_number': friend.room_number or '未设置',
                    'avatar': convert_avatar_url(friend.wechat_avatar)
                }
            }))
            
        except Exception as e:
            logging.error(f"获取消息异常: {e}")
            self.write(json.dumps({'success': False, 'error': str(e), 'messages': []}))
    
    @tornado.gen.coroutine
    def post(self):
        """发送消息"""
        from models.friendship import Friendship
        
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        
        try:
            data = json.loads(self.request.body)
            friend_id = data.get('friend_id')
            message = data.get('message', '').strip()
            
            if not friend_id or not message:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '缺少必要参数'}))
                return
            
            friend_id = int(friend_id)
            
            user = self.session.query(User).filter_by(id=user_id).first()
            friend = self.session.query(User).filter_by(id=friend_id).first()
            
            if not user or not friend:
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '用户不存在'}))
                return
            
            friendship = self.session.query(Friendship).filter_by(user_id=user_id, friend_id=friend_id).first()
            if not friendship:
                friendship = Friendship(user_id=user_id, friend_id=friend_id)
                self.session.add(friendship)
            
            reverse_friendship = self.session.query(Friendship).filter_by(user_id=friend_id, friend_id=user_id).first()
            if not reverse_friendship:
                reverse_friendship = Friendship(user_id=friend_id, friend_id=user_id)
                self.session.add(reverse_friendship)
            
            self.session.commit()
            
            # 使用UTC时间（与其他接口统一）
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            
            message_doc = {
                "from_user_id": user_id,
                "from_username": user.username,
                "to_user_id": friend_id,
                "message": message,
                "timestamp": now_utc,
                "status": "unread"
            }
            
            result = yield self.mongo.chat_messages.insert_one(message_doc)
            message_id = str(result.inserted_id)
            timestamp_ms = int(now_utc.timestamp() * 1000)
            time_str = now_utc.strftime('%H:%M')
            
            # 通过WebSocket推送给接收方（返回UTC时间，前端处理转换）
            from controllers.chat_controller import connections
            
            # 检查接收方是否在线（兼容 int/str 类型的 key，并安全访问ws_connection）
            friend_id_int = int(friend_id)
            friend_id_str = str(friend_id)
            
            friend_online = False
            try:
                if friend_id_int in connections:
                    conn = connections.get(friend_id_int)
                    if conn and hasattr(conn, 'ws_connection') and conn.ws_connection:
                        friend_online = True
                if not friend_online and friend_id_str in connections:
                    conn = connections.get(friend_id_str)
                    if conn and hasattr(conn, 'ws_connection') and conn.ws_connection:
                        friend_online = True
            except Exception as conn_err:
                logging.warning(f"[MINIPROGRAM_MSG] 检查连接状态异常: {conn_err}")
                friend_online = False
            
            logging.info(f"[MINIPROGRAM_MSG] 发送者: {user_id}, 接收者: {friend_id}, 在线状态: {friend_online}")
            
            if friend_online:
                ws_message = {
                    'id': message_id,
                    '_id': message_id,
                    'from_user_id': user_id,
                    'to_user_id': friend_id,
                    'sender_id': user_id,
                    'content': message,
                    'message': message,
                    'type': 'text',
                    'time': time_str,
                    'timestamp': now_utc.strftime('%Y-%m-%d %H:%M:%S'),
                    'timestamp_ms': timestamp_ms,
                    'status': 'unread'
                }
                try:
                    target_conn = connections.get(friend_id_int) or connections.get(friend_id_str)
                    if target_conn:
                        target_conn.write_message(json.dumps(ws_message))
                except Exception as ws_error:
                    logging.error(f"WebSocket推送失败: {ws_error}")
            else:
                # 对方不在线，发送订阅消息通知
                logging.info(f"[MINIPROGRAM_MSG] 对方不在线，发送订阅通知: target={friend_id}")
                sender_display = user.room_number if user.room_number else user.username
                notification_info = {
                    'target_user_id': friend_id,
                    'target_openid': friend.wechat_openid,
                    'sender_name': sender_display,
                    'sender_id': user_id
                }
                IOLoop.current().spawn_callback(self._send_new_message_notification, notification_info)
            
            self.write(json.dumps({
                'success': True,
                'message': '发送成功',
                'message_id': message_id,
                'data': {
                    'id': message_id,
                    '_id': message_id,
                    'from_user_id': user_id,
                    'to_user_id': friend_id,
                    'sender_id': user_id,
                    'content': message,
                    'message': message,
                    'type': 'text',
                    'time': time_str,
                    'timestamp': now_utc.strftime('%Y-%m-%d %H:%M:%S'),
                    'timestamp_ms': timestamp_ms
                }
            }))
            
        except Exception as e:
            logging.error(f"发送消息异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    async def _send_new_message_notification(self, info):
        """发送新消息订阅通知（异步）"""
        try:
            from utils.wechat_subscribe_service import send_new_message_notification, get_beijing_time_str
            
            target_user_id = info['target_user_id']
            target_openid = info['target_openid']
            sender_name = info['sender_name']
            sender_id = info['sender_id']
            
            logging.info(f"[MINIPROGRAM_MSG] 异步通知开始: target={target_user_id}, sender={sender_name}")
            
            if not target_openid:
                logging.info(f"[MINIPROGRAM_MSG] 接收方未设置openid，跳过: user_id={target_user_id}")
                return
            
            time_str = get_beijing_time_str()
            result = send_new_message_notification(
                openid=target_openid,
                sender_name=sender_name,
                reminder_text='请点击查看详情查阅消息内容',
                send_time=time_str,
                page=f'pages/chat/room?friend_id={sender_id}'
            )
            
            logging.info(f"[MINIPROGRAM_MSG] 通知发送结果: target={target_user_id}, result={result}")
            
        except Exception as e:
            logging.error(f"[MINIPROGRAM_MSG] 发送通知异常: {e}")
    
    def on_finish(self):
        self.session.close()


class MiniprogramMarkMessagesReadHandler(tornado.web.RequestHandler):
    """小程序标记消息已读接口"""
    
    def check_xsrf_cookie(self):
        pass
    
    def initialize(self, mongo):
        self.mongo = mongo
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
    
    @tornado.gen.coroutine
    def post(self):
        """标记与指定好友的消息为已读"""
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        
        try:
            data = json.loads(self.request.body)
            friend_id = data.get('friend_id')
            
            if not friend_id or friend_id == 'undefined':
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '缺少friend_id参数'}))
                return
            
            try:
                friend_id = int(friend_id)
            except (ValueError, TypeError):
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '无效的friend_id参数'}))
                return
            
            result = yield self.mongo.chat_messages.update_many(
                {"from_user_id": friend_id, "to_user_id": user_id, "status": "unread"},
                {"$set": {"status": "read"}}
            )
            
            self.write(json.dumps({
                'success': True,
                'message': '标记成功',
                'modified_count': result.modified_count
            }))
            
        except Exception as e:
            logging.error(f"标记已读异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramProductsListHandler(tornado.web.RequestHandler):
    """小程序商品列表接口"""
    
    def check_xsrf_cookie(self):
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
    
    def _get_blocked_user_ids(self, current_user_id):
        """获取当前用户拉黑的用户ID列表"""
        from models.blacklist import Blacklist
        try:
            blocked_users = self.session.query(Blacklist.blocked_id).filter(
                Blacklist.blocker_id == int(current_user_id)
            ).all()
            return [b[0] for b in blocked_users]
        except Exception as e:
            logging.error(f"获取黑名单失败: {e}")
            return []
    
    def get(self):
        """获取商品列表（支持分页、标签过滤、关键词搜索）"""
        from models.product import Product
        
        try:
            # 获取分页参数
            page = int(self.get_argument('page', 1))
            page_size = int(self.get_argument('page_size', 20))
            
            # 获取过滤参数
            tag = self.get_argument('tag', '')
            keyword = self.get_argument('keyword', '')
            user_id = self.get_argument('user_id', '')
            
            # 获取当前登录用户ID（用于黑名单过滤）
            current_user_id = self._get_user_id()
            blocked_user_ids = []
            if current_user_id:
                blocked_user_ids = self._get_blocked_user_ids(current_user_id)
            
            # 构建查询
            query = self.session.query(Product).filter(
                Product.status == '在售',
                Product.quantity > 0
            )
            
            # 过滤被拉黑用户的商品
            if blocked_user_ids:
                query = query.filter(~Product.user_id.in_(blocked_user_ids))
            
            # 按标签过滤（支持逗号分隔的多标签模糊匹配）
            if tag and tag != '全部':
                # 使用LIKE进行模糊匹配，支持"书籍"匹配"书籍,家电"
                query = query.filter(Product.tag.ilike(f'%{tag}%'))
            
            # 按卖家ID过滤
            if user_id:
                query = query.filter(Product.user_id == int(user_id))
            
            # 按关键词搜索（商品名称或描述）
            if keyword:
                query = query.filter(
                    (Product.name.ilike(f'%{keyword}%')) |
                    (Product.description.ilike(f'%{keyword}%'))
                )
            
            # 获取总数
            total = query.count()
            
            # 分页
            offset = (page - 1) * page_size
            products = query.order_by(Product.upload_time.desc()).offset(offset).limit(page_size).all()
            
            # 构建返回数据
            from models.product import ProductImage
            products_list = []
            for product in products:
                seller = self.session.query(User).filter_by(id=product.user_id).first()
                
                # 获取主图（Product.image 字段存储的是主图文件名）
                main_image = product.image
                thumb_image = None
                
                # 如果主图为空，使用第一张图片
                if not main_image:
                    first_image_obj = self.session.query(ProductImage).filter_by(product_id=product.id).first()
                    if first_image_obj:
                        main_image = first_image_obj.filename
                        thumb_image = first_image_obj.thumb_filename
                else:
                    # 根据主图文件名查找对应的缩略图
                    main_image_obj = self.session.query(ProductImage).filter_by(
                        product_id=product.id, 
                        filename=main_image
                    ).first()
                    if main_image_obj and main_image_obj.thumb_filename:
                        thumb_image = main_image_obj.thumb_filename
                
                products_list.append({
                    'id': product.id,
                    'name': product.name,
                    'description': product.description,
                    'price': float(product.price),
                    'quantity': product.quantity,
                    'tag': product.tag,
                    'condition': product.condition or '九成新',
                    'image': thumb_image or main_image or '',  # 列表页优先使用缩略图
                    'original_image': main_image or '',  # 原图URL（详情页使用）
                    'status': product.status,
                    'upload_time': product.upload_time.strftime('%Y-%m-%d %H:%M') if product.upload_time else '',
                    'seller_id': product.user_id,
                    'seller_name': seller.username if seller else '未知',
                    'seller_room': seller.room_number if seller else '未设置'
                })
            
            self.write(json.dumps({
                'success': True,
                'products': products_list,
                'total': total,
                'page': page,
                'page_size': page_size,
                'has_more': offset + page_size < total
            }))
            
        except Exception as e:
            logging.error(f"获取商品列表异常: {e}")
            self.set_status(500)
            self.write(json.dumps({
                'success': False,
                'error': str(e),
                'products': []
            }))
    
    def on_finish(self):
        self.session.close()


class MiniprogramProductsVersionHandler(tornado.web.RequestHandler):
    """小程序商品列表版本检查接口 - 用于判断是否需要刷新缓存"""
    
    def check_xsrf_cookie(self):
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
    
    def _get_blocked_user_ids(self, current_user_id):
        """获取当前用户拉黑的用户ID列表"""
        from models.blacklist import Blacklist
        try:
            blocked_users = self.session.query(Blacklist.blocked_id).filter(
                Blacklist.blocker_id == int(current_user_id)
            ).all()
            return [b[0] for b in blocked_users]
        except Exception as e:
            logging.error(f"获取黑名单失败: {e}")
            return []
    
    def get(self):
        """获取商品列表版本信息（最新上传时间和总数）"""
        from models.product import Product
        
        try:
            tag = self.get_argument('tag', '')
            
            # 获取当前登录用户ID（用于黑名单过滤）
            current_user_id = self._get_user_id()
            blocked_user_ids = []
            if current_user_id:
                blocked_user_ids = self._get_blocked_user_ids(current_user_id)
            
            query = self.session.query(Product).filter(
                Product.status == '在售',
                Product.quantity > 0
            )
            
            # 过滤被拉黑用户的商品
            if blocked_user_ids:
                query = query.filter(~Product.user_id.in_(blocked_user_ids))
            
            if tag and tag != '全部' and tag != '':
                query = query.filter(Product.tag.ilike(f'%{tag}%'))
            
            total = query.count()
            
            latest_product = query.order_by(Product.upload_time.desc()).first()
            latest_time = ''
            if latest_product and latest_product.upload_time:
                latest_time = latest_product.upload_time.strftime('%Y-%m-%d %H:%M:%S')
            
            self.write(json.dumps({
                'success': True,
                'total': total,
                'latest_time': latest_time
            }))
            
        except Exception as e:
            logging.error(f"获取商品版本信息异常: {e}")
            self.set_status(500)
            self.write(json.dumps({
                'success': False,
                'error': str(e)
            }))
    
    def on_finish(self):
        self.session.close()


class MiniprogramActiveTagsHandler(tornado.web.RequestHandler):
    """小程序获取实际使用的商品标签接口"""
    
    def check_xsrf_cookie(self):
        pass
    
    def initialize(self):
        self.session = Session()
    
    def get(self):
        """获取所有在售商品中实际使用的标签（去重）- 支持逗号分隔多标签"""
        from models.product import Product
        
        try:
            # 查询所有在售且有库存的商品的标签
            tags_query = self.session.query(Product.tag).filter(
                Product.status == '在售',
                Product.quantity > 0,
                Product.tag.isnot(None),
                Product.tag != ''
            ).all()
            
            # 分割逗号分隔的标签并去重
            tag_set = set()
            for tag_row in tags_query:
                if tag_row[0]:
                    # 分割逗号分隔的标签（如"书籍,家电"）
                    tags = [t.strip() for t in tag_row[0].split(',')]
                    tag_set.update(tags)
            
            active_tags = list(tag_set)
            
            # 按固定顺序排序（保持与预设标签相同的顺序）
            preset_order = ['数码产品', '家用电器', '服装鞋包', '图书音像', '运动户外', '美妆个护', '家居用品', '其他']
            sorted_tags = []
            for preset_tag in preset_order:
                if preset_tag in active_tags:
                    sorted_tags.append(preset_tag)
            
            # 添加任何不在预设列表中的标签
            for tag in active_tags:
                if tag not in sorted_tags:
                    sorted_tags.append(tag)
            
            self.write(json.dumps({
                'success': True,
                'tags': sorted_tags,
                'count': len(sorted_tags)
            }))
            
        except Exception as e:
            logging.error(f"获取活跃标签异常: {e}")
            self.set_status(500)
            self.write(json.dumps({
                'success': False,
                'error': str(e),
                'tags': []
            }))
    
    def on_finish(self):
        self.session.close()


class MiniprogramChatListHandler(tornado.web.RequestHandler):
    """小程序聊天列表接口"""
    
    def check_xsrf_cookie(self):
        pass
    
    def initialize(self, mongo):
        self.mongo = mongo
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
    
    async def get(self):
        """获取聊天会话列表"""
        from models.friendship import Friendship
        from models.blacklist import Blacklist
        
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        
        # 验证当前用户是否存在
        current_user = self.session.query(User).filter_by(id=user_id).first()
        if not current_user:
            self.set_status(401)
            self.write(json.dumps({
                'success': False, 
                'error': '用户不存在，请重新登录',
                'need_relogin': True
            }))
            return
        
        try:
            # 第一步：从MongoDB查询给当前用户发过消息的用户ID
            message_senders = set()
            async for message in self.mongo.chat_messages.find({"to_user_id": user_id}):
                message_senders.add(message.get("from_user_id"))
            
            # 第二步：将这些用户添加为好友（如果还不是好友）
            existing_friendships = self.session.query(Friendship).filter_by(user_id=user_id).all()
            existing_friend_ids = {friendship.friend_id for friendship in existing_friendships}
            
            for sender_id in message_senders:
                if sender_id != user_id and sender_id not in existing_friend_ids:
                    # 验证发送者是否存在于数据库中
                    sender_exists = self.session.query(User).filter_by(id=sender_id).first()
                    if not sender_exists:
                        logging.warning(f"跳过不存在的用户ID {sender_id} 的好友关系")
                        continue
                    try:
                        new_friendship = Friendship(user_id=user_id, friend_id=sender_id)
                        self.session.add(new_friendship)
                        self.session.flush()
                    except Exception as e:
                        self.session.rollback()
                        logging.error(f"添加好友关系失败: {e}")
            
            try:
                self.session.commit()
            except Exception as e:
                self.session.rollback()
                logging.error(f"提交好友关系失败: {e}")
            
            # 第三步：查询更新后的好友列表
            friendships = self.session.query(Friendship).filter_by(user_id=user_id).all()
            
            conversations = []
            for friendship in friendships:
                friend = self.session.query(User).filter_by(id=friendship.friend_id).first()
                if not friend:
                    continue
                
                # 检查是否被屏蔽
                is_blocked = self.session.query(Blacklist).filter_by(blocker_id=user_id, blocked_id=friend.id).first() is not None
                if is_blocked:
                    continue
                
                last_message = await self.mongo.chat_messages.find_one(
                    {
                        "$or": [
                            {"from_user_id": user_id, "to_user_id": friendship.friend_id},
                            {"from_user_id": friendship.friend_id, "to_user_id": user_id}
                        ]
                    },
                    sort=[("timestamp", -1)]
                )
                
                unread_count = await self.mongo.chat_messages.count_documents({
                    "from_user_id": friendship.friend_id,
                    "to_user_id": user_id,
                    "status": "unread"
                })
                
                last_message_content = ""
                last_message_time = ""
                if last_message:
                    last_message_content = last_message.get("message", "")
                    if "timestamp" in last_message:
                        ts = last_message["timestamp"]
                        if isinstance(ts, datetime.datetime):
                            # 返回原始UTC时间，前端执行UTC+8转换
                            last_message_time = ts.strftime("%Y-%m-%d %H:%M")
                        else:
                            last_message_time = str(ts)
                
                # 优先显示房间号，如果没有则显示用户名
                display_name = friend.room_number if friend.room_number else friend.username
                
                conversations.append({
                    "id": friendship.friend_id,
                    "friend_id": friendship.friend_id,
                    "username": display_name,
                    "room_number": friend.room_number or "未设置",
                    "avatar": convert_avatar_url(friend.wechat_avatar),
                    "last_message": last_message_content[:50] if last_message_content else "暂无消息",
                    "last_time": last_message_time,
                    "unread_count": unread_count
                })
            
            conversations.sort(key=lambda x: x.get("last_time", ""), reverse=True)
            
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps(conversations))
            
        except Exception as e:
            logging.error(f"获取聊天列表异常: {e}")
            import traceback
            traceback.print_exc()
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramClearChatHandler(tornado.web.RequestHandler):
    """小程序清除聊天记录接口"""
    
    def check_xsrf_cookie(self):
        pass
    
    def initialize(self, mongo):
        self.mongo = mongo
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
    
    async def delete(self, friend_id):
        """删除与指定好友的所有聊天记录"""
        from models.friendship import Friendship
        
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        friend_id = int(friend_id)
        
        try:
            # 从MongoDB删除双向聊天记录
            result = await self.mongo.chat_messages.delete_many({
                "$or": [
                    {"from_user_id": user_id, "to_user_id": friend_id},
                    {"from_user_id": friend_id, "to_user_id": user_id}
                ]
            })
            
            deleted_count = result.deleted_count
            logging.info(f"用户 {user_id} 删除了与用户 {friend_id} 的 {deleted_count} 条聊天记录")
            
            # 可选：删除好友关系（让用户的聊天列表中不再显示该会话）
            friendship = self.session.query(Friendship).filter_by(
                user_id=user_id, friend_id=friend_id
            ).first()
            
            if friendship:
                self.session.delete(friendship)
                self.session.commit()
                logging.info(f"已删除用户 {user_id} 与 {friend_id} 的好友关系")
            
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps({
                'success': True,
                'message': f'已删除 {deleted_count} 条聊天记录',
                'deleted_count': deleted_count
            }))
            
        except Exception as e:
            logging.error(f"删除聊天记录异常: {e}")
            import traceback
            traceback.print_exc()
            self.session.rollback()
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramBroadcastsHandler(tornado.web.RequestHandler):
    """获取系统广播（最近10条商品发布）"""
    
    def check_xsrf_cookie(self):
        """禁用XSRF检查"""
        pass
    
    def initialize(self):
        self.session = Session()
    
    def get(self):
        """获取最近10条商品发布广播"""
        from models.product import Product
        
        try:
            # 查询最近10条商品，包含用户信息
            products = self.session.query(Product, User).join(
                User, Product.user_id == User.id
            ).filter(
                Product.status == '在售'
            ).order_by(
                Product.upload_time.desc()
            ).limit(10).all()
            
            broadcasts = []
            for product, user in products:
                import datetime
                
                beijing_tz = datetime.timezone(datetime.timedelta(hours=8))
                now = datetime.datetime.now(beijing_tz)
                upload_time = product.upload_time
                
                if upload_time.tzinfo is None:
                    upload_time_utc = upload_time.replace(tzinfo=datetime.timezone.utc)
                    upload_time_beijing = upload_time_utc.astimezone(beijing_tz)
                else:
                    upload_time_beijing = upload_time.astimezone(beijing_tz)
                
                delta = now - upload_time_beijing
                if delta.days > 0:
                    time_str = f'{delta.days}天前'
                elif delta.seconds > 3600:
                    hours = delta.seconds // 3600
                    time_str = f'{hours}小时前'
                elif delta.seconds > 60:
                    minutes = delta.seconds // 60
                    time_str = f'{minutes}分钟前'
                else:
                    time_str = '刚刚'
                
                broadcasts.append({
                    'room_number': user.room_number,
                    'product_id': product.id,
                    'product_name': product.name,
                    'time': time_str,
                    'upload_time': upload_time_beijing.strftime('%Y-%m-%d %H:%M:%S') if product.upload_time else ''
                })
            
            self.write(json.dumps({
                'success': True,
                'broadcasts': broadcasts
            }))
        except Exception as e:
            logging.error(f"获取广播失败: {e}")
            self.write(json.dumps({
                'success': False,
                'error': '获取广播失败'
            }))
    
    def on_finish(self):
        self.session.close()


class MiniprogramOrdersHandler(tornado.web.RequestHandler):
    """小程序订单API - 创建和获取订单列表"""
    
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
        """获取订单列表"""
        from models.order import Order
        from models.product import Product
        
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        order_type = self.get_argument('type', 'all')  # all, buying, selling
        
        try:
            from sqlalchemy import or_, and_, desc
            
            query = self.session.query(Order, Product, User).outerjoin(
                Product, Order.product_id == Product.id
            ).join(User, Order.user_id == User.id)
            
            if order_type == 'buying':
                query = query.filter(Order.user_id == user_id, Order.status != 'cancelled')
            elif order_type == 'selling':
                query = query.filter(
                    or_(
                        Order.seller_id == user_id,
                        and_(Order.seller_id == None, Product.user_id == user_id)
                    ),
                    Order.status != 'cancelled'
                )
            else:
                query = query.filter(
                    or_(
                        Order.user_id == user_id,
                        Order.seller_id == user_id,
                        and_(Order.seller_id == None, Product.user_id == user_id)
                    ),
                    Order.status != 'cancelled'
                )
            
            orders_result = query.order_by(desc(Order.created_at)).all()
            
            orders_data = []
            for order, product, buyer in orders_result:
                seller = None
                if order.seller_id:
                    seller = self.session.query(User).filter_by(id=order.seller_id).first()
                elif product:
                    seller = self.session.query(User).filter_by(id=product.user_id).first()
                
                # 处理商品图片URL - 返回完整路径
                product_image = ''
                if product and product.image:
                    # 返回相对于/static/images/的路径，前端会拼接完整URL
                    product_image = product.image
                
                orders_data.append({
                    'id': order.id,
                    'product_id': order.product_id,
                    'product_name': order.product_name or (product.name if product else '商品已删除'),
                    'product_image': product_image,
                    'price': float(product.price) if product else 0,
                    'quantity': order.quantity,
                    'status': order.status,
                    'buyer_id': buyer.id,
                    'buyer_name': buyer.username,
                    'buyer_room': buyer.room_number or '',
                    'seller_id': seller.id if seller else None,
                    'seller_name': seller.username if seller else '未知',
                    'seller_room': seller.room_number if seller else '',
                    'created_at': order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else '',
                    'is_buyer': order.user_id == user_id,
                    'order_number': f'ORD{order.id:06d}'
                })
            
            self.write(json.dumps({'success': True, 'orders': orders_data}))
            
        except Exception as e:
            logging.error(f"获取订单列表异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def post(self):
        """创建订单"""
        from models.order import Order
        from models.product import Product
        
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        
        # 验证用户是否存在于数据库中
        current_user = self.session.query(User).filter_by(id=user_id).first()
        if not current_user:
            self.set_status(401)
            self.write(json.dumps({
                'success': False, 
                'error': '用户不存在，请重新登录',
                'need_relogin': True
            }))
            return
        
        try:
            data = json.loads(self.request.body)
            product_id = int(data.get('product_id'))
            quantity = int(data.get('quantity', 1))
            order_note = data.get('order_note', '')
            
            if quantity <= 0:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '购买数量必须大于0'}))
                return
            
            # 使用行锁FOR UPDATE防止并发下单导致超卖
            from sqlalchemy.exc import OperationalError as SQLOperationalError
            
            try:
                product = self.session.query(Product).filter_by(id=product_id).with_for_update(nowait=True).first()
            except SQLOperationalError:
                # 行锁冲突，说明有其他用户正在购买
                self.set_status(409)
                self.write(json.dumps({'success': False, 'error': '有其他用户正在购买此商品，请稍后重试'}))
                return
            
            if not product:
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '商品不存在'}))
                return
            
            # 再次检查库存（加锁后检查）
            if product.status == '已售完':
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '商品已售完'}))
                return
            
            if product.quantity < quantity:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '库存不足'}))
                return
            
            if product.user_id == user_id:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '不能购买自己的商品'}))
                return
            
            new_order = Order(
                product_id=product_id,
                user_id=user_id,
                quantity=quantity,
                product_name=product.name,
                seller_id=product.user_id,
                order_note=order_note
            )
            
            self.session.add(new_order)
            
            product.quantity -= quantity
            if product.quantity <= 0:
                product.status = "已售完"
            
            self.session.commit()
            
            # 获取发送通知需要的数据（在会话关闭前提取）
            buyer = self.session.query(User).filter_by(id=user_id).first()
            notification_info = {
                'seller_id': product.user_id,
                'product_id': product.id,
                'product_name': product.name,
                'buyer_username': buyer.username if buyer else '买家',
                'buyer_room_number': buyer.room_number if buyer else None,
                'quantity': quantity,
                'order_id': new_order.id
            }
            IOLoop.current().spawn_callback(self._send_seller_notification, notification_info)
            
            self.write(json.dumps({
                'success': True,
                'message': '订单创建成功',
                'order_id': new_order.id
            }))
            
        except ValueError as e:
            self.session.rollback()
            self.set_status(400)
            self.write(json.dumps({'success': False, 'error': '参数格式不正确'}))
        except Exception as e:
            self.session.rollback()
            logging.error(f"创建订单异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    async def _send_seller_notification(self, info):
        """发送订单通知给卖家（异步）"""
        try:
            seller_id = info['seller_id']
            product_id = info['product_id']
            product_name = info['product_name']
            buyer_username = info['buyer_username']
            buyer_room_number = info['buyer_room_number']
            quantity = info['quantity']
            order_id = info['order_id']
            
            china_tz = datetime.timezone(datetime.timedelta(hours=8))
            timestamp = datetime.datetime.now(china_tz).strftime("%Y-%m-%d %H:%M")
            
            # 构建系统通知消息
            notification_data = {
                "from_user_id": 0,
                "from_username": "系统通知",
                "to_user_id": seller_id,
                "message": f"您有新订单！买家{buyer_username}购买了您的商品《{product_name}》，数量：{quantity}件。",
                "product_id": product_id,
                "product_name": product_name,
                "timestamp": timestamp,
                "status": "unread",
                "type": "order_notification",
                "order_id": order_id
            }
            
            # 保存到MongoDB
            try:
                await mongo_database.chat_messages.insert_one(notification_data)
                logging.info(f"订单通知已保存到数据库: 订单{order_id}, 卖家{seller_id}")
            except Exception as db_error:
                logging.error(f"保存通知到数据库失败: {str(db_error)}")
            
            # 发送微信订阅消息通知卖家（商品售出通知）
            try:
                from utils.wechat_subscribe_service import send_product_sold_notification
                db_session = Session()
                try:
                    seller = db_session.query(User).filter_by(id=seller_id).first()
                    if seller and seller.wechat_openid:
                        buyer_display = buyer_room_number if buyer_room_number else buyer_username
                        result = send_product_sold_notification(
                            openid=seller.wechat_openid,
                            product_name=product_name,
                            buyer_name=buyer_display,
                            sold_time=timestamp,
                            page=f'pages/order/detail?id={order_id}'
                        )
                        logging.info(f"商品售出订阅消息发送结果: 订单{order_id}, 结果={result}")
                    else:
                        logging.info(f"卖家未设置openid，跳过订阅消息: seller_id={seller_id}")
                finally:
                    db_session.close()
            except Exception as subscribe_error:
                logging.warning(f"发送订阅消息失败: {str(subscribe_error)}")
                
        except Exception as notif_error:
            logging.error(f"发送卖家通知失败: {str(notif_error)}")
    
    def on_finish(self):
        self.session.close()


class MiniprogramOrderDetailHandler(tornado.web.RequestHandler):
    """小程序订单详情"""
    
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
    
    def get(self, order_id):
        """获取订单详情"""
        from models.order import Order
        from models.product import Product
        
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        
        try:
            order = self.session.query(Order).filter_by(id=order_id).first()
            
            if not order:
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '订单不存在'}))
                return
            
            can_view = order.user_id == user_id or order.seller_id == user_id
            if not can_view:
                product = self.session.query(Product).filter_by(id=order.product_id).first()
                if product and product.user_id == user_id:
                    can_view = True
            
            if not can_view:
                self.set_status(403)
                self.write(json.dumps({'success': False, 'error': '无权查看此订单'}))
                return
            
            product = self.session.query(Product).filter_by(id=order.product_id).first()
            buyer = self.session.query(User).filter_by(id=order.user_id).first()
            seller = None
            if order.seller_id:
                seller = self.session.query(User).filter_by(id=order.seller_id).first()
            elif product:
                seller = self.session.query(User).filter_by(id=product.user_id).first()
            
            # 处理商品图片URL
            product_image = ''
            if product and product.image:
                product_image = product.image
            
            self.write(json.dumps({
                'success': True,
                'order': {
                    'id': order.id,
                    'order_number': f'ORD{order.id:06d}',
                    'product_id': order.product_id,
                    'product_name': order.product_name or (product.name if product else '商品已删除'),
                    'product_image': product_image,
                    'price': float(product.price) if product else 0,
                    'quantity': order.quantity,
                    'status': order.status,
                    'order_note': order.order_note or '',
                    'buyer_id': buyer.id if buyer else None,
                    'buyer_name': buyer.username if buyer else '',
                    'buyer_room': buyer.room_number if buyer else '',
                    'seller_id': seller.id if seller else None,
                    'seller_name': seller.username if seller else '',
                    'seller_room': seller.room_number if seller else '',
                    'created_at': order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else '',
                    'shipped_at': order.shipped_at.strftime('%Y-%m-%d %H:%M') if order.shipped_at else '',
                    'completed_at': order.completed_at.strftime('%Y-%m-%d %H:%M') if order.completed_at else '',
                    'is_buyer': order.user_id == user_id,
                    'is_seller': (order.seller_id == user_id) or (product and product.user_id == user_id)
                }
            }))
            
        except Exception as e:
            logging.error(f"获取订单详情异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramOrderCancelHandler(tornado.web.RequestHandler):
    """小程序取消订单"""
    
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
    
    def post(self, order_id):
        """取消订单"""
        from models.order import Order
        from models.product import Product
        
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        
        try:
            order = self.session.query(Order).filter_by(id=order_id).first()
            
            if not order:
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '订单不存在'}))
                return
            
            if order.user_id != user_id:
                self.set_status(403)
                self.write(json.dumps({'success': False, 'error': '只有买家可以取消订单'}))
                return
            
            if order.status != 'pending':
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '只能取消待确认的订单'}))
                return
            
            product = self.session.query(Product).filter_by(id=order.product_id).first()
            if product:
                product.quantity += order.quantity
                product.status = "在售"
            
            order.status = 'cancelled'
            self.session.commit()
            
            self.write(json.dumps({'success': True, 'message': '订单取消成功'}))
            
        except Exception as e:
            self.session.rollback()
            logging.error(f"取消订单异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramOrderDeleteHandler(tornado.web.RequestHandler):
    """小程序删除订单（已完成或已取消的订单）"""
    
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
    
    def delete(self, order_id):
        """删除订单"""
        from models.order import Order
        
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        
        try:
            order = self.session.query(Order).filter_by(id=order_id).first()
            
            if not order:
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '订单不存在'}))
                return
            
            is_buyer = order.user_id == user_id
            is_seller = order.seller_id == user_id
            
            if not is_buyer and not is_seller:
                self.set_status(403)
                self.write(json.dumps({'success': False, 'error': '无权删除此订单'}))
                return
            
            if order.status not in ['completed', 'cancelled']:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '只能删除已完成或已取消的订单'}))
                return
            
            self.session.delete(order)
            self.session.commit()
            
            self.write(json.dumps({'success': True, 'message': '订单删除成功'}))
            
        except Exception as e:
            self.session.rollback()
            logging.error(f"删除订单异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramOrderShipHandler(tornado.web.RequestHandler):
    """小程序卖家发货"""
    
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
    
    def post(self, order_id):
        """卖家发货"""
        from models.order import Order
        from models.product import Product
        
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        
        try:
            order = self.session.query(Order).filter_by(id=order_id).first()
            
            if not order:
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '订单不存在'}))
                return
            
            is_seller = False
            if order.seller_id and order.seller_id == user_id:
                is_seller = True
            elif not order.seller_id:
                product = self.session.query(Product).filter_by(id=order.product_id).first()
                if product and product.user_id == user_id:
                    is_seller = True
            
            if not is_seller:
                self.set_status(403)
                self.write(json.dumps({'success': False, 'error': '只有卖家可以发货'}))
                return
            
            if order.status != 'pending':
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '只有待确认的订单才能发货'}))
                return
            
            order.status = 'shipped'
            order.shipped_at = datetime.datetime.now()
            self.session.commit()
            
            # 发送订单状态通知给买家
            from utils.wechat_subscribe_service import send_order_status_notification
            self._send_order_status_notification(order, '已发货')
            
            self.write(json.dumps({'success': True, 'message': '发货成功'}))
            
        except Exception as e:
            self.session.rollback()
            logging.error(f"发货异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def _send_order_status_notification(self, order, status_text):
        """发送订单状态通知给买家"""
        try:
            from models.product import Product
            from utils.wechat_subscribe_service import send_order_status_notification, get_beijing_time_str
            
            # 获取买家信息
            buyer = self.session.query(User).filter_by(id=order.user_id).first()
            
            if not buyer or not buyer.wechat_openid:
                logging.info(f"买家未设置openid，跳过通知: order_id={order.id}")
                return
            
            # 获取商品名称
            product = self.session.query(Product).filter_by(id=order.product_id).first()
            product_name = product.name if product else '未知商品'
            
            # 发送通知 - 模板字段: character_string2(订单编号), thing7(备注), phrase10(订单状态), thing11(商品名称)
            result = send_order_status_notification(
                openid=buyer.wechat_openid,
                order_number=str(order.id),
                product_name=product_name,
                status_text=status_text,
                remark='卖家已发货，请注意查收',
                page=f'pages/order/detail?id={order.id}'
            )
            
            if result['success']:
                logging.info(f"订单状态通知发送成功: order_id={order.id}, status={status_text}")
            else:
                logging.warning(f"订单状态通知发送失败: {result.get('error')}")
                
        except Exception as e:
            logging.error(f"发送订单状态通知异常: {e}")
    
    def on_finish(self):
        self.session.close()


class MiniprogramMyProductsHandler(tornado.web.RequestHandler):
    """小程序获取我的商品列表"""
    
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
        """获取我的商品列表"""
        from models.product import Product, ProductImage
        
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        status_filter = self.get_argument('status', 'all')  # all, 在售, 已售完, 已删除
        
        try:
            from sqlalchemy import desc
            
            query = self.session.query(Product).filter(Product.user_id == user_id)
            
            if status_filter != 'all':
                query = query.filter(Product.status == status_filter)
            else:
                query = query.filter(Product.status != '已删除')
            
            products = query.order_by(desc(Product.upload_time)).all()
            
            products_data = []
            for product in products:
                images = self.session.query(ProductImage).filter_by(product_id=product.id).all()
                products_data.append({
                    'id': product.id,
                    'name': product.name,
                    'description': product.description[:100] if product.description else '',
                    'price': float(product.price),
                    'quantity': product.quantity,
                    'status': product.status,
                    'condition': product.condition or '九成新',
                    'tag': product.tag,
                    'image': product.image or '',
                    'images': [img.filename for img in images],
                    'upload_time': product.upload_time.strftime('%Y-%m-%d %H:%M') if product.upload_time else ''
                })
            
            self.write(json.dumps({'success': True, 'products': products_data}))
            
        except Exception as e:
            logging.error(f"获取我的商品列表异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramProductDeleteImageHandler(tornado.web.RequestHandler):
    """小程序删除商品图片接口"""
    
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
    
    def _delete_image(self, product_id, image_id):
        """删除图片的核心逻辑"""
        from models.product import Product, ProductImage
        
        user_id = self._get_user_id()
        if not user_id:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        try:
            # 验证商品所有权
            product = self.session.query(Product).filter_by(id=int(product_id)).first()
            if not product or product.user_id != int(user_id):
                self.set_status(403)
                self.write(json.dumps({'success': False, 'error': '无权操作该商品'}))
                return
            
            # 删除图片
            image = self.session.query(ProductImage).filter_by(id=int(image_id), product_id=int(product_id)).first()
            if image:
                import os
                upload_path = 'mystatics/images'
                
                # 检查是否是云存储文件（cloud://开头）
                if image.filename and image.filename.startswith('cloud://'):
                    # 调用微信云托管API删除云存储文件
                    try:
                        from utils.wechat_cloud_storage import delete_cloud_files
                        result = delete_cloud_files([image.filename])
                        if result['success']:
                            logging.info(f"云存储文件删除成功: {image.filename}")
                        else:
                            logging.warning(f"云存储文件删除失败: {result['message']}")
                    except Exception as e:
                        logging.warning(f"调用云存储删除API失败: {e}")
                else:
                    # 本地文件：删除文件系统中的文件
                    image_path = os.path.join(upload_path, image.filename)
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        logging.info(f"已删除商品图片文件: {image_path}")
                    
                    # 删除缩略图文件（如果存在）
                    if image.thumb_filename and not image.thumb_filename.startswith('cloud://'):
                        thumb_path = os.path.join(upload_path, image.thumb_filename)
                        if os.path.exists(thumb_path):
                            os.remove(thumb_path)
                            logging.info(f"已删除商品缩略图文件: {thumb_path}")
                    
                    # 删除中等尺寸图（如果存在）
                    if image.medium_filename and not image.medium_filename.startswith('cloud://'):
                        medium_path = os.path.join(upload_path, image.medium_filename)
                        if os.path.exists(medium_path):
                            os.remove(medium_path)
                            logging.info(f"已删除商品中等尺寸图: {medium_path}")
                
                # 检查删除的是否是主图
                was_primary = (product.image == image.filename)
                
                self.session.delete(image)
                
                # 如果删除的是主图，更新为剩余图片的第一张
                if was_primary:
                    remaining_images = self.session.query(ProductImage).filter_by(product_id=int(product_id)).first()
                    if remaining_images:
                        product.image = remaining_images.filename
                    else:
                        product.image = ""
                
                self.session.commit()
                
                self.write(json.dumps({'success': True, 'message': '图片删除成功'}))
            else:
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '图片不存在'}))
        except Exception as e:
            self.session.rollback()
            logging.error(f"删除商品图片异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': f'删除失败: {str(e)}'}))
    
    def post(self, product_id, image_id):
        """删除商品图片（POST方法）"""
        self._delete_image(product_id, image_id)
    
    def delete(self, product_id, image_id):
        """删除商品图片（DELETE方法）"""
        self._delete_image(product_id, image_id)
    
    def on_finish(self):
        self.session.close()


class MiniprogramProductUpdateHandler(tornado.web.RequestHandler):
    """小程序编辑商品接口"""
    
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
    
    def post(self):
        """编辑商品信息"""
        from models.product import Product, ProductImage
        import os
        
        user_id = self._get_user_id()
        if not user_id:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        try:
            # 从 JSON body 或查询参数中获取数据
            try:
                data = json.loads(self.request.body)
            except:
                data = {}
            
            product_id = data.get("product_id") or self.get_argument("product_id", None)
            name = data.get("name", "") or self.get_argument("name", "")
            description = data.get("description", "") or self.get_argument("description", "")
            price_str = data.get("price", "0") or self.get_argument("price", "0")
            tag = data.get("tag", "其他") or self.get_argument("tag", "其他")
            condition = data.get("condition", "九成新") or self.get_argument("condition", "九成新")
            quantity_str = data.get("quantity") or self.get_argument("quantity", None)
            
            if not product_id:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '商品ID不能为空'}))
                return
            
            product = self.session.query(Product).filter_by(id=int(product_id)).first()
            if not product:
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '商品不存在'}))
                return
            
            if product.user_id != int(user_id):
                self.set_status(403)
                self.write(json.dumps({'success': False, 'error': '无权编辑该商品'}))
                return
            
            if len(description) > 5000:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '商品描述过长，最多5000字符'}))
                return
            
            product.name = name
            product.description = description
            product.price = float(price_str)
            product.tag = tag
            product.condition = condition
            
            # 更新商品数量
            if quantity_str is not None:
                new_quantity = int(quantity_str)
                product.quantity = new_quantity
                # 如果数量从0变为大于0，将状态改为"在售"
                if new_quantity > 0 and product.status == '已售完':
                    product.status = '在售'
                # 如果数量变为0，将状态改为"已售完"
                elif new_quantity <= 0:
                    product.status = '已售完'
            
            self.session.commit()
            
            self.write(json.dumps({
                'success': True,
                'message': '商品编辑成功',
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'price': float(product.price)
                }
            }))
            
        except ValueError as e:
            self.session.rollback()
            self.set_status(400)
            self.write(json.dumps({'success': False, 'error': '价格格式不正确'}))
        except Exception as e:
            self.session.rollback()
            logging.error(f"编辑商品异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': f'编辑失败: {str(e)}'}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramAvatarUploadHandler(tornado.web.RequestHandler):
    """小程序用户头像上传接口"""
    
    def check_xsrf_cookie(self):
        """禁用XSRF检查"""
        pass
    
    def initialize(self, app_settings=None):
        self.session = Session()
        self.app_settings = app_settings or {}
    
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
        """上传用户头像到微信云托管或本地存储
        
        优先使用微信云托管对象存储，否则回退到本地存储
        """
        import os
        import uuid
        from utils.wechat_cloud_storage import upload_file_to_cloud, get_is_cloud_run
        from utils.wechat_cloud_storage import delete_cloud_files
        
        try:
            user_id = self._get_user_id()
            logging.info(f"头像上传请求: user_id={user_id}, files={list(self.request.files.keys())}")
            
            if not user_id:
                self.set_status(401)
                self.write(json.dumps({
                    'success': False,
                    'error': '未登录'
                }))
                return
            
            avatar_files = self.request.files.get('avatar', [])
            logging.info(f"上传的文件数量: {len(avatar_files)}")
            if not avatar_files:
                logging.error("没有找到avatar文件")
                self.set_status(400)
                self.write(json.dumps({
                    'success': False,
                    'error': '请选择头像文件'
                }))
                return
            
            avatar = avatar_files[0]
            orig_filename = avatar['filename']
            image_body = avatar['body']
            
            user = self.session.query(User).filter_by(id=int(user_id)).first()
            if not user:
                self.set_status(404)
                self.write(json.dumps({
                    'success': False,
                    'error': '用户不存在'
                }))
                return
            
            old_avatar = user.wechat_avatar
            avatar_url = None
            is_cloud = False
            
            # 优先尝试上传到微信云托管
            if get_is_cloud_run():
                cloud_result = upload_file_to_cloud(image_body, orig_filename, 'avatars')
                if cloud_result['success']:
                    avatar_url = cloud_result['file_id']
                    is_cloud = True
                    logging.info(f"头像已上传到微信云托管: {avatar_url}")
                    
                    if old_avatar and old_avatar.startswith('cloud://'):
                        delete_cloud_files([old_avatar])
                else:
                    logging.warning(f"微信云托管上传失败，回退到本地存储: {cloud_result.get('message')}")
            
            # 云上传失败或非云环境时，使用本地存储
            if not avatar_url:
                ext = os.path.splitext(orig_filename)[1] or '.jpg'
                filename = f"avatar_{user_id}_{uuid.uuid4().hex[:8]}{ext}"
                
                upload_base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mystatics', 'images')
                upload_path = os.path.join(upload_base, 'avatars')
                os.makedirs(upload_path, exist_ok=True)
                filepath = os.path.join(upload_path, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(image_body)
                
                avatar_url = f"/images/avatars/{filename}"
                is_cloud = False
                logging.info(f"头像已保存到本地存储: {avatar_url}")
                
                if old_avatar and old_avatar.startswith('/images/avatars/'):
                    old_filename = old_avatar.split('/')[-1]
                    old_filepath = os.path.join(upload_path, old_filename)
                    try:
                        if os.path.exists(old_filepath):
                            os.remove(old_filepath)
                            logging.info(f"已删除旧头像: {old_filepath}")
                    except Exception as e:
                        logging.warning(f"删除旧头像失败: {e}")
            
            user.wechat_avatar = avatar_url
            user.avatar_security_status = 'pending'
            
            from models.image_verification import ImageVerification
            from controllers.content_security_controller import check_media_security_async
            
            trace_id = None
            if user.wechat_openid:
                if is_cloud:
                    full_url = avatar_url
                else:
                    host = self.request.headers.get('X-Forwarded-Host') or self.request.host
                    protocol = self.request.headers.get('X-Forwarded-Proto', 'https')
                    full_url = f"{protocol}://{host}{avatar_url}"
                
                logging.info(f"[AVATAR] 提交安全检测 URL: {full_url}")
                result = check_media_security_async(full_url, user.wechat_openid, media_type=2, scene=1)
                trace_id = result.get('trace_id')
                
                if trace_id:
                    user.avatar_trace_id = trace_id
                    
                    verification = ImageVerification(
                        owner_user_id=user.id,
                        biz_type='avatar',
                        file_url=avatar_url,
                        image_url=avatar_url,
                        trace_id=trace_id,
                        status='pending'
                    )
                    self.session.add(verification)
                    logging.info(f"[AVATAR] 创建验证记录: user={user.id}, trace_id={trace_id}")
                else:
                    logging.error(f"[AVATAR] 安全检测提交失败，无 trace_id，保持 pending 状态")
            else:
                user.avatar_security_status = 'approved'
                logging.warning(f"[AVATAR] 用户无 openid，跳过安全检测")
            
            self.session.commit()
            
            self.write(json.dumps({
                'success': True,
                'message': '头像上传成功',
                'avatar_url': avatar_url,
                'security_status': user.avatar_security_status,
                'trace_id': trace_id,
                'is_cloud': is_cloud
            }))
            
        except Exception as e:
            self.session.rollback()
            logging.error(f"头像上传异常: {e}")
            import traceback
            traceback.print_exc()
            self.set_status(500)
            self.write(json.dumps({
                'success': False,
                'error': f'上传失败: {str(e)}'
            }))
    
    def on_finish(self):
        self.session.close()


class MiniprogramProductStatsHandler(tornado.web.RequestHandler):
    """小程序商品统计接口"""
    
    def check_xsrf_cookie(self):
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
                    return token.split('_')[-1]
                except:
                    pass
        return None
    
    def get(self):
        """获取用户商品统计数据"""
        from models.product import Product
        from models.favorite import Favorite
        
        try:
            user_id = self._get_user_id()
            if not user_id:
                self.set_status(401)
                self.write(json.dumps({'success': False, 'error': '请先登录'}))
                return
            
            # 统计在售商品数量
            selling_count = self.session.query(Product).filter(
                Product.user_id == int(user_id),
                Product.status == '在售',
                Product.quantity > 0
            ).count()
            
            # 统计已售商品数量
            sold_count = self.session.query(Product).filter(
                Product.user_id == int(user_id),
                Product.status == '已售'
            ).count()
            
            # 统计收藏数量（查询 xu_favorites 表）
            favorites_count = self.session.query(Favorite).filter(
                Favorite.user_id == int(user_id)
            ).count()
            
            self.write(json.dumps({
                'success': True,
                'selling': selling_count,
                'sold': sold_count,
                'favorites': favorites_count
            }))
            
        except Exception as e:
            logging.error(f"获取商品统计异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramUnreadCountHandler(tornado.web.RequestHandler):
    """小程序未读订单计数接口"""
    
    def check_xsrf_cookie(self):
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
                    return token.split('_')[-1]
                except:
                    pass
        return None
    
    def get(self):
        """获取用户未读订单数量（卖家待处理订单）"""
        from models.order import Order
        
        try:
            user_id = self._get_user_id()
            if not user_id:
                self.set_status(401)
                self.write(json.dumps({'success': False, 'error': '请先登录'}))
                return
            
            # 查询该卖家的待处理订单数量 (status='pending' AND seller_id=user_id)
            unread_count = self.session.query(Order).filter(
                Order.seller_id == int(user_id),
                Order.status == 'pending'
            ).count()
            
            self.write(json.dumps({
                'success': True,
                'count': unread_count,
                'unread_count': unread_count
            }))
            
        except Exception as e:
            logging.error(f"获取未读订单计数异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e), 'count': 0}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramPhoneBindSendCodeHandler(tornado.web.RequestHandler):
    """小程序绑定手机号 - 发送验证码"""
    
    def check_xsrf_cookie(self):
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
                    return token.split('_')[-1]
                except:
                    pass
        return None
    
    def post(self):
        """发送手机号绑定验证码"""
        from utils.sms_service import create_verification_code
        
        try:
            user_id = self._get_user_id()
            if not user_id:
                self.set_status(401)
                self.write(json.dumps({'success': False, 'error': '请先登录'}))
                return
            
            data = json.loads(self.request.body)
            phone = data.get('phone', '').strip()
            
            if not phone:
                self.write(json.dumps({'success': False, 'error': '请输入手机号'}))
                return
            
            if len(phone) != 11 or not phone.isdigit():
                self.write(json.dumps({'success': False, 'error': '请输入有效的11位手机号'}))
                return
            
            # 检查手机号是否已被其他用户绑定
            existing_user = self.session.query(User).filter(
                User.phone == phone,
                User.id != int(user_id)
            ).first()
            
            if existing_user:
                self.write(json.dumps({
                    'success': False, 
                    'error': '该手机号已被其他账号绑定，如有疑问请联系管理员'
                }))
                return
            
            # 发送验证码
            code = create_verification_code(self.session, phone)
            
            if code:
                self.write(json.dumps({
                    'success': True,
                    'message': '验证码已发送',
                    'dev_code': code  # 开发模式返回验证码，生产环境可移除
                }))
            else:
                self.write(json.dumps({'success': False, 'error': '发送验证码失败，请稍后重试'}))
                
        except Exception as e:
            logging.error(f"发送绑定验证码异常: {e}")
            self.write(json.dumps({'success': False, 'error': '系统错误，请稍后重试'}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramPhoneBindVerifyHandler(tornado.web.RequestHandler):
    """小程序绑定手机号 - 验证并绑定"""
    
    def check_xsrf_cookie(self):
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
                    return token.split('_')[-1]
                except:
                    pass
        return None
    
    def post(self):
        """验证手机号并绑定到当前用户
        
        使用事务确保验证码验证和绑定操作的原子性：
        - 验证码标记used和手机号绑定在同一事务中
        - 任一步骤失败都会回滚整个事务
        """
        from models.verification_code import VerificationCode
        
        try:
            user_id = self._get_user_id()
            if not user_id:
                self.set_status(401)
                self.write(json.dumps({'success': False, 'error': '请先登录'}))
                return
            
            data = json.loads(self.request.body)
            phone = data.get('phone', '').strip()
            code = data.get('code', '').strip()
            
            if not phone or not code:
                self.write(json.dumps({'success': False, 'error': '请输入手机号和验证码'}))
                return
            
            # 再次检查手机号是否已被其他用户绑定
            existing_user = self.session.query(User).filter(
                User.phone == phone,
                User.id != int(user_id)
            ).first()
            
            if existing_user:
                self.write(json.dumps({
                    'success': False, 
                    'error': '该手机号已被其他账号绑定'
                }))
                return
            
            # 在同一事务中验证验证码并绑定手机号
            now = datetime.datetime.now(datetime.timezone.utc)
            
            verification = self.session.query(VerificationCode).filter(
                VerificationCode.phone == phone,
                VerificationCode.code == code,
                VerificationCode.is_used == 0,
                VerificationCode.expires_at > now
            ).order_by(VerificationCode.created_at.desc()).first()
            
            if not verification:
                self.write(json.dumps({'success': False, 'error': '验证码错误或已过期'}))
                return
            
            # 获取用户
            user = self.session.query(User).filter_by(id=int(user_id)).first()
            if not user:
                self.write(json.dumps({'success': False, 'error': '用户不存在'}))
                return
            
            # 在同一事务中：标记验证码已用 + 绑定手机号
            verification.is_used = 1
            user.phone = phone
            self.session.commit()
            
            logging.info(f"用户 {user.username} (ID:{user_id}) 成功绑定手机号: {phone}")
            
            self.write(json.dumps({
                'success': True,
                'message': '手机号绑定成功',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'phone': user.phone,
                    'room_number': user.room_number,
                    'wechat_nickname': user.wechat_nickname,
                    'wechat_avatar': convert_avatar_url(user.wechat_avatar)
                }
            }))
            
        except Exception as e:
            self.session.rollback()
            logging.error(f"绑定手机号异常: {e}")
            self.write(json.dumps({'success': False, 'error': '绑定失败，请稍后重试'}))
    
    def on_finish(self):
        self.session.close()


class MiniprogramPhoneUnbindHandler(tornado.web.RequestHandler):
    """小程序解绑手机号"""
    
    def check_xsrf_cookie(self):
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
                    return token.split('_')[-1]
                except:
                    pass
        return None
    
    def post(self):
        """解绑当前用户的手机号"""
        try:
            user_id = self._get_user_id()
            if not user_id:
                self.set_status(401)
                self.write(json.dumps({'success': False, 'error': '请先登录'}))
                return
            
            user = self.session.query(User).filter_by(id=int(user_id)).first()
            if not user:
                self.write(json.dumps({'success': False, 'error': '用户不存在'}))
                return
            
            if not user.phone:
                self.write(json.dumps({'success': False, 'error': '当前账号未绑定手机号'}))
                return
            
            old_phone = user.phone
            user.phone = None
            self.session.commit()
            
            logging.info(f"用户 {user.username} (ID:{user_id}) 解绑手机号: {old_phone}")
            
            self.write(json.dumps({
                'success': True,
                'message': '手机号已解绑',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'phone': user.phone,
                    'room_number': user.room_number
                }
            }))
            
        except Exception as e:
            self.session.rollback()
            logging.error(f"解绑手机号异常: {e}")
            self.write(json.dumps({'success': False, 'error': '解绑失败，请稍后重试'}))
    
    def on_finish(self):
        self.session.close()
