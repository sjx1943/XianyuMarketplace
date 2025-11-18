#!/usr/bin/env python
#coding=utf-8

"""创建批量测试数据"""

import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from base.base import engine
from models.user import User
from models.product import Product
from models.order import Order

Session = sessionmaker(bind=engine)
session = Session()

def create_test_users(count=10):
    """创建批量测试用户"""
    created_count = 0
    password_md5 = hashlib.md5("Test123456".encode()).hexdigest()
    
    for i in range(4, 4 + count):
        building = (i % 5) + 1
        unit = (i % 3) + 1
        room = 100 + i
        room_number = f"{building}-{unit}-{room}"
        
        existing = session.query(User).filter_by(room_number=room_number).first()
        if not existing:
            user = User(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password=password_md5
            )
            user.room_number = room_number
            user.phone = f"138{i:08d}"
            user.is_active = 1
            session.add(user)
            created_count += 1
    
    session.commit()
    print(f"✅ 创建了 {created_count} 个测试用户 (密码: Test123456)")
    return created_count

def create_test_products(count=10):
    """创建批量测试商品"""
    product_names = [
        "二手自行车", "电动车充电器", "台式电脑", "笔记本电脑", "电饭煲",
        "微波炉", "空调扇", "书桌", "办公椅", "跑步机",
        "羽毛球拍", "乒乓球桌", "吉他", "键盘", "鼠标",
        "显示器", "路由器", "音箱", "耳机", "充电宝"
    ]
    
    descriptions = [
        "九成新，几乎没怎么用", "功能正常，价格实惠", "成色很好，诚心出售",
        "用了一年，质量不错", "闲置在家，低价转让", "急转，价格可商量",
        "搬家清仓，便宜卖了", "原价XXX，现在半价", "正品保证，无质量问题",
        "自用物品，爱护有加"
    ]
    
    statuses = ["在售", "在售", "在售", "已售完"]
    
    users = session.query(User).all()
    if not users:
        print("❌ 没有找到用户，请先创建用户")
        return 0
    
    created_count = 0
    for i in range(count):
        user = users[i % len(users)]
        product = Product(
            name=product_names[i % len(product_names)],
            description=descriptions[i % len(descriptions)],
            price=round(50 + (i * 37.5) % 500, 1),
            user_id=user.id,
            tag="二手",
            image="/static/uploads/default.jpg",
            quantity=1,
            status=statuses[i % len(statuses)]
        )
        session.add(product)
        created_count += 1
    
    session.commit()
    print(f"✅ 创建了 {created_count} 个测试商品")
    return created_count

def create_test_orders(count=15):
    """创建批量测试订单"""
    products = session.query(Product).filter(Product.status != '已删除').all()
    users = session.query(User).all()
    
    if not products or not users:
        print("❌ 没有足够的商品或用户，请先创建")
        return 0
    
    statuses = ["pending", "shipped", "completed"]
    created_count = 0
    
    for i in range(count):
        product = products[i % len(products)]
        buyer = users[i % len(users)]
        
        if buyer.id == product.user_id:
            buyer = users[(i + 1) % len(users)]
        
        created_at = datetime.now() - timedelta(days=i)
        
        order = Order(
            product_id=product.id,
            user_id=buyer.id,
            quantity=1,
            product_name=product.name,
            seller_id=product.user_id,
            order_note=f"测试订单{i+1}"
        )
        order.status = statuses[i % len(statuses)]
        order.created_at = created_at
        
        if order.status in ['shipped', 'completed']:
            order.shipped_at = created_at + timedelta(days=1)
        if order.status == 'completed':
            order.completed_at = created_at + timedelta(days=2)
        
        session.add(order)
        created_count += 1
    
    session.commit()
    print(f"✅ 创建了 {created_count} 个测试订单")
    return created_count

def main():
    print("========================================")
    print("创建批量测试数据")
    print("========================================\n")
    
    try:
        user_count = create_test_users(10)
        product_count = create_test_products(15)
        order_count = create_test_orders(20)
        
        print("\n========================================")
        print("测试数据创建完成！")
        print("========================================")
        print(f"新增用户: {user_count}")
        print(f"新增商品: {product_count}")
        print(f"新增订单: {order_count}")
        print("\n测试账号密码: Test123456")
        print("========================================")
        
    except Exception as e:
        print(f"❌ 创建测试数据时出错: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
