#coding=utf-8

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.base import Base, engine
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True) # 允许为空
    product_name = Column(String(255), nullable=True) # 新增商品名称字段
    user_id = Column(Integer, ForeignKey('xu_user.id'), nullable=False)  # 买家
    quantity = Column(Integer, nullable=False, default=1)
    status = Column(String(50), nullable=False, default='pending')  # pending, confirmed, shipped, delivered, completed, cancelled
    order_note = Column(Text, nullable=True)  # 订单备注
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)  # 完成时间

    product = relationship("Product")
    user = relationship("User")

    def __init__(self, product_id, user_id, quantity, product_name, order_note=None):
        self.product_id = product_id
        self.user_id = user_id
        self.quantity = quantity
        self.product_name = product_name
        self.order_note = order_note

    def __repr__(self):
        return f"<Order(id={self.id}, product_id={self.product_id}, user_id={self.user_id}, status={self.status})>"

# from models.user import User
# from models.product import Product
# Base.metadata.create_all(engine)
