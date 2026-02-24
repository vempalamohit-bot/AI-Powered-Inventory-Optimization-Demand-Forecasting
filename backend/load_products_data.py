import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.models import Product, Base
from datetime import datetime

# Database setup
DATABASE_URL = "sqlite:///./inventory.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def load_products_csv():
    """Load products data from CSV file into database"""
    csv_path = "../data/products_50k.csv"
    
    print(f"Loading products data from: {csv_path}")
    print("This should take about 10-20 seconds...")
    
    db = SessionLocal()
    
    try:
        # Read CSV
        print("\nReading CSV file...")
        df = pd.read_csv(csv_path)
        print(f"✓ Found {len(df)} products in CSV")
        
        # Get existing products
        existing_products = {p.sku: p for p in db.query(Product).all()}
        print(f"✓ Found {len(existing_products)} existing products in database")
        
        # Process products
        products_to_add = []
        products_updated = 0
        products_skipped = 0
        
        for idx, row in df.iterrows():
            sku = str(row['sku']).strip() if pd.notna(row['sku']) else None
            if not sku:
                products_skipped += 1
                continue
            
            # Get product data
            name = str(row.get('product_name', row.get('name', sku)))
            category = str(row.get('category', 'General'))
            current_stock = int(row.get('current_stock', 0)) if pd.notna(row.get('current_stock')) else 0
            unit_cost = float(row.get('unit_cost', 10.0)) if pd.notna(row.get('unit_cost')) else 10.0
            unit_price = float(row.get('unit_price', 15.0)) if pd.notna(row.get('unit_price')) else 15.0
            lead_time_days = int(row.get('lead_time_days', 7)) if pd.notna(row.get('lead_time_days')) else 7
            
            # Check if product exists
            if sku in existing_products:
                # Update existing product
                product = existing_products[sku]
                product.name = name
                product.category = category
                product.current_stock = current_stock
                product.unit_cost = unit_cost
                product.unit_price = unit_price
                product.lead_time_days = lead_time_days
                
                # Update optional fields if they exist
                if 'reorder_point' in row and pd.notna(row['reorder_point']):
                    product.reorder_point = int(row['reorder_point'])
                if 'safety_stock' in row and pd.notna(row['safety_stock']):
                    product.safety_stock = int(row['safety_stock'])
                if 'supplier_name' in row and pd.notna(row['supplier_name']):
                    product.supplier_name = str(row['supplier_name'])
                if 'min_order_qty' in row and pd.notna(row['min_order_qty']):
                    product.min_order_qty = int(row['min_order_qty'])
                if 'storage_cost_per_unit' in row and pd.notna(row['storage_cost_per_unit']):
                    product.storage_cost_per_unit = float(row['storage_cost_per_unit'])
                
                products_updated += 1
            else:
                # Create new product
                product_data = {
                    'sku': sku,
                    'name': name,
                    'category': category,
                    'current_stock': current_stock,
                    'unit_cost': unit_cost,
                    'unit_price': unit_price,
                    'lead_time_days': lead_time_days,
                }
                
                # Add optional fields
                if 'reorder_point' in row and pd.notna(row['reorder_point']):
                    product_data['reorder_point'] = int(row['reorder_point'])
                if 'safety_stock' in row and pd.notna(row['safety_stock']):
                    product_data['safety_stock'] = int(row['safety_stock'])
                if 'supplier_name' in row and pd.notna(row['supplier_name']):
                    product_data['supplier_name'] = str(row['supplier_name'])
                if 'min_order_qty' in row and pd.notna(row['min_order_qty']):
                    product_data['min_order_qty'] = int(row['min_order_qty'])
                if 'storage_cost_per_unit' in row and pd.notna(row['storage_cost_per_unit']):
                    product_data['storage_cost_per_unit'] = float(row['storage_cost_per_unit'])
                
                product = Product(**product_data)
                products_to_add.append(product)
            
            # Progress indicator every 1000 products
            if (idx + 1) % 1000 == 0:
                print(f"  Processed {idx + 1:,} products...")
        
        # Bulk insert new products
        if products_to_add:
            print(f"\n✓ Adding {len(products_to_add)} new products...")
            db.bulk_save_objects(products_to_add)
        
        # Commit all changes
        db.commit()
        
        print(f"\n✅ SUCCESS!")
        print(f"  New products added: {len(products_to_add):,}")
        print(f"  Existing products updated: {products_updated:,}")
        if products_skipped > 0:
            print(f"  Products skipped (invalid SKU): {products_skipped:,}")
        print(f"  Total products in database: {db.query(Product).count():,}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    load_products_csv()
