#!/usr/bin/env python3
"""
修复数据库中 URL 编码的图片文件名
问题：图片文件名被存储为 URL 编码形式（如 %20 为空格）
但文件系统中实际文件名是解码后的形式
"""
import os
import sys
import urllib.parse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.base import engine
from models.product import Product, ProductImage
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine)

def fix_image_urls():
    """修复所有 URL 编码的图片文件名"""
    session = SessionLocal()
    
    try:
        print("=" * 60)
        print("🔧 开始修复 URL 编码的图片文件名")
        print("=" * 60)
        
        # 修复 Product.image 字段
        products = session.query(Product).all()
        product_fixed = 0
        
        for product in products:
            if product.image and '%' in product.image:
                decoded = urllib.parse.unquote(product.image)
                print(f"产品 ID {product.id}: {product.image} → {decoded}")
                product.image = decoded
                product_fixed += 1
        
        # 修复 ProductImage.filename 字段
        product_images = session.query(ProductImage).all()
        image_fixed = 0
        
        for img in product_images:
            if img.filename and '%' in img.filename:
                decoded = urllib.parse.unquote(img.filename)
                print(f"图片 ID {img.id}: {img.filename} → {decoded}")
                img.filename = decoded
                image_fixed += 1
        
        if product_fixed > 0 or image_fixed > 0:
            session.commit()
            print("=" * 60)
            print(f"✅ 修复完成!")
            print(f"   - 产品图片: {product_fixed} 条")
            print(f"   - 产品图像记录: {image_fixed} 条")
            print("=" * 60)
        else:
            print("✅ 没有需要修复的 URL 编码")
        
    except Exception as e:
        session.rollback()
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    fix_image_urls()
