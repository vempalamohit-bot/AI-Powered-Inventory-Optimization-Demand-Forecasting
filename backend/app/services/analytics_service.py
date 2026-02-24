import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta

class AnalyticsService:
    """Service for calculating inventory analytics and business metrics"""
    
    def calculate_inventory_turnover(
        self,
        annual_sales: float,
        avg_inventory: float
    ) -> float:
        """Calculate inventory turnover ratio"""
        if avg_inventory == 0:
            return 0
        return annual_sales / avg_inventory
    
    def calculate_days_of_inventory(
        self,
        current_inventory: float,
        avg_daily_sales: float
    ) -> float:
        """Calculate days of inventory on hand"""
        if avg_daily_sales == 0:
            return 999
        return current_inventory / avg_daily_sales
    
    def identify_slow_movers(
        self,
        products_df: pd.DataFrame,
        threshold_days: int = 90
    ) -> List[Dict]:
        """Identify slow-moving inventory items"""
        slow_movers = []
        
        for _, product in products_df.iterrows():
            days_of_inventory = self.calculate_days_of_inventory(
                product['current_stock'],
                product['avg_daily_sales']
            )
            
            if days_of_inventory > threshold_days:
                slow_movers.append({
                    'product_id': product['product_id'],
                    'product_name': product['product_name'],
                    'days_of_inventory': days_of_inventory,
                    'current_stock': product['current_stock']
                })
        
        return slow_movers
    
    def calculate_fill_rate(
        self,
        orders_fulfilled: int,
        total_orders: int
    ) -> float:
        """Calculate order fill rate"""
        if total_orders == 0:
            return 1.0
        return orders_fulfilled / total_orders
    
    def calculate_carrying_cost(
        self,
        inventory_value: float,
        carrying_cost_rate: float = 0.25
    ) -> float:
        """Calculate annual inventory carrying cost"""
        return inventory_value * carrying_cost_rate
