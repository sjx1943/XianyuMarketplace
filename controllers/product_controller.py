import tornado.web
import os
from sqlalchemy.orm import Session
from models.product import Product, ProductImage
from sqlalchemy.orm import sessionmaker, scoped_session
from base.base import engine
from models.user import User
import json
import re
from models.comment import Comment
from models.order import Order

Session = sessionmaker(bind=engine)

class ProductDetailHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = Session()

    def get_current_user(self):
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return self.session.query(User).filter_by(id=int(user_id)).first()
        return None

    def get(self, product_id):
        product = self.session.query(Product).filter_by(id=product_id).first()
        
        if not product or product.status == '已删除':
            self.set_status(404)
            self.write("商品不存在或已被删除")
            return
            
        uploader = self.session.query(User).filter_by(id=product.user_id).first()
        user = self.get_current_user()
        images = self.session.query(ProductImage).filter_by(product_id=product_id).all()

        if user:
            user_id = user.id
        else:
            user_id = None

        self.render('product_detail.html', 
                  product=product, 
                  uploader=uploader, 
                  user_id=user_id, 
                  product_id=product_id,
                  images=images)

class ProductUploadHandler(tornado.web.RequestHandler):
    def initialize(self, app_settings):
        self.app_settings = app_settings
        self.session = Session()

    def get(self):
        user_id = self.get_secure_cookie("user_id")
        if not user_id:
            self.redirect("/login")
            return
        self.render("publish_product.html", product=None)

    #上传商品...
    def post(self):
        user_id = self.get_secure_cookie("user_id")
        if not user_id:
            self.set_status(401)
            self.write({'error': '请先登录'})
            return

        try:
            name = self.get_argument("name")
            description = self.get_argument("description")
            price = float(self.get_argument("price"))
            quantity = int(self.get_argument("quantity"))
            tag = self.get_argument("tag")
            images = self.request.files.get("images", [])

            if not images:
                self.set_status(400)
                self.write({"error": "请至少上传一张图片"})
                return
            
            if len(images) > 9:
                self.set_status(400)
                self.write({"error": "最多只能上传9张图片"})
                return

            # 1. 创建商品，初始没有封面图
            new_product = Product(
                name=name,
                description=description,
                price=price,
                user_id=int(user_id.decode('utf-8')),
                tag=tag,
                image="",  # 稍后设置
                quantity=quantity,
                status="在售"
            )
            self.session.add(new_product)
            self.session.flush()  # 使用 flush 来获取 new_product.id

            # 2. 处理并保存图片
            image_filenames = []
            for i, image in enumerate(images):
                filename = f"{new_product.id}_{i}_{image['filename']}"
                filepath = os.path.join(self.app_settings["upload_path"], filename)
                with open(filepath, "wb") as f:
                    f.write(image["body"])
                
                # 将所有图片信息存入 ProductImage 表
                product_image = ProductImage(filename=filename, product_id=new_product.id)
                self.session.add(product_image)
                image_filenames.append(filename)

            # 3. 将第一张图片设为封面
            if image_filenames:
                new_product.image = image_filenames[0]

            self.session.commit()
            self.redirect(f"/product/detail/{new_product.id}")

        except Exception as e:
            self.session.rollback()
            self.set_status(500)
            self.write({'error': f'上传失败: {str(e)}'})
        finally:
            self.session.close()

    def validate_product_data(self, name, description, price, images, quantity):
            # 验证产品数据是否合法
        if name and description and price > 0 and len(images) > 0 and quantity >0:
            return True
        else:
            return False

    def on_finish(self):
        self.session.close()


class ProductEditHandler(tornado.web.RequestHandler):
    def initialize(self, app_settings):
        self.app_settings = app_settings
        self.session = Session()

    def get_current_user(self):
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            # Make sure to decode user_id and convert to int for consistent comparison
            return self.session.query(User).filter_by(id=int(user_id.decode('utf-8'))).first()
        return None

    async def get(self, product_id):
        user = self.get_current_user()
        if not user:
            self.redirect("/login")
            return

        product = self.session.query(Product).filter_by(id=product_id).first()
        
        if not product:
            self.set_status(404)
            self.write("商品不存在")
            return

        # Verify ownership
        if product.user_id != user.id:
            self.set_status(403)
            self.write("您没有权限编辑此商品")
            return

        # 获取商品的图片
        images = self.session.query(ProductImage).filter_by(product_id=product_id).all()

        self.render("publish_product.html", product=product, images=images)

    async def post(self, product_id):
        user = self.get_current_user()
        if not user:
            self.set_status(401)
            self.write(json.dumps({'error': '请先登录'}))
            return

        product = self.session.query(Product).filter_by(id=product_id).first()
        if not product:
            self.set_status(404)
            self.write(json.dumps({'error': '商品不存在'}))
            return

        if product.user_id != user.id:
            self.set_status(403)
            self.write(json.dumps({'error': '您没有权限编辑此商品'}))
            return

        try:
            # 1. 更新商品文本信息
            product.name = self.get_argument("name")
            product.description = self.get_argument("description")
            product.price = float(self.get_argument("price"))
            product.quantity = int(self.get_argument("quantity"))
            product.tag = self.get_argument("tag")

            # 2. 处理图片删除
            delete_ids = self.get_arguments("delete_images")
            if delete_ids:
                # 查询要删除的图片对象
                images_to_delete = self.session.query(ProductImage).filter(ProductImage.id.in_([int(id) for id in delete_ids])).all()
                
                is_cover_deleted = False
                for img in images_to_delete:
                    # 检查删除的是否是封面图
                    if product.image == img.filename:
                        is_cover_deleted = True

                    # 从文件系统删除
                    image_path = os.path.join(self.app_settings["upload_path"], img.filename)
                    if os.path.exists(image_path):
                        os.remove(image_path)
                    
                    # 从数据库删除
                    self.session.delete(img)
                
                # 如果封面被删了，需要重新指定一个
                if is_cover_deleted:
                    remaining_image = self.session.query(ProductImage).filter(
                        ProductImage.product_id == product.id,
                        ~ProductImage.id.in_([int(id) for id in delete_ids])
                    ).first()
                    
                    if remaining_image:
                        product.image = remaining_image.filename
                    else:
                        product.image = "" # 没有剩余图片了

            # 3. 处理新上传的图片
            new_images = self.request.files.get("images", [])
            if new_images:
                # 获取当前最大索引，以避免文件名冲突
                last_image = self.session.query(ProductImage).filter_by(product_id=product.id).order_by(ProductImage.id.desc()).first()
                start_index = 0
                if last_image and '_' in last_image.filename:
                    try:
                        # 从 "productid_index_filename" 中解析出 index
                        start_index = int(last_image.filename.split('_')[1]) + 1
                    except (ValueError, IndexError):
                        start_index = self.session.query(ProductImage).filter_by(product_id=product.id).count()

                for i, image in enumerate(new_images, start=start_index):
                    filename = f"{product.id}_{i}_{image['filename']}"
                    filepath = os.path.join(self.app_settings["upload_path"], filename)
                    with open(filepath, "wb") as f:
                        f.write(image["body"])
                    
                    product_image = ProductImage(filename=filename, product_id=product.id)
                    self.session.add(product_image)

                # 如果之前没有封面图，将新上传的第一张设为封面
                if not product.image:
                    first_new_image = self.session.query(ProductImage).filter_by(product_id=product.id).first()
                    if first_new_image:
                        product.image = first_new_image.filename


            self.session.commit()
            self.redirect(f"/product/detail/{product.id}")

        except Exception as e:
            self.session.rollback()
            self.set_status(500)
            self.write(json.dumps({'error': f'更新失败: {str(e)}'}))
        finally:
            self.session.close()


class ProductListHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = scoped_session(Session)

    def get(self):
        tags = self.get_arguments("tag")
        query = self.session.query(Product).filter(
            Product.status == '在售',
            Product.quantity > 0
        )
        if tags and 'all' not in tags:
            query = query.filter(Product.tag.in_(tags))
        
        products = query.all()

        products_list = [
            {
                'id': product.id,
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "tag": product.tag,
                "image": product.image,
                "quantity": product.quantity,
                "user_id": product.user_id
            }
            for product in products
        ]
        self.write(json.dumps(products_list))


    def on_finish(self):
        self.session.remove()


class HomePageHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = scoped_session(Session)

    def get(self):
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            user_id = user_id.decode('utf-8')
            user = self.session.query(User).filter_by(id=user_id).first()
            
            # 获取用户的所有商品
            all_products = self.session.query(Product).filter(
                Product.user_id == user_id
            ).order_by(Product.upload_time.desc()).all()

            self.render("home_page.html", 
                        products=all_products, 
                        username=user.username, 
                        user_id=user_id)
        else:
            self.redirect("/login")

    def on_finish(self):
        self.session.remove()

class ElseHomePageHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = scoped_session(Session)

    def get(self):
        user_id = self.get_argument("user_id", None)
        if user_id is None:
            self.write("User ID is required")
            return

        try:
            user_id = int(user_id)
            user = self.session.query(User).filter_by(id=user_id).first()
            if not user:
                self.write("User not found")
                return

            # 获取当前登录用户ID
            current_user_id_val = None
            current_user_cookie = self.get_secure_cookie("user_id")
            if current_user_cookie:
                current_user_id_val = int(current_user_cookie)

            products = self.session.query(Product).filter_by(user_id=user_id).all()

            self.render("else_home_page.html",
                        products=products,
                        username=user.username,
                        user_id=user_id,
                        current_user_id=current_user_id_val
                        )

        except ValueError:
            self.write("Invalid User ID format")
        except Exception as e:
            self.write(f"Error: {str(e)}")
        finally:
            self.session.remove()


class UpdateProductStatusHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = scoped_session(Session)

    def get_current_user(self):
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return self.session.query(User).filter_by(id=int(user_id)).first()
        return None

    def post(self, product_id):
        try:
            user = self.get_current_user()
            if not user:
                self.write(json.dumps({'success': False, 'error': '请先登录'}))
                return

            product = self.session.query(Product).filter_by(id=product_id).first()
            if not product:
                self.write(json.dumps({'success': False, 'error': '商品不存在'}))
                return

            if product.user_id != user.id:
                self.write(json.dumps({'success': False, 'error': '您没有权限修改此商品'}))
                return

            data = json.loads(self.request.body)
            new_status = data.get("status")
            new_quantity = data.get("quantity")

            if new_status not in ["在售", "已下架"]:
                self.write(json.dumps({'success': False, 'error': '无效的商品状态'}))
                return

            # 如果是重新上架，必须确保数量大于0
            if new_status == "在售":
                if new_quantity is None:
                    # 如果前端没有传递数量，就检查现有数量
                    if product.quantity <= 0:
                        self.write(json.dumps({'success': False, 'error': '商品数量为0，请先更新数量再上架'}))
                        return
                elif int(new_quantity) <= 0:
                    self.write(json.dumps({'success': False, 'error': '上架失败，商品数量必须大于0'}))
                    return
                else:
                    product.quantity = int(new_quantity)

            product.status = new_status
            self.session.commit()
            self.write(json.dumps({'success': True, 'message': '商品状态更新成功'}))

        except Exception as e:
            self.session.rollback()
            self.write(json.dumps({'success': False, 'error': str(e)}))
        finally:
            self.session.remove()


class DeleteProductHandler(tornado.web.RequestHandler):
    """软删除商品处理器"""
    def initialize(self):
        self.session = Session()

    def get_current_user(self):
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return self.session.query(User).filter_by(id=int(user_id)).first()
        return None

    def post(self, product_id):
        try:
            user = self.get_current_user()
            if not user:
                self.write(json.dumps({'success': False, 'error': '请先登录'}))
                return

            # 检查是否存在未完成的关联订单
            uncompleted_order = self.session.query(Order).filter(
                Order.product_id == product_id,
                Order.status.notin_(['已完成', '已取消'])
            ).first()

            if uncompleted_order:
                self.write(json.dumps({'success': False, 'error': '操作失败，该商品尚有关联的未完成订单。'}))
                return

            product = self.session.query(Product).filter_by(id=product_id, user_id=user.id).first()
            if product:
                product.status = '已删除'
                self.session.commit()
                self.write(json.dumps({'success': True}))
            else:
                self.write(json.dumps({'success': False, 'error': '商品不存在或权限不足'}))

        except Exception as e:
            self.session.rollback()
            self.write(json.dumps({'success': False, 'error': str(e)}))
        finally:
            self.session.close()

class PhysicalDeleteProductHandler(tornado.web.RequestHandler):
    """
    物理删除商品处理器（高风险操作）
    """
    def initialize(self, app_settings):
        self.app_settings = app_settings
        self.session = Session()

    def get_current_user(self):
        # 在实际应用中，这里应该增加管理员权限校验
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return self.session.query(User).filter_by(id=int(user_id)).first()
        return None

    def post(self, product_id):
        try:
            user = self.get_current_user()
            # 增加管理员验证，只允许特定用户访问
            if not user or user.username != 'sjx1943':
                self.set_status(403)
                self.write(json.dumps({'success': False, 'error': '权限不足'}))
                return

            product = self.session.query(Product).filter_by(id=product_id).first()
            if not product:
                self.write(json.dumps({'success': False, 'error': '商品不存在'}))
                return

            # 确保只有软删除状态的商品才能被物理删除
            if product.status != '已删除':
                self.write(json.dumps({'success': False, 'error': '操作失败，该商品不处于“已删除”状态。'}))
                return

            # 在删除商品前，解除其与所有订单的关联
            self.session.query(Order).filter_by(product_id=product_id).update({"product_id": None})

            # 删除商品图片
            images = self.session.query(ProductImage).filter_by(product_id=product_id).all()
            for image in images:
                try:
                    image_path = os.path.join(self.settings['upload_path'], image.image_url)
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except Exception as e:
                    print(f"删除图片失败: {e}") # 记录日志
            
            # 删除商品和关联图片记录
            self.session.query(ProductImage).filter_by(product_id=product_id).delete()
            self.session.delete(product)
            self.session.commit()
            self.write(json.dumps({'success': True}))

        except Exception as e:
            self.session.rollback()
            self.write(json.dumps({'success': False, 'error': f'操作失败: {str(e)}'}))
        finally:
            self.session.close()

class AdminDashboardHandler(tornado.web.RequestHandler):
    """管理员仪表盘处理器"""
    def initialize(self):
        self.session = Session()

    def get_current_user(self):
        # 在实际应用中，这里应该增加管理员权限校验
        user_id = self.get_secure_cookie("user_id")
        if user_id:
            return self.session.query(User).filter_by(id=int(user_id)).first()
        return None

    def get(self):
        user = self.get_current_user()
        # 增加管理员验证，只允许特定用户访问
        if not user or user.username != 'sjx1943':
            self.set_header('Content-Type', 'text/html; charset=UTF-8')
            self.write("<script>alert('暂无相关权限'); window.history.back();</script>")
            return
        
        deleted_products = self.session.query(Product).filter_by(status='已删除').all()
        self.render("admin_dashboard.html", products=deleted_products)

    def on_finish(self):
        self.session.close()