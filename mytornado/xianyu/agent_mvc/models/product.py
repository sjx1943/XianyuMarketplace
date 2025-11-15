# product.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, desc, Column, text, ForeignKey, and_
from sqlalchemy.orm import declarative_base, sessionmaker, joinedload, relationship, Session
from sqlalchemy.types import Integer, String, DateTime, Float
from sqlalchemy.sql import func
from base.base import Base, engine
# from user import User
# from sqlalchemy.orm import Session

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255))
    price = Column(Float, nullable=False)
    user_id = Column(Integer, ForeignKey('xu_user.id'), nullable=False)
    tag = Column(String(255), nullable=False)
    image = Column(String(255))
    quantity = Column(Integer)
    status = Column(String(64))
    upload_time = Column(DateTime, server_default=func.now())   #本期新增
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")

    def __init__(self, name, description, price, user_id, tag, image, quantity, status):
        self.name = name
        self.description = description
        self.price = price
        self.user_id = user_id
        self.tag = tag
        self.image = image
        self.quantity = quantity
        self.status = status

    @classmethod
    def find_seller_by_product_id(cls, product_id: int, session: Session):
        product = session.query(cls).filter_by(id=product_id).first()
        if product:
            return product.user_id
        else:
            return None

    @classmethod
    async def update_product(cls, session: Session, product_id: int, data: dict):
        """更新商品信息"""
        try:
            product = session.query(cls).filter_by(id=product_id).first()
            if product:
                for key, value in data.items():
                    setattr(product, key, value)
                session.commit()
                return product
            return None
        except Exception as e:
            session.rollback()
            print(f"Error updating product: {e}")
            return None

    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name}, price={self.price}, user_id={self.user_id}, tag={self.tag})>"

class ProductImage(Base):
    __tablename__ = 'product_images'
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    product = relationship("Product", back_populates="images")

    def __init__(self, filename, product_id):
        self.filename = filename
        self.product_id = product_id

# Create the products table after xu_user table
#if __name__ == '__main__':
#    Base.metadata.create_all(engine)
