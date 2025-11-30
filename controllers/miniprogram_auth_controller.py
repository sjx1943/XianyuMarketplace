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
                    import re
                    existing_images = self.session.query(ProductImage).filter_by(product_id=product.id).count()
                    for i, image in enumerate(images):
                        idx = existing_images + i
                        # 规范化文件名：移除空格和特殊字符
                        orig_filename = image['filename']
                        normalized_filename = re.sub(r'[^\w\-\.]', '_', orig_filename)
                        filename = f"{product.id}_{idx}_{normalized_filename}"
                        filepath = os.path.join(upload_path, filename)
                        
                        with open(filepath, "wb") as f:
                            f.write(image["body"])
                        
                        product_image = ProductImage(filename=filename, product_id=product.id)
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
            import re
            
            for i, image in enumerate(images):
                # 规范化文件名：移除空格和特殊字符
                orig_filename = image['filename']
                normalized_filename = re.sub(r'[^\w\-\.]', '_', orig_filename)
                filename = f"{new_product.id}_{i}_{normalized_filename}"
                filepath = os.path.join(upload_path, filename)
                
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
                'image': main_image,
                'images': [{'id': img.id, 'filename': img.filename} for img in images],
                'upload_time': product.upload_time.strftime('%Y-%m-%d %H:%M') if product.upload_time else '',
                'seller_id': product.user_id,
                'seller': {
                    'id': seller.id,
                    'username': seller.username,
                    'room_number': seller.room_number or '未设置',
                    'avatar': seller.wechat_avatar or ''
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
        """删除商品（软删除）"""
        from models.product import Product
        
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
            
            self.write(json.dumps({'success': True, 'message': '确认收货成功'}))
            
        except Exception as e:
            self.session.rollback()
            logging.error(f"确认收货异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
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
                    # 转换为北京时间（UTC+8）
                    beijing_time = ts + datetime.timedelta(hours=8)
                    time_str = beijing_time.strftime('%H:%M')
                else:
                    time_str = ''
                
                result.append({
                    'id': str(msg.get('_id', '')),
                    'from_user_id': msg.get('from_user_id'),
                    'to_user_id': msg.get('to_user_id'),
                    'sender_id': msg.get('from_user_id'),
                    'content': msg.get('message', ''),
                    'message': msg.get('message', ''),
                    'type': 'text',
                    'time': time_str,
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
                    'avatar': friend.wechat_avatar or ''
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
            
            china_tz = datetime.timezone(datetime.timedelta(hours=8))
            now = datetime.datetime.now(china_tz)
            
            message_doc = {
                "from_user_id": user_id,
                "from_username": user.username,
                "to_user_id": friend_id,
                "message": message,
                "timestamp": now,
                "status": "unread"
            }
            
            yield self.mongo.chat_messages.insert_one(message_doc)
            
            self.write(json.dumps({
                'success': True,
                'message': '发送成功',
                'data': {
                    'from_user_id': user_id,
                    'to_user_id': friend_id,
                    'message': message,
                    'timestamp': now.strftime('%Y-%m-%d %H:%M:%S')
                }
            }))
            
        except Exception as e:
            logging.error(f"发送消息异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
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
            
            # 构建查询
            query = self.session.query(Product).filter(
                Product.status == '在售',
                Product.quantity > 0
            )
            
            # 按标签过滤
            if tag and tag != '全部':
                query = query.filter(Product.tag == tag)
            
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
            products_list = []
            for product in products:
                seller = self.session.query(User).filter_by(id=product.user_id).first()
                products_list.append({
                    'id': product.id,
                    'name': product.name,
                    'description': product.description,
                    'price': float(product.price),
                    'quantity': product.quantity,
                    'tag': product.tag,
                    'condition': product.condition or '九成新',
                    'image': product.image,
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
    
    @tornado.gen.coroutine
    def get(self):
        """获取聊天会话列表"""
        from models.friendship import Friendship
        
        user_id_str = self._get_user_id()
        if not user_id_str:
            self.set_status(401)
            self.write(json.dumps({'success': False, 'error': '请先登录'}))
            return
        
        user_id = int(user_id_str)
        
        try:
            friendships = self.session.query(Friendship).filter_by(user_id=user_id).all()
            
            conversations = []
            for friendship in friendships:
                friend = self.session.query(User).filter_by(id=friendship.friend_id).first()
                if not friend:
                    continue
                
                last_message = yield self.mongo.chat_messages.find_one(
                    {
                        "$or": [
                            {"from_user_id": user_id, "to_user_id": friendship.friend_id},
                            {"from_user_id": friendship.friend_id, "to_user_id": user_id}
                        ]
                    },
                    sort=[("timestamp", -1)]
                )
                
                unread_count = yield self.mongo.chat_messages.count_documents({
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
                            last_message_time = ts.strftime("%Y-%m-%d %H:%M")
                        else:
                            last_message_time = str(ts)
                
                conversations.append({
                    "id": friendship.friend_id,
                    "friend_id": friendship.friend_id,
                    "username": friend.username,
                    "room_number": friend.room_number or "未设置",
                    "avatar": friend.wechat_avatar or "",
                    "last_message": last_message_content[:50] if last_message_content else "暂无消息",
                    "last_time": last_message_time,
                    "unread_count": unread_count
                })
            
            conversations.sort(key=lambda x: x.get("last_time", ""), reverse=True)
            
            self.write(json.dumps(conversations))
            
        except Exception as e:
            logging.error(f"获取聊天列表异常: {e}")
            self.write(json.dumps([]))
    
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
                # 相对时间计算
                import datetime
                from pytz import timezone
                
                # 获取北京时间
                beijing_tz = timezone('Asia/Shanghai')
                now = datetime.datetime.now(beijing_tz)
                upload_time = product.upload_time
                
                # 将upload_time转换为北京时区
                if upload_time.tzinfo is None:
                    upload_time = beijing_tz.localize(upload_time)
                else:
                    upload_time = upload_time.astimezone(beijing_tz)
                
                delta = now - upload_time
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
                    'upload_time': product.upload_time.strftime('%Y-%m-%d %H:%M:%S') if product.upload_time else ''
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
                
                orders_data.append({
                    'id': order.id,
                    'product_id': order.product_id,
                    'product_name': order.product_name or (product.name if product else '商品已删除'),
                    'product_image': product.image if product else '',
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
                    'is_buyer': order.user_id == user_id
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
        
        try:
            data = json.loads(self.request.body)
            product_id = int(data.get('product_id'))
            quantity = int(data.get('quantity', 1))
            order_note = data.get('order_note', '')
            
            if quantity <= 0:
                self.set_status(400)
                self.write(json.dumps({'success': False, 'error': '购买数量必须大于0'}))
                return
            
            product = self.session.query(Product).filter_by(id=product_id).first()
            if not product:
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '商品不存在'}))
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
            
            self.write(json.dumps({
                'success': True,
                'order': {
                    'id': order.id,
                    'product_id': order.product_id,
                    'product_name': order.product_name or (product.name if product else '商品已删除'),
                    'product_image': product.image if product else '',
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
            
            self.write(json.dumps({'success': True, 'message': '发货成功'}))
            
        except Exception as e:
            self.session.rollback()
            logging.error(f"发货异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
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
                    'image': product.image,
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
    
    def post(self, product_id, image_id):
        """删除商品图片"""
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
                image_path = os.path.join(upload_path, image.filename)
                if os.path.exists(image_path):
                    os.remove(image_path)
                
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
        from models.product import Product
        
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
