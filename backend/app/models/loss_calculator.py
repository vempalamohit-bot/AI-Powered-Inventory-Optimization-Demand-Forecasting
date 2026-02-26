"""
AI-Powered Loss Calculator - Calculates revenue loss from stockouts and poor inventory decisions
Shows financial impact of AI predictions
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from typing import Dict, List
from ..database.models import SalesHistory, Product

class LossCalculator:
    """Calculate various types of losses and opportunity costs"""
    
    @staticmethod
    def calculate_stockout_loss(db: Session, product_id: int = None) -> Dict:
        """
        Calculate daily revenue loss from out-of-stock products
        AI predicts what we WOULD have sold if product was in stock
        """
        
        # Find out of stock products
        out_of_stock_query = db.query(Product).filter(Product.current_stock == 0)
        
        if product_id:
            out_of_stock_query = out_of_stock_query.filter(Product.id == product_id)
        
        out_of_stock_products = out_of_stock_query.all()
        
        total_daily_loss = 0
        product_losses = []
        
        for product in out_of_stock_products:
            # Get average daily demand from last 30 days
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            avg_daily_demand = db.query(
                func.avg(SalesHistory.quantity_sold)
            ).filter(
                and_(
                    SalesHistory.product_id == product.id,
                    SalesHistory.date >= thirty_days_ago
                )
            ).scalar() or 0
            
            # AI prediction: compute trend-adjusted daily demand from 30-day history
            # Uses linear trend extrapolation instead of a fixed multiplier
            from sqlalchemy import func as sqla_func
            recent_sales = db.query(
                SalesHistory.date,
                sqla_func.sum(SalesHistory.quantity_sold).label('qty')
            ).filter(
                SalesHistory.product_id == product.id,
                SalesHistory.date >= thirty_days_ago
            ).group_by(SalesHistory.date).order_by(SalesHistory.date).all()
            
            if len(recent_sales) >= 7:
                # Fit linear trend to recent daily sales
                import numpy as np
                qtys = np.array([float(r.qty) for r in recent_sales])
                X = np.arange(len(qtys))
                slope = np.polyfit(X, qtys, 1)[0]
                # Project one step ahead: last value + trend
                predicted_daily_demand = max(1, int(qtys[-1] + slope))
            else:
                predicted_daily_demand = max(1, int(avg_daily_demand))
            
            # Calculate loss
            unit_profit = product.unit_price - product.unit_cost
            daily_loss = predicted_daily_demand * unit_profit
            
            # ML-based reorder quantity: demand during lead time + z-score safety stock
            # Uses demand std dev and 95% service level (z=1.65) 
            import math as _math
            demand_std = 0
            if len(recent_sales) >= 2:
                import numpy as np
                demand_std = float(np.std([r.qty for r in recent_sales]))
            lead_time = product.lead_time_days or 7
            z_score = 1.65  # 95% service level
            safety_stock = z_score * demand_std * _math.sqrt(lead_time)
            recommended_quantity = max(1, int(
                (predicted_daily_demand * lead_time) + safety_stock
            ))
            
            total_daily_loss += daily_loss
            
            product_losses.append({
                'product_id': product.id,
                'sku': product.sku,
                'product_name': product.name,
                'category': product.category,
                'current_stock': 0,
                'stock_category': 'OUT_OF_STOCK',  # 4 category system
                'predicted_daily_demand': predicted_daily_demand,
                'unit_profit': round(unit_profit, 2),
                'daily_revenue_loss': round(predicted_daily_demand * product.unit_price, 2),
                'daily_profit_loss': round(daily_loss, 2),
                'weekly_loss': round(daily_loss * 7, 2),
                'monthly_loss': round(daily_loss * 30, 2),
                'ai_recommendation': 'URGENT: Order immediately to prevent further losses',
                'recommended_order_quantity': recommended_quantity,
                'estimated_cost': round(recommended_quantity * product.unit_cost, 2),
                'lead_time_days': product.lead_time_days,
                'urgency_level': 'OUT_OF_STOCK',
                'send_email_alert': True
            })
        
        return {
            'total_out_of_stock_products': len(out_of_stock_products),
            'total_daily_loss': round(total_daily_loss, 2),
            'total_weekly_loss': round(total_daily_loss * 7, 2),
            'total_monthly_loss': round(total_daily_loss * 30, 2),
            'total_annual_loss': round(total_daily_loss * 365, 2),
            'product_details': product_losses,
            'alert_type': 'STOCKOUT_REVENUE_LOSS',
            'generated_by_ai': True
        }
    
    @staticmethod
    def _calculate_dynamic_threshold(product: Product, avg_demand: float) -> float:
        """
        AI: Calculate dynamic low stock threshold based on product's demand and lead time
        
        Dynamic Threshold = (Daily Demand × Lead Time) × Safety Factor
        This ensures threshold adapts to each product's velocity
        """
        lead_time = product.lead_time_days or 7
        
        # ML-driven threshold: lead-time demand + z-score based safety stock
        # z=1.28 for 90% service level (suitable for low-stock alert threshold)
        import math as _math
        z_score = 1.28
        demand_cv = (avg_demand * 0.3) if avg_demand > 0 else 1  # Estimate σ as 30% of mean if unknown
        safety_buffer = z_score * demand_cv * _math.sqrt(lead_time)
        dynamic_threshold = (avg_demand * lead_time) + safety_buffer
        
        # Scale minimum to product value: expensive items get lower min threshold
        unit_price = product.unit_price if product.unit_price else 10
        min_threshold = max(1, int(5000 / unit_price))  # e.g., $10 item → min 500, $500 → min 10
        min_threshold = min(min_threshold, 50)  # Cap at 50
        
        return max(min_threshold, dynamic_threshold)
    
    @staticmethod
    def calculate_low_stock_risk(db: Session) -> Dict:
        """
        AI-Enhanced: Calculate potential loss for low stock items approaching stockout
        Uses ML-based dynamic thresholds per product instead of static value
        """
        
        # Get all products with stock > 0
        all_products = db.query(Product).filter(Product.current_stock > 0).all()
        
        # Calculate demand for all products in batch for efficiency
        seven_days_ago = datetime.now() - timedelta(days=7)
        demand_data = db.query(
            SalesHistory.product_id,
            func.avg(SalesHistory.quantity_sold).label('avg_demand')
        ).filter(
            SalesHistory.date >= seven_days_ago
        ).group_by(SalesHistory.product_id).all()
        
        demand_map = {row.product_id: float(row.avg_demand or 1) for row in demand_data}
        
        # Find low stock products using AI-based dynamic threshold
        low_stock_products = []
        for product in all_products:
            avg_demand = demand_map.get(product.id, 1)
            dynamic_threshold = LossCalculator._calculate_dynamic_threshold(product, avg_demand)
            
            if product.current_stock < dynamic_threshold:
                low_stock_products.append((product, avg_demand, dynamic_threshold))
        
        at_risk_products = []
        
        for product, recent_sales, threshold in low_stock_products:
            # Use pre-calculated demand from batch query
            
            # AI prediction: days until stockout
            if recent_sales > 0:
                days_until_stockout = int(product.current_stock / recent_sales)
            else:
                days_until_stockout = 999
            
            # Calculate buffer days and determine 4 CATEGORY classification
            lead_time = product.lead_time_days or 7
            buffer_days = days_until_stockout - lead_time
            
            # 4 CATEGORIES: OUT_OF_STOCK, LOW_WARNING, MEDIUM, HIGH
            if buffer_days <= 10:
                # LOW_WARNING: threshold reached, needs reorder
                urgency = 'LOW_WARNING'
                if buffer_days < 0:
                    alert_message = f'⚠️ CRITICAL: Will stockout in {days_until_stockout} days - BEFORE reorder arrives ({lead_time} day lead time)'
                elif buffer_days <= 5:
                    alert_message = f'⚠️ URGENT: Order now - only {buffer_days} days buffer remaining'
                else:
                    alert_message = f'⚠️ WARNING: Threshold reached - {buffer_days} days to reorder'
                send_email = buffer_days <= 5
            elif buffer_days <= 30:
                urgency = 'MEDIUM'
                alert_message = f'Monitor - {days_until_stockout} days of stock ({buffer_days} days buffer)'
                send_email = False
            else:
                urgency = 'HIGH'  # HIGH = well stocked
                alert_message = f'Well stocked - {days_until_stockout} days of stock'
                send_email = False
            
            # Calculate potential loss if we don't reorder
            unit_profit = product.unit_price - product.unit_cost
            potential_daily_loss = recent_sales * unit_profit
            
            at_risk_products.append({
                'product_id': product.id,
                'sku': product.sku,
                'product_name': product.name,
                'category': product.category,
                'current_stock': product.current_stock,
                'dynamic_threshold': int(threshold),  # AI-calculated threshold
                'daily_demand': round(recent_sales, 1),
                'days_until_stockout': days_until_stockout,
                'buffer_days': buffer_days,
                'lead_time_days': lead_time,
                'stock_category': urgency,  # 4 category system
                'urgency_level': urgency,
                'potential_daily_loss': round(potential_daily_loss, 2),
                'ai_alert': alert_message,
                'recommended_action': 'Reorder now' if urgency == 'LOW_WARNING' else 'Monitor',
                'send_email_alert': send_email,
                'threshold_reached': buffer_days <= 10
            })
        
        # Sort by buffer days (most urgent first)
        at_risk_products.sort(key=lambda x: x['buffer_days'])
        
        return {
            'total_at_risk_products': len(at_risk_products),
            'low_warning_count': sum(1 for p in at_risk_products if p['stock_category'] == 'LOW_WARNING'),
            'medium_count': sum(1 for p in at_risk_products if p['stock_category'] == 'MEDIUM'),
            'high_count': sum(1 for p in at_risk_products if p['stock_category'] == 'HIGH'),
            'product_details': at_risk_products[:50],  # Top 50 at-risk
            'generated_by_ai': True
        }
    
    @staticmethod
    def calculate_product_level_loss(db: Session, time_period: str = 'daily') -> List[Dict]:
        """
        Calculate profit/loss at product level for Daily, WoW, MoM, YoY
        Shows trends in product performance over time
        """
        
        # Determine date range based on period
        now = datetime.now()
        
        if time_period == 'daily':
            start_date = now - timedelta(days=1)
            previous_start = now - timedelta(days=2)
            previous_end = now - timedelta(days=1)
            label = 'Daily'
        elif time_period == 'wow':
            start_date = now - timedelta(days=7)
            previous_start = now - timedelta(days=14)
            previous_end = now - timedelta(days=7)
            label = 'WoW (Week over Week)'
        elif time_period == 'mom':
            start_date = now - timedelta(days=30)
            previous_start = now - timedelta(days=60)
            previous_end = now - timedelta(days=30)
            label = 'MoM (Month over Month)'
        elif time_period == 'yoy':
            start_date = now - timedelta(days=365)
            previous_start = now - timedelta(days=730)
            previous_end = now - timedelta(days=365)
            label = 'YoY (Year over Year)'
        else:
            start_date = now - timedelta(days=1)
            previous_start = now - timedelta(days=2)
            previous_end = now - timedelta(days=1)
            label = 'Daily'
        
        # Get current period data
        current_period = db.query(
            SalesHistory.product_id,
            func.sum(SalesHistory.quantity_sold).label('quantity'),
            func.sum(SalesHistory.revenue).label('revenue'),
            func.sum(SalesHistory.profit).label('profit')
        ).filter(
            SalesHistory.date >= start_date
        ).group_by(SalesHistory.product_id).all()
        
        # Get previous period for comparison
        previous_period = db.query(
            SalesHistory.product_id,
            func.sum(SalesHistory.revenue).label('revenue'),
            func.sum(SalesHistory.profit).label('profit')
        ).filter(
            and_(
                SalesHistory.date >= previous_start,
                SalesHistory.date < previous_end
            )
        ).group_by(SalesHistory.product_id).all()
        
        # Create lookup for previous period
        prev_dict = {p.product_id: {'revenue': float(p.revenue or 0), 'profit': float(p.profit or 0)} for p in previous_period}
        
        results = []
        for current in current_period:
            product = db.query(Product).filter(Product.id == current.product_id).first()
            if not product:
                continue
            
            current_revenue = float(current.revenue or 0)
            current_profit = float(current.profit or 0)
            
            prev = prev_dict.get(current.product_id, {'revenue': 0, 'profit': 0})
            prev_revenue = prev['revenue']
            prev_profit = prev['profit']
            
            # Calculate growth
            revenue_growth = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
            profit_growth = ((current_profit - prev_profit) / prev_profit * 100) if prev_profit > 0 else 0
            
            results.append({
                'product_id': product.id,
                'sku': product.sku,
                'product_name': product.name,
                'category': product.category,
                'period': label,
                'quantity_sold': int(current.quantity or 0),
                'revenue': round(current_revenue, 2),
                'profit': round(current_profit, 2),
                'is_profitable': current_profit > 0,
                'previous_revenue': round(prev_revenue, 2),
                'previous_profit': round(prev_profit, 2),
                'revenue_growth_percentage': round(revenue_growth, 2),
                'profit_growth_percentage': round(profit_growth, 2),
                'trend': 'UP' if profit_growth > 5 else 'DOWN' if profit_growth < -5 else 'STABLE'
            })
        
        # Sort by profit (show biggest losses first)
        results.sort(key=lambda x: x['profit'])
        
        return results
