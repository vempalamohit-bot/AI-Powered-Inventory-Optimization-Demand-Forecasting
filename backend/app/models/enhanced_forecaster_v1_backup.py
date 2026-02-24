"""
Enhanced Multi-Model Demand Forecasting Engine
Intelligent model selection based on product segmentation
Supports SARIMA, Prophet, XGBoost, Croston, and ensemble predictions
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

# ML models
try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("XGBoost not available - install with: pip install xgboost")

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    print("Prophet not available - install with: pip install prophet")

from sklearn.linear_model import LinearRegression
import scipy.stats as stats

from .product_segmentation import ProductSegmenter


class EnhancedDemandForecaster:
    """
    Production-grade forecasting engine with intelligent model selection:
    
    Models:
    - SARIMA: Seasonal products with predictable patterns
    - Prophet: Products with strong trends and seasonality
    - XGBoost: Complex, feature-rich products with non-linear patterns
    - Croston/SBA: Intermittent demand products
    - Exponential Smoothing: Stable products with simple patterns
    - ARIMA: Baseline for moderate products
    
    Features:
    - Automatic product segmentation
    - Dynamic feature engineering
    - Confidence intervals
    - Model performance tracking
    - NLP explanations
    """
    
    def __init__(self, segment_info: Dict = None):
        """
        Initialize forecaster
        
        Args:
            segment_info: Product segmentation info (optional, will auto-detect if None)
        """
        self.segment_info = segment_info
        self.segmenter = ProductSegmenter()
        self.model = None
        self.model_name = None
        self.feature_names = []
        self.forecast_metadata = {}
        
    def fit_and_forecast(self, sales_data: pd.DataFrame, forecast_days: int = 30,
                        product_metadata: Dict = None) -> Dict:
        """
        Main forecasting pipeline - automatically selects best model and generates forecast
        
        Args:
            sales_data: DataFrame with 'date' and 'quantity_sold' columns
            forecast_days: Number of days to forecast
            product_metadata: Additional product info (category, price, promotions, etc.)
            
        Returns:
            Dictionary with forecast, confidence intervals, model info, and explanations
        """
        # Step 1: Segment product if not already done
        if self.segment_info is None:
            self.segment_info = self.segmenter.segment_product(sales_data)
        
        segment = self.segment_info['segment']
        recommended_model = self.segment_info['recommended_model']
        
        # Step 2: Prepare data
        df = self._prepare_data(sales_data)
        
        if len(df) < 14:
            return self._fallback_forecast(df, forecast_days, "insufficient_data")
        
        # Step 3: Select and fit model based on segment
        try:
            if recommended_model == 'sarima':
                result = self._fit_sarima(df, forecast_days)
            elif recommended_model == 'prophet' and PROPHET_AVAILABLE:
                result = self._fit_prophet(df, forecast_days)
            elif recommended_model == 'xgboost' and XGBOOST_AVAILABLE:
                result = self._fit_xgboost(df, forecast_days, product_metadata)
            elif recommended_model == 'croston':
                result = self._fit_croston(df, forecast_days)
            elif recommended_model == 'exponential_smoothing':
                result = self._fit_exponential(df, forecast_days)
            else:
                result = self._fit_arima(df, forecast_days)
        except Exception as e:
            print(f"Model {recommended_model} failed: {e}, falling back to simple forecast")
            result = self._fallback_forecast(df, forecast_days, f"{recommended_model}_failed")
        
        # Step 4: Generate NLP explanation
        explanation = self._generate_explanation(
            segment=segment,
            model_name=self.model_name,
            characteristics=self.segment_info['characteristics'],
            forecast_summary=result
        )
        
        result['explanation'] = explanation
        result['segment_info'] = self.segment_info
        
        return result
    
    def _prepare_data(self, sales_data: pd.DataFrame) -> pd.DataFrame:
        """Prepare and validate sales data"""
        df = sales_data.copy()
        
        # Ensure date column is datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            # Aggregate multiple transactions per day
            df = df.groupby('date').agg({'quantity_sold': 'sum'}).reset_index()
            df = df.sort_values('date').reset_index(drop=True)
        
        # Fill missing days with 0 sales
        df = df.set_index('date')
        df = df.asfreq('D', fill_value=0)
        df = df.reset_index()
        
        return df
    
    def _fit_sarima(self, df: pd.DataFrame, forecast_days: int) -> Dict:
        """Fit SARIMA model for seasonal products"""
        self.model_name = "SARIMA"
        
        # Get seasonality period from segmentation
        seasonal_period = self.segment_info['characteristics'].get('seasonality_period', 7)
        
        try:
            # SARIMA parameters: (p,d,q) x (P,D,Q,s)
            # p,d,q: non-seasonal parameters
            # P,D,Q: seasonal parameters
            # s: seasonal period
            model = SARIMAX(
                df['quantity_sold'],
                order=(1, 1, 1),
                seasonal_order=(1, 1, 1, seasonal_period),
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            
            fitted_model = model.fit(disp=False)
            self.model = fitted_model
            
            # Generate forecast
            forecast_result = fitted_model.get_forecast(steps=forecast_days)
            forecast_mean = forecast_result.predicted_mean.values
            conf_int = forecast_result.conf_int()
            
            # Ensure non-negative forecasts
            forecast_mean = np.maximum(forecast_mean, 0)
            lower_bound = np.maximum(conf_int.iloc[:, 0].values, 0)
            upper_bound = np.maximum(conf_int.iloc[:, 1].values, 0)
            
            forecast_dates = pd.date_range(
                start=df['date'].iloc[-1] + timedelta(days=1),
                periods=forecast_days,
                freq='D'
            )
            
            self.model_name = f"SARIMA(1,1,1)x(1,1,1,{seasonal_period})"
            
            return {
                'forecast_dates': forecast_dates.tolist(),
                'forecast': forecast_mean.tolist(),
                'lower_bound': lower_bound.tolist(),
                'upper_bound': upper_bound.tolist(),
                'model_used': self.model_name,
                'confidence_level': 0.95,
                'model_type': 'seasonal_statistical'
            }
        
        except Exception as e:
            print(f"SARIMA failed: {e}, trying Prophet")
            if PROPHET_AVAILABLE:
                return self._fit_prophet(df, forecast_days)
            else:
                return self._fit_arima(df, forecast_days)
    
    def _fit_prophet(self, df: pd.DataFrame, forecast_days: int) -> Dict:
        """Fit Facebook Prophet model for trend + seasonality"""
        self.model_name = "Prophet"
        
        # Prepare data in Prophet format
        prophet_df = df[['date', 'quantity_sold']].rename(
            columns={'date': 'ds', 'quantity_sold': 'y'}
        )
        
        # Initialize and fit Prophet
        model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=(len(df) > 365),
            seasonality_mode='additive',
            interval_width=0.95
        )
        
        model.fit(prophet_df)
        self.model = model
        
        # Create future dates
        future = model.make_future_dataframe(periods=forecast_days, freq='D')
        
        # Generate forecast
        forecast_result = model.predict(future)
        
        # Extract forecast for future dates only
        forecast_result = forecast_result.tail(forecast_days)
        
        # Ensure non-negative
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
            'model_type': 'ml_time_series'
        }
    
    def _fit_xgboost(self, df: pd.DataFrame, forecast_days: int, product_metadata: Dict = None) -> Dict:
        """Fit XGBoost with engineered features"""
        self.model_name = "XGBoost"
        
        # Feature engineering
        df_features = self._engineer_features(df, product_metadata)
        
        # Prepare training data
        feature_cols = [col for col in df_features.columns if col not in ['date', 'quantity_sold']]
        self.feature_names = feature_cols
        
        X = df_features[feature_cols].values
        y = df_features['quantity_sold'].values
        
        # Train XGBoost
        model = XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
            objective='reg:squarederror'
        )
        
        model.fit(X, y)
        self.model = model
        
        # Generate future features and forecast
        last_date = df['date'].iloc[-1]
        future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=forecast_days, freq='D')
        
        # Build future feature dataframe
        future_df = pd.DataFrame({'date': future_dates})
        future_df = self._engineer_features(future_df, product_metadata, is_future=True, historical_df=df)
        
        X_future = future_df[feature_cols].values
        forecast_mean = model.predict(X_future)
        forecast_mean = np.maximum(forecast_mean, 0)
        
        # Estimate confidence intervals using historical residuals
        train_predictions = model.predict(X)
        residuals = y - train_predictions
        std_residual = np.std(residuals)
        
        lower_bound = np.maximum(forecast_mean - 1.96 * std_residual, 0)
        upper_bound = forecast_mean + 1.96 * std_residual
        
        return {
            'forecast_dates': future_dates.tolist(),
            'forecast': forecast_mean.tolist(),
            'lower_bound': lower_bound.tolist(),
            'upper_bound': upper_bound.tolist(),
            'model_used': self.model_name,
            'confidence_level': 0.95,
            'model_type': 'ml_gradient_boosting',
            'feature_importance': dict(zip(feature_cols, model.feature_importances_.tolist()))
        }
    
    def _fit_croston(self, df: pd.DataFrame, forecast_days: int) -> Dict:
        """Croston's method for intermittent demand"""
        self.model_name = "Croston"
        
        quantities = df['quantity_sold'].values
        
        # Find non-zero demand periods
        non_zero_indices = np.where(quantities > 0)[0]
        
        if len(non_zero_indices) < 2:
            # Too sparse, use simple average
            avg_demand = np.mean(quantities[quantities > 0]) if len(non_zero_indices) > 0 else 0
            forecast_mean = np.full(forecast_days, avg_demand)
        else:
            # Calculate inter-demand intervals
            intervals = np.diff(non_zero_indices)
            demand_sizes = quantities[non_zero_indices[1:]]
            
            # Exponential smoothing on intervals and sizes
            alpha = 0.1
            
            # Smoothed interval
            smooth_interval = intervals[0]
            for interval in intervals[1:]:
                smooth_interval = alpha * interval + (1 - alpha) * smooth_interval
            
            # Smoothed demand size
            smooth_size = demand_sizes[0]
            for size in demand_sizes[1:]:
                smooth_size = alpha * size + (1 - alpha) * smooth_size
            
            # Forecast = size / interval
            forecast_value = smooth_size / smooth_interval if smooth_interval > 0 else 0
            forecast_mean = np.full(forecast_days, forecast_value)
        
        # Simple confidence intervals
        std_demand = np.std(quantities[quantities > 0]) if len(non_zero_indices) > 0 else 0
        lower_bound = np.maximum(forecast_mean - 1.96 * std_demand, 0)
        upper_bound = forecast_mean + 1.96 * std_demand
        
        forecast_dates = pd.date_range(
            start=df['date'].iloc[-1] + timedelta(days=1),
            periods=forecast_days,
            freq='D'
        )
        
        return {
            'forecast_dates': forecast_dates.tolist(),
            'forecast': forecast_mean.tolist(),
            'lower_bound': lower_bound.tolist(),
            'upper_bound': upper_bound.tolist(),
            'model_used': self.model_name,
            'confidence_level': 0.95,
            'model_type': 'intermittent_demand'
        }
    
    def _fit_exponential(self, df: pd.DataFrame, forecast_days: int) -> Dict:
        """Exponential Smoothing for stable products"""
        self.model_name = "Exponential Smoothing"
        
        try:
            model = ExponentialSmoothing(
                df['quantity_sold'],
                trend='add',
                seasonal=None
            ).fit()
            
            self.model = model
            forecast_mean = model.forecast(steps=forecast_days)
            forecast_mean = np.maximum(forecast_mean, 0)
            
            # Estimate confidence intervals
            residuals = df['quantity_sold'] - model.fittedvalues
            std_residual = np.std(residuals)
            
            lower_bound = np.maximum(forecast_mean - 1.96 * std_residual, 0)
            upper_bound = forecast_mean + 1.96 * std_residual
            
            forecast_dates = pd.date_range(
                start=df['date'].iloc[-1] + timedelta(days=1),
                periods=forecast_days,
                freq='D'
            )
            
            return {
                'forecast_dates': forecast_dates.tolist(),
                'forecast': forecast_mean.tolist(),
                'lower_bound': lower_bound.tolist(),
                'upper_bound': upper_bound.tolist(),
                'model_used': self.model_name,
                'confidence_level': 0.95,
                'model_type': 'statistical_smoothing'
            }
        except:
            return self._fit_arima(df, forecast_days)
    
    def _fit_arima(self, df: pd.DataFrame, forecast_days: int) -> Dict:
        """Baseline ARIMA model"""
        self.model_name = "ARIMA"
        
        try:
            model = ARIMA(df['quantity_sold'], order=(1,1,1)).fit()
            self.model = model
            
            forecast_result = model.get_forecast(steps=forecast_days)
            forecast_mean = np.maximum(forecast_result.predicted_mean.values, 0)
            conf_int = forecast_result.conf_int()
            
            lower_bound = np.maximum(conf_int.iloc[:, 0].values, 0)
            upper_bound = np.maximum(conf_int.iloc[:, 1].values, 0)
            
            forecast_dates = pd.date_range(
                start=df['date'].iloc[-1] + timedelta(days=1),
                periods=forecast_days,
                freq='D'
            )
            
            return {
                'forecast_dates': forecast_dates.tolist(),
                'forecast': forecast_mean.tolist(),
                'lower_bound': lower_bound.tolist(),
                'upper_bound': upper_bound.tolist(),
                'model_used': self.model_name,
                'confidence_level': 0.95,
                'model_type': 'statistical_baseline'
            }
        except:
            return self._fallback_forecast(df, forecast_days, "arima_failed")
    
    def _fallback_forecast(self, df: pd.DataFrame, forecast_days: int, reason: str) -> Dict:
        """Simple moving average fallback"""
        self.model_name = f"Simple Average ({reason})"
        
        # Use last 7 days average
        recent_avg = df['quantity_sold'].tail(7).mean()
        forecast_mean = np.full(forecast_days, recent_avg)
        
        # Wide confidence intervals to reflect uncertainty
        std_recent = df['quantity_sold'].tail(14).std()
        lower_bound = np.maximum(forecast_mean - 2 * std_recent, 0)
        upper_bound = forecast_mean + 2 * std_recent
        
        forecast_dates = pd.date_range(
            start=df['date'].iloc[-1] + timedelta(days=1),
            periods=forecast_days,
            freq='D'
        )
        
        return {
            'forecast_dates': forecast_dates.tolist(),
            'forecast': forecast_mean.tolist(),
            'lower_bound': lower_bound.tolist(),
            'upper_bound': upper_bound.tolist(),
            'model_used': self.model_name,
            'confidence_level': 0.95,
            'model_type': 'fallback_average'
        }
    
    def _engineer_features(self, df: pd.DataFrame, product_metadata: Dict = None,
                          is_future: bool = False, historical_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Engineer features for ML models
        
        Features:
        - Lag features (7, 14, 30 days)
        - Rolling averages (7, 14, 30 days)
        - Time features (day of week, month, quarter, is_weekend)
        - Trend features
        - Product metadata (category, price, promotion flags)
        """
        df = df.copy()
        
        # Time features
        df['day_of_week'] = df['date'].dt.dayofweek
        df['day_of_month'] = df['date'].dt.day
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        df['week_of_year'] = df['date'].dt.isocalendar().week
        
        if not is_future:
            # Lag features (only for training data)
            for lag in [7, 14, 30]:
                df[f'lag_{lag}'] = df['quantity_sold'].shift(lag)
            
            # Rolling averages
            for window in [7, 14, 30]:
                df[f'rolling_avg_{window}'] = df['quantity_sold'].rolling(window=window, min_periods=1).mean()
                df[f'rolling_std_{window}'] = df['quantity_sold'].rolling(window=window, min_periods=1).std().fillna(0)
        else:
            # For future data, use historical statistics
            if historical_df is not None:
                for lag in [7, 14, 30]:
                    df[f'lag_{lag}'] = historical_df['quantity_sold'].tail(lag).mean()
                
                for window in [7, 14, 30]:
                    df[f'rolling_avg_{window}'] = historical_df['quantity_sold'].tail(window).mean()
                    df[f'rolling_std_{window}'] = historical_df['quantity_sold'].tail(window).std()
        
        # Product metadata features
        if product_metadata:
            if 'price' in product_metadata:
                df['price'] = product_metadata['price']
            if 'has_promotion' in product_metadata:
                df['has_promotion'] = product_metadata['has_promotion']
            if 'category_encoded' in product_metadata:
                df['category'] = product_metadata['category_encoded']
        
        # Fill NaN values
        df = df.fillna(0)
        
        return df
    
    def _generate_explanation(self, segment: str, model_name: str, characteristics: Dict, forecast_summary: Dict) -> str:
        """
        Generate natural language explanation of forecast
        
        Returns human-readable explanation of:
        - Why this model was chosen
        - Key demand drivers
        - Confidence level
        - Business implications
        """
        # Extract key characteristics
        cv = characteristics.get('coefficient_of_variation', 0)
        seasonality = characteristics.get('seasonality_strength', 0)
        trend = characteristics.get('trend_direction', 'flat')
        zero_pct = characteristics.get('zero_sales_pct', 0)
        
        # Build explanation
        explanation_parts = []
        
        # 1. Segment description
        segment_descriptions = {
            'STABLE_FLAT': "This product shows stable, predictable demand with minimal fluctuation.",
            'STABLE_TRENDING': "This product has stable demand with a clear trend pattern.",
            'SEASONAL_STABLE': "This product exhibits strong seasonal patterns with predictable cycles.",
            'SEASONAL_VOLATILE': "This product shows seasonal behavior but with high variability.",
            'VOLATILE': "This product has highly variable demand requiring robust forecasting methods.",
            'INTERMITTENT': "This product has sparse, intermittent demand with many zero-sales days.",
            'MODERATE': "This product shows moderate demand patterns suitable for standard forecasting."
        }
        
        explanation_parts.append(segment_descriptions.get(segment, "Standard product demand pattern."))
        
        # 2. Model selection rationale
        model_rationales = {
            'SARIMA': f"Using SARIMA model to capture the {characteristics.get('seasonality_period', 7)}-day seasonal cycle.",
            'Prophet': "Using Facebook Prophet to model complex trends and multiple seasonal patterns.",
            'XGBoost': "Using gradient boosting to handle non-linear relationships and external features.",
            'Croston': f"Using Croston's method optimized for intermittent demand ({zero_pct:.1f}% zero-sales days).",
            'Exponential Smoothing': "Using exponential smoothing for stable demand with simple patterns.",
            'ARIMA': "Using ARIMA as a reliable baseline time-series model."
        }
        
        model_key = model_name.split('(')[0].strip()
        explanation_parts.append(model_rationales.get(model_key, f"Using {model_name} for forecasting."))
        
        # 3. Key drivers
        drivers = []
        if seasonality > 0.6:
            drivers.append(f"strong seasonality (strength: {seasonality:.2f})")
        if trend != 'flat':
            drivers.append(f"{trend} trend")
        if cv > 0.7:
            drivers.append("high demand variability")
        
        if drivers:
            explanation_parts.append(f"Key demand drivers: {', '.join(drivers)}.")
        
        # 4. Forecast summary
        avg_forecast = np.mean(forecast_summary['forecast'])
        explanation_parts.append(f"Expected average daily demand: {avg_forecast:.1f} units.")
        
        # 5. Confidence level
        confidence_descriptions = {
            'high': "High confidence - historical patterns are clear and consistent.",
            'medium': "Medium confidence - some variability in historical behavior.",
            'low': "Lower confidence - limited data or high unpredictability."
        }
        
        conf_level = self.segment_info.get('confidence', 'medium')
        explanation_parts.append(confidence_descriptions.get(conf_level, ""))
        
        return " ".join(explanation_parts)


# Utility function for batch forecasting
def batch_forecast_products(sales_df: pd.DataFrame, forecast_days: int = 30, product_col: str = 'sku') -> pd.DataFrame:
    """
    Forecast multiple products efficiently
    
    Args:
        sales_df: DataFrame with columns [product_col, 'date', 'quantity_sold']
        forecast_days: Days to forecast
        product_col: Product identifier column name
        
    Returns:
        DataFrame with forecasts for all products
    """
    results = []
    
    for product_id in sales_df[product_col].unique():
        product_sales = sales_df[sales_df[product_col] == product_id].copy()
        
        forecaster = EnhancedDemandForecaster()
        forecast_result = forecaster.fit_and_forecast(product_sales, forecast_days)
        
        # Add product ID to results
        forecast_result['product_id'] = product_id
        results.append(forecast_result)
    
    return results
