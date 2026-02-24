"""Generate 2 years of sales data for 50,000 products"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

print('Loading products...')
products_df = pd.read_csv('../data/products_50k.csv')
print(f'Loaded {len(products_df)} products')

# Generate 2 years of dates (Feb 17, 2024 to Feb 16, 2026)
end_date = datetime(2026, 2, 16)
start_date = end_date - timedelta(days=729)  # 730 days total = 2 years
date_range = pd.date_range(start=start_date, end=end_date, freq='D')
print(f'Date range: {start_date.date()} to {end_date.date()} ({len(date_range)} days)')

# Generate sales data with realistic patterns
print('Generating sales data (this may take a few minutes)...')

# We'll generate sales for each product on 30-70% of days (random)
sales_records = []

for i, row in products_df.iterrows():
    sku = row['sku']
    avg_demand = row.get('average_daily_demand', 10) or 10
    unit_price = row.get('unit_price', 50) or 50
    category = row.get('category', 'General')
    
    # Determine how many days this product had sales (30-70% of days)
    sales_probability = random.uniform(0.3, 0.7)
    
    # Seasonal patterns based on category
    is_summer = 'Summer' in str(category)
    is_winter = 'Winter' in str(category)
    
    for date in date_range:
        # Random chance of sale on this day
        if random.random() > sales_probability:
            continue
            
        # Add seasonality
        month = date.month
        seasonal_factor = 1.0
        if is_summer:
            seasonal_factor = 1.5 if month in [5, 6, 7, 8] else 0.7
        elif is_winter:
            seasonal_factor = 1.5 if month in [11, 12, 1, 2] else 0.7
        
        # Weekend boost for consumer goods
        if date.weekday() >= 5:  # Saturday, Sunday
            seasonal_factor *= 1.2
        
        # Generate quantity with some variance
        base_qty = avg_demand * seasonal_factor
        qty = max(1, int(np.random.poisson(max(1, base_qty))))
        revenue = round(qty * unit_price, 2)
        
        sales_records.append({
            'date': date.strftime('%Y-%m-%d'),
            'sku': sku,
            'quantity_sold': qty,
            'revenue': revenue
        })
    
    if (i + 1) % 5000 == 0:
        print(f'Processed {i + 1}/{len(products_df)} products... ({len(sales_records):,} records so far)')

print(f'\nTotal sales records: {len(sales_records):,}')

# Create DataFrame and save
print('Creating DataFrame...')
sales_df = pd.DataFrame(sales_records)

print(f'Saving to CSV... ({len(sales_df):,} rows)')
output_path = '../data/sales_2years_50k.csv'
sales_df.to_csv(output_path, index=False)

# Get actual file size
file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
print(f'\nDone! File saved to: data/sales_2years_50k.csv')
print(f'File size: {file_size_mb:.1f} MB')
print(f'Total records: {len(sales_df):,}')

# Show sample
print('\nSample data:')
print(sales_df.head(10).to_string())

# Show distribution by month
print('\nSales distribution by month:')
sales_df['month'] = pd.to_datetime(sales_df['date']).dt.to_period('M')
monthly = sales_df.groupby('month').agg({'quantity_sold': 'sum', 'revenue': 'sum'})
print(monthly.head(12).to_string())
