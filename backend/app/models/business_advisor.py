"""
Business Recommendation Engine
Provides AI-powered insights and recommendations for inventory management
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict
import statistics

from ..database.models import Product, SalesHistory, Forecast
from .reorder_calculator import ReorderCalculator


class BusinessRecommendationEngine:
    """Generate actionable business recommendations for products"""
    
    @staticmethod
    def get_product_recommendations(db: Session, product_id: int) -> Dict:
        """Get comprehensive recommendations for a specific product"""
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"error": "Product not found"}
        
        # Get sales history
        sales = db.query(SalesHistory)\
            .filter(SalesHistory.product_id == product_id)\
            .order_by(SalesHistory.date.desc())\
            .limit(90)\
            .all()
        
        if not sales:
            return {
                "product": {
                    "sku": product.sku,
                    "name": product.name,
                    "category": product.category
                },
                "recommendations": [{
                    "type": "warning",
                    "priority": "medium",
                    "title": "Insufficient Data",
                    "message": "No sales history available. Start tracking sales to get recommendations.",
                    "action": "Upload sales data"
                }]
            }
        
        recommendations = []
        
        # Calculate reorder metrics
        reorder_info = ReorderCalculator.calculate_reorder_point(db, product_id)
        stockout_info = ReorderCalculator.calculate_stockout_risk(db, product_id)
        
        # 1. REORDER RECOMMENDATION
        if product.current_stock <= reorder_info['reorder_point']:
            urgency = "critical" if stockout_info['risk_level'] == "HIGH" else "high"
            recommendations.append({
                "type": "action",
                "priority": urgency,
                "title": "Reorder Now",
                "message": f"Current stock ({product.current_stock} units) is at or below reorder point ({reorder_info['reorder_point']} units).",
                "details": f"Days until stockout: {stockout_info['days_until_stockout']}",
                "action": f"Order {reorder_info['reorder_point'] * 2} units immediately",
                "estimated_cost": f"${(reorder_info['reorder_point'] * 2 * product.unit_cost):.2f}"
            })
        
        # 2. STOCKOUT RISK
        if stockout_info['risk_level'] == "HIGH" and product.current_stock > 0:
            recommendations.append({
                "type": "warning",
                "priority": "critical",
                "title": "High Stockout Risk",
                "message": f"Only {stockout_info['days_until_stockout']} days of stock remaining at current demand rate.",
                "details": f"Average daily demand: {reorder_info['average_daily_demand']} units",
                "action": f"Expedite order with supplier (Lead time: {product.lead_time_days} days)"
            })
        
        # 3. OVERSTOCK ANALYSIS
        if product.current_stock > reorder_info['reorder_point'] * 5:
            holding_cost = product.current_stock * product.unit_cost * 0.25  # 25% annual holding cost
            recommendations.append({
                "type": "info",
                "priority": "medium",
                "title": "Overstock Alert",
                "message": f"Current stock is {(product.current_stock / reorder_info['reorder_point']):.1f}x above reorder point.",
                "details": f"Annual holding cost: ${holding_cost:.2f}",
                "action": "Consider promotional pricing or markdown to reduce excess inventory"
            })
        
        # 4. PRICE OPTIMIZATION
        avg_daily_demand = reorder_info['average_daily_demand']
        if avg_daily_demand < 1 and product.current_stock > 100:
            potential_revenue = product.current_stock * product.unit_price * 0.7  # 30% markdown
            recommendations.append({
                "type": "action",
                "priority": "medium",
                "title": "Slow-Moving Inventory",
                "message": f"Product sells less than 1 unit per day (current: {avg_daily_demand:.2f}).",
                "details": f"Excess stock: {product.current_stock} units",
                "action": f"Apply 30% markdown to clear inventory. Projected revenue: ${potential_revenue:.2f}"
            })
        
        # 5. DEMAND TREND ANALYSIS
        if len(sales) >= 30:
            recent_demand = sum(s.quantity_sold for s in sales[:15]) / 15
            older_demand = sum(s.quantity_sold for s in sales[15:30]) / 15
            
            if recent_demand > older_demand * 1.2:
                recommendations.append({
                    "type": "success",
                    "priority": "high",
                    "title": "Increasing Demand Trend",
                    "message": f"Demand increased by {((recent_demand / older_demand - 1) * 100):.1f}% in last 2 weeks.",
                    "details": f"Recent avg: {recent_demand:.1f} units/day vs Previous: {older_demand:.1f} units/day",
                    "action": "Consider increasing safety stock and reorder quantities"
                })
            elif recent_demand < older_demand * 0.8:
                recommendations.append({
                    "type": "warning",
                    "priority": "medium",
                    "title": "Declining Demand Trend",
                    "message": f"Demand decreased by {((1 - recent_demand / older_demand) * 100):.1f}% in last 2 weeks.",
                    "details": f"Recent avg: {recent_demand:.1f} units/day vs Previous: {older_demand:.1f} units/day",
                    "action": "Review pricing strategy and marketing efforts"
                })
        
        # 6. PROFITABILITY ANALYSIS
        profit_margin = ((product.unit_price - product.unit_cost) / product.unit_price) * 100
        if profit_margin < 20:
            recommendations.append({
                "type": "warning",
                "priority": "medium",
                "title": "Low Profit Margin",
                "message": f"Current margin: {profit_margin:.1f}% (below 20% benchmark).",
                "details": f"Cost: ${product.unit_cost:.2f}, Price: ${product.unit_price:.2f}",
                "action": "Review supplier costs or consider price increase"
            })
        elif profit_margin > 60:
            recommendations.append({
                "type": "success",
                "priority": "low",
                "title": "High Profit Margin Product",
                "message": f"Excellent margin: {profit_margin:.1f}%.",
                "details": "This product is highly profitable",
                "action": "Maintain current pricing and ensure adequate stock levels"
            })
        
        # 7. SEASONAL PATTERN DETECTION
        if len(sales) >= 60:
            # Check for weekly patterns
            sales_by_weekday = {}
            for sale in sales:
                weekday = sale.date.weekday()
                if weekday not in sales_by_weekday:
                    sales_by_weekday[weekday] = []
                sales_by_weekday[weekday].append(sale.quantity_sold)
            
            weekday_avgs = {wd: sum(sales) / len(sales) for wd, sales in sales_by_weekday.items()}
            if weekday_avgs:
                max_day = max(weekday_avgs, key=weekday_avgs.get)
                min_day = min(weekday_avgs, key=weekday_avgs.get)
                
                if weekday_avgs[max_day] > weekday_avgs[min_day] * 1.5:
                    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    recommendations.append({
                        "type": "info",
                        "priority": "low",
                        "title": "Weekly Sales Pattern Detected",
                        "message": f"Peak sales on {day_names[max_day]}, lowest on {day_names[min_day]}.",
                        "details": f"Peak: {weekday_avgs[max_day]:.1f} units/day, Low: {weekday_avgs[min_day]:.1f} units/day",
                        "action": "Plan promotions and restocking around peak days"
                    })
        
        # 8. SUPPLIER LEAD TIME ALERT
        if product.lead_time_days and product.lead_time_days > 14:
            safety_days = product.lead_time_days + 7  # Lead time + 1 week buffer
            safety_stock_needed = reorder_info['average_daily_demand'] * safety_days
            
            if product.current_stock < safety_stock_needed:
                recommendations.append({
                    "type": "warning",
                    "priority": "high",
                    "title": "Long Lead Time Risk",
                    "message": f"Supplier lead time is {product.lead_time_days} days.",
                    "details": f"Need {safety_stock_needed:.0f} units buffer for long lead time (currently: {product.current_stock})",
                    "action": "Increase safety stock or find alternative supplier with shorter lead time"
                })
        
        return {
            "product": {
                "sku": product.sku,
                "name": product.name,
                "category": product.category,
                "current_stock": product.current_stock,
                "unit_price": product.unit_price,
                "unit_cost": product.unit_cost,
                "profit_margin": round(profit_margin, 2)
            },
            "metrics": {
                "reorder_point": reorder_info['reorder_point'],
                "safety_stock": reorder_info['safety_stock'],
                "average_daily_demand": reorder_info['average_daily_demand'],
                "days_until_stockout": stockout_info['days_until_stockout'],
                "risk_level": stockout_info['risk_level'],
                "lead_time_days": product.lead_time_days
            },
            "recommendations": sorted(recommendations, key=lambda x: {
                "critical": 0, "high": 1, "medium": 2, "low": 3
            }[x['priority']])
        }
    
    @staticmethod
    def get_top_recommendations(db: Session, limit: int = 20) -> List[Dict]:
        """Get top actionable recommendations across all products"""
        products = db.query(Product).all()
        all_recommendations = []
        
        for product in products[:100]:  # Limit to first 100 for performance
            result = BusinessRecommendationEngine.get_product_recommendations(db, product.id)
            if "recommendations" in result and result["recommendations"]:
                for rec in result["recommendations"]:
                    if rec.get("priority") in ["critical", "high"]:
                        all_recommendations.append({
                            "product_sku": result["product"]["sku"],
                            "product_name": result["product"]["name"],
                            "category": result["product"]["category"],
                            **rec
                        })
        
        # Sort by priority
        return sorted(all_recommendations, key=lambda x: {
            "critical": 0, "high": 1, "medium": 2, "low": 3
        }[x['priority']])[:limit]
