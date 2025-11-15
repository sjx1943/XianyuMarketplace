#!/usr/bin/env python
"""Initialize database tables"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from base.base import Base, engine
from models.user import User
from models.product import Product, ProductImage
from models.order import Order
from models.comment import Comment
from models.friendship import Friendship
from models.blacklist import Blacklist

print("Creating database tables...")
try:
    Base.metadata.create_all(engine)
    print("Database tables created successfully!")
except Exception as e:
    print(f"Error creating tables: {e}")
    sys.exit(1)
