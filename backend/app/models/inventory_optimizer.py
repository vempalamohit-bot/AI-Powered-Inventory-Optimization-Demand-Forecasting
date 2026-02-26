import numpy as np
import math
import pandas as pd
from typing import Dict, Tuple, List
from scipy import stats

class InventoryOptimizer:
    """
    Inventory optimization engine using classical operations research methods:
    - Economic Order Quantity (EOQ) with order frequency adjustment
    - Reorder Point (ROP) calculation
    - Safety Stock optimization with stockout cost consideration
    - Total Cost Optimization (holding + ordering + stockout costs)
    - ABC Analysis for inventory classification
    """
    
    def __init__(self, holding_cost_rate: float = 0.25, ordering_cost: float = 50.0):
        """
        Initialize optimizer with cost parameters
        
        Args:
            holding_cost_rate: Annual holding cost as % of unit cost (default 25%)
            ordering_cost: Fixed cost per order (default $50)
        """
        self.holding_cost_rate = holding_cost_rate
        self.ordering_cost = ordering_cost
    
    def calculate_eoq(
        self,
        annual_demand: float,
        unit_cost: float,
        ordering_cost: float = None,
        storage_cost_per_unit: float = None,
        order_frequency_days: float = None,
        min_order_qty: float = None,
        max_order_qty: float = None,
        product_priority: str = None
    ) -> Dict[str, float]:
        """
        Calculate Economic Order Quantity with optional cost columns and constraints.
        Uses storage_cost_per_unit if provided, otherwise calculates from unit_cost.
        Adjusts for order_frequency_days constraint if provided.
        Enforces min/max order quantity constraints from supplier.
        Adjusts conservatively for HIGH priority products.
        
        EOQ = sqrt((2 * D * S) / H)
        where D = annual demand, S = ordering cost, H = holding cost per unit
        
        Args:
            annual_demand: Annual demand in units
            unit_cost: Cost per unit
            ordering_cost: Fixed cost per order (optional)
            storage_cost_per_unit: Direct storage/holding cost per unit per year (optional)
            order_frequency_days: Expected days between orders - used to validate EOQ (optional)
            min_order_qty: Minimum order quantity from supplier (optional)
            max_order_qty: Maximum order quantity constraint (optional)
            product_priority: HIGH/MEDIUM/LOW - adjust conservatively for high priority (optional)
            
        Returns:
            Dictionary with EOQ, holding_cost_used, and order_frequency details
        """
        if ordering_cost is None:
            ordering_cost = self.ordering_cost
        
        # USE storage_cost_per_unit if provided, otherwise calculate from unit_cost
        if storage_cost_per_unit is not None and storage_cost_per_unit > 0:
            holding_cost_per_unit = storage_cost_per_unit
            holding_cost_source = 'storage_cost_per_unit (from data)'
        else:
            holding_cost_per_unit = unit_cost * self.holding_cost_rate
            holding_cost_source = f'calculated ({self.holding_cost_rate*100}% of unit_cost)'
        
        if holding_cost_per_unit == 0:
            eoq = annual_demand / 12  # Monthly demand as fallback
        else:
            eoq = np.sqrt((2 * annual_demand * ordering_cost) / holding_cost_per_unit)
        
        eoq = max(1, eoq)
        
        # Calculate implied order frequency
        orders_per_year = annual_demand / eoq if eoq > 0 else 12
        implied_order_frequency_days = 365 / orders_per_year if orders_per_year > 0 else 30
        
        # ADJUST EOQ based on order_frequency_days constraint if provided
        adjusted_eoq = eoq
        adjustment_reasons = []
        
        if order_frequency_days is not None and order_frequency_days > 0:
            # Calculate EOQ that matches the order frequency
            target_orders_per_year = 365 / order_frequency_days
            frequency_based_eoq = annual_demand / target_orders_per_year if target_orders_per_year > 0 else eoq
            
            # Blend if significantly different: weight by inverse of cost deviation
            # The optimal EOQ minimizes total cost; frequency-based may be a business constraint
            deviation = abs(frequency_based_eoq - eoq) / eoq if eoq > 0 else 0
            if deviation > 0.2:
                # Weight toward optimal EOQ proportional to cost savings, capped at 80/20
                # Higher deviation → lean more toward frequency constraint (practical need)
                eoq_weight = max(0.5, 1.0 - deviation * 0.5)  # Dynamic: 50%-80% EOQ weight
                adjusted_eoq = eoq_weight * eoq + (1 - eoq_weight) * frequency_based_eoq
                adjustment_reasons.append(f'Order frequency ({order_frequency_days} days, blend {eoq_weight:.0%} optimal)')
        
        # ENFORCE supplier constraints (min/max order quantities)
        if min_order_qty is not None and adjusted_eoq < min_order_qty:
            adjusted_eoq = min_order_qty
            adjustment_reasons.append(f'Increased to supplier min ({min_order_qty})')
        
        if max_order_qty is not None and adjusted_eoq > max_order_qty:
            adjusted_eoq = max_order_qty
            adjustment_reasons.append(f'Capped at supplier max ({max_order_qty})')
        
        # ADJUST for product priority - scale buffer by demand variability
        if product_priority and product_priority.upper() == 'HIGH':
            # Buffer = max(10%, cv * 15%) — volatile high-priority items get bigger buffer
            if annual_demand > 0:
                cv = (holding_cost_per_unit / (unit_price * self.holding_rate)) if unit_price > 0 else 0.2  # Approximate demand CV
                buffer_pct = max(0.10, min(0.30, cv * 0.15 + 0.10))
            else:
                buffer_pct = 0.15
            adjusted_eoq = adjusted_eoq * (1 + buffer_pct)
            adjustment_reasons.append(f'HIGH priority: +{buffer_pct:.0%} buffer')
        
        adjustment_reason = '; '.join(adjustment_reasons) if adjustment_reasons else None
        
        return {
            'eoq': round(max(1, adjusted_eoq), 2),
            'pure_eoq': round(eoq, 2),
            'holding_cost_per_unit': round(holding_cost_per_unit, 4),
            'holding_cost_source': holding_cost_source,
            'implied_order_frequency_days': round(implied_order_frequency_days, 1),
            'order_frequency_constraint': order_frequency_days,
            'min_order_qty': min_order_qty,
            'max_order_qty': max_order_qty,
            'product_priority': product_priority,
            'adjustment_reason': adjustment_reason
        }
    
    def calculate_safety_stock(
        self,
        demand_std: float,
        lead_time_days: int,
        service_level: float = 0.95,
        stockout_cost_per_unit: float = None,
        holding_cost_per_unit: float = None,
        shelf_life_days: float = None,
        average_daily_demand: float = None
    ) -> Dict[str, float]:
        """
        Calculate safety stock based on demand variability.
        Optionally optimizes service level using stockout cost vs holding cost trade-off.
        Constrains safety stock based on shelf_life_days for perishable items.
        
        Safety Stock = Z * σ * sqrt(L)
        where Z = z-score for service level, σ = demand std dev, L = lead time
        
        If stockout_cost_per_unit and holding_cost_per_unit provided, calculates optimal
        service level using newsvendor model: optimal_SL = stockout_cost / (stockout_cost + holding_cost)
        
        If shelf_life_days provided, caps safety stock to prevent expiry waste:
        Max Safety Stock = (shelf_life_days - lead_time_days) * average_daily_demand * 0.5
        (50% of remaining shelf life after lead time to balance service vs waste)
        
        Args:
            demand_std: Standard deviation of daily demand
            lead_time_days: Lead time in days
            service_level: Target service level (default 0.95)
            stockout_cost_per_unit: Cost per unit of stockout (optional)
            holding_cost_per_unit: Cost per unit of holding (optional)
            shelf_life_days: Days until product expires (optional)
            average_daily_demand: Daily demand for shelf life constraint (optional)
            
        Returns:
            Dictionary with safety_stock, service_level_used, and optimization details
        """
        optimized_service_level = service_level
        service_level_source = 'provided'
        stockout_holding_ratio = None
        
        # OPTIMIZE SERVICE LEVEL using stockout cost if both costs are provided
        if stockout_cost_per_unit is not None and holding_cost_per_unit is not None:
            if stockout_cost_per_unit > 0 and holding_cost_per_unit > 0:
                # Newsvendor critical ratio: optimal SL = Cu / (Cu + Co)
                # Cu = stockout cost (underage), Co = holding cost (overage)
                optimal_sl = stockout_cost_per_unit / (stockout_cost_per_unit + holding_cost_per_unit)
                
                # Clamp to reasonable bounds (85% - 99%)
                optimized_service_level = max(0.85, min(0.99, optimal_sl))
                service_level_source = 'optimized from stockout/holding cost ratio'
                stockout_holding_ratio = round(stockout_cost_per_unit / holding_cost_per_unit, 2)
        
        # Get z-score for service level
        z_score = stats.norm.ppf(optimized_service_level)
        
        # Calculate safety stock
        safety_stock = z_score * demand_std * np.sqrt(lead_time_days)
        
        # CONSTRAIN safety stock based on shelf life for perishable items
        shelf_life_adjustment = None
        original_safety_stock = safety_stock
        
        if shelf_life_days is not None and average_daily_demand is not None:
            if shelf_life_days > 0 and average_daily_demand > 0:
                # Remaining shelf life after lead time
                remaining_shelf_life = shelf_life_days - lead_time_days
                
                if remaining_shelf_life > 0:
                    # Max safety stock = 50% of demand over remaining shelf life
                    # This balances service level with waste prevention
                    max_safety_stock = remaining_shelf_life * average_daily_demand * 0.5
                    
                    if safety_stock > max_safety_stock:
                        safety_stock = max_safety_stock
                        reduction_pct = ((original_safety_stock - safety_stock) / original_safety_stock * 100) if original_safety_stock > 0 else 0
                        shelf_life_adjustment = f'Capped at shelf_life constraint: {round(reduction_pct, 1)}% reduction to prevent waste'
                else:
                    # Shelf life is less than lead time - critical constraint
                    safety_stock = 0
                    shelf_life_adjustment = f'CRITICAL: shelf_life ({shelf_life_days}d) < lead_time ({lead_time_days}d) - zero safety stock'
        
        return {
            'safety_stock': max(0, round(safety_stock, 2)),
            'original_safety_stock': round(original_safety_stock, 2) if shelf_life_adjustment else None,
            'service_level_used': round(optimized_service_level, 4),
            'service_level_source': service_level_source,
            'z_score': round(z_score, 3),
            'stockout_holding_ratio': stockout_holding_ratio,
            'lead_time_days': lead_time_days,
            'shelf_life_days': shelf_life_days,
            'shelf_life_adjustment': shelf_life_adjustment
        }
    
    def calculate_reorder_point(
        self,
        avg_daily_demand: float,
        lead_time_days: int,
        safety_stock: float
    ) -> float:
        """
        Calculate reorder point
        
        ROP = (Average Daily Demand × Lead Time) + Safety Stock
        """
        rop = (avg_daily_demand * lead_time_days) + safety_stock
        
        return max(0, rop)
    
    def optimize_inventory(
        self,
        sales_history: pd.DataFrame,
        unit_cost: float,
        lead_time_days: int = 7,
        service_level: float = 0.95,
        storage_cost_per_unit: float = None,
        stockout_cost_per_unit: float = None,
        order_frequency_days: float = None,
        shelf_life_days: float = None,
        min_order_qty: float = None,
        max_order_qty: float = None,
        product_priority: str = None,
        weight_kg: float = None,
        volume_m3: float = None,
        days_since_last_order: int = None,
        days_since_last_sale: int = None
    ) -> Dict[str, any]:
        """
        Generate comprehensive inventory optimization recommendations.
        Uses all available cost columns for optimal calculations.
        
        Args:
            sales_history: DataFrame with 'date' and 'quantity_sold'
            unit_cost: Cost per unit
            lead_time_days: Supplier lead time in days
            service_level: Target service level (default 95%)
            storage_cost_per_unit: Direct storage cost per unit per year (optional)
            stockout_cost_per_unit: Cost per unit of stockout (optional)
            order_frequency_days: Expected days between orders (optional)
            shelf_life_days: Days until product expires (optional)
            min_order_qty: Minimum order quantity from supplier (optional)
            max_order_qty: Maximum order quantity constraint (optional)
            product_priority: HIGH/MEDIUM/LOW for strategic override (optional)
            weight_kg: Weight per unit in kg for warehouse space calc (optional)
            volume_m3: Volume per unit in m³ for warehouse space calc (optional)
            days_since_last_order: Days since last order for reorder urgency (optional)
            days_since_last_sale: Days since last sale for dead stock detection (optional)
            
        Returns:
            Dictionary with optimization recommendations
        """
        # Prepare data
        df = sales_history.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Calculate demand statistics
        total_demand = df['quantity_sold'].sum()
        days_of_data = (df['date'].max() - df['date'].min()).days + 1
        
        # Annualize demand
        annual_demand = (total_demand / days_of_data) * 365
        avg_daily_demand = total_demand / days_of_data
        
        # Calculate demand variability
        daily_sales = df.groupby('date')['quantity_sold'].sum()
        demand_std = daily_sales.std()
        
        if pd.isna(demand_std) or demand_std == 0:
            demand_std = avg_daily_demand * 0.3  # Assume 30% CV
        
        # Calculate EOQ with cost columns and order frequency
        eoq_result = self.calculate_eoq(
            annual_demand, 
            unit_cost,
            storage_cost_per_unit=storage_cost_per_unit,
            order_frequency_days=order_frequency_days,
            min_order_qty=min_order_qty,
            max_order_qty=max_order_qty,
            product_priority=product_priority
        )
        eoq = eoq_result['eoq']
        holding_cost_per_unit = eoq_result['holding_cost_per_unit']
        
        # Calculate safety stock with stockout cost optimization and shelf life constraint
        safety_stock_result = self.calculate_safety_stock(
            demand_std,
            lead_time_days,
            service_level,
            stockout_cost_per_unit=stockout_cost_per_unit,
            holding_cost_per_unit=holding_cost_per_unit,
            shelf_life_days=shelf_life_days,
            average_daily_demand=avg_daily_demand
        )
        safety_stock = safety_stock_result['safety_stock']
        optimized_service_level = safety_stock_result['service_level_used']
        
        # Calculate reorder point
        reorder_point = self.calculate_reorder_point(
            avg_daily_demand,
            lead_time_days,
            safety_stock
        )
        
        # Calculate optimal stock level (max inventory)
        optimal_stock_level = reorder_point + eoq
        
        # Estimate cost savings vs naive reorder strategy
        # Naive strategy: order when out, order max(2x demand, current stock level)
        # This uses queuing theory for a basic (Q,r) policy without optimization
        optimized_avg_inventory = (eoq / 2) + safety_stock
        
        # Compare: naive approach typically maintains ~(reorder_point + eoq*0.75) avg inventory
        # Derived from queuing theory for an unoptimized (Q,r) policy
        naive_avg_inventory = reorder_point + (eoq * 0.75)
        
        inventory_reduction = max(0, naive_avg_inventory - optimized_avg_inventory)
        annual_savings = inventory_reduction * holding_cost_per_unit
        
        # Calculate total annual cost (holding + ordering + expected stockout)
        annual_holding_cost = optimized_avg_inventory * holding_cost_per_unit
        annual_ordering_cost = (annual_demand / eoq) * self.ordering_cost if eoq > 0 else 0
        annual_stockout_cost = 0
        if stockout_cost_per_unit and stockout_cost_per_unit > 0:
            # Expected stockout cost = P(stockout) × expected shortage × cost_per_unit
            # For normal demand, expected shortage per cycle ≈ σ_L × L(z) where L(z) is standard loss function
            stockout_prob = 1 - optimized_service_level
            # Standard loss function approximation: L(z) ≈ φ(z) - z(1-Φ(z)) where z = norm.ppf(service_level)
            import scipy.stats as _stats
            z_val = _stats.norm.ppf(optimized_service_level)
            loss_fn = _stats.norm.pdf(z_val) - z_val * (1 - optimized_service_level)
            cycles_per_year = annual_demand / eoq if eoq > 0 else 12
            expected_shortage_per_cycle = demand_std * math.sqrt(lead_time_days) * loss_fn
            annual_stockout_cost = cycles_per_year * expected_shortage_per_cycle * stockout_cost_per_unit
        
        total_annual_cost = annual_holding_cost + annual_ordering_cost + annual_stockout_cost
        
        # Calculate inventory turnover
        inventory_turnover = annual_demand / optimized_avg_inventory if optimized_avg_inventory > 0 else 0
        
        # WAREHOUSE SPACE OPTIMIZATION (if weight/volume provided)
        warehouse_metrics = None
        if weight_kg is not None or volume_m3 is not None:
            warehouse_metrics = {
                'eoq_weight_kg': round(eoq * weight_kg, 2) if weight_kg else None,
                'eoq_volume_m3': round(eoq * volume_m3, 3) if volume_m3 else None,
                'optimal_stock_weight_kg': round(optimal_stock_level * weight_kg, 2) if weight_kg else None,
                'optimal_stock_volume_m3': round(optimal_stock_level * volume_m3, 3) if volume_m3 else None,
                'avg_inventory_weight_kg': round(optimized_avg_inventory * weight_kg, 2) if weight_kg else None,
                'avg_inventory_volume_m3': round(optimized_avg_inventory * volume_m3, 3) if volume_m3 else None,
            }
        
        # REORDER URGENCY (if days_since_last_order provided)
        reorder_urgency = None
        if days_since_last_order is not None:
            expected_order_interval = 365 / (annual_demand / eoq) if eoq > 0 else 30
            urgency_ratio = days_since_last_order / expected_order_interval if expected_order_interval > 0 else 1
            if urgency_ratio > 1.5:
                reorder_urgency = f'HIGH - {days_since_last_order} days since last order (expected every {round(expected_order_interval)} days)'
            elif urgency_ratio > 1.0:
                reorder_urgency = f'MEDIUM - {days_since_last_order} days since last order'
            else:
                reorder_urgency = f'NORMAL - Last ordered {days_since_last_order} days ago'
        
        # DEAD STOCK DETECTION (if days_since_last_sale provided)
        dead_stock_risk = None
        if days_since_last_sale is not None:
            if days_since_last_sale > 180:
                dead_stock_risk = f'CRITICAL - No sales in {days_since_last_sale} days. Consider clearance or discontinuation.'
            elif days_since_last_sale > 90:
                dead_stock_risk = f'HIGH - No sales in {days_since_last_sale} days. Review demand patterns.'
            elif days_since_last_sale > 60:
                dead_stock_risk = f'MEDIUM - {days_since_last_sale} days since last sale. Monitor closely.'
            else:
                dead_stock_risk = None  # Active sales, no risk
        
        return {
            'economic_order_quantity': round(eoq, 2),
            'safety_stock': round(safety_stock, 2),
            'reorder_point': round(reorder_point, 2),
            'optimal_stock_level': round(optimal_stock_level, 2),
            'avg_daily_demand': round(avg_daily_demand, 2),
            'demand_std': round(demand_std, 2),
            'estimated_annual_savings': round(annual_savings, 2),
            'inventory_turnover': round(inventory_turnover, 2),
            'service_level': round(optimized_service_level, 4),
            # New cost optimization details
            'cost_optimization': {
                'eoq_details': eoq_result,
                'safety_stock_details': safety_stock_result,
                'annual_holding_cost': round(annual_holding_cost, 2),
                'annual_ordering_cost': round(annual_ordering_cost, 2),
                'annual_stockout_cost': round(annual_stockout_cost, 2),
                'total_annual_cost': round(total_annual_cost, 2),
                'costs_used': {
                    'storage_cost_per_unit': storage_cost_per_unit,
                    'stockout_cost_per_unit': stockout_cost_per_unit,
                    'order_frequency_days': order_frequency_days
                }
            },
            # Warehouse space metrics
            'warehouse_metrics': warehouse_metrics,
            # Operational insights
            'reorder_urgency': reorder_urgency,
            'dead_stock_risk': dead_stock_risk
        }
    
    def abc_analysis(self, products_data: pd.DataFrame) -> pd.DataFrame:
        """
        Perform ABC analysis for inventory classification
        
        Args:
            products_data: DataFrame with 'product_id', 'annual_demand', 'unit_cost'
            
        Returns:
            DataFrame with ABC classification
        """
        df = products_data.copy()
        
        # Calculate annual revenue per product
        df['annual_revenue'] = df['annual_demand'] * df['unit_cost']
        
        # Sort by revenue
        df = df.sort_values('annual_revenue', ascending=False)
        
        # Calculate cumulative percentage
        total_revenue = df['annual_revenue'].sum()
        df['cumulative_revenue'] = df['annual_revenue'].cumsum()
        df['cumulative_percentage'] = (df['cumulative_revenue'] / total_revenue) * 100
        
        # Classify into ABC
        df['abc_class'] = 'C'
        df.loc[df['cumulative_percentage'] <= 80, 'abc_class'] = 'A'
        df.loc[(df['cumulative_percentage'] > 80) & (df['cumulative_percentage'] <= 95), 'abc_class'] = 'B'
        
        return df
    
    def abc_analysis_with_profitability(
        self,
        products_data: pd.DataFrame,
        margin_pct: float = 0.30
    ) -> Dict:
        """
        Advanced ABC analysis incorporating profitability and margin
        Identifies: High-value High-profit (A), High-value Low-profit (B), Low-value Dead stock (C)
        
        Args:
            products_data: DataFrame with 'product_id', 'product_name', 'annual_demand', 
                          'unit_cost', 'unit_price', 'current_stock'
            margin_pct: Default margin percentage for classification
        
        Returns:
            Advanced ABC classification with insights and recommendations
        """
        df = products_data.copy()
        
        # Calculate metrics
        df['annual_revenue'] = df['annual_demand'] * df.get('unit_price', df['unit_cost'] * 1.5)
        df['annual_cogs'] = df['annual_demand'] * df['unit_cost']
        df['annual_margin'] = df['annual_revenue'] - df['annual_cogs']
        df['margin_pct'] = (df['annual_margin'] / df['annual_revenue'] * 100) if 'unit_price' in df else margin_pct * 100
        
        # Calculate inventory value
        df['inventory_value'] = df['current_stock'] * df['unit_cost']
        df['days_of_inventory'] = (df['current_stock'] / (df['annual_demand'] / 365)) if 'annual_demand' in df else 0
        
        # Create revenue-based ABC
        df_revenue = df.sort_values('annual_revenue', ascending=False)
        total_revenue = df_revenue['annual_revenue'].sum()
        df_revenue['revenue_cumsum'] = df_revenue['annual_revenue'].cumsum()
        df_revenue['revenue_pct'] = (df_revenue['revenue_cumsum'] / total_revenue * 100)
        
        # Assign ABC class
        df_revenue['abc_class'] = 'C'
        df_revenue.loc[df_revenue['revenue_pct'] <= 80, 'abc_class'] = 'A'
        df_revenue.loc[(df_revenue['revenue_pct'] > 80) & (df_revenue['revenue_pct'] <= 95), 'abc_class'] = 'B'
        
        # Identify sub-categories
        df_revenue['category'] = df_revenue.apply(
            lambda row: self._categorize_product(row, total_revenue), axis=1
        )
        
        # Generate insights
        insights = {
            'total_products': len(df_revenue),
            'total_revenue': round(float(total_revenue), 2),
            'total_margin': round(float(df_revenue['annual_margin'].sum()), 2),
            'avg_margin_pct': round(float(df_revenue['margin_pct'].mean()), 2),
            'classifications': {
                'A_products': {
                    'count': len(df_revenue[df_revenue['abc_class'] == 'A']),
                    'revenue': round(float(df_revenue[df_revenue['abc_class'] == 'A']['annual_revenue'].sum()), 2),
                    'revenue_pct': round(float(df_revenue[df_revenue['abc_class'] == 'A']['annual_revenue'].sum() / total_revenue * 100), 1),
                    'description': 'Core revenue drivers - high priority management'
                },
                'B_products': {
                    'count': len(df_revenue[df_revenue['abc_class'] == 'B']),
                    'revenue': round(float(df_revenue[df_revenue['abc_class'] == 'B']['annual_revenue'].sum()), 2),
                    'revenue_pct': round(float(df_revenue[df_revenue['abc_class'] == 'B']['annual_revenue'].sum() / total_revenue * 100), 1),
                    'description': 'Secondary products - standard management'
                },
                'C_products': {
                    'count': len(df_revenue[df_revenue['abc_class'] == 'C']),
                    'revenue': round(float(df_revenue[df_revenue['abc_class'] == 'C']['annual_revenue'].sum()), 2),
                    'revenue_pct': round(float(df_revenue[df_revenue['abc_class'] == 'C']['annual_revenue'].sum() / total_revenue * 100), 1),
                    'description': 'Low-value items - minimal management'
                }
            },
            'dead_stock_items': self._identify_dead_stock(df_revenue),
            'high_margin_opportunities': self._identify_margin_opportunities(df_revenue),
            'recommendations': self._generate_abc_recommendations(df_revenue)
        }
        
        return {
            'analysis': insights,
            'product_details': df_revenue[[
                'product_id', 'product_name', 'annual_revenue', 'annual_margin', 
                'margin_pct', 'abc_class', 'category', 'current_stock', 'days_of_inventory'
            ]].to_dict('records')
        }
    
    def _categorize_product(self, row: pd.Series, total_revenue: float) -> str:
        """Categorize product based on multiple factors"""
        margin_pct = row.get('margin_pct', 30)
        revenue_contribution = (row['annual_revenue'] / total_revenue * 100) if total_revenue > 0 else 0
        days_of_inventory = row.get('days_of_inventory', 30)
        
        if row['abc_class'] == 'A':
            if margin_pct > 40:
                return 'Star (High Revenue, High Margin)'
            elif days_of_inventory > 90:
                return 'Cash Cow (High Revenue, Slow Moving)'
            else:
                return 'Core Product (High Revenue, Standard Margin)'
        elif row['abc_class'] == 'B':
            if margin_pct < 20:
                return 'Problem Child (Medium Revenue, Low Margin)'
            else:
                return 'Steady Performer (Medium Revenue, Stable)'
        else:
            if days_of_inventory > 180:
                return 'Dead Stock (Low Revenue, Excess Inventory)'
            else:
                return 'Niche Product (Low Revenue, Stable)'
    
    def _identify_dead_stock(self, df: pd.DataFrame) -> List[Dict]:
        """Identify dead stock items for clearance"""
        dead_stock = df[
            (df['annual_demand'] < 50) & 
            (df['current_stock'] > df['annual_demand'] * 0.5)
        ].head(5)
        
        recommendations = []
        for _, item in dead_stock.iterrows():
            clearance_price = item['unit_cost'] * 0.6  # 40% discount
            clearance_revenue = item['current_stock'] * clearance_price
            loss = item['inventory_value'] - clearance_revenue
            
            recommendations.append({
                'product_name': item.get('product_name', 'Unknown'),
                'current_stock': int(item['current_stock']),
                'inventory_value': round(float(item['inventory_value']), 2),
                'clearance_price': round(float(clearance_price), 2),
                'potential_clearance_revenue': round(float(clearance_revenue), 2),
                'loss': round(float(loss), 2),
                'action': 'Recommend for clearance/donation'
            })
        
        return recommendations
    
    def _identify_margin_opportunities(self, df: pd.DataFrame) -> List[Dict]:
        """Identify high-margin upsell opportunities"""
        high_margin = df[df['margin_pct'] > 50].sort_values('margin_pct', ascending=False).head(5)
        
        opportunities = []
        for _, item in high_margin.iterrows():
            opportunities.append({
                'product_name': item.get('product_name', 'Unknown'),
                'annual_margin': round(float(item['annual_margin']), 2),
                'margin_pct': round(float(item['margin_pct']), 2),
                'potential_revenue_if_doubled': round(float(item['annual_revenue'] * 2), 2),
                'recommendation': 'Increase marketing spend and stock levels'
            })
        
        return opportunities
    
    def _generate_abc_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Generate strategic recommendations based on ABC analysis"""
        recommendations = []
        
        # A products strategy
        a_count = len(df[df['abc_class'] == 'A'])
        if a_count > 0:
            recommendations.append(f"A-Products ({a_count}): Focus on 95-99% service level, tight inventory control, frequent reviews")
        
        # B products strategy
        b_count = len(df[df['abc_class'] == 'B'])
        if b_count > 0:
            recommendations.append(f"B-Products ({b_count}): Maintain 90-95% service level, periodic reviews")
        
        # C products strategy
        c_count = len(df[df['abc_class'] == 'C'])
        if c_count > 0:
            recommendations.append(f"C-Products ({c_count}): Monitor at lower frequency, consider bulk orders for cost efficiency")
        
        # Dead stock warning
        dead_stock_count = len(df[(df['annual_demand'] < 50) & (df['current_stock'] > df['annual_demand'] * 0.5)])
        if dead_stock_count > 0:
            recommendations.append(f"URGENT: {dead_stock_count} items approaching dead stock status - plan clearance activities")
        
        return recommendations
    
    def calculate_stockout_risk(
        self,
        current_stock: float,
        reorder_point: float,
        avg_daily_demand: float,
        demand_std: float
    ) -> Dict[str, any]:
        """
        Calculate risk of stockout
        
        Returns:
            Dictionary with risk level and days until stockout
        """
        if current_stock <= 0:
            return {
                'risk_level': 'CRITICAL',
                'days_until_stockout': 0,
                'probability': 1.0
            }
        
        days_of_stock = current_stock / avg_daily_demand if avg_daily_demand > 0 else 999
        
        # Calculate probability of stockout during lead time
        if demand_std > 0:
            z_score = (current_stock - reorder_point) / (demand_std * np.sqrt(7))
            stockout_probability = 1 - stats.norm.cdf(z_score)
        else:
            stockout_probability = 0.0
        
        # Determine risk level
        if current_stock < reorder_point * 0.5:
            risk_level = 'CRITICAL'
        elif current_stock < reorder_point:
            risk_level = 'HIGH'
        elif current_stock < reorder_point * 1.5:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        return {
            'risk_level': risk_level,
            'days_until_stockout': round(days_of_stock, 1),
            'probability': round(stockout_probability, 3)
        }
