import tornado.web
import json
import logging
from sqlalchemy.orm import sessionmaker
from base.base import engine
from models.user import User
from utils.sms_service import create_verification_code, verify_code
import hashlib

Session = sessionmaker(bind=engine)

class SendCodeHandler(tornado.web.RequestHandler):
    """发送验证码API"""
    
    def initialize(self):
        self.session = Session()
    
    def on_finish(self):
        if hasattr(self, 'session'):
            self.session.close()
    
    async def post(self):
        try:
            data = json.loads(self.request.body)
            phone = data.get('phone', '').strip()
            
            if not phone:
                self.write({'success': False, 'message': '请输入手机号'})
                return
            
            if len(phone) != 11 or not phone.isdigit():
                self.write({'success': False, 'message': '请输入有效的11位手机号'})
                return
            
            code = create_verification_code(self.session, phone)
            
            if code:
                self.write({
                    'success': True,
                    'message': '验证码已发送',
                    'code': code,
                    'dev_mode': True
                })
            else:
                self.write({'success': False, 'message': '发送验证码失败，请稍后重试'})
                
        except Exception as e:
            logging.error(f"发送验证码错误: {e}")
            self.write({'success': False, 'message': '系统错误'})

class PhoneLoginHandler(tornado.web.RequestHandler):
    """手机号登录处理"""
    
    def initialize(self):
        self.session = Session()
    
    def on_finish(self):
        if hasattr(self, 'session'):
            self.session.close()
    
    def get(self):
        """渲染手机号登录页面"""
        self.render('phone_login.html')
    
    async def post(self):
        """验证码登录"""
        try:
            data = json.loads(self.request.body)
            phone = data.get('phone', '').strip()
            code = data.get('code', '').strip()
            
            if not phone or not code:
                self.write({'success': False, 'message': '请输入手机号和验证码'})
                return
            
            if not verify_code(self.session, phone, code):
                self.write({'success': False, 'message': '验证码错误或已过期'})
                return
            
            user = self.session.query(User).filter_by(phone=phone).first()
            
            if not user:
                username = f"user_{phone[-4:]}"
                temp_password = hashlib.md5(phone.encode()).hexdigest()
                temp_email = f"{phone}@temp.local"
                
                user = User(
                    username=username,
                    password=temp_password,
                    email=temp_email,
                    phone=phone
                )
                self.session.add(user)
                self.session.commit()
                
                logging.info(f"新用户通过手机号注册: {phone}")
            
            if not user.is_active:
                self.write({'success': False, 'message': '账号已被禁用，请联系管理员'})
                return
            
            self.set_secure_cookie("user_id", str(user.id))
            self.set_secure_cookie("username", user.username)
            
            if user.room_number:
                self.set_secure_cookie("room_number", user.room_number)
                redirect_url = "/"
            else:
                redirect_url = "/set_room_number"
            
            self.write({
                'success': True,
                'message': '登录成功',
                'redirect_url': redirect_url
            })
            
        except Exception as e:
            logging.error(f"手机号登录错误: {e}")
            self.session.rollback()
            self.write({'success': False, 'message': '登录失败，请重试'})
