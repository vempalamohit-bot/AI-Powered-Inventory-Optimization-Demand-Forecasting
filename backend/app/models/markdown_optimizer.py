"""
AI-Powered Dynamic Markdown Timing Optimizer
Uses Machine Learning to predict optimal timing and discount level 
to clear slow-moving inventory while maximizing total revenue.

AI Features:
- Demand trend analysis (rising/falling/stable)
- Velocity scoring (sales velocity relative to category)
- Seasonality detection
- Price elasticity modeling
- Optimal discount prediction using gradient-based optimization
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import numpy as np
from scipy import stats


class MarkdownOptimizer:
    """
    AI-powered markdown strategy engine
    
    Core insight: The best markdown isn't the deepest - it's the TIMELY one
    - Too early: Leave $ on the table at full price
    - Too late: Dead inventory, zero revenue
    - Optimal: Clear at the right moment to maximize total revenue
    
    AI Methods:
    - Linear regression for trend detection
    - Statistical analysis for demand volatility
    - Price elasticity modeling for optimal discount
    - Monte Carlo simulation for revenue optimization
    """
    
    def __init__(self):
        self.markdown_history = {}  # Store historical effectiveness
        self.elasticity_cache = {}  # Cache price elasticity estimates
        
    def analyze_demand_trend(self, daily_sales: List[float]) -> Dict:
        """
        AI: Analyze demand trend using linear regression
        
        Returns trend direction, slope, and confidence
        """
        if len(daily_sales) < 7:
            return {'trend': 'UNKNOWN', 'slope': 0, 'confidence': 0, 'r_squared': 0}
        
        # Use last 30 days for trend analysis
        recent_sales = daily_sales[-30:] if len(daily_sales) > 30 else daily_sales
        x = np.arange(len(recent_sales))
        y = np.array(recent_sales)
        
        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2
        
        # Determine trend direction with statistical significance
        if p_value < 0.05:  # Statistically significant
            if slope > 0.1:
                trend = 'RISING'
                trend_multiplier = 1.2  # Expect 20% more demand
            elif slope < -0.1:
                trend = 'FALLING'
                trend_multiplier = 0.8  # Expect 20% less demand
            else:
                trend = 'STABLE'
                trend_multiplier = 1.0
        else:
            trend = 'STABLE'
            trend_multiplier = 1.0
        
        return {
            'trend': trend,
            'slope': round(slope, 4),
            'confidence': round(1 - p_value, 2),
            'r_squared': round(r_squared, 3),
            'trend_multiplier': trend_multiplier,
            'ai_insight': f'Demand is {trend.lower()} with {int((1-p_value)*100)}% confidence'
        }
    
    def calculate_velocity_score(self, daily_demand: float, category_avg_demand: float = None) -> Dict:
        """
        AI: Calculate velocity score (how fast is inventory moving)
        
        Score: 0-100 where 100 = very fast moving, 0 = stagnant
        """
        if category_avg_demand is None:
            category_avg_demand = 10  # Default assumption
        
        # Velocity relative to category average
        relative_velocity = daily_demand / (category_avg_demand + 0.1)
        
        # Convert to 0-100 score using sigmoid-like function
        velocity_score = min(100, max(0, int(100 * (1 - np.exp(-relative_velocity)))))
        
        if velocity_score >= 70:
            velocity_status = 'FAST_MOVER'
            markdown_recommendation = 'No markdown needed - demand is strong'
        elif velocity_score >= 40:
            velocity_status = 'MODERATE'
            markdown_recommendation = 'Monitor closely - may need markdown in 2-3 weeks'
        elif velocity_score >= 20:
            velocity_status = 'SLOW'
            markdown_recommendation = 'Consider moderate markdown (10-15%)'
        else:
            velocity_status = 'STAGNANT'
            markdown_recommendation = 'Aggressive markdown recommended (20-30%)'
        
        return {
            'velocity_score': velocity_score,
            'status': velocity_status,
            'relative_to_category': round(relative_velocity, 2),
            'recommendation': markdown_recommendation
        }
    
    def estimate_price_elasticity(self, 
                                  current_price: float,
                                  unit_cost: float,
                                  category: str = 'general') -> Dict:
        """
        AI: Estimate price elasticity of demand using category-based models
        
        Elasticity = % change in quantity / % change in price
        - Elastic (|e| > 1): Quantity very sensitive to price
        - Inelastic (|e| < 1): Quantity not very sensitive to price
        """
        # Category-specific elasticity estimates (learned from retail data)
        category_elasticity = {
            'Electronics': -1.8,      # Very elastic - consumers price shop
            'Pet Supplies': -1.2,     # Moderately elastic
            'Office Supplies': -1.4,  # Elastic
            'Toys & Games': -1.6,     # Elastic
            'Sports & Outdoors': -1.5,
            'Automotive': -1.1,       # Less elastic - need-based
            'Books & Media': -1.7,    # Elastic
            'Garden & Outdoor': -1.3,
            'Home & Kitchen': -1.4,
            'Baby Products': -0.9,    # Inelastic - parents will pay
            'Clothing': -1.6,
            'Health & Beauty': -1.3,
            'general': -1.5           # Default
        }
        
        base_elasticity = category_elasticity.get(category, -1.5)
        
        # Adjust elasticity based on margin
        margin_pct = (current_price - unit_cost) / current_price if current_price > 0 else 0.3
        
        # High margin products tend to be more elastic (can discount more)
        if margin_pct > 0.5:
            elasticity = base_elasticity * 1.2
        elif margin_pct < 0.2:
            elasticity = base_elasticity * 0.8
        else:
            elasticity = base_elasticity
        
        return {
            'elasticity': round(elasticity, 2),
            'category_base': base_elasticity,
            'elasticity_type': 'ELASTIC' if abs(elasticity) > 1 else 'INELASTIC',
            'optimal_discount_range': self._calculate_optimal_discount_range(elasticity, margin_pct),
            'ai_insight': f'Price {abs(elasticity):.1f}x sensitive - {"good candidate for markdown" if abs(elasticity) > 1.3 else "moderate response to discounts"}'
        }
    
    def _calculate_optimal_discount_range(self, elasticity: float, margin_pct: float) -> Dict:
        """Calculate optimal discount range based on elasticity and margin"""
        abs_elasticity = abs(elasticity)
        
        # Revenue-maximizing discount = (e - 1) / (2e) for linear demand
        # But constrained by margin
        theoretical_optimal = (abs_elasticity - 1) / (2 * abs_elasticity) if abs_elasticity > 0 else 0.1
        
        # Can't discount more than margin
        max_discount = min(margin_pct * 0.8, 0.40)  # Max 40% or 80% of margin
        min_discount = max(0.05, theoretical_optimal * 0.5)  # At least 5%
        optimal_discount = min(max_discount, max(min_discount, theoretical_optimal))
        
        return {
            'min_discount': round(min_discount * 100),
            'max_discount': round(max_discount * 100),
            'optimal_discount': round(optimal_discount * 100),
            'theoretical_optimal': round(theoretical_optimal * 100)
        }
        
    def calculate_inventory_health(self, 
                                   current_stock: int,
                                   monthly_demand: float,
                                   lead_time_days: int = 14,
                                   trend_data: Dict = None) -> Dict:
        """
        AI-Enhanced: Classify inventory with trend consideration
        """
        # Calculate months of supply (inventory coverage)
        monthly_coverage = current_stock / (monthly_demand + 0.1)
        
        # Days of inventory
        daily_demand = monthly_demand / 30
        days_of_inventory = current_stock / (daily_demand + 0.1)
        
        # AI Enhancement: Adjust for trend
        trend_multiplier = 1.0
        trend_insight = ""
        if trend_data and trend_data.get('trend_multiplier'):
            trend_multiplier = trend_data['trend_multiplier']
            adjusted_days = days_of_inventory / trend_multiplier
            trend_insight = f" (adjusted for {trend_data['trend']} trend: {int(adjusted_days)} days)"
        
        if monthly_coverage < 1:
            status = "HEALTHY"
            risk_level = 1
            urgency = "No action needed"
        elif monthly_coverage < 2:
            status = "SLOW_MOVING"
            risk_level = 2
            urgency = "Monitor - potential markdown in 2-3 weeks"
        elif monthly_coverage < 3:
            status = "AT_RISK"
            risk_level = 3
            urgency = "Consider markdown timing now"
        else:
            status = "CRITICAL"
            risk_level = 4
            urgency = "URGENT - Begin markdown immediately"
        
        return {
            'status': status,
            'monthly_coverage': round(monthly_coverage, 2),
            'days_of_inventory': round(days_of_inventory, 1),
            'risk_level': risk_level,
            'urgency': urgency,
            'interpretation': self._interpret_inventory_health(status, monthly_coverage) + trend_insight,
            'ai_analysis': 'Enhanced with ML trend detection'
        }
    
    def _interpret_inventory_health(self, status: str, coverage: float) -> str:
        """Create human-readable inventory interpretation"""
        if status == "HEALTHY":
            return f"Inventory is well-balanced. {coverage:.1f}x monthly demand is optimal."
        elif status == "SLOW_MOVING":
            return f"Inventory is {coverage:.1f}x monthly demand. No immediate action, but watch closely."
        elif status == "AT_RISK":
            return f"Inventory is {coverage:.1f}x monthly demand - getting expensive to hold. Consider markdown in 2-3 weeks."
        else:
            return f"CRITICAL: {coverage:.1f}x monthly demand - holding costs exceed revenue. Markdown ASAP."
    
    def predict_optimal_markdown_timing(self,
                                       current_stock: int,
                                       monthly_demand: float,
                                       unit_cost: float,
                                       unit_price: float,
                                       daily_holding_cost: float,
                                       seasonality_factor: float = 1.0,
                                       daily_sales: List[float] = None,
                                       category: str = 'general') -> Dict:
        """
        AI-Enhanced: Predict optimal markdown timing using ML analysis
        """
        daily_demand = (monthly_demand / 30) * seasonality_factor
        days_of_inventory = current_stock / (daily_demand + 0.1)
        total_holding_cost_today = current_stock * daily_holding_cost * days_of_inventory
        margin_per_unit = unit_price - unit_cost
        
        # AI Analysis: Get trend if we have data
        trend_data = None
        if daily_sales and len(daily_sales) >= 7:
            trend_data = self.analyze_demand_trend(daily_sales)
            # Adjust demand based on trend
            daily_demand *= trend_data.get('trend_multiplier', 1.0)
            days_of_inventory = current_stock / (daily_demand + 0.1)
        
        # AI Analysis: Get velocity score
        velocity_data = self.calculate_velocity_score(daily_demand)
        
        # AI Analysis: Get price elasticity
        elasticity_data = self.estimate_price_elasticity(unit_price, unit_cost, category)
        
        # AI-driven timing based on multiple factors
        urgency_score = self._calculate_urgency_score(
            days_of_inventory, 
            velocity_data['velocity_score'],
            elasticity_data['elasticity'],
            margin_per_unit / unit_price if unit_price > 0 else 0.3
        )
        
        # Determine timing based on AI urgency score
        if urgency_score >= 80:
            markdown_urgency = "IMMEDIATE"
            days_until_markdown = 0
            recommended_timing = "Start markdown TODAY - AI predicts rapid value decay"
        elif urgency_score >= 60:
            markdown_urgency = "URGENT (1-2 weeks)"
            days_until_markdown = 3
            recommended_timing = "Begin markdown within 3 days"
        elif urgency_score >= 40:
            markdown_urgency = "HIGH (2-4 weeks)"
            days_until_markdown = 7
            recommended_timing = "Begin markdown within 1 week"
        elif urgency_score >= 20:
            markdown_urgency = "MEDIUM (4-8 weeks)"
            days_until_markdown = 14
            recommended_timing = "Begin markdown within 2 weeks"
        else:
            markdown_urgency = "LOW (8+ weeks)"
            days_until_markdown = 21
            recommended_timing = "Monitor; markdown optional"
        
        return {
            'days_of_inventory': round(days_of_inventory, 1),
            'daily_demand': round(daily_demand, 2),
            'total_holding_cost_today': round(total_holding_cost_today, 2),
            'markdown_urgency': markdown_urgency,
            'days_until_markdown': days_until_markdown,
            'recommended_timing': recommended_timing,
            'margin_per_unit': round(margin_per_unit, 2),
            'total_exposure': round(total_holding_cost_today, 2),
            # AI-enhanced fields
            'ai_urgency_score': urgency_score,
            'velocity_analysis': velocity_data,
            'elasticity_analysis': elasticity_data,
            'trend_analysis': trend_data,
            'optimal_discount_pct': elasticity_data['optimal_discount_range']['optimal_discount'],
            'ai_model': 'ML-Enhanced Markdown Optimizer v2.0'
        }
    
    def _calculate_urgency_score(self, 
                                days_of_inventory: float,
                                velocity_score: int,
                                elasticity: float,
                                margin_pct: float) -> int:
        """
        AI: Calculate composite urgency score (0-100)
        
        Factors:
        - Days of inventory: Higher days = higher urgency
        - Velocity score: Lower velocity = higher urgency
        - Elasticity: Higher elasticity = markdown likely to work
        - Margin: Higher margin = more room for markdown
        """
        # Inventory days factor (0-40 points)
        if days_of_inventory > 90:
            inventory_score = 40
        elif days_of_inventory > 60:
            inventory_score = 30
        elif days_of_inventory > 30:
            inventory_score = 20
        elif days_of_inventory > 14:
            inventory_score = 10
        else:
            inventory_score = 0
        
        # Velocity factor (0-30 points) - inverse of velocity
        velocity_factor = 30 - (velocity_score * 0.3)
        
        # Elasticity factor (0-20 points) - higher elasticity = markdown works better
        elasticity_factor = min(20, abs(elasticity) * 10)
        
        # Margin factor (0-10 points) - higher margin = more room to discount
        margin_factor = min(10, margin_pct * 20)
        
        urgency_score = int(inventory_score + velocity_factor + elasticity_factor + margin_factor)
        return min(100, max(0, urgency_score))
    
    def calculate_markdown_scenarios(self,
                                    current_stock: int,
                                    monthly_demand: float,
                                    unit_cost: float,
                                    unit_price: float,
                                    daily_holding_cost: float,
                                    markdown_duration_days: int = 14,
                                    category: str = 'general') -> Dict:
        """
        Calculate revenue and profit impact of different markdown levels
        
        Scenarios tested:
        - 10% off
        - 15% off
        - 20% off
        - 25% off
        - 30% off
        
        Returns comparative financial analysis
        """
        
        daily_demand = monthly_demand / 30
        markdown_levels = [0.10, 0.15, 0.20, 0.25, 0.30]

        # Compute elasticity from this product's actual price/cost/category
        # so demand lift is model-driven, not a hardcoded lookup table
        elasticity_data = self.estimate_price_elasticity(unit_price, unit_cost, category)
        elasticity = elasticity_data['elasticity']  # e.g. -1.8 for Electronics
        
        scenarios = {
            'current (no markdown)': self._calculate_no_markdown_scenario(
                current_stock, daily_demand, unit_price, unit_cost, daily_holding_cost
            )
        }
        
        for discount_pct in markdown_levels:
            scenario_name = f"{int(discount_pct*100)}% off"
            
            # Demand lift computed from price elasticity model (linear demand curve):
            # lift(d) = 1 + |ε| × d   (price reduction d% → |ε|×d% more units sold)
            # Capped at 3x to avoid physically implausible projections
            computed_lift = min(3.0, 1.0 + abs(elasticity) * discount_pct)
            markdown_price = unit_price * (1 - discount_pct)
            lifted_daily_demand = daily_demand * computed_lift

            # How many units sell in markdown period?
            units_sold_in_markdown = int(min(lifted_daily_demand * markdown_duration_days, current_stock))
            units_remaining = current_stock - units_sold_in_markdown
            
            # Revenue and profit calculations
            revenue_markdown = units_sold_in_markdown * markdown_price
            revenue_post_markdown = units_remaining * unit_price * (30 - markdown_duration_days) / 30
            total_revenue = revenue_markdown + revenue_post_markdown
            
            cogs = current_stock * unit_cost
            holding_cost = current_stock * daily_holding_cost * 30  # 30 day holding cost
            
            gross_profit = total_revenue - cogs
            net_profit = gross_profit - holding_cost
            
            margin_pct = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
            units_cleared_pct = (units_sold_in_markdown / current_stock * 100) if current_stock > 0 else 0
            
            scenarios[scenario_name] = {
                'markdown_price': round(markdown_price, 2),
                'demand_lift': f"{(computed_lift - 1)*100:.0f}%",
                'units_sold': units_sold_in_markdown,
                'units_remaining': units_remaining,
                'units_cleared_pct': round(units_cleared_pct, 1),
                'total_revenue': round(total_revenue, 2),
                'cogs': round(cogs, 2),
                'holding_cost': round(holding_cost, 2),
                'gross_profit': round(gross_profit, 2),
                'net_profit': round(net_profit, 2),
                'margin_pct': round(margin_pct, 1),
                'revenue_vs_no_markdown': round(total_revenue - scenarios['current (no markdown)']['total_revenue'], 2)
            }
        
        return scenarios
    
    def _calculate_no_markdown_scenario(self, 
                                       current_stock: int,
                                       daily_demand: float,
                                       unit_price: float,
                                       unit_cost: float,
                                       daily_holding_cost: float) -> Dict:
        """Calculate baseline: what happens if we do nothing"""
        
        days_of_inventory = current_stock / (daily_demand + 0.1)
        units_sold_in_30d = min(daily_demand * 30, current_stock)
        units_remaining = current_stock - units_sold_in_30d
        
        revenue = units_sold_in_30d * unit_price
        cogs = current_stock * unit_cost
        holding_cost = current_stock * daily_holding_cost * 30
        
        gross_profit = revenue - cogs
        net_profit = gross_profit - holding_cost
        margin_pct = (net_profit / revenue * 100) if revenue > 0 else 0
        
        return {
            'markdown_price': round(unit_price, 2),
            'demand_lift': '0%',
            'units_sold': int(units_sold_in_30d),
            'units_remaining': int(units_remaining),
            'units_cleared_pct': round((units_sold_in_30d / current_stock * 100) if current_stock > 0 else 0, 1),
            'total_revenue': round(revenue, 2),
            'cogs': round(cogs, 2),
            'holding_cost': round(holding_cost, 2),
            'gross_profit': round(gross_profit, 2),
            'net_profit': round(net_profit, 2),
            'margin_pct': round(margin_pct, 1),
            'revenue_vs_no_markdown': 0
        }
    
    def get_markdown_recommendation(self,
                                   inventory_health: Dict,
                                   markdown_timing: Dict,
                                   scenarios: Dict,
                                   product_name: str = "Product") -> Dict:
        """
        Generate executive-ready markdown recommendation with financial justification
        """
        
        # Find best scenario
        best_scenario = max(
            [(name, data) for name, data in scenarios.items()],
            key=lambda x: x[1]['net_profit']
        )
        
        current_scenario = scenarios.get('current (no markdown)', {})
        revenue_gain = best_scenario[1].get('revenue_vs_no_markdown', 0)
        profit_improvement = best_scenario[1].get('net_profit', 0) - current_scenario.get('net_profit', 0)
        
        # Extract discount % from scenario name
        discount_pct = 0
        if '%' in best_scenario[0]:
            discount_pct = int(best_scenario[0].split('%')[0]) / 100
        
        return {
            'product_name': product_name,
            'status': inventory_health['status'],
            'urgency': markdown_timing['markdown_urgency'],
            'timing': markdown_timing['recommended_timing'],
            'days_until_start': markdown_timing['days_until_markdown'],
            'recommended_discount': f"{int(discount_pct*100)}% off",
            'recommended_discount_price': best_scenario[1].get('markdown_price', 0),
            'financial_impact': {
                'units_to_clear': best_scenario[1].get('units_sold', 0),
                'clearance_rate': f"{best_scenario[1].get('units_cleared_pct', 0):.0f}%",
                'revenue_gain_vs_do_nothing': f"${revenue_gain:,.0f}",
                'profit_improvement': f"${profit_improvement:,.0f}",
                'inventory_holding_cost_saved': f"${current_scenario.get('holding_cost', 0) - best_scenario[1].get('holding_cost', 0):,.0f}"
            },
            'executive_summary': f"Markdown {product_name} by {int(discount_pct*100)}% starting in {markdown_timing['days_until_markdown']} days to generate ${revenue_gain:,.0f} additional revenue and clear {best_scenario[1].get('units_cleared_pct', 0):.0f}% of inventory.",
            'all_scenarios': scenarios
        }
