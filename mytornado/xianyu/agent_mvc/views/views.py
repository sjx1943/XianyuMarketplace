#coding=utf-8
from tornado.web import RequestHandler,Application

from modes import User
from utils.sessions import SessionManager

class BaseHandler(RequestHandler):
    def prepare(self):
        #从cookie中获取sessionid
        c_sessionid = self.get_cookie('sessionid','')

        #根据sessionid获取session对象
        sessionobj = SessionManager.getSessionObjBySid(c_sessionid)

        #判断是否需要重置cookie中的sessionid
        if sessionobj.sessionid != c_sessionid:
            self.set_cookie('sessionid',sessionobj.sessionid,expires_days=14)

        self.session = sessionobj

    # 持久化session对象
    def on_finish(self):
        SessionManager.cache2redis(self.session)


class LoginHandler(BaseHandler):
    def get(self, *args, **kwargs):
        self.render('login.html')

    def post(self, *args, **kwargs):
        #获取请求参数
        uname = self.get_argument('uname')
        pwd = self.get_argument('pwd')

        #判断是否登录成功
        if uname=='zhangsan' and pwd =='123':
            user = User(uname,pwd)
            #将登陆用户对象存放至session对象中
            self.session.set('user',user)
            #重定向至center
            self.redirect('/center/')



class CenterHandler(BaseHandler):
    def get(self, *args, **kwargs):
        #从session中获取当前登录用户对象
        user = self.session.get('user')

        self.write(u'欢迎%s登录成功！'%user.uname)
