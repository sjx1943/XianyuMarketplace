import hashlib
from sqlalchemy.orm import sessionmaker
from base.base import engine
from models.user import User

Session = sessionmaker(bind=engine)
session = Session()

try:
    admin = session.query(User).filter_by(username='admin').first()
    
    password_md5 = hashlib.md5('Zpepc001@'.encode()).hexdigest()
    
    if admin:
        print(f"管理员账号已存在 (ID: {admin.id})，正在更新...")
        admin.password = password_md5
        admin.is_admin = 1
        admin.is_active = 1
        admin.room_number = 'ADMIN-0-001'
        print("管理员账号已更新！")
    else:
        print("创建新管理员账号...")
        admin = User(
            username='admin',
            password=password_md5,
            email='admin@community.local',
            room_number='ADMIN-0-001',
            is_admin=1
        )
        admin.is_active = 1
        session.add(admin)
        print("管理员账号创建成功！")
    
    session.commit()
    print(f"\n管理员登录信息：")
    print(f"用户名: admin")
    print(f"密码: Zpepc001@")
    print(f"房间号: ADMIN-0-001")
    print(f"管理员权限: {'是' if admin.is_admin == 1 else '否'}")
    
except Exception as e:
    session.rollback()
    print(f"错误: {e}")
finally:
    session.close()
