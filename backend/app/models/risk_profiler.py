import numpy as np
import pandas as pd
from typing import Dict, List
from enum import Enum

class RiskProfile(Enum):
    """Risk tolerance profiles - map to business strategy"""
    CONSERVATIVE = {"sl_target": 0.99, "description": "Critical items - pharma, medical, aerospace"}
    BALANCED = {"sl_target": 0.95, "description": "Standard products - most retail/FMCG"}
    AGGRESSIVE = {"sl_target": 0.90, "description": "Fashion, seasonal, fast-moving trendy items"}

class RiskProfiler:
    """
    RISK-ADJUSTED INVENTORY PLANNING
    
    Philosophy: Different products need different strategies.
    - Pharma needs 99% service level (regulated, critical)
    - FMCG needs 95% (manageable stockout risk)
    - Fashion needs 90% (high obsolescence cost)
    
    Output: CFO-friendly matrix showing service level vs cost trade-off
    
    "If we inventory-manage this product for 95% service vs 99%, we free up $2M working capital"
    """
    
    def __init__(self):
        self.holding_cost_rate = 0.25
        self.ordering_cost = 50
    
    def classify_product_risk_profile(
        self,
        product_name: str,
        annual_demand: float,
        demand_volatility: float,  # Coefficient of variation (std/mean)
        unit_margin_pct: float,
        product_lifespan_months: int,
        supplier_reliability_pct: float,
        customer_criticality: str  # "critical", "important", "standard", "seasonal"
    ) -> Dict:
        """
        Automatically classify product into risk profile (Conservative/Balanced/Aggressive)
        based on business characteristics.
        
        This is the SCORING ENGINE that justifies why SKU X needs 99% vs why SKU Y needs 90%.
        """
        
        # Scoring factors (0-100)
        scores = {}
        
        # 1. Criticality Score (40% weight)
        criticality_map = {
            "critical": 100,      # Pharma, medical implants
            "important": 70,      # Key revenue drivers
            "standard": 50,       # Regular products
            "seasonal": 30        # Fashion, seasonal items
        }
        scores['criticality'] = criticality_map.get(customer_criticality, 50)
        
        # 2. Volatility Score (30% weight) - high volatility = need buffer
        # Convert to 0-100 (0 = stable, 100 = highly volatile)
        volatility_score = min(100, demand_volatility * 100)
        scores['volatility'] = volatility_score
        
        # 3. Margin Health (20% weight) - high margin = afford service
        scores['margin'] = min(100, unit_margin_pct * 100)
        
        # 4. Product Lifespan (10% weight) - short lifespan = more aggressive
        if product_lifespan_months < 3:
            scores['lifespan'] = 30  # Seasonal/trendy
        elif product_lifespan_months < 12:
            scores['lifespan'] = 50  # Medium
        else:
            scores['lifespan'] = 80  # Stable/evergreen
        
        # Weighted composite score
        risk_tendency_score = (
            scores['criticality'] * 0.40 +
            scores['volatility'] * 0.30 +
            scores['margin'] * 0.20 +
            scores['lifespan'] * 0.10
        )
        
        # Determine profile
        if risk_tendency_score >= 70:
            profile = "CONSERVATIVE"
            target_sl = 0.99
            rationale = "High criticality, stable demand, or regulated industry"
        elif risk_tendency_score >= 50:
            profile = "BALANCED"
            target_sl = 0.95
            rationale = "Standard product with moderate characteristics"
        else:
            profile = "AGGRESSIVE"
            target_sl = 0.90
            rationale = "High obsolescence risk, volatile demand, or seasonal"
        
        # Supplier reliability adjustment
        if supplier_reliability_pct < 85:
            target_sl += 0.02  # Add 2 percentage points for unreliable suppliers
            rationale += " (Supplier reliability adjusted)"
        
        return {
            'product_name': product_name,
            'recommended_profile': profile,
            'profile_target_service_level': round(target_sl * 100, 1),
            'confidence_score': round(risk_tendency_score, 1),
            'rationale': rationale,
            'component_scores': {
                'criticality': round(scores['criticality'], 1),
                'demand_volatility': round(scores['volatility'], 1),
                'margin_health': round(scores['margin'], 1),
                'product_lifespan': round(scores['lifespan'], 1)
            },
            'supplier_adjustment': {
                'reliability_pct': supplier_reliability_pct,
                'adjustment_applied': "Yes" if supplier_reliability_pct < 85 else "No"
            }
        }
    
    def generate_risk_profile_inventory_plan(
        self,
        product_name: str,
        risk_profile: str,  # "CONSERVATIVE", "BALANCED", "AGGRESSIVE"
        annual_demand: float,
        demand_std: float,
        unit_cost: float,
        unit_price: float,
        lead_time_days: int,
        current_stock: float,
        supplier_lead_time_variance: float = 0.0
    ) -> Dict:
        """
        Generate complete inventory plan for a product given its risk profile.
        
        Returns: Service level targets, safety stock, order points, and cost implications.
        
        This is what CFOs love: one table that shows the trade-off.
        """
        
        from scipy import stats
        
        # Map profile to service level
        profile_map = {
            "CONSERVATIVE": 0.99,
            "BALANCED": 0.95,
            "AGGRESSIVE": 0.90
        }
        target_sl = profile_map.get(risk_profile, 0.95)
        
        unit_margin = unit_price - unit_cost
        daily_demand = annual_demand / 365
        holding_cost_per_unit = unit_cost * self.holding_cost_rate
        
        # Calculate z-score for service level
        z_score = stats.norm.ppf(target_sl)
        
        # Adjust for supplier variability
        adjusted_lead_time = lead_time_days * (1 + supplier_lead_time_variance)
        
        # Safety stock calculation
        safety_stock = z_score * demand_std * np.sqrt(adjusted_lead_time)
        
        # Reorder point
        reorder_point = (daily_demand * adjusted_lead_time) + safety_stock
        
        # EOQ
        if holding_cost_per_unit > 0:
            eoq = np.sqrt((2 * annual_demand * self.ordering_cost) / holding_cost_per_unit)
        else:
            eoq = annual_demand / 12
        
        # Maximum inventory (ROP + EOQ)
        max_inventory = reorder_point + eoq
        
        # Costs
        annual_ordering_cost = (annual_demand / eoq) * self.ordering_cost
        annual_holding_cost = (safety_stock + eoq/2) * holding_cost_per_unit
        total_inventory_cost = annual_ordering_cost + annual_holding_cost
        
        # Working capital
        avg_inventory_units = safety_stock + (eoq / 2)
        inventory_value = avg_inventory_units * unit_cost
        
        # Risk metrics
        stockout_probability = 1 - target_sl
        estimated_annual_stockout_units = annual_demand * stockout_probability * 0.01
        estimated_lost_margin = estimated_annual_stockout_units * unit_margin
        
        # Decision metrics
        order_recommendation = "ORDER" if current_stock < reorder_point else "HOLD"
        order_qty = max(0, reorder_point - current_stock) if current_stock < reorder_point else 0
        if order_qty > 0:
            order_qty = max(order_qty, eoq)
        
        return {
            'product_name': product_name,
            'risk_profile_applied': risk_profile,
            'inventory_policy': {
                'service_level_target': round(target_sl * 100, 1),
                'reorder_point': round(reorder_point, 1),
                'safety_stock': round(safety_stock, 1),
                'economic_order_quantity': round(eoq, 1),
                'maximum_inventory': round(max_inventory, 1),
                'order_recommendation': order_recommendation,
                'order_quantity_if_needed': round(order_qty, 0) if order_qty > 0 else 0
            },
            'cost_structure': {
                'annual_ordering_cost': round(annual_ordering_cost, 2),
                'annual_holding_cost': round(annual_holding_cost, 2),
                'total_annual_inventory_cost': round(total_inventory_cost, 2),
                'cost_per_unit_annual': round(total_inventory_cost / max(1, annual_demand), 4)
            },
            'financial_impact': {
                'average_inventory_units': round(avg_inventory_units, 0),
                'average_inventory_value': round(inventory_value, 2),
                'stockout_probability': round(stockout_probability * 100, 2),
                'estimated_annual_lost_margin': round(estimated_lost_margin, 2)
            },
            'performance_metrics': {
                'inventory_turnover': round(annual_demand / max(1, avg_inventory_units), 2),
                'days_of_inventory': round(avg_inventory_units / daily_demand, 1) if daily_demand > 0 else 0,
                'cash_to_inventory_ratio': round(inventory_value / unit_margin / max(1, annual_demand), 2)
            }
        }
    
    def compare_risk_profiles_for_sku(
        self,
        product_name: str,
        annual_demand: float,
        demand_std: float,
        unit_cost: float,
        unit_price: float,
        lead_time_days: int
    ) -> Dict:
        """
        Show CFO the exact cost and working capital trade-off across all 3 risk profiles.
        
        "If we accept 90% vs 99% service level, we free up $2M working capital and save $150K/year"
        
        This is the TABLE that wins executive approval.
        """
        
        unit_margin = unit_price - unit_cost
        daily_demand = annual_demand / 365
        holding_cost_per_unit = unit_cost * self.holding_cost_rate
        
        profiles_data = []
        
        for profile_name in ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]:
            result = self.generate_risk_profile_inventory_plan(
                product_name=product_name,
                risk_profile=profile_name,
                annual_demand=annual_demand,
                demand_std=demand_std,
                unit_cost=unit_cost,
                unit_price=unit_price,
                lead_time_days=lead_time_days,
                current_stock=0
            )
            
            profiles_data.append({
                'profile': profile_name,
                'service_level_target': result['inventory_policy']['service_level_target'],
                'safety_stock': result['inventory_policy']['safety_stock'],
                'annual_inventory_cost': result['cost_structure']['total_annual_inventory_cost'],
                'average_inventory_value': result['financial_impact']['average_inventory_value'],
                'estimated_lost_margin_annual': result['financial_impact']['estimated_annual_lost_margin'],
                'total_cost_including_risk': result['cost_structure']['total_annual_inventory_cost'] + result['financial_impact']['estimated_annual_lost_margin'],
                'inventory_days': result['performance_metrics']['days_of_inventory']
            })
        
        # Compare to baseline (BALANCED = 95%)
        balanced_idx = 1
        baseline_cost = profiles_data[balanced_idx]['total_cost_including_risk']
        
        for profile in profiles_data:
            profile['cost_vs_balanced'] = profile['total_cost_including_risk'] - baseline_cost
            profile['working_capital_vs_balanced'] = profile['average_inventory_value'] - profiles_data[balanced_idx]['average_inventory_value']
        
        return {
            'product_name': product_name,
            'risk_profile_comparison': {
                'description': 'Compare inventory strategy trade-offs across risk profiles',
                'scenarios': profiles_data,
                'recommendation': self._recommend_profile(profiles_data),
                'executive_summary': self._generate_executive_summary(profiles_data)
            }
        }
    
    def _recommend_profile(self, profiles_data: List[Dict]) -> str:
        """Recommend the best profile based on cost"""
        best = min(profiles_data, key=lambda x: x['total_cost_including_risk'])
        return f"Recommended: {best['profile']} (lowest total cost at ${best['total_cost_including_risk']:,.2f}/year)"
    
    def _generate_executive_summary(self, profiles_data: List[Dict]) -> str:
        """Generate plain-English summary"""
        conservative = profiles_data[0]
        balanced = profiles_data[1]
        aggressive = profiles_data[2]
        
        return (
            f"• CONSERVATIVE (99% service): Invest ${conservative['average_inventory_value']:,.0f} working capital, "
            f"cost ${conservative['total_cost_including_risk']:,.0f}/year\n"
            f"• BALANCED (95% service): Invest ${balanced['average_inventory_value']:,.0f} working capital, "
            f"cost ${balanced['total_cost_including_risk']:,.0f}/year [RECOMMENDED]\n"
            f"• AGGRESSIVE (90% service): Invest ${aggressive['average_inventory_value']:,.0f} working capital, "
            f"cost ${aggressive['total_cost_including_risk']:,.0f}/year\n"
            f"→ Moving from Conservative to Aggressive frees ${conservative['average_inventory_value'] - aggressive['average_inventory_value']:,.0f} working capital"
        )
