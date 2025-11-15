# auth_controller.py
import tornado.web
from sqlalchemy.orm import sessionmaker, scoped_session
from tornado.web import UIModule, StaticFileHandler
from models.user import User
from base.base import engine
import logging
import bcrypt
import uuid,smtplib,secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# Create a session
Session = sessionmaker(bind=engine)



class Loginmodule(UIModule):
    def render(self, *args, **kwargs):
        result = kwargs.get('result', '')
        return self.render_string('modules/login_module.html', result=result)

class LoginHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = Session()  # 创建新的会话
        # logging.basicConfig(level=logging.INFO)

    def on_finish(self):
        self.session.close()  # 关闭会话

    def get(self):
        message = self.get_argument("message", None)
        self.render("login.html", message="", result=message)

    def post(self):
        username = self.get_argument("username")
        password = self.get_argument("password")
        # logging.info(f"Attempting to log in user: {username}")

        user = self.session.query(User).filter_by(username=username).first()
        # logging.info(f"User query completed. User found: {user is not None}")

        try:
            if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
                # logging.info("Password is correct.")
                self.set_secure_cookie("user_id", str(user.id), expires_days=1)
                
                # 检查用户是否已设置房间号
                if not user.room_number:
                    # 未设置房间号，跳转到设置页面
                    self.set_secure_cookie("username", user.username, expires_days=1)
                    self.redirect("/set_room_number")
                else:
                    # 已设置房间号，使用房间号作为显示名称
                    self.set_secure_cookie("username", user.room_number, expires_days=1)
                    self.redirect("/main")
            else:
                # logging.warning("Invalid username or password.")
                self.render("login.html", message="Invalid username or password", result="用户名或密码错误")
        except Exception as e:
            # logging.error(f"Error occurred during login for user {username}: {e}")
            self.render("login.html", message="An error occurred", result=str(e))

def generate_reset_token():
    """生成一个简单的重置令牌"""
    return secrets.token_urlsafe(16)

def send_email(to_email, subject, body):
    """发送电子邮件的简单实现"""
    msg = MIMEMultipart()
    msg['From'] = '363328084@qq.com'
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.qq.com', 587)
    server.starttls()
    server.login('363328084@qq.com', 'jluwcomlwzycbieb')
    text = msg.as_string()
    server.sendmail('363328084@qq.com', to_email, text)
    server.quit()


def send_reset_email(email, reset_token):
    """发送包含密码重置令牌的电子邮件"""
    reset_link = f"http://yourwebsite.com/reset_password?reset_token={reset_token}"
    subject = "密码重置"
    body = f"您的验证码为：\n\n {reset_token} \n\n请点击以下链接输入验证码和新密码进行密码重置： {reset_link}"

    send_email(email, subject, body)

class Forgotmodule(UIModule):
    def render(self, *args, **kwargs):
        ms = kwargs.get('result', '')
        return self.render_string('modules/forgot_module.html',ms="f module")

class ForgotPasswordHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = Session()  # 创建新的会话

    def on_finish(self):
        self.session.close()  # 关闭会话

    def get(self):
        ms = self.get_argument('message',default=None)
        self.render("forgot_password.html",result=ms)
    def post(self):
        email = self.get_argument("email")
        user = self.session.query(User).filter_by(email=email).first()
        if user is not None:
            reset_token = generate_reset_token()
            user.reset_token = reset_token
            self.session.commit()
            send_reset_email(email, reset_token)
            self.render("token_input.html", result="请输入您的邮箱中的验证码和新密码")
        else:
            self.render("forgot_password.html", result="未查到关联邮箱，请核实后输入正确邮箱")



def hash_password(password):
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode('utf-8')
    # return hashed_password

class ResetPasswordHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = Session()  # 创建新的会话

    def on_finish(self):
        self.session.close()  # 关闭会话

    def post(self):
        reset_token = self.get_argument("reset_token")
        new_password = self.get_argument("new_password")
        user = self.session.query(User).filter_by(reset_token=reset_token).first()
        if user is not None:
            # 使用 hash_password 函数对新密码进行哈希处理
            user.password = hash_password(new_password)
            self.session.commit()
            self.render("password_reset_success.html")
        else:
            self.render("token_input.html", result="Invalid reset token，请核实后输入正确的邮箱验证码")

class Registmodule(UIModule):
    def render(self, *args, **kwargs):
        result = kwargs.get('result', '')
        return self.render_string('modules/register_module.html',result=result)


class RegisterHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = Session()  # 创建新的会话

    def on_finish(self):
        self.session.close()  # 关闭会话

    def get(self):
        self.render("reg.html", result="")

    def post(self):
        # 处理注册逻辑
        # 获取用户输入的用户名和密码
        username = self.get_argument("username")
        password = self.get_argument("password")
        email = self.get_argument("email")

        existing_user = self.session.query(User).filter_by(username=username).first()
        existing_email = self.session.query(User).filter_by(email=email).first()

        if existing_user is not None:
            self.render("reg.html", result="用户名已存在")
        elif existing_email is not None:
            self.render("reg.html", result="该邮箱已注册")
        else:
            # 创建新用户并添加到数据库
            hashed_password = hash_password(password)  # Hash the password before storing
            new_user = User(username=username, password=hashed_password, email=email)
            self.session.add(new_user)
            try:
                self.session.commit()
                self.clear()
                self.redirect("/login?message=注册成功，请登录")
            except Exception as e:
                self.session.rollback()
                self.render("reg.html", result="Registration failed: " + str(e))



class SetRoomNumberHandler(tornado.web.RequestHandler):
    """处理用户设置房间号"""
    def initialize(self):
        self.session = Session()
    
    def on_finish(self):
        self.session.close()
    
    def get(self):
        user_id = self.get_secure_cookie("user_id")
        if not user_id:
            self.redirect("/login")
            return
        self.render("set_room_number.html", result="")
    
    def post(self):
        import re
        user_id = self.get_secure_cookie("user_id")
        if not user_id:
            self.redirect("/login")
            return
        
        room_number = self.get_argument("room_number").strip()
        
        # 验证房间号格式：楼号-单元号-房间号（如'3-1-801'）
        pattern = r'^\d{1,3}-\d{1,2}-\d{1,4}$'
        if not re.match(pattern, room_number):
            self.render("set_room_number.html", result="房间号格式不正确，请按照'楼号-单元号-房间号'格式输入，例如：3-1-801")
            return
        
        # 检查房间号是否已被使用
        existing_room = self.session.query(User).filter_by(room_number=room_number).first()
        if existing_room:
            self.render("set_room_number.html", result="该房间号已被占用，如有疑问请联系管理员")
            return
        
        # 更新用户房间号
        user = self.session.query(User).filter_by(id=int(user_id.decode('utf-8'))).first()
        if user:
            user.room_number = room_number
            try:
                self.session.commit()
                # 更新cookie中的username为room_number
                self.set_secure_cookie("username", room_number, expires_days=1)
                self.redirect("/main")
            except Exception as e:
                self.session.rollback()
                self.render("set_room_number.html", result=f"设置失败：{str(e)}")
        else:
            self.render("set_room_number.html", result="用户不存在")


class LogoutHandler(tornado.web.RequestHandler):
    """处理用户登出"""
    def get(self):
        self.clear_cookie("user_id")
        self.clear_cookie("username")
        self.redirect("/login?message=已成功登出")
    
    def post(self):
        self.clear_cookie("user_id")
        self.clear_cookie("username")
        self.redirect("/login?message=已成功登出")


class ChatHandler(tornado.web.RequestHandler):
    def get(self):
        user_id = self.get_secure_cookie("user_id")
        username = self.get_secure_cookie("username")

        if user_id is not None:
            user_id = user_id.decode('utf-8')
        if username is not None:
            username = username.decode('utf-8')

        # Retrieve recent messages from the Chat model
        recent_messages = self.session.query(Chat).filter(
            (Chat.user1_id == user_id) | (Chat.user2_id == user_id)
        ).order_by(Chat.id.desc()).limit(10).all()

        friends = []
        for message in recent_messages:
            friend_id = message.user2_id if message.user1_id == user_id else message.user1_id
            friend = self.session.query(User).filter_by(id=friend_id).first()
            friends.append(friend.username)

        self.render('chat_room.html', current_user=username, friends=friends)

