"""
Enhance Product Data with Additional AI/ML Columns
Adds more features for better machine learning model training and forecasting
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

print('Loading existing product data...')
products_df = pd.read_csv('../data/products_50k.csv')
print(f'Loaded {len(products_df)} products with {len(products_df.columns)} columns')
print(f'Current columns: {list(products_df.columns)}')

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

# Define supplier IDs (100 suppliers for 50K products)
suppliers = [f'SUP-{str(i).zfill(4)}' for i in range(1, 101)]

# Define product priorities
priorities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'MINIMAL']

# Add new AI/ML-friendly columns
print('\nAdding new AI/ML columns...')

# 1. Supplier ID - for supplier analysis
products_df['supplier_id'] = [random.choice(suppliers) for _ in range(len(products_df))]

# 2. Minimum Order Quantity (MOQ) - constraint for optimization
products_df['min_order_qty'] = np.random.randint(10, 100, len(products_df))

# 3. Maximum Order Quantity - warehouse/budget constraints
products_df['max_order_qty'] = products_df['min_order_qty'] * np.random.randint(10, 50, len(products_df))

# 4. Order Frequency (days) - how often to review/order
products_df['order_frequency_days'] = np.random.choice([7, 14, 21, 30, 60], len(products_df), p=[0.3, 0.3, 0.2, 0.15, 0.05])

# 5. Seasonality Factor (1 = no seasonality, >1 = seasonal peaks)
seasonality = []
for cat in products_df['category']:
    if 'Summer' in str(cat):
        seasonality.append(round(random.uniform(1.3, 1.8), 2))
    elif 'Winter' in str(cat):
        seasonality.append(round(random.uniform(1.2, 1.6), 2))
    else:
        seasonality.append(round(random.uniform(0.8, 1.2), 2))
products_df['seasonality_factor'] = seasonality

# 6. Demand Volatility (coefficient of variation: std/mean)
products_df['demand_volatility'] = np.round(np.random.uniform(0.1, 0.8, len(products_df)), 2)

# 7. Profit Margin (calculated from price/cost)
products_df['profit_margin'] = np.round((products_df['unit_price'] - products_df['unit_cost']) / products_df['unit_price'], 2)

# 8. ABC Classification (based on revenue potential)
revenue_potential = products_df['unit_price'] * products_df['average_daily_demand']
percentiles = revenue_potential.quantile([0.2, 0.5])
abc_class = []
for rev in revenue_potential:
    if rev >= percentiles[0.5]:
        abc_class.append('A')  # Top 50% by revenue
    elif rev >= percentiles[0.2]:
        abc_class.append('B')  # Middle 30%
    else:
        abc_class.append('C')  # Bottom 20%
products_df['abc_classification'] = abc_class

# 9. XYZ Classification (based on demand volatility)
xyz_class = []
for vol in products_df['demand_volatility']:
    if vol <= 0.3:
        xyz_class.append('X')  # Stable demand
    elif vol <= 0.5:
        xyz_class.append('Y')  # Variable demand
    else:
        xyz_class.append('Z')  # Highly unpredictable
products_df['xyz_classification'] = xyz_class

# 10. Last Order Date (for lead time analysis)
end_date = datetime(2026, 2, 16)
products_df['last_order_date'] = [(end_date - timedelta(days=random.randint(1, 90))).strftime('%Y-%m-%d') for _ in range(len(products_df))]

# 11. Last Sale Date (for slow-moving item detection)
products_df['last_sale_date'] = [(end_date - timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d') for _ in range(len(products_df))]

# 12. Shelf Life Days (0 = non-perishable)
shelf_life = []
for cat in products_df['category']:
    if 'Food' in str(cat) or 'Kitchen' in str(cat):
        shelf_life.append(random.choice([30, 60, 90, 180, 365]))
    else:
        shelf_life.append(0)  # Non-perishable
products_df['shelf_life_days'] = shelf_life

# 13. Storage Cost Per Unit (carrying cost)
products_df['storage_cost_per_unit'] = np.round(products_df['unit_cost'] * np.random.uniform(0.01, 0.05, len(products_df)), 2)

# 14. Stockout Cost Per Unit (penalty/lost sale cost)
products_df['stockout_cost_per_unit'] = np.round(products_df['unit_price'] * np.random.uniform(0.2, 0.5, len(products_df)), 2)

# 15. Target Service Level (availability target %)
products_df['target_service_level'] = np.round(np.random.choice([0.90, 0.92, 0.95, 0.97, 0.99], len(products_df), p=[0.1, 0.2, 0.4, 0.2, 0.1]), 2)

# 16. Product Priority (business importance)
products_df['product_priority'] = np.random.choice(priorities, len(products_df), p=[0.05, 0.15, 0.5, 0.2, 0.1])

# 17. Weight (kg) - for shipping optimization
products_df['weight_kg'] = np.round(np.random.uniform(0.1, 25.0, len(products_df)), 2)

# 18. Volume (cubic meters) - for storage optimization
products_df['volume_m3'] = np.round(np.random.uniform(0.001, 0.5, len(products_df)), 4)

# 19. Is Perishable (boolean)
products_df['is_perishable'] = (products_df['shelf_life_days'] > 0).astype(int)

# 20. Is Hazardous (boolean) - for shipping constraints
products_df['is_hazardous'] = np.random.choice([0, 1], len(products_df), p=[0.95, 0.05])

# 21. Days Since Last Order
products_df['days_since_last_order'] = [(end_date - datetime.strptime(d, '%Y-%m-%d')).days for d in products_df['last_order_date']]

# 22. Days Since Last Sale  
products_df['days_since_last_sale'] = [(end_date - datetime.strptime(d, '%Y-%m-%d')).days for d in products_df['last_sale_date']]

# 23. Economic Order Quantity (EOQ) - calculated field
# EOQ = sqrt((2 * Annual Demand * Order Cost) / Holding Cost)
annual_demand = products_df['average_daily_demand'] * 365
order_cost = 50  # Fixed order cost
holding_cost = products_df['storage_cost_per_unit'] * 365
products_df['economic_order_qty'] = np.round(np.sqrt((2 * annual_demand * order_cost) / (holding_cost + 0.01)), 0).astype(int)

# 24. Reorder Quantity (based on EOQ but constrained by MOQ/Max)
products_df['reorder_quantity'] = np.maximum(products_df['min_order_qty'], 
                                             np.minimum(products_df['economic_order_qty'], 
                                                       products_df['max_order_qty']))

# 25. Inventory Turnover Rate (annual)
products_df['inventory_turnover'] = np.round((annual_demand / (products_df['current_stock'] + 1)), 2)

# 26. Weeks of Supply (current stock / weekly demand)
weekly_demand = products_df['average_daily_demand'] * 7
products_df['weeks_of_supply'] = np.round(products_df['current_stock'] / (weekly_demand + 0.01), 1)

# 27. Stock Status Category
stock_status = []
for row in products_df.itertuples():
    if row.current_stock == 0:
        stock_status.append('OUT_OF_STOCK')
    elif row.current_stock <= row.safety_stock:
        stock_status.append('CRITICAL')
    elif row.current_stock <= row.reorder_point:
        stock_status.append('LOW')
    elif row.current_stock <= row.reorder_point * 2:
        stock_status.append('MEDIUM')
    else:
        stock_status.append('HIGH')
products_df['stock_status'] = stock_status

print(f'\nNew columns added: {len(products_df.columns)} total columns')
print(f'New column list: {list(products_df.columns)}')

# Save to sample_data.csv
output_path = '../data/sample_data.csv'
products_df.to_csv(output_path, index=False)
print(f'\nSaved enhanced data to: {output_path}')
print(f'File size: {os.path.getsize(output_path) / (1024*1024):.2f} MB')

# Also update products_50k.csv
products_df.to_csv('../data/products_50k.csv', index=False)
print(f'Also updated: data/products_50k.csv')

# Show sample
print('\nSample of enhanced data (first 3 rows):')
print(products_df.head(3).T.to_string())

print('\n✅ Data enhancement complete!')
print(f'Total products: {len(products_df):,}')
print(f'Total columns: {len(products_df.columns)}')
print(f'\nNew AI/ML-friendly columns added:')
new_cols = ['supplier_id', 'min_order_qty', 'max_order_qty', 'order_frequency_days',
            'seasonality_factor', 'demand_volatility', 'profit_margin', 'abc_classification',
            'xyz_classification', 'last_order_date', 'last_sale_date', 'shelf_life_days',
            'storage_cost_per_unit', 'stockout_cost_per_unit', 'target_service_level',
            'product_priority', 'weight_kg', 'volume_m3', 'is_perishable', 'is_hazardous',
            'days_since_last_order', 'days_since_last_sale', 'economic_order_qty',
            'reorder_quantity', 'inventory_turnover', 'weeks_of_supply', 'stock_status']
for col in new_cols:
    print(f'  - {col}')
