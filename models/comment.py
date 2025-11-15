#coding=utf-8

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.base import Base, engine
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class Comment(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('xu_user.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    text = Column(String(500), nullable=False)
    rating = Column(Float, nullable=False, default=5.0)  # 评分 1-5
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系定义（需要在User和Product模型中添加对应的back_populates）
    # user = relationship('User', back_populates='comments')
    # product = relationship('Product', back_populates='comments')

    def __init__(self, user_id, product_id, text, rating=5.0):
        self.user_id = user_id
        self.product_id = product_id
        self.text = text
        self.rating = rating

    def __repr__(self):
        return f"<Comment(id={self.id}, user_id={self.user_id}, product_id={self.product_id}, rating={self.rating})>"

#Base.metadata.create_all(engine)
