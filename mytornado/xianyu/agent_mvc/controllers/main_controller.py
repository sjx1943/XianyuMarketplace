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
        # self.session = Session()
        self.session = scoped_session(Session)

    # def get_current_user(self):
    #     return self.get_secure_cookie("user")
    #     # 获取用户信息、推荐商品等...

    def get_current_user(self):
        try:
            username = self.get_secure_cookie("username")
            if username:
                user = self.session.query(User).filter_by(username=username.decode()).first()
                return user
        except Exception as e:
            logging.error(f"Error fetching current user: {e}")
        return None

    def prepare(self):
        if not self.current_user:
            self.redirect("/login")
            raise tornado.web.Finish()

    def get_products(self):
        # 获取商品列表，确保只显示在售且数量大于0的商品
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

    def get(self):
    # 从当前用户对象获取user_id
        current_user = self.get_current_user()
        user_id = str(current_user.id) if current_user else None
        username = self.get_secure_cookie("username")

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
                    user_id=user_id,  # 使用从用户对象获取的user_id
                    tags=tags,
                    products=products,
                    product_id=product_id)

    def on_finish(self) -> None:
        self.session.remove()