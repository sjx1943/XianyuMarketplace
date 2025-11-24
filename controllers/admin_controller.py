import tornado.web
import json
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func, or_
from base.base import engine
from models.user import User
from models.product import Product
from models.order import Order
import hashlib

Session = sessionmaker(bind=engine)

class AdminBaseHandler(tornado.web.RequestHandler):
    """管理员基础Handler，验证管理员权限"""
    
    def initialize(self):
        self.session = Session()
    
    def on_finish(self):
        if hasattr(self, 'session'):
            self.session.close()
    
    def prepare(self):
        """检查管理员权限"""
        user_id_cookie = self.get_secure_cookie("user_id")
        if not user_id_cookie:
            self.redirect("/admin/login")
            self.finish()
            raise tornado.web.Finish()
        
        user_id = int(user_id_cookie.decode("utf-8"))
        user = self.session.query(User).filter_by(id=user_id).first()
        
        if not user or user.is_admin != 1:
            self.clear_all_cookies()
            self.redirect("/admin/login?error=unauthorized")
            self.finish()
            raise tornado.web.Finish()
        
        self.current_admin = user

class AdminLoginHandler(tornado.web.RequestHandler):
    """管理员登录"""
    
    def initialize(self):
        self.session = Session()
    
    def on_finish(self):
        if hasattr(self, 'session'):
            self.session.close()
    
    def get(self):
        """渲染管理员登录页面"""
        error = self.get_argument("error", None)
        self.render('admin_login.html', error=error)
    
    async def post(self):
        """处理管理员登录"""
        self.set_header('Content-Type', 'application/json')
        try:
            data = json.loads(self.request.body)
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            
            if not username or not password:
                self.write({'success': False, 'message': '请输入用户名和密码'})
                return
            
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            
            user = self.session.query(User).filter(
                or_(
                    User.username == username,
                    User.email == username
                )
            ).first()
            
            if not user or user.password != hashed_password:
                self.write({'success': False, 'message': '用户名或密码错误'})
                return
            
            if user.is_admin != 1:
                self.write({'success': False, 'message': '您没有管理员权限'})
                return
            
            self.set_secure_cookie("user_id", str(user.id))
            self.set_secure_cookie("username", user.username)
            self.set_secure_cookie("is_admin", "1")
            
            self.write({
                'success': True,
                'message': '登录成功',
                'redirect_url': '/admin/dashboard'
            })
            
        except Exception as e:
            logging.error(f"管理员登录错误: {e}")
            self.write({'success': False, 'message': '登录失败，请重试'})

class AdminDashboardHandler(AdminBaseHandler):
    """管理员控制面板"""
    
    async def get(self):
        """渲染Dashboard"""
        try:
            total_users = self.session.query(func.count(User.id)).scalar()
            active_users = self.session.query(func.count(User.id)).filter(User.is_active == 1).scalar()
            
            total_products = self.session.query(func.count(Product.id)).filter(Product.status != '已删除').scalar()
            on_sale_products = self.session.query(func.count(Product.id)).filter(Product.status == '在售').scalar()
            
            total_orders = self.session.query(func.count(Order.id)).scalar()
            pending_orders = self.session.query(func.count(Order.id)).filter(Order.status == 'pending').scalar()
            
            recent_users = self.session.query(User).order_by(User.id.desc()).limit(10).all()
            recent_products = self.session.query(Product).filter(Product.status != '已删除').order_by(Product.id.desc()).limit(10).all()
            recent_orders = self.session.query(Order).order_by(Order.id.desc()).limit(10).all()
            
            self.render('admin_dashboard.html',
                       admin=self.current_admin,
                       stats={
                           'total_users': total_users,
                           'active_users': active_users,
                           'total_products': total_products,
                           'on_sale_products': on_sale_products,
                           'total_orders': total_orders,
                           'pending_orders': pending_orders
                       },
                       recent_users=recent_users,
                       recent_products=recent_products,
                       recent_orders=recent_orders)
            
        except Exception as e:
            logging.error(f"Dashboard加载错误: {e}")
            self.write("加载错误，请刷新页面")

class AdminUserManagementHandler(AdminBaseHandler):
    """用户管理"""
    
    async def get(self):
        """获取所有用户"""
        try:
            page = max(1, int(self.get_argument("page", 1)))
            search_keyword = self.get_argument("search", "").strip()
            per_page = 20
            
            query = self.session.query(User)
            if search_keyword:
                query = query.filter(
                    or_(
                        User.username.ilike(f'%{search_keyword}%'),
                        User.email.ilike(f'%{search_keyword}%'),
                        User.room_number.ilike(f'%{search_keyword}%')
                    )
                )
            
            total = query.count()
            total_pages = max(1, (total + per_page - 1) // per_page) if total > 0 else 1
            page = min(page, total_pages)
            offset = (page - 1) * per_page
            
            users = query.offset(offset).limit(per_page).all()
            
            self.render('admin_users.html',
                       admin=self.current_admin,
                       users=users,
                       page=page,
                       total_pages=total_pages,
                       search_keyword=search_keyword)
            
        except Exception as e:
            logging.error(f"用户管理加载错误: {e}")
            self.write("加载错误")
    
    async def post(self):
        """用户操作（禁用/启用/删除）"""
        self.set_header('Content-Type', 'application/json')
        try:
            data = json.loads(self.request.body)
            action = data.get('action')
            user_id = data.get('user_id')
            
            if not action or not user_id:
                self.write({'success': False, 'message': '参数错误'})
                return
            
            user = self.session.query(User).filter_by(id=user_id).first()
            if not user:
                self.write({'success': False, 'message': '用户不存在'})
                return
            
            if action == 'toggle_active':
                user.is_active = 1 - user.is_active
                status = "启用" if user.is_active else "禁用"
                self.session.commit()
                self.write({'success': True, 'message': f'用户已{status}'})
            
            elif action == 'delete':
                self.session.delete(user)
                self.session.commit()
                self.write({'success': True, 'message': '用户已删除'})
            
            else:
                self.write({'success': False, 'message': '未知操作'})
                
        except Exception as e:
            logging.error(f"用户操作错误: {e}")
            self.session.rollback()
            self.write({'success': False, 'message': f'操作失败: {str(e)}'})
            return

class AdminProductManagementHandler(AdminBaseHandler):
    """商品管理"""
    
    async def get(self):
        """获取所有商品"""
        try:
            page = max(1, int(self.get_argument("page", 1)))
            status_filter = self.get_argument("status", "all")
            per_page = 20
            
            query = self.session.query(Product)
            if status_filter != "all":
                query = query.filter(Product.status == status_filter)
            else:
                query = query.filter(Product.status != '已删除')
            
            total = query.count()
            total_pages = max(1, (total + per_page - 1) // per_page) if total > 0 else 1
            page = min(page, total_pages)
            offset = (page - 1) * per_page
            
            products = query.offset(offset).limit(per_page).all()
            
            self.render('admin_products.html',
                       admin=self.current_admin,
                       products=products,
                       page=page,
                       status_filter=status_filter,
                       total_pages=total_pages)
            
        except Exception as e:
            logging.error(f"商品管理加载错误: {e}")
            self.write("加载错误")
    
    async def post(self):
        """商品操作（删除/修改状态）"""
        self.set_header('Content-Type', 'application/json')
        try:
            data = json.loads(self.request.body)
            action = data.get('action')
            product_id = data.get('product_id')
            
            if not action or not product_id:
                self.write({'success': False, 'message': '参数错误'})
                return
            
            product = self.session.query(Product).filter_by(id=product_id).first()
            if not product:
                self.write({'success': False, 'message': '商品不存在'})
                return
            
            if action == 'delete':
                product.status = '已删除'
                self.session.commit()
                self.write({'success': True, 'message': '商品已删除'})
            
            elif action == 'restore':
                product.status = '在售'
                self.session.commit()
                self.write({'success': True, 'message': '商品已恢复'})
            
            else:
                self.write({'success': False, 'message': '未知操作'})
                
        except Exception as e:
            logging.error(f"商品操作错误: {e}")
            self.session.rollback()
            self.write({'success': False, 'message': f'操作失败: {str(e)}'})
            return

class AdminOrderManagementHandler(AdminBaseHandler):
    """订单管理"""
    
    async def get(self):
        """获取所有订单"""
        try:
            page = max(1, int(self.get_argument("page", 1)))
            status_filter = self.get_argument("status", "all")
            per_page = 20
            
            query = self.session.query(Order)
            if status_filter != "all":
                query = query.filter(Order.status == status_filter)
            
            total = query.count()
            total_pages = max(1, (total + per_page - 1) // per_page) if total > 0 else 1
            page = min(page, total_pages)
            offset = (page - 1) * per_page
            
            orders = query.order_by(Order.id.desc()).offset(offset).limit(per_page).all()
            
            # 统计1年以上的订单数量
            from datetime import datetime, timedelta
            one_year_ago = datetime.now() - timedelta(days=365)
            old_orders_count = self.session.query(func.count(Order.id)).filter(Order.created_at <= one_year_ago).scalar()
            
            self.render('admin_orders.html',
                       admin=self.current_admin,
                       orders=orders,
                       page=page,
                       status_filter=status_filter,
                       total_pages=total_pages,
                       old_orders_count=old_orders_count)
            
        except Exception as e:
            logging.error(f"订单管理加载错误: {e}")
            self.write("加载错误")
    
    async def post(self):
        """处理订单操作（删除等）"""
        self.set_header('Content-Type', 'application/json')
        try:
            data = json.loads(self.request.body)
            action = data.get('action')
            order_id = data.get('order_id')
            
            if action == 'delete' and order_id:
                # 删除单个订单
                order = self.session.query(Order).filter_by(id=order_id).first()
                if not order:
                    self.write({'success': False, 'message': '订单不存在'})
                    return
                
                self.session.delete(order)
                self.session.commit()
                self.write({'success': True, 'message': '订单已删除'})
                
            elif action == 'delete_old_orders':
                # 删除1年以上的订单
                from datetime import datetime, timedelta
                one_year_ago = datetime.now() - timedelta(days=365)
                old_orders = self.session.query(Order).filter(Order.created_at <= one_year_ago).all()
                deleted_count = len(old_orders)
                
                for order in old_orders:
                    self.session.delete(order)
                
                self.session.commit()
                self.write({
                    'success': True,
                    'message': f'已删除 {deleted_count} 个订单',
                    'deleted_count': deleted_count
                })
            else:
                self.write({'success': False, 'message': '无效操作'})
                
        except Exception as e:
            logging.error(f"订单操作错误: {e}")
            self.session.rollback()
            self.write({'success': False, 'message': f'操作失败: {str(e)}'})

class AdminOrderDetailHandler(AdminBaseHandler):
    """管理员订单详情查看"""
    
    async def get(self, order_id):
        """获取订单详情"""
        try:
            order = self.session.query(Order).filter_by(id=int(order_id)).first()
            if not order:
                self.write("订单不存在")
                return
            
            product = self.session.query(Product).filter_by(id=order.product_id).first()
            buyer = self.session.query(User).filter_by(id=order.user_id).first()
            
            seller = None
            if order.seller_id:
                seller = self.session.query(User).filter_by(id=order.seller_id).first()
            elif product:
                seller = self.session.query(User).filter_by(id=product.user_id).first()
            
            self.render('admin_order_detail.html',
                       admin=self.current_admin,
                       order=order,
                       product=product,
                       buyer=buyer,
                       seller=seller)
            
        except Exception as e:
            logging.error(f"订单详情加载错误: {e}")
            self.write("加载错误")
