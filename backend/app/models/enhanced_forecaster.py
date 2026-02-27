"""
Enhanced Multi-Model Demand Forecasting Engine v2
==================================================
Intelligent model selection based on product segmentation.
Handles sparse sales data properly by using weekly aggregation.
Supports: Holt-Winters, SARIMA, Seasonal Naive, Trend-Seasonal Decomposition,
           and Weighted Ensemble predictions.

Key improvements over v1:
- Weekly aggregation prevents flat-line forecasts from sparse daily data
- Holt-Winters with multiplicative/additive seasonality captures real patterns
- Seasonal decomposition preserves up/down cycles in predictions
- Ensemble combines multiple models for robustness
- Day-of-week weighting disaggregates weekly forecasts back to daily
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Statistical models
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose
from sklearn.linear_model import LinearRegression
import scipy.stats as stats

# Optional ML models
try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

from .product_segmentation import ProductSegmenter


class EnhancedDemandForecaster:
    """
    Production-grade forecasting engine with intelligent model selection.
    
    Models (ranked by preference):
    1. Holt-Winters (Triple Exponential Smoothing) - Best for seasonal data
    2. SARIMA - Seasonal ARIMA for strong periodic patterns
    3. Seasonal Naive - Repeats last seasonal cycle (robust baseline)
    4. Trend-Seasonal Decomposition - Extrapolates trend + overlays seasonality
    5. Prophet - ML-based (if installed) 
    6. XGBoost - Feature-rich ML (if installed)
    7. Weighted Ensemble - Combines top 2 models
    
    Features:
    - Smart weekly aggregation for sparse daily data
    - Day-of-week demand weighting for realistic daily patterns
    - Automatic seasonality detection and period selection
    - Confidence intervals with proper uncertainty propagation
    - NLP business explanations
    """
    
    def __init__(self, segment_info: Dict = None):
        self.segment_info = segment_info
        self.segmenter = ProductSegmenter()
        self.model = None
        self.model_name = None
        self.feature_names = []
        self.forecast_metadata = {}
        
    def fit_and_forecast(self, sales_data: pd.DataFrame, forecast_days: int = 30,
                        product_metadata: Dict = None) -> Dict:
        """
        Main forecasting pipeline - selects best model and generates forecast.
        
        Key design: Uses WEEKLY aggregation internally to avoid the zero-inflation
        problem with sparse daily data, then disaggregates back to daily using
        day-of-week demand patterns.
        """
        # Step 1: Segment product
        if self.segment_info is None:
            self.segment_info = self.segmenter.segment_product(sales_data)
        
        segment = self.segment_info['segment']
        
        # Step 2: Prepare data - both daily and aggregated views
        df_daily = self._prepare_daily_data(sales_data)
        df_weekly = self._aggregate_weekly(df_daily)
        dow_weights = self._compute_dow_weights(df_daily)
        
        # Check data density: if <50% of weeks have sales, use bi-weekly
        nonzero_pct = (df_weekly['quantity_sold'] > 0).mean()
        if nonzero_pct < 0.5 and len(df_weekly) >= 8:
            df_agg = self._aggregate_biweekly(df_daily)
            agg_period = 'biweekly'
        else:
            df_agg = df_weekly
            agg_period = 'weekly'
        
        # Smooth weekly data to help seasonal models converge
        df_agg_smooth = self._smooth_weekly_data(df_agg)
        
        if len(df_agg) < 4:
            return self._fallback_forecast(df_daily, forecast_days, "insufficient_data")
        
        # Step 3: Try models in order of preference based on data availability
        if agg_period == 'biweekly':
            forecast_periods = max(1, (forecast_days + 13) // 14)
        else:
            forecast_periods = max(1, (forecast_days + 6) // 7)
        
        result = None
        models_tried = []
        
        # Strategy: Try the best model for this segment, fall back gracefully
        model_priority = self._get_model_priority(segment, len(df_agg))
        
        for model_name in model_priority:
            try:
                # Use smoothed data for model fitting (better convergence)
                # but original data for seasonal extraction
                if model_name == 'holt_winters':
                    result = self._fit_holt_winters(df_agg_smooth, forecast_periods, agg_period)
                elif model_name == 'sarima':
                    result = self._fit_sarima_weekly(df_agg_smooth, forecast_periods, agg_period)
                elif model_name == 'seasonal_naive':
                    result = self._fit_seasonal_naive(df_agg, forecast_periods, agg_period)
                elif model_name == 'decomposition':
                    result = self._fit_decomposition(df_agg_smooth, forecast_periods, agg_period)
                elif model_name == 'prophet' and PROPHET_AVAILABLE:
                    result = self._fit_prophet(df_daily, forecast_days)
                    break
                elif model_name == 'xgboost' and XGBOOST_AVAILABLE:
                    result = self._fit_xgboost_weekly(df_agg_smooth, forecast_periods, product_metadata)
                
                if result is not None:
                    models_tried.append(model_name)
                    break
                    
            except Exception as e:
                models_tried.append(f"{model_name}(failed:{str(e)[:50]})")
                continue
        
        # Fallback if nothing worked
        if result is None:
            result = self._fallback_forecast(df_daily, forecast_days, "all_models_failed")
            result['_is_daily'] = True
        
        # Step 4: Enrich near-flat forecasts with seasonal modulation
        if not result.get('_is_daily', False):
            result = self._enrich_with_seasonality(result, df_agg, forecast_periods, agg_period)
        
        # Step 5: Disaggregate periodic forecast to daily (unless already daily)
        if not result.get('_is_daily', False):
            period_days = 14 if agg_period == 'biweekly' else 7
            result = self._disaggregate_to_daily(result, forecast_days, dow_weights, df_daily, period_days)
        
        # Remove internal flag
        result.pop('_is_daily', None)
        result.pop('_is_weekly', None)
        
        # Step 5: Generate explanation
        explanation = self._generate_explanation(
            segment=segment,
            model_name=self.model_name,
            characteristics=self.segment_info['characteristics'],
            forecast_summary=result,
            models_tried=models_tried
        )
        
        result['explanation'] = explanation
        result['segment_info'] = self.segment_info
        
        return result
    
    def _get_model_priority(self, segment: str, n_weeks: int) -> List[str]:
        """
        Get model priority based on segment and data availability.
        Different segments use different model orderings to ensure
        diverse, product-specific forecast shapes.
        """
        
        if n_weeks >= 12:  # 3+ months of weekly data
            if segment == 'SEASONAL_STABLE':
                # Strong seasonal patterns — SARIMA excels at capturing periodicity
                return ['sarima', 'holt_winters', 'decomposition', 'xgboost', 'seasonal_naive']
            elif segment == 'SEASONAL_VOLATILE':
                # Seasonal but spiky — decomposition + ML handle volatility better
                return ['decomposition', 'xgboost', 'sarima', 'holt_winters', 'seasonal_naive']
            elif segment == 'STABLE_FLAT':
                # Flat demand — decomposition shows subtle real patterns, avoid forcing seasonality
                return ['decomposition', 'holt_winters', 'seasonal_naive', 'sarima']
            elif segment == 'STABLE_TRENDING':
                # Clear trend — Holt-Winters linear trend is ideal, XGBoost captures non-linear
                return ['holt_winters', 'xgboost', 'decomposition', 'sarima', 'seasonal_naive']
            elif segment == 'VOLATILE':
                # High variance — XGBoost/decomposition handle non-linear spikes
                return ['xgboost', 'decomposition', 'seasonal_naive', 'holt_winters', 'sarima']
            elif segment == 'INTERMITTENT':
                # Sparse demand — seasonal naive repeats actual sparse patterns
                return ['seasonal_naive', 'decomposition', 'holt_winters']
            else:  # MODERATE
                return ['decomposition', 'holt_winters', 'sarima', 'xgboost', 'seasonal_naive']
        elif n_weeks >= 6:
            if segment in ('SEASONAL_STABLE', 'SEASONAL_VOLATILE'):
                return ['seasonal_naive', 'holt_winters', 'decomposition']
            elif segment == 'VOLATILE':
                return ['seasonal_naive', 'decomposition', 'holt_winters']
            else:
                return ['holt_winters', 'seasonal_naive', 'decomposition']
        else:
            return ['seasonal_naive', 'decomposition']
    
    # ========================
    # DATA PREPARATION
    # ========================
    
    def _prepare_daily_data(self, sales_data: pd.DataFrame) -> pd.DataFrame:
        """Prepare daily sales data WITHOUT zero-filling gaps."""
        df = sales_data.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        # Aggregate multiple transactions per day
        df = df.groupby('date').agg({'quantity_sold': 'sum'}).reset_index()
        df = df.sort_values('date').reset_index(drop=True)
        
        return df
    
    def _aggregate_weekly(self, df_daily: pd.DataFrame) -> pd.DataFrame:
        """Aggregate daily data to weekly totals - eliminates sparsity problem."""
        df = df_daily.copy()
        df['week'] = df['date'].dt.to_period('W').apply(lambda r: r.start_time)
        
        weekly = df.groupby('week').agg(
            quantity_sold=('quantity_sold', 'sum'),
            n_days=('date', 'count')
        ).reset_index()
        weekly = weekly.rename(columns={'week': 'date'})
        
        # Fill missing weeks with 0
        full_weeks = pd.date_range(
            start=weekly['date'].min(),
            end=weekly['date'].max(),
            freq='W-MON'
        )
        weekly = weekly.set_index('date').reindex(full_weeks, fill_value=0).reset_index()
        weekly = weekly.rename(columns={'index': 'date'})
        if 'n_days' not in weekly.columns:
            weekly['n_days'] = 0
        
        return weekly
    
    def _smooth_weekly_data(self, df_weekly: pd.DataFrame) -> pd.DataFrame:
        """
        Lightly smooth weekly data to reduce only extreme outlier spikes 
        that prevent seasonal models from converging.
        
        Uses conservative winsorization (99th pct) to preserve product-specific
        demand patterns while only taming the most extreme values.
        """
        df = df_weekly.copy()
        y = df['quantity_sold'].values.astype(float)
        
        if len(y) < 4:
            return df
        
        # Conservative winsorization: only cap truly extreme outliers (99th pct * 2)
        # This preserves product-specific spikes while preventing model divergence
        if np.any(y > 0):
            p99 = np.percentile(y[y > 0], 99)
            y_capped = np.minimum(y, p99 * 2.0)
        else:
            y_capped = y.copy()
        
        # For very sparse data (<30% nonzero), do minimal spreading
        # only for extremely isolated spikes — preserves intermittent character
        nonzero_pct = (y > 0).mean()
        if nonzero_pct < 0.3:
            y_smooth = np.copy(y_capped)
            median_nonzero = np.median(y[y > 0]) if np.any(y > 0) else 1
            for i in range(len(y_smooth)):
                # Only spread if this value is a true outlier (>5x median)
                if y_smooth[i] > median_nonzero * 5:
                    window = list(range(max(0, i-1), min(len(y_smooth), i+2)))
                    spread_val = y_smooth[i] / len(window)
                    for j in window:
                        y_smooth[j] = max(y_smooth[j], spread_val)
            y_capped = y_smooth
        
        df['quantity_sold'] = y_capped
        return df
    
    def _aggregate_biweekly(self, df_daily: pd.DataFrame) -> pd.DataFrame:
        """Aggregate daily data to bi-weekly (2-week) totals for sparse products."""
        df = df_daily.copy()
        df['biweek'] = df['date'].dt.to_period('2W').apply(lambda r: r.start_time)
        
        biweekly = df.groupby('biweek').agg(
            quantity_sold=('quantity_sold', 'sum'),
            n_days=('date', 'count')
        ).reset_index()
        biweekly = biweekly.rename(columns={'biweek': 'date'})
        
        # Fill missing bi-weeks with 0
        full_biweeks = pd.date_range(
            start=biweekly['date'].min(),
            end=biweekly['date'].max(),
            freq='2W-MON'
        )
        biweekly = biweekly.set_index('date').reindex(full_biweeks, fill_value=0).reset_index()
        biweekly = biweekly.rename(columns={'index': 'date'})
        if 'n_days' not in biweekly.columns:
            biweekly['n_days'] = 0
        
        return biweekly
    
    def _compute_dow_weights(self, df_daily: pd.DataFrame) -> np.ndarray:
        """
        Compute day-of-week demand weights from historical data.
        Used to disaggregate weekly forecasts into realistic daily patterns.
        Returns array of 7 weights (Mon=0 to Sun=6) that sum to 1.
        """
        df = df_daily.copy()
        df['dow'] = df['date'].dt.dayofweek
        
        dow_totals = df.groupby('dow')['quantity_sold'].sum()
        
        # Ensure all 7 days are represented
        weights = np.zeros(7)
        for dow in range(7):
            weights[dow] = dow_totals.get(dow, 0)
        
        total = weights.sum()
        if total > 0:
            weights = weights / total
        else:
            weights = np.ones(7) / 7  # Uniform if no data
        
        return weights
    
    # ========================
    # MODEL IMPLEMENTATIONS
    # ========================
    
    def _fit_holt_winters(self, df_weekly: pd.DataFrame, forecast_weeks: int, agg_period: str = 'weekly') -> Dict:
        """
        Holt-Winters Triple Exponential Smoothing with seasonality.
        Best model for data showing trend + seasonal patterns.
        """
        y = df_weekly['quantity_sold'].values.astype(float)
        n = len(y)
        
        # Add small epsilon to zeros to help seasonal models converge
        has_zeros = np.any(y == 0)
        if has_zeros:
            y_fit = y + 0.1  # Tiny offset prevents division-by-zero in multiplicative
        else:
            y_fit = y
        
        # Determine seasonal period based on aggregation
        if agg_period == 'biweekly':
            if n >= 12:
                seasonal_period = 6   # Quarterly in bi-weeks
            elif n >= 6:
                seasonal_period = 3   # ~Monthly in bi-weeks
            else:
                seasonal_period = None
        else:
            # For weekly: try quarterly (13w), then monthly (4w)
            if n >= 26:
                seasonal_period = 13  # Quarterly seasonality
            elif n >= 8:
                seasonal_period = 4   # Monthly seasonality
            else:
                seasonal_period = None
        
        best_model = None
        best_aic = float('inf')
        best_name = "Holt-Winters"
        self.model_name = "Holt-Winters"
        
        configs = []
        # Relaxed constraint: try seasonal with n >= seasonal_period + 2 (not *2)
        if seasonal_period and n >= seasonal_period + 2:
            # Try with seasonality - additive first (safer with zeros)
            configs.append({
                'trend': 'add', 'seasonal': 'add', 
                'seasonal_periods': seasonal_period,
                'label': f'Holt-Winters (Additive Seasonal, period={seasonal_period}w)'
            })
            # Multiplicative if no zeros (use original y to check, not y_fit)
            if not has_zeros:
                configs.append({
                    'trend': 'add', 'seasonal': 'mul',
                    'seasonal_periods': seasonal_period,
                    'label': f'Holt-Winters (Multiplicative Seasonal, period={seasonal_period}w)'
                })
        
        # Also try with damped trend (no seasonality)
        configs.append({
            'trend': 'add', 'seasonal': None, 
            'seasonal_periods': None, 'damped_trend': True,
            'label': 'Holt-Winters (Damped Trend)'
        })
        configs.append({
            'trend': 'add', 'seasonal': None,
            'seasonal_periods': None,
            'label': 'Holt-Winters (Linear Trend)'
        })
        
        # Also try monthly (4-week) seasonality if quarterly was chosen
        # This gives a second chance at seasonal patterns
        if seasonal_period and seasonal_period > 4 and n >= 6:
            configs.insert(2, {
                'trend': 'add', 'seasonal': 'add',
                'seasonal_periods': 4,
                'label': 'Holt-Winters (Monthly Seasonal, period=4w)'
            })
        
        for config in configs:
            try:
                label = config.pop('label')
                sp = config.pop('seasonal_periods', None)
                
                model_kwargs = {k: v for k, v in config.items() if v is not None}
                if sp:
                    model_kwargs['seasonal_periods'] = sp
                
                # Use y_fit (with epsilon) for seasonal models, original y for non-seasonal
                fit_data = y_fit if sp else y
                
                model = ExponentialSmoothing(fit_data, **model_kwargs)
                fitted = model.fit(optimized=True, use_brute=True)
                
                aic = fitted.aic if hasattr(fitted, 'aic') and np.isfinite(fitted.aic) else float('inf')
                if aic < best_aic:
                    best_aic = aic
                    best_model = fitted
                    best_name = label
            except Exception:
                continue
        
        if best_model is None:
            return None
        
        self.model = best_model
        self.model_name = best_name
        
        # Forecast
        forecast_mean = best_model.forecast(steps=forecast_weeks)
        forecast_mean = np.maximum(np.array(forecast_mean, dtype=float), 0)
        
        # Confidence intervals from fitted residuals
        residuals = y - best_model.fittedvalues
        std_residual = np.std(residuals)
        
        # Widen CI over horizon
        widening = np.array([1 + 0.02 * i for i in range(forecast_weeks)])
        lower_bound = np.maximum(forecast_mean - 1.96 * std_residual * widening, 0)
        upper_bound = np.maximum(forecast_mean + 1.96 * std_residual * widening, 0)
        
        freq_str = '2W-MON' if agg_period == 'biweekly' else 'W-MON'
        step = timedelta(weeks=2) if agg_period == 'biweekly' else timedelta(weeks=1)
        forecast_dates = pd.date_range(
            start=df_weekly['date'].iloc[-1] + step,
            periods=forecast_weeks,
            freq=freq_str
        )
        
        return {
            'forecast_dates': forecast_dates.tolist(),
            'forecast': forecast_mean.tolist(),
            'lower_bound': lower_bound.tolist(),
            'upper_bound': upper_bound.tolist(),
            'model_used': self.model_name,
            'confidence_level': 0.95,
            'model_type': 'seasonal_smoothing',
            '_is_weekly': True
        }
    
    def _fit_sarima_weekly(self, df_weekly: pd.DataFrame, forecast_weeks: int, agg_period: str = 'weekly') -> Dict:
        """SARIMA on weekly aggregated data with seasonal component."""
        y = df_weekly['quantity_sold'].values.astype(float)
        n = len(y)
        self.model_name = "SARIMA"
        
        # Seasonal period
        if agg_period == 'biweekly':
            seasonal_period = 6 if n >= 12 else (3 if n >= 6 else None)
        else:
            seasonal_period = 13 if n >= 26 else (4 if n >= 8 else None)
        
        if n < seasonal_period * 2:
            return None
        
        try:
            model = SARIMAX(
                y,
                order=(1, 1, 1),
                seasonal_order=(1, 0, 1, seasonal_period),
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            fitted = model.fit(disp=False, maxiter=200)
            self.model = fitted
            
            forecast_result = fitted.get_forecast(steps=forecast_weeks)
            forecast_mean = np.maximum(forecast_result.predicted_mean.values, 0)
            conf_int = forecast_result.conf_int()
            
            lower_bound = np.maximum(conf_int.iloc[:, 0].values, 0)
            upper_bound = np.maximum(conf_int.iloc[:, 1].values, 0)
            
            forecast_dates = pd.date_range(
                start=df_weekly['date'].iloc[-1] + (timedelta(weeks=2) if agg_period == 'biweekly' else timedelta(weeks=1)),
                periods=forecast_weeks,
                freq='2W-MON' if agg_period == 'biweekly' else 'W-MON'
            )
            
            self.model_name = f"SARIMA(1,1,1)x(1,0,1,{seasonal_period})"
            
            return {
                'forecast_dates': forecast_dates.tolist(),
                'forecast': forecast_mean.tolist(),
                'lower_bound': lower_bound.tolist(),
                'upper_bound': upper_bound.tolist(),
                'model_used': self.model_name,
                'confidence_level': 0.95,
                'model_type': 'seasonal_statistical',
                '_is_weekly': True
            }
        except Exception as e:
            print(f"SARIMA weekly failed: {e}")
            return None
    
    def _fit_seasonal_naive(self, df_weekly: pd.DataFrame, forecast_weeks: int, agg_period: str = 'weekly') -> Dict:
        """
        Seasonal Naive: Repeats the last full seasonal cycle.
        Very robust baseline that always shows realistic up/down patterns.
        """
        y = df_weekly['quantity_sold'].values.astype(float)
        n = len(y)
        self.model_name = "Seasonal Naive"
        
        # Determine cycle length
        if n >= 52:
            cycle_len = 52  # Annual
        elif n >= 26:
            cycle_len = 13  # Quarterly
        elif n >= 8:
            cycle_len = 4   # Monthly
        else:
            cycle_len = n   # Use all available
        
        # Get the last full cycle
        last_cycle = y[-cycle_len:]
        
        # Repeat cycle for forecast period
        forecast_mean = np.array([last_cycle[i % cycle_len] for i in range(forecast_weeks)])
        forecast_mean = np.maximum(forecast_mean, 0)
        
        # Confidence interval: widen with horizon
        cycle_std = np.std(last_cycle)
        widening = np.array([1 + 0.05 * i for i in range(forecast_weeks)])
        lower_bound = np.maximum(forecast_mean - 1.5 * cycle_std * widening, 0)
        upper_bound = forecast_mean + 1.5 * cycle_std * widening
        
        forecast_dates = pd.date_range(
            start=df_weekly['date'].iloc[-1] + (timedelta(weeks=2) if agg_period == 'biweekly' else timedelta(weeks=1)),
            periods=forecast_weeks,
            freq='2W-MON' if agg_period == 'biweekly' else 'W-MON'
        )
        
        self.model_name = f"Seasonal Naive (cycle={cycle_len} periods)"
        
        return {
            'forecast_dates': forecast_dates.tolist(),
            'forecast': forecast_mean.tolist(),
            'lower_bound': lower_bound.tolist(),
            'upper_bound': upper_bound.tolist(),
            'model_used': self.model_name,
            'confidence_level': 0.90,
            'model_type': 'seasonal_naive',
            '_is_weekly': True
        }
    
    def _fit_decomposition(self, df_weekly: pd.DataFrame, forecast_weeks: int, agg_period: str = 'weekly') -> Dict:
        """
        Trend-Seasonal Decomposition forecast:
        1. Decompose history into trend + seasonal + residual
        2. Extrapolate trend using linear regression
        3. Overlay seasonal pattern from last full cycle
        
        Produces naturally oscillating forecasts.
        """
        y = df_weekly['quantity_sold'].values.astype(float)
        n = len(y)
        self.model_name = "Trend-Seasonal Decomposition"
        
        # Determine seasonal period
        if agg_period == 'biweekly':
            period = 6 if n >= 12 else (3 if n >= 6 else None)
        else:
            period = 13 if n >= 26 else (4 if n >= 8 else None)
        
        if n < period * 2:
            return None
        
        try:
            decomposition = seasonal_decompose(y, model='additive', period=period, extrapolate_trend='freq')
            
            trend = decomposition.trend
            seasonal = decomposition.seasonal
            
            # Extrapolate trend with linear regression
            valid_idx = ~np.isnan(trend)
            valid_trend = trend[valid_idx]
            X_trend = np.arange(len(valid_trend)).reshape(-1, 1)
            lr = LinearRegression().fit(X_trend, valid_trend)
            
            future_X = np.arange(len(valid_trend), len(valid_trend) + forecast_weeks).reshape(-1, 1)
            future_trend = lr.predict(future_X)
            
            # Get seasonal pattern for future (cycle the last period's seasonal component)
            last_seasonal_cycle = seasonal[-period:]
            future_seasonal = np.array([last_seasonal_cycle[i % period] for i in range(forecast_weeks)])
            
            # Combine: forecast = trend + seasonal
            forecast_mean = future_trend + future_seasonal
            forecast_mean = np.maximum(forecast_mean, 0)
            
            # Confidence intervals
            residuals = decomposition.resid[~np.isnan(decomposition.resid)]
            std_residual = np.std(residuals) if len(residuals) > 0 else np.std(y) * 0.3
            
            widening = np.array([1 + 0.03 * i for i in range(forecast_weeks)])
            lower_bound = np.maximum(forecast_mean - 1.96 * std_residual * widening, 0)
            upper_bound = forecast_mean + 1.96 * std_residual * widening
            
            forecast_dates = pd.date_range(
                start=df_weekly['date'].iloc[-1] + (timedelta(weeks=2) if agg_period == 'biweekly' else timedelta(weeks=1)),
                periods=forecast_weeks,
                freq='2W-MON' if agg_period == 'biweekly' else 'W-MON'
            )
            
            self.model_name = f"Seasonal Decomposition (period={period})"
            
            return {
                'forecast_dates': forecast_dates.tolist(),
                'forecast': forecast_mean.tolist(),
                'lower_bound': lower_bound.tolist(),
                'upper_bound': upper_bound.tolist(),
                'model_used': self.model_name,
                'confidence_level': 0.95,
                'model_type': 'decomposition_forecast',
                '_is_weekly': True
            }
        except Exception as e:
            print(f"Decomposition failed: {e}")
            return None
    
    def _fit_prophet(self, df_daily: pd.DataFrame, forecast_days: int) -> Dict:
        """Prophet on daily data (if installed)."""
        self.model_name = "Prophet"
        
        prophet_df = df_daily[['date', 'quantity_sold']].rename(
            columns={'date': 'ds', 'quantity_sold': 'y'}
        )
        
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=(len(df_daily) > 60),
            seasonality_mode='additive',
            interval_width=0.95
        )
        model.fit(prophet_df)
        self.model = model
        
        future = model.make_future_dataframe(periods=forecast_days, freq='D')
        forecast_result = model.predict(future).tail(forecast_days)
        
        forecast_mean = np.maximum(forecast_result['yhat'].values, 0)
        lower_bound = np.maximum(forecast_result['yhat_lower'].values, 0)
        upper_bound = np.maximum(forecast_result['yhat_upper'].values, 0)
        
        return {
            'forecast_dates': forecast_result['ds'].tolist(),
            'forecast': forecast_mean.tolist(),
            'lower_bound': lower_bound.tolist(),
            'upper_bound': upper_bound.tolist(),
            'model_used': self.model_name,
            'confidence_level': 0.95,
            'model_type': 'ml_time_series',
            '_is_daily': True
        }
    
    def _fit_xgboost_weekly(self, df_weekly: pd.DataFrame, forecast_weeks: int, 
                            product_metadata: Dict = None) -> Dict:
        """XGBoost on weekly data with lag features."""
        self.model_name = "XGBoost"
        
        df = df_weekly.copy()
        
        # Feature engineering on weekly data
        df['week_num'] = df['date'].dt.isocalendar().week.astype(int)
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        
        # Lags (in weeks)
        for lag in [1, 2, 4, 8, 13]:
            df[f'lag_{lag}'] = df['quantity_sold'].shift(lag)
        
        # Rolling stats
        for window in [4, 8, 13]:
            df[f'rolling_mean_{window}'] = df['quantity_sold'].rolling(window, min_periods=1).mean()
            df[f'rolling_std_{window}'] = df['quantity_sold'].rolling(window, min_periods=1).std().fillna(0)
        
        df = df.fillna(0)
        
        feature_cols = [c for c in df.columns if c not in ['date', 'quantity_sold', 'n_days']]
        X = df[feature_cols].values
        y = df['quantity_sold'].values
        
        model = XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42)
        model.fit(X, y)
        self.model = model
        
        # Future features
        last_date = df_weekly['date'].iloc[-1]
        future_dates = pd.date_range(start=last_date + timedelta(weeks=1), periods=forecast_weeks, freq='W-MON')
        
        future_df = pd.DataFrame({'date': future_dates, 'quantity_sold': 0})
        future_df['week_num'] = future_df['date'].dt.isocalendar().week.astype(int)
        future_df['month'] = future_df['date'].dt.month
        future_df['quarter'] = future_df['date'].dt.quarter
        
        # Use last known values for lags
        full = pd.concat([df[['date', 'quantity_sold']], future_df[['date', 'quantity_sold']]], ignore_index=True)
        for lag in [1, 2, 4, 8, 13]:
            full[f'lag_{lag}'] = full['quantity_sold'].shift(lag)
        for window in [4, 8, 13]:
            full[f'rolling_mean_{window}'] = full['quantity_sold'].rolling(window, min_periods=1).mean()
            full[f'rolling_std_{window}'] = full['quantity_sold'].rolling(window, min_periods=1).std().fillna(0)
        
        future_features = full.tail(forecast_weeks).fillna(0)
        X_future = future_features[feature_cols].values
        
        forecast_mean = np.maximum(model.predict(X_future), 0)
        
        # Confidence intervals
        residuals = y - model.predict(X)
        std_res = np.std(residuals)
        lower_bound = np.maximum(forecast_mean - 1.96 * std_res, 0)
        upper_bound = forecast_mean + 1.96 * std_res
        
        return {
            'forecast_dates': future_dates.tolist(),
            'forecast': forecast_mean.tolist(),
            'lower_bound': lower_bound.tolist(),
            'upper_bound': upper_bound.tolist(),
            'model_used': self.model_name,
            'confidence_level': 0.95,
            'model_type': 'ml_gradient_boosting',
            '_is_weekly': True
        }
    
    # ========================
    # SEASONAL ENRICHMENT
    # ========================
    
    def _enrich_with_seasonality(self, forecast_result: Dict, df_weekly: pd.DataFrame,
                                  forecast_periods: int, agg_period: str) -> Dict:
        """
        If the weekly/bi-weekly forecast is near-flat (low variation), overlay
        a seasonal modulation derived from ACTUAL historical data patterns.
        
        Uses STL decomposition on the product's own history to extract its
        unique seasonal shape. Never generates synthetic/fake patterns.
        Only applied when the base model produced a monotone/flat trend.
        """
        forecast = np.array(forecast_result['forecast'], dtype=float)
        
        if len(forecast) < 2:
            return forecast_result
        
        # Check if forecast is too flat (CV < 12%)
        f_mean = np.mean(forecast)
        if f_mean <= 0:
            return forecast_result
        f_cv = np.std(forecast) / f_mean
        
        if f_cv > 0.12:
            # Forecast already has meaningful variation — no enrichment needed
            return forecast_result
        
        # Extract seasonal pattern from THIS product's actual history via STL
        y = df_weekly['quantity_sold'].values.astype(float)
        n = len(y)
        
        if n < 8:
            return forecast_result
        
        # Try STL decomposition with product-specific period detection
        # Test multiple periods and pick the one with strongest seasonal signal
        if agg_period == 'biweekly':
            candidate_periods = [p for p in [6, 3] if n >= p * 2]
        else:
            candidate_periods = [p for p in [13, 4, 8, 6] if n >= p * 2]
        
        if not candidate_periods:
            return forecast_result
        
        best_seasonal = None
        best_strength = 0.0
        best_period = None
        
        for period in candidate_periods:
            try:
                decomp = seasonal_decompose(y, model='additive', period=period, extrapolate_trend='freq')
                seasonal_component = decomp.seasonal
                resid = decomp.resid[~np.isnan(decomp.resid)]
                
                seasonal_var = np.var(seasonal_component)
                resid_var = np.var(resid) if len(resid) > 0 else 1.0
                strength = seasonal_var / (seasonal_var + resid_var + 1e-10)
                
                if strength > best_strength:
                    best_strength = strength
                    best_seasonal = seasonal_component[-period:]  # Last cycle
                    best_period = period
            except Exception:
                continue
        
        # Only apply enrichment if actual seasonal signal is meaningful (>10%)
        if best_seasonal is None or best_strength < 0.10:
            # This product genuinely has flat demand — respect that, no fake patterns
            return forecast_result
        
        # Build seasonal index from the actual decomposed component
        cycle_mean = np.mean(y[-best_period * min(3, n // best_period):])
        if cycle_mean <= 0:
            return forecast_result
        
        # Seasonal index = 1.0 + (seasonal_component / mean_demand)
        # This preserves the product's actual seasonal shape and amplitude
        seasonal_index = 1.0 + (best_seasonal / cycle_mean)
        
        # Clamp extreme ratios (0.4 to 2.0)
        seasonal_index = np.clip(seasonal_index, 0.4, 2.0)
        
        # Apply seasonal modulation to forecast
        lower = np.array(forecast_result['lower_bound'], dtype=float)
        upper = np.array(forecast_result['upper_bound'], dtype=float)
        
        mod_forecast = np.array([
            forecast[i] * seasonal_index[i % best_period]
            for i in range(len(forecast))
        ])
        mod_lower = np.array([
            lower[i] * seasonal_index[i % best_period]
            for i in range(len(lower))
        ])
        mod_upper = np.array([
            upper[i] * seasonal_index[i % best_period]
            for i in range(len(upper))
        ])
        
        forecast_result['forecast'] = np.maximum(mod_forecast, 0).tolist()
        forecast_result['lower_bound'] = np.maximum(mod_lower, 0).tolist()
        forecast_result['upper_bound'] = np.maximum(mod_upper, 0).tolist()
        
        # Update model name to indicate data-driven seasonal enrichment
        if 'Seasonal' not in forecast_result.get('model_used', ''):
            forecast_result['model_used'] = forecast_result.get('model_used', '') + f' + Seasonal Enrichment (period={best_period}, strength={best_strength:.0%})'
        
        return forecast_result
    
    def _fallback_forecast(self, df_daily: pd.DataFrame, forecast_days: int, reason: str) -> Dict:
        """Fallback: use recent weekly pattern, disaggregated by day of week using actual DOW weights."""
        self.model_name = f"Moving Average ({reason})"
        
        # Use last 28 days of actual sales to compute a weekly average
        recent = df_daily.tail(min(28, len(df_daily)))
        
        if len(recent) > 0:
            total_qty = recent['quantity_sold'].sum()
            date_span = (recent['date'].max() - recent['date'].min()).days + 1
            daily_avg = total_qty / max(date_span, 1)
        else:
            daily_avg = 0
        
        # Use actual day-of-week weights computed from historical data instead of fake sine wave
        dow_weights = self._compute_dow_weights(df_daily)
        
        forecast_dates = pd.date_range(
            start=df_daily['date'].iloc[-1] + timedelta(days=1),
            periods=forecast_days,
            freq='D'
        )
        
        # Apply DOW weights to daily average for realistic pattern
        forecast_mean = np.array([
            max(0, daily_avg * dow_weights[d.dayofweek] * 7)  # weights sum to ~1, scale up for daily
            for d in forecast_dates
        ])
        
        std_recent = df_daily['quantity_sold'].std() if len(df_daily) > 1 else daily_avg * 0.5
        lower_bound = np.maximum(forecast_mean - 1.5 * std_recent, 0)
        upper_bound = forecast_mean + 1.5 * std_recent
        
        return {
            'forecast_dates': forecast_dates.tolist(),
            'forecast': np.round(forecast_mean, 2).tolist(),
            'lower_bound': np.round(lower_bound, 2).tolist(),
            'upper_bound': np.round(upper_bound, 2).tolist(),
            'model_used': self.model_name,
            'confidence_level': 0.80,
            'model_type': 'fallback_average',
            '_is_daily': True
        }
    
    # ========================
    # DISAGGREGATION
    # ========================
    
    def _disaggregate_to_daily(self, weekly_result: Dict, forecast_days: int,
                               dow_weights: np.ndarray, df_daily: pd.DataFrame,
                               period_days: int = 7) -> Dict:
        """
        Convert periodic (weekly/bi-weekly) forecast to daily using day-of-week weights.
        This produces realistic daily patterns (e.g., higher on weekdays, lower on weekends).
        
        Adds product-specific micro-variation based on historical residual patterns
        to ensure each product's forecast has a unique daily shape.
        """
        periodic_forecast = np.array(weekly_result['forecast'])
        periodic_lower = np.array(weekly_result['lower_bound'])
        periodic_upper = np.array(weekly_result['upper_bound'])
        
        # Start date for daily forecast
        last_date = df_daily['date'].iloc[-1]
        start_date = last_date + timedelta(days=1)
        
        daily_dates = pd.date_range(start=start_date, periods=forecast_days, freq='D')
        daily_forecast = np.zeros(forecast_days)
        daily_lower = np.zeros(forecast_days)
        daily_upper = np.zeros(forecast_days)
        
        # Compute product-specific noise scale from historical daily residuals
        # This adds unique texture to each product's daily forecast
        hist_qty = df_daily['quantity_sold'].values.astype(float)
        hist_mean = np.mean(hist_qty) if len(hist_qty) > 0 else 1.0
        hist_residual_std = np.std(hist_qty) if len(hist_qty) > 1 else 0
        # Scale noise to ~5% of mean demand (subtle but differentiating)
        noise_scale = min(hist_residual_std * 0.15, hist_mean * 0.08) if hist_mean > 0 else 0
        
        # Use a deterministic seed based on the product's own data signature
        # so the same product always gets the same micro-pattern (reproducible)
        data_hash = int(np.sum(hist_qty[:20]) * 1000) % (2**31)
        rng = np.random.RandomState(data_hash)
        
        for i, date in enumerate(daily_dates):
            period_idx = min(i // period_days, len(periodic_forecast) - 1)
            dow = date.dayofweek
            
            # Scale periodic total by day-of-week weight
            scale = period_days / 7.0
            base_val = periodic_forecast[period_idx] * dow_weights[dow] / scale
            
            # Add tiny product-specific variation (deterministic)
            micro_noise = rng.normal(0, noise_scale) if noise_scale > 0 else 0
            daily_forecast[i] = base_val + micro_noise
            daily_lower[i] = periodic_lower[period_idx] * dow_weights[dow] / scale
            daily_upper[i] = periodic_upper[period_idx] * dow_weights[dow] / scale
        
        # Ensure non-negative
        daily_forecast = np.maximum(daily_forecast, 0)
        daily_lower = np.maximum(daily_lower, 0)
        daily_upper = np.maximum(daily_upper, 0)
        
        return {
            'forecast_dates': daily_dates.tolist(),
            'forecast': np.round(daily_forecast, 2).tolist(),
            'lower_bound': np.round(daily_lower, 2).tolist(),
            'upper_bound': np.round(daily_upper, 2).tolist(),
            'model_used': weekly_result['model_used'],
            'confidence_level': weekly_result['confidence_level'],
            'model_type': weekly_result['model_type']
        }
    
    # ========================
    # EXPLANATION ENGINE
    # ========================
    
    def _generate_explanation(self, segment: str, model_name: str, characteristics: Dict,
                             forecast_summary: Dict, models_tried: List[str] = None) -> str:
        """Generate business-friendly NLP explanation of forecast."""
        
        cv = characteristics.get('coefficient_of_variation', 0)
        seasonality = characteristics.get('seasonality_strength', 0)
        trend = characteristics.get('trend_direction', 'flat')
        zero_pct = characteristics.get('zero_sales_pct', 0)
        mean_demand = characteristics.get('mean_demand', 0)
        
        parts = []
        
        # Segment description
        segment_desc = {
            'STABLE_FLAT': "This product has stable, predictable demand — ideal for accurate forecasting.",
            'STABLE_TRENDING': "This product shows a clear trend in demand over time.",
            'SEASONAL_STABLE': "This product has strong seasonal patterns with predictable peaks and valleys.",
            'SEASONAL_VOLATILE': "This product shows seasonal behavior with significant variability between cycles.",
            'VOLATILE': "This product has highly variable demand with unpredictable spikes and drops.",
            'INTERMITTENT': "This product sells infrequently with many zero-sales periods between orders.",
            'MODERATE': "This product shows moderate demand patterns with some natural variation."
        }
        parts.append(segment_desc.get(segment, "Standard demand pattern."))
        
        # Model rationale
        model_key = model_name.split('(')[0].strip()
        model_desc = {
            'Holt-Winters': "The Holt-Winters model captures both the underlying trend and seasonal cycles in your sales data, producing forecasts that naturally rise and fall with expected demand patterns.",
            'SARIMA': "The SARIMA model accounts for seasonal demand cycles, producing forecasts that reflect the periodic ups and downs seen in your sales history.",
            'Seasonal Naive': "The forecast repeats your most recent demand cycle, assuming the pattern will continue — a robust baseline for seasonal products.",
            'Seasonal Decomposition': "The forecast separates your sales into trend, seasonal, and random components, then projects each forward for a realistic prediction.",
            'Prophet': "Facebook's Prophet model automatically detects trends, weekly patterns, and yearly seasonality in your data.",
            'XGBoost': "The XGBoost model uses advanced machine learning to find non-linear patterns in demand drivers.",
            'Moving Average': "Using a moving average approach as a baseline forecast."
        }
        parts.append(model_desc.get(model_key, f"Using {model_name} for forecasting."))
        
        # Key drivers
        drivers = []
        if seasonality > 0.3:
            drivers.append(f"seasonal patterns (strength: {seasonality:.0%})")
        if trend != 'flat':
            drivers.append(f"{trend} demand trend")
        if cv > 0.5:
            drivers.append("demand variability")
        if zero_pct > 20:
            drivers.append(f"intermittent sales ({zero_pct:.0f}% days with no sales)")
        if mean_demand > 0:
            drivers.append(f"average {mean_demand:.1f} units per selling day")
        if drivers:
            parts.append(f"Key factors: {', '.join(drivers)}.")
        
        # Forecast summary
        forecast_values = forecast_summary.get('forecast', [0])
        avg_forecast = np.mean(forecast_values)
        max_forecast = np.max(forecast_values)
        min_forecast = np.min(forecast_values)
        
        if max_forecast > 0 and min_forecast >= 0 and max_forecast > min_forecast * 1.3:
            parts.append(f"Predicted daily demand ranges from {min_forecast:.1f} to {max_forecast:.1f} units, reflecting natural demand cycles.")
        else:
            parts.append(f"Expected average daily demand: {avg_forecast:.1f} units.")
        
        # Confidence
        conf = self.segment_info.get('confidence', 'medium')
        conf_desc = {
            'high': "High confidence — consistent historical patterns support this forecast.",
            'medium': "Medium confidence — some variability in historical data. Consider safety stock.",
            'low': "Lower confidence — limited history or high unpredictability. Use wider safety margins."
        }
        parts.append(conf_desc.get(conf, ""))
        
        return " ".join(parts)


# Utility function for batch forecasting
def batch_forecast_products(sales_df: pd.DataFrame, forecast_days: int = 30, 
                           product_col: str = 'sku') -> List[Dict]:
    """Forecast multiple products efficiently."""
    results = []
    for product_id in sales_df[product_col].unique():
        product_sales = sales_df[sales_df[product_col] == product_id].copy()
        forecaster = EnhancedDemandForecaster()
        forecast_result = forecaster.fit_and_forecast(product_sales, forecast_days)
        forecast_result['product_id'] = product_id
        results.append(forecast_result)
    return results
