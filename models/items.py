#coding=utf-8
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.base import Base, engine

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship


class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    description = Column(String(255))
    age = Column(Integer)

# Base.metadata.create_all(engine)