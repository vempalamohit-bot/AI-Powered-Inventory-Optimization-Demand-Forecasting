import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.models import SalesHistory, Product, Base
from datetime import datetime

# Database setup
DATABASE_URL = "sqlite:///./inventory.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def load_sales_csv():
    """Load sales data from CSV file into database"""
    csv_path = "../data/sales_2years_50k.csv"
    
    print(f"Loading sales data from: {csv_path}")
    print("This may take 1-2 minutes for 570MB file...")
    
    # Read CSV in chunks to handle large file
    chunk_size = 50000
    total_records = 0
    
    db = SessionLocal()
    
    try:
        # Build SKU to product_id mapping
        print("Building SKU mapping...")
        products = db.query(Product.id, Product.sku).all()
        sku_to_id = {p.sku: p.id for p in products}
        print(f"✓ Mapped {len(sku_to_id)} SKUs")
        
        # Clear existing sales data (optional - comment out if you want to append)
        db.query(SalesHistory).delete()
        db.commit()
        print("✓ Cleared existing sales data")
        
        # Read and process CSV in chunks
        for chunk_num, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunk_size), 1):
            print(f"Processing chunk {chunk_num} ({len(chunk)} records)...")
            
            # Convert DataFrame to list of dicts
            records = []
            skipped = 0
            for _, row in chunk.iterrows():
                # Map SKU to product_id
                sku = row['sku']
                if sku not in sku_to_id:
                    skipped += 1
                    continue
                
                product_id = sku_to_id[sku]
                
                # Calculate price from revenue if available
                unit_price = None
                if 'revenue' in row and pd.notna(row['revenue']):
                    unit_price = float(row['revenue']) / float(row['quantity_sold'])
                
                record = {
                    'date': datetime.strptime(row['date'], '%Y-%m-%d').date() if isinstance(row['date'], str) else row['date'],
                    'product_id': product_id,
                    'quantity_sold': int(row['quantity_sold']),
                }
                
                # Add price if calculated
                if unit_price:
                    record['unit_price_at_sale'] = unit_price
                
                # Add optional fields if they exist
                if 'unit_cost_at_sale' in row and pd.notna(row['unit_cost_at_sale']):
                    record['unit_cost_at_sale'] = float(row['unit_cost_at_sale'])
                if 'profit_loss_amount' in row and pd.notna(row['profit_loss_amount']):
                    record['profit_loss_amount'] = float(row['profit_loss_amount'])
                if 'channel' in row and pd.notna(row['channel']):
                    record['channel'] = str(row['channel'])
                if 'is_promotional' in row and pd.notna(row['is_promotional']):
                    record['is_promotional'] = bool(row['is_promotional'])
                
                records.append(record)
            
            # Bulk insert
            db.bulk_insert_mappings(SalesHistory, records)
            db.commit()
            
            total_records += len(records)
            if skipped > 0:
                print(f"  ⚠ Skipped {skipped} records with unknown SKUs")
            print(f"  ✓ Inserted {len(records)} records (total so far: {total_records:,})")
        
        print(f"\n✅ SUCCESS! Loaded {total_records:,} sales records")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    load_sales_csv()
