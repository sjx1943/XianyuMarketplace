# 小程序扩展API：收藏、卖家店铺、黑名单功能
import tornado.web
import json
import logging
from sqlalchemy.orm import sessionmaker
from models.user import User
from models.product import Product, ProductImage
from models.favorite import Favorite
from models.blacklist import Blacklist
from base.base import engine
from utils.wechat_cloud_storage import convert_cloud_url, convert_image_url

Session = sessionmaker(bind=engine)
logger = logging.getLogger(__name__)

# 默认头像URL
DEFAULT_AVATAR = '/static/images/default-avatar.png'


def convert_avatar_url(avatar_url):
    """
    转换头像URL：如果是云存储格式(cloud://)，转换为临时HTTPS URL
    - 云托管环境：转换为临时HTTPS URL
    - 非云托管环境：保留原始cloud://格式（小程序可直接加载）
    """
    if not avatar_url:
        return DEFAULT_AVATAR
    
    if isinstance(avatar_url, str) and avatar_url.startswith('cloud://'):
        try:
            from utils.wechat_cloud_storage import get_is_cloud_run, convert_cloud_url
            # 非云托管环境，保留原始cloud://格式
            if not get_is_cloud_run():
                return avatar_url
            converted = convert_cloud_url(avatar_url, DEFAULT_AVATAR)
            return converted if converted else DEFAULT_AVATAR
        except Exception as e:
            logger.warning(f"转换云存储头像URL失败: {e}")
            return avatar_url  # 返回原始URL而不是默认值
    
    return avatar_url


class MiniprogramFavoriteListHandler(tornado.web.RequestHandler):
    """收藏列表API"""
    
    def check_xsrf_cookie(self):
        pass
    
    def initialize(self):
        self.session = Session()
    
    def _get_user_id(self):
        """从Cookie或Authorization头获取用户ID（与miniprogram_auth_controller一致）"""
        # 优先从Cookie获取
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return user_id.decode('utf-8') if isinstance(user_id, bytes) else user_id
        
        # 其次从Authorization头获取
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
        """获取当前用户的收藏列表"""
        try:
            user_id = self._get_user_id()
            
            if not user_id:
                self.set_status(401)
                self.write({'success': False, 'error': '未登录'})
                return
            
            favorites = self.session.query(Favorite).filter(
                Favorite.user_id == int(user_id)
            ).order_by(Favorite.created_at.desc()).all()
            
            result = []
            for fav in favorites:
                product = self.session.query(Product).filter(Product.id == fav.product_id).first()
                if product:
                    # 获取主图
                    image_url = ''
                    if product.images:
                        primary_img = next((img for img in product.images if getattr(img, 'is_primary', False)), None)
                        if primary_img:
                            image_url = primary_img.image_url if hasattr(primary_img, 'image_url') else primary_img.filename
                        elif product.images:
                            first_img = product.images[0]
                            image_url = first_img.image_url if hasattr(first_img, 'image_url') else first_img.filename
                    
                    result.append({
                        'id': product.id,
                        'name': product.name,
                        'price': str(product.price),
                        'image': image_url or '',
                        'stock': product.quantity or 0,
                        'status': product.status,
                        'favorited_at': fav.created_at.isoformat() if fav.created_at else None
                    })
            
            self.write({
                'success': True,
                'favorites': result,
                'count': len(result)
            })
        except Exception as e:
            logger.error(f"获取收藏列表失败: {e}")
            self.set_status(500)
            self.write({'success': False, 'error': str(e)})
    
    def post(self):
        """添加收藏"""
        try:
            user_id = self._get_user_id()
            
            if not user_id:
                self.set_status(401)
                self.write({'success': False, 'error': '未登录'})
                return
            
            data = json.loads(self.request.body)
            product_id = data.get('product_id')
            
            if not product_id:
                self.set_status(400)
                self.write({'success': False, 'error': '缺少物品ID'})
                return
            
            # 检查物品是否存在
            product = self.session.query(Product).filter(Product.id == product_id).first()
            if not product:
                self.set_status(404)
                self.write({'success': False, 'error': '物品不存在'})
                return
            
            # 检查是否已收藏
            existing = self.session.query(Favorite).filter(
                Favorite.user_id == int(user_id),
                Favorite.product_id == product_id
            ).first()
            
            if existing:
                self.write({'success': True, 'message': '已收藏'})
                return
            
            # 添加收藏
            favorite = Favorite(user_id=int(user_id), product_id=product_id)
            self.session.add(favorite)
            self.session.commit()
            
            self.write({'success': True, 'message': '收藏成功'})
        except Exception as e:
            self.session.rollback()
            logger.error(f"添加收藏失败: {e}")
            self.set_status(500)
            self.write({'success': False, 'error': str(e)})
    
    def on_finish(self):
        self.session.close()


class MiniprogramFavoriteHandler(tornado.web.RequestHandler):
    """收藏单项操作API"""
    
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
    
    def delete(self, product_id):
        """取消收藏"""
        try:
            user_id = self._get_user_id()
            
            if not user_id:
                self.set_status(401)
                self.write({'success': False, 'error': '未登录'})
                return
            
            favorite = self.session.query(Favorite).filter(
                Favorite.user_id == int(user_id),
                Favorite.product_id == int(product_id)
            ).first()
            
            if favorite:
                self.session.delete(favorite)
                self.session.commit()
            
            self.write({'success': True, 'message': '已取消收藏'})
        except Exception as e:
            self.session.rollback()
            logger.error(f"取消收藏失败: {e}")
            self.set_status(500)
            self.write({'success': False, 'error': str(e)})
    
    def on_finish(self):
        self.session.close()


class MiniprogramFavoriteCheckHandler(tornado.web.RequestHandler):
    """检查是否收藏API"""
    
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
    
    def get(self, product_id):
        """检查物品是否已收藏"""
        try:
            user_id = self._get_user_id()
            
            if not user_id:
                self.set_status(401)
                self.write({'success': False, 'error': '未登录'})
                return
            
            favorite = self.session.query(Favorite).filter(
                Favorite.user_id == int(user_id),
                Favorite.product_id == int(product_id)
            ).first()
            
            self.write({
                'success': True,
                'is_favorited': favorite is not None
            })
        except Exception as e:
            logger.error(f"检查收藏状态失败: {e}")
            self.set_status(500)
            self.write({'success': False, 'error': str(e)})
    
    def on_finish(self):
        self.session.close()


class MiniprogramSellerInfoHandler(tornado.web.RequestHandler):
    """卖家信息API"""
    
    def check_xsrf_cookie(self):
        pass
    
    def initialize(self):
        self.session = Session()
    
    def get(self, seller_id):
        """获取卖家信息"""
        try:
            seller = self.session.query(User).filter(User.id == int(seller_id)).first()
            
            if not seller:
                self.set_status(404)
                self.write({'success': False, 'error': '卖家不存在'})
                return
            
            self.write({
                'success': True,
                'seller': {
                    'id': seller.id,
                    'username': seller.username,
                    'wechat_nickname': seller.wechat_nickname,
                    'wechat_avatar': convert_avatar_url(seller.wechat_avatar),
                    'room_number': seller.room_number
                }
            })
        except Exception as e:
            logger.error(f"获取卖家信息失败: {e}")
            self.set_status(500)
            self.write({'success': False, 'error': str(e)})
    
    def on_finish(self):
        self.session.close()


class MiniprogramSellerProductsHandler(tornado.web.RequestHandler):
    """卖家物品列表API"""
    
    def check_xsrf_cookie(self):
        pass
    
    def initialize(self):
        self.session = Session()
    
    def get(self, seller_id):
        """获取卖家的物品列表"""
        try:
            # 只显示在售的物品(quantity > 0)
            products = self.session.query(Product).filter(
                Product.user_id == int(seller_id),
                Product.status == '在售',
                Product.quantity > 0
            ).order_by(Product.upload_time.desc()).all()
            
            result = []
            for product in products:
                # 获取主图
                image_url = ''
                if product.images:
                    primary_img = next((img for img in product.images if getattr(img, 'is_primary', False)), None)
                    if primary_img:
                        image_url = primary_img.image_url if hasattr(primary_img, 'image_url') else primary_img.filename
                    elif product.images:
                        first_img = product.images[0]
                        image_url = first_img.image_url if hasattr(first_img, 'image_url') else first_img.filename
                
                result.append({
                    'id': product.id,
                    'name': product.name,
                    'price': str(product.price),
                    'image': image_url or '',
                    'stock': product.quantity or 0
                })
            
            self.write({
                'success': True,
                'products': result,
                'count': len(result)
            })
        except Exception as e:
            logger.error(f"获取卖家物品列表失败: {e}")
            self.set_status(500)
            self.write({'success': False, 'error': str(e)})
    
    def on_finish(self):
        self.session.close()


class MiniprogramBlacklistHandler(tornado.web.RequestHandler):
    """黑名单API"""
    
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
    
    def get(self):
        """获取黑名单列表"""
        try:
            user_id = self._get_user_id()
            
            if not user_id:
                self.set_status(401)
                self.write({'success': False, 'error': '未登录'})
                return
            
            blacklist = self.session.query(Blacklist).filter(
                Blacklist.blocker_id == int(user_id)
            ).all()
            
            result = []
            for item in blacklist:
                blocked_user = self.session.query(User).filter(User.id == item.blocked_id).first()
                if blocked_user:
                    result.append({
                        'id': blocked_user.id,
                        'username': blocked_user.username,
                        'nickname': blocked_user.wechat_nickname,
                        'avatar': convert_avatar_url(blocked_user.wechat_avatar)
                    })
            
            self.write({
                'success': True,
                'blacklist': result,
                'count': len(result)
            })
        except Exception as e:
            logger.error(f"获取黑名单失败: {e}")
            self.set_status(500)
            self.write({'success': False, 'error': str(e)})
    
    def post(self):
        """添加到黑名单"""
        try:
            user_id = self._get_user_id()
            
            if not user_id:
                self.set_status(401)
                self.write({'success': False, 'error': '未登录'})
                return
            
            data = json.loads(self.request.body)
            blocked_user_id = data.get('user_id')
            
            if not blocked_user_id:
                self.set_status(400)
                self.write({'success': False, 'error': '缺少用户ID'})
                return
            
            if int(blocked_user_id) == int(user_id):
                self.set_status(400)
                self.write({'success': False, 'error': '不能拉黑自己'})
                return
            
            # 检查用户是否存在
            target_user = self.session.query(User).filter(User.id == int(blocked_user_id)).first()
            if not target_user:
                self.set_status(404)
                self.write({'success': False, 'error': '用户不存在'})
                return
            
            # 检查是否已在黑名单
            existing = self.session.query(Blacklist).filter(
                Blacklist.blocker_id == int(user_id),
                Blacklist.blocked_id == int(blocked_user_id)
            ).first()
            
            if existing:
                self.write({'success': True, 'message': '已在黑名单'})
                return
            
            # 添加到黑名单
            blacklist_item = Blacklist(blocker_id=int(user_id), blocked_id=int(blocked_user_id))
            self.session.add(blacklist_item)
            self.session.commit()
            
            self.write({'success': True, 'message': '已加入黑名单'})
        except Exception as e:
            self.session.rollback()
            logger.error(f"添加黑名单失败: {e}")
            self.set_status(500)
            self.write({'success': False, 'error': str(e)})
    
    def on_finish(self):
        self.session.close()


class MiniprogramBlacklistItemHandler(tornado.web.RequestHandler):
    """黑名单单项操作API"""
    
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
    
    def delete(self, blocked_user_id):
        """从黑名单移除"""
        try:
            user_id = self._get_user_id()
            
            if not user_id:
                self.set_status(401)
                self.write({'success': False, 'error': '未登录'})
                return
            
            blacklist_item = self.session.query(Blacklist).filter(
                Blacklist.blocker_id == int(user_id),
                Blacklist.blocked_id == int(blocked_user_id)
            ).first()
            
            if blacklist_item:
                self.session.delete(blacklist_item)
                self.session.commit()
            
            self.write({'success': True, 'message': '已移出黑名单'})
        except Exception as e:
            self.session.rollback()
            logger.error(f"移出黑名单失败: {e}")
            self.set_status(500)
            self.write({'success': False, 'error': str(e)})
    
    def on_finish(self):
        self.session.close()


class MiniprogramBlacklistCheckHandler(tornado.web.RequestHandler):
    """检查是否在黑名单API"""
    
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
    
    def get(self, blocked_user_id):
        """检查用户是否在黑名单"""
        try:
            user_id = self._get_user_id()
            
            if not user_id:
                self.set_status(401)
                self.write({'success': False, 'error': '未登录'})
                return
            
            blacklist_item = self.session.query(Blacklist).filter(
                Blacklist.blocker_id == int(user_id),
                Blacklist.blocked_id == int(blocked_user_id)
            ).first()
            
            self.write({
                'success': True,
                'is_blocked': blacklist_item is not None
            })
        except Exception as e:
            logger.error(f"检查黑名单状态失败: {e}")
            self.set_status(500)
            self.write({'success': False, 'error': str(e)})
    
    def on_finish(self):
        self.session.close()
