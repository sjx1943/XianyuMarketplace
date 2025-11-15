# File: xianyu/MVC/controllers/friend_profile_controller.py
from datetime import datetime
from itertools import product
import json
import tornado.web
from sqlalchemy.orm import scoped_session, sessionmaker
from models.user import User
from models.product import Product
from models.friendship import Friendship
from base.base import engine

Session = sessionmaker(bind=engine)


from models.blacklist import Blacklist

class BlockFriendHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo
        self.session = scoped_session(Session)

    def post(self):
        try:
            data = json.loads(self.request.body)
            blocked_id = int(data.get("friend_id"))
            user_id_cookie = self.get_secure_cookie("user_id")

            if not user_id_cookie:
                self.set_status(401)
                self.write({"status": "error", "message": "请先登录"})
                return
            
            blocker_id = int(user_id_cookie.decode("utf-8"))

            # Check if the block entry already exists
            existing_block = self.session.query(Blacklist).filter_by(
                blocker_id=blocker_id,
                blocked_id=blocked_id
            ).first()

            if existing_block:
                # If it exists, unblock the user by deleting the entry
                self.session.delete(existing_block)
                message = "已取消拉黑"
            else:
                # If it doesn't exist, block the user by creating a new entry
                new_block = Blacklist(blocker_id=blocker_id, blocked_id=blocked_id)
                self.session.add(new_block)
                message = "好友已拉黑"
            
            self.session.commit()
            self.write({"status": "success", "message": message})

        except Exception as e:
            self.session.rollback()
            self.set_status(500)
            self.write({"status": "error", "message": str(e)})
        finally:
            self.session.remove()


class InitiateChatHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo
        self.session = scoped_session(Session)

    def get(self):
        try:
            seller_id = int(self.get_argument("user_id"))
            buyer_id_cookie = self.get_secure_cookie("user_id")
            if not buyer_id_cookie:
                self.redirect("/login")
                return
            
            buyer_id = int(buyer_id_cookie.decode("utf-8"))

            if seller_id == buyer_id:
                # 如果是自己的商品，可以重定向到首页或提示信息
                self.redirect("/main")
                return

            # 检查是否被拉黑
            friendship = self.session.query(Friendship).filter(
                ((Friendship.user_id == buyer_id) & (Friendship.friend_id == seller_id)) |
                ((Friendship.user_id == seller_id) & (Friendship.friend_id == buyer_id))
            ).first()

            if friendship and friendship.status == 'blocked':
                self.write("您已被对方拉黑，无法添加好友")
                return

            # 检查是否已经是好友 (A -> B)
            existing_friendship_ab = self.session.query(Friendship).filter(
                (Friendship.user_id == buyer_id) &
                (Friendship.friend_id == seller_id)
            ).first()

            if not existing_friendship_ab:
                new_friendship_ab = Friendship(user_id=buyer_id, friend_id=seller_id)
                self.session.add(new_friendship_ab)

            # 检查是否已经是好友 (B -> A)
            existing_friendship_ba = self.session.query(Friendship).filter(
                (Friendship.user_id == seller_id) &
                (Friendship.friend_id == buyer_id)
            ).first()

            if not existing_friendship_ba:
                new_friendship_ba = Friendship(user_id=seller_id, friend_id=buyer_id)
                self.session.add(new_friendship_ba)
            
            self.session.commit()

            # 重定向到聊天室，并带上好友ID以便自动打开聊天窗口
            self.redirect(f"/chat_room?friend_id={seller_id}")

        except Exception as e:
            self.session.rollback()
            self.write(f"发生错误: {e}")
        finally:
            self.session.remove()


class FriendProfileHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo  # 确保这里正确接收了mongo连接
        self.session = scoped_session(Session)

    async def post(self):
        try:
            user_id_cookie = self.get_secure_cookie("user_id")
            if not user_id_cookie:
                self.set_status(401)
                self.write({"success": False, "message": "请先登录"})
                return

            user_id = int(user_id_cookie.decode("utf-8"))
            data = json.loads(self.request.body)
            friend_id = int(data.get("friend_id"))

            # Check if a block exists in either direction
            is_blocked = self.session.query(Blacklist).filter(
                ((Blacklist.blocker_id == user_id) & (Blacklist.blocked_id == friend_id)) |
                ((Blacklist.blocker_id == friend_id) & (Blacklist.blocked_id == user_id))
            ).first()

            if is_blocked:
                self.write({"success": False, "message": "操作失败，无法添加好友"})
                return

            # 检查是否已经是好友
            existing_friendship = self.session.query(Friendship).filter(
                (Friendship.user_id == user_id) &
                (Friendship.friend_id == friend_id)
            ).first()

            if existing_friendship:
                self.write({"success": False, "message": "已经是好友"})
                return

            # 创建新的好友关系
            new_friendship = Friendship(
                user_id=user_id,
                friend_id=friend_id
            )
            self.session.add(new_friendship)
            self.session.commit()

            self.write({"success": True, "message": "好友添加成功"})
        except Exception as e:
            self.session.rollback()
            self.write({"success": False, "message": str(e)})
        finally:
            self.session.remove()

    @tornado.gen.coroutine
    def get(self, friend_id):
        user_id_cookie = self.get_secure_cookie("user_id")
        user_id = int(user_id_cookie.decode("utf-8")) if user_id_cookie else None

        if not friend_id:
            self.write("Invalid friend id")
            return
        
        # 如果查看的是自己的主页，重定向到/home_page
        if user_id and int(friend_id) == user_id:
            self.redirect("/home_page")
            return

        try:
            friend_id = int(friend_id)
            friend = self.session.query(User).filter_by(id=friend_id).first()

            if not friend:
                self.write("Friend not found")
                return

            # Check friendship status
            friendship = self.session.query(Friendship).filter(
                (Friendship.user_id == user_id) & (Friendship.friend_id == friend_id)
            ).first()
            is_friend = friendship is not None

            # Check blacklist status (two-way check)
            i_am_blocking = self.session.query(Blacklist).filter_by(blocker_id=user_id, blocked_id=friend_id).first() is not None
            i_am_blocked = self.session.query(Blacklist).filter_by(blocker_id=friend_id, blocked_id=user_id).first() is not None

            # Fetch chat messages
            messages = yield self.mongo.chat_messages.find({
                "$or": [
                    {"from_user_id": user_id, "to_user_id": friend_id},
                    {"from_user_id": friend_id, "to_user_id": user_id}
                ]
            }).sort("timestamp", 1).to_list(length=None)

            # Format messages
            for msg in messages:
                msg['_id'] = str(msg['_id'])
                if isinstance(msg['timestamp'], datetime):
                    msg['timestamp'] = msg['timestamp'].strftime("%Y-%m-%d %H:%M:%S")

            # Fetch friend's products
            products = self.session.query(Product).filter(Product.user_id == friend.id).all()

            self.render("profile.html",
                        current_user=self.get_secure_cookie("username").decode("utf-8"),
                        current_user_id=user_id,
                        friend=friend,
                        messages=messages,
                        products=products,
                        is_friend=is_friend,
                        i_am_blocking=i_am_blocking,
                        i_am_blocked=i_am_blocked
                        )

        except Exception as e:
            self.write(f"Error: {str(e)}")


class DeleteFriendHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo
        self.session = scoped_session(Session)

    async def post(self):
        try:
            data = json.loads(self.request.body)
            friend_id = int(data.get("friend_id"))
            user_id_cookie = self.get_secure_cookie("user_id")

            if not user_id_cookie:
                self.set_status(401)
                self.write({"status": "error", "message": "请先登录"})
                return

            user_id = int(user_id_cookie.decode("utf-8"))

            # 验证参数
            if not friend_id:
                self.set_status(400)
                self.write({"status": "error", "message": "缺少必要参数: friend_id"})
                return

            # 单向删除好友关系
            friendship_to_delete = self.session.query(Friendship).filter(
                (Friendship.user_id == user_id) & (Friendship.friend_id == friend_id)
            ).first()

            if friendship_to_delete:
                self.session.delete(friendship_to_delete)
                self.session.commit()
                self.write({"status": "success", "message": "好友删除成功"})
            else:
                self.set_status(404)
                self.write({"status": "error", "message": "好友关系不存在"})

        except Exception as e:
            self.session.rollback()
            self.set_status(500)
            self.write({"status": "error", "message": str(e)})

        finally:
            self.session.remove()
