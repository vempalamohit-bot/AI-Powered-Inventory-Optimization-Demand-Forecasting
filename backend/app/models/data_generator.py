"""
Smart Data Generator + HyperLocal Signals
Generates realistic sample data + enriches with external signals
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd
import numpy as np

class SmartDataGenerator:
    """Generate realistic sales data with patterns"""
    
    @staticmethod
    def generate_sales(days: int = 90) -> List[Dict]:
        """Generate N days of realistic sales data (default 90)"""
        
        sales = []
        start_date = datetime.now() - timedelta(days=days)
        
        # Define 50 realistic products with different patterns
        products = {
            # ===== Beverages (Summer) =====
            'ICE_CREAM': {'base': 100, 'price': 5, 'cost': 2, 'seasonal': 'summer', 'category': 'Beverage', 'description': 'Premium Ice Cream'},
            'ENERGY_DRINK': {'base': 200, 'price': 2, 'cost': 0.8, 'seasonal': 'summer', 'category': 'Beverage', 'description': 'Energy Drink'},
            'ICED_TEA': {'base': 150, 'price': 3.5, 'cost': 1.2, 'seasonal': 'summer', 'category': 'Beverage', 'description': 'Iced Tea'},
            'LEMONADE': {'base': 120, 'price': 2.5, 'cost': 0.8, 'seasonal': 'summer', 'category': 'Beverage', 'description': 'Fresh Lemonade'},
            'SMOOTHIE': {'base': 110, 'price': 6, 'cost': 2.5, 'seasonal': 'summer', 'category': 'Beverage', 'description': 'Fruit Smoothie'},
            'SPORTS_DRINK': {'base': 180, 'price': 2.8, 'cost': 0.9, 'seasonal': 'summer', 'category': 'Beverage', 'description': 'Sports Drink'},
            'COCONUT_WATER': {'base': 95, 'price': 4, 'cost': 1.5, 'seasonal': 'summer', 'category': 'Beverage', 'description': 'Coconut Water'},
            'JUICE': {'base': 140, 'price': 3.2, 'cost': 1, 'seasonal': 'summer', 'category': 'Beverage', 'description': 'Fresh Juice'},
            
            # ===== Beverages (Winter) =====
            'HOT_COCOA': {'base': 150, 'price': 3, 'cost': 1.2, 'seasonal': 'winter', 'category': 'Beverage', 'description': 'Hot Cocoa'},
            'COFFEE': {'base': 250, 'price': 4.5, 'cost': 1.5, 'seasonal': 'winter', 'category': 'Beverage', 'description': 'Premium Coffee'},
            'TEA': {'base': 180, 'price': 2.5, 'cost': 0.8, 'seasonal': 'winter', 'category': 'Beverage', 'description': 'Premium Tea'},
            'HOT_APPLE_CIDER': {'base': 130, 'price': 3.5, 'cost': 1.3, 'seasonal': 'winter', 'category': 'Beverage', 'description': 'Hot Apple Cider'},
            
            # ===== Apparel (Winter) =====
            'WINTER_COAT': {'base': 30, 'price': 80, 'cost': 32, 'seasonal': 'winter', 'category': 'Apparel', 'description': 'Winter Coat'},
            'THERMAL_UNDERWEAR': {'base': 60, 'price': 25, 'cost': 10, 'seasonal': 'winter', 'category': 'Apparel', 'description': 'Thermal Underwear'},
            'WOOL_SWEATER': {'base': 45, 'price': 45, 'cost': 18, 'seasonal': 'winter', 'category': 'Apparel', 'description': 'Wool Sweater'},
            'WINTER_BOOTS': {'base': 35, 'price': 90, 'cost': 36, 'seasonal': 'winter', 'category': 'Apparel', 'description': 'Winter Boots'},
            'GLOVES': {'base': 80, 'price': 15, 'cost': 6, 'seasonal': 'winter', 'category': 'Apparel', 'description': 'Winter Gloves'},
            'SCARF': {'base': 70, 'price': 20, 'cost': 8, 'seasonal': 'winter', 'category': 'Apparel', 'description': 'Wool Scarf'},
            'BEANIE': {'base': 90, 'price': 18, 'cost': 7, 'seasonal': 'winter', 'category': 'Apparel', 'description': 'Winter Beanie'},
            
            # ===== Apparel (Summer) =====
            'SUNGLASSES': {'base': 55, 'price': 50, 'cost': 20, 'seasonal': 'summer', 'category': 'Apparel', 'description': 'UV Protection Sunglasses'},
            'SHORTS': {'base': 100, 'price': 35, 'cost': 14, 'seasonal': 'summer', 'category': 'Apparel', 'description': 'Summer Shorts'},
            'T_SHIRT': {'base': 150, 'price': 20, 'cost': 8, 'seasonal': 'summer', 'category': 'Apparel', 'description': 'Cotton T-Shirt'},
            'SANDALS': {'base': 85, 'price': 40, 'cost': 16, 'seasonal': 'summer', 'category': 'Apparel', 'description': 'Comfortable Sandals'},
            'HAT': {'base': 75, 'price': 22, 'cost': 9, 'seasonal': 'summer', 'category': 'Apparel', 'description': 'Summer Hat'},
            
            # ===== Personal Care (Summer) =====
            'SUNSCREEN': {'base': 80, 'price': 12, 'cost': 4, 'seasonal': 'summer', 'category': 'Personal Care', 'description': 'Sunscreen SPF 50'},
            'AFTER_SUN_LOTION': {'base': 70, 'price': 10, 'cost': 3.5, 'seasonal': 'summer', 'category': 'Personal Care', 'description': 'After Sun Lotion'},
            'INSECT_REPELLENT': {'base': 90, 'price': 8, 'cost': 2.5, 'seasonal': 'summer', 'category': 'Personal Care', 'description': 'Mosquito Repellent'},
            'LIP_BALM_SPF': {'base': 120, 'price': 4, 'cost': 1.2, 'seasonal': 'summer', 'category': 'Personal Care', 'description': 'SPF Lip Balm'},
            
            # ===== Personal Care (Winter) =====
            'LIP_BALM': {'base': 110, 'price': 3.5, 'cost': 1, 'seasonal': 'winter', 'category': 'Personal Care', 'description': 'Moisturizing Lip Balm'},
            'HAND_LOTION': {'base': 95, 'price': 8, 'cost': 2.5, 'seasonal': 'winter', 'category': 'Personal Care', 'description': 'Hand Lotion'},
            'BODY_LOTION': {'base': 100, 'price': 12, 'cost': 4, 'seasonal': 'winter', 'category': 'Personal Care', 'description': 'Moisturizing Body Lotion'},
            
            # ===== Snacks & Candy =====
            'CHOCOLATE': {'base': 180, 'price': 3, 'cost': 1, 'seasonal': 'winter', 'category': 'Snacks', 'description': 'Premium Chocolate'},
            'CANDY': {'base': 200, 'price': 2, 'cost': 0.6, 'seasonal': 'spring', 'category': 'Snacks', 'description': 'Mixed Candy'},
            'CHIPS': {'base': 160, 'price': 2.5, 'cost': 0.8, 'seasonal': 'neutral', 'category': 'Snacks', 'description': 'Potato Chips'},
            'POPCORN': {'base': 140, 'price': 4, 'cost': 1.2, 'seasonal': 'neutral', 'category': 'Snacks', 'description': 'Gourmet Popcorn'},
            'NUTS': {'base': 120, 'price': 8, 'cost': 3, 'seasonal': 'neutral', 'category': 'Snacks', 'description': 'Mixed Nuts'},
            
            # ===== Sports & Outdoor =====
            'UMBRELLA': {'base': 50, 'price': 25, 'cost': 10, 'seasonal': 'spring', 'category': 'Outdoor', 'description': 'Rain Umbrella'},
            'RAINCOAT': {'base': 40, 'price': 60, 'cost': 24, 'seasonal': 'spring', 'category': 'Outdoor', 'description': 'Waterproof Raincoat'},
            'BICYCLE': {'base': 15, 'price': 300, 'cost': 120, 'seasonal': 'summer', 'category': 'Sports', 'description': 'Mountain Bike'},
            'SKATEBOARD': {'base': 25, 'price': 80, 'cost': 32, 'seasonal': 'summer', 'category': 'Sports', 'description': 'Pro Skateboard'},
            'ROLLERBLADES': {'base': 20, 'price': 120, 'cost': 48, 'seasonal': 'summer', 'category': 'Sports', 'description': 'Inline Rollerblades'},
            
            # ===== Miscellaneous =====
            'WATER_BOTTLE': {'base': 130, 'price': 15, 'cost': 5, 'seasonal': 'neutral', 'category': 'Accessories', 'description': 'Reusable Water Bottle'},
            'BACKPACK': {'base': 85, 'price': 45, 'cost': 18, 'seasonal': 'neutral', 'category': 'Accessories', 'description': 'Travel Backpack'},
            'PHONE_CASE': {'base': 200, 'price': 20, 'cost': 6, 'seasonal': 'neutral', 'category': 'Accessories', 'description': 'Phone Case'},
            'HEADPHONES': {'base': 60, 'price': 80, 'cost': 30, 'seasonal': 'neutral', 'category': 'Electronics', 'description': 'Wireless Headphones'},
            'POWER_BANK': {'base': 75, 'price': 30, 'cost': 10, 'seasonal': 'neutral', 'category': 'Electronics', 'description': '20000mAh Power Bank'},
        }
        
        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)
            day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
            month = current_date.month
            day_of_month = current_date.day
            week_of_year = current_date.isocalendar()[1]
            
            for product_id, product_info in products.items():
                base_qty = product_info['base']
                
                # ===== Factor 1: Weekend Boost =====
                weekend_factor = 1.5 if day_of_week >= 5 else 1.0
                
                # ===== Factor 2: Seasonal Boost =====
                seasonal_factor = 1.0
                if product_info['seasonal'] == 'summer' and month in [6, 7, 8]:
                    seasonal_factor = 2.0  # Double sales in summer
                elif product_info['seasonal'] == 'winter' and month in [11, 12, 1, 2]:
                    seasonal_factor = 2.5  # Triple sales in winter
                elif product_info['seasonal'] == 'spring' and month in [3, 4, 5]:
                    seasonal_factor = 1.8  # Good sales in spring
                elif product_info['seasonal'] == 'neutral':
                    seasonal_factor = 1.0  # No seasonal effect
                
                # ===== Factor 3: Payday Boost (15th, 30th) =====
                payday_factor = 1.3 if day_of_month in [15, 30] else 1.0
                
                # ===== Factor 4: Viral/Trend Spike (5% chance) =====
                viral_factor = random.choice([1.0] * 95 + [3.0] * 5)
                
                # ===== Factor 5: Holiday Boost =====
                holiday_factor = 1.0
                if month == 2 and day_of_month == 14:  # Valentine's Day
                    holiday_factor = 1.5 if 'GIFT' not in product_id else 2.0
                elif month == 12 and day_of_month in range(20, 26):  # Christmas week
                    holiday_factor = 3.0
                elif month == 1 and day_of_month == 1:  # New Year
                    holiday_factor = 1.3
                elif month == 7 and day_of_month == 4:  # Independence Day (US)
                    holiday_factor = 1.2
                
                # ===== Factor 6: Weather Pattern =====
                # Weather affects products by their seasonal category
                weather_factor = 1.0
                if product_info['seasonal'] == 'summer':
                    # Hot summer = higher demand for summer products
                    if month in [6, 7, 8]:
                        weather_factor = 1.3
                    else:
                        weather_factor = 0.7  # Lower demand in other seasons
                elif product_info['seasonal'] == 'winter':
                    # Cold winter = higher demand for winter products
                    if month in [11, 12, 1, 2]:
                        weather_factor = 1.4
                    else:
                        weather_factor = 0.6  # Lower demand in other seasons
                elif product_info['seasonal'] == 'spring':
                    # Spring season
                    if month in [3, 4, 5]:
                        weather_factor = 1.2
                    else:
                        weather_factor = 0.8
                # Neutral products are not affected by weather (factor = 1.0)
                
                # ===== Calculate Final Quantity =====
                qty = int(base_qty * weekend_factor * seasonal_factor * 
                         payday_factor * viral_factor * holiday_factor * weather_factor)
                
                # Add randomness (±15%)
                qty = int(qty * random.uniform(0.85, 1.15))
                qty = max(1, qty)  # Never 0
                
                sales.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'product_id': hash(product_id) % 1000,
                    'sku': product_id,
                    'product_name': product_id.replace('_', ' ').title(),
                    'category': product_info['category'],
                    'quantity_sold': qty,
                    'revenue': qty * product_info['price'],
                    'unit_cost': product_info['cost'],
                    'unit_price': product_info['price'],
                    'margin_pct': round((product_info['price'] - product_info['cost']) / product_info['price'] * 100, 1),
                    'current_stock': random.randint(100, 500),
                    'lead_time_days': random.randint(3, 14),
                    'factors': {
                        'weekend': round(weekend_factor, 2),
                        'seasonal': round(seasonal_factor, 2),
                        'payday': round(payday_factor, 2),
                        'viral': round(viral_factor, 2),
                        'holiday': round(holiday_factor, 2),
                        'weather': round(weather_factor, 2)
                    }
                })
        
        return sales
    
    @staticmethod
    def generate_90days_sales() -> List[Dict]:
        """Backwards compatible helper for existing endpoints (90 days)"""
        return SmartDataGenerator.generate_sales(90)
    
    @staticmethod
    def generate_365days_sales() -> List[Dict]:
        """Generate 365 days of realistic sales data for full-year demos"""
        return SmartDataGenerator.generate_sales(365)
    
    @staticmethod
    def get_sample_data_summary(sales_data: List[Dict]) -> Dict:
        """Get summary statistics of generated data"""
        df = pd.DataFrame(sales_data)
        
        summary = {
            'total_records': int(len(df)),
            'date_range': {
                'start': str(df['date'].min()),
                'end': str(df['date'].max())
            },
            'products_count': int(df['sku'].nunique()),
            'products': df['sku'].unique().tolist(),
            'total_revenue': float(round(df['revenue'].sum(), 2)),
            'avg_daily_revenue': float(round(df['revenue'].mean(), 2)),
            'total_units_sold': int(df['quantity_sold'].sum()),
            'by_category': {k: float(v) for k, v in df.groupby('category')['revenue'].sum().to_dict().items()},
            'by_product': {k: {sk: int(sv) if isinstance(sv, (int, np.integer)) else float(sv) for sk, sv in v.items()} for k, v in df.groupby('sku')[['quantity_sold', 'revenue']].sum().to_dict().items()}
        }
        
        return summary


class HyperLocalSignals:
    """Enrich forecasts with external signals"""
    
    @staticmethod
    def get_weather_signal(date_str: str) -> Dict:
        """Get weather impact on demand"""
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            month = date.month
            
            # Seasonal weather patterns
            if month in [6, 7, 8]:  # Summer
                return {
                    'season': 'Summer',
                    'temp_range': '25-32°C',
                    'condition': 'Hot & Sunny',
                    'impact': 'High demand for cold drinks, sunscreen',
                    'boost_factor': 1.5,
                    'affected_products': ['ICE_CREAM', 'ENERGY_DRINK', 'SUNSCREEN']
                }
            elif month in [12, 1, 2]:  # Winter
                return {
                    'season': 'Winter',
                    'temp_range': '-5 to 10°C',
                    'condition': 'Cold & Dry',
                    'impact': 'High demand for winter coats, hot drinks',
                    'boost_factor': 1.8,
                    'affected_products': ['WINTER_COAT', 'HOT_COCOA']
                }
            else:  # Spring/Fall
                return {
                    'season': 'Mild',
                    'temp_range': '10-20°C',
                    'condition': 'Pleasant',
                    'impact': 'Baseline demand',
                    'boost_factor': 1.0,
                    'affected_products': []
                }
        except:
            return {
                'season': 'Unknown',
                'temp_range': 'N/A',
                'condition': 'Unknown',
                'impact': 'Unable to determine',
                'boost_factor': 1.0,
                'affected_products': []
            }
    
    @staticmethod
    def get_holiday_signal(date_str: str) -> Dict:
        """Detect holidays and special events"""
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            month = date.month
            day = date.day
            
            holidays = {
                (1, 1): {
                    'name': "New Year's Day",
                    'boost': 1.3,
                    'description': 'New Year resolutions - fitness & health products',
                    'affected_products': ['ENERGY_DRINK']
                },
                (2, 14): {
                    'name': "Valentine's Day",
                    'boost': 1.5,
                    'description': 'Romance & gift giving',
                    'affected_products': ['ICE_CREAM']
                },
                (7, 4): {
                    'name': 'Independence Day',
                    'boost': 1.2,
                    'description': 'Summer celebration & outdoor activities',
                    'affected_products': ['ICE_CREAM', 'SUNSCREEN']
                },
                (11, 25): {
                    'name': 'Black Friday',
                    'boost': 2.5,
                    'description': 'Major shopping event - all categories',
                    'affected_products': ['WINTER_COAT', 'ENERGY_DRINK']
                },
                (12, 25): {
                    'name': 'Christmas',
                    'boost': 3.0,
                    'description': 'Holiday season - maximum demand',
                    'affected_products': ['WINTER_COAT', 'HOT_COCOA']
                }
            }
            
            holiday_key = (month, day)
            if holiday_key in holidays:
                return {
                    'is_holiday': True,
                    'holiday': holidays[holiday_key]['name'],
                    'boost': holidays[holiday_key]['boost'],
                    'description': holidays[holiday_key]['description'],
                    'affected_products': holidays[holiday_key]['affected_products']
                }
            else:
                return {
                    'is_holiday': False,
                    'holiday': 'Regular Day',
                    'boost': 1.0,
                    'description': 'Normal business day',
                    'affected_products': []
                }
        except:
            return {
                'is_holiday': False,
                'holiday': 'Unknown',
                'boost': 1.0,
                'description': 'Unable to determine',
                'affected_products': []
            }
    
    @staticmethod
    def get_payday_signal(date_str: str) -> Dict:
        """Detect payday patterns"""
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            day = date.day
            
            if day in [15, 30]:
                return {
                    'is_payday': True,
                    'payday_date': day,
                    'boost': 1.3,
                    'description': 'Salary payment - increased purchasing power',
                    'affected_products': ['PREMIUM_ITEMS', 'ALL_CATEGORIES']
                }
            else:
                return {
                    'is_payday': False,
                    'payday_date': None,
                    'boost': 1.0,
                    'description': 'Regular business day',
                    'affected_products': []
                }
        except:
            return {
                'is_payday': False,
                'payday_date': None,
                'boost': 1.0,
                'description': 'Unable to determine',
                'affected_products': []
            }
    
    @staticmethod
    def get_weekend_signal(date_str: str) -> Dict:
        """Detect weekend patterns"""
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            day_of_week = date.weekday()
            day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day_of_week]
            
            if day_of_week >= 5:  # Saturday or Sunday
                return {
                    'is_weekend': True,
                    'day': day_name,
                    'boost': 1.5,
                    'description': 'Weekend - higher retail traffic',
                    'affected_products': ['ALL_RETAIL']
                }
            else:
                return {
                    'is_weekend': False,
                    'day': day_name,
                    'boost': 1.0,
                    'description': 'Weekday - baseline traffic',
                    'affected_products': []
                }
        except:
            return {
                'is_weekend': False,
                'day': 'Unknown',
                'boost': 1.0,
                'description': 'Unable to determine',
                'affected_products': []
            }
    
    @staticmethod
    def get_trend_signal() -> Dict:
        """Detect viral trends (random for demo)"""
        trend_scenarios = [
            {
                'is_trending': True,
                'trend': 'Viral TikTok Challenge',
                'product': 'ENERGY_DRINK',
                'boost': 3.0,
                'description': '#EnergySummerChallenge going viral - 2M+ views',
                'duration_days': 7,
                'confidence': 0.95
            },
            {
                'is_trending': True,
                'trend': 'Celebrity Endorsement',
                'product': 'SUNSCREEN',
                'boost': 2.2,
                'description': 'Celebrity recommends sunscreen brand on Instagram',
                'duration_days': 5,
                'confidence': 0.87
            },
            {
                'is_trending': False,
                'trend': 'No major trends',
                'product': 'None',
                'boost': 1.0,
                'description': 'Market conditions normal',
                'duration_days': 0,
                'confidence': 0.5
            }
        ]
        
        return random.choice(trend_scenarios)
    
    @staticmethod
    def combine_all_signals(date_str: str, product: str = None) -> Dict:
        """Combine all signals into one forecast multiplier"""
        
        weather = HyperLocalSignals.get_weather_signal(date_str)
        holiday = HyperLocalSignals.get_holiday_signal(date_str)
        payday = HyperLocalSignals.get_payday_signal(date_str)
        weekend = HyperLocalSignals.get_weekend_signal(date_str)
        trend = HyperLocalSignals.get_trend_signal()
        
        # Start with base multiplier
        multiplier = 1.0
        
        # Apply relevant signals
        multiplier *= weather['boost_factor']
        multiplier *= holiday['boost']
        multiplier *= payday['boost']
        multiplier *= weekend['boost']
        
        # Apply trend if product matches
        if trend['is_trending'] and product and product == trend['product']:
            multiplier *= trend['boost']
        
        signals_breakdown = {
            'date': date_str,
            'product': product,
            'weather': weather,
            'holiday': holiday,
            'payday': payday,
            'weekend': weekend,
            'trend': trend,
            'combined_multiplier': round(multiplier, 2),
            'interpretation': f"Multiply base forecast by {multiplier:.2f}x on {date_str}"
        }
        
        return signals_breakdown
