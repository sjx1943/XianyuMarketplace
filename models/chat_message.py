#coding=utf-8

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.base import Base, engine
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_user_id = Column(Integer, ForeignKey('xu_user.id'), nullable=False)
    from_username = Column(String(255), nullable=False)
    to_user_id = Column(Integer, ForeignKey('xu_user.id'), nullable=False)
    message = Column(Text, nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True)
    product_name = Column(String(255), nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    status = Column(String(20), nullable=False, default='unread')  # 'unread' or 'read'

    # 关系
    sender = relationship("User", foreign_keys=[from_user_id])
    receiver = relationship("User", foreign_keys=[to_user_id])
    product = relationship("Product", foreign_keys=[product_id])

    def __init__(self, from_user_id, from_username, to_user_id, message, 
                 product_id=None, product_name=None, status='unread'):
        self.from_user_id = from_user_id
        self.from_username = from_username
        self.to_user_id = to_user_id
        self.message = message
        self.product_id = product_id
        self.product_name = product_name
        self.status = status

    def to_dict(self):
        """转换为字典格式，兼容原MongoDB格式"""
        return {
            'id': self.id,
            'from_user_id': self.from_user_id,
            'from_username': self.from_username,
            'to_user_id': self.to_user_id,
            'message': self.message,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'timestamp': self.timestamp.isoformat() if self.timestamp is not None else None,
            'status': self.status
        }

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, from={self.from_user_id}, to={self.to_user_id}, status={self.status})>"
