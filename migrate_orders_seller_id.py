#!/usr/bin/env python
"""
Migration script to backfill seller_id for existing orders.
This ensures all historical orders have the seller_id snapshot populated.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from base.base import engine
from models.order import Order
from models.product import Product
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)
session = Session()

print("Starting migration: backfilling seller_id for existing orders...")

try:
    # Find all orders without seller_id
    orders_without_seller = session.query(Order).filter(Order.seller_id == None).all()
    
    print(f"Found {len(orders_without_seller)} orders without seller_id")
    
    updated_count = 0
    skipped_count = 0
    
    for order in orders_without_seller:
        # Try to get the product
        product = session.query(Product).filter_by(id=order.product_id).first()
        
        if product:
            # Update seller_id from product
            order.seller_id = product.user_id
            updated_count += 1
            if updated_count % 100 == 0:
                print(f"Progress: {updated_count} orders updated...")
        else:
            # Product has been deleted, we can't backfill seller_id
            skipped_count += 1
            print(f"Warning: Order #{order.id} has deleted product, cannot backfill seller_id")
    
    # Commit all changes
    session.commit()
    
    print(f"\nMigration completed successfully!")
    print(f"- Updated: {updated_count} orders")
    print(f"- Skipped: {skipped_count} orders (deleted products)")
    print(f"- Total processed: {len(orders_without_seller)} orders")
    
except Exception as e:
    session.rollback()
    print(f"Error during migration: {e}")
    sys.exit(1)
finally:
    session.close()
