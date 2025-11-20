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
        self.session = Session()  # 每个Handler独立session
        # logging.basicConfig(level=logging.INFO)

    def on_finish(self):
        self.session.close()  # 关闭session

    def get(self):
        message = self.get_argument("message", None)
        self.render("login.html", message="", result=message)

    def post(self):
        from sqlalchemy import or_
        from models.verification_code import VerificationCode
        from datetime import datetime, timezone, timedelta
        import hashlib
        
        login_type = self.get_argument("login_type", "password")
        
        try:
            if login_type == "code":
                from utils.sms_service import normalize_verification_expiry
                
                phone = self.get_argument("phone", "").strip()
                code = self.get_argument("code", "").strip()
                
                if not phone or not code:
                    self.render("login.html", message="", result="请输入手机号和验证码")
                    return
                
                # 使用UTC时间验证（标准做法，避免时区混淆）
                now_utc = datetime.now(timezone.utc)
                
                verification = self.session.query(VerificationCode).filter_by(
                    phone=phone,
                    code=code,
                    is_used=0
                ).first()
                
                if not verification:
                    self.render("login.html", message="", result="验证码错误或已使用")
                    return
                
                # 标准化过期时间并验证（使用UTC比较）
                expires_utc = verification.expires_at if verification.expires_at.tzinfo else verification.expires_at.replace(tzinfo=timezone.utc)
                beijing_tz = timezone(timedelta(hours=8))
                now_beijing = now_utc.astimezone(beijing_tz)
                expires_beijing = normalize_verification_expiry(verification.expires_at)
                logging.debug(f"登录验证码检查: now={now_beijing}, expires_at={expires_beijing}")
                
                if now_utc > expires_utc:
                    self.render("login.html", message="", result="验证码已过期")
                    return
                
                verification.is_used = 1
                self.session.commit()
                
                user = self.session.query(User).filter_by(phone=phone).first()
                if not user:
                    password_hash = hashlib.md5('123456'.encode()).hexdigest()
                    user = User(
                        username=f"user_{phone[-4:]}",
                        password=password_hash,
                        email=f"{phone}@temp.com",
                        phone=phone
                    )
                    self.session.add(user)
                    self.session.commit()
                
                self.set_secure_cookie("user_id", str(user.id), expires_days=1)
                
                if not user.room_number:
                    self.set_secure_cookie("username", user.username, expires_days=1)
                    self.redirect("/set_room_number")
                else:
                    self.set_secure_cookie("username", user.room_number, expires_days=1)
                    self.redirect("/main")
            
            else:
                identifier = self.get_argument("username", "").strip()
                password = self.get_argument("password", "").strip()
                
                if not identifier or not password:
                    self.render("login.html", message="", result="请输入用户名和密码")
                    return
                
                user = self.session.query(User).filter(
                    or_(
                        User.username == identifier,
                        User.room_number == identifier,
                        User.phone == identifier
                    )
                ).first()
                
                if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
                    if user.is_active == 0:
                        self.render("login.html", message="", result="账号已被禁用，请联系管理员")
                        return
                    
                    self.set_secure_cookie("user_id", str(user.id), expires_days=1)
                    
                    if not user.room_number:
                        self.set_secure_cookie("username", user.username, expires_days=1)
                        self.redirect("/set_room_number")
                    else:
                        self.set_secure_cookie("username", user.room_number, expires_days=1)
                        self.redirect("/main")
                else:
                    self.render("login.html", message="", result="用户名/房间号/手机号或密码错误")
                    
        except Exception as e:
            logging.error(f"登录错误: {e}")
            self.session.rollback()
            self.render("login.html", message="", result=f"登录失败: {str(e)}")

def generate_reset_token():
    """生成一个简单的重置令牌"""
    return secrets.token_urlsafe(16)

def send_email(to_email, subject, body):
    """
    发送电子邮件，支持SSL/TLS双模式
    
    环境变量（可选）：
    - SMTP_SERVER: SMTP服务器地址（默认：smtp.qq.com）
    - SMTP_PORT: SMTP端口（默认：465，QQ邮箱推荐SSL端口）
    - SMTP_USER: SMTP用户名/邮箱（默认：363328084@qq.com）
    - SMTP_PASSWORD: SMTP密码/授权码（默认：jluwcomlwzycbieb）
    - SMTP_USE_SSL: 使用SSL而非TLS（默认：True）
    """
    import os
    
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.qq.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 465))
    smtp_user = os.environ.get('SMTP_USER', '363328084@qq.com')
    smtp_password = os.environ.get('SMTP_PASSWORD', 'jluwcomlwzycbieb')
    use_ssl = os.environ.get('SMTP_USE_SSL', 'True').lower() in ['true', '1', 'yes']
    
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        logging.info(f"尝试发送邮件: {to_email} (服务器:{smtp_server}:{smtp_port}, SSL:{use_ssl})")
        
        # 根据配置选择SSL或TLS连接
        if use_ssl:
            # SSL连接（端口465，QQ邮箱推荐）
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15)
        else:
            # TLS连接（端口587）
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
            server.starttls()
        
        # 登录
        server.login(smtp_user, smtp_password)
        
        # 发送邮件
        text = msg.as_string()
        server.sendmail(smtp_user, to_email, text)
        server.quit()
        
        logging.info(f"✅ 邮件发送成功: {to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logging.error(f"❌ SMTP认证失败: {e}")
        logging.error(f"   请检查: 1) QQ邮箱授权码是否正确 2) 是否开启了SMTP服务")
        raise Exception("邮箱认证失败，请检查授权码是否正确")
    except smtplib.SMTPException as e:
        logging.error(f"❌ SMTP错误: {e}")
        raise Exception(f"邮件发送失败: {str(e)}")
    except Exception as e:
        logging.error(f"❌ 邮件发送异常: {type(e).__name__}: {e}")
        raise Exception(f"邮件发送失败: {str(e)}")


def send_reset_email(email, reset_token, base_url=None):
    """发送包含密码重置令牌的电子邮件"""
    import os
    # 优先使用传入的base_url，否则从环境变量获取，最后使用默认值
    if not base_url:
        # 从环境变量获取域名（Replit会自动设置REPLIT_DOMAINS）
        domains = os.environ.get('REPLIT_DOMAINS', '')
        if domains:
            # REPLIT_DOMAINS可能包含多个域名，用逗号分隔，取第一个
            base_url = f"https://{domains.split(',')[0].strip()}"
        else:
            # 如果没有环境变量，使用默认值
            base_url = os.environ.get('RESET_URL', 'http://localhost:5000')
    
    reset_link = f"{base_url}/reset_password?reset_token={reset_token}"
    subject = "密码重置"
    body = f"您的验证码为：\n\n {reset_token} \n\n请点击以下链接输入验证码和新密码进行密码重置： {reset_link}"

    send_email(email, subject, body)

class Forgotmodule(UIModule):
    def render(self, *args, **kwargs):
        ms = kwargs.get('result', '')
        return self.render_string('modules/forgot_module.html',ms="f module")

class ForgotPasswordHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = Session()  # 每个Handler独立session

    def on_finish(self):
        self.session.close()  # 关闭session

    def get(self):
        ms = self.get_argument('message',default=None)
        self.render("forgot_password.html",result=ms)
    
    def post(self):
        from models.verification_code import VerificationCode
        from datetime import datetime, timezone, timedelta
        import hashlib
        
        reset_type = self.get_argument("reset_type", "email")
        
        try:
            if reset_type == "phone":
                # 手机号+验证码重置密码
                phone = self.get_argument("phone", "").strip()
                code = self.get_argument("code", "").strip()
                new_password = self.get_argument("new_password", "").strip()
                confirm_password = self.get_argument("confirm_password", "").strip()
                
                if not phone or not code or not new_password:
                    self.render("forgot_password.html", result="请填写所有必填项")
                    return
                
                if new_password != confirm_password:
                    self.render("forgot_password.html", result="两次输入的密码不一致")
                    return
                
                # 验证验证码（使用UTC时间，避免时区混淆）
                from utils.sms_service import normalize_verification_expiry
                
                now_utc = datetime.now(timezone.utc)
                
                verification = self.session.query(VerificationCode).filter_by(
                    phone=phone,
                    code=code,
                    is_used=0
                ).first()
                
                if not verification:
                    self.render("forgot_password.html", result="验证码错误或已使用")
                    return
                
                # 标准化过期时间（UTC → Beijing，用于用户友好的日志）
                beijing_tz = timezone(timedelta(hours=8))
                now_beijing = now_utc.astimezone(beijing_tz)
                verification_expires_beijing = normalize_verification_expiry(verification.expires_at)
                
                logging.debug(f"验证码过期时间检查: now={now_beijing}, expires_at={verification_expires_beijing}")
                
                # 使用UTC时间比较（避免时区混淆）
                expires_utc = verification.expires_at if verification.expires_at.tzinfo else verification.expires_at.replace(tzinfo=timezone.utc)
                if now_utc > expires_utc:
                    self.render("forgot_password.html", result="验证码已过期")
                    return
                
                # 查找用户并重置密码
                user = self.session.query(User).filter_by(phone=phone).first()
                if not user:
                    self.render("forgot_password.html", result="该手机号未注册")
                    return
                
                # 标记验证码已使用并更新密码（使用hash_password加密）
                verification.is_used = 1
                user.password = hash_password(new_password)
                
                # CRITICAL: 提交事务保存密码和验证码状态
                self.session.commit()
                
                logging.info(f"手机号重置密码成功: {phone}")
                self.render("password_reset_success.html")
            
            else:
                # 邮箱重置密码（原有逻辑）
                email = self.get_argument("email")
                user = self.session.query(User).filter_by(email=email).first()
                if user is not None:
                    reset_token = generate_reset_token()
                    user.reset_token = reset_token
                    self.session.commit()
                    
                    try:
                        # 获取当前请求的域名
                        base_url = f"{self.request.protocol}://{self.request.host}"
                        send_reset_email(email, reset_token, base_url)
                        logging.info(f"邮箱重置密码邮件已发送: {email}")
                        self.render("token_input.html", result="请输入您的邮箱中的验证码和新密码")
                    except Exception as e:
                        logging.error(f"发送重置邮件失败: {e}")
                        # 失败时清除reset_token，避免用户无法重新请求
                        user.reset_token = None
                        self.session.commit()
                        self.render("forgot_password.html", result="发送邮件失败，请稍后重试或联系管理员")
                else:
                    self.render("forgot_password.html", result="未查到关联邮箱，请核实后输入正确邮箱")
        
        except Exception as e:
            logging.error(f"密码重置错误: {e}")
            self.session.rollback()
            self.render("forgot_password.html", result=f"重置失败: {str(e)}")



def hash_password(password):
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode('utf-8')
    # return hashed_password

class ResetPasswordHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = Session()  # 每个Handler独立session

    def on_finish(self):
        self.session.close()  # 关闭session

    def get(self):
        # 显示重置密码表单
        reset_token = self.get_argument("reset_token", default=None)
        result = self.get_argument("result", default="请输入您的邮箱验证码和新密码")
        self.render("token_input.html", result=result, reset_token=reset_token)

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
        self.session = Session()  # 每个Handler独立session

    def on_finish(self):
        self.session.close()  # 关闭session

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

