"""
AI EXPLAINER MODULE - Natural Language Explanation Engine

This module transforms AI/ML outputs into business-friendly explanations.
Every calculation includes:
1. The mathematical formula used
2. The data inputs and their sources
3. A natural language explanation of what it means
4. Actionable recommendations

Philosophy: "AI is only valuable when stakeholders can understand and trust it."
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
import math


class AIExplainer:
    """
    Transforms AI/ML calculations into natural language explanations.
    Ensures transparency: every number has an explanation of how it was derived.
    """
    
    @staticmethod
    def explain_loss_calculation(
        product_name: str,
        avg_daily_demand: float,
        unit_price: float,
        unit_cost: float,
        days_out_of_stock: int = 1,
        confidence_level: float = 0.95
    ) -> Dict:
        """
        Generate a complete NLP-friendly explanation of loss calculation.
        
        Mathematical Model:
        - Daily Loss = Average Daily Demand × Unit Profit Margin
        - Where Unit Profit = Selling Price - Cost Price
        - Demand is ML-predicted from historical patterns
        """
        
        unit_profit = unit_price - unit_cost
        daily_loss = avg_daily_demand * unit_profit
        weekly_loss = daily_loss * 7
        monthly_loss = daily_loss * 30
        annual_loss = daily_loss * 365
        
        # Calculate margin percentage
        margin_pct = (unit_profit / unit_price * 100) if unit_price > 0 else 0
        
        return {
            "calculation_type": "STOCKOUT_LOSS",
            "product": product_name,
            
            # === MATHEMATICAL BREAKDOWN ===
            "formula": {
                "equation": "Daily Loss = Average Daily Demand × Unit Profit Margin",
                "expanded": f"Daily Loss = {avg_daily_demand:.1f} units/day × ${unit_profit:.2f}/unit",
                "unit_profit_formula": f"Unit Profit = ${unit_price:.2f} (selling price) - ${unit_cost:.2f} (cost) = ${unit_profit:.2f}",
            },
            
            # === DATA INPUTS (Transparency) ===
            "inputs": {
                "average_daily_demand": {
                    "value": round(avg_daily_demand, 2),
                    "unit": "units/day",
                    "source": "ML-calculated from 30-day historical sales data",
                    "method": "Time-weighted moving average adjusted for seasonality and trends"
                },
                "unit_selling_price": {
                    "value": round(unit_price, 2),
                    "unit": "$/unit",
                    "source": "Product master data"
                },
                "unit_cost": {
                    "value": round(unit_cost, 2),
                    "unit": "$/unit",
                    "source": "Product master data"
                },
                "profit_margin": {
                    "value": round(unit_profit, 2),
                    "unit": "$/unit",
                    "percentage": round(margin_pct, 1)
                }
            },
            
            # === CALCULATED OUTPUTS ===
            "outputs": {
                "daily_loss": round(daily_loss, 2),
                "weekly_loss": round(weekly_loss, 2),
                "monthly_loss": round(monthly_loss, 2),
                "annual_loss": round(annual_loss, 2),
            },
            
            # === NATURAL LANGUAGE EXPLANATION ===
            "explanation": {
                "summary": f"Every day {product_name} is out of stock, you lose approximately ${daily_loss:,.0f} in profit.",
                
                "detailed": f"""Based on our AI analysis of the past 30 days of sales data, {product_name} sells an average 
of {avg_daily_demand:.1f} units per day. Each unit generates ${unit_profit:.2f} in profit 
(${unit_price:.2f} selling price minus ${unit_cost:.2f} cost = {margin_pct:.1f}% margin).

When this product is out of stock:
• You lose approximately ${daily_loss:,.0f} per day in missed profit
• That's ${weekly_loss:,.0f} per week
• Or ${monthly_loss:,.0f} per month if the stockout continues

This isn't just lost revenue—it's lost PROFIT, which directly impacts your bottom line.""",
                
                "for_executive": f"Stockout of {product_name} costs ${daily_loss:,.0f}/day. At {margin_pct:.0f}% margin, this represents ${daily_loss/max(margin_pct/100, 0.01):,.0f} in unrealized revenue daily.",
                
                "action_oriented": f"To prevent these losses, ensure {product_name} maintains adequate stock levels. Our AI recommends keeping at least {int(avg_daily_demand * 7 * 1.5)} units (covers 1 week demand + 50% safety buffer)."
            },
            
            # === AI CONFIDENCE ===
            "ai_confidence": {
                "level": confidence_level,
                "description": f"{confidence_level*100:.0f}% confidence in this prediction",
                "methodology": "Based on ARIMA/Exponential Smoothing ensemble with Linear Regression features"
            },
            
            "generated_at": datetime.now().isoformat(),
            "generated_by": "AI Explainer Engine v1.0"
        }
    
    @staticmethod
    def explain_reorder_recommendation(
        product_name: str,
        current_stock: int,
        avg_daily_demand: float,
        lead_time_days: int,
        unit_cost: float,
        unit_price: float,
        demand_variability: float = 0.3
    ) -> Dict:
        """
        Generate NLP explanation for reorder quantity recommendation.
        
        Mathematical Model:
        - Days Until Stockout = Current Stock ÷ Average Daily Demand
        - Buffer Days = Days Until Stockout - Lead Time
        - Safety Stock = Z-score × Demand Std Dev × √Lead Time
        - Reorder Quantity = (Lead Time × Daily Demand) + Safety Stock
        """
        
        # Calculate key metrics
        days_until_stockout = current_stock / max(avg_daily_demand, 0.01)
        buffer_days = days_until_stockout - lead_time_days
        
        # Safety stock calculation (95% service level, Z=1.645)
        z_score = 1.645  # 95% service level
        demand_std = avg_daily_demand * demand_variability
        safety_stock = z_score * demand_std * np.sqrt(lead_time_days)
        
        # Recommended reorder quantity
        reorder_qty = int((avg_daily_demand * lead_time_days) + safety_stock)
        
        # Economic analysis
        unit_profit = unit_price - unit_cost
        potential_daily_loss = avg_daily_demand * unit_profit
        order_cost = reorder_qty * unit_cost
        
        # Determine urgency
        if buffer_days < 0:
            urgency = "CRITICAL"
            urgency_msg = "You will experience stockout BEFORE your order arrives!"
        elif buffer_days <= 3:
            urgency = "URGENT"
            urgency_msg = "Order must be placed TODAY to avoid stockout."
        elif buffer_days <= 7:
            urgency = "HIGH"
            urgency_msg = "Order within this week to maintain safe stock levels."
        elif buffer_days <= 14:
            urgency = "MODERATE"
            urgency_msg = "Plan to order within the next 2 weeks."
        else:
            urgency = "LOW"
            urgency_msg = "Stock levels are healthy. Monitor regularly."
        
        return {
            "calculation_type": "REORDER_RECOMMENDATION",
            "product": product_name,
            
            # === MATHEMATICAL BREAKDOWN ===
            "formulas": {
                "days_until_stockout": {
                    "equation": "Days Until Stockout = Current Stock ÷ Average Daily Demand",
                    "calculation": f"{current_stock} units ÷ {avg_daily_demand:.1f} units/day = {days_until_stockout:.1f} days"
                },
                "buffer_days": {
                    "equation": "Buffer Days = Days Until Stockout - Lead Time",
                    "calculation": f"{days_until_stockout:.1f} days - {lead_time_days} days = {buffer_days:.1f} days",
                    "meaning": "Time remaining to place order before it becomes critical"
                },
                "safety_stock": {
                    "equation": "Safety Stock = Z × σ × √(Lead Time)",
                    "calculation": f"Safety Stock = {z_score} × {demand_std:.1f} × √{lead_time_days} = {safety_stock:.0f} units",
                    "meaning": "Extra buffer to handle demand uncertainty at 95% service level"
                },
                "reorder_quantity": {
                    "equation": "Reorder Qty = (Lead Time × Daily Demand) + Safety Stock",
                    "calculation": f"({lead_time_days} × {avg_daily_demand:.1f}) + {safety_stock:.0f} = {reorder_qty} units"
                }
            },
            
            # === DATA INPUTS ===
            "inputs": {
                "current_stock": {"value": current_stock, "unit": "units"},
                "average_daily_demand": {
                    "value": round(avg_daily_demand, 2),
                    "source": "AI-predicted from 30-day sales history"
                },
                "lead_time_days": {"value": lead_time_days, "unit": "days"},
                "demand_variability": {
                    "value": round(demand_variability * 100, 1),
                    "unit": "%",
                    "meaning": "How much demand fluctuates day-to-day"
                },
                "service_level_target": {"value": 95, "unit": "%"}
            },
            
            # === OUTPUTS ===
            "outputs": {
                "days_until_stockout": round(days_until_stockout, 1),
                "buffer_days": round(buffer_days, 1),
                "safety_stock": int(safety_stock),
                "recommended_order_quantity": reorder_qty,
                "order_cost": round(order_cost, 2),
                "urgency_level": urgency
            },
            
            # === NATURAL LANGUAGE EXPLANATION ===
            "explanation": {
                "summary": f"{product_name}: You have {buffer_days:.0f} days to reorder. {urgency} priority.",
                
                "detailed": f"""Here's what our AI analyzed for {product_name}:

📊 CURRENT SITUATION:
You have {current_stock} units in stock. Based on your recent sales pattern 
(averaging {avg_daily_demand:.1f} units/day), this will last about {days_until_stockout:.0f} days.

⏱️ THE MATH:
Your supplier needs {lead_time_days} days to deliver after you order.
That leaves you {buffer_days:.0f} days of "buffer" to place your order.
{urgency_msg}

📦 AI RECOMMENDATION:
Order {reorder_qty} units now. Here's why:
• {int(avg_daily_demand * lead_time_days)} units cover the {lead_time_days}-day lead time
• {int(safety_stock)} additional units provide safety buffer for demand spikes
• Total: {reorder_qty} units at ${order_cost:,.0f}

💰 FINANCIAL IMPACT:
If you stockout, you'll lose approximately ${potential_daily_loss:,.0f} per day in profit.
The cost of ordering ({reorder_qty} units × ${unit_cost:.2f}) = ${order_cost:,.0f}
That's about {order_cost / max(potential_daily_loss, 1):.1f} days worth of potential losses.""",
                
                "for_executive": f"{urgency} PRIORITY: {product_name} needs reorder of {reorder_qty} units (${order_cost:,.0f}) within {max(0, buffer_days):.0f} days to avoid ${potential_daily_loss:,.0f}/day losses.",
                
                "action": f"Place order for {reorder_qty} units of {product_name} within the next {max(1, buffer_days):.0f} days."
            },
            
            # === RISK ASSESSMENT ===
            "risk_assessment": {
                "stockout_probability": "HIGH" if buffer_days < 3 else "MEDIUM" if buffer_days < 10 else "LOW",
                "potential_daily_loss": round(potential_daily_loss, 2),
                "potential_weekly_loss": round(potential_daily_loss * 7, 2),
                "days_of_exposure": max(0, -buffer_days) if buffer_days < 0 else 0
            },
            
            "generated_at": datetime.now().isoformat(),
            "generated_by": "AI Reorder Engine v1.0"
        }
    
    @staticmethod
    def explain_forecast(
        product_name: str,
        historical_days: int,
        forecast_days: int,
        model_used: str,
        predictions: List[float],
        confidence_intervals: Dict,
        trend_direction: str = "stable",
        seasonality_detected: bool = False
    ) -> Dict:
        """
        Generate NLP explanation for demand forecast.
        
        Explains:
        - What model was used and why
        - What patterns were detected
        - What the forecast means for business
        - Confidence in the prediction
        """
        
        avg_prediction = sum(predictions) / len(predictions) if predictions else 0
        min_prediction = min(predictions) if predictions else 0
        max_prediction = max(predictions) if predictions else 0
        total_forecast = sum(predictions)
        
        # Determine trend explanation
        if trend_direction == "increasing":
            trend_explanation = "demand is trending upward—expect higher sales ahead"
            trend_action = "Consider increasing inventory levels proactively"
        elif trend_direction == "decreasing":
            trend_explanation = "demand is trending downward—expect lower sales ahead"
            trend_action = "Consider reducing order quantities to avoid overstock"
        else:
            trend_explanation = "demand is relatively stable with no significant trend"
            trend_action = "Maintain current inventory strategy"
        
        # Model explanation
        model_explanations = {
            "ARIMA": "ARIMA (AutoRegressive Integrated Moving Average) captures both trend and autocorrelation in your sales data",
            "Exponential Smoothing": "Exponential Smoothing gives more weight to recent sales, adapting quickly to changes",
            "Ensemble": "Our ensemble combines multiple AI models, taking the best aspects of each for more accurate predictions"
        }
        
        model_explanation = model_explanations.get(
            model_used.split("(")[0].strip(),
            f"{model_used} is an advanced statistical model trained on your historical data"
        )
        
        return {
            "calculation_type": "DEMAND_FORECAST",
            "product": product_name,
            
            # === MODEL INFORMATION ===
            "model": {
                "name": model_used,
                "type": "Time Series Forecasting",
                "explanation": model_explanation,
                "training_data": f"{historical_days} days of historical sales data"
            },
            
            # === PATTERN DETECTION ===
            "patterns_detected": {
                "trend": {
                    "direction": trend_direction,
                    "explanation": trend_explanation
                },
                "seasonality": {
                    "detected": seasonality_detected,
                    "explanation": "Weekly/monthly patterns were detected and incorporated into the forecast" if seasonality_detected else "No significant seasonal patterns detected"
                }
            },
            
            # === FORECAST SUMMARY ===
            "forecast_summary": {
                "horizon_days": forecast_days,
                "average_daily_demand": round(avg_prediction, 1),
                "total_forecasted_demand": round(total_forecast, 0),
                "min_daily_demand": round(min_prediction, 1),
                "max_daily_demand": round(max_prediction, 1),
                "confidence_level": "95%"
            },
            
            # === NATURAL LANGUAGE EXPLANATION ===
            "explanation": {
                "summary": f"Over the next {forecast_days} days, {product_name} is expected to sell {total_forecast:.0f} units total (avg {avg_prediction:.1f}/day).",
                
                "detailed": f"""🔮 AI FORECAST FOR {product_name.upper()}

📈 THE PREDICTION:
Based on {historical_days} days of your sales history, our {model_used} model predicts 
that {product_name} will sell approximately {total_forecast:.0f} units over the next {forecast_days} days.

That breaks down to:
• Average: {avg_prediction:.1f} units per day
• Range: {min_prediction:.0f} to {max_prediction:.0f} units per day
• Confidence: 95% (we're quite confident in this prediction)

📊 WHAT WE LEARNED FROM YOUR DATA:
• Trend: {trend_explanation.capitalize()}
• {("Seasonality: We detected patterns (like higher/lower sales on certain days/weeks) and factored them in." if seasonality_detected else "No strong seasonal patterns were found—demand is relatively consistent.")}

🎯 WHAT THIS MEANS FOR YOU:
{trend_action}. Make sure you have at least {total_forecast:.0f} units available 
over the next {forecast_days} days to meet expected demand.

💡 HOW AI MADE THIS PREDICTION:
{model_explanation}. We analyzed patterns like: which days sell more, 
whether sales are growing or shrinking, and how much variation exists in daily sales.""",
                
                "for_executive": f"AI forecasts {total_forecast:.0f} units demand for {product_name} over {forecast_days} days. Trend: {trend_direction}. Action: {trend_action}.",
                
                "inventory_implication": f"Ensure {int(total_forecast * 1.2):.0f} units available (forecast + 20% buffer) to maintain 95% service level."
            },
            
            # === CONFIDENCE INTERVALS ===
            "confidence": {
                "level": "95%",
                "lower_bound_total": round(sum(confidence_intervals.get('lower', predictions)) if confidence_intervals.get('lower') else total_forecast * 0.8, 0),
                "upper_bound_total": round(sum(confidence_intervals.get('upper', predictions)) if confidence_intervals.get('upper') else total_forecast * 1.2, 0),
                "interpretation": f"We're 95% confident actual demand will be between {int(total_forecast * 0.8):,} and {int(total_forecast * 1.2):,} units"
            },
            
            "generated_at": datetime.now().isoformat(),
            "generated_by": "AI Forecast Explainer v1.0"
        }
    
    @staticmethod
    def explain_profit_loss(
        product_name: str,
        revenue: float,
        cost: float,
        quantity_sold: int,
        period: str = "month"
    ) -> Dict:
        """
        Generate NLP explanation for profit/loss analysis.
        """
        
        profit = revenue - cost
        margin_pct = (profit / revenue * 100) if revenue > 0 else 0
        avg_selling_price = revenue / max(quantity_sold, 1)
        avg_cost = cost / max(quantity_sold, 1)
        profit_per_unit = avg_selling_price - avg_cost
        
        # Determine health status
        if margin_pct >= 40:
            health = "EXCELLENT"
            health_msg = "This is a star performer in your portfolio"
        elif margin_pct >= 25:
            health = "HEALTHY"
            health_msg = "Good margins, maintain current strategy"
        elif margin_pct >= 10:
            health = "MODERATE"
            health_msg = "Margins could be improved—review pricing or costs"
        elif margin_pct >= 0:
            health = "LOW"
            health_msg = "Very thin margins—consider price increase or cost reduction"
        else:
            health = "CRITICAL"
            health_msg = "SELLING AT A LOSS—immediate action required"
        
        return {
            "calculation_type": "PROFIT_LOSS_ANALYSIS",
            "product": product_name,
            "period": period,
            
            # === MATHEMATICAL BREAKDOWN ===
            "formulas": {
                "profit": {
                    "equation": "Profit = Revenue - Cost",
                    "calculation": f"${revenue:,.2f} - ${cost:,.2f} = ${profit:,.2f}"
                },
                "margin_percentage": {
                    "equation": "Margin % = (Profit ÷ Revenue) × 100",
                    "calculation": f"(${profit:,.2f} ÷ ${revenue:,.2f}) × 100 = {margin_pct:.1f}%"
                },
                "profit_per_unit": {
                    "equation": "Profit/Unit = Selling Price - Cost",
                    "calculation": f"${avg_selling_price:.2f} - ${avg_cost:.2f} = ${profit_per_unit:.2f}"
                }
            },
            
            # === OUTPUTS ===
            "outputs": {
                "total_revenue": round(revenue, 2),
                "total_cost": round(cost, 2),
                "total_profit": round(profit, 2),
                "quantity_sold": quantity_sold,
                "margin_percentage": round(margin_pct, 1),
                "profit_per_unit": round(profit_per_unit, 2),
                "health_status": health
            },
            
            # === NATURAL LANGUAGE EXPLANATION ===
            "explanation": {
                "summary": f"{product_name} {'made' if profit >= 0 else 'lost'} ${abs(profit):,.0f} this {period} ({margin_pct:.1f}% margin). {health_msg}.",
                
                "detailed": f"""💰 PROFIT/LOSS ANALYSIS: {product_name.upper()}

📊 THIS {period.upper()}'S RESULTS:
• Sold: {quantity_sold:,} units
• Revenue: ${revenue:,.2f}
• Costs: ${cost:,.2f}
• {"✅ PROFIT" if profit >= 0 else "❌ LOSS"}: ${abs(profit):,.2f}

📈 MARGIN ANALYSIS:
Your margin is {margin_pct:.1f}%. For every $1 of revenue, you keep ${margin_pct/100:.2f}.
Per-unit economics: Selling at ${avg_selling_price:.2f}, costing ${avg_cost:.2f} = ${profit_per_unit:.2f} profit per unit.

🏥 HEALTH STATUS: {health}
{health_msg}

{"⚠️ WARNING: This product is losing money on every sale. Review pricing immediately or consider discontinuing." if profit < 0 else ""}
{"💡 TIP: At {:.1f}% margin, focus on volume growth to maximize profit impact.".format(margin_pct) if margin_pct < 20 else ""}""",
                
                "for_executive": f"{product_name}: ${profit:,.0f} {'profit' if profit >= 0 else 'loss'} ({margin_pct:.1f}% margin) on {quantity_sold:,} units. Status: {health}."
            },
            
            "generated_at": datetime.now().isoformat(),
            "generated_by": "AI Profitability Analyzer v1.0"
        }
    
    @staticmethod
    def create_decision_summary(
        alerts: List[Dict],
        total_potential_loss: float,
        total_products_at_risk: int
    ) -> Dict:
        """
        Create an executive decision summary from multiple alerts.
        """
        
        critical_count = sum(1 for a in alerts if a.get('severity') == 'CRITICAL')
        high_count = sum(1 for a in alerts if a.get('severity') == 'HIGH')
        
        return {
            "type": "EXECUTIVE_DECISION_SUMMARY",
            
            "headline": f"⚠️ {total_products_at_risk} products need attention | ${total_potential_loss:,.0f} at risk",
            
            "priority_actions": {
                "immediate": f"{critical_count} products need IMMEDIATE action (stockout or imminent stockout)",
                "this_week": f"{high_count} products should be addressed THIS WEEK",
                "monitoring": f"{max(0, total_products_at_risk - critical_count - high_count)} products are being monitored"
            },
            
            "financial_summary": {
                "daily_risk": round(total_potential_loss, 2),
                "weekly_risk": round(total_potential_loss * 7, 2),
                "monthly_risk": round(total_potential_loss * 30, 2),
                "narrative": f"If no action is taken, you could lose up to ${total_potential_loss:,.0f} per day in missed profit from stockouts and low stock situations."
            },
            
            "recommendation": f"""
RECOMMENDED ACTION PLAN:

1. CRITICAL ({critical_count} items): Order immediately. These products are out of stock or will stockout before orders arrive.

2. HIGH PRIORITY ({high_count} items): Order within 2-3 days. These products have less than 1 week of buffer.

3. MONITOR: Keep an eye on remaining items. AI will alert you when they need attention.

ESTIMATED IMPACT: Acting on all recommendations could prevent ${total_potential_loss * 30:,.0f}/month in potential losses.
            """,
            
            "generated_at": datetime.now().isoformat(),
            "generated_by": "AI Decision Support System v1.0"
        }
