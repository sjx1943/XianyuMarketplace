# models/favorite.py - 收藏模型
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.sql import func
from base.base import Base


class Favorite(Base):
    __tablename__ = 'xu_favorites'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('xu_user.id'), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='_user_product_favorite_uc'),
    )

    def __repr__(self):
        return f"<Favorite(user_id={self.user_id}, product_id={self.product_id})>"
