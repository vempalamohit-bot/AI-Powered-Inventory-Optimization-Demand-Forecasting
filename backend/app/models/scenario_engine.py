import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime

class ScenarioEngine:
    """
    What-If scenario modeling for supply chain decisions:
    - Price change simulations
    - Demand shift analysis
    - Supplier change impact
    - Lead time variation effects
    - Promotion planning
    """
    
    def __init__(self):
        pass
    
    def simulate_price_change(
        self,
        current_price: float,
        price_change_pct: float,
        price_elasticity: float = -1.2,
        current_demand: float = 100
    ) -> Dict:
        """
        Simulate impact of price change on demand and profitability
        
        Args:
            current_price: Current unit price
            price_change_pct: Price change percentage (e.g., -10 for 10% reduction)
            price_elasticity: Price elasticity of demand (typical -0.5 to -2.0)
            current_demand: Current annual demand
        
        Returns:
            Scenario analysis with revenue, volume, and margin impact
        """
        new_price = current_price * (1 + price_change_pct / 100)
        
        # Calculate demand change using price elasticity
        # % change in quantity = elasticity * % change in price
        demand_change_pct = price_elasticity * (price_change_pct / 100) * 100
        new_demand = current_demand * (1 + demand_change_pct / 100)
        
        # Volume impact
        volume_change = new_demand - current_demand
        volume_change_pct = (volume_change / current_demand * 100) if current_demand > 0 else 0
        
        # Revenue impact (assuming 40% cost of goods)
        cogs_pct = 0.40
        current_revenue = current_price * current_demand
        new_revenue = new_price * new_demand
        revenue_change = new_revenue - current_revenue
        revenue_change_pct = (revenue_change / current_revenue * 100) if current_revenue > 0 else 0
        
        # Margin impact
        current_cost = current_price * cogs_pct * current_demand
        new_cost = new_price * cogs_pct * new_demand
        current_margin = current_revenue - current_cost
        new_margin = new_revenue - new_cost
        margin_change = new_margin - current_margin
        
        # Breakeven analysis
        margin_pct_change = ((new_margin / current_margin - 1) * 100) if current_margin > 0 else 0
        
        return {
            'scenario': f'Price Change: {price_change_pct:+.1f}%',
            'current_price': round(current_price, 2),
            'new_price': round(new_price, 2),
            'price_elasticity': price_elasticity,
            'current_demand': round(current_demand, 0),
            'new_demand': round(new_demand, 0),
            'volume_change': round(volume_change, 0),
            'volume_change_pct': round(volume_change_pct, 2),
            'current_revenue': round(current_revenue, 2),
            'new_revenue': round(new_revenue, 2),
            'revenue_change': round(revenue_change, 2),
            'revenue_change_pct': round(revenue_change_pct, 2),
            'current_margin': round(current_margin, 2),
            'new_margin': round(new_margin, 2),
            'margin_change': round(margin_change, 2),
            'margin_change_pct': round(margin_pct_change, 2),
            'recommendation': self._get_price_recommendation(revenue_change_pct, margin_change)
        }
    
    def _get_price_recommendation(self, revenue_change_pct: float, margin_change: float) -> str:
        """Generate pricing recommendation"""
        if revenue_change_pct > 5 and margin_change > 0:
            return "✓ RECOMMENDED: Strong revenue and margin improvement"
        elif revenue_change_pct > 0 and margin_change > 0:
            return "✓ GOOD: Positive impact on both revenue and margin"
        elif margin_change > 0:
            return "⚠ CAUTION: Margin improves but revenue may decline"
        else:
            return "✗ NOT RECOMMENDED: Negative impact on profitability"
    
    def simulate_demand_shift(
        self,
        current_demand: float,
        demand_shift_pct: float,
        current_eoq: float,
        current_rop: float,
        safety_stock: float,
        avg_daily_demand: float        unit_cost: float = 20.0,
        ordering_cost: float = 50.0,    ) -> Dict:
        """
        Simulate impact of demand increase/decrease
        
        Args:
            current_demand: Current annual demand
            demand_shift_pct: Demand change percentage
            current_eoq: Current economic order quantity
            current_rop: Current reorder point
            safety_stock: Current safety stock level
            avg_daily_demand: Current average daily demand
        
        Returns:
            Scenario analysis with inventory impact
        """
        new_demand = current_demand * (1 + demand_shift_pct / 100)
        new_avg_daily_demand = avg_daily_demand * (1 + demand_shift_pct / 100)
        
        # Recalculate EOQ with new demand
        holding_cost_rate = 0.25
        holding_cost_per_unit = unit_cost * holding_cost_rate
        
        new_eoq = np.sqrt((2 * new_demand * ordering_cost) / holding_cost_per_unit)
        
        # Reorder point scales with demand
        new_rop = current_rop * (1 + demand_shift_pct / 100)
        
        # Safety stock scales with demand variability
        new_safety_stock = safety_stock * (1 + abs(demand_shift_pct) / 100)
        
        # Inventory optimization impact
        current_avg_inventory = (current_eoq / 2) + safety_stock
        new_avg_inventory = (new_eoq / 2) + new_safety_stock
        inventory_change = new_avg_inventory - current_avg_inventory
        
        # Cost impacts
        carrying_cost_rate = 0.25
        inventory_cost_change = inventory_change * unit_cost * carrying_cost_rate
        
        # Stockout risk
        if new_avg_daily_demand > 0:
            days_of_stock = new_avg_inventory / new_avg_daily_demand
        else:
            days_of_stock = 999
        
        return {
            'scenario': f'Demand {demand_shift_pct:+.1f}%',
            'current_demand': round(current_demand, 0),
            'new_demand': round(new_demand, 0),
            'demand_change': round(new_demand - current_demand, 0),
            'current_avg_daily_demand': round(avg_daily_demand, 2),
            'new_avg_daily_demand': round(new_avg_daily_demand, 2),
            'current_eoq': round(current_eoq, 0),
            'new_eoq': round(new_eoq, 0),
            'eoq_change': round(new_eoq - current_eoq, 0),
            'current_rop': round(current_rop, 0),
            'new_rop': round(new_rop, 0),
            'rop_change': round(new_rop - current_rop, 0),
            'current_safety_stock': round(safety_stock, 0),
            'new_safety_stock': round(new_safety_stock, 0),
            'current_avg_inventory': round(current_avg_inventory, 0),
            'new_avg_inventory': round(new_avg_inventory, 0),
            'inventory_change': round(inventory_change, 0),
            'inventory_cost_impact': round(inventory_cost_change, 2),
            'days_of_inventory': round(days_of_stock, 1),
            'stockout_risk': 'HIGH' if days_of_stock < 5 else 'MEDIUM' if days_of_stock < 15 else 'LOW',
            'recommendation': self._get_demand_recommendation(inventory_change, inventory_cost_change)
        }
    
    def _get_demand_recommendation(self, inventory_change: float, cost_change: float) -> str:
        """Generate demand scenario recommendation"""
        if inventory_change < 0 and cost_change < 0:
            return "✓ FAVORABLE: Demand increase improves inventory efficiency"
        elif inventory_change > 0 and cost_change > 100:
            return "⚠ PLAN AHEAD: Prepare for carrying cost increase"
        elif inventory_change > 0:
            return "⚠ MONITOR: Watch inventory carrying costs"
        else:
            return "→ STATUS QUO: Minimal inventory impact"
    
    def simulate_supplier_change(
        self,
        current_unit_cost: float,
        new_unit_cost: float,
        current_lead_time: int,
        new_lead_time: int,
        current_reliability: float,
        new_reliability: float,
        annual_demand: float
    ) -> Dict:
        """
        Simulate switching to alternative supplier
        
        Args:
            current_unit_cost: Current supplier unit cost
            new_unit_cost: Alternative supplier unit cost
            current_lead_time: Current lead time (days)
            new_lead_time: Alternative lead time (days)
            current_reliability: Current on-time delivery rate (0-1)
            new_reliability: Alternative reliability (0-1)
            annual_demand: Annual demand quantity
        
        Returns:
            Supplier switch impact analysis
        """
        # Cost impact
        cost_per_unit_change = new_unit_cost - current_unit_cost
        annual_cost_change = cost_per_unit_change * annual_demand
        cost_change_pct = (cost_per_unit_change / current_unit_cost * 100) if current_unit_cost > 0 else 0
        
        # Lead time impact on safety stock
        lead_time_change = new_lead_time - current_lead_time
        
        # Safety stock is proportional to sqrt(lead_time)
        # Assume demand std is 20% of mean
        demand_std = annual_demand * 0.2 / 365  # Daily std
        current_ss_multiplier = np.sqrt(current_lead_time)
        new_ss_multiplier = np.sqrt(max(1, new_lead_time))  # Ensure minimum 1 day
        
        ss_change = demand_std * (new_ss_multiplier - current_ss_multiplier) * 1.645  # Z-score for 95%
        holding_cost = 20 * 0.25  # Assumed cost
        ss_cost_impact = ss_change * holding_cost
        
        # Reliability impact (stockout risk)
        reliability_change = new_reliability - current_reliability
        
        # Total impact
        total_annual_impact = annual_cost_change + ss_cost_impact
        
        # Transition costs
        transition_cost = 5000  # Setup, testing, etc.
        payback_months = (transition_cost / abs(total_annual_impact) * 12) if total_annual_impact != 0 else 0
        
        return {
            'scenario': 'Supplier Switch Analysis',
            'current_unit_cost': round(current_unit_cost, 2),
            'new_unit_cost': round(new_unit_cost, 2),
            'cost_per_unit_change': round(cost_per_unit_change, 2),
            'annual_cost_change': round(annual_cost_change, 2),
            'cost_change_pct': round(cost_change_pct, 2),
            'current_lead_time': current_lead_time,
            'new_lead_time': new_lead_time,
            'lead_time_change': lead_time_change,
            'safety_stock_cost_impact': round(ss_cost_impact, 2),
            'current_reliability': round(current_reliability * 100, 1),
            'new_reliability': round(new_reliability * 100, 1),
            'reliability_change': round(reliability_change * 100, 1),
            'total_annual_impact': round(total_annual_impact, 2),
            'transition_cost': transition_cost,
            'payback_period_months': round(payback_months, 1) if total_annual_impact > 0 else "N/A",
            'recommendation': self._get_supplier_switch_recommendation(total_annual_impact, payback_months, reliability_change)
        }
    
    def _get_supplier_switch_recommendation(self, total_impact: float, payback: float, reliability_change: float) -> str:
        """Generate supplier switch recommendation"""
        if total_impact > 5000 and payback < 12 and reliability_change >= 0:
            return "✓ STRONGLY RECOMMENDED: Quick payback with improved reliability"
        elif total_impact > 2000 and reliability_change >= -0.05:
            return "✓ RECOMMENDED: Positive financial impact"
        elif total_impact > 0 and reliability_change >= -0.10:
            return "⚠ CONSIDER: Evaluate strategic benefits"
        elif reliability_change > 0.10:
            return "→ REVIEW: Reliability gains may justify costs"
        else:
            return "✗ NOT RECOMMENDED: Negative impact or poor payback"
    
    def create_scenario_matrix(
        self,
        base_case: Dict,
        scenarios: List[Dict]
    ) -> Dict:
        """
        Create comparison matrix of multiple scenarios
        
        Args:
            base_case: Current state metrics
            scenarios: List of scenario results
        
        Returns:
            Comparative analysis matrix
        """
        comparison = {
            'base_case': base_case,
            'scenarios': scenarios,
            'summary': {
                'best_revenue_scenario': max(scenarios, key=lambda x: x.get('new_revenue', 0))['scenario'] if scenarios else 'Base Case',
                'best_margin_scenario': max(scenarios, key=lambda x: x.get('margin_change', 0))['scenario'] if scenarios else 'Base Case',
                'best_cost_scenario': min(scenarios, key=lambda x: x.get('annual_cost_change', 0))['scenario'] if scenarios else 'Base Case',
                'recommended_scenario': self._select_best_scenario(scenarios)
            }
        }
        return comparison
    
    def _select_best_scenario(self, scenarios: List[Dict]) -> str:
        """Select best overall scenario"""
        if not scenarios:
            return 'Base Case'
        
        # Weighted scoring: 40% revenue, 40% margin, 20% cost
        for scenario in scenarios:
            score = (
                scenario.get('revenue_change_pct', 0) * 0.40 +
                scenario.get('margin_change_pct', 0) * 0.40 -
                scenario.get('annual_cost_change', 0) / 1000 * 0.20
            )
            scenario['scenario_score'] = score
        
        best = max(scenarios, key=lambda x: x['scenario_score'])
        return best['scenario']
