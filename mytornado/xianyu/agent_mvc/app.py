import sys
import os
import configparser
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import logging_config

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import tornado.ioloop
from tornado.web import Application, RequestHandler, UIModule, StaticFileHandler
# from controllers.search_controller import AIQueryHandler
from controllers.main_controller import MainHandler, MyStaticFileHandler
# from controllers.message_details_controller import MessageDetailsHandler
from controllers.auth_controller import LoginHandler, RegisterHandler, ForgotPasswordHandler, ResetPasswordHandler, Loginmodule, Registmodule, Forgotmodule
from controllers.product_controller import ProductUploadHandler, HomePageHandler, ProductDetailHandler, ProductListHandler, ElseHomePageHandler, UpdateProductStatusHandler, DeleteProductHandler, PhysicalDeleteProductHandler, AdminDashboardHandler, ProductEditHandler
from controllers.chat_controller import ChatWebSocketHandler, ChatHandler, MessageAPIHandler, SendMessageAPIHandler, MarkMessagesReadHandler, DeleteMessagesHandler, UnreadCountHandler
from controllers.friend_profile_controller import FriendProfileHandler, DeleteFriendHandler, InitiateChatHandler, BlockFriendHandler
from controllers.search_controller import SearchHandler
from controllers.comment_controller import CommentHandler, ProductRatingHandler
from controllers.order_controller import OrderHandler, CreateOrderHandler, ConfirmTransactionHandler
from motor import motor_tornado
import redis
from models.friendship import Friendship
from models.user import User

# 404 Handler
class NotFoundHandler(RequestHandler):
    def prepare(self):
        self.set_status(404)
        self.render("404.html")

settings = {
    'static_path': os.path.join(os.path.dirname(__file__), "mystatics"),
    'template_path': os.path.join(os.path.dirname(__file__), "templates"),
    'upload_path': os.path.join(os.path.dirname(__file__), "mystatics/images"),
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    "login_url": "/login",
    'cookie_secret': 'sjxxxx',
    'xsrf_cookies': True
}

def make_app():
    # 读取配置文件
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))

    # 优先从环境变量获取MongoDB连接信息，否则从配置文件读取
    mongo_host = os.environ.get('MONGODB_HOST', config.get('mongodb', 'host'))
    mongo_port = int(os.environ.get('MONGODB_PORT', config.getint('mongodb', 'port')))
    mongo_db = os.environ.get('MONGODB_DATABASE', config.get('mongodb', 'database'))

    mongo = motor_tornado.MotorClient(f'mongodb://{mongo_host}:{mongo_port}')[mongo_db]

    # 为 chat_messages 集合创建索引
    async def create_indexes():
        await mongo.chat_messages.create_index([("from_user_id", 1), ("to_user_id", 1), ("timestamp", 1)])
    
    tornado.ioloop.IOLoop.current().add_callback(create_indexes)

    redis_client = redis.StrictRedis()

    return Application([
        (r"/", MainHandler),
        (r"/main", MainHandler),
        (r"/home_page", HomePageHandler),
        (r"/profile/([0-9]+)", FriendProfileHandler, dict(mongo=mongo)),

        (r"/login", LoginHandler),
        (r"/register", RegisterHandler),
        (r"/forgot_password", ForgotPasswordHandler),
        (r"/reset_password", ResetPasswordHandler),
        (r"/product/upload", ProductUploadHandler, dict(app_settings=settings)),
        (r"/product/edit/([0-9]+)", ProductEditHandler, dict(app_settings=settings)),
        (r"/product_list", ProductListHandler),
        (r"/product/detail/([0-9]+)", ProductDetailHandler),
        
        # 管理员面板
        (r"/admin/dashboard", AdminDashboardHandler),
        
        # 评价相关路由
        (r"/api/comments", CommentHandler),
        (r"/api/comments/([0-9]+)", CommentHandler),
        (r"/api/product/([0-9]+)/rating", ProductRatingHandler),
        
        # 订单相关路由
        (r"/orders", OrderHandler),
        (r"/orders/([0-9]+)", OrderHandler),
        (r"/create_order", CreateOrderHandler),
        (r"/api/order/([0-9]+)/confirm", ConfirmTransactionHandler),

        # 商品状态相关路由
        (r"/api/product/([0-9]+)/status", UpdateProductStatusHandler),
        (r"/api/product/([0-9]+)/delete", DeleteProductHandler),
        (r"/api/admin/product/([0-9]+)/physical_delete", PhysicalDeleteProductHandler, dict(app_settings=settings)),
        
        # 聊天和消息相关路由
        (r"/api/messages", MessageAPIHandler, dict(mongo=mongo)),
        (r"/api/search", SearchHandler),
        (r"/api/send_message", SendMessageAPIHandler, dict(mongo=mongo)),
        (r"/chat_room", ChatHandler, dict(mongo=mongo)),
        (r"/ws/chat_room", ChatWebSocketHandler, dict(mongo=mongo)),
        (r"/initiate_chat", InitiateChatHandler, dict(mongo=mongo)),
        (r"/api/add_friend", FriendProfileHandler, dict(mongo=mongo)),
        (r"/api/delete_friend", DeleteFriendHandler,dict(mongo=mongo)),
        (r"/api/block_friend", BlockFriendHandler, dict(mongo=mongo)),
        (r"/api/delete_messages", DeleteMessagesHandler, dict(mongo=mongo)),
        (r"/api/mark_messages_read", MarkMessagesReadHandler, dict(mongo=mongo)),
        (r"/api/unread_count", UnreadCountHandler, dict(mongo=mongo)),
        (r"/static/(.*)", MyStaticFileHandler, {"path": settings['static_path']}),
    ],
        ui_modules={'loginmodule': Loginmodule,
                    'registmodule': Registmodule,
                    'forgotmodule': Forgotmodule
                    }, 
        debug = True,
        default_handler_class=NotFoundHandler,
        **settings
    )


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Tornado Application')
    parser.add_argument('--port', type=int, default=9000, help='Port to listen on')
    args = parser.parse_args()
    
    app = make_app()
    app.listen(args.port)
    print(f"后端已在端口 {args.port} 启动,可通过远程开发工具运行服务")
    tornado.ioloop.IOLoop.current().start()
