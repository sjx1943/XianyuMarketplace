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
class MyStaticFileHandler(tornado.web.StaticFileHandler):
    def validate_absolute_path(self, root, absolute_path):
        absolute_path = urllib.parse.unquote(absolute_path)
        return super().validate_absolute_path(root, absolute_path)


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