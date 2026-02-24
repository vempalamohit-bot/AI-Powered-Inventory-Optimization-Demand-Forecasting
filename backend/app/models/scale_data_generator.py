"""
Scale Data Generator - 50,000 Products
Generates 50,000 products with sales history for scalability testing.
"""

import csv
import random
from datetime import datetime, timedelta
import os

# Seed for reproducibility
random.seed(42)

# Categories for variety
CATEGORIES = [
    'Electronics', 'Apparel - Summer', 'Apparel - Winter', 'Home & Kitchen',
    'Office Supplies', 'Health & Beauty', 'Sports & Outdoors', 'Baby & Kids',
    'Automotive', 'Garden & Patio', 'Pet Supplies', 'Food & Grocery'
]

# Product name components for generating unique names
ADJECTIVES = [
    'Premium', 'Classic', 'Modern', 'Deluxe', 'Professional', 'Ultra',
    'Essential', 'Advanced', 'Compact', 'Portable', 'Heavy-Duty', 'Lightweight',
    'Eco-Friendly', 'Organic', 'Natural', 'Smart', 'Wireless', 'Digital',
    'Ergonomic', 'Adjustable', 'Foldable', 'Waterproof', 'Stainless', 'Bamboo'
]

CATEGORY_PRODUCTS = {
    'Electronics': ['Charger', 'Cable', 'Adapter', 'Speaker', 'Headphones', 'Mouse', 'Keyboard', 
                   'Monitor Stand', 'USB Hub', 'Power Bank', 'Webcam', 'Microphone', 'LED Light',
                   'Phone Case', 'Tablet Cover', 'Laptop Bag', 'Screen Protector', 'Battery Pack'],
    'Apparel - Summer': ['T-Shirt', 'Shorts', 'Sandals', 'Hat', 'Sunglasses', 'Tank Top', 
                        'Dress', 'Swimsuit', 'Beach Towel', 'Flip Flops', 'Polo Shirt', 'Skirt'],
    'Apparel - Winter': ['Jacket', 'Sweater', 'Coat', 'Gloves', 'Scarf', 'Beanie', 'Boots',
                        'Hoodie', 'Thermal Wear', 'Earmuffs', 'Vest', 'Cardigan'],
    'Home & Kitchen': ['Cookware Set', 'Blender', 'Toaster', 'Coffee Maker', 'Pan', 'Pot',
                      'Utensil Set', 'Cutting Board', 'Storage Container', 'Dish Rack', 'Towel Set'],
    'Office Supplies': ['Notebook', 'Pen Set', 'Stapler', 'Paper Clips', 'Desk Organizer',
                       'File Folder', 'Binder', 'Sticky Notes', 'Highlighters', 'Calculator'],
    'Health & Beauty': ['Shampoo', 'Conditioner', 'Body Lotion', 'Face Cream', 'Sunscreen',
                       'Lip Balm', 'Hair Brush', 'Makeup Kit', 'Vitamins', 'First Aid Kit'],
    'Sports & Outdoors': ['Yoga Mat', 'Dumbbells', 'Resistance Bands', 'Water Bottle', 
                         'Sports Bag', 'Running Shoes', 'Fitness Tracker', 'Tent', 'Backpack'],
    'Baby & Kids': ['Diapers', 'Baby Wipes', 'Bottle Set', 'Pacifier', 'Baby Monitor',
                   'Stroller Cover', 'Car Seat', 'Toy Set', 'Blanket', 'Onesie Pack'],
    'Automotive': ['Car Charger', 'Phone Mount', 'Seat Cover', 'Floor Mat', 'Air Freshener',
                  'Dash Cam', 'Jump Starter', 'Tool Kit', 'Tire Inflator', 'Car Cleaner'],
    'Garden & Patio': ['Plant Pot', 'Garden Gloves', 'Watering Can', 'Seeds Pack', 'Fertilizer',
                      'Pruning Shears', 'Lawn Chair', 'Umbrella', 'String Lights', 'Bird Feeder'],
    'Pet Supplies': ['Dog Food', 'Cat Food', 'Pet Bed', 'Leash', 'Collar', 'Toy Pack',
                    'Grooming Kit', 'Food Bowl', 'Litter Box', 'Pet Carrier'],
    'Food & Grocery': ['Coffee Beans', 'Tea Collection', 'Snack Box', 'Olive Oil', 'Honey',
                      'Spice Set', 'Pasta Pack', 'Rice Bag', 'Cereal', 'Protein Bar']
}

SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '2-Pack', '3-Pack', '5-Pack', '6ft', '10ft', '500ml', '1L']
COLORS = ['Black', 'White', 'Blue', 'Red', 'Green', 'Gray', 'Navy', 'Beige', 'Brown', 'Pink']


def generate_product_name(category: str, index: int) -> str:
    """Generate a unique product name."""
    adj = random.choice(ADJECTIVES)
    product = random.choice(CATEGORY_PRODUCTS.get(category, ['Item']))
    
    # Add variation
    if random.random() > 0.7:
        size = random.choice(SIZES)
        return f"{adj} {product} {size}"
    elif random.random() > 0.5:
        color = random.choice(COLORS)
        return f"{adj} {product} {color}"
    else:
        return f"{adj} {product} v{index % 100 + 1}"


def generate_50k_products(output_dir: str):
    """Generate 50,000 products with sales history."""
    
    # Output paths
    products_file = os.path.join(output_dir, 'products_50k.csv')
    sales_file = os.path.join(output_dir, 'sales_50k.csv')
    
    print("=" * 60)
    print("Generating 50,000 Products for Scalability Testing")
    print("=" * 60)
    
    products = []
    all_sales = []
    
    # Date range for sales history (1 year)
    end_date = datetime(2026, 2, 17)
    start_date = end_date - timedelta(days=365)
    
    # Stock distribution for realistic alerts
    # 70% healthy, 15% low, 9% critical, 6% out of stock
    stock_distribution = {
        'healthy': 0.70,    # 35,000 products
        'low': 0.15,        # 7,500 products  
        'critical': 0.09,   # 4,500 products
        'out_of_stock': 0.06  # 3,000 products
    }
    
    print(f"\nGenerating products...")
    
    for i in range(50000):
        if (i + 1) % 10000 == 0:
            print(f"  Generated {i + 1:,} products...")
        
        # Assign category
        category = CATEGORIES[i % len(CATEGORIES)]
        
        # Generate unique SKU
        sku = f"SKU-{str(i + 1).zfill(6)}"
        
        # Generate product name
        name = generate_product_name(category, i)
        
        # Price based on category
        base_prices = {
            'Electronics': (15, 200),
            'Apparel - Summer': (10, 80),
            'Apparel - Winter': (20, 150),
            'Home & Kitchen': (10, 100),
            'Office Supplies': (5, 50),
            'Health & Beauty': (8, 80),
            'Sports & Outdoors': (15, 120),
            'Baby & Kids': (10, 80),
            'Automotive': (10, 100),
            'Garden & Patio': (10, 80),
            'Pet Supplies': (8, 60),
            'Food & Grocery': (5, 40)
        }
        price_range = base_prices.get(category, (10, 100))
        unit_price = round(random.uniform(*price_range), 2)
        unit_cost = round(unit_price * random.uniform(0.4, 0.7), 2)
        
        # Determine stock level category
        rand_val = random.random()
        if rand_val < stock_distribution['out_of_stock']:
            current_stock = 0
        elif rand_val < stock_distribution['out_of_stock'] + stock_distribution['critical']:
            current_stock = random.randint(1, 20)
        elif rand_val < stock_distribution['out_of_stock'] + stock_distribution['critical'] + stock_distribution['low']:
            current_stock = random.randint(21, 50)
        else:
            current_stock = random.randint(51, 500)
        
        # Other attributes
        lead_time = random.randint(3, 14)
        avg_demand = round(random.uniform(2, 30), 1)
        reorder_point = int(avg_demand * lead_time * 1.2)
        safety_stock = int(avg_demand * lead_time * 0.3)
        
        products.append({
            'sku': sku,
            'name': name,
            'category': category,
            'unit_price': unit_price,
            'unit_cost': unit_cost,
            'current_stock': current_stock,
            'lead_time_days': lead_time,
            'reorder_point': reorder_point,
            'safety_stock': safety_stock,
            'average_daily_demand': avg_demand
        })
        
        # Generate sales history (reduced for 50k - just 30 days average per product)
        # This will create ~1.5M sales records
        num_sales_days = random.randint(20, 40)
        for _ in range(num_sales_days):
            sale_date = start_date + timedelta(days=random.randint(0, 365))
            quantity = max(1, int(random.gauss(avg_demand, avg_demand * 0.3)))
            revenue = round(quantity * unit_price, 2)
            
            all_sales.append({
                'sku': sku,
                'date': sale_date.strftime('%Y-%m-%d'),
                'quantity_sold': quantity,
                'revenue': revenue
            })
    
    print(f"\nTotal products: {len(products):,}")
    print(f"Total sales records: {len(all_sales):,}")
    
    # Write products CSV
    print(f"\nWriting products to {products_file}...")
    with open(products_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=products[0].keys())
        writer.writeheader()
        writer.writerows(products)
    
    # Write sales CSV
    print(f"Writing sales to {sales_file}...")
    with open(sales_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_sales[0].keys())
        writer.writeheader()
        writer.writerows(all_sales)
    
    # Summary statistics
    out_of_stock = sum(1 for p in products if p['current_stock'] == 0)
    critical = sum(1 for p in products if 0 < p['current_stock'] <= 20)
    low = sum(1 for p in products if 20 < p['current_stock'] <= 50)
    healthy = sum(1 for p in products if p['current_stock'] > 50)
    
    print("\n" + "=" * 60)
    print("Generation Complete!")
    print("=" * 60)
    print(f"\nStock Distribution:")
    print(f"  🔴 Out of Stock: {out_of_stock:,} ({out_of_stock/500:.1f}%)")
    print(f"  🟠 Critical (1-20): {critical:,} ({critical/500:.1f}%)")
    print(f"  🟡 Low (21-50): {low:,} ({low/500:.1f}%)")
    print(f"  🟢 Healthy (51+): {healthy:,} ({healthy/500:.1f}%)")
    print(f"\nFiles created:")
    print(f"  - {products_file}")
    print(f"  - {sales_file}")
    
    return products_file, sales_file


if __name__ == "__main__":
    # Run from project root
    import sys
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', '..', '..', '..', 'data')
    data_dir = os.path.abspath(data_dir)
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    generate_50k_products(data_dir)
