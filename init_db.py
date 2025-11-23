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

print("=" * 60)
print("🗄️  数据库初始化中...")
print("=" * 60)

try:
    # 创建所有表（如果已存在则跳过）
    Base.metadata.create_all(engine)
    print("✅ 数据库表初始化成功！")
    print("\n📋 已创建的表:")
    print("  - xu_user (用户)")
    print("  - xu_product (商品)")
    print("  - xu_product_image (商品图片)")
    print("  - xu_order (订单)")
    print("  - xu_comment (评论)")
    print("  - xu_friendship (好友关系)")
    print("  - xu_blacklist (黑名单)")
    print("  - xu_chat_message (聊天消息)")
    print("  - xu_verification_code (验证码)")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ 数据库初始化失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
