# chat_controller.py

import tornado.web
import tornado.websocket
import json
from models.product import Product
from models.user import User
from sqlalchemy.orm import scoped_session, sessionmaker
from base.base import engine
from tornado.gen import coroutine
from motor import motor_tornado
import redis
import datetime
from tornado.websocket import WebSocketHandler
import logging
from bson.objectid import ObjectId
from models.friendship import Friendship
from models.blacklist import Blacklist

Session = sessionmaker(bind=engine)
connections = {}

#ws类方法
class ChatWebSocketHandler(tornado.websocket.WebSocketHandler):
    def initialize(self, mongo):
        self.mongo = mongo

    def open(self):
        user_id = self.get_argument("user_id", None)
        if user_id is None or not user_id.isdigit():
            logging.warning("WebSocket connection opened with invalid user_id, connection closed.")
            self.close()
            return
        self.user_id = int(user_id)  # Ensure user_id is an integer
        connections[self.user_id] = self
        logging.warning(f"WebSocket connection established, user_id: {self.user_id}")
        self.send_stored_messages()


    @coroutine
    def send_stored_messages(self):
        try:
            user_id = self.user_id
            product_id = self.get_argument("product_id", None)
            if not user_id:
                return

            # 检查是否有选中的好友
            if not hasattr(self, 'selected_friend_id') or not self.selected_friend_id:
                return

            # 构建查询条件
            query = {"to_user_id": user_id, "status": "unread"}
            if product_id:
                query["product_id"] = int(product_id)

            messages = yield self.mongo.chat_messages.find(query).to_list(length=None)
            logging.info(f"Found {len(messages)} unread messages for user_id: {user_id}")

            for message in messages:
                message['_id'] = str(message['_id'])

                # 格式化时间戳
                if 'timestamp' in message:
                    if isinstance(message['timestamp'], datetime.datetime):
                        message['timestamp'] = message['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        try:
                            message['timestamp'] = datetime.datetime.fromisoformat(message['timestamp']).strftime(
                                "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            logging.error(f"Invalid timestamp format: {message['timestamp']}")
                            message['timestamp'] = "Invalid Date"

                # 添加isSelf字段并处理发送方显示名称
                message['isSelf'] = message['from_user_id'] == user_id
                if message['isSelf']:

                    # 修改为"我（用户名）"格式
                    from_user = yield self.mongo.users.find_one({"_id": message['from_user_id']})
                    username = from_user['username'] if from_user else '未知用户'
                    message['from_username'] = f'我({username})'
                else:
                    # 获取发送方用户名
                    from_user = yield self.mongo.users.find_one({"_id": message['from_user_id']})
                    message['from_username'] = from_user['username'] if from_user else '未知发件人'

                if self.ws_connection:
                    self.write_message(json.dumps(message))
                    # 更新消息状态为已读
                    yield self.mongo.chat_messages.update_one(
                        {"_id": ObjectId(message['_id'])},
                        {"$set": {"status": "read"}}
                    )
                else:
                    break

        except Exception as e:
            logging.error(f"Error sending stored messages: {e}")
            if self.ws_connection:
                self.write_message(json.dumps({"error": str(e)}))

    @coroutine
    def on_message(self, message):
        try:
            data = json.loads(message)
            target_user_id = int(data.get("target_user_id"))
            from_user_id = int(self.get_secure_cookie("user_id").decode("utf-8"))
            from_username = self.get_secure_cookie("username").decode("utf-8")
            message_content = data.get("message")
            product_id = int(data.get("product_id", 0))  # 默认值为0
            product_name = data.get("product_name", "")  # 默认值为空字符串

            if not all([target_user_id, message_content]):
                self.write_message(json.dumps({"error": "缺少必要参数"}))
                return

            # 定向检查拉黑状态
            session = scoped_session(Session)
            try:
                # 检查发送方是否已拉黑接收方
                if session.query(Blacklist).filter_by(blocker_id=from_user_id, blocked_id=target_user_id).first():
                    self.write_message(json.dumps({"status": "error", "error": "您已将对方拉黑，无法发送消息"}))
                    return

                # 检查接收方是否已拉黑发送方
                if session.query(Blacklist).filter_by(blocker_id=target_user_id, blocked_id=from_user_id).first():
                    self.write_message(json.dumps({"status": "error", "error": "您已被对方拉黑，无法发送消息"}))
                    return
            finally:
                session.remove()

            # 使用中国时区
            china_tz = datetime.timezone(datetime.timedelta(hours=8))
            timestamp = datetime.datetime.now(china_tz).strftime("%Y-%m-%d %H:%M:%S")

            # 构建消息数据结构
            message_data = {
                "from_user_id": from_user_id,
                "from_username": from_username,
                "to_user_id": target_user_id,
                "message": message_content,
                "product_id": product_id,
                "product_name": product_name,
                "timestamp": timestamp,
                "status": "unread"  # 设置消息状态为未读
            }

            # 保存到数据库
            yield self.mongo.chat_messages.insert_one(message_data)

            # 如果目标用户在线，发送消息
            if target_user_id in connections:
                connections[target_user_id].write_message(json.dumps(message_data))

            # 发送成功的响应
            self.write_message(json.dumps({"status": "Message sent successfully"}))

            # 也发回给发送者
            if from_user_id in connections and from_user_id != target_user_id:
                sender_data = message_data.copy()
                sender_data["status"] = "read"  # 发送者看到的消息默认为已读
                connections[from_user_id].write_message(json.dumps(sender_data))
        except Exception as e:
            self.write_message(json.dumps({"error": str(e)}))

##渲染加载聊天页面
class ChatHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo
        self.session = scoped_session(Session)

    async def get(self):
        user_id_cookie = self.get_secure_cookie("user_id")
        username_cookie = self.get_secure_cookie("username")

        if not user_id_cookie:
            self.redirect("/login")
            return

        user_id = int(user_id_cookie.decode("utf-8"))
        username = username_cookie.decode("utf-8") if username_cookie else None

        # 获取系统广播消息 - 异步处理

        broadcast_cursor = self.mongo.broadcast_messages.find().sort([('timestamp', -1)]).limit(5)
        broadcasts = []
        recent_products = self.session.query(Product).order_by(Product.id.desc()).limit(10).all()
        for p in recent_products:
            uploader = self.session.query(User).filter_by(id=p.user_id).first()
            broadcasts.append({
                "product_id": p.id,
                "product_name": p.name,
                "uploader": uploader.username if uploader else "Unknown",
                "time": p.upload_time.strftime("%Y-%m-%d %H:%M:%S") if p.upload_time else "",
                "image": "/mystatics/images/c.png"
            })

        # 获取MongoDB中的广播消息
        broadcast_cursor = self.mongo.broadcast_messages.find().sort([('timestamp', -1)]).limit(5)
        async for broadcast in broadcast_cursor:
            if '_id' in broadcast:
                broadcast['_id'] = str(broadcast['_id'])
            broadcasts.append({
                'product_id': broadcast.get('product_id', ''),
                'uploader': broadcast.get('uploader', '未知用户'),
                'time': broadcast.get('timestamp', '未知时间'),
                'product_name': broadcast.get('product_name', '')
            })

        # 第一步：从MongoDB查询给当前用户发过消息的用户ID
        message_senders = set()
        async for message in self.mongo.chat_messages.find({"to_user_id": user_id}):
            message_senders.add(message.get("from_user_id"))

        # 第二步：将这些用户添加为好友（如果还不是好友）
        existing_friendships = self.session.query(Friendship).filter_by(user_id=user_id).all()
        existing_friend_ids = {friendship.friend_id for friendship in existing_friendships}

        for sender_id in message_senders:
            if sender_id != user_id and sender_id not in existing_friend_ids:
                try:
                    new_friendship = Friendship(user_id=user_id, friend_id=sender_id)
                    self.session.add(new_friendship)
                    self.session.flush()
                except Exception as e:
                    self.session.rollback()
                    logging.error(f"添加好友关系失败: {e}")

        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logging.error(f"提交好友关系失败: {e}")

        # Step 3: Query the updated friend list
        friends = []
        friendships = self.session.query(Friendship).filter_by(user_id=user_id).all()

        for friendship in friendships:
            friend = self.session.query(User).filter_by(id=friendship.friend_id).first()
            if friend:
                # Check if the friend is blocked by the current user
                is_blocked = self.session.query(Blacklist).filter_by(blocker_id=user_id, blocked_id=friend.id).first() is not None
                friends.append({
                    'id': friend.id,
                    'username': friend.username,
                    'status': 'blocked' if is_blocked else 'active'
                })

        self.render("chat_room.html",
                    current_user=username,
                    user_id=user_id,
                    broadcasts=broadcasts,
                    friends=friends)

    def on_finish(self):
        self.session.remove()

#标记消息为已读
class MarkMessagesReadHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo

    @tornado.gen.coroutine
    def post(self):
        try:
            user_id = int(self.get_secure_cookie("user_id").decode("utf-8"))
            data = json.loads(self.request.body)
            friend_id = int(data.get("friend_id"))

            # 更新消息状态为已读
            result = yield self.mongo.chat_messages.update_many(
                {
                    "from_user_id": friend_id,
                    "to_user_id": user_id,
                    "status": "unread"
                },
                {"$set": {"status": "read"}}
            )

            self.write({"status": "success", "updated_count": result.modified_count})
        except Exception as e:
            self.write({"status": "error", "error": str(e)})



#加载对应好友的聊天记录
class MessageAPIHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo

    @tornado.gen.coroutine
    def get(self):
        user_id = int(self.get_secure_cookie("user_id").decode("utf-8"))
        friend_id = int(self.get_argument("friend_id"))

        messages = yield self.mongo.chat_messages.find({
            "$or": [
                {"from_user_id": user_id, "to_user_id": friend_id},
                {"from_user_id": friend_id, "to_user_id": user_id}
            ]
        }).sort("timestamp", 1).to_list(length=None)

        for msg in messages:
            msg['_id'] = str(msg['_id'])
            msg['isSelf'] = msg['from_user_id'] == user_id
            if isinstance(msg['timestamp'], datetime.datetime):
                msg['timestamp'] = msg['timestamp'].strftime("%Y-%m-%d %H:%M:%S")

        self.write(json.dumps(messages))

#点击发送按钮后，实现消息的发送
class SendMessageAPIHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo
        self.session = scoped_session(Session)

    @tornado.gen.coroutine
    def post(self):
        try:
            user_id = int(self.get_secure_cookie("user_id").decode("utf-8"))
            data = json.loads(self.request.body)
            friend_id = int(data["friend_id"])

            # 定向检查拉黑状态
            # 检查发送方是否已拉黑接收方
            if self.session.query(Blacklist).filter_by(blocker_id=user_id, blocked_id=friend_id).first():
                self.write({"status": "error", "error": "您已将对方拉黑，无法发送消息"})
                return

            # 检查接收方是否已拉黑发送方
            if self.session.query(Blacklist).filter_by(blocker_id=friend_id, blocked_id=user_id).first():
                self.write({"status": "error", "error": "您已被对方拉黑，无法发送消息"})
                return
            
            # 检查对方是否已将自己删除，如果是，则恢复好友关系并清空聊天记录
            reverse_friendship = self.session.query(Friendship).filter(
                (Friendship.user_id == friend_id) & (Friendship.friend_id == user_id)
            ).first()

            if not reverse_friendship:
                # 恢复好友关系
                new_friendship = Friendship(user_id=friend_id, friend_id=user_id)
                self.session.add(new_friendship)
                self.session.commit()
                
                # 同时清空双方的聊天记录
                yield self.mongo.chat_messages.delete_many({
                    "$or": [
                        {"from_user_id": user_id, "to_user_id": friend_id},
                        {"from_user_id": friend_id, "to_user_id": user_id}
                    ]
                })

            temp_id = data.get("tempId")

            message = {
                "from_user_id": user_id,
                "from_username": self.get_secure_cookie("username").decode("utf-8"),
                "to_user_id": friend_id,
                "message": data["message"],
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "unread",
                "temp_id": temp_id
            }

            # 插入消息到数据库
            result = yield self.mongo.chat_messages.insert_one(message)
            message_id = str(result.inserted_id)

            # 检查目标用户是否在线且WebSocket连接正常
            target_user_id = friend_id
            if target_user_id in connections and connections[target_user_id].ws_connection:
                message_data = message.copy()
                message_data["_id"] = message_id
                connections[target_user_id].write_message(json.dumps(message_data))

            # 也发回给发送者
            if user_id in connections and connections[user_id].ws_connection:
                sender_data = message.copy()
                sender_data["_id"] = message_id
                sender_data["status"] = "read"
                connections[user_id].write_message(json.dumps(sender_data))

            self.write({
                "status": "success",
                "messageId": message_id
            })
        except Exception as e:
            self.write({"status": "error", "error": str(e)})
        finally:
            self.session.remove()

#点击感兴趣的商品，触发聊天
class InitiateChatHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo
        self.session = scoped_session(Session)

    @tornado.web.authenticated
    async def get(self):
        try:
            seller_id_str = self.get_argument("user_id", None)
            if not seller_id_str or not seller_id_str.isdigit():
                self.send_error(400, reason="无效的卖家ID")
                return

            seller_id = int(seller_id_str)
            current_user_id = int(self.get_secure_cookie("user_id").decode("utf-8"))

            if seller_id == current_user_id:
                self.redirect("/chat_room")
                return

            friendship_model = FriendshipModel(self.session)
            
            # 使用 add_friend_if_not_exists 确保双向好友关系
            success = friendship_model.add_friend_if_not_exists(current_user_id, seller_id)

            if success:
                # 重定向到聊天室并附带friend_id，以便JS自动选择
                self.redirect(f"/chat_room?friend_id={seller_id}")
            else:
                # 如果添加好友失败，可以跳转到聊天室但不指定好友
                self.redirect("/chat_room")

        except Exception as e:
            logging.error(f"发起聊天失败: {e}")
            self.redirect("/chat_room") # 出错时重定向到主聊天页
        finally:
            self.session.remove()

    def on_finish(self):
        if hasattr(self, 'session'):
            self.session.remove()


class DeleteMessagesHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo

    @tornado.gen.coroutine
    def post(self):
        try:
            user_id = int(self.get_secure_cookie("user_id").decode("utf-8"))
            data = json.loads(self.request.body)
            message_ids = data.get("message_ids", [])
            friend_id = data.get("friend_id")

            if not message_ids:
                self.write({"status": "error", "error": "没有提供消息ID"})
                return

            # 验证用户是否有权限删除这些消息
            query = {
                "_id": {"$in": [ObjectId(msg_id) for msg_id in message_ids]},
                "$or": [
                    {"from_user_id": user_id},
                    {"to_user_id": user_id}
                ]
            }

            if friend_id:
                query["$or"].append({
                    "$and": [
                        {"from_user_id": int(friend_id)},
                        {"to_user_id": user_id}
                    ]
                })
                query["$or"].append({
                    "$and": [
                        {"from_user_id": user_id},
                        {"to_user_id": int(friend_id)}
                    ]

         })

            # 删除消息
            result = yield self.mongo.chat_messages.delete_many(query)
            # 确保返回正确的状态和删除数量
            self.write({
                "status": "success",
                "deleted_count": result.deleted_count
            })
        except Exception as e:
            self.write({"status": "error", "error": str(e)})

# 获取未读消息数量
class UnreadCountHandler(tornado.web.RequestHandler):
    def initialize(self, mongo):
        self.mongo = mongo

    @tornado.gen.coroutine
    def get(self):
        try:
            user_id_cookie = self.get_secure_cookie("user_id")
            if not user_id_cookie:
                self.write({"status": "error", "error": "User not logged in"})
                return

            user_id = int(user_id_cookie.decode("utf-8"))
            
            pipeline = [
                {"$match": {"to_user_id": user_id, "status": "unread"}},
                {"$group": {"_id": "$from_user_id", "count": {"$sum": 1}}}
            ]

            results = yield self.mongo.chat_messages.aggregate(pipeline).to_list(length=None)
            
            counts_by_friend = {res["_id"]: res["count"] for res in results}
            total_count = sum(counts_by_friend.values())

            self.write({
                "status": "success",
                "total_count": total_count,
                "counts": counts_by_friend
            })
        except Exception as e:
            self.write({"status": "error", "error": str(e)})