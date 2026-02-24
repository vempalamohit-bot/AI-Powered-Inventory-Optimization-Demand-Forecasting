"""Validate and clean the POC CSV files"""
import pandas as pd
import os

# Direct paths
PRODUCTS_FILE = r'C:\Users\vempa\OneDrive\Documents\Miracle_AI_driven_POC\data\poc_500_products.csv'
SALES_FILE = r'C:\Users\vempa\OneDrive\Documents\Miracle_AI_driven_POC\data\poc_2years_sales.csv'

def validate_and_clean():
    print("=" * 60)
    print("VALIDATING CSV FILES")
    print("=" * 60)
    
    # Load products
    print("\n📦 PRODUCTS CSV")
    print("-" * 40)
    products = pd.read_csv(PRODUCTS_FILE)
    print(f"Total rows: {len(products)}")
    print(f"Columns: {list(products.columns)}")
    
    # Check duplicates
    dup_skus = products['sku'].duplicated().sum()
    print(f"Duplicate SKUs: {dup_skus}")
    
    # Check nulls
    null_counts = products.isnull().sum()
    total_nulls = null_counts.sum()
    print(f"Total null values: {total_nulls}")
    if total_nulls > 0:
        print("Null values per column:")
        for col, count in null_counts.items():
            if count > 0:
                print(f"  {col}: {count}")
    
    # Clean products if needed
    if dup_skus > 0 or total_nulls > 0:
        print("\n🔧 Cleaning products...")
        products = products.drop_duplicates(subset=['sku'], keep='first')
        products = products.dropna()
        products.to_csv(PRODUCTS_FILE, index=False)
        print(f"✅ Cleaned products saved. New count: {len(products)}")
    else:
        print("✅ Products CSV is clean!")
    
    # Load sales
    print("\n📈 SALES CSV")
    print("-" * 40)
    sales = pd.read_csv(SALES_FILE)
    print(f"Total rows: {len(sales):,}")
    print(f"Columns: {list(sales.columns)}")
    
    # Check duplicates (same product, same date should be unique)
    dup_rows = sales.duplicated(subset=['sku', 'date']).sum()
    print(f"Duplicate (sku+date) entries: {dup_rows}")
    
    # Check nulls
    null_counts = sales.isnull().sum()
    total_nulls = null_counts.sum()
    print(f"Total null values: {total_nulls}")
    if total_nulls > 0:
        print("Null values per column:")
        for col, count in null_counts.items():
            if count > 0:
                print(f"  {col}: {count}")
    
    # Clean sales if needed
    if dup_rows > 0 or total_nulls > 0:
        print("\n🔧 Cleaning sales...")
        sales = sales.drop_duplicates(subset=['sku', 'date'], keep='first')
        sales = sales.dropna()
        sales.to_csv(SALES_FILE, index=False)
        print(f"✅ Cleaned sales saved. New count: {len(sales):,}")
    else:
        print("✅ Sales CSV is clean!")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY")
    print("=" * 60)
    products = pd.read_csv(PRODUCTS_FILE)
    sales = pd.read_csv(SALES_FILE)
    
    print(f"\n📦 Products: {len(products)} items")
    print(f"   Categories: {products['category'].nunique()}")
    print(f"   Price range: ${products['price'].min():.2f} - ${products['price'].max():.2f}")
    
    print(f"\n📈 Sales: {len(sales):,} records")
    print(f"   Date range: {sales['date'].min()} to {sales['date'].max()}")
    print(f"   Total revenue: ${sales['revenue'].sum():,.2f}")
    print(f"   Unique products sold: {sales['sku'].nunique()}")
    
    # File locations
    print(f"\n📁 File Locations:")
    print(f"   Products: {os.path.abspath(PRODUCTS_FILE)}")
    print(f"   Sales:    {os.path.abspath(SALES_FILE)}")

if __name__ == "__main__":
    validate_and_clean()
