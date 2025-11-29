#!/usr/bin/env python
"""
在Replit或VPS上创建管理员账号的脚本

使用方法：
1. Replit开发环境：python scripts/add_admin_prod.py
2. VPS生产环境：docker exec -it <container_name> python scripts/add_admin_prod.py
"""
import os
import sys
import bcrypt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.base import Base, engine
from models.user import User
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

def hash_password(password):
    """使用bcrypt加密密码（与auth_controller.py保持一致）"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode('utf-8')

def create_admin_user():
    """创建管理员账号"""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        admin_username = "admin"
        admin_password = "Admin@123456"
        admin_email = "admin@okashii.top"
        admin_room_number = "1-1-101"
        
        existing_admin = session.query(User).filter_by(username=admin_username).first()
        if existing_admin:
            if existing_admin.is_admin:
                print(f"✅ 管理员账号已存在: {admin_username}")
                print(f"   用户名: {admin_username}")
                print(f"   邮箱: {existing_admin.email}")
                print(f"   房间号: {existing_admin.room_number}")
                print("   ℹ️  密码保持不变（防止意外覆盖）")
            else:
                existing_admin.is_admin = True
                session.commit()
                print(f"✅ 已将用户 {admin_username} 提升为管理员")
            return
        
        # 使用与系统一致的bcrypt加密（不是SHA256）
        password_hash = hash_password(admin_password)
        
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
