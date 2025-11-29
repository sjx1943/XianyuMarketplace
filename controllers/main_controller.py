from itertools import product
from typing import Optional, Awaitable
from models.product import Product
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import desc
from base.base import engine
import tornado
from models.user import User
import urllib.parse
import tornado.web
import logging
import os

class MyStaticFileHandler(tornado.web.StaticFileHandler):
    def validate_absolute_path(self, root, absolute_path):
        # URL 解码处理，支持多层编码和中文字符
        decoded_path = urllib.parse.unquote(absolute_path)
        
        # 处理可能的双重编码或其他编码问题
        try:
            # 尝试构建完整路径
            abs_path = os.path.abspath(os.path.join(root, decoded_path))
            root_abs = os.path.abspath(root)
            
            # 检查路径是否在根目录内
            if not abs_path.startswith(root_abs):
                logging.warning(f"路径超出根目录范围: {abs_path} (根目录: {root_abs})")
                raise tornado.web.HTTPError(404)
            
            # 检查文件是否存在
            if not os.path.exists(abs_path):
                # 尝试查找相似的文件（处理编码问题、中文字符、空格等）
                if os.path.isdir(root):
                    basename = os.path.basename(decoded_path)
                    for filename in os.listdir(root):
                        # 多种匹配方式
                        if (filename.lower() == basename.lower() or 
                            filename == basename or
                            filename.replace(' ', '%20') == urllib.parse.quote(basename.encode('utf-8'))):
                            abs_path = os.path.join(root, filename)
                            logging.info(f"找到匹配文件: {abs_path}")
                            break
            
            if not os.path.exists(abs_path):
                logging.warning(f"文件不存在: {abs_path} (原始路径: {absolute_path}, 解码路径: {decoded_path})")
                raise tornado.web.HTTPError(404)
            
            if not os.path.isfile(abs_path):
                logging.warning(f"路径不是文件: {abs_path}")
                raise tornado.web.HTTPError(404)
            
            return abs_path
            
        except tornado.web.HTTPError:
            raise
        except Exception as e:
            logging.error(f"路径验证异常: {e}, 路径: {absolute_path}, 解码: {decoded_path}")
            raise tornado.web.HTTPError(404)


Session = sessionmaker(bind=engine)

class MainHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = Session()

    # def get_current_user(self):
    #     return self.get_secure_cookie("user")
    #     # 获取用户信息、推荐商品等...

    def get_current_user(self):
        try:
            user_id = self.get_secure_cookie("user_id")
            if user_id:
                user = self.session.query(User).filter_by(id=int(user_id.decode())).first()
                return user
        except Exception as e:
            logging.error(f"Error fetching current user: {e}")
        return None

    def prepare(self):
        # 游客模式：允许未登录用户浏览商品列表
        # 不再强制重定向到登录页面
        
        # 如果用户已登录，检查是否已设置房间号
        if self.current_user and not self.current_user.room_number:
            # 如果当前路径不是设置房间号页面，则跳转
            if self.request.path != "/set_room_number":
                self.redirect("/set_room_number")
                raise tornado.web.Finish()

    def get_products(self):
        # 获取商品列表，确保只显示在售且数量大于0的商品
        try:
            products = self.session.query(Product).filter(
                Product.status == '在售',
                Product.quantity > 0
            ).order_by(desc(Product.upload_time)).all()

            logging.info(f"查询到 {len(products)} 件符合条件的商品。")

            products_list = [
                {
                    'id': product.id,
                    "name": product.name,
                    "description": product.description,
                    "price": product.price,
                    "quantity": product.quantity,
                    "tag": product.tag,
                    "status": product.status,
                    "image": product.image,
                    "user_id": str(product.user_id)
                }
                for product in products
            ]
            return products_list
        except Exception as e:
            logging.error(f"获取商品列表错误: {e}")
            self.session.rollback()
            return []

    def get(self):
        # 未登录用户跳转到登录页
        if not self.current_user:
            self.redirect("/login")
            return
        
        try:
            current_user = self.get_current_user()
            user_id = str(current_user.id) if current_user else None
            username = self.get_secure_cookie("username")
            
            # 判断是否为游客模式
            is_guest = current_user is None

            products = self.get_products()
            tags = []
            for product in products:
                if product['tag'] not in tags:
                    tags.append(product['tag'])

            if username is not None:
                username = username.decode('utf-8')

            product_id = products[0]['id'] if products else None

            self.render("main_page.html",
                        username=username,
                        user_id=user_id,
                        is_guest=is_guest,
                        tags=tags,
                        products=products,
                        product_id=product_id)
        except Exception as e:
            logging.error(f"主页渲染错误: {e}")
            self.session.rollback()
            self.write("加载错误，请刷新页面")

    def on_finish(self) -> None:
        self.session.close()