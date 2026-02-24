import pandas as pd
from typing import Dict, List
from datetime import datetime

class FinancialStoryTeller:
    """
    FINANCIAL STORYTELLING ENGINE
    
    Core Insight: "Executives don't buy ML. They buy margin improvement."
    
    This module translates every AI recommendation into business language:
    - Revenue at risk
    - Cash tied up
    - Margin impact
    - Payback period
    
    Philosophy: The best recommendation is worthless if you can't explain it in dollars.
    
    Output: Every decision comes with a "here's how much money this makes/saves" story.
    """
    
    def __init__(self):
        pass
    
    def tell_decision_story(
        self,
        product_name: str,
        current_situation: Dict,
        ai_recommendation: Dict,
        company_cogs_pct: float = 0.40,
        cost_of_capital_pct: float = 0.08  # 8% annual cost of working capital
    ) -> Dict:
        """
        Convert an AI recommendation into a compelling financial story for decision-makers.
        
        Format: "If you act on this AI recommendation, here's what happens to your money:"
        
        Args:
            product_name: Product name
            current_situation: {current_stock, annual_demand, unit_cost, unit_price, historical_stockout_pct}
            ai_recommendation: {recommended_order_qty, service_level, safety_stock}
            company_cogs_pct: Your typical COGS %
            cost_of_capital_pct: What does working capital cost you?
        
        Returns:
            Complete financial story with multiple impact dimensions
        """
        
        current_stock = current_situation['current_stock']
        annual_demand = current_situation['annual_demand']
        unit_cost = current_situation['unit_cost']
        unit_price = current_situation['unit_price']
        historical_stockout_pct = current_situation.get('historical_stockout_pct', 0.02)
        
        recommended_order_qty = ai_recommendation['recommended_order_qty']
        new_service_level = ai_recommendation['service_level']
        safety_stock = ai_recommendation['safety_stock']
        
        unit_margin = unit_price - unit_cost
        daily_demand = annual_demand / 365
        
        # ===== FINANCIAL IMPACT STORY =====
        
        # 1. REVENUE AT RISK (Current Situation)
        current_stockout_probability = historical_stockout_pct / 100
        annual_revenue_at_risk_current = (annual_demand * current_stockout_probability * 0.01) * unit_price
        annual_margin_at_risk_current = annual_revenue_at_risk_current * (1 - company_cogs_pct)
        
        # 2. REVENUE AT RISK (After Recommendation)
        new_stockout_probability = 1 - new_service_level
        annual_revenue_at_risk_new = (annual_demand * new_stockout_probability * 0.01) * unit_price
        annual_margin_at_risk_new = annual_revenue_at_risk_new * (1 - company_cogs_pct)
        
        # 3. WORKING CAPITAL IMPACT
        current_wc = current_stock * unit_cost
        new_wc = (current_stock + recommended_order_qty) * unit_cost
        wc_increase = new_wc - current_wc
        annual_cost_of_wc = wc_increase * cost_of_capital_pct
        
        # 4. HOLDING/CARRYING COSTS
        average_inventory = (current_stock + recommended_order_qty + current_stock) / 2
        annual_holding_cost_rate = 0.25  # 25% standard
        annual_carrying_cost = average_inventory * unit_cost * annual_holding_cost_rate
        
        # 5. NET FINANCIAL IMPACT
        margin_improvement = annual_margin_at_risk_current - annual_margin_at_risk_new
        total_cost_of_action = annual_cost_of_wc + annual_carrying_cost
        net_annual_benefit = margin_improvement - total_cost_of_action
        
        # 6. PAYBACK CALCULATION
        payback_days = (wc_increase / max(1, net_annual_benefit)) * 365 if net_annual_benefit > 0 else 999
        
        # ===== CREATE THE STORY =====
        
        return {
            'product_name': product_name,
            'executive_summary': {
                'headline': self._create_headline(net_annual_benefit, payback_days),
                'cfo_summary': f"Implementing AI recommendation saves ${net_annual_benefit:,.0f} annually with {payback_days:.0f}-day payback",
                'timestamp': datetime.now().isoformat()
            },
            'revenue_at_risk_story': {
                'title': '💰 REVENUE PROTECTION',
                'current_state': {
                    'annual_revenue_exposed': round(annual_revenue_at_risk_current, 2),
                    'annual_margin_exposed': round(annual_margin_at_risk_current, 2),
                    'narrative': f"Currently, {historical_stockout_pct:.1f}% historical stockout rate exposes ${annual_margin_at_risk_current:,.0f} in margin annually"
                },
                'after_ai_recommendation': {
                    'annual_revenue_exposed': round(annual_revenue_at_risk_new, 2),
                    'annual_margin_exposed': round(annual_margin_at_risk_new, 2),
                    'service_level_improvement': f"{(1-historical_stockout_pct/100)*100:.1f}% → {new_service_level*100:.1f}%",
                    'narrative': f"AI recommendation reduces stockout risk to {new_stockout_probability*100:.1f}%, protecting ${annual_margin_at_risk_current - annual_margin_at_risk_new:,.0f} margin"
                },
                'margin_saved': round(margin_improvement, 2)
            },
            'working_capital_story': {
                'title': '💳 WORKING CAPITAL IMPACT',
                'current_investment': round(current_wc, 2),
                'proposed_investment': round(new_wc, 2),
                'additional_cash_required': round(wc_increase, 2),
                'cost_of_capital_annually': round(annual_cost_of_wc, 2),
                'narrative': f"Ordering {recommended_order_qty:.0f} units requires ${wc_increase:,.0f} additional working capital, costing ${annual_cost_of_wc:,.0f}/year at {cost_of_capital_pct*100:.1f}% cost of capital"
            },
            'inventory_carrying_story': {
                'title': '📦 HOLDING & CARRYING COSTS',
                'average_inventory_units': round(average_inventory, 0),
                'annual_carrying_cost': round(annual_carrying_cost, 2),
                'narrative': f"Carrying {average_inventory:.0f} units costs ~${annual_carrying_cost:,.0f}/year (25% of unit cost)"
            },
            'net_financial_impact': {
                'title': '💵 NET IMPACT (THE BOTTOM LINE)',
                'margin_improvement_from_risk_reduction': round(margin_improvement, 2),
                'less_working_capital_cost': round(annual_cost_of_wc, 2),
                'less_carrying_costs': round(annual_carrying_cost, 2),
                'net_annual_benefit': round(net_annual_benefit, 2),
                'net_annual_benefit_per_unit': round(net_annual_benefit / max(1, annual_demand), 4),
                'three_year_impact': round(net_annual_benefit * 3, 2),
                'cfo_decision': self._create_cfo_recommendation(net_annual_benefit, payback_days),
                'roi_percent': round((net_annual_benefit / max(1, wc_increase)) * 100, 1) if wc_increase > 0 else 0
            },
            'financial_dashboard': {
                'metrics': [
                    {'label': 'Revenue At Risk (Currently)', 'value': f"${annual_revenue_at_risk_current:,.0f}", 'metric_type': 'revenue'},
                    {'label': 'Margin At Risk (Currently)', 'value': f"${annual_margin_at_risk_current:,.0f}", 'metric_type': 'margin'},
                    {'label': 'Margin Saved by AI', 'value': f"${margin_improvement:,.0f}", 'metric_type': 'savings'},
                    {'label': 'Working Capital Required', 'value': f"${wc_increase:,.0f}", 'metric_type': 'cash'},
                    {'label': 'Annual Carrying Cost', 'value': f"${annual_carrying_cost:,.0f}", 'metric_type': 'cost'},
                    {'label': 'Net Annual Benefit', 'value': f"${net_annual_benefit:,.0f}", 'metric_type': 'benefit'}
                ]
            }
        }
    
    def _create_headline(self, benefit: float, payback_days: float) -> str:
        """Create attention-grabbing headline"""
        if benefit > 100000:
            return f"🎯 This AI recommendation saves ${benefit:,.0f} annually (payback in {payback_days:.0f} days)"
        elif benefit > 10000:
            return f"✅ This recommendation generates ${benefit:,.0f} annual value"
        else:
            return f"→ This recommendation provides marginal benefit of ${benefit:,.0f}"
    
    def _create_cfo_recommendation(self, benefit: float, payback_days: float) -> str:
        """Create CFO-language recommendation"""
        if benefit < 0:
            return "❌ NOT RECOMMENDED: Negative financial impact"
        elif payback_days > 365:
            return "⚠️  REVIEW: Long payback period, check for strategic factors"
        elif payback_days > 180:
            return "✓ APPROVE: 6-month payback acceptable"
        elif payback_days > 90:
            return "✓✓ RECOMMEND: Strong ROI (3-6 month payback)"
        else:
            return "✓✓✓ HIGH PRIORITY: Exceptional ROI (payback <90 days)"
    
    def portfolio_impact_story(
        self,
        portfolio_recommendations: List[Dict],
        total_annual_revenue: float
    ) -> Dict:
        """
        Aggregate financial story across entire product portfolio.
        
        "Across your portfolio, implementing these AI recommendations will:"
        """
        
        total_margin_saved = sum(r.get('margin_saved', 0) for r in portfolio_recommendations)
        total_wc_required = sum(r.get('wc_required', 0) for r in portfolio_recommendations)
        total_carrying_cost = sum(r.get('carrying_cost', 0) for r in portfolio_recommendations)
        net_portfolio_benefit = total_margin_saved - total_wc_required - total_carrying_cost
        
        top_opportunities = sorted(
            portfolio_recommendations,
            key=lambda x: x.get('margin_saved', 0),
            reverse=True
        )[:5]
        
        return {
            'portfolio_impact': {
                'total_products': len(portfolio_recommendations),
                'total_annual_margin_saved': round(total_margin_saved, 2),
                'total_working_capital_required': round(total_wc_required, 2),
                'total_carrying_costs': round(total_carrying_cost, 2),
                'net_annual_portfolio_benefit': round(net_portfolio_benefit, 2),
                'portfolio_benefit_as_pct_revenue': round((net_portfolio_benefit / total_annual_revenue) * 100, 2)
            },
            'portfolio_narrative': f"""
PORTFOLIO FINANCIAL IMPACT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Total margin protected: ${total_margin_saved:,.0f}
✓ Working capital required: ${total_wc_required:,.0f}
✓ Total carrying costs: ${total_carrying_cost:,.0f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ NET ANNUAL BENEFIT: ${net_portfolio_benefit:,.0f}
→ As % of revenue: {(net_portfolio_benefit / total_annual_revenue) * 100:.2f}%

Top 5 Opportunities:
{self._format_top_opportunities(top_opportunities)}
            """.strip(),
            'top_opportunities': top_opportunities
        }
    
    def _format_top_opportunities(self, opportunities: List[Dict]) -> str:
        """Format top opportunities for readable output"""
        lines = []
        for i, opp in enumerate(opportunities, 1):
            lines.append(f"{i}. {opp.get('product_name', 'Unknown')}: ${opp.get('margin_saved', 0):,.0f}")
        return "\n".join(lines)
    
    def create_financial_justification_memo(
        self,
        recommendation_id: str,
        product_name: str,
        financial_story: Dict,
        decision_owner: str = "Inventory Manager",
        approval_required: bool = True
    ) -> str:
        """
        Generate a formal financial justification memo suitable for executive email.
        """
        
        story = financial_story
        
        memo = f"""
MEMORANDUM

TO: Finance & Operations Leadership
FROM: AI Inventory Optimization System
DATE: {datetime.now().strftime('%B %d, %Y')}
RE: Financial Justification for {product_name} Inventory Recommendation

EXECUTIVE SUMMARY
{'='*70}
This AI-driven recommendation will improve {product_name} profitability by
${story['net_financial_impact']['net_annual_benefit']:,.2f} annually.

KEY METRICS
{'='*70}
• Revenue at Risk (current approach): ${story['revenue_at_risk_story']['current_state']['annual_margin_exposed']:,.2f}
• Revenue Protection (AI approach):  ${story['revenue_at_risk_story']['after_ai_recommendation']['annual_margin_exposed']:,.2f}
• Margin Improvement:                 ${story['revenue_at_risk_story']['margin_saved']:,.2f}
• Working Capital Required:          ${story['working_capital_story']['additional_cash_required']:,.2f}
• Annual Carrying Costs:             ${story['inventory_carrying_story']['annual_carrying_cost']:,.2f}
────────────────────────────────────────────────
• NET ANNUAL BENEFIT:                ${story['net_financial_impact']['net_annual_benefit']:,.2f}

FINANCIAL JUSTIFICATION
{'='*70}
1. REVENUE PROTECTION
   {story['revenue_at_risk_story']['current_state']['narrative']}
   {story['revenue_at_risk_story']['after_ai_recommendation']['narrative']}

2. WORKING CAPITAL IMPACT
   {story['working_capital_story']['narrative']}

3. CARRYING COSTS
   {story['inventory_carrying_story']['narrative']}

RECOMMENDATION
{'='*70}
{story['net_financial_impact']['cfo_decision']}

ROI: {story['net_financial_impact']['roi_percent']:.0f}%
3-Year Impact: ${story['net_financial_impact']['three_year_impact']:,.2f}

Prepared by: AI Inventory Optimization Engine
Recommendation ID: {recommendation_id}
"""
        
        return memo
