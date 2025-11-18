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
from controllers.auth_controller import LoginHandler, RegisterHandler, ForgotPasswordHandler, ResetPasswordHandler, LogoutHandler, SetRoomNumberHandler, Loginmodule, Registmodule, Forgotmodule
from controllers.phone_auth_controller import PhoneLoginHandler, SendCodeHandler
from controllers.product_controller import ProductUploadHandler, HomePageHandler, ProductDetailHandler, ProductListHandler, ElseHomePageHandler, UpdateProductStatusHandler, DeleteProductHandler, PhysicalDeleteProductHandler, AdminDashboardHandler, ProductEditHandler
from controllers.admin_controller import AdminLoginHandler, AdminDashboardHandler as NewAdminDashboardHandler, AdminUserManagementHandler, AdminProductManagementHandler, AdminOrderManagementHandler, AdminOrderDetailHandler
from controllers.chat_controller import ChatWebSocketHandler, ChatHandler, MessageAPIHandler, SendMessageAPIHandler, MarkMessagesReadHandler, DeleteMessagesHandler, UnreadCountHandler
from controllers.friend_profile_controller import FriendProfileHandler, DeleteFriendHandler, InitiateChatHandler, BlockFriendHandler
from controllers.search_controller import SearchHandler
from controllers.comment_controller import CommentHandler, ProductRatingHandler
from controllers.order_controller import OrderHandler, CreateOrderHandler, ConfirmTransactionHandler
from motor import motor_tornado
import redis
from models.friendship import Friendship
from models.user import User

# Health Check Handler for deployment
class HealthCheckHandler(RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.write({"status": "ok"})

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

    # 优先使用MONGODB_URI环境变量（MongoDB Atlas），否则使用本地配置
    mongodb_uri = os.environ.get('MONGODB_URI')
    if mongodb_uri:
        # 使用MongoDB Atlas连接字符串
        # 如果URI中包含数据库名，使用get_default_database()
        # 否则使用chat_db作为默认数据库
        mongo_client = motor_tornado.MotorClient(mongodb_uri)
        try:
            mongo = mongo_client.get_default_database()
        except Exception:
            # 如果URI中没有指定数据库，使用chat_db
            mongo = mongo_client['chat_db']
    else:
        # 使用本地MongoDB配置
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
        (r"/health", HealthCheckHandler),
        (r"/", MainHandler),
        (r"/main", MainHandler),
        (r"/home_page", HomePageHandler),
        (r"/profile/([0-9]+)", FriendProfileHandler, dict(mongo=mongo)),

        (r"/login", LoginHandler),
        (r"/logout", LogoutHandler),
        (r"/register", RegisterHandler),
        (r"/regist", RegisterHandler),
        (r"/set_room_number", SetRoomNumberHandler),
        (r"/forgot_password", ForgotPasswordHandler),
        (r"/forgot", ForgotPasswordHandler),
        (r"/reset_password", ResetPasswordHandler),
        (r"/reset", ResetPasswordHandler),
        
        # 手机号登录
        (r"/phone_login", PhoneLoginHandler),
        (r"/api/send_code", SendCodeHandler),
        
        # 管理员路由
        (r"/admin/login", AdminLoginHandler),
        (r"/admin/dashboard", NewAdminDashboardHandler),
        (r"/admin/users", AdminUserManagementHandler),
        (r"/admin/products", AdminProductManagementHandler),
        (r"/admin/orders", AdminOrderManagementHandler),
        (r"/admin/order/([0-9]+)", AdminOrderDetailHandler),
        
        (r"/product/upload", ProductUploadHandler, dict(app_settings=settings)),
        (r"/product/edit/([0-9]+)", ProductEditHandler, dict(app_settings=settings)),
        (r"/product_list", ProductListHandler),
        (r"/product/detail/([0-9]+)", ProductDetailHandler),
        
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
    parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
    args = parser.parse_args()
    
    app = make_app()
    # Bind to 0.0.0.0 for Autoscale deployments
    app.listen(args.port, address="0.0.0.0")
    print(f"后端已在端口 {args.port} 启动,可通过远程开发工具运行服务")
    tornado.ioloop.IOLoop.current().start()
