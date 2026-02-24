import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta
from scipy import stats

class DemandSensing:
    """
    Real-time demand sensing and anomaly detection:
    - Multi-channel demand aggregation
    - Demand anomaly detection
    - Trend acceleration detection
    - Promotional impact tracking
    - Supply chain signal integration
    """
    
    def __init__(self):
        pass
    
    def aggregate_multi_channel_demand(
        self,
        channels: Dict[str, List[float]],
        channel_weights: Dict[str, float] = None
    ) -> Dict:
        """
        Aggregate demand from multiple sales channels (retail, online, B2B, etc.)
        
        Args:
            channels: Dict of channel_name -> list of daily demand
            channel_weights: Optional weights for each channel (for future forecasting)
        
        Returns:
            Aggregated demand with channel breakdown
        """
        if not channels:
            return {'error': 'No channel data provided'}
        
        # Default equal weights
        if channel_weights is None:
            channel_weights = {ch: 1/len(channels) for ch in channels}
        
        aggregated_demand = []
        channel_stats = {}
        total_daily_demand = []
        
        # Normalize channel names and data
        max_length = max(len(data) for data in channels.values()) if channels else 0
        
        for i in range(max_length):
            daily_total = 0
            for channel_name, demand_data in channels.items():
                if i < len(demand_data):
                    daily_total += demand_data[i]
            total_daily_demand.append(daily_total)
        
        # Calculate statistics per channel
        for channel_name, demand_data in channels.items():
            channel_array = np.array(demand_data)
            channel_stats[channel_name] = {
                'total_demand': round(float(channel_array.sum()), 2),
                'average_daily': round(float(channel_array.mean()), 2),
                'std_deviation': round(float(channel_array.std()), 2),
                'min_daily': round(float(channel_array.min()), 2),
                'max_daily': round(float(channel_array.max()), 2),
                'trend': self._detect_trend(demand_data),
                'contribution_pct': round(float(channel_array.sum() / np.array(total_daily_demand).sum() * 100), 1) if np.array(total_daily_demand).sum() > 0 else 0
            }
        
        # Aggregated metrics
        total_demand_array = np.array(total_daily_demand)
        
        return {
            'aggregation_method': 'Multi-Channel Consolidation',
            'channels_included': list(channels.keys()),
            'total_channels': len(channels),
            'aggregated_total_demand': round(float(total_demand_array.sum()), 2),
            'aggregated_average_daily': round(float(total_demand_array.mean()), 2),
            'aggregated_std_dev': round(float(total_demand_array.std()), 2),
            'aggregated_trend': self._detect_trend(total_daily_demand),
            'channel_breakdown': channel_stats,
            'top_channel': max(channel_stats.items(), key=lambda x: x[1]['total_demand'])[0],
            'demand_concentration': self._calculate_concentration(channel_stats)
        }
    
    def _detect_trend(self, data: List[float]) -> str:
        """Detect trend direction in demand data"""
        if len(data) < 2:
            return "INSUFFICIENT_DATA"
        
        data_array = np.array(data)
        if len(data) >= 3:
            # Use linear regression to detect trend
            x = np.arange(len(data))
            slope = np.polyfit(x, data_array, 1)[0]
            
            if slope > 0.05:
                return "INCREASING"
            elif slope < -0.05:
                return "DECREASING"
            else:
                return "STABLE"
        else:
            # Simple comparison for short data
            if data[-1] > data[0]:
                return "INCREASING"
            elif data[-1] < data[0]:
                return "DECREASING"
            else:
                return "STABLE"
    
    def _calculate_concentration(self, channel_stats: Dict) -> str:
        """Calculate demand concentration (Herfindahl index)"""
        contributions = [v['contribution_pct'] / 100 for v in channel_stats.values()]
        hhi = sum(c**2 for c in contributions)
        
        if hhi > 0.5:
            return "HIGH (single channel dominance)"
        elif hhi > 0.25:
            return "MODERATE (some channel dependency)"
        else:
            return "LOW (well distributed)"
    
    def detect_demand_anomalies(
        self,
        daily_demand: List[float],
        sensitivity: float = 2.0,
        lookback_days: int = 30
    ) -> Dict:
        """
        Detect unusual demand patterns using statistical methods
        
        Args:
            daily_demand: List of daily demand values
            sensitivity: Z-score threshold (2.0 = 95% normal, 3.0 = 99.7% normal)
            lookback_days: Days to analyze
        
        Returns:
            Anomaly detection results with severity levels
        """
        if len(daily_demand) < 7:
            return {'error': 'Insufficient data for anomaly detection'}
        
        demand_array = np.array(daily_demand[-lookback_days:])
        
        # Calculate baseline statistics
        mean = np.mean(demand_array)
        std = np.std(demand_array)
        
        # Identify anomalies
        anomalies = []
        for i, value in enumerate(demand_array):
            if std > 0:
                z_score = abs((value - mean) / std)
            else:
                z_score = 0
            
            if z_score > sensitivity:
                severity = "HIGH" if z_score > 3.0 else "MEDIUM"
                anomalies.append({
                    'date_offset': i - len(demand_array),
                    'actual_demand': round(float(value), 2),
                    'expected_demand': round(float(mean), 2),
                    'deviation_pct': round(float((value - mean) / mean * 100), 1) if mean > 0 else 0,
                    'z_score': round(float(z_score), 2),
                    'severity': severity
                })
        
        # Overall anomaly level
        if len(anomalies) > 3:
            overall_status = "HIGH"
            status_message = f"Detected {len(anomalies)} unusual demand spikes"
        elif len(anomalies) > 0:
            overall_status = "MEDIUM"
            status_message = f"Detected {len(anomalies)} demand anomalies"
        else:
            overall_status = "NORMAL"
            status_message = "Demand pattern is normal"
        
        return {
            'analysis_period_days': len(demand_array),
            'baseline_mean': round(float(mean), 2),
            'baseline_std': round(float(std), 2),
            'sensitivity_threshold': sensitivity,
            'anomalies_detected': len(anomalies),
            'overall_status': overall_status,
            'status_message': status_message,
            'anomalies': anomalies,
            'recommendation': self._get_anomaly_recommendation(overall_status, anomalies)
        }
    
    def _get_anomaly_recommendation(self, status: str, anomalies: List) -> str:
        """Generate anomaly response recommendation"""
        if status == "HIGH":
            if any(a['severity'] == "HIGH" for a in anomalies):
                return "Investigate cause - could be promotional campaign, market event, or supply issue"
            else:
                return "Monitor closely - unusual demand may indicate new trend"
        elif status == "MEDIUM":
            return "Adjust safety stock and monitor for pattern changes"
        else:
            return "Demand stable - maintain current inventory policy"
    
    def detect_trend_acceleration(
        self,
        daily_demand: List[float],
        window_size: int = 7
    ) -> Dict:
        """
        Detect if demand trend is accelerating or decelerating
        
        Args:
            daily_demand: List of daily demand values
            window_size: Window for moving average (days)
        
        Returns:
            Trend acceleration analysis
        """
        if len(daily_demand) < window_size * 2:
            return {'error': 'Insufficient data for trend analysis'}
        
        demand_array = np.array(daily_demand)
        
        # Calculate moving averages
        ma1 = pd.Series(demand_array).rolling(window=window_size).mean().values
        ma2 = pd.Series(demand_array).rolling(window=window_size*2).mean().values
        
        # Get recent values (avoid NaN)
        recent_ma1 = ma1[~np.isnan(ma1)][-10:]
        recent_ma2 = ma2[~np.isnan(ma2)][-10:]
        
        if len(recent_ma1) < 2 or len(recent_ma2) < 2:
            return {'error': 'Insufficient valid data'}
        
        # Calculate acceleration (second derivative)
        trend_recent = recent_ma1[-1] - recent_ma2[-1]
        trend_previous = recent_ma1[-5] - recent_ma2[-5] if len(recent_ma1) >= 5 else recent_ma1[-1] - recent_ma2[-1]
        
        acceleration = trend_recent - trend_previous
        
        # Classify
        if abs(acceleration) < recent_ma2[-1] * 0.02:
            trend_status = "STABLE"
        elif acceleration > 0:
            trend_status = "ACCELERATING"
        else:
            trend_status = "DECELERATING"
        
        # Forecast next period
        if trend_status == "ACCELERATING":
            forecast_multiplier = 1.05
            forecast_message = "Demand accelerating - may need increased orders"
        elif trend_status == "DECELERATING":
            forecast_multiplier = 0.95
            forecast_message = "Demand decelerating - consider reducing orders"
        else:
            forecast_multiplier = 1.0
            forecast_message = "Demand trend stable - maintain current strategy"
        
        next_period_forecast = recent_ma1[-1] * forecast_multiplier
        
        return {
            'current_7day_avg': round(float(recent_ma1[-1]), 2),
            'previous_7day_avg': round(float(recent_ma1[-5] if len(recent_ma1) >= 5 else recent_ma1[0]), 2),
            'trend_status': trend_status,
            'acceleration_value': round(float(acceleration), 2),
            'next_period_forecast': round(float(next_period_forecast), 2),
            'forecast_confidence': 'MEDIUM' if trend_status == "STABLE" else 'LOW',
            'recommendation': forecast_message
        }
    
    def track_promotional_impact(
        self,
        pre_promotion_demand: List[float],
        during_promotion_demand: List[float],
        post_promotion_demand: List[float] = None
    ) -> Dict:
        """
        Analyze impact of promotional campaigns on demand
        
        Args:
            pre_promotion_demand: Baseline demand before promotion
            during_promotion_demand: Demand during promotional period
            post_promotion_demand: Demand after promotion (optional)
        
        Returns:
            Promotional impact analysis
        """
        pre_array = np.array(pre_promotion_demand)
        during_array = np.array(during_promotion_demand)
        
        pre_avg = np.mean(pre_array)
        during_avg = np.mean(during_array)
        
        # Lift calculation
        lift_pct = ((during_avg - pre_avg) / pre_avg * 100) if pre_avg > 0 else 0
        
        # Total uplift
        total_uplift = (during_avg - pre_avg) * len(during_array)
        
        # Post-promotion analysis
        if post_promotion_demand:
            post_array = np.array(post_promotion_demand)
            post_avg = np.mean(post_array)
            
            # Carryover effect
            carryover = ((post_avg - pre_avg) / pre_avg * 100) if pre_avg > 0 else 0
            
            # Payback period (how long to recover excess inventory)
            excess_inventory = np.cumsum(during_array - pre_avg)[-1] if len(during_array) > 0 else 0
            if post_avg > pre_avg:
                payback_days = (excess_inventory / (post_avg - pre_avg)) if (post_avg - pre_avg) > 0 else 0
            else:
                payback_days = 0
            
            post_analysis = {
                'post_promotion_avg': round(float(post_avg), 2),
                'carryover_effect_pct': round(float(carryover), 2),
                'payback_period_days': round(float(payback_days), 1),
                'sustainable_lift': carryover > 0
            }
        else:
            post_analysis = None
        
        return {
            'promotion_impact': 'Promotional Campaign Analysis',
            'pre_promotion_avg': round(float(pre_avg), 2),
            'during_promotion_avg': round(float(during_avg), 2),
            'lift_percentage': round(float(lift_pct), 2),
            'total_uplift_units': round(float(total_uplift), 0),
            'pre_promotion_volume': round(float(pre_array.sum()), 0),
            'promotion_volume': round(float(during_array.sum()), 0),
            'volume_increase': round(float(during_array.sum() - pre_array.sum()), 0),
            'post_promotion_analysis': post_analysis,
            'roi_recommendation': self._calculate_promotion_roi(lift_pct, total_uplift)
        }
    
    def _calculate_promotion_roi(self, lift_pct: float, uplift_units: float) -> str:
        """Calculate promotion ROI"""
        # Assume promotion cost $500, margin $10/unit
        promotion_cost = 500
        margin_per_unit = 10
        margin_gained = uplift_units * margin_per_unit
        roi = ((margin_gained - promotion_cost) / promotion_cost * 100) if promotion_cost > 0 else 0
        
        if roi > 50:
            return f"HIGHLY EFFECTIVE: {roi:.0f}% ROI - Repeat this promotion"
        elif roi > 0:
            return f"EFFECTIVE: {roi:.0f}% ROI - Consider repeating with adjustments"
        else:
            return f"LOW RETURN: {roi:.0f}% ROI - Review promotion strategy"
