import tornado.web
import json
import logging
from sqlalchemy.orm import sessionmaker, scoped_session
from base.base import engine
from models.product import Product

Session = sessionmaker(bind=engine)


class SearchHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = scoped_session(Session)

    def get(self):
        try:
            query = self.get_argument("q", "")
            logging.info(f"搜索查询: {query}")

            # 使用 LIKE 进行模糊搜索
            search_results = self.session.query(Product).filter(
                Product.name.like(f'%{query}%'),
                Product.status != '已删除'
            ).all()

            # 将结果转换为 JSON 格式
            results = []
            for product in search_results:
                results.append({
                    'id': product.id,
                    'name': product.name,
                    'description': product.description,
                    'price': product.price,
                    'quantity': product.quantity,
                    'tag': product.tag,
                    'image': product.image,
                    'user_id': product.user_id
                })

            self.set_header("Content-Type", "application/json")
            self.write(json.dumps(results))
        except Exception as e:
            logging.error(f"搜索处理时出错: {e}", exc_info=True)
            self.set_status(500)
            self.write(json.dumps({"error": "服务器内部错误，请稍后重试"}))

    def on_finish(self):
        self.session.remove()