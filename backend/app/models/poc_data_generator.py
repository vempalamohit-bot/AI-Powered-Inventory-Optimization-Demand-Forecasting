"""
Comprehensive POC Data Generator
Generates 500 products with 2 years of sales history and realistic stock scenarios.

Stock Level Distribution (Business-Friendly):
- Healthy Stock (70%): Most products are well-stocked
- Low Stock (15%): Some products need attention soon
- Critical (9%): Fewer products in urgent need
- Out of Stock (6%): Minimal out-of-stock (less than critical)

This ensures business owner sees a manageable number of critical alerts.
"""

import csv
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import math

# Seed for reproducibility
random.seed(42)

# ============================================================================
# PRODUCT CATEGORIES AND BASE DATA
# ============================================================================

CATEGORIES = {
    'Electronics': {
        'items': [
            ('Wireless Earbuds', 79.99, 32, 'neutral'),
            ('Bluetooth Speaker', 49.99, 20, 'neutral'),
            ('Smart Watch', 199.99, 80, 'neutral'),
            ('Tablet Stand', 24.99, 10, 'neutral'),
            ('USB-C Hub', 39.99, 16, 'neutral'),
            ('Wireless Charger', 29.99, 12, 'neutral'),
            ('Power Bank 10000mAh', 34.99, 14, 'neutral'),
            ('Power Bank 20000mAh', 49.99, 20, 'neutral'),
            ('Phone Case Premium', 19.99, 8, 'neutral'),
            ('Screen Protector', 9.99, 4, 'neutral'),
            ('HDMI Cable 6ft', 12.99, 5, 'neutral'),
            ('Lightning Cable', 14.99, 6, 'neutral'),
            ('USB-C Cable', 11.99, 5, 'neutral'),
            ('Webcam HD', 59.99, 24, 'neutral'),
            ('Ring Light', 34.99, 14, 'neutral'),
            ('Laptop Sleeve', 24.99, 10, 'neutral'),
            ('Mouse Pad XL', 19.99, 8, 'neutral'),
            ('Keyboard Wireless', 44.99, 18, 'neutral'),
            ('Mouse Wireless', 29.99, 12, 'neutral'),
            ('Desk Lamp LED', 39.99, 16, 'neutral'),
        ],
        'base_demand': 25,
    },
    'Apparel - Summer': {
        'items': [
            ('Cotton T-Shirt White', 19.99, 8, 'summer'),
            ('Cotton T-Shirt Black', 19.99, 8, 'summer'),
            ('Cotton T-Shirt Navy', 19.99, 8, 'summer'),
            ('Polo Shirt Classic', 34.99, 14, 'summer'),
            ('Summer Dress Floral', 49.99, 20, 'summer'),
            ('Linen Pants', 44.99, 18, 'summer'),
            ('Shorts Khaki', 29.99, 12, 'summer'),
            ('Shorts Denim', 34.99, 14, 'summer'),
            ('Sandals Comfort', 39.99, 16, 'summer'),
            ('Flip Flops', 14.99, 6, 'summer'),
            ('Beach Towel', 24.99, 10, 'summer'),
            ('Swim Trunks', 29.99, 12, 'summer'),
            ('Swimsuit One-Piece', 44.99, 18, 'summer'),
            ('Sun Hat Wide Brim', 24.99, 10, 'summer'),
            ('Baseball Cap', 19.99, 8, 'summer'),
            ('Sunglasses Polarized', 49.99, 20, 'summer'),
            ('Tank Top', 14.99, 6, 'summer'),
            ('Crop Top', 19.99, 8, 'summer'),
            ('Maxi Skirt', 39.99, 16, 'summer'),
            ('Romper', 44.99, 18, 'summer'),
        ],
        'base_demand': 40,
    },
    'Apparel - Winter': {
        'items': [
            ('Winter Jacket Puffer', 89.99, 36, 'winter'),
            ('Wool Coat Classic', 129.99, 52, 'winter'),
            ('Fleece Hoodie', 49.99, 20, 'winter'),
            ('Thermal Underwear Set', 34.99, 14, 'winter'),
            ('Wool Sweater Cable Knit', 59.99, 24, 'winter'),
            ('Cashmere Scarf', 44.99, 18, 'winter'),
            ('Leather Gloves', 39.99, 16, 'winter'),
            ('Knit Gloves', 14.99, 6, 'winter'),
            ('Beanie Wool', 19.99, 8, 'winter'),
            ('Earmuffs', 14.99, 6, 'winter'),
            ('Winter Boots Waterproof', 79.99, 32, 'winter'),
            ('Snow Boots', 89.99, 36, 'winter'),
            ('Thick Socks 3-Pack', 14.99, 6, 'winter'),
            ('Thermal Socks', 12.99, 5, 'winter'),
            ('Down Vest', 59.99, 24, 'winter'),
            ('Flannel Shirt', 34.99, 14, 'winter'),
            ('Corduroy Pants', 49.99, 20, 'winter'),
            ('Wool Trousers', 64.99, 26, 'winter'),
            ('Turtleneck Sweater', 44.99, 18, 'winter'),
            ('Cardigan Long', 54.99, 22, 'winter'),
        ],
        'base_demand': 35,
    },
    'Beverages - Cold': {
        'items': [
            ('Iced Coffee Concentrate', 12.99, 5, 'summer'),
            ('Cold Brew Coffee', 14.99, 6, 'summer'),
            ('Lemonade Fresh', 4.99, 2, 'summer'),
            ('Iced Tea Peach', 3.99, 1.5, 'summer'),
            ('Iced Tea Green', 3.99, 1.5, 'summer'),
            ('Energy Drink Original', 2.99, 1.2, 'summer'),
            ('Energy Drink Sugar-Free', 2.99, 1.2, 'summer'),
            ('Sports Drink Blue', 2.49, 1, 'summer'),
            ('Sports Drink Orange', 2.49, 1, 'summer'),
            ('Coconut Water Pure', 4.99, 2, 'summer'),
            ('Sparkling Water Lime', 1.99, 0.8, 'summer'),
            ('Sparkling Water Berry', 1.99, 0.8, 'summer'),
            ('Fruit Smoothie Mango', 5.99, 2.4, 'summer'),
            ('Fruit Smoothie Berry', 5.99, 2.4, 'summer'),
            ('Protein Shake Vanilla', 4.99, 2, 'summer'),
            ('Protein Shake Chocolate', 4.99, 2, 'summer'),
            ('Fresh Orange Juice', 5.99, 2.4, 'summer'),
            ('Apple Juice Organic', 4.99, 2, 'summer'),
            ('Kombucha Original', 4.49, 1.8, 'summer'),
            ('Kombucha Ginger', 4.49, 1.8, 'summer'),
        ],
        'base_demand': 80,
    },
    'Beverages - Hot': {
        'items': [
            ('Premium Coffee Beans', 14.99, 6, 'winter'),
            ('Coffee Ground Medium', 11.99, 5, 'winter'),
            ('Espresso Beans Dark', 16.99, 7, 'winter'),
            ('Hot Cocoa Mix', 7.99, 3, 'winter'),
            ('Hot Cocoa Premium', 12.99, 5, 'winter'),
            ('Green Tea Bags', 8.99, 3.5, 'winter'),
            ('Black Tea English', 9.99, 4, 'winter'),
            ('Herbal Tea Chamomile', 7.99, 3, 'winter'),
            ('Chai Tea Spiced', 9.99, 4, 'winter'),
            ('Matcha Powder', 24.99, 10, 'winter'),
            ('Apple Cider Mix', 6.99, 2.8, 'winter'),
            ('Mulled Wine Spices', 8.99, 3.5, 'winter'),
            ('Instant Coffee', 8.99, 3.5, 'winter'),
            ('Decaf Coffee Ground', 12.99, 5, 'winter'),
            ('Earl Grey Tea', 9.99, 4, 'winter'),
            ('Peppermint Tea', 7.99, 3, 'winter'),
            ('Ginger Tea', 8.99, 3.5, 'winter'),
            ('Turmeric Latte Mix', 11.99, 5, 'winter'),
            ('Coffee Creamer Vanilla', 5.99, 2.4, 'winter'),
            ('Coffee Creamer Hazelnut', 5.99, 2.4, 'winter'),
        ],
        'base_demand': 60,
    },
    'Personal Care - Summer': {
        'items': [
            ('Sunscreen SPF 30', 12.99, 5, 'summer'),
            ('Sunscreen SPF 50', 14.99, 6, 'summer'),
            ('Sunscreen Sport', 16.99, 7, 'summer'),
            ('After Sun Lotion', 9.99, 4, 'summer'),
            ('Aloe Vera Gel', 8.99, 3.5, 'summer'),
            ('Bug Spray Natural', 10.99, 4.5, 'summer'),
            ('Bug Spray DEET', 8.99, 3.5, 'summer'),
            ('Citronella Candles', 14.99, 6, 'summer'),
            ('Cooling Face Mist', 12.99, 5, 'summer'),
            ('SPF Lip Balm', 4.99, 2, 'summer'),
            ('Deodorant Sport', 6.99, 2.8, 'summer'),
            ('Body Spray Fresh', 9.99, 4, 'summer'),
            ('Dry Shampoo', 8.99, 3.5, 'summer'),
            ('Face Wipes Cooling', 7.99, 3, 'summer'),
            ('Blotting Papers', 5.99, 2.4, 'summer'),
            ('Tanning Oil', 11.99, 5, 'summer'),
            ('Self-Tanner Lotion', 14.99, 6, 'summer'),
            ('Hair Protector UV', 12.99, 5, 'summer'),
            ('Foot Spray Cool', 7.99, 3, 'summer'),
            ('Body Powder', 8.99, 3.5, 'summer'),
        ],
        'base_demand': 45,
    },
    'Personal Care - Winter': {
        'items': [
            ('Moisturizing Lotion', 11.99, 5, 'winter'),
            ('Body Butter Shea', 14.99, 6, 'winter'),
            ('Hand Cream Intensive', 8.99, 3.5, 'winter'),
            ('Lip Balm Intensive', 4.99, 2, 'winter'),
            ('Lip Balm Tinted', 6.99, 2.8, 'winter'),
            ('Cuticle Oil', 7.99, 3, 'winter'),
            ('Foot Cream', 9.99, 4, 'winter'),
            ('Face Moisturizer Rich', 24.99, 10, 'winter'),
            ('Night Cream Hydrating', 29.99, 12, 'winter'),
            ('Face Oil Rosehip', 19.99, 8, 'winter'),
            ('Humidifier Essential', 34.99, 14, 'winter'),
            ('Essential Oil Eucalyptus', 12.99, 5, 'winter'),
            ('Bath Salts Lavender', 14.99, 6, 'winter'),
            ('Bubble Bath Relax', 9.99, 4, 'winter'),
            ('Shower Gel Moisturizing', 8.99, 3.5, 'winter'),
            ('Body Scrub Sugar', 12.99, 5, 'winter'),
            ('Hair Mask Deep', 14.99, 6, 'winter'),
            ('Scalp Treatment', 16.99, 7, 'winter'),
            ('Beard Oil', 14.99, 6, 'winter'),
            ('Beard Balm', 12.99, 5, 'winter'),
        ],
        'base_demand': 50,
    },
    'Snacks & Confectionery': {
        'items': [
            ('Chocolate Bar Dark', 3.99, 1.5, 'winter'),
            ('Chocolate Bar Milk', 3.49, 1.4, 'winter'),
            ('Chocolate Truffles', 12.99, 5, 'winter'),
            ('Gummy Bears', 4.99, 2, 'neutral'),
            ('Sour Candy Mix', 4.49, 1.8, 'neutral'),
            ('Hard Candy Assorted', 5.99, 2.4, 'neutral'),
            ('Lollipops Pack', 3.99, 1.5, 'neutral'),
            ('Potato Chips Classic', 3.99, 1.5, 'neutral'),
            ('Potato Chips BBQ', 3.99, 1.5, 'neutral'),
            ('Tortilla Chips', 4.49, 1.8, 'neutral'),
            ('Popcorn Butter', 4.99, 2, 'neutral'),
            ('Popcorn Caramel', 5.99, 2.4, 'neutral'),
            ('Mixed Nuts Salted', 9.99, 4, 'neutral'),
            ('Almonds Roasted', 8.99, 3.5, 'neutral'),
            ('Cashews Raw', 11.99, 5, 'neutral'),
            ('Trail Mix Energy', 7.99, 3, 'neutral'),
            ('Granola Bars 6-Pack', 5.99, 2.4, 'neutral'),
            ('Protein Bars 4-Pack', 11.99, 5, 'neutral'),
            ('Dried Mango', 6.99, 2.8, 'neutral'),
            ('Beef Jerky', 8.99, 3.5, 'neutral'),
        ],
        'base_demand': 55,
    },
    'Home & Kitchen': {
        'items': [
            ('Kitchen Towels 3-Roll', 8.99, 3.5, 'neutral'),
            ('Paper Napkins 200ct', 6.99, 2.8, 'neutral'),
            ('Trash Bags 30ct', 9.99, 4, 'neutral'),
            ('Dish Soap Lemon', 4.99, 2, 'neutral'),
            ('Sponges 6-Pack', 5.99, 2.4, 'neutral'),
            ('All-Purpose Cleaner', 6.99, 2.8, 'neutral'),
            ('Glass Cleaner', 5.99, 2.4, 'neutral'),
            ('Laundry Detergent', 14.99, 6, 'neutral'),
            ('Fabric Softener', 9.99, 4, 'neutral'),
            ('Dryer Sheets 80ct', 7.99, 3, 'neutral'),
            ('Air Freshener Spray', 5.99, 2.4, 'neutral'),
            ('Candle Scented Large', 19.99, 8, 'neutral'),
            ('Candle Scented Small', 9.99, 4, 'neutral'),
            ('Storage Containers Set', 24.99, 10, 'neutral'),
            ('Reusable Bags 5-Pack', 12.99, 5, 'neutral'),
            ('Bento Box Adult', 19.99, 8, 'neutral'),
            ('Water Filter Pitcher', 29.99, 12, 'neutral'),
            ('Ice Cube Trays 2-Pack', 8.99, 3.5, 'neutral'),
            ('Cutting Board Bamboo', 14.99, 6, 'neutral'),
            ('Kitchen Timer Digital', 9.99, 4, 'neutral'),
        ],
        'base_demand': 35,
    },
    'Sports & Fitness': {
        'items': [
            ('Yoga Mat Premium', 34.99, 14, 'neutral'),
            ('Resistance Bands Set', 19.99, 8, 'neutral'),
            ('Dumbbells 5lb Pair', 24.99, 10, 'neutral'),
            ('Dumbbells 10lb Pair', 34.99, 14, 'neutral'),
            ('Jump Rope Speed', 12.99, 5, 'neutral'),
            ('Exercise Ball 65cm', 24.99, 10, 'neutral'),
            ('Foam Roller', 19.99, 8, 'neutral'),
            ('Ab Wheel', 14.99, 6, 'neutral'),
            ('Fitness Tracker Band', 49.99, 20, 'neutral'),
            ('Sports Bottle 32oz', 14.99, 6, 'neutral'),
            ('Gym Bag Duffle', 34.99, 14, 'neutral'),
            ('Workout Gloves', 19.99, 8, 'neutral'),
            ('Sweatband Set', 9.99, 4, 'neutral'),
            ('Tennis Balls 3-Pack', 7.99, 3, 'summer'),
            ('Basketball Official', 29.99, 12, 'summer'),
            ('Soccer Ball Size 5', 24.99, 10, 'summer'),
            ('Volleyball Beach', 19.99, 8, 'summer'),
            ('Frisbee Pro', 14.99, 6, 'summer'),
            ('Badminton Set', 29.99, 12, 'summer'),
            ('Golf Balls 12-Pack', 24.99, 10, 'summer'),
        ],
        'base_demand': 30,
    },
    'Outdoor & Garden': {
        'items': [
            ('Garden Gloves', 9.99, 4, 'spring'),
            ('Pruning Shears', 14.99, 6, 'spring'),
            ('Watering Can 2 Gal', 12.99, 5, 'spring'),
            ('Plant Pots 4-Pack', 19.99, 8, 'spring'),
            ('Potting Soil 10lb', 11.99, 5, 'spring'),
            ('Seeds Vegetable Mix', 4.99, 2, 'spring'),
            ('Seeds Flower Mix', 4.99, 2, 'spring'),
            ('Bird Feeder', 24.99, 10, 'spring'),
            ('Bird Seed 5lb', 9.99, 4, 'spring'),
            ('Outdoor String Light', 29.99, 12, 'summer'),
            ('Solar Garden Lights', 19.99, 8, 'summer'),
            ('Citronella Torch', 14.99, 6, 'summer'),
            ('Picnic Blanket', 24.99, 10, 'summer'),
            ('Cooler Soft 24-Can', 34.99, 14, 'summer'),
            ('BBQ Tools Set', 29.99, 12, 'summer'),
            ('Camping Chair Fold', 29.99, 12, 'summer'),
            ('Tent 2-Person', 89.99, 36, 'summer'),
            ('Sleeping Bag', 49.99, 20, 'summer'),
            ('Flashlight LED', 14.99, 6, 'neutral'),
            ('First Aid Kit Outdoor', 24.99, 10, 'neutral'),
        ],
        'base_demand': 25,
    },
    'Baby & Kids': {
        'items': [
            ('Baby Wipes 80ct', 5.99, 2.4, 'neutral'),
            ('Diapers Size 3 32ct', 14.99, 6, 'neutral'),
            ('Diapers Size 4 28ct', 14.99, 6, 'neutral'),
            ('Baby Lotion', 7.99, 3, 'neutral'),
            ('Baby Shampoo', 6.99, 2.8, 'neutral'),
            ('Baby Powder', 5.99, 2.4, 'neutral'),
            ('Sippy Cup 2-Pack', 9.99, 4, 'neutral'),
            ('Baby Bottles 3-Pack', 14.99, 6, 'neutral'),
            ('Pacifiers 2-Pack', 7.99, 3, 'neutral'),
            ('Teething Ring', 6.99, 2.8, 'neutral'),
            ('Baby Food Pouch 6ct', 8.99, 3.5, 'neutral'),
            ('Baby Cereal', 5.99, 2.4, 'neutral'),
            ('Kids Toothpaste', 4.99, 2, 'neutral'),
            ('Kids Shampoo', 6.99, 2.8, 'neutral'),
            ('Kids Vitamins Gummy', 12.99, 5, 'neutral'),
            ('Crayons 64ct', 5.99, 2.4, 'neutral'),
            ('Colored Pencils 24ct', 7.99, 3, 'neutral'),
            ('Play-Doh 4-Pack', 9.99, 4, 'neutral'),
            ('Building Blocks Set', 19.99, 8, 'neutral'),
            ('Stuffed Animal', 14.99, 6, 'neutral'),
        ],
        'base_demand': 40,
    },
    'Pet Supplies': {
        'items': [
            ('Dog Food Dry 5lb', 14.99, 6, 'neutral'),
            ('Dog Food Wet 6-Pack', 12.99, 5, 'neutral'),
            ('Dog Treats Biscuits', 7.99, 3, 'neutral'),
            ('Dog Treats Jerky', 9.99, 4, 'neutral'),
            ('Cat Food Dry 4lb', 12.99, 5, 'neutral'),
            ('Cat Food Wet 12-Pack', 14.99, 6, 'neutral'),
            ('Cat Treats Crunchy', 5.99, 2.4, 'neutral'),
            ('Cat Litter 20lb', 16.99, 7, 'neutral'),
            ('Dog Toy Rope', 9.99, 4, 'neutral'),
            ('Dog Toy Ball', 7.99, 3, 'neutral'),
            ('Cat Toy Mouse 3-Pack', 6.99, 2.8, 'neutral'),
            ('Cat Scratching Post', 24.99, 10, 'neutral'),
            ('Pet Bed Small', 29.99, 12, 'neutral'),
            ('Pet Bed Large', 44.99, 18, 'neutral'),
            ('Dog Collar Adjustable', 12.99, 5, 'neutral'),
            ('Dog Leash 6ft', 14.99, 6, 'neutral'),
            ('Pet Shampoo', 9.99, 4, 'neutral'),
            ('Pet Brush', 11.99, 5, 'neutral'),
            ('Fish Food Flakes', 6.99, 2.8, 'neutral'),
            ('Aquarium Filter', 19.99, 8, 'neutral'),
        ],
        'base_demand': 45,
    },
    'Health & Wellness': {
        'items': [
            ('Multivitamin Daily', 14.99, 6, 'neutral'),
            ('Vitamin C 1000mg', 11.99, 5, 'neutral'),
            ('Vitamin D 2000IU', 12.99, 5, 'neutral'),
            ('Fish Oil Omega-3', 16.99, 7, 'neutral'),
            ('Probiotic 30-Day', 24.99, 10, 'neutral'),
            ('Melatonin 5mg', 9.99, 4, 'neutral'),
            ('Pain Reliever 100ct', 8.99, 3.5, 'neutral'),
            ('Cold Medicine Day', 9.99, 4, 'winter'),
            ('Cold Medicine Night', 9.99, 4, 'winter'),
            ('Cough Drops 30ct', 5.99, 2.4, 'winter'),
            ('Tissues Box 3-Pack', 8.99, 3.5, 'winter'),
            ('Hand Sanitizer 8oz', 5.99, 2.4, 'neutral'),
            ('Bandages Assorted', 6.99, 2.8, 'neutral'),
            ('Thermometer Digital', 12.99, 5, 'neutral'),
            ('Blood Pressure Monitor', 49.99, 20, 'neutral'),
            ('Heating Pad', 29.99, 12, 'winter'),
            ('Ice Pack Reusable', 9.99, 4, 'neutral'),
            ('Eye Drops', 8.99, 3.5, 'neutral'),
            ('Allergy Medicine', 14.99, 6, 'spring'),
            ('Nasal Spray', 9.99, 4, 'winter'),
        ],
        'base_demand': 50,
    },
    'Office & School': {
        'items': [
            ('Notebooks 3-Pack', 9.99, 4, 'neutral'),
            ('Pens Black 12-Pack', 7.99, 3, 'neutral'),
            ('Pencils 24-Pack', 5.99, 2.4, 'neutral'),
            ('Highlighters 6-Pack', 6.99, 2.8, 'neutral'),
            ('Sticky Notes 4-Pack', 8.99, 3.5, 'neutral'),
            ('Paper Clips 200ct', 3.99, 1.5, 'neutral'),
            ('Binder Clips 48ct', 5.99, 2.4, 'neutral'),
            ('Stapler Desktop', 12.99, 5, 'neutral'),
            ('Staples 5000ct', 4.99, 2, 'neutral'),
            ('Tape Dispenser', 8.99, 3.5, 'neutral'),
            ('Scissors Office', 6.99, 2.8, 'neutral'),
            ('Calculator Basic', 9.99, 4, 'neutral'),
            ('Ruler 12 inch', 2.99, 1.2, 'neutral'),
            ('Eraser Pack', 3.99, 1.5, 'neutral'),
            ('Folder Manila 25-Pack', 11.99, 5, 'neutral'),
            ('Binder 1.5 inch', 7.99, 3, 'neutral'),
            ('Index Cards 100ct', 3.99, 1.5, 'neutral'),
            ('Planner Weekly', 14.99, 6, 'neutral'),
            ('Desk Organizer', 19.99, 8, 'neutral'),
            ('Whiteboard Small', 24.99, 10, 'neutral'),
        ],
        'base_demand': 35,
    },
}

# ============================================================================
# STOCK SCENARIO DISTRIBUTION (Business-Friendly)
# ============================================================================

# Distribution ensures: Low Stock > Critical > Out of Stock (less shocking for owner)
# NOTE: "Severity" is calculated by AI based on buffer_days = days_until_stockout - lead_time
# buffer_days < 0: CRITICAL (will have gap), buffer_days 0-3: HIGH, buffer_days 4-7: WARNING
STOCK_SCENARIOS = {
    'HEALTHY': 0.78,      # 78% - Well stocked (390 products) - buffer_days > 14
    'LOW_STOCK': 0.12,    # 12% - Needs attention (60 products) - buffer_days 4-7 (WARNING)
    'CRITICAL': 0.06,     # 6% - Urgent (30 products) - buffer_days 0-3 (HIGH/CRITICAL)
    'OUT_OF_STOCK': 0.04  # 4% - Out of stock (20 products) - STOCKOUT
}


def get_season_multiplier(month: int, season: str) -> float:
    """Calculate sales multiplier based on season"""
    summer_months = [5, 6, 7, 8]
    winter_months = [11, 12, 1, 2]
    spring_months = [3, 4]
    fall_months = [9, 10]
    
    if season == 'summer':
        if month in summer_months:
            return random.uniform(1.8, 2.5)
        elif month in winter_months:
            return random.uniform(0.3, 0.5)
        else:
            return random.uniform(0.8, 1.2)
    
    elif season == 'winter':
        if month in winter_months:
            return random.uniform(1.8, 2.5)
        elif month in summer_months:
            return random.uniform(0.3, 0.5)
        else:
            return random.uniform(0.8, 1.2)
    
    elif season == 'spring':
        if month in spring_months:
            return random.uniform(1.6, 2.2)
        elif month in fall_months:
            return random.uniform(0.5, 0.7)
        else:
            return random.uniform(0.8, 1.1)
    
    else:  # neutral
        return random.uniform(0.9, 1.1)


def get_day_multiplier(day_of_week: int, is_holiday: bool) -> float:
    """Calculate sales multiplier based on day of week"""
    if is_holiday:
        return random.uniform(1.5, 2.5)
    elif day_of_week >= 5:  # Weekend
        return random.uniform(1.3, 1.6)
    elif day_of_week == 4:  # Friday
        return random.uniform(1.1, 1.3)
    else:  # Mon-Thu
        return random.uniform(0.8, 1.0)


def get_trend_multiplier(days_ago: int, total_days: int) -> float:
    """Gradual growth trend over time"""
    progress = 1 - (days_ago / total_days)  # 0 at start, 1 at end
    return 1 + (progress * 0.3)  # 0% to 30% growth


def generate_products() -> List[Dict]:
    """Generate 500 products with realistic attributes"""
    products = []
    product_id = 1
    
    # Calculate products per category to reach ~500
    total_items = sum(len(cat['items']) for cat in CATEGORIES.values())
    
    for category_name, category_data in CATEGORIES.items():
        # Clean category name (remove season suffix for display)
        display_category = category_name.split(' - ')[0]
        
        for item_name, price, cost, season in category_data['items']:
            # Generate SKU
            sku = f"SKU{product_id:05d}"
            
            # Calculate lead time (3-14 days based on category)
            if 'Electronics' in category_name:
                lead_time = random.randint(7, 14)
            elif 'Beverage' in category_name:
                lead_time = random.randint(2, 5)
            else:
                lead_time = random.randint(3, 10)
            
            # Base daily demand
            base_demand = category_data['base_demand']
            daily_demand_avg = base_demand + random.randint(-10, 15)
            
            products.append({
                'id': product_id,
                'sku': sku,
                'name': item_name,
                'category': display_category,
                'price': price,
                'cost': cost,
                'season': season,
                'lead_time': lead_time,
                'base_demand': daily_demand_avg,
            })
            
            product_id += 1
    
    # If we need more products to reach 500, duplicate with variations
    while len(products) < 500:
        base_product = random.choice(products[:300])
        variant_num = len([p for p in products if base_product['name'] in p['name']]) + 1
        
        new_product = base_product.copy()
        new_product['id'] = product_id
        new_product['sku'] = f"SKU{product_id:05d}"
        new_product['name'] = f"{base_product['name']} V{variant_num}"
        new_product['price'] = round(base_product['price'] * random.uniform(0.9, 1.1), 2)
        new_product['cost'] = round(base_product['cost'] * random.uniform(0.9, 1.1), 2)
        
        products.append(new_product)
        product_id += 1
    
    return products[:500]


def assign_stock_scenarios(products: List[Dict]) -> List[Dict]:
    """
    Assign stock levels ensuring realistic distribution based on AI alert thresholds.
    
    CRITICAL decision is based on: buffer_days = days_until_stockout - lead_time
    - buffer_days < 0: CRITICAL (stockout before delivery even if ordered today)
    - buffer_days 0-3: HIGH urgency
    - buffer_days 4-7: WARNING (order soon)
    - buffer_days > 7: HEALTHY
    """
    
    total = len(products)
    
    # Calculate exact counts
    healthy_count = int(total * STOCK_SCENARIOS['HEALTHY'])
    low_stock_count = int(total * STOCK_SCENARIOS['LOW_STOCK'])
    critical_count = int(total * STOCK_SCENARIOS['CRITICAL'])
    out_of_stock_count = total - healthy_count - low_stock_count - critical_count
    
    # Shuffle products for random assignment
    shuffled_indices = list(range(total))
    random.shuffle(shuffled_indices)
    
    scenario_assignments = []
    scenario_assignments.extend(['HEALTHY'] * healthy_count)
    scenario_assignments.extend(['LOW_STOCK'] * low_stock_count)
    scenario_assignments.extend(['CRITICAL'] * critical_count)
    scenario_assignments.extend(['OUT_OF_STOCK'] * out_of_stock_count)
    
    for i, idx in enumerate(shuffled_indices):
        product = products[idx]
        scenario = scenario_assignments[i]
        daily_demand = product['base_demand']
        lead_time = product['lead_time']
        
        # Safety stock = 3 days of demand
        safety_stock = daily_demand * 3
        # Reorder point = lead time demand + safety stock
        reorder_point = (daily_demand * lead_time) + safety_stock
        
        # Stock calculation based on desired buffer_days
        # buffer_days = (current_stock / daily_demand) - lead_time
        # So: current_stock = daily_demand * (buffer_days + lead_time)
        
        if scenario == 'HEALTHY':
            # Buffer days > 14 (plenty of time)
            buffer_days = random.randint(14, 30)
            current_stock = int(daily_demand * (buffer_days + lead_time))
        
        elif scenario == 'LOW_STOCK':
            # Buffer days 5-10 days (WARNING level - order soon)
            buffer_days = random.randint(5, 10)
            current_stock = int(daily_demand * (buffer_days + lead_time))
        
        elif scenario == 'CRITICAL':
            # Buffer days 1-4 (HIGH severity - order this week)
            buffer_days = random.randint(1, 4)
            current_stock = int(daily_demand * (buffer_days + lead_time))
        
        else:  # OUT_OF_STOCK
            current_stock = 0
        
        product['current_stock'] = current_stock
        product['reorder_point'] = int(reorder_point)
        product['safety_stock'] = int(safety_stock)
        product['scenario'] = scenario
    
    return products


def generate_sales_history(products: List[Dict], days: int = 730) -> List[Dict]:
    """Generate 2 years (730 days) of sales history"""
    sales = []
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today - timedelta(days=days)
    
    # Holiday dates (major US holidays)
    holidays = []
    for year in [today.year - 2, today.year - 1, today.year]:
        holidays.extend([
            datetime(year, 1, 1),    # New Year
            datetime(year, 2, 14),   # Valentine's
            datetime(year, 7, 4),    # July 4th
            datetime(year, 10, 31),  # Halloween
            datetime(year, 11, 25),  # Thanksgiving (approx)
            datetime(year, 12, 25),  # Christmas
            datetime(year, 12, 26),  # Boxing Day
        ])
    
    for product in products:
        product_id = product['id']
        sku = product['sku']
        base_demand = product['base_demand']
        season = product['season']
        price = product['price']
        cost = product['cost']
        
        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)
            day_of_week = current_date.weekday()
            month = current_date.month
            
            # Check if holiday
            is_holiday = any(
                abs((current_date - h).days) <= 1 
                for h in holidays 
                if h.year == current_date.year
            )
            
            # Calculate multipliers
            season_mult = get_season_multiplier(month, season)
            day_mult = get_day_multiplier(day_of_week, is_holiday)
            trend_mult = get_trend_multiplier(days - day_offset, days)
            
            # Random noise
            noise = random.uniform(0.7, 1.3)
            
            # Final quantity
            quantity = int(base_demand * season_mult * day_mult * trend_mult * noise)
            quantity = max(0, quantity)  # No negative sales
            
            # Some days might have 0 sales (realistic)
            if random.random() < 0.05:  # 5% chance of no sales
                quantity = 0
            
            if quantity > 0:
                revenue = round(quantity * price, 2)
                cost_total = round(quantity * cost, 2)
                
                sales.append({
                    'product_id': product_id,
                    'sku': sku,
                    'date': current_date.strftime('%Y-%m-%d'),
                    'quantity': quantity,
                    'revenue': revenue,
                    'cost': cost_total,
                    'profit': round(revenue - cost_total, 2)
                })
    
    return sales


def write_products_csv(products: List[Dict], filepath: str):
    """Write products to CSV file - column names match API expectations"""
    fieldnames = ['sku', 'name', 'category', 'unit_price', 'unit_cost', 'current_stock', 
                  'reorder_point', 'lead_time_days', 'safety_stock']
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for p in products:
            writer.writerow({
                'sku': p['sku'],
                'name': p['name'],
                'category': p['category'],
                'unit_price': p['price'],
                'unit_cost': p['cost'],
                'current_stock': p['current_stock'],
                'reorder_point': p['reorder_point'],
                'lead_time_days': p['lead_time'],
                'safety_stock': p['safety_stock']
            })
    
    print(f"✅ Products CSV written: {filepath}")


def write_sales_csv(sales: List[Dict], filepath: str):
    """Write sales history to CSV file - column names match API expectations"""
    fieldnames = ['sku', 'date', 'quantity_sold', 'revenue']
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for s in sales:
            writer.writerow({
                'sku': s['sku'],
                'date': s['date'],
                'quantity_sold': s['quantity'],
                'revenue': s['revenue']
            })
    
    print(f"✅ Sales CSV written: {filepath}")


def print_summary(products: List[Dict]):
    """Print summary statistics"""
    scenarios = {}
    for p in products:
        s = p['scenario']
        scenarios[s] = scenarios.get(s, 0) + 1
    
    print("\n" + "="*60)
    print("📊 DATA GENERATION SUMMARY")
    print("="*60)
    print(f"\n📦 Total Products: {len(products)}")
    print(f"\n🏷️ Stock Level Distribution:")
    print(f"   ✅ Healthy Stock:  {scenarios.get('HEALTHY', 0):,} ({scenarios.get('HEALTHY', 0)/len(products)*100:.1f}%)")
    print(f"   ⚠️  Low Stock:     {scenarios.get('LOW_STOCK', 0):,} ({scenarios.get('LOW_STOCK', 0)/len(products)*100:.1f}%)")
    print(f"   🔴 Critical:       {scenarios.get('CRITICAL', 0):,} ({scenarios.get('CRITICAL', 0)/len(products)*100:.1f}%)")
    print(f"   ❌ Out of Stock:   {scenarios.get('OUT_OF_STOCK', 0):,} ({scenarios.get('OUT_OF_STOCK', 0)/len(products)*100:.1f}%)")
    
    print(f"\n📈 Verification:")
    print(f"   Critical ({scenarios.get('CRITICAL', 0)}) < Low Stock ({scenarios.get('LOW_STOCK', 0)}): {'✅ YES' if scenarios.get('CRITICAL', 0) < scenarios.get('LOW_STOCK', 0) else '❌ NO'}")
    print(f"   Out of Stock ({scenarios.get('OUT_OF_STOCK', 0)}) < Critical ({scenarios.get('CRITICAL', 0)}): {'✅ YES' if scenarios.get('OUT_OF_STOCK', 0) < scenarios.get('CRITICAL', 0) else '❌ NO'}")
    
    # Category distribution
    categories = {}
    for p in products:
        c = p['category']
        categories[c] = categories.get(c, 0) + 1
    
    print(f"\n📁 Categories ({len(categories)}):")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count} products")


if __name__ == "__main__":
    import os
    
    # Generate data
    print("🔄 Generating 500 products...")
    products = generate_products()
    
    print("🔄 Assigning stock scenarios...")
    products = assign_stock_scenarios(products)
    
    print("🔄 Generating 2 years of sales history (this may take a moment)...")
    sales = generate_sales_history(products, days=730)
    
    # Get script directory for output
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(script_dir))), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    products_path = os.path.join(data_dir, 'poc_500_products.csv')
    sales_path = os.path.join(data_dir, 'poc_2years_sales.csv')
    
    # Write CSVs
    write_products_csv(products, products_path)
    write_sales_csv(sales, sales_path)
    
    # Print summary
    print_summary(products)
    
    print(f"\n📄 Files created:")
    print(f"   Products: {products_path}")
    print(f"   Sales:    {sales_path}")
    print(f"\n🎉 Data generation complete!")
