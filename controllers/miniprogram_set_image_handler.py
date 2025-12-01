import tornado.web
import json
import logging
from db import Session
from models.product import Product, ProductImage


class MiniprogramProductSetImagePrimaryHandler(tornado.web.RequestHandler):
    """小程序设置商品主图接口"""
    
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
    
    def post(self, product_id, image_id):
        """设置商品主图"""
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
            
            # 验证图片存在
            image = self.session.query(ProductImage).filter_by(
                id=int(image_id), 
                product_id=int(product_id)
            ).first()
            
            if not image:
                self.set_status(404)
                self.write(json.dumps({'success': False, 'error': '图片不存在'}))
                return
            
            # 设置为主图
            product.image = image.filename
            self.session.commit()
            
            logging.info(f"已设置商品 {product_id} 的主图为 {image.filename}")
            self.write(json.dumps({
                'success': True,
                'message': '主图设置成功',
                'primary_image': image.filename
            }))
            
        except Exception as e:
            self.session.rollback()
            logging.error(f"设置主图异常: {e}")
            self.set_status(500)
            self.write(json.dumps({'success': False, 'error': str(e)}))
    
    def on_finish(self):
        self.session.close()
