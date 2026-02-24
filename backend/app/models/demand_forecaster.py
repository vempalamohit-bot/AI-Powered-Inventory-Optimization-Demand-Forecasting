import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from sklearn.linear_model import LinearRegression
from scipy.stats import pearsonr, spearmanr
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    print("Prophet not available - install with: pip install prophet")

class DemandForecaster:
    """
    Advanced demand forecasting engine using multiple techniques:
    - ARIMA (AutoRegressive Integrated Moving Average) for non-stationary time series
    - Exponential Smoothing (Holt-Winters) for trend and seasonality
    - Linear Regression for feature-based predictions
    - Ensemble predictions with confidence intervals
    - Product metadata adjustment for seasonality, volatility, and classification
    """
    
    def __init__(self, model_type: str = 'auto'):
        """
        Initialize forecaster with specified model type
        
        Args:
            model_type: 'arima', 'exponential', 'prophet', or 'auto' (default: 'auto')
                       'auto' will test all available models and pick the best one
        """
        self.model = None
        self.prophet_model = None
        self.feature_model = None
        self.model_type = model_type
        self.model_name = None
        self.product_metadata = None  # Store product metadata for adjustments
        self.best_model_type = None  # Track which model performed best in auto mode
        
        # Dynamic feature selection and ensemble weighting
        self.selected_features = None  # Auto-selected features based on correlation
        self.feature_importance = {}  # Correlation scores for each feature
        self.ensemble_weights = {'time_series': 0.7, 'feature': 0.3}  # Dynamic weights
        self.historical_accuracy = None  # Track accuracy for weight adjustment
    
    def set_product_metadata(self, metadata: dict):
        """
        Set product metadata for enhanced predictions.
        
        Uses these CSV columns for better forecasting:
        - seasonality_factor: Multiplier for seasonal demand patterns (default 1.0)
        - demand_volatility: 0-1 scale for prediction confidence adjustment
        - abc_classification: A/B/C for inventory prioritization
        - xyz_classification: X/Y/Z for demand predictability
        - profit_margin: For prioritization
        - target_service_level: For safety stock calculation
        - is_perishable: Affects reorder recommendations
        - lead_time_days: For reorder timing
        - inventory_turnover: Annual turnover rate - high turnover = more reactive forecasts
        """
        self.product_metadata = {
            'seasonality_factor': float(metadata.get('seasonality_factor', 1.0)),
            'demand_volatility': float(metadata.get('demand_volatility', 0.5)),
            'abc_classification': metadata.get('abc_classification', 'B'),
            'xyz_classification': metadata.get('xyz_classification', 'Y'),
            'profit_margin': float(metadata.get('profit_margin', 0.3)),
            'target_service_level': float(metadata.get('target_service_level', 0.95)),
            'is_perishable': bool(metadata.get('is_perishable', False)),
            'lead_time_days': int(metadata.get('lead_time_days', 7)),
            'average_daily_demand': float(metadata.get('average_daily_demand', 0)) if metadata.get('average_daily_demand') else None,
            'stockout_cost_per_unit': float(metadata.get('stockout_cost_per_unit', 0)) if metadata.get('stockout_cost_per_unit') else None,
            'inventory_turnover': float(metadata.get('inventory_turnover', 0)) if metadata.get('inventory_turnover') else None,
        }
    
    def adjust_forecast_with_metadata(self, forecast: np.ndarray, lower_bound: np.ndarray, upper_bound: np.ndarray) -> tuple:
        """
        Adjust forecast using product metadata for more accurate predictions.
        
        Adjustments:
        1. Apply seasonality_factor to scale predictions
        2. Widen confidence intervals based on demand_volatility
        3. Use ABC/XYZ classification for weighting
        """
        if self.product_metadata is None:
            return forecast, lower_bound, upper_bound
        
        # 1. Apply seasonality factor
        seasonality = self.product_metadata.get('seasonality_factor', 1.0)
        forecast = forecast * seasonality
        lower_bound = lower_bound * seasonality
        upper_bound = upper_bound * seasonality
        
        # 2. Adjust confidence intervals based on demand volatility
        volatility = self.product_metadata.get('demand_volatility', 0.5)
        # Higher volatility = wider confidence intervals
        volatility_multiplier = 1.0 + (volatility - 0.5) * 0.5  # 0.75x to 1.25x
        interval_width = upper_bound - lower_bound
        center = (upper_bound + lower_bound) / 2
        lower_bound = center - (interval_width / 2) * volatility_multiplier
        upper_bound = center + (interval_width / 2) * volatility_multiplier
        
        # 3. XYZ adjustment (X=predictable, Y=moderate, Z=unpredictable)
        xyz = self.product_metadata.get('xyz_classification', 'Y')
        if xyz == 'Z':  # Highly unpredictable - widen intervals more
            interval_width = upper_bound - lower_bound
            lower_bound = lower_bound - interval_width * 0.2
            upper_bound = upper_bound + interval_width * 0.2
        elif xyz == 'X':  # Highly predictable - narrow intervals
            interval_width = upper_bound - lower_bound
            lower_bound = lower_bound + interval_width * 0.1
            upper_bound = upper_bound - interval_width * 0.1
        
        # 4. Use average_daily_demand as sanity check if available
        avg_demand = self.product_metadata.get('average_daily_demand')
        if avg_demand and avg_demand > 0:
            # Blend with stored average if significantly different
            forecast_avg = np.mean(forecast)
            if abs(forecast_avg - avg_demand) / avg_demand > 0.5:  # >50% difference
                # Weight towards stored average (30%) for stability
                adjustment = (avg_demand - forecast_avg) * 0.3
                forecast = forecast + adjustment
                lower_bound = lower_bound + adjustment
                upper_bound = upper_bound + adjustment
        
        # 5. Adjust forecast reactivity based on inventory_turnover
        # High turnover products (fast movers) should react faster to recent trends
        # Low turnover products (slow movers) should rely more on long-term averages
        inventory_turnover = self.product_metadata.get('inventory_turnover')
        if inventory_turnover is not None and inventory_turnover > 0:
            # Turnover categories:
            # High (>12): Monthly+ cycles - very reactive to recent data
            # Medium (4-12): Quarterly cycles - balanced
            # Low (<4): Slow movers - conservative, rely on averages
            
            if inventory_turnover > 12:  # High turnover - fast moving
                # Increase recent trend weight by boosting forecast variation
                forecast_trend = np.diff(forecast, prepend=forecast[0])
                forecast = forecast + forecast_trend * 0.15  # 15% more reactive
            elif inventory_turnover < 4:  # Low turnover - slow moving
                # Reduce forecast variation, smooth towards average
                forecast_mean = np.mean(forecast)
                forecast = forecast * 0.7 + forecast_mean * 0.3  # 30% pull to average
        
        # Ensure non-negative
        forecast = np.maximum(forecast, 0)
        lower_bound = np.maximum(lower_bound, 0)
        
        return forecast, lower_bound, upper_bound
        
    def prepare_data(self, sales_data: pd.DataFrame) -> pd.DataFrame:
        """Prepare and clean sales data for forecasting"""
        df = sales_data.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df.set_index('date', inplace=True)
        
        # Resample to daily frequency and fill missing dates
        df = df.resample('D').sum()
        df['quantity_sold'] = df['quantity_sold'].fillna(0)
        
        return df
    
    def add_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features for enhanced prediction"""
        df['day_of_week'] = df.index.dayofweek
        df['day_of_month'] = df.index.day
        df['month'] = df.index.month
        df['quarter'] = df.index.quarter
        df['is_weekend'] = (df.index.dayofweek >= 5).astype(int)
        df['week_of_year'] = df.index.isocalendar().week
        
        return df
    
    def auto_select_features(self, df: pd.DataFrame, target_col: str = 'quantity_sold', 
                              min_correlation: float = 0.1) -> List[str]:
        """
        Auto-detect relevant features based on correlation analysis.
        Dynamically selects features that have meaningful correlation with demand.
        
        Args:
            df: DataFrame with features and target
            target_col: Target column name
            min_correlation: Minimum absolute correlation threshold (default 0.1)
            
        Returns:
            List of selected feature names sorted by importance
        """
        all_features = ['day_of_week', 'day_of_month', 'month', 'quarter', 'is_weekend', 'week_of_year']
        feature_correlations = {}
        
        if target_col not in df.columns or len(df) < 10:
            # Return default features if insufficient data
            self.selected_features = ['day_of_week', 'month', 'is_weekend']
            return self.selected_features
        
        for feature in all_features:
            if feature in df.columns:
                try:
                    # Use Spearman for non-linear relationships
                    corr, p_value = spearmanr(df[feature].values, df[target_col].values)
                    
                    # Only include if correlation is significant (p < 0.05) and meaningful
                    if not np.isnan(corr) and p_value < 0.05 and abs(corr) >= min_correlation:
                        feature_correlations[feature] = {
                            'correlation': abs(corr),
                            'direction': 'positive' if corr > 0 else 'negative',
                            'p_value': p_value
                        }
                except Exception:
                    continue
        
        # Store feature importance for transparency
        self.feature_importance = feature_correlations
        
        # Sort by correlation strength and select top features
        sorted_features = sorted(
            feature_correlations.keys(), 
            key=lambda x: feature_correlations[x]['correlation'], 
            reverse=True
        )
        
        # Always include at least 2 features if available
        if len(sorted_features) < 2:
            # Fallback to default features with lowest threshold
            self.selected_features = ['day_of_week', 'month', 'is_weekend']
        else:
            # Take top features that meet threshold
            self.selected_features = sorted_features[:min(4, len(sorted_features))]
        
        return self.selected_features
    
    def calculate_ensemble_weights(self, df: pd.DataFrame, validation_split: float = 0.2) -> Dict[str, float]:
        """
        Dynamically calculate ensemble weights based on historical accuracy.
        Tests both models on holdout data and weights by performance.
        
        Args:
            df: Historical sales data with date index
            validation_split: Fraction of data to use for validation
            
        Returns:
            Dictionary with 'time_series' and 'feature' weights
        """
        if len(df) < 30:
            # Not enough data for validation - use defaults
            return {'time_series': 0.7, 'feature': 0.3}
        
        # Split data for validation
        split_idx = int(len(df) * (1 - validation_split))
        train_df = df.iloc[:split_idx]
        val_df = df.iloc[split_idx:]
        
        if len(val_df) < 5:
            return {'time_series': 0.7, 'feature': 0.3}
        
        ts_mae = float('inf')
        feature_mae = float('inf')
        
        try:
            # Test time-series model
            if self.model is not None and hasattr(self.model, 'get_forecast'):
                ts_forecast = self.model.get_forecast(steps=len(val_df))
                ts_pred = ts_forecast.predicted_mean.values
                actual = val_df['quantity_sold'].values
                if len(ts_pred) == len(actual):
                    ts_mae = np.mean(np.abs(actual - ts_pred))
        except Exception:
            pass
        
        try:
            # Test feature model
            if self.feature_model is not None:
                val_features = self.add_features(val_df.copy())
                feature_cols = self.selected_features or ['day_of_week', 'day_of_month', 'month', 'is_weekend']
                available_cols = [c for c in feature_cols if c in val_features.columns]
                
                if available_cols:
                    X_val = val_features[available_cols].values
                    feature_pred = self.feature_model.predict(X_val)
                    actual = val_df['quantity_sold'].values
                    if len(feature_pred) == len(actual):
                        feature_mae = np.mean(np.abs(actual - feature_pred))
        except Exception:
            pass
        
        # Calculate weights inversely proportional to MAE
        if ts_mae == float('inf') and feature_mae == float('inf'):
            return {'time_series': 0.7, 'feature': 0.3}
        
        if ts_mae == float('inf'):
            return {'time_series': 0.3, 'feature': 0.7}
        
        if feature_mae == float('inf'):
            return {'time_series': 0.9, 'feature': 0.1}
        
        # Inverse MAE weighting (lower error = higher weight)
        total_inverse = (1 / (ts_mae + 1)) + (1 / (feature_mae + 1))
        ts_weight = (1 / (ts_mae + 1)) / total_inverse
        feature_weight = (1 / (feature_mae + 1)) / total_inverse
        
        # Clamp weights to reasonable range (20%-80%)
        ts_weight = max(0.2, min(0.8, ts_weight))
        feature_weight = 1 - ts_weight
        
        self.ensemble_weights = {'time_series': round(ts_weight, 2), 'feature': round(feature_weight, 2)}
        self.historical_accuracy = {
            'time_series_mae': round(ts_mae, 2) if ts_mae != float('inf') else None,
            'feature_mae': round(feature_mae, 2) if feature_mae != float('inf') else None
        }
        
        return self.ensemble_weights
    
    def check_stationarity(self, data: pd.Series) -> bool:
        """
        Check if time series is stationary using Augmented Dickey-Fuller test
        
        Args:
            data: Time series data
            
        Returns:
            True if stationary (p-value < 0.05), False otherwise
        """
        try:
            result = adfuller(data.dropna())
            return result[1] < 0.05  # p-value < 0.05 means stationary
        except:
            return False
    
    def auto_arima_order(self, data: pd.Series) -> tuple:
        """
        Automatically determine ARIMA order (p,d,q) based on data characteristics
        
        Args:
            data: Time series data
            
        Returns:
            Tuple of (p, d, q) parameters
        """
        # Check stationarity to determine d (differencing order)
        d = 0
        temp_data = data.copy()
        
        # Maximum 2 differences
        for diff in range(3):
            if self.check_stationarity(temp_data):
                d = diff
                break
            temp_data = temp_data.diff().dropna()
        
        # Conservative parameters that work well for inventory data
        # p (AR order): 1-2, q (MA order): 1-2
        p = 1  # Autoregressive order
        q = 1  # Moving average order
        
        return (p, d, q)
    
    def fit_arima(self, sales_data: pd.DataFrame):
        """
        Fit ARIMA model on historical sales data
        
        Args:
            sales_data: DataFrame with 'date' and 'quantity_sold' columns
        """
        df = self.prepare_data(sales_data)
        
        if len(df) < 14:
            self.model = None
            self.model_name = "insufficient_data"
            return
        
        try:
            # Auto-determine ARIMA parameters
            order = self.auto_arima_order(df['quantity_sold'])
            
            # Fit ARIMA model
            self.model = ARIMA(
                df['quantity_sold'],
                order=order,
                enforce_stationarity=False,
                enforce_invertibility=False
            ).fit()
            
            self.model_name = f"ARIMA{order}"
            
        except Exception as e:
            print(f"ARIMA fitting failed: {e}, falling back to simple ARIMA(1,1,1)")
            try:
                self.model = ARIMA(df['quantity_sold'], order=(1,1,1)).fit()
                self.model_name = "ARIMA(1,1,1)"
            except:
                self.model = None
                self.model_name = "failed"
    
    def fit_exponential(self, sales_data: pd.DataFrame, seasonal_periods: int = 7):
        """
        Fit Exponential Smoothing model on historical sales data
        
        Args:
            sales_data: DataFrame with 'date' and 'quantity_sold' columns
            seasonal_periods: Number of periods in a season (7 for weekly patterns)
        """
        df = self.prepare_data(sales_data)
        
        if len(df) < seasonal_periods * 2:
            self.model = None
            self.model_name = "insufficient_data"
            return
        
        try:
            self.model = ExponentialSmoothing(
                df['quantity_sold'],
                seasonal_periods=seasonal_periods,
                trend='add',
                seasonal='add',
                initialization_method='estimated'
            ).fit()
            self.model_name = "Exponential Smoothing (Holt-Winters)"
        except:
            try:
                self.model = ExponentialSmoothing(
                    df['quantity_sold'],
                    trend='add',
                    seasonal=None
                ).fit()
                self.model_name = "Exponential Smoothing (Simple)"
            except:
                self.model = None
                self.model_name = "failed"
    
    def fit_prophet(self, sales_data: pd.DataFrame):
        """
        Fit Prophet model on historical sales data.
        Prophet automatically detects:
        - Yearly seasonality
        - Weekly seasonality
        - Holiday effects
        - Trend changes
        
        Args:
            sales_data: DataFrame with 'date' and 'quantity_sold' columns
        """
        if not PROPHET_AVAILABLE:
            self.prophet_model = None
            self.model_name = "prophet_unavailable"
            return
        
        df = self.prepare_data(sales_data)
        
        if len(df) < 14:
            self.prophet_model = None
            self.model_name = "insufficient_data"
            return
        
        try:
            # Prepare data for Prophet (requires 'ds' and 'y' columns)
            prophet_df = pd.DataFrame({
                'ds': df.index,
                'y': df['quantity_sold'].values
            })
            
            # Initialize Prophet with appropriate settings for inventory data
            self.prophet_model = Prophet(
                yearly_seasonality=True if len(df) >= 365 else False,
                weekly_seasonality=True if len(df) >= 14 else False,
                daily_seasonality=False,
                seasonality_mode='multiplicative',  # Better for retail data
                changepoint_prior_scale=0.05,  # Conservative trend changes
                seasonality_prior_scale=10.0,  # Allow strong seasonality
            )
            
            # Add monthly seasonality if enough data
            if len(df) >= 60:
                self.prophet_model.add_seasonality(
                    name='monthly',
                    period=30.5,
                    fourier_order=5
                )
            
            # Fit the model
            self.prophet_model.fit(prophet_df)
            self.model_name = "Prophet (Seasonality-Aware)"
            
        except Exception as e:
            print(f"Prophet model failed: {e}")
            self.prophet_model = None
            self.model_name = "prophet_failed"
    
    def fit(self, sales_data: pd.DataFrame, seasonal_periods: int = 7):
        """
        Fit the forecasting model on historical sales data
        
        Args:
            sales_data: DataFrame with 'date' and 'quantity_sold' columns
            seasonal_periods: Number of periods in a season (7 for weekly patterns)
        """
        df = self.prepare_data(sales_data)
        
        if len(df) < 14:
            self.model = None
            self.model_name = "insufficient_data"
            return
        
        # Fit primary model based on model_type
        if self.model_type == 'arima':
            self.fit_arima(sales_data)
        elif self.model_type == 'exponential':
            self.fit_exponential(sales_data, seasonal_periods)
        elif self.model_type == 'prophet':
            self.fit_prophet(sales_data)
        else:  # auto mode - test all models and pick best
            self._auto_select_best_model(sales_data, seasonal_periods)
        
        # Fit feature-based model for ensemble with auto-selected features
        df_features = self.add_features(df)
        
        # AUTO-SELECT FEATURES based on correlation analysis
        self.auto_select_features(df_features, 'quantity_sold')
        feature_cols = self.selected_features or ['day_of_week', 'day_of_month', 'month', 'is_weekend']
        
        if len(df_features) > 10:
            X = df_features[feature_cols].values
            y = df_features['quantity_sold'].values
            
            self.feature_model = LinearRegression()
            self.feature_model.fit(X, y)
            
            # CALCULATE DYNAMIC ENSEMBLE WEIGHTS based on historical accuracy
            self.calculate_ensemble_weights(df)
    
    def _auto_select_best_model(self, sales_data: pd.DataFrame, seasonal_periods: int = 7):
        """
        Automatically test all available models and select the best performing one.
        Tests models on validation data and picks the one with lowest error.
        
        Args:
            sales_data: DataFrame with 'date' and 'quantity_sold' columns
            seasonal_periods: Number of periods in a season
        """
        df = self.prepare_data(sales_data)
        
        if len(df) < 30:
            # Not enough data for validation - fallback to ARIMA
            self.fit_arima(sales_data)
            self.best_model_type = 'arima'
            return
        
        # Split data for validation (80/20)
        split_idx = int(len(df) * 0.8)
        train_df = df.iloc[:split_idx].copy()
        val_df = df.iloc[split_idx:].copy()
        
        model_scores = {}
        
        # Test ARIMA
        try:
            test_forecaster_arima = DemandForecaster('arima')
            test_forecaster_arima.set_product_metadata(self.product_metadata or {})
            train_sales = pd.DataFrame({
                'date': train_df.index,
                'quantity_sold': train_df['quantity_sold']
            }).reset_index(drop=True)
            test_forecaster_arima.fit(train_sales)
            
            if test_forecaster_arima.model is not None:
                pred_result = test_forecaster_arima.predict(steps=len(val_df))
                predictions = pred_result['predictions'][:len(val_df)]
                actual = val_df['quantity_sold'].values
                
                mae = np.mean(np.abs(actual - predictions))
                model_scores['arima'] = mae
                print(f"   ARIMA MAE: {mae:.2f}")
        except Exception as e:
            print(f"   ARIMA test failed: {e}")
        
        # Test Exponential Smoothing
        try:
            test_forecaster_exp = DemandForecaster('exponential')
            test_forecaster_exp.set_product_metadata(self.product_metadata or {})
            train_sales = pd.DataFrame({
                'date': train_df.index,
                'quantity_sold': train_df['quantity_sold']
            }).reset_index(drop=True)
            test_forecaster_exp.fit(train_sales, seasonal_periods)
            
            if test_forecaster_exp.model is not None:
                pred_result = test_forecaster_exp.predict(steps=len(val_df))
                predictions = pred_result['predictions'][:len(val_df)]
                actual = val_df['quantity_sold'].values
                
                mae = np.mean(np.abs(actual - predictions))
                model_scores['exponential'] = mae
                print(f"   Exponential MAE: {mae:.2f}")
        except Exception as e:
            print(f"   Exponential test failed: {e}")
        
        # Test Prophet (if available)
        if PROPHET_AVAILABLE:
            try:
                test_forecaster_prophet = DemandForecaster('prophet')
                test_forecaster_prophet.set_product_metadata(self.product_metadata or {})
                train_sales = pd.DataFrame({
                    'date': train_df.index,
                    'quantity_sold': train_df['quantity_sold']
                }).reset_index(drop=True)
                test_forecaster_prophet.fit(train_sales)
                
                if test_forecaster_prophet.prophet_model is not None:
                    pred_result = test_forecaster_prophet.predict(steps=len(val_df))
                    predictions = pred_result['predictions'][:len(val_df)]
                    actual = val_df['quantity_sold'].values
                    
                    mae = np.mean(np.abs(actual - predictions))
                    model_scores['prophet'] = mae
                    print(f"   Prophet MAE: {mae:.2f}")
            except Exception as e:
                print(f"   Prophet test failed: {e}")
        
        # Select best model
        if not model_scores:
            # All models failed - fallback to ARIMA
            self.fit_arima(sales_data)
            self.best_model_type = 'arima_fallback'
            return
        
        best_model = min(model_scores, key=model_scores.get)
        self.best_model_type = best_model
        
        print(f"   ✅ Selected: {best_model.upper()} (MAE: {model_scores[best_model]:.2f})")
        
        # Fit the best model on full data
        if best_model == 'arima':
            self.fit_arima(sales_data)
        elif best_model == 'exponential':
            self.fit_exponential(sales_data, seasonal_periods)
        elif best_model == 'prophet':
            self.fit_prophet(sales_data)
    
    def predict(self, steps: int = 30) -> Dict[str, List]:
        """
        Generate demand forecast for the next N steps
        
        Args:
            steps: Number of days to forecast
            
        Returns:
            Dictionary with dates, predictions, lower_bound, upper_bound, model_used
        """
        # Check if Prophet model is available and should be used
        if self.prophet_model is not None:
            return self._predict_with_prophet(steps)
        
        if self.model is None:
            return self._simple_forecast(steps)
        
        # Get base forecast and confidence intervals
        if hasattr(self.model, 'get_forecast'):
            # ARIMA model - has built-in confidence intervals
            forecast_result = self.model.get_forecast(steps=steps)
            forecast = forecast_result.predicted_mean
            forecast_ci = forecast_result.conf_int(alpha=0.05)  # 95% confidence
            lower_bound = forecast_ci.iloc[:, 0]
            upper_bound = forecast_ci.iloc[:, 1]
        else:
            # Exponential Smoothing model - approximate confidence intervals
            forecast = self.model.forecast(steps=steps)
            residuals = self.model.resid
            std_error = np.std(residuals)
            z_score = 1.96  # 95% confidence
            
            lower_bound = forecast.values - z_score * std_error * np.sqrt(np.arange(1, steps + 1))
            upper_bound = forecast.values + z_score * std_error * np.sqrt(np.arange(1, steps + 1))
        
        # Generate future dates
        if hasattr(self.model, 'fittedvalues'):
            last_date = self.model.fittedvalues.index[-1]
        else:
            last_date = datetime.now()
            
        future_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            periods=steps,
            freq='D'
        )
        
        # Convert to numpy arrays for ensemble
        if isinstance(forecast, pd.Series):
            forecast = forecast.values
        if isinstance(lower_bound, pd.Series):
            lower_bound = lower_bound.values
        if isinstance(upper_bound, pd.Series):
            upper_bound = upper_bound.values
        
        # Ensemble with feature model if available using DYNAMIC WEIGHTS
        if self.feature_model is not None:
            future_df = pd.DataFrame(index=future_dates)
            future_df = self.add_features(future_df)
            
            # Use auto-selected features
            feature_cols = self.selected_features or ['day_of_week', 'day_of_month', 'month', 'is_weekend']
            available_cols = [c for c in feature_cols if c in future_df.columns]
            
            X_future = future_df[available_cols].values
            feature_predictions = self.feature_model.predict(X_future)
            
            # DYNAMIC ENSEMBLE: Weights based on historical accuracy per product
            ts_weight = self.ensemble_weights.get('time_series', 0.7)
            feature_weight = self.ensemble_weights.get('feature', 0.3)
            ensemble_forecast = ts_weight * forecast + feature_weight * feature_predictions
        else:
            ensemble_forecast = forecast
        
        # =========================================================
        # APPLY PRODUCT METADATA ADJUSTMENTS (uses CSV extra columns)
        # =========================================================
        # This uses: seasonality_factor, demand_volatility, xyz_classification,
        # average_daily_demand from the product's stored metadata
        ensemble_forecast, lower_bound, upper_bound = self.adjust_forecast_with_metadata(
            ensemble_forecast, lower_bound, upper_bound
        )
        
        # Ensure non-negative predictions
        ensemble_forecast = np.maximum(ensemble_forecast, 0)
        lower_bound = np.maximum(lower_bound, 0)
        upper_bound = np.maximum(upper_bound, 0)
        
        # Calculate trend direction from predictions
        if len(ensemble_forecast) > 7:
            first_week_avg = np.mean(ensemble_forecast[:7])
            last_week_avg = np.mean(ensemble_forecast[-7:])
            change_pct = ((last_week_avg - first_week_avg) / max(first_week_avg, 1)) * 100
            if change_pct > 10:
                trend_direction = "increasing"
            elif change_pct < -10:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
        else:
            trend_direction = "stable"
            change_pct = 0
        
        # Calculate summary statistics
        total_forecast = float(np.sum(ensemble_forecast))
        avg_daily = float(np.mean(ensemble_forecast))
        min_daily = float(np.min(ensemble_forecast))
        max_daily = float(np.max(ensemble_forecast))
        
        return {
            'dates': [d.strftime('%Y-%m-%d') for d in future_dates],
            'predictions': ensemble_forecast.tolist(),
            'lower_bound': lower_bound.tolist(),
            'upper_bound': upper_bound.tolist(),
            'model_used': self.model_name or 'Unknown',
            
            # === METHODOLOGY TRANSPARENCY: Show how prediction was made ===
            'methodology': {
                'primary_model': self.model_name,
                # DYNAMIC ENSEMBLE with auto-calculated weights
                'ensemble_approach': f"Weighted average: {self.ensemble_weights.get('time_series', 0.7)*100:.0f}% time-series + {self.ensemble_weights.get('feature', 0.3)*100:.0f}% feature-based (weights calculated from historical accuracy)" if self.feature_model is not None else 'Single model prediction',
                'ensemble_weights': self.ensemble_weights if self.feature_model is not None else None,
                'historical_accuracy': self.historical_accuracy if self.feature_model is not None else None,
                'confidence_level': '95%',
                # AUTO-SELECTED FEATURES based on correlation
                'features_auto_selected': self.selected_features is not None,
                'time_features_used': self.selected_features or ['day_of_week', 'day_of_month', 'month', 'is_weekend'] if self.feature_model is not None else [],
                'feature_importance': self.feature_importance if self.feature_importance else None,
                # Product metadata used for adjustments
                'product_adjustments_applied': self.product_metadata is not None,
                'product_factors': {
                    'seasonality_factor': self.product_metadata.get('seasonality_factor', 1.0) if self.product_metadata else 1.0,
                    'demand_volatility': self.product_metadata.get('demand_volatility', 0.5) if self.product_metadata else 0.5,
                    'xyz_classification': self.product_metadata.get('xyz_classification', 'Y') if self.product_metadata else 'Y',
                    'abc_classification': self.product_metadata.get('abc_classification', 'B') if self.product_metadata else 'B',
                } if self.product_metadata else None
            },
            
            # === TREND ANALYSIS ===
            'trend_analysis': {
                'direction': trend_direction,
                'change_percentage': round(change_pct, 1),
                'interpretation': f"Demand is {'projected to increase by' if change_pct > 0 else 'projected to decrease by'} {abs(change_pct):.1f}% over the forecast period" if abs(change_pct) > 5 else "Demand is expected to remain relatively stable"
            },
            
            # === SUMMARY STATISTICS ===
            'summary': {
                'total_forecasted_demand': round(total_forecast, 0),
                'average_daily_demand': round(avg_daily, 1),
                'min_daily_demand': round(min_daily, 1),
                'max_daily_demand': round(max_daily, 1),
                'forecast_horizon_days': steps
            }
        }
    
    def _predict_with_prophet(self, steps: int) -> Dict[str, List]:
        """
        Generate forecast using Prophet model with seasonality detection.
        
        Args:
            steps: Number of days to forecast
            
        Returns:
            Dictionary with dates, predictions, lower_bound, upper_bound, model_used
        """
        # Create future dataframe for Prophet
        future = self.prophet_model.make_future_dataframe(periods=steps, freq='D')
        
        # Generate forecast with confidence intervals
        forecast = self.prophet_model.predict(future)
        
        # Extract the forecast for future dates only (last 'steps' rows)
        future_forecast = forecast.tail(steps)
        
        # Get predictions and confidence intervals
        predictions = future_forecast['yhat'].values
        lower_bound = future_forecast['yhat_lower'].values
        upper_bound = future_forecast['yhat_upper'].values
        future_dates = future_forecast['ds'].values
        
        # Apply product metadata adjustments
        predictions, lower_bound, upper_bound = self.adjust_forecast_with_metadata(
            predictions, lower_bound, upper_bound
        )
        
        # Ensure non-negative
        predictions = np.maximum(predictions, 0)
        lower_bound = np.maximum(lower_bound, 0)
        
        # Convert dates to strings
        date_strings = [pd.Timestamp(d).strftime('%Y-%m-%d') for d in future_dates]
        
        model_description = self.model_name or "Prophet (Seasonality-Aware)"
        if self.best_model_type:
            model_description += f" [Auto-selected from {self.best_model_type}]"
        
        return {
            'dates': date_strings,
            'predictions': predictions.tolist(),
            'lower_bound': lower_bound.tolist(),
            'upper_bound': upper_bound.tolist(),
            'model_used': model_description,
            'seasonality_detected': {
                'weekly': len(self.prophet_model.train_holiday_names) > 0 if hasattr(self.prophet_model, 'train_holiday_names') else False,
                'yearly': self.prophet_model.yearly_seasonality if hasattr(self.prophet_model, 'yearly_seasonality') else False
            }
        }
    
    def _simple_forecast(self, steps: int) -> Dict[str, List]:
        """Fallback simple forecast when not enough data - uses product-specific metadata and statistical variation"""
        # Try to use product's average_daily_demand from metadata (from CSV extra columns)
        avg_demand = self.product_metadata.get('average_daily_demand')
        
        # If no metadata, estimate from available product statistics
        if avg_demand is None or avg_demand <= 0:
            # Use unit_price and cost to infer demand tier (higher-priced items tend to sell fewer units)
            unit_price = self.product_metadata.get('unit_price', 0) or 0
            unit_cost = self.product_metadata.get('unit_cost', 0) or 0
            current_stock = self.product_metadata.get('current_stock', 0) or 0
            lead_time = self.product_metadata.get('lead_time_days', 7) or 7
            
            if unit_price > 0 and current_stock > 0:
                # Estimate turnover: stock / lead_time gives rough daily consumption
                avg_demand = max(1, current_stock / (lead_time * 3))  # Assume ~3x lead time stock coverage
            else:
                # Minimal fallback: use reorder_point if available
                rop = self.product_metadata.get('reorder_point', 0) or 0
                if rop > 0:
                    avg_demand = max(1, rop / max(lead_time, 7))
                else:
                    avg_demand = 1  # Absolute minimum
        
        # Apply seasonality if available
        seasonality_factor = self.product_metadata.get('seasonality_factor', 1.0) or 1.0
        avg_demand = avg_demand * seasonality_factor
        
        future_dates = pd.date_range(
            start=datetime.now(),
            periods=steps,
            freq='D'
        )
        
        # Use demand volatility from metadata for realistic variation
        demand_volatility = self.product_metadata.get('demand_volatility', 0.3) or 0.3
        predictions = []
        for i in range(steps):
            # Apply day-of-week effect using typical retail patterns from data
            dow = future_dates[i].dayofweek
            # Empirical DOW factors (based on retail patterns): Mon-Sun
            dow_factors = [1.05, 1.02, 1.0, 0.98, 1.08, 1.1, 0.77]
            daily_demand = avg_demand * dow_factors[dow]
            # Add noise proportional to volatility
            noise = np.random.normal(0, demand_volatility * 0.1)
            daily_demand *= (1 + noise)
            predictions.append(max(0, daily_demand))
        
        # Confidence intervals scale with volatility
        lower_bound = [max(0, p * (1 - 0.3 * (1 + demand_volatility))) for p in predictions]
        upper_bound = [p * (1 + 0.3 * (1 + demand_volatility)) for p in predictions]
        
        return {
            'dates': [d.strftime('%Y-%m-%d') for d in future_dates],
            'predictions': predictions,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'model_used': 'Product-Metadata Baseline (Insufficient Sales Data)'
        }
    
    def calculate_accuracy_metrics(self, actual: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
        """Calculate forecast accuracy metrics"""
        mae = np.mean(np.abs(actual - predicted))
        mape = np.mean(np.abs((actual - predicted) / (actual + 1))) * 100  # +1 to avoid division by zero
        rmse = np.sqrt(np.mean((actual - predicted) ** 2))
        
        return {
            'mae': float(mae),
            'mape': float(mape),
            'rmse': float(rmse)
        }
