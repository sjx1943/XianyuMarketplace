#!/bin/bash

# 等待数据库启动
echo "等待数据库连接..."
sleep 10

# 创建数据库表
echo "创建数据库表..."
python -c "
import sys
sys.path.append('.')
from base.base import Base, engine
from models.user import User
from models.product import Product
from models.comment import Comment
from models.order import Order
from models.friendship import Friendship

try:
    Base.metadata.create_all(engine)
    print('数据库表创建成功')
except Exception as e:
    print(f'数据库表创建失败: {e}')
"

# 启动应用
echo "启动Tornado应用..."
python app.py
