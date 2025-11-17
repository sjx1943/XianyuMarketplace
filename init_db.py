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
from models.chat_message import ChatMessage
from models.verification_code import VerificationCode

print("Creating database tables...")
try:
    Base.metadata.create_all(engine)
    print("Database tables created successfully!")
    print("Tables created: xu_user, xu_product, xu_product_image, xu_order, xu_comment, xu_friendship, xu_blacklist, xu_chat_message, xu_verification_code")
except Exception as e:
    print(f"Error creating tables: {e}")
    sys.exit(1)
