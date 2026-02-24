"""
Reorder Point and Stockout Risk Calculator
Calculates when to reorder inventory and assesses stockout risk
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..database.models import Product, SalesHistory, Forecast
import statistics
import math


class ReorderCalculator:
    """Calculate reorder points and stockout risk for products"""
    
    SAFETY_STOCK_MULTIPLIER = 1.5  # 50% buffer for demand variability
    FORECAST_DAYS = 30
    STOCKOUT_RISK_THRESHOLD_DAYS = 7  # Days until stockout triggers HIGH risk
    
    @staticmethod
    def calculate_average_daily_demand(db: Session, product_id: int, days: int = 30) -> int:
        """Calculate average daily demand from sales history (returns integer, rounded UP for safety)"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        sales = db.query(SalesHistory).filter(
            SalesHistory.product_id == product_id,
            SalesHistory.date >= cutoff_date
        ).all()
        
        if not sales:
            return 1  # Minimum 1 unit/day
        
        total_sold = sum(s.quantity_sold for s in sales)
        avg_daily = total_sold / days
        
        # Round UP for safety (3.1 → 4, 3.9 → 4)
        return max(1, math.ceil(avg_daily))
    
    @staticmethod
    def calculate_demand_variance(db: Session, product_id: int, days: int = 30) -> float:
        """Calculate demand variance (standard deviation) for safety stock calculation"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        sales = db.query(SalesHistory).filter(
            SalesHistory.product_id == product_id,
            SalesHistory.date >= cutoff_date
        ).all()
        
        if len(sales) < 2:
            return 0.0
        
        daily_amounts = {}
        for sale in sales:
            date_key = sale.date.date()
            daily_amounts[date_key] = daily_amounts.get(date_key, 0) + sale.quantity_sold
        
        if len(daily_amounts) < 2:
            return 0.0
        
        try:
            variance = statistics.stdev(daily_amounts.values())
            return variance
        except:
            return 0.0
    
    @staticmethod
    def calculate_reorder_point(db: Session, product_id: int) -> dict:
        """
        Calculate reorder point for a product
        Reorder Point = (Average Daily Demand × Lead Time) + Safety Stock
        Returns: Integers (no decimals)
        """
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {
                "reorder_point": 0,
                "safety_stock": 0,
                "average_daily_demand": 0,
                "status": "PRODUCT_NOT_FOUND"
            }
        
        # Calculate average daily demand (already integer)
        avg_daily_demand = ReorderCalculator.calculate_average_daily_demand(db, product_id)
        
        # Calculate demand variance for safety stock
        demand_variance = ReorderCalculator.calculate_demand_variance(db, product_id)
        
        # Lead time in days
        lead_time = product.lead_time_days or 7
        
        # Reorder Point = (Avg Daily Demand × Lead Time) + Safety Stock
        # Safety Stock = Z-score × std dev × sqrt(lead time)
        # For simplicity, using variance multiplier approach
        safety_stock = (demand_variance * ReorderCalculator.SAFETY_STOCK_MULTIPLIER) + (avg_daily_demand * 0.5)
        
        reorder_point = (avg_daily_demand * lead_time) + safety_stock
        
        return {
            "reorder_point": int(math.ceil(reorder_point)),  # Round up to nearest integer
            "safety_stock": int(math.ceil(safety_stock)),
            "average_daily_demand": avg_daily_demand,  # Already integer
            "lead_time_days": lead_time,
            "status": "NORMAL" if product.current_stock > reorder_point else "REORDER_NEEDED"
        }
    
    @staticmethod
    def calculate_stockout_risk(db: Session, product_id: int) -> dict:
        """
        Calculate stockout risk based on:
        - Current stock level
        - Average daily demand
        - Forecast demand for next 30 days
        Returns: Integers (no decimals)
        """
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {
                "risk_level": "UNKNOWN",
                "days_until_stockout": None,
                "risk_percentage": 0
            }
        
        # Get average daily demand (already integer)
        avg_daily_demand = ReorderCalculator.calculate_average_daily_demand(db, product_id)
        
        if avg_daily_demand == 0:
            return {
                "risk_level": "UNKNOWN",
                "days_until_stockout": None,
                "risk_percentage": 0,
                "reason": "NO_SALES_DATA"
            }
        
        # Calculate days until stockout at current velocity
        days_until_stockout = product.current_stock / avg_daily_demand
        
        # Get latest forecast if available
        latest_forecast = db.query(Forecast).filter(
            Forecast.product_id == product_id
        ).order_by(Forecast.created_at.desc()).first()
        
        forecast_demand = None
        confidence = 0
        if latest_forecast:
            forecast_demand = latest_forecast.predicted_demand
            confidence = latest_forecast.confidence_level or 0.95
        
        # Determine risk level
        if days_until_stockout <= ReorderCalculator.STOCKOUT_RISK_THRESHOLD_DAYS:
            risk_level = "HIGH"
            risk_percentage = min(100, 100 - (days_until_stockout / ReorderCalculator.STOCKOUT_RISK_THRESHOLD_DAYS * 80))
        elif days_until_stockout <= ReorderCalculator.STOCKOUT_RISK_THRESHOLD_DAYS * 2:
            risk_level = "MEDIUM"
            risk_percentage = 50
        else:
            risk_level = "LOW"
            risk_percentage = 20
        
        # Adjust risk based on forecast if available
        if forecast_demand and forecast_demand > avg_daily_demand * 1.2:
            # Demand spike detected - increase risk
            risk_level = "HIGH" if risk_level != "HIGH" else "HIGH"
            risk_percentage = min(100, risk_percentage + 20)
        
        return {
            "risk_level": risk_level,
            "days_until_stockout": int(math.floor(days_until_stockout)),  # Round down (conservative)
            "risk_percentage": int(round(risk_percentage)),  # Integer percentage
            "average_daily_demand": avg_daily_demand,  # Integer
            "current_stock": product.current_stock,
            "forecast_demand_30d": int(round(forecast_demand)) if forecast_demand else None,
            "forecast_confidence": int(round(confidence * 100)) if confidence else None
        }
    
    @staticmethod
    def get_product_inventory_metrics(db: Session, product_id: int) -> dict:
        """Get all inventory metrics for a product (reorder point + stockout risk)"""
        reorder_info = ReorderCalculator.calculate_reorder_point(db, product_id)
        stockout_info = ReorderCalculator.calculate_stockout_risk(db, product_id)
        
        return {
            "reorder_point": reorder_info,
            "stockout_risk": stockout_info
        }
