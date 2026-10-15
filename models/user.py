#user.py
#写user表的model
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, desc, Column, text, ForeignKey, and_, Sequence
from sqlalchemy.orm import declarative_base, sessionmaker,joinedload
from sqlalchemy.types import Integer, String, DateTime, Float
from sqlalchemy.sql import func
# from MVC.base.base import Base, engine
from base.base import Base, engine

class User(Base):
    __tablename__ = 'xu_user'
    id = Column(Integer, Sequence('xu_user_id_seq'), primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    reset_token = Column(String(255))
    room_number = Column(String(50), nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    is_admin = Column(Integer, default=0)
    is_active = Column(Integer, default=1)
    wechat_openid = Column(String(255), unique=True, nullable=True)
    wechat_nickname = Column(String(255), nullable=True)
    wechat_avatar = Column(String(500), nullable=True)
    avatar_security_status = Column(String(20), nullable=True, default='approved')
    avatar_trace_id = Column(String(100), nullable=True)

    def __init__(self, username, password, email, room_number=None, phone=None, is_admin=0, wechat_openid=None):
        self.username = username
        self.password = password
        self.email = email
        self.room_number = room_number
        self.phone = phone
        self.is_admin = is_admin
        self.is_active = 1
        self.wechat_openid = wechat_openid


    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


# Base.metadata.create_all(engine)

# if __name__ == '__main__':
#     Base.metadata.create_all(engine)
#

