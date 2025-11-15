
# xianyu/MVC/models/friendship.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from sqlalchemy import Column, Integer, UniqueConstraint, ForeignKey, String
from sqlalchemy.orm import relationship
from base.base import Base, engine
from models.user import User # 导入User模型

class Friendship(Base):
    __tablename__ = 'friendships'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('xu_user.id'))
    friend_id = Column(Integer, ForeignKey('xu_user.id'))
    status = Column(String(20), default='active')  # active, blocked

    __table_args__ = (UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),)

    def __init__(self, user_id, friend_id, status='active'):
        self.user_id = user_id
        self.friend_id = friend_id
        self.status = status

    def __repr__(self):
        return f"<Friendship(id={self.id}, user_id={self.user_id}, friend_id={self.friend_id}, status='{self.status}')>"


# Base.metadata.create_all(engine)
