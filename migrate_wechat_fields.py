#!/usr/bin/env python
#coding=utf-8

"""
数据库迁移：添加微信OAuth字段
为xu_user表添加wechat_openid, wechat_nickname, wechat_avatar字段
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from base.base import engine
from sqlalchemy import text

def migrate_wechat_fields():
    """添加微信OAuth相关字段"""
    print("开始迁移：添加微信OAuth字段...")
    
    with engine.connect() as conn:
        try:
            # 检查字段是否已存在
            check_sql = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='xu_user' AND column_name='wechat_openid'
            """)
            result = conn.execute(check_sql)
            if result.fetchone():
                print("✓ 微信字段已存在，跳过迁移")
                return
            
            # 添加wechat_openid字段
            conn.execute(text("""
                ALTER TABLE xu_user 
                ADD COLUMN wechat_openid VARCHAR(255) UNIQUE
            """))
            print("✓ 添加wechat_openid字段")
            
            # 添加wechat_nickname字段
            conn.execute(text("""
                ALTER TABLE xu_user 
                ADD COLUMN wechat_nickname VARCHAR(255)
            """))
            print("✓ 添加wechat_nickname字段")
            
            # 添加wechat_avatar字段
            conn.execute(text("""
                ALTER TABLE xu_user 
                ADD COLUMN wechat_avatar VARCHAR(500)
            """))
            print("✓ 添加wechat_avatar字段")
            
            conn.commit()
            print("✅ 微信OAuth字段迁移完成！")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ 迁移失败: {e}")
            raise

if __name__ == '__main__':
    migrate_wechat_fields()
