import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime

class DecisionOptimizer:
    """
    DECISION-CENTRIC AI ENGINE
    
    Converts forecasts & optimization parameters into PRESCRIPTIONS with financial outcomes.
    
    Philosophy: Don't just predict demand. Decide what to order, balancing:
    - Cost of holding inventory
    - Cost of stockouts (lost revenue)
    - Working capital impact
    - Service level commitments
    
    Output: "If we order 150 units today, we have 98% service level and save $2,400 vs current strategy"
    """
    
    def __init__(self):
        self.holding_cost_rate = 0.25  # 25% annual holding cost
        self.ordering_cost = 50  # Fixed cost per order
        
    def generate_decision_recommendation(
        self,
        product_name: str,
        current_stock: float,
        predicted_demand: float,
        demand_std: float,
        unit_cost: float,
        unit_price: float,
        lead_time_days: int,
        annual_demand: float,
        target_service_level: float = 0.95,
        cost_of_stockout_pct: float = 0.40  # 40% of margin lost per stockout
    ) -> Dict:
        """
        Generate a prescriptive recommendation with financial justification.
        
        Args:
            product_name: Product identifier
            current_stock: Current inventory level
            predicted_demand: Forecasted demand for next period
            demand_std: Demand standard deviation
            unit_cost: Cost per unit
            unit_price: Selling price per unit
            lead_time_days: Supplier lead time
            annual_demand: Annual demand
            target_service_level: Desired service level (0.90-0.99)
            cost_of_stockout_pct: % of margin lost per unit stocked out
        
        Returns:
            Prescriptive decision with financial impact analysis
        """
        
        # Calculate key metrics
        unit_margin = unit_price - unit_cost
        annual_margin_dollars = unit_margin * annual_demand
        daily_demand = annual_demand / 365
        
        # Calculate optimal order quantity
        holding_cost_per_unit = unit_cost * self.holding_cost_rate
        if holding_cost_per_unit > 0:
            eoq = np.sqrt((2 * annual_demand * self.ordering_cost) / holding_cost_per_unit)
        else:
            eoq = annual_demand / 12
        
        # Calculate safety stock for target service level
        from scipy import stats
        z_score = stats.norm.ppf(target_service_level)
        safety_stock = z_score * demand_std * np.sqrt(lead_time_days)
        
        # Calculate reorder point
        reorder_point = (daily_demand * lead_time_days) + safety_stock
        
        # DECISION LOGIC: Should we order now?
        order_quantity = max(0, reorder_point - current_stock)
        if order_quantity < eoq * 0.5:
            order_quantity = 0  # Don't bother with small orders
        else:
            order_quantity = max(eoq, order_quantity)
        
        # Calculate financial outcomes for THIS decision vs alternatives
        
        # Scenario 1: Order what we recommend
        if order_quantity > 0:
            scenario_order_cost = (order_quantity / 2) * holding_cost_per_unit + self.ordering_cost
            scenario_inventory = current_stock + order_quantity
            scenario_stockout_probability = 0.0  # Assume we ordered enough
            scenario_cost = scenario_order_cost
        else:
            scenario_inventory = current_stock
            scenario_order_cost = 0
            # Estimate stockout probability if we don't order
            z_current = (current_stock - reorder_point) / (demand_std * np.sqrt(lead_time_days)) if demand_std > 0 else 0
            scenario_stockout_probability = 1 - stats.norm.cdf(z_current) if demand_std > 0 else 0
            scenario_cost = 0
        
        # Expected stockout cost
        expected_stockout_impact = scenario_stockout_probability * (predicted_demand * unit_margin * cost_of_stockout_pct)
        total_cost_to_order = scenario_cost
        total_cost_to_wait = expected_stockout_impact
        
        # Decision outcome
        if total_cost_to_wait > total_cost_to_order:
            decision = "ORDER NOW"
            financial_justification = f"Expected stockout cost (${total_cost_to_wait:,.2f}) exceeds holding cost (${total_cost_to_order:,.2f})"
            savings = total_cost_to_wait - total_cost_to_order
            roi = (savings / (total_cost_to_order + 1)) * 100  # Avoid division by zero
        else:
            decision = "WAIT/MONITOR"
            financial_justification = f"Holding cost (${total_cost_to_order:,.2f}) exceeds expected stockout risk (${total_cost_to_wait:,.2f})"
            savings = 0
            roi = 0
        
        # Calculate working capital impact
        working_capital_tied = (current_stock + order_quantity) * unit_cost if order_quantity > 0 else current_stock * unit_cost
        working_capital_current = current_stock * unit_cost
        wc_impact = working_capital_tied - working_capital_current
        
        # Service level achievement
        current_service_level = 1 - scenario_stockout_probability if order_quantity == 0 else target_service_level
        
        return {
            'product_name': product_name,
            'decision': {
                'recommendation': decision,
                'order_quantity': round(order_quantity, 0) if decision == "ORDER NOW" else 0,
                'target_service_level': round(target_service_level * 100, 1),
                'projected_service_level': round(current_service_level * 100, 1),
                'reorder_point': round(reorder_point, 1),
                'safety_stock': round(safety_stock, 1),
            },
            'financial_justification': {
                'rationale': financial_justification,
                'cost_to_order': round(total_cost_to_order, 2),
                'cost_of_stockout_risk': round(total_cost_to_wait, 2),
                'net_savings': round(savings, 2),
                'roi_percent': round(roi, 1)
            },
            'working_capital_impact': {
                'current_inventory_value': round(working_capital_current, 2),
                'projected_inventory_value': round(working_capital_tied, 2),
                'cash_impact': round(wc_impact, 2),
                'impact_direction': 'cash_out' if wc_impact > 0 else 'neutral'
            },
            'risk_metrics': {
                'stockout_probability_if_wait': round(scenario_stockout_probability * 100, 2),
                'expected_lost_margin_if_stockout': round(expected_stockout_impact, 2),
                'days_of_stock_current': round(current_stock / daily_demand, 1) if daily_demand > 0 else 999,
                'days_of_stock_after_order': round((current_stock + order_quantity) / daily_demand, 1) if daily_demand > 0 else 999
            },
            'approval_trigger': self._get_approval_trigger(decision, savings, wc_impact)
        }
    
    def _get_approval_trigger(self, decision: str, savings: float, wc_impact: float) -> Dict:
        """Determine approval level needed"""
        if decision == "WAIT/MONITOR":
            return {
                'approval_level': 'NONE',
                'requires_review': False,
                'next_check_days': 3
            }
        elif savings > 5000:
            return {
                'approval_level': 'AUTO_APPROVED',
                'requires_review': False,
                'reason': f'High savings (${savings:,.2f}) justifies order'
            }
        elif wc_impact > 50000:
            return {
                'approval_level': 'FINANCE_REVIEW',
                'requires_review': True,
                'reason': f'Large working capital impact (${wc_impact:,.2f})'
            }
        else:
            return {
                'approval_level': 'MANAGER_REVIEW',
                'requires_review': True,
                'reason': 'Standard approval workflow'
            }
    
    def compare_service_level_trade_offs(
        self,
        product_name: str,
        current_stock: float,
        predicted_demand: float,
        demand_std: float,
        unit_cost: float,
        unit_price: float,
        lead_time_days: int,
        annual_demand: float
    ) -> Dict:
        """
        Show decision-maker the cost of each service level choice.
        
        "If we accept 90% vs 95% service level, we save $X and free up $Y working capital"
        
        This is THE decision-making tool for inventory trade-offs.
        """
        
        from scipy import stats
        
        unit_margin = unit_price - unit_cost
        daily_demand = annual_demand / 365
        holding_cost_per_unit = unit_cost * self.holding_cost_rate
        
        # Service levels to compare
        service_levels = [0.85, 0.90, 0.95, 0.99]
        
        scenarios = []
        
        for service_level in service_levels:
            z_score = stats.norm.ppf(service_level)
            safety_stock = z_score * demand_std * np.sqrt(lead_time_days)
            reorder_point = (daily_demand * lead_time_days) + safety_stock
            
            # Calculate costs
            holding_cost = (safety_stock / 2) * holding_cost_per_unit  # Annual cost
            monthly_holding_cost = holding_cost / 12
            
            # Stockout probability (inverse of service level)
            stockout_probability = 1 - service_level
            
            # Expected lost margin per year
            expected_stockout_units = annual_demand * stockout_probability * 0.01  # Assume 1% of demand at risk
            expected_lost_margin = expected_stockout_units * unit_margin
            
            # Working capital
            wc = (current_stock + safety_stock) * unit_cost
            
            scenarios.append({
                'service_level_target': round(service_level * 100, 0),
                'service_level_pct': round(service_level * 100, 1),
                'safety_stock_units': round(safety_stock, 0),
                'monthly_holding_cost': round(monthly_holding_cost, 2),
                'annual_holding_cost': round(holding_cost, 2),
                'stockout_probability_pct': round(stockout_probability * 100, 2),
                'expected_annual_lost_margin': round(expected_lost_margin, 2),
                'total_annual_cost': round(holding_cost + expected_lost_margin, 2),
                'working_capital_required': round(wc, 2),
                'recommendation': self._get_sl_recommendation(service_level, holding_cost, expected_lost_margin)
            })
        
        # Find optimal (minimum total cost)
        best_scenario = min(scenarios, key=lambda x: x['total_annual_cost'])
        
        return {
            'product_name': product_name,
            'trade_off_analysis': {
                'description': 'Service level vs cost analysis - choose your risk tolerance',
                'scenarios': scenarios,
                'optimal_scenario': best_scenario,
                'cost_range': {
                    'minimum_annual_cost': min(s['total_annual_cost'] for s in scenarios),
                    'maximum_annual_cost': max(s['total_annual_cost'] for s in scenarios),
                    'cost_range': max(s['total_annual_cost'] for s in scenarios) - min(s['total_annual_cost'] for s in scenarios)
                }
            },
            'business_context': {
                'if_95_percent': f"Accepting 5% stockout risk costs ${scenarios[2]['annual_holding_cost']:,.2f} holding + ${scenarios[2]['expected_annual_lost_margin']:,.2f} expected lost margin",
                'if_90_percent': f"Accepting 10% stockout risk saves ${scenarios[1]['annual_holding_cost']:,.2f} vs 95%",
                'if_99_percent': f"Achieving 99% costs additional ${scenarios[3]['annual_holding_cost'] - scenarios[2]['annual_holding_cost']:,.2f} annually",
            }
        }
    
    def _get_sl_recommendation(self, service_level: float, holding_cost: float, lost_margin: float) -> str:
        """Recommend service level based on product characteristics"""
        if service_level == 0.85:
            return "Conservative - for slow movers, seasonal, or obsolete risk"
        elif service_level == 0.90:
            return "Balanced - for standard products with moderate demand"
        elif service_level == 0.95:
            return "Recommended - balances cost and customer satisfaction"
        elif service_level == 0.99:
            return "Premium - for critical items, high-margin products, or strategic SKUs"
        
        return "Standard"
    
    def quantify_decision_impact(
        self,
        product_name: str,
        historical_stockouts: int,
        historical_holding_waste: float,
        proposed_order_qty: float,
        unit_cost: float,
        unit_price: float,
        proposed_service_level: float = 0.95
    ) -> Dict:
        """
        Quantify business impact of AI-recommended decision vs historical behavior.
        
        "Your current approach: 12 stockouts/year costing $45K in lost margin
         AI recommendation: 1 stockout/year costing $4K, saves net $41K annually"
        """
        
        unit_margin = unit_price - unit_cost
        
        # Historical costs
        historical_stockout_cost = historical_stockouts * unit_margin * 100  # Assume 100 units per stockout
        historical_holding_cost = historical_holding_waste  # Waste from over-ordering
        total_historical_cost = historical_stockout_cost + historical_holding_cost
        
        # Projected costs with AI decision
        estimated_stockouts = max(0, int(historical_stockouts * (1 - proposed_service_level)))
        projected_stockout_cost = estimated_stockouts * unit_margin * 100
        projected_holding_cost = (proposed_order_qty / 2) * unit_cost * 0.25 / 12  # Monthly
        total_projected_cost = projected_stockout_cost + projected_holding_cost
        
        # Savings
        annual_savings = total_historical_cost - total_projected_cost
        savings_pct = (annual_savings / (total_historical_cost + 1)) * 100
        
        return {
            'product_name': product_name,
            'business_impact': {
                'metric': 'Annual Cost Reduction',
                'current_state': {
                    'stockout_events': historical_stockouts,
                    'stockout_cost': round(historical_stockout_cost, 2),
                    'holding_waste': round(historical_holding_cost, 2),
                    'total_annual_cost': round(total_historical_cost, 2)
                },
                'proposed_state': {
                    'stockout_events': estimated_stockouts,
                    'projected_stockout_cost': round(projected_stockout_cost, 2),
                    'projected_holding_cost': round(projected_holding_cost, 2),
                    'total_projected_cost': round(total_projected_cost, 2)
                },
                'improvement': {
                    'annual_savings': round(annual_savings, 2),
                    'savings_percentage': round(savings_pct, 1),
                    'stockout_reduction': historical_stockouts - estimated_stockouts
                }
            },
            'roi_calculation': {
                'implementation_effort': 'Low (2-4 hours)',
                'annual_benefit': round(annual_savings, 2),
                'payback_period_days': round(14 if annual_savings > 0 else 0, 0),  # Assume 2 weeks effort
                'three_year_impact': round(annual_savings * 3, 2)
            }
        }
