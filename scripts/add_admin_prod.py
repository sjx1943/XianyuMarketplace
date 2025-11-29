#!/usr/bin/env python
"""
生产环境管理员账号创建脚本

使用方法（在生产服务器上执行）:
1. 进入Docker容器: docker exec -it <container_name> bash
2. 执行: python scripts/add_admin_prod.py

或者直接通过Docker执行:
docker exec -it <container_name> python scripts/add_admin_prod.py
"""
import os
import sys
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Session, engine
from models.user import User
from sqlalchemy.exc import IntegrityError

def create_admin_user():
    """创建管理员账号"""
    session = Session()
    
    try:
        admin_username = "admin"
        admin_password = "Admin@123456"
        admin_email = "admin@okashii.top"
        admin_room_number = "1-1-101"
        
        existing_admin = session.query(User).filter_by(username=admin_username).first()
        if existing_admin:
            if existing_admin.is_admin:
                print(f"✅ 管理员账号已存在: {admin_username}")
            else:
                existing_admin.is_admin = True
                session.commit()
                print(f"✅ 已将用户 {admin_username} 提升为管理员")
            return
        
        password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
        
        admin_user = User(
            username=admin_username,
            password=password_hash,
            email=admin_email,
            room_number=admin_room_number,
            is_admin=True,
            is_active=True
        )
        
        session.add(admin_user)
        session.commit()
        
        print("=" * 60)
        print("✅ 管理员账号创建成功！")
        print("=" * 60)
        print(f"📧 用户名: {admin_username}")
        print(f"🔑 密码: {admin_password}")
        print(f"📬 邮箱: {admin_email}")
        print(f"🏠 房间号: {admin_room_number}")
        print("=" * 60)
        print("⚠️  请立即登录后台修改密码！")
        print(f"🔗 管理后台: https://okashii.top/admin/login")
        print("=" * 60)
        
    except IntegrityError as e:
        session.rollback()
        print(f"❌ 创建失败（用户名或邮箱已存在）: {e}")
    except Exception as e:
        session.rollback()
        print(f"❌ 创建失败: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    create_admin_user()
