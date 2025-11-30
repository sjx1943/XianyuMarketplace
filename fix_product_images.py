#!/usr/bin/env python3
"""修复所有产品的主图字段，确保指向有效的图片文件"""

import os
import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.product import Product, ProductImage
from models.base import Base

# 获取数据库连接
DATABASE_URL = os.environ.get('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def fix_product_images():
    session = Session()
    try:
        products = session.query(Product).filter(Product.status != '已删除').all()
        fixed_count = 0
        
        for product in products:
            current_image = product.image
            
            # 检查当前主图是否有效
            if current_image and current_image.startswith('/static/uploads/'):
                # 默认图片路径，跳过
                continue
            
            # 检查当前主图文件是否存在
            if current_image:
                image_path = os.path.join('mystatics/images', current_image)
                if os.path.exists(image_path):
                    continue  # 文件存在，无需修复
            
            # 当前主图无效，尝试从product_images表获取第一张有效图片
            images = session.query(ProductImage).filter_by(product_id=product.id).order_by(ProductImage.id).all()
            
            new_image = None
            for img in images:
                img_path = os.path.join('mystatics/images', img.filename)
                if os.path.exists(img_path):
                    new_image = img.filename
                    break
            
            if new_image:
                print(f"产品 {product.id} ({product.name}): 主图从 '{current_image}' 更新为 '{new_image}'")
                product.image = new_image
                fixed_count += 1
            elif not current_image or (current_image and not os.path.exists(os.path.join('mystatics/images', current_image))):
                # 检查product_images表中是否有任何图片记录
                if len(images) == 0:
                    print(f"产品 {product.id} ({product.name}): 没有图片记录，保持原状")
                else:
                    print(f"产品 {product.id} ({product.name}): 没有有效图片文件")
        
        if fixed_count > 0:
            session.commit()
            print(f"\n已修复 {fixed_count} 个产品的主图")
        else:
            print("所有产品的主图都是有效的（或使用默认图片）")
            
    except Exception as e:
        session.rollback()
        print(f"修复失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == '__main__':
    fix_product_images()
