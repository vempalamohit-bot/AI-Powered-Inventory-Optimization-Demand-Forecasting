"""
Product Segmentation Engine
Automatically segments products into Stable, Seasonal, Volatile, and Intermittent categories
Based on historical demand patterns for intelligent model selection
"""

import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.tsa.seasonal import seasonal_decompose
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')


class ProductSegmenter:
    """
    Segments products based on demand characteristics:
    - STABLE: Low coefficient of variation, predictable demand
    - SEASONAL: Strong periodic patterns (weekly/monthly/yearly)
    - VOLATILE: High variance, unpredictable spikes
    - INTERMITTENT: Many zero-sales days, sparse demand
    """
    
    def __init__(self):
        self.segment_thresholds = {
            'cv_stable': 0.4,  # CV < 0.4 = stable
            'cv_volatile': 0.6,  # CV > 0.6 = volatile
            'zero_intermittent': 0.25,  # >25% zeros = intermittent
            'seasonality_strong': 0.3  # Seasonality strength > 0.3 = seasonal
        }
    
    def segment_product(self, sales_data: pd.DataFrame) -> Dict:
        """
        Analyze a single product's sales history and assign segment
        
        Args:
            sales_data: DataFrame with 'date' and 'quantity_sold' columns
            
        Returns:
            Dictionary with segment info and characteristics
        """
        if len(sales_data) < 14:
            return {
                'segment': 'INSUFFICIENT_DATA',
                'recommended_model': 'simple_average',
                'confidence': 'low',
                'characteristics': {'data_points': len(sales_data)}
            }
        
        # Calculate key characteristics
        quantities = sales_data['quantity_sold'].values
        mean_demand = np.mean(quantities)
        std_demand = np.std(quantities)
        
        # 1. Coefficient of Variation (CV)
        cv = std_demand / mean_demand if mean_demand > 0 else 999
        
        # 2. Zero-sales percentage
        zero_pct = (quantities == 0).sum() / len(quantities)
        
        # 3. Seasonality detection
        seasonality_info = self.detect_seasonality(sales_data)
        seasonality_strength = seasonality_info['strength']
        
        # 4. Trend detection
        trend_info = self.detect_trend(sales_data)
        
        # Decision logic for segmentation
        segment, model, confidence = self._assign_segment(
            cv=cv,
           zero_pct=zero_pct,
            seasonality_strength=seasonality_strength,
            trend_slope=trend_info['slope']
        )
        
        return {
            'segment': segment,
            'recommended_model': model,
            'confidence': confidence,
            'characteristics': {
                'mean_demand': round(mean_demand, 2),
                'std_demand': round(std_demand, 2),
                'coefficient_of_variation': round(cv, 3),
                'zero_sales_pct': round(zero_pct * 100, 1),
                'seasonality_strength': round(seasonality_strength, 3),
                'seasonality_period': seasonality_info['period'],
                'trend_direction': trend_info['direction'],
                'trend_strength': round(abs(trend_info['slope']), 3) if trend_info['slope'] else 0,
                'data_points': len(sales_data)
            }
        }
    
    def _assign_segment(self, cv: float, zero_pct: float, seasonality_strength: float, trend_slope: float) -> Tuple[str, str, str]:
        """
        Assign segment and recommended model based on characteristics
        
        Returns:
            (segment_name, recommended_model, confidence_level)
        """
        # Priority 1: Intermittent demand (many zeros)
        if zero_pct > self.segment_thresholds['zero_intermittent']:
            return 'INTERMITTENT', 'croston', 'high'
        
        # Priority 2: Strong seasonality
        if seasonality_strength > self.segment_thresholds['seasonality_strong']:
            if cv < self.segment_thresholds['cv_stable']:
                return 'SEASONAL_STABLE', 'sarima', 'high'
            else:
                return 'SEASONAL_VOLATILE', 'prophet', 'medium'
        
        # Priority 3: Volatility check
        if cv > self.segment_thresholds['cv_volatile']:
            return 'VOLATILE', 'xgboost', 'medium'
        
        # Priority 4: Stable demand
        if cv < self.segment_thresholds['cv_stable']:
            if abs(trend_slope) if trend_slope else 0 > 0.05:
                return 'STABLE_TRENDING', 'prophet', 'high'
            else:
                return 'STABLE_FLAT', 'exponential_smoothing', 'high'
        
        # Default: Moderate behavior
        return 'MODERATE', 'arima', 'medium'
    
    def detect_seasonality(self, sales_data: pd.DataFrame) -> Dict:
        """
        Detect seasonality strength and optimal period
        
        Returns:
            Dictionary with strength (0-1) and period (days)
        """
        if len(sales_data) < 14:
            return {'strength': 0.0, 'period': None}
        
        quantities = sales_data['quantity_sold'].values
        
        # Test common seasonal periods
        periods_to_test = [7, 14, 30, 90]  # Weekly, bi-weekly, monthly, quarterly
        best_strength = 0.0
        best_period = None
        
        for period in periods_to_test:
            if len(quantities) < period * 2:
                continue
            
            try:
                # Use seasonal decompose to extract seasonal component
                decomposition = seasonal_decompose(
                    quantities,
                    model='additive',
                    period=period,
                    extrapolate_trend='freq'
                )
                
                # Calculate seasonality strength
                seasonal_var = np.var(decomposition.seasonal)
                residual_var = np.var(decomposition.resid[~np.isnan(decomposition.resid)])
                
                if seasonal_var + residual_var > 0:
                    strength = seasonal_var / (seasonal_var + residual_var)
                    
                    if strength > best_strength:
                        best_strength = strength
                        best_period = period
            except:
                continue
        
        return {
            'strength': float(best_strength),
            'period': best_period
        }
    
    def detect_trend(self, sales_data: pd.DataFrame) -> Dict:
        """
        Detect trend direction and strength using linear regression
        
        Returns:
            Dictionary with direction and slope
        """
        if len(sales_data) < 7:
            return {'direction': 'flat', 'slope': 0.0}
        
        # Time index as X
        X = np.arange(len(sales_data)).reshape(-1, 1)
        y = sales_data['quantity_sold'].values
        
        # Fit linear trend
        from sklearn.linear_model import LinearRegression
        model = LinearRegression().fit(X, y)
        slope = model.coef_[0]
        
        # Categorize trend
        if abs(slope) < 0.01:
            direction = 'flat'
        elif slope > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'
        
        return {
            'direction': direction,
            'slope': float(slope)
        }
    
    def batch_segment_products(self, sales_df: pd.DataFrame, product_col: str = 'sku') -> pd.DataFrame:
        """
        Segment multiple products at once
        
        Args:
            sales_df: DataFrame with columns: [product_col, 'date', 'quantity_sold']
            product_col: Name of product identifier column
            
        Returns:
            DataFrame with segment info per product
        """
        results = []
        
        for product_id in sales_df[product_col].unique():
            product_sales = sales_df[sales_df[product_col] == product_id].copy()
            product_sales = product_sales.sort_values('date').reset_index(drop=True)
            
            segment_info = self.segment_product(product_sales)
            
            results.append({
                product_col: product_id,
                **segment_info
            })
        
        return pd.DataFrame(results)
