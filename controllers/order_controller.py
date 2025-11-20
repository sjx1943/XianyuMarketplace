#coding=utf-8

import tornado.web
import json
import sys
import os
import datetime
from datetime import datetime as dt_class
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session, sessionmaker
from models.order import Order
from models.user import User
from models.product import Product
from base.base import engine
from sqlalchemy import desc, or_, and_, func
from motor import motor_tornado
from tornado.ioloop import IOLoop

Session = sessionmaker(bind=engine)

# MongoDB连接配置（用于存储通知）
mongo_host = os.getenv('MONGO_HOST', 'localhost')
mongo_port = int(os.getenv('MONGO_PORT', '27017'))
mongo_db = os.getenv('MONGO_DB', 'marketplace_chat')
mongo_client = motor_tornado.MotorClient(f'mongodb://{mongo_host}:{mongo_port}')
mongo_database = mongo_client[mongo_db]


class OrderHandler(tornado.web.RequestHandler):
    """订单管理处理器"""
    
    def initialize(self):
        self.session = Session()

    def get_current_user(self):
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return self.session.query(User).filter_by(id=int(user_id)).first()
        return None

    def get(self, order_id=None):
        """获取订单信息"""
        try:
            user = self.get_current_user()
            if not user:
                self.redirect("/login")
                return

            if order_id:
                # 获取特定订单详情, 使用 outerjoin 确保商品被删除的订单也能显示
                order_details = self.session.query(Order, Product, User).outerjoin(Product, Order.product_id == Product.id).join(User, Order.user_id == User.id).filter(Order.id == order_id).first()
                
                if not order_details:
                    self.write("订单不存在")
                    return
                
                order, product, buyer = order_details
                seller = None
                if order.seller_id:
                    seller = self.session.query(User).filter_by(id=order.seller_id).first()
                elif product:
                    # 降级方案：如果没有seller_id快照，从product获取
                    seller = self.session.query(User).filter_by(id=product.user_id).first()

                # 检查权限（只有买家或卖家能查看）
                can_view = False
                if user.id == buyer.id:
                    can_view = True
                elif order.seller_id and user.id == order.seller_id:
                    can_view = True
                elif seller and user.id == seller.id:
                    can_view = True

                if not can_view:
                    self.write("无权限查看此订单")
                    return
                
                self.render('order_detail.html', 
                           order=order, 
                           product=product, 
                           buyer=buyer, 
                           seller=seller,
                           current_user=user)
            else:
                # 获取用户的订单列表
                order_type = self.get_argument("type", "all")  # all, buying, selling, cancelled
                keyword = self.get_argument("keyword", "")
                date_str = self.get_argument("date", "")
                
                # 基础查询，使用 outerjoin 确保商品被删除的订单也能显示
                query = self.session.query(Order, Product, User).outerjoin(Product, Order.product_id == Product.id).join(User, Order.user_id == User.id)

                # 根据订单类型筛选
                if order_type == "buying":
                    query = query.filter(Order.user_id == user.id, Order.status != 'cancelled')
                elif order_type == "selling":
                    # 使用seller_id快照筛选，降级使用Product.user_id支持老数据
                    query = query.filter(
                        or_(
                            Order.seller_id == user.id,
                            and_(Order.seller_id == None, Product.user_id == user.id)
                        ),
                        Order.status != 'cancelled'
                    )
                elif order_type == "cancelled":
                    # 获取用户作为买家或卖家的所有已取消订单
                    query = query.filter(
                        or_(
                            Order.user_id == user.id,
                            Order.seller_id == user.id,
                            and_(Order.seller_id == None, Product.user_id == user.id)
                        ),
                        Order.status == 'cancelled'
                    )
                else: # "all"
                    # 获取用户作为买家或卖家的所有未取消订单
                    query = query.filter(
                        or_(
                            Order.user_id == user.id,
                            Order.seller_id == user.id,
                            and_(Order.seller_id == None, Product.user_id == user.id)
                        ),
                        Order.status != 'cancelled'
                    )

                # 根据关键词搜索
                if keyword:
                    query = query.filter(Product.name.ilike(f"%{keyword}%"))

                # 根据日期搜索
                if date_str:
                    try:
                        search_date = dt_class.strptime(date_str, '%Y-%m-%d').date()
                        query = query.filter(func.date(Order.created_at) == search_date)
                    except ValueError:
                        pass  # 忽略无效的日期格式

                orders_result = query.order_by(desc(Order.created_at)).all()
                
                # 获取订单相关信息
                orders_data = []
                for order, product, buyer in orders_result:
                    seller = None
                    if order.seller_id:
                        seller = self.session.query(User).filter_by(id=order.seller_id).first()
                    elif product:
                        # 降级方案：如果没有seller_id快照，从product获取
                        seller = self.session.query(User).filter_by(id=product.user_id).first()
                    
                    orders_data.append({
                        'order': order,
                        'product': product,
                        'buyer': buyer,
                        'seller': seller,
                        'is_buyer': order.user_id == user.id
                    })
                
                self.render('orders_list.html', 
                            orders=orders_data, 
                            order_type=order_type, 
                            current_user=user,
                            keyword=keyword,
                            date=date_str)
                
        except Exception as e:
            self.write(f"获取订单失败: {str(e)}")

    def post(self):
        """创建订单"""
        try:
            user = self.get_current_user()
            if not user:
                self.write(json.dumps({'success': False, 'error': '请先登录'}))
                return

            product_id = int(self.get_argument("product_id"))
            quantity = int(self.get_argument("quantity", 1))
            shipping_address = self.get_argument("shipping_address", "")
            contact_phone = self.get_argument("contact_phone", "")
            order_note = self.get_argument("order_note", "")

            # 验证商品是否存在
            product = self.session.query(Product).filter_by(id=product_id).first()
            if not product:
                self.write(json.dumps({'success': False, 'error': '商品不存在'}))
                return

            # 检查库存
            if product.quantity < quantity:
                self.write(json.dumps({'success': False, 'error': '库存不足'}))
                return

            # 不能购买自己的商品
            if product.user_id == user.id:
                self.write(json.dumps({'success': False, 'error': '不能购买自己的商品'}))
                return

            # 创建订单
            new_order = Order(
                product_id=product_id,
                user_id=user.id,
                quantity=quantity,
                product_name=product.name,  # 保存当前商品名称快照
                seller_id=product.user_id,  # 保存卖家ID快照
                order_note=order_note
            )
            
            self.session.add(new_order)
            
            # 更新商品库存（订单创建时立即减少库存）
            product.quantity -= quantity
            if product.quantity <= 0:
                product.status = "已售完"
            
            self.session.commit()
            
            # 发送通知给卖家（异步执行，不阻塞订单创建响应）
            IOLoop.current().spawn_callback(self._send_seller_notification, product, user, quantity, new_order.id)
            
            self.write(json.dumps({
                'success': True, 
                'message': '订单创建成功',
                'order_id': new_order.id
            }))
            
        except Exception as e:
            self.session.rollback()
            self.write(json.dumps({'success': False, 'error': str(e)}))

    async def _send_seller_notification(self, product, buyer, quantity, order_id):
        """发送订单通知给卖家（异步）"""
        try:
            from controllers.chat_controller import connections
            
            seller_id = product.user_id
            china_tz = datetime.timezone(datetime.timedelta(hours=8))
            timestamp = datetime.datetime.now(china_tz).strftime("%Y-%m-%d %H:%M:%S")
            
            # 构建系统通知消息
            notification_data = {
                "from_user_id": 0,  # 0表示系统消息
                "from_username": "系统通知",
                "to_user_id": seller_id,
                "message": f"🔔 您有新订单！买家 {buyer.username} 购买了您的商品《{product.name}》，数量：{quantity}件。<a href='/orders'>查看订单详情</a>",
                "product_id": product.id,
                "product_name": product.name,
                "timestamp": timestamp,
                "status": "unread",
                "type": "order_notification",  # 标记为订单通知
                "order_id": order_id
            }
            
            # 保存到MongoDB（持久化，供离线用户查看）
            try:
                await mongo_database.chat_messages.insert_one(notification_data)
                print(f"订单通知已保存到数据库")
            except Exception as db_error:
                print(f"保存通知到数据库失败: {str(db_error)}")
            
            # 如果卖家在线，立即推送通知
            if seller_id in connections:
                connections[seller_id].write_message(json.dumps(notification_data))
                print(f"成功发送实时通知给在线卖家 {seller_id}")
            else:
                print(f"卖家 {seller_id} 不在线，通知已保存，将在下次登录时显示")
                
        except Exception as notif_error:
            # 即使通知失败，订单创建也应该成功
            print(f"发送卖家通知失败: {str(notif_error)}")

    def put(self, order_id):
        """更新订单状态"""
        try:
            user = self.get_current_user()
            if not user:
                self.write(json.dumps({'success': False, 'error': '请先登录'}))
                return

            order = self.session.query(Order).filter_by(id=order_id).first()
            if not order:
                self.write(json.dumps({'success': False, 'error': '订单不存在'}))
                return

            # 只有卖家可以更新订单状态
            is_seller = False
            if order.seller_id and order.seller_id == user.id:
                is_seller = True
            elif not order.seller_id:
                # 降级方案：对于老数据，从Product表查询
                product = self.session.query(Product).filter_by(id=order.product_id).first()
                if product and product.user_id == user.id:
                    is_seller = True
            
            if not is_seller:
                self.write(json.dumps({'success': False, 'error': '只有卖家可以更新订单状态'}))
                return

            new_status = self.get_argument("status")
            # 简化流程：只支持直接发货（确认订单=发货）
            valid_statuses = ['shipped'] 
            
            if new_status not in valid_statuses:
                self.write(json.dumps({'success': False, 'error': '无效的操作'}))
                return

            # 验证订单状态转换逻辑：只有待确认的订单可以发货
            if new_status == 'shipped' and order.status != 'pending':
                self.write(json.dumps({'success': False, 'error': '只有待确认的订单才能发货'}))
                return

            order.status = new_status
            order.shipped_at = dt_class.now()  # 记录发货时间
            
            self.session.commit()
            
            self.write(json.dumps({
                'success': True, 
                'message': '订单状态更新成功',
                'new_status': new_status
            }))
            
        except Exception as e:
            self.session.rollback()
            self.write(json.dumps({'success': False, 'error': str(e)}))

    def delete(self, order_id):
        """取消订单"""
        try:
            user = self.get_current_user()
            if not user:
                self.write(json.dumps({'success': False, 'error': '请先登录'}))
                return

            order = self.session.query(Order).filter_by(id=order_id).first()
            if not order:
                self.write(json.dumps({'success': False, 'error': '订单不存在'}))
                return

            # 只有买家可以取消订单，且订单状态必须是pending
            if order.user_id != user.id:
                self.write(json.dumps({'success': False, 'error': '只有买家可以取消订单'}))
                return
                
            if order.status != 'pending':
                self.write(json.dumps({'success': False, 'error': '只能取消待确认的订单'}))
                return

            # 恢复商品库存
            product = self.session.query(Product).filter_by(id=order.product_id).first()
            if product:
                product.quantity += order.quantity
                product.status = "在售"

            order.status = 'cancelled'
            self.session.commit()
            
            self.write(json.dumps({'success': True, 'message': '订单取消成功'}))
            
        except Exception as e:
            self.session.rollback()
            self.write(json.dumps({'success': False, 'error': str(e)}))

    def on_finish(self):
        self.session.close()


class CreateOrderHandler(tornado.web.RequestHandler):
    """创建订单页面处理器"""
    
    def initialize(self):
        self.session = Session()

    def get_current_user(self):
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return self.session.query(User).filter_by(id=int(user_id)).first()
        return None

    def get(self):
        """显示创建订单页面"""
        user = self.get_current_user()
        if not user:
            self.redirect("/login")
            return

        product_id = self.get_argument("product_id")
        product = self.session.query(Product).filter_by(id=product_id).first()
        
        if not product:
            self.write("商品不存在")
            return
            
        if product.user_id == user.id:
            self.write("不能购买自己的商品")
            return

        self.render('create_order.html', product=product, user=user)

    def on_finish(self):
        self.session.close()


class ConfirmTransactionHandler(tornado.web.RequestHandler):
    """确认交易处理器"""

    def initialize(self):
        self.session = Session()

    def get_current_user(self):
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return self.session.query(User).filter_by(id=int(user_id)).first()
        return None

    def post(self, order_id):
        try:
            user = self.get_current_user()
            if not user:
                self.write(json.dumps({'success': False, 'error': '请先登录'}))
                return

            order = self.session.query(Order).filter_by(id=order_id).first()
            if not order:
                self.write(json.dumps({'success': False, 'error': '订单不存在'}))
                return

            # 只有买家可以确认收货
            if order.user_id != user.id:
                self.write(json.dumps({'success': False, 'error': '只有买家可以确认收货'}))
                return
            
            if order.status != 'shipped':
                self.write(json.dumps({'success': False, 'error': '订单状态不是已发货，无法确认收货'}))
                return

            order.status = 'completed'
            order.completed_at = dt_class.now()

            # 注意：商品库存已经在创建订单时减少，确认收货时不需要再次减少
            # 只需要更新订单状态即可
            
            self.session.commit()

            self.write(json.dumps({'success': True, 'message': '交易确认成功'}))

        except Exception as e:
            self.session.rollback()
            self.write(json.dumps({'success': False, 'error': str(e)}))
        finally:
            self.session.close()


class UnreadOrdersCountHandler(tornado.web.RequestHandler):
    """获取卖家未读订单数量（pending状态的订单）"""
    
    def initialize(self):
        self.session = Session()
    
    def get_current_user(self):
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return self.session.query(User).filter_by(id=int(user_id)).first()
        return None
    
    def get(self):
        """返回当前用户作为卖家的未读订单数量"""
        try:
            user = self.get_current_user()
            if not user:
                self.write(json.dumps({'success': False, 'count': 0}))
                return
            
            # 查询当前用户作为卖家的pending状态订单数量
            unread_count = self.session.query(Order).filter(
                Order.seller_id == user.id,
                Order.status == 'pending'
            ).count()
            
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps({
                'success': True,
                'count': unread_count
            }))
            
        except Exception as e:
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps({'success': False, 'count': 0, 'error': str(e)}))
    
    def on_finish(self):
        self.session.close()
