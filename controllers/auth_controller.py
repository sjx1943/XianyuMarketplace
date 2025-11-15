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
        self.render("login.html", message="", result=None)

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
                self.set_secure_cookie("username", user.username, expires_days=1)
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

