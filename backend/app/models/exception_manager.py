"""
Exception Manager - Surface only what needs attention

Reduces noise by 80% by flagging:
- Top risk items (80/20 rule)
- Forecast confidence drops
- Recommendations that need manual override
- Items requiring urgent action
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime

class ExceptionManager:
    """
    Intelligent exception detection and prioritization.
    Respects manager time by surfacing only critical items.
    """
    
    def __init__(self):
        self.exception_threshold = 0.70  # Flag items below 70% confidence
        self.risk_threshold = 1000  # Flag stockout risk > $1000
    
    def get_critical_items_today(
        self,
        all_products: List[Dict],
        forecast_confidences: Dict,
        stockout_risks: Dict,
        current_stocks: Dict
    ) -> Dict:
        """
        Get TODAY's critical items (things that need immediate attention)
        
        Returns only 3-5 items max (respects manager time)
        """
        
        critical_items = []
        
        # Identify critical conditions
        for product in all_products:
            product_id = product['id']
            product_name = product['name']
            
            confidence = forecast_confidences.get(product_id, 0.80)
            stockout_risk = stockout_risks.get(product_id, 0)
            current_stock = current_stocks.get(product_id, 0)
            
            # Flag low confidence forecasts
            if confidence < self.exception_threshold:
                critical_items.append({
                    'product': product_name,
                    'product_id': product_id,
                    'issue': 'LOW_FORECAST_CONFIDENCE',
                    'severity': '🔴 HIGH',
                    'confidence': round(confidence * 100, 0),
                    'message': f"Forecast confidence dropped to {confidence*100:.0f}%. Manual review recommended.",
                    'suggested_action': 'Review recent demand signals and adjust forecast',
                    'priority': 1
                })
            
            # Flag high stockout risk
            if stockout_risk > self.risk_threshold:
                critical_items.append({
                    'product': product_name,
                    'product_id': product_id,
                    'issue': 'HIGH_STOCKOUT_RISK',
                    'severity': '🔴 HIGH',
                    'risk_amount': round(stockout_risk, 0),
                    'message': f"Stockout risk: ${stockout_risk:,.0f}. Consider ordering today.",
                    'suggested_action': 'Review decision optimizer recommendation',
                    'priority': 1
                })
            
            # Flag low stock with high demand
            if current_stock < 50 and stockout_risk > 500:
                critical_items.append({
                    'product': product_name,
                    'product_id': product_id,
                    'issue': 'CRITICAL_STOCK_LEVEL',
                    'severity': '🔴 URGENT',
                    'current_stock': current_stock,
                    'message': f"Stock at {current_stock} units with high demand coming. Order ASAP.",
                    'suggested_action': 'Execute emergency purchase order',
                    'priority': 0
                })
        
        # Sort by priority and take top 5
        critical_items.sort(key=lambda x: x['priority'])
        top_critical = critical_items[:5]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_critical_items': len(critical_items),
            'display_items': len(top_critical),
            'critical_items': top_critical,
            'summary': f"{len(top_critical)} item(s) need attention today",
            'actionable': True if top_critical else False
        }
    
    def identify_high_risk_skus(
        self,
        all_products: List[Dict],
        stockout_risks: Dict,
        variance_ratios: Dict
    ) -> Dict:
        """
        Pareto principle: Identify top 20% of products causing 80% of risk
        
        Answer: "Which products matter most?"
        """
        
        product_risks = []
        
        for product in all_products:
            product_id = product['id']
            product_name = product['name']
            
            risk = stockout_risks.get(product_id, 0)
            variance = variance_ratios.get(product_id, 0)
            
            product_risks.append({
                'product': product_name,
                'product_id': product_id,
                'stockout_risk': round(risk, 0),
                'demand_variance': round(variance * 100, 1),
                'risk_category': self._categorize_risk(risk)
            })
        
        # Sort by risk
        product_risks.sort(key=lambda x: x['stockout_risk'], reverse=True)
        
        total_risk = sum(p['stockout_risk'] for p in product_risks)
        cumulative_risk = 0
        risk_80_percent = total_risk * 0.80
        
        # Find items that make up 80% of risk
        critical_80 = []
        for item in product_risks:
            critical_80.append(item)
            cumulative_risk += item['stockout_risk']
            if cumulative_risk >= risk_80_percent:
                break
        
        return {
            'analysis_type': 'Pareto Risk Analysis (80/20)',
            'total_products': len(product_risks),
            'total_risk_amount': round(total_risk, 0),
            'high_risk_products_count': len(critical_80),
            'high_risk_percentage': round(len(critical_80) / len(product_risks) * 100, 1),
            'risk_concentration': f"{len(critical_80)} products ({round(len(critical_80)/len(product_risks)*100, 1)}%) drive 80% of risk",
            'top_20_percent_risk': [
                {
                    'rank': i+1,
                    'product': item['product'],
                    'product_id': item['product_id'],
                    'stockout_risk': item['stockout_risk'],
                    'demand_variance': item['demand_variance'],
                    'category': item['risk_category'],
                    'focus_level': '🔴 CRITICAL' if i < 3 else '🟡 HIGH'
                }
                for i, item in enumerate(critical_80)
            ],
            'insight': f"Focus on {len(critical_80)} products - they drive {round(cumulative_risk/total_risk*100, 0)}% of total stockout risk",
            'recommendation': "Dedicate 80% of planning effort to these products"
        }
    
    def flag_override_candidates(
        self,
        all_products: List[Dict],
        ai_recommendations: Dict,
        forecast_confidences: Dict,
        special_conditions: Dict = None
    ) -> Dict:
        """
        Flag items where MANUAL override might be needed
        
        Answer: "Which recommendations should I double-check?"
        """
        
        override_candidates = []
        
        for product in all_products:
            product_id = product['id']
            product_name = product['name']
            
            rec = ai_recommendations.get(product_id, {})
            confidence = forecast_confidences.get(product_id, 0.80)
            
            # Case 1: Low confidence high-value decisions
            if rec.get('decision') == 'ORDER NOW' and confidence < 0.75:
                override_candidates.append({
                    'product': product_name,
                    'product_id': product_id,
                    'reason': 'LOW_CONFIDENCE_HIGH_VALUE',
                    'description': f"High-value order ({rec.get('recommended_qty', 0):.0f} units) with only {confidence*100:.0f}% forecast confidence",
                    'ai_recommendation': rec.get('decision'),
                    'confidence_level': round(confidence * 100, 0),
                    'suggested_override': 'Consider waiting 1-2 days for better signals',
                    'severity': '🟡 MEDIUM'
                })
            
            # Case 2: Large quantity with unusual conditions
            if rec.get('recommended_qty', 0) > 1000:
                override_candidates.append({
                    'product': product_name,
                    'product_id': product_id,
                    'reason': 'LARGE_ORDER_REQUIRES_REVIEW',
                    'description': f"Large quantity order: {rec.get('recommended_qty', 0):.0f} units",
                    'ai_recommendation': f"ORDER {rec.get('recommended_qty', 0):.0f} units",
                    'cost_impact': rec.get('order_cost', 0),
                    'suggested_override': 'Verify budget and warehouse space available',
                    'severity': '🟡 MEDIUM'
                })
            
            # Case 3: Conflicting signals
            if special_conditions and product_id in special_conditions:
                condition = special_conditions[product_id]
                override_candidates.append({
                    'product': product_name,
                    'product_id': product_id,
                    'reason': 'SPECIAL_CONDITION_DETECTED',
                    'description': f"AI recommendation conflicts with: {condition.get('condition', 'unknown')}",
                    'ai_recommendation': rec.get('decision'),
                    'special_note': condition.get('note', ''),
                    'suggested_override': f"Consider {condition.get('override', 'manual review')}",
                    'severity': '🔴 HIGH'
                })
        
        # Limit to top 5
        override_candidates.sort(key=lambda x: {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}.get(x['severity'][-5], 3))
        top_overrides = override_candidates[:5]
        
        return {
            'total_override_candidates': len(override_candidates),
            'display_count': len(top_overrides),
            'override_items': top_overrides,
            'insight': f"{len(override_candidates)} recommendations flagged for manual review",
            'percentage_requiring_review': round(len(override_candidates) / len(all_products) * 100, 1),
            'actionable_message': 'Review these items before implementing recommendations'
        }
    
    def generate_daily_summary(
        self,
        critical_items: List[Dict],
        high_risk_skus: List[Dict],
        override_candidates: List[Dict]
    ) -> Dict:
        """
        One-screen dashboard summary of what needs attention TODAY
        """
        
        total_items_flagged = (len(critical_items) + len(high_risk_skus) + len(override_candidates))
        
        # Traffic light status
        if len(critical_items) > 3:
            status = "🔴 RED - Multiple urgent items"
            tone = "Action Required"
        elif len(critical_items) > 0:
            status = "🟡 YELLOW - Some attention needed"
            tone = "Review Recommended"
        else:
            status = "🟢 GREEN - Normal operations"
            tone = "Monitor & Continue"
        
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'overall_status': status,
            'tone': tone,
            'summary': {
                'critical_items': len(critical_items),
                'high_risk_skus': min(len(high_risk_skus), 5),
                'manual_reviews_needed': len(override_candidates),
                'total_items_flagged': total_items_flagged
            },
            'action_items': [
                {
                    'priority': 1,
                    'action': f"Review {len(critical_items)} critical items",
                    'time_estimate': '5-10 min'
                },
                {
                    'priority': 2,
                    'action': f"Focus planning on top {min(len(high_risk_skus), 5)} high-risk products",
                    'time_estimate': '15-20 min'
                },
                {
                    'priority': 3,
                    'action': f"Manual review {len(override_candidates)} items before ordering",
                    'time_estimate': '10-15 min'
                }
            ],
            'estimated_total_time': '30-45 min',
            'next_review': 'Tomorrow, 9 AM',
            'message': 'Exceptions identified. Review action items above.'
        }
    
    def _categorize_risk(self, risk_amount: float) -> str:
        """Categorize risk level"""
        if risk_amount > 10000:
            return '🔴 CRITICAL'
        elif risk_amount > 5000:
            return '🟡 HIGH'
        elif risk_amount > 1000:
            return '🟠 MEDIUM'
        else:
            return '🟢 LOW'
