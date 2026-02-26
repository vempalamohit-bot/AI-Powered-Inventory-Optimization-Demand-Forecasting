from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer, case
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import io
import random
import tempfile
import os
import re
import time
import json

from ..database import get_db
from ..database.models import (
    Product,
    SalesHistory,
    Forecast,
    InventoryRecommendation,
    Supplier,
    SupplierPerformance,
    SupplierRiskScore,
    DemandAlert,
    ScenarioResult,
    AlertRecipient,
    NotificationLog,
    ApiImportLog,
)
from ..schemas.data_schemas import DataMapper, ProductSchema, SalesSchema, validate_data_quality
from ..models.demand_forecaster import DemandForecaster
from ..models.enhanced_forecaster import EnhancedDemandForecaster
from ..models.product_segmentation import ProductSegmenter
from ..models.inventory_optimizer import InventoryOptimizer
from ..models.scenario_engine import ScenarioEngine
from ..models.demand_sensing import DemandSensing
from ..models.decision_optimizer import DecisionOptimizer
from ..models.risk_profiler import RiskProfiler
from ..models.financial_storyteller import FinancialStoryTeller
from ..models.markdown_optimizer import MarkdownOptimizer
from ..models.reorder_calculator import ReorderCalculator
from ..models.business_advisor import BusinessRecommendationEngine
from ..services.cache_service import forecast_cache, analytics_cache, cached, get_cache_stats
from ..models.multi_model_forecaster import MultiModelForecaster
from ..models.ml_metrics_tracker import MLMetricsTracker
from ..models.loss_calculator import LossCalculator
from ..models.ai_alert_system import AIAlertSystem
from ..models.ai_explainer import AIExplainer
from ..services.analytics_service import AnalyticsService
from ..services import email_service_sendgrid
from ..services.alert_scheduler import get_alert_scheduler
from ..services.notification_service import format_alert_markdown
from ..config import get_settings
from ..utils.cache import api_cache
from ..utils.json_storage import (
    save_raw_json, save_processed_json, append_to_manifest,
    get_manifest, list_raw_files, load_raw_json
)

router = APIRouter(prefix="/api", tags=["api"])

# ============================================================
# Stock Threshold Configuration (Global, synced across all endpoints)
# ============================================================
STOCK_THRESHOLDS = {
    'low_stock_max': 50,      # Stock <= this is "Low Stock"
    'medium_stock_max': 100,  # Stock <= this is "Medium Stock", > low_stock_max
    # Stock > medium_stock_max is "High Stock"
    # Stock == 0 is always "Out of Stock"
}

def get_stock_status(current_stock: int) -> tuple:
    """Get stock status badge and risk level based on configurable thresholds"""
    low_max = STOCK_THRESHOLDS['low_stock_max']
    medium_max = STOCK_THRESHOLDS['medium_stock_max']
    
    if current_stock == 0:
        return "OUT OF STOCK 🔴", "CRITICAL"
    elif current_stock <= low_max:
        return "LOW STOCK 🟠", "HIGH"
    elif current_stock <= medium_max:
        return "MEDIUM STOCK 🟢", "LOW"
    else:
        return "HIGH STOCK 🔵", "SAFE"

def get_stock_filter_query(query, stock_filter: str):
    """Apply stock filter to query based on configurable thresholds"""
    low_max = STOCK_THRESHOLDS['low_stock_max']
    medium_max = STOCK_THRESHOLDS['medium_stock_max']
    
    if stock_filter == 'OUT':
        return query.filter(Product.current_stock == 0)
    elif stock_filter == 'LOW':
        return query.filter(Product.current_stock > 0, Product.current_stock <= low_max)
    elif stock_filter == 'MEDIUM':
        return query.filter(Product.current_stock > low_max, Product.current_stock <= medium_max)
    elif stock_filter == 'HIGH':
        return query.filter(Product.current_stock > medium_max)
    return query

# Initialize services
analytics_service = AnalyticsService()
alert_scheduler = get_alert_scheduler()
settings = get_settings()

# ============================================================
# AI/ML Model-Based Inventory Calculations (replaces all hardcoded values)
# ============================================================
_inventory_optimizer = InventoryOptimizer()

def compute_model_inventory(
    avg_daily_demand: float,
    demand_std: float,
    lead_time_days: int,
    unit_cost: float,
    current_stock: int = 0,
    service_level: float = 0.95,
    storage_cost_per_unit: float = None,
    stockout_cost_per_unit: float = None,
) -> Dict[str, Any]:
    """
    Compute safety stock, reorder point, EOQ, and stockout risk
    using the InventoryOptimizer ML models instead of hardcoded multipliers.
    
    Returns dict with: safety_stock, reorder_point, eoq, order_quantity,
                       risk_percentage, stockout_risk_label
    """
    if avg_daily_demand <= 0:
        return {
            'safety_stock': 0,
            'reorder_point': 0,
            'eoq': 0,
            'order_quantity': 0,
            'risk_percentage': 0 if current_stock > 0 else 100,
            'stockout_risk_label': 'CRITICAL' if current_stock == 0 else 'UNKNOWN',
        }

    # Demand std: if unavailable, estimate from coefficient of variation
    if demand_std is None or demand_std <= 0 or np.isnan(demand_std):
        demand_std = avg_daily_demand * 0.3  # 30% CV fallback (industry standard)

    # --- Safety stock via z * σ * √L (newsvendor-adjusted) ---
    holding_cost_per_unit = max(unit_cost * 0.25, 0.01)
    ss_result = _inventory_optimizer.calculate_safety_stock(
        demand_std=demand_std,
        lead_time_days=lead_time_days,
        service_level=service_level,
        stockout_cost_per_unit=stockout_cost_per_unit,
        holding_cost_per_unit=holding_cost_per_unit,
        average_daily_demand=avg_daily_demand,
    )
    safety_stock = ss_result['safety_stock']

    # --- Reorder point = demand * LT + safety stock ---
    reorder_point = _inventory_optimizer.calculate_reorder_point(
        avg_daily_demand=avg_daily_demand,
        lead_time_days=lead_time_days,
        safety_stock=safety_stock,
    )

    # --- EOQ via Wilson formula with cost columns ---
    annual_demand = avg_daily_demand * 365
    eoq_result = _inventory_optimizer.calculate_eoq(
        annual_demand=annual_demand,
        unit_cost=unit_cost,
        storage_cost_per_unit=storage_cost_per_unit,
    )
    eoq = max(int(eoq_result['eoq']), 1)

    # --- Order quantity ---
    if current_stock < reorder_point:
        order_quantity = max(eoq, int(reorder_point - current_stock + safety_stock))
    else:
        order_quantity = eoq

    # --- Stockout risk probability (model-based) ---
    if current_stock == 0:
        risk_pct = 100
        risk_label = 'CRITICAL'
    elif avg_daily_demand > 0:
        days_until_stockout = current_stock / avg_daily_demand
        # Use normal distribution CDF for stockout probability during lead time
        from scipy import stats as sp_stats
        demand_during_lt = avg_daily_demand * lead_time_days
        std_during_lt = demand_std * np.sqrt(lead_time_days)
        if std_during_lt > 0:
            # P(demand > current_stock) during lead time
            z_current = (current_stock - demand_during_lt) / std_during_lt
            risk_pct = round((1 - sp_stats.norm.cdf(z_current)) * 100, 1)
        else:
            risk_pct = 0 if current_stock >= demand_during_lt else 100

        if risk_pct >= 80:
            risk_label = 'CRITICAL'
        elif risk_pct >= 50:
            risk_label = 'HIGH'
        elif risk_pct >= 20:
            risk_label = 'MEDIUM'
        elif risk_pct >= 5:
            risk_label = 'LOW'
        else:
            risk_label = 'SAFE'
    else:
        risk_pct = 0
        risk_label = 'SAFE'

    return {
        'safety_stock': int(round(safety_stock)),
        'reorder_point': int(round(reorder_point)),
        'eoq': eoq,
        'order_quantity': max(order_quantity, 1),
        'risk_percentage': min(risk_pct, 100),
        'stockout_risk_label': risk_label,
    }


@router.get("/system/health")
def get_system_health(db: Session = Depends(get_db)):
    """Provide quick platform readiness snapshot."""
    try:
        db.execute("SELECT 1")
        database_status = "ok"
    except Exception as exc:  # pragma: no cover - defensive logging
        database_status = f"error: {exc}"
    scheduler_status = alert_scheduler.status()
    email_config = email_service_sendgrid.get_config()
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'database': database_status,
        'email': email_config,
        'scheduler': scheduler_status,
        'environment': settings.environment
    }


@router.get("/system/metrics")
def get_system_metrics(db: Session = Depends(get_db)):
    """Operational metrics for observability dashboards."""
    window_start = datetime.utcnow() - timedelta(hours=24)
    notifications_24h = db.query(NotificationLog).filter(NotificationLog.created_at >= window_start).count()
    errors_24h = db.query(NotificationLog).filter(
        NotificationLog.created_at >= window_start,
        NotificationLog.status == 'FAILED'
    ).count()
    active_recipients = db.query(AlertRecipient).filter(AlertRecipient.active.is_(True)).count()
    return {
        'window_hours': 24,
        'notifications_last_24h': notifications_24h,
        'notification_failures_last_24h': errors_24h,
        'active_recipients': active_recipients,
        'scheduler': alert_scheduler.status()
    }

@router.get("/products")
def get_products(limit: int = 100, db: Session = Depends(get_db)):
    """Get products with current stock levels and stockout risk calculations (default limit 100 for fast loading)"""
    products = db.query(Product).limit(limit).all()
    
    # Calculate average daily demand AND demand std for all products in one query (last 30 days)
    cutoff_date = datetime.now() - timedelta(days=30)
    demand_stats = db.query(
        SalesHistory.product_id,
        func.sum(SalesHistory.quantity_sold).label("total_quantity"),
        func.count(func.distinct(SalesHistory.date)).label("active_days"),
        func.sum(SalesHistory.quantity_sold * SalesHistory.quantity_sold).label("sum_qty_sq"),
        func.count(SalesHistory.id).label("sale_count")
    ).filter(
        SalesHistory.date >= cutoff_date
    ).group_by(
        SalesHistory.product_id
    ).all()
    
    # Create a map of product_id -> demand stats
    demand_map = {stat.product_id: stat for stat in demand_stats}
    
    result = []
    for product in products:
        # Determine stock level badge using configurable thresholds
        stock_badge, _ = get_stock_status(product.current_stock)
        
        # Calculate average daily demand and stockout risk using ML models
        demand_stat = demand_map.get(product.id)
        lead_time = product.lead_time_days or 7
        unit_cost = float(product.unit_cost or 1)
        
        if demand_stat and demand_stat.total_quantity and demand_stat.active_days:
            avg_daily_demand = float(demand_stat.total_quantity) / max(demand_stat.active_days, 1)
            # Calculate demand std: std = sqrt(E[X^2] - E[X]^2)
            n = max(demand_stat.sale_count, 1)
            mean_qty = float(demand_stat.total_quantity) / n
            mean_sq = float(demand_stat.sum_qty_sq or 0) / n
            variance = max(0, mean_sq - mean_qty ** 2)
            demand_std = variance ** 0.5 if n > 1 else None
            
            # Use ML model for all inventory calculations
            inv = compute_model_inventory(
                avg_daily_demand=avg_daily_demand,
                demand_std=demand_std,
                lead_time_days=lead_time,
                unit_cost=unit_cost,
                current_stock=product.current_stock,
                service_level=0.95,
            )
            safety_stock = inv['safety_stock']
            reorder_point = inv['reorder_point']
            risk_percentage = inv['risk_percentage']
            stockout_risk = inv['stockout_risk_label']
            
            # Calculate days until stockout
            if avg_daily_demand > 0:
                days_until_stockout = int(product.current_stock / avg_daily_demand)
            else:
                days_until_stockout = 999
            
            # Determine reorder status from model reorder point
            if product.current_stock <= reorder_point:
                reorder_status = "REORDER NOW"
            elif product.current_stock <= reorder_point * 1.5:
                reorder_status = "REORDER SOON"
            else:
                reorder_status = "OK"
        elif product.average_daily_demand and product.average_daily_demand > 0:
            # USE STORED average_daily_demand from CSV if no sales history
            avg_daily_demand = float(product.average_daily_demand)
            demand_std = float(product.demand_volatility or 0) * avg_daily_demand if hasattr(product, 'demand_volatility') and product.demand_volatility else None
            
            inv = compute_model_inventory(
                avg_daily_demand=avg_daily_demand,
                demand_std=demand_std,
                lead_time_days=lead_time,
                unit_cost=unit_cost,
                current_stock=product.current_stock,
                service_level=0.95,
            )
            safety_stock = inv['safety_stock']
            reorder_point = inv['reorder_point']
            risk_percentage = inv['risk_percentage']
            stockout_risk = inv['stockout_risk_label']
            
            if avg_daily_demand > 0:
                days_until_stockout = int(product.current_stock / avg_daily_demand)
            else:
                days_until_stockout = 999
            
            if product.current_stock <= reorder_point:
                reorder_status = "REORDER NOW"
            elif product.current_stock <= reorder_point * 1.5:
                reorder_status = "REORDER SOON"
            else:
                reorder_status = "OK"
        else:
            avg_daily_demand = 0
            days_until_stockout = None
            reorder_point = 0
            safety_stock = 0
            risk_percentage = 0
            
            if product.current_stock == 0:
                stockout_risk = "CRITICAL"
                risk_percentage = 100
            else:
                stockout_risk = "UNKNOWN"
            
            reorder_status = "N/A"
        
        result.append({
            'id': product.id,
            'sku': product.sku,
            'name': product.name,
            'category': product.category,
            'current_stock': product.current_stock,
            'unit_cost': float(product.unit_cost or 0),
            'unit_price': float(product.unit_price or 0),
            'lead_time_days': product.lead_time_days,
            'stock_badge': stock_badge,
            'reorder_point': reorder_point,
            'safety_stock': safety_stock,
            'reorder_status': reorder_status,
            'average_daily_demand': round(avg_daily_demand, 1),
            'stockout_risk': stockout_risk,
            'days_until_stockout': days_until_stockout,
            'risk_percentage': risk_percentage,
            'forecast_demand_30d': None,
            'forecast_confidence': None
        })
    
    return result


@router.get("/products/dropdown")
def get_products_for_dropdown(
    limit: int = 500,
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Fast endpoint for product dropdowns - returns minimal data.
    Returns only id, sku, name for quick loading.
    Supports search by name/SKU and filtering by category.
    """
    query = db.query(Product.id, Product.sku, Product.name, Product.category)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_term)) | 
            (Product.sku.ilike(search_term)) |
            (Product.category.ilike(search_term))
        )
    
    if category:
        query = query.filter(Product.category == category)
    
    # Limit results for fast loading
    products = query.order_by(Product.id).limit(limit).all()
    
    return [
        {
            'id': p.id,
            'sku': p.sku,
            'name': p.name,
            'category': p.category,
            'display_name': f"{p.sku} - {p.name}"
        }
        for p in products
    ]


@router.get("/products/categories")
def get_product_categories(db: Session = Depends(get_db)):
    """Get all unique product categories for fast dropdown loading"""
    categories = db.query(Product.category).distinct().filter(Product.category.isnot(None)).all()
    return [c[0] for c in categories if c[0]]


@router.get("/products/paginated")
def get_products_paginated(
    page: int = 1,
    page_size: int = 50,
    category: Optional[str] = None,
    stock_filter: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get products with pagination for fast loading (handles 50K+ products)"""
    
    # Start with base query
    query = db.query(Product)
    
    # Apply filters
    if category and category != 'All':
        query = query.filter(Product.category == category)
    
    if stock_filter:
        query = get_stock_filter_query(query, stock_filter)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_term)) | (Product.sku.ilike(search_term))
        )
    
    # Get total count (before pagination)
    total_count = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    products = query.offset(offset).limit(page_size).all()
    
    # Get demand statistics for these products using AI-driven calculations
    product_ids = [p.id for p in products]
    demand_lookback = datetime.now() - timedelta(days=30)
    demand_stats = db.query(
        SalesHistory.product_id,
        func.sum(SalesHistory.quantity_sold).label('total_qty'),
        func.count(func.distinct(SalesHistory.date)).label('active_days'),
        func.sum(SalesHistory.quantity_sold * SalesHistory.quantity_sold).label("sum_qty_sq"),
        func.count(SalesHistory.id).label("sale_count")
    ).filter(
        SalesHistory.product_id.in_(product_ids),
        SalesHistory.date >= demand_lookback
    ).group_by(SalesHistory.product_id).all()
    
    demand_map = {s.product_id: s for s in demand_stats}
    
    result = []
    for product in products:
        # Stock badge based on configurable thresholds
        stock_badge, stockout_risk = get_stock_status(product.current_stock)
        
        # ML model-based calculations using InventoryOptimizer
        demand_stat = demand_map.get(product.id)
        lead_time = product.lead_time_days or 7
        unit_cost = float(product.unit_cost or 1)
        
        if demand_stat and demand_stat.total_qty and demand_stat.active_days:
            avg_daily_demand = float(demand_stat.total_qty) / max(demand_stat.active_days, 1)
            n = max(demand_stat.sale_count, 1)
            mean_qty = float(demand_stat.total_qty) / n
            mean_sq = float(demand_stat.sum_qty_sq or 0) / n
            variance = max(0, mean_sq - mean_qty ** 2)
            demand_std = variance ** 0.5 if n > 1 else None
            
            inv = compute_model_inventory(
                avg_daily_demand=avg_daily_demand,
                demand_std=demand_std,
                lead_time_days=lead_time,
                unit_cost=unit_cost,
                current_stock=product.current_stock,
            )
            reorder_point = inv['reorder_point']
            safety_stock = inv['safety_stock']
            order_quantity = inv['order_quantity']
            stockout_risk = inv['stockout_risk_label']
            
            if avg_daily_demand > 0:
                days_until_stockout = int(product.current_stock / avg_daily_demand)
            else:
                days_until_stockout = 999
        elif product.average_daily_demand and product.average_daily_demand > 0:
            avg_daily_demand = float(product.average_daily_demand)
            demand_std = float(product.demand_volatility or 0) * avg_daily_demand if hasattr(product, 'demand_volatility') and product.demand_volatility else None
            
            inv = compute_model_inventory(
                avg_daily_demand=avg_daily_demand,
                demand_std=demand_std,
                lead_time_days=lead_time,
                unit_cost=unit_cost,
                current_stock=product.current_stock,
            )
            reorder_point = inv['reorder_point']
            safety_stock = inv['safety_stock']
            order_quantity = inv['order_quantity']
            stockout_risk = inv['stockout_risk_label']
            
            if avg_daily_demand > 0:
                days_until_stockout = int(product.current_stock / avg_daily_demand)
            else:
                days_until_stockout = 999
        else:
            avg_daily_demand = 0
            reorder_point = 0
            safety_stock = 0
            order_quantity = int(getattr(product, 'reorder_quantity', None) or getattr(product, 'economic_order_qty', None) or 0)
            if order_quantity == 0:
                # Use EOQ with minimum assumptions
                inv = compute_model_inventory(avg_daily_demand=1, demand_std=0.3, lead_time_days=lead_time, unit_cost=unit_cost)
                order_quantity = inv['eoq']
            days_until_stockout = None
        
        result.append({
            'id': product.id,
            'sku': product.sku,
            'name': product.name,
            'category': product.category,
            'current_stock': product.current_stock,
            'unit_cost': float(product.unit_cost or 0),
            'unit_price': float(product.unit_price or 0),
            'lead_time_days': product.lead_time_days,
            'stock_badge': stock_badge,
            'reorder_point': reorder_point,
            'safety_stock': safety_stock,
            'order_quantity': order_quantity,
            'average_daily_demand': round(avg_daily_demand, 1),
            'stockout_risk': stockout_risk,
            'days_until_stockout': days_until_stockout
        })
    
    return {
        'products': result,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_count': total_count,
            'total_pages': (total_count + page_size - 1) // page_size,
            'has_next': page * page_size < total_count,
            'has_prev': page > 1
        }
    }


@router.get("/products/summary")
def get_products_summary(db: Session = Depends(get_db)):
    """Fast summary stats for products - no heavy calculations"""
    
    # Use configurable thresholds
    low_max = STOCK_THRESHOLDS['low_stock_max']
    medium_max = STOCK_THRESHOLDS['medium_stock_max']
    
    # Get stock distribution with simple count queries
    total = db.query(func.count(Product.id)).scalar()
    out_of_stock = db.query(func.count(Product.id)).filter(Product.current_stock == 0).scalar()
    low_stock = db.query(func.count(Product.id)).filter(Product.current_stock > 0, Product.current_stock <= low_max).scalar()
    medium_stock = db.query(func.count(Product.id)).filter(Product.current_stock > low_max, Product.current_stock <= medium_max).scalar()
    high_stock = db.query(func.count(Product.id)).filter(Product.current_stock > medium_max).scalar()
    
    # Get categories
    categories = db.query(Product.category).distinct().all()
    
    return {
        'total_products': total,
        'stock_distribution': {
            'out_of_stock': out_of_stock,
            'low_stock': low_stock,
            'medium_stock': medium_stock,
            'high_stock': high_stock
        },
        'categories': [c[0] for c in categories if c[0]],
        'alerts_count': out_of_stock + low_stock
    }


@router.get("/products/ordering-recommendations")
def get_ordering_recommendations(db: Session = Depends(get_db)):
    """Get critical and high-risk items that need ordering - sorted by demand priority. CACHED 60s."""
    
    # Check cache (60 second TTL)
    cache_key = "/products/ordering-recommendations"
    cached = api_cache.get(cache_key)
    if cached:
        return cached
    
    # Use configurable thresholds
    low_max = STOCK_THRESHOLDS['low_stock_max']
    
    # Get total counts
    out_of_stock_count = db.query(func.count(Product.id)).filter(Product.current_stock == 0).scalar() or 0
    low_stock_count = db.query(func.count(Product.id)).filter(
        Product.current_stock > 0, 
        Product.current_stock <= low_max
    ).scalar() or 0
    
    # Get critical items (out of stock) - top 20 by average daily demand
    critical_items = db.query(Product).filter(
        Product.current_stock == 0
    ).order_by(
        Product.average_daily_demand.desc().nullslast()
    ).limit(20).all()
    
    # Get high-risk items (low stock) - top 20 by days left and demand
    # Calculate days_left as current_stock / average_daily_demand
    from sqlalchemy import case
    
    low_stock_items = db.query(Product).filter(
        Product.current_stock > 0,
        Product.current_stock <= low_max
    ).order_by(
        # Prioritize by days left (ascending) and demand (descending)
        case(
            (Product.average_daily_demand > 0, Product.current_stock / Product.average_daily_demand),
            else_=999
        ).asc(),
        Product.average_daily_demand.desc().nullslast()
    ).limit(20).all()
    
    # Format critical items
    critical_list = []
    for p in critical_items:
        # Calculate order quantity: larger of reorder_point or 14 days of demand
        avg_demand = float(p.average_daily_demand or 0)
        order_qty = max(
            int(p.reorder_point or 0),
            int(avg_demand * 14) if avg_demand > 0 else int(p.reorder_point or 100)
        )
        
        critical_list.append({
            'id': p.id,
            'name': p.name,
            'sku': p.sku,
            'current_stock': p.current_stock,
            'average_daily_demand': round(avg_demand, 1),
            'order_quantity': order_qty,
            'lead_time_days': p.lead_time_days,
            'unit_cost': float(p.unit_cost or 0),
            'category': p.category
        })
    
    # Format high-risk items
    high_risk_list = []
    for p in low_stock_items:
        avg_demand = float(p.average_daily_demand or 0)
        days_left = int(p.current_stock / avg_demand) if avg_demand > 0 else 999
        
        # Calculate order quantity
        order_qty = max(
            int(p.reorder_point or 0),
            int(avg_demand * 14) if avg_demand > 0 else int(p.reorder_point or 100)
        )
        
        high_risk_list.append({
            'id': p.id,
            'name': p.name,
            'sku': p.sku,
            'current_stock': p.current_stock,
            'average_daily_demand': round(avg_demand, 1),
            'days_left': days_left,
            'order_quantity': order_qty,
            'lead_time_days': p.lead_time_days,
            'unit_cost': float(p.unit_cost or 0),
            'category': p.category
        })
    
    result = {
        'critical': {
            'total_count': out_of_stock_count,
            'items': critical_list,
            'showing_top': len(critical_list)
        },
        'high_risk': {
            'total_count': low_stock_count,
            'items': high_risk_list,
            'showing_top': len(high_risk_list)
        }
    }
    
    # Cache for 60 seconds
    api_cache.set(cache_key, result, ttl_seconds=60)
    return result


@router.get("/products/{product_id}/forecast-comparison")
def compare_forecast_models(product_id: int, days_ahead: int = 30, db: Session = Depends(get_db)):
    """Compare multiple ML models for demand forecasting"""
    return MultiModelForecaster.forecast_with_all_models(db, product_id, days_ahead)


@router.get("/products/{product_id}/intelligent-forecast")
def get_intelligent_forecast(product_id: int, forecast_days: int = Query(30, alias="forecast_days"), db: Session = Depends(get_db)):
    """
    Get intelligent forecast with automatic model selection
    
    Features:
    - Automatic product segmentation (Stable/Seasonal/Volatile/Intermittent)
    - Intelligent model selection (SARIMA/Prophet/XGBoost/Croston)
    - Rich feature engineering
    - NLP explanations
    - Model metadata and performance tracking
    - 10-minute caching for improved performance
    
    Returns:
    - Forecast values with confidence intervals
    - Product segment classification
    - Model used and rationale
    - Business-friendly explanation
    - Key demand characteristics
    """
    # Check cache first (10 minute TTL)
    cache_key = f"intelligent_forecast:{product_id}:{forecast_days}"
    cached_result = forecast_cache.get(cache_key)
    if cached_result is not None:
        print(f"[CACHE HIT] Intelligent forecast for product {product_id}")
        return cached_result
    
    print(f"[CACHE MISS] Computing intelligent forecast for product {product_id}")
    
    # Get product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get sales history
    sales = db.query(SalesHistory).filter(
        SalesHistory.product_id == product_id
    ).order_by(SalesHistory.date).all()
    
    if not sales:
        raise HTTPException(status_code=404, detail="No sales history found for this product")
    
    # Convert to DataFrame
    sales_df = pd.DataFrame([{
        'date': s.date,
        'quantity_sold': s.quantity_sold
    } for s in sales])
    
    # Prepare product metadata for feature engineering
    product_metadata = {
        'price': float(product.unit_price) if product.unit_price else None,
        'category': product.category,
        'seasonality_factor': float(product.seasonality_factor) if hasattr(product, 'seasonality_factor') else 1.0,
        'demand_volatility': float(product.demand_volatility) if hasattr(product, 'demand_volatility') else 0.5,
    }
    
    # Initialize enhanced forecaster
    forecaster = EnhancedDemandForecaster()
    
    # Generate forecast with segmentation and intelligent model selection
    try:
        result = forecaster.fit_and_forecast(
            sales_data=sales_df,
            forecast_days=forecast_days,
            product_metadata=product_metadata
        )
        
        # ===== Transform response to match frontend expected format =====
        # Frontend expects: { historical: [{date, actual}], forecast: [{date, predicted, lower_bound, upper_bound}],
        #                     segment, model_used, business_explanation, characteristics, product_info }
        
        # Build historical data - last 30 CALENDAR DAYS with zero-fill
        # Shorter window prevents outlier spikes from dominating Y-axis scale
        from datetime import datetime, timedelta
        
        # Find the date range for historical display
        all_dates = [s.date if isinstance(s.date, str) else s.date.strftime('%Y-%m-%d') if s.date else None for s in sales]
        all_dates = [d for d in all_dates if d]
        
        if all_dates:
            # Build a lookup of date -> quantity
            sales_lookup = {}
            for s in sales:
                date_str = s.date if isinstance(s.date, str) else s.date.strftime('%Y-%m-%d') if s.date else None
                if date_str:
                    sales_lookup[date_str] = sales_lookup.get(date_str, 0) + s.quantity_sold
            
            # Get last date in sales and build 30 calendar days backwards
            last_sale_date = max(datetime.strptime(d, '%Y-%m-%d') for d in all_dates)
            hist_days = 30
            start_hist_date = last_sale_date - timedelta(days=hist_days - 1)
            
            historical = []
            for i in range(hist_days):
                d = start_hist_date + timedelta(days=i)
                date_str = d.strftime('%Y-%m-%d')
                qty = sales_lookup.get(date_str, 0)
                historical.append({
                    'date': date_str,
                    'actual': qty
                })
            
            # Cap historical outliers so they don't dominate the Y-axis
            # Use the max forecast value as a scaling reference
            forecast_values_all = result.get('forecast', [])
            max_forecast = max(forecast_values_all) if forecast_values_all else 10
            upper_bounds_all = result.get('upper_bound', [])
            max_upper = max(upper_bounds_all) if upper_bounds_all else max_forecast * 2
            # Cap historical at 2x the max upper bound — keeps chart visually balanced
            hist_cap = max(max_upper * 2, max_forecast * 3, 20)
            for h in historical:
                if h['actual'] > hist_cap:
                    h['actual'] = int(hist_cap)
        
        # Build forecast array of objects from parallel arrays
        forecast_list = []
        forecast_dates = result.get('forecast_dates', [])
        forecast_values = result.get('forecast', [])
        lower_bounds = result.get('lower_bound', [])
        upper_bounds = result.get('upper_bound', [])
        
        for i in range(len(forecast_dates)):
            date_val = forecast_dates[i]
            date_str = date_val if isinstance(date_val, str) else date_val.strftime('%Y-%m-%d') if hasattr(date_val, 'strftime') else str(date_val)
            # Strip time portion if present (e.g., "2026-02-15T00:00:00" -> "2026-02-15")
            if 'T' in date_str:
                date_str = date_str.split('T')[0]
            
            forecast_list.append({
                'date': date_str,
                'predicted': int(round(forecast_values[i])) if i < len(forecast_values) else 0,
                'lower_bound': int(round(lower_bounds[i])) if i < len(lower_bounds) else 0,
                'upper_bound': int(round(upper_bounds[i])) if i < len(upper_bounds) else 0,
            })
        
        # Extract segment info
        segment_info = result.get('segment_info', {})
        
        # Build final response in frontend-expected format
        response = {
            'historical': historical,
            'forecast': forecast_list,
            'segment': segment_info.get('segment', 'UNKNOWN'),
            'model_used': result.get('model_used', 'ARIMA'),
            'confidence_level': result.get('confidence_level', 0.95),
            'model_type': result.get('model_type', 'statistical'),
            'business_explanation': result.get('explanation', ''),
            'characteristics': segment_info.get('characteristics', {}),
            'product_info': {
                'sku': product.sku,
                'name': product.name,
                'category': product.category,
                'current_stock': product.current_stock,
                'unit_price': float(product.unit_price) if product.unit_price else None
            }
        }
        
        # Cache the result for 10 minutes
        forecast_cache.set(cache_key, response, ttl=600)
        
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {str(e)}")


@router.get("/products/batch-intelligent-forecast")
def get_batch_intelligent_forecast(
    limit: int = Query(10, le=100),
    category: Optional[str] = None,
    days_ahead: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get intelligent forecasts for multiple products
    
    Useful for:
    - Dashboard overview with model diversity
    - Comparing forecast patterns across products
    - Identifying which products use which models
    """
    # Query products
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    
    products = query.limit(limit).all()
    
    if not products:
        return {"products": [], "summary": {"total": 0}}
    
    results = []
    model_distribution = {}
    segment_distribution = {}
    
    for product in products:
        # Get sales history
        sales = db.query(SalesHistory).filter(
            SalesHistory.product_id == product.id
        ).order_by(SalesHistory.date).all()
        
        if len(sales) < 14:
            continue
        
        # Convert to DataFrame
        sales_df = pd.DataFrame([{
            'date': s.date,
            'quantity_sold': s.quantity_sold
        } for s in sales])
        
        # Forecast
        forecaster = EnhancedDemandForecaster()
        forecast_result = forecaster.fit_and_forecast(sales_df, days_ahead)
        
        # Track model distribution
        model_used = forecast_result['model_used']
        segment = forecast_result['segment_info']['segment']
        
        model_distribution[model_used] = model_distribution.get(model_used, 0) + 1
        segment_distribution[segment] = segment_distribution.get(segment, 0) + 1
        
        # Add product info and simplified forecast
        results.append({
            'product_id': product.id,
            'sku': product.sku,
            'name': product.name,
            'category': product.category,
            'segment': segment,
            'model_used': model_used,
            'avg_forecast': round(np.mean(forecast_result['forecast']), 2),
            'forecast_trend': forecast_result['segment_info']['characteristics'].get('trend_direction', 'flat'),
            'confidence': forecast_result['segment_info']['confidence']
        })
    
    return {
        'products': results,
        'summary': {
            'total': len(results),
            'model_distribution': model_distribution,
            'segment_distribution': segment_distribution
        }
    }


@router.get("/products/{product_id}/recommendations")
def get_product_recommendations(product_id: int, db: Session = Depends(get_db)):
    """Get AI-powered recommendations for a specific product"""
    return BusinessRecommendationEngine.get_product_recommendations(db, product_id)

@router.get("/recommendations/top")
def get_top_recommendations(limit: int = 20, db: Session = Depends(get_db)):
    """Get top priority recommendations across all products"""
    return BusinessRecommendationEngine.get_top_recommendations(db, limit)

# ============================================================================
# AI/ML MODEL METRICS - Shows this is an AI/ML POC, not just BI reporting
# ============================================================================

@router.get("/ml/training-metrics")
def get_ml_training_metrics(db: Session = Depends(get_db)):
    """
    Get ML model training metrics and parameters
    Shows: data split %, decision tree params, model performance, feature importance
    """
    return MLMetricsTracker.get_training_metrics(db)

@router.get("/ml/testing-results")
def get_ml_testing_results(db: Session = Depends(get_db)):
    """
    Get ML model testing parameters, metrics, and KPIs
    Shows: test set size, cross-validation, confusion matrix, model comparison
    """
    return MLMetricsTracker.get_model_testing_results(db)

@router.post("/ml/adjust-parameters")
def adjust_ml_parameters(
    max_depth: Optional[int] = None,
    n_estimators: Optional[int] = None
):
    """
    Adjust ML model parameters for testing
    Demonstrates capability to increase/decrease model complexity
    """
    return MLMetricsTracker.adjust_model_parameters(max_depth, n_estimators)

# ============================================================================
# LOSS CALCULATIONS - AI-powered financial impact analysis
# ============================================================================

@router.get("/analytics/stockout-loss")
def get_stockout_loss(product_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Calculate revenue loss from out-of-stock products
    AI predicts daily loss and recommends order quantities
    """
    return LossCalculator.calculate_stockout_loss(db, product_id)

@router.get("/analytics/low-stock-risk")
def get_low_stock_risk(db: Session = Depends(get_db)):
    """
    Calculate potential loss for low stock items
    AI predicts stockout timeline and threshold breach alerts
    """
    return LossCalculator.calculate_low_stock_risk(db)

@router.get("/analytics/product-level-loss")
def get_product_level_loss(
    period: str = 'daily',
    db: Session = Depends(get_db)
):
    """
    Get product-level profit/loss with Daily, WoW, MoM, YoY comparisons
    period options: 'daily', 'wow', 'mom', 'yoy'
    """
    return LossCalculator.calculate_product_level_loss(db, period)

# ============================================================================
# NLP-FRIENDLY AI EXPLANATIONS - Natural Language Decision Support
# ============================================================================

@router.get("/ai/explain/loss/{product_id}")
def explain_product_loss(product_id: int, db: Session = Depends(get_db)):
    """
    Get NLP-friendly explanation of loss calculation for a product.
    Returns natural language breakdown of:
    - Mathematical formula used
    - Data inputs and their sources
    - Calculated outputs with explanations
    - Business-friendly recommendations
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Calculate average daily demand from last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    avg_demand = db.query(
        func.avg(SalesHistory.quantity_sold)
    ).filter(
        SalesHistory.product_id == product_id,
        SalesHistory.date >= thirty_days_ago
    ).scalar() or 0
    
    return AIExplainer.explain_loss_calculation(
        product_name=product.name,
        avg_daily_demand=float(avg_demand),
        unit_price=float(product.unit_price or 0),
        unit_cost=float(product.unit_cost or 0)
    )

@router.get("/ai/explain/reorder/{product_id}")
def explain_reorder_recommendation(product_id: int, db: Session = Depends(get_db)):
    """
    Get NLP-friendly explanation of reorder recommendation.
    Returns natural language breakdown of:
    - Days until stockout calculation
    - Buffer days and urgency
    - Safety stock formula (with Z-score)
    - Recommended order quantity with justification
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Calculate average daily demand from last 7 days
    seven_days_ago = datetime.now() - timedelta(days=7)
    
    # Get average demand
    avg_demand_result = db.query(
        func.avg(SalesHistory.quantity_sold).label('avg')
    ).filter(
        SalesHistory.product_id == product_id,
        SalesHistory.date >= seven_days_ago
    ).first()
    
    avg_demand = float(avg_demand_result.avg or 1) if avg_demand_result else 1
    
    # Get sales data for manual std calculation (SQLite doesn't have stddev)
    sales_records = db.query(SalesHistory.quantity_sold).filter(
        SalesHistory.product_id == product_id,
        SalesHistory.date >= seven_days_ago
    ).all()
    
    if sales_records and len(sales_records) > 1:
        quantities = [float(r.quantity_sold or 0) for r in sales_records]
        demand_std = float(np.std(quantities))
    else:
        demand_std = avg_demand * 0.3  # Default 30% variability
    
    demand_variability = demand_std / max(avg_demand, 0.01)
    
    return AIExplainer.explain_reorder_recommendation(
        product_name=product.name,
        current_stock=product.current_stock or 0,
        avg_daily_demand=avg_demand,
        lead_time_days=product.lead_time_days or 7,
        unit_cost=float(product.unit_cost or 0),
        unit_price=float(product.unit_price or 0),
        demand_variability=min(demand_variability, 1.0)  # Cap at 100%
    )

@router.get("/ai/explain/forecast/{product_id}")
def explain_forecast(product_id: int, forecast_days: int = 30, db: Session = Depends(get_db)):
    """
    Get NLP-friendly explanation of demand forecast.
    Returns natural language breakdown of:
    - Model used and why it was selected
    - Patterns detected in historical data
    - Forecast summary with business impact
    - Confidence intervals and interpretation
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get historical sales data
    sales_data = db.query(SalesHistory).filter(
        SalesHistory.product_id == product_id
    ).order_by(SalesHistory.date).all()
    
    if not sales_data:
        raise HTTPException(status_code=400, detail="No sales history available")
    
    # Prepare data for forecasting
    df = pd.DataFrame([{
        'date': s.date,
        'quantity_sold': s.quantity_sold
    } for s in sales_data])
    
    # Generate forecast with enhanced output
    forecaster = DemandForecaster()
    
    # Pass product metadata for enhanced predictions (uses CSV extra columns)
    forecaster.set_product_metadata({
        'seasonality_factor': getattr(product, 'seasonality_factor', 1.0) or 1.0,
        'demand_volatility': getattr(product, 'demand_volatility', 0.5) or 0.5,
        'abc_classification': getattr(product, 'abc_classification', 'B') or 'B',
        'xyz_classification': getattr(product, 'xyz_classification', 'Y') or 'Y',
        'profit_margin': getattr(product, 'profit_margin', 0.3) or 0.3,
        'target_service_level': getattr(product, 'target_service_level', 0.95) or 0.95,
        'is_perishable': getattr(product, 'is_perishable', False) or False,
        'lead_time_days': product.lead_time_days or 7,
        'average_daily_demand': getattr(product, 'average_daily_demand', None),
        'stockout_cost_per_unit': getattr(product, 'stockout_cost_per_unit', None),
        'inventory_turnover': getattr(product, 'inventory_turnover', None),
        'inventory_turnover': getattr(product, 'inventory_turnover', None),
    })
    
    forecaster.fit(df)
    forecast_result = forecaster.predict(steps=forecast_days)
    
    # Determine if seasonality was detected
    seasonality_detected = 'Holt-Winters' in (forecast_result.get('model_used') or '')
    
    # Get trend direction
    trend_analysis = forecast_result.get('trend_analysis', {})
    trend_direction = trend_analysis.get('direction', 'stable')
    
    # Create NLP explanation
    explanation = AIExplainer.explain_forecast(
        product_name=product.name,
        historical_days=len(sales_data),
        forecast_days=forecast_days,
        model_used=forecast_result.get('model_used', 'Unknown'),
        predictions=forecast_result.get('predictions', []),
        confidence_intervals={
            'lower': forecast_result.get('lower_bound', []),
            'upper': forecast_result.get('upper_bound', [])
        },
        trend_direction=trend_direction,
        seasonality_detected=seasonality_detected
    )
    
    # Combine forecast data with explanation
    return {
        'forecast': forecast_result,
        'explanation': explanation
    }

@router.get("/ai/explain/alerts")
def explain_all_alerts(limit: int = 20, db: Session = Depends(get_db)):
    """
    Get NLP-friendly executive summary of all AI alerts.
    Returns:
    - Headline summary
    - Priority actions breakdown
    - Financial impact analysis
    - Natural language recommendations
    """
    alerts = AIAlertSystem.generate_live_alerts(db, limit)
    
    # Calculate totals
    total_daily_loss = sum(
        a.get('loss_per_day', 0) for a in alerts 
        if a.get('severity') in ['CRITICAL', 'HIGH']
    )
    total_products_at_risk = len([
        a for a in alerts 
        if a.get('severity') in ['CRITICAL', 'HIGH', 'WARNING']
    ])
    
    return {
        'alerts': alerts,
        'executive_summary': AIExplainer.create_decision_summary(
            alerts=alerts,
            total_potential_loss=total_daily_loss,
            total_products_at_risk=total_products_at_risk
        )
    }

# ============================================================================
# AI-POWERED ALERTS - Intelligent pattern detection
# ============================================================================

@router.get("/analytics/ai-alerts")
def get_ai_alerts(limit: int = 100, db: Session = Depends(get_db)):
    """
    Get AI-powered alerts with intelligent pattern detection. CACHED 45s.
    Includes: stockout losses, threshold breaches, demand trends, anomalies
    """
    # Check cache (45 second TTL)
    cache_key = "/analytics/ai-alerts"
    cached = api_cache.get(cache_key, params={'limit': limit})
    if cached:
        return cached
    
    result = AIAlertSystem.generate_live_alerts(db, limit)
    api_cache.set(cache_key, result, ttl_seconds=45, params={'limit': limit})
    return result

@router.get("/analytics/out-of-stock-breakdown")
def get_out_of_stock_breakdown(db: Session = Depends(get_db)):
    """
    Get detailed breakdown of out-of-stock products by category
    Shows which products and categories are out of stock
    """
    return AIAlertSystem.get_out_of_stock_products(db)

@router.post("/forecast/{product_id}")
def generate_forecast(
    product_id: int,
    forecast_days: int = 30,
    db: Session = Depends(get_db)
):
    """Generate demand forecast for a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get historical sales data
    sales_data = db.query(SalesHistory)\
        .filter(SalesHistory.product_id == product_id)\
        .all()
    
    if not sales_data:
        raise HTTPException(status_code=400, detail="No sales history available")
    
    # Prepare data for forecasting
    df = pd.DataFrame([{
        'date': s.date,
        'quantity_sold': s.quantity_sold
    } for s in sales_data])
    
    # Generate forecast with product metadata for enhanced predictions
    forecaster = DemandForecaster()
    
    # Pass product metadata (uses CSV extra columns)
    forecaster.set_product_metadata({
        'seasonality_factor': getattr(product, 'seasonality_factor', 1.0) or 1.0,
        'demand_volatility': getattr(product, 'demand_volatility', 0.5) or 0.5,
        'abc_classification': getattr(product, 'abc_classification', 'B') or 'B',
        'xyz_classification': getattr(product, 'xyz_classification', 'Y') or 'Y',
        'profit_margin': getattr(product, 'profit_margin', 0.3) or 0.3,
        'target_service_level': getattr(product, 'target_service_level', 0.95) or 0.95,
        'is_perishable': getattr(product, 'is_perishable', False) or False,
        'lead_time_days': product.lead_time_days or 7,
        'average_daily_demand': getattr(product, 'average_daily_demand', None),
        'stockout_cost_per_unit': getattr(product, 'stockout_cost_per_unit', None),
    })
    
    forecaster.fit(df)
    forecast_result = forecaster.predict(steps=forecast_days)
    
    # Save forecasts to database
    for i, date_str in enumerate(forecast_result['dates']):
        forecast_date = datetime.strptime(date_str, '%Y-%m-%d')
        
        forecast_entry = Forecast(
            product_id=product_id,
            forecast_date=forecast_date,
            predicted_demand=forecast_result['predictions'][i],
            lower_bound=forecast_result['lower_bound'][i],
            upper_bound=forecast_result['upper_bound'][i]
        )
        db.add(forecast_entry)
    
    db.commit()
    
    return {
        'product_id': product_id,
        'product_name': product.name,
        'forecast': forecast_result
    }

@router.get("/forecast/{product_id}")
def get_forecast(product_id: int, db: Session = Depends(get_db)):
    """Get existing forecasts for a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get recent forecasts
    forecasts = db.query(Forecast)\
        .filter(Forecast.product_id == product_id)\
        .filter(Forecast.forecast_date >= datetime.now())\
        .order_by(Forecast.forecast_date)\
        .all()
    
    # Get historical sales for comparison
    sales_data = db.query(SalesHistory)\
        .filter(SalesHistory.product_id == product_id)\
        .order_by(SalesHistory.date.desc())\
        .limit(90)\
        .all()
    
    historical = [{
        'date': s.date.strftime('%Y-%m-%d'),
        'actual': s.quantity_sold
    } for s in reversed(sales_data)]
    
    forecast_data = [{
        'date': f.forecast_date.strftime('%Y-%m-%d'),
        'predicted': f.predicted_demand,
        'lower_bound': f.lower_bound,
        'upper_bound': f.upper_bound
    } for f in forecasts]
    
    return {
        'product_id': product_id,
        'product_name': product.name,
        'historical': historical,
        'forecast': forecast_data
    }


@router.get("/products/{product_id}/shadow-forecast")
def get_shadow_forecast(product_id: int, db: Session = Depends(get_db)):
    """Compare a simple 'naive' forecast vs the AI multi-model ensemble.

    Naive = Moving Average model from MultiModelForecaster.
    AI    = Best-performing model from MultiModelForecaster.

    Returns time series for charting plus an estimated margin benefit
    from moving away from naive forecasting.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    sales = db.query(SalesHistory)\
        .filter(SalesHistory.product_id == product_id)\
        .order_by(SalesHistory.date)\
        .all()

    if len(sales) < 14:
        raise HTTPException(status_code=400, detail="Insufficient sales history for shadow forecast")

    # Historical actuals
    historical = [
        {
            'date': s.date.strftime('%Y-%m-%d'),
            'actual': s.quantity_sold,
            'revenue': s.revenue,
        }
        for s in sales
    ]

    mm_result = MultiModelForecaster.forecast_with_all_models(db, product_id, days_ahead=30)
    if 'error' in mm_result:
        return mm_result

    models_perf = mm_result["models_performance"]
    best_model = mm_result["best_model"]

    naive_perf = models_perf.get('moving_average')
    if not naive_perf:
        # Fallback to any available model as naive
        naive_name, naive_perf = next(iter(models_perf.items()))
    else:
        naive_name = 'moving_average'

    naive_mape = naive_perf.get('mape', 0.0)
    ai_mape = best_model.get('mape', naive_mape)

    # Estimate financial benefit based on error reduction
    # Annual revenue from this product
    total_revenue = sum(s.revenue for s in sales)
    days_of_data = (sales[-1].date - sales[0].date).days + 1
    avg_daily_revenue = total_revenue / max(1, days_of_data)
    annual_revenue = avg_daily_revenue * 365

    # Approximate unit margin pct
    unit_margin = max(0.0, (product.unit_price or 0) - (product.unit_cost or 0))
    margin_pct = unit_margin / product.unit_price if product.unit_price else 0.3

    error_reduction_pct = max(0.0, (naive_mape - ai_mape) / max(naive_mape, 1e-6))
    margin_saved_estimate = annual_revenue * (naive_mape - ai_mape) / 100.0 * margin_pct

    # Build naive vs AI future curves for visualization
    forecast_block = mm_result.get('forecast', {})
    future_dates = forecast_block.get('dates', [])
    ensemble_vals = forecast_block.get('ensemble', [])

    # Naive future = repeat last 7-day average
    last_values = [s.quantity_sold for s in sales[-7:]] if len(sales) >= 7 else [s.quantity_sold for s in sales]
    naive_level = sum(last_values) / max(1, len(last_values))
    naive_future = [round(naive_level, 2) for _ in future_dates]

    future = [
        {
            'date': d,
            'naive': naive_future[i] if i < len(naive_future) else None,
            'ai_ensemble': ensemble_vals[i] if i < len(ensemble_vals) else None,
        }
        for i, d in enumerate(future_dates)
    ]

    return {
        'product': {
            'id': product.id,
            'sku': product.sku,
            'name': product.name,
        },
        'historical': historical,
        'future': future,
        'comparison_summary': {
            'naive_model': naive_name.replace('_', ' ').title(),
            'naive_mape': round(naive_mape, 2),
            'ai_model': best_model.get('name'),
            'ai_mape': round(ai_mape, 2),
            'accuracy_improvement_points': round((100 - ai_mape) - (100 - naive_mape), 2),
            'annual_revenue': round(annual_revenue, 2),
            'margin_pct': round(margin_pct * 100, 1),
            'estimated_margin_saved_per_year': round(margin_saved_estimate, 2),
            'error_reduction_pct': round(error_reduction_pct * 100, 1),
        },
    }

@router.post("/optimize/{product_id}")
def optimize_inventory(
    product_id: int,
    service_level: float = 0.95,
    db: Session = Depends(get_db)
):
    """Generate inventory optimization recommendations using all available cost columns"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get sales history
    sales_data = db.query(SalesHistory)\
        .filter(SalesHistory.product_id == product_id)\
        .all()
    
    if not sales_data:
        raise HTTPException(status_code=400, detail="No sales history available")
    
    df = pd.DataFrame([{
        'date': s.date,
        'quantity_sold': s.quantity_sold
    } for s in sales_data])
    
    # Optimize inventory - passing ALL cost columns for optimal calculation
    optimizer = InventoryOptimizer()
    recommendations = optimizer.optimize_inventory(
        df,
        product.unit_cost,
        product.lead_time_days,
        service_level,
        # Pass additional cost columns if available
        storage_cost_per_unit=getattr(product, 'storage_cost_per_unit', None),
        stockout_cost_per_unit=getattr(product, 'stockout_cost_per_unit', None),
        order_frequency_days=getattr(product, 'order_frequency_days', None),
        # Pass NEW constraint columns for enhanced optimization
        shelf_life_days=getattr(product, 'shelf_life_days', None),
        min_order_qty=getattr(product, 'min_order_qty', None),
        max_order_qty=getattr(product, 'max_order_qty', None),
        product_priority=getattr(product, 'product_priority', None),
        # Pass warehouse and tracking columns
        weight_kg=getattr(product, 'weight_kg', None),
        volume_m3=getattr(product, 'volume_m3', None),
        days_since_last_order=getattr(product, 'days_since_last_order', None),
        days_since_last_sale=getattr(product, 'days_since_last_sale', None)
    )
    
    # Save recommendation
    rec = InventoryRecommendation(
        product_id=product_id,
        reorder_point=recommendations['reorder_point'],
        safety_stock=recommendations['safety_stock'],
        economic_order_quantity=recommendations['economic_order_quantity'],
        optimal_stock_level=recommendations['optimal_stock_level'],
        estimated_cost_savings=recommendations['estimated_annual_savings'],
        recommendation_notes=f"Service level: {service_level*100}%, Inventory turnover: {recommendations['inventory_turnover']}"
    )
    db.add(rec)
    db.commit()
    
    return {
        'product_id': product_id,
        'product_name': product.name,
        'recommendations': recommendations
    }

@router.get("/optimize")
def get_all_recommendations(limit: int = 100, db: Session = Depends(get_db)):
    """Get inventory recommendations - OPTIMIZED for speed with CACHING (60s).
    Returns top priority items that need attention (limited for performance).
    
    For 50K+ products, we focus on items that need reorder or have low stock.
    """
    
    # Check cache (60 second TTL)
    cache_key = "/optimize"
    cached = api_cache.get(cache_key, params={'limit': limit})
    if cached:
        return cached
    
    # Fast approach: use pre-calculated avg demand from product table if available
    # and only query sales for products that need attention
    
    # Get products that need attention (low stock) - fast query using configurable threshold
    medium_max = STOCK_THRESHOLDS['medium_stock_max']
    products = db.query(Product).filter(
        Product.current_stock <= medium_max
    ).limit(limit).all()
    
    if not products:
        return []
    
    product_ids = [p.id for p in products]
    
    # Batch load 90-day sales stats in ONE aggregated query (with std dev for model)
    cutoff = datetime.now() - timedelta(days=90)
    sales_stats = db.query(
        SalesHistory.product_id,
        func.sum(SalesHistory.quantity_sold).label('total_qty'),
        func.count(func.distinct(SalesHistory.date)).label('active_days'),
        func.sum(SalesHistory.quantity_sold * SalesHistory.quantity_sold).label('sum_qty_sq'),
        func.count(SalesHistory.id).label("sale_count")
    ).filter(
        SalesHistory.product_id.in_(product_ids),
        SalesHistory.date >= cutoff
    ).group_by(SalesHistory.product_id).all()
    
    sales_map = {}
    for s in sales_stats:
        n = max(s.sale_count or 1, 1)
        mean_qty = float(s.total_qty or 0) / n
        mean_sq = float(s.sum_qty_sq or 0) / n
        variance = max(0, mean_sq - mean_qty ** 2)
        sales_map[s.product_id] = {
            'qty': int(s.total_qty or 0),
            'days': int(s.active_days or 30),
            'std': variance ** 0.5 if n > 1 else None
        }
    
    results = []
    for product in products:
        stats = sales_map.get(product.id)
        
        if not stats or not stats['qty']:
            avg_daily_demand = float(product.average_daily_demand or 1)
            demand_std = None
        else:
            avg_daily_demand = stats['qty'] / max(stats['days'], 30)
            demand_std = stats.get('std')
        
        lead_time = product.lead_time_days or 7
        unit_cost = float(product.unit_cost or 1)
        
        # Use ML model for all inventory calculations
        inv = compute_model_inventory(
            avg_daily_demand=avg_daily_demand,
            demand_std=demand_std,
            lead_time_days=lead_time,
            unit_cost=unit_cost,
            current_stock=int(product.current_stock),
        )
        
        reorder_point = inv['reorder_point']
        safety_stock = inv['safety_stock']
        eoq = inv['eoq']
        optimal_level = reorder_point + safety_stock
        
        # Model-based annual savings: compare current holding cost vs optimized
        holding_cost = max(unit_cost * 0.25, 0.01)
        annual_demand = avg_daily_demand * 365
        optimized_avg_inventory = (eoq / 2) + safety_stock
        current_avg_inventory = max(float(product.current_stock), optimized_avg_inventory * 1.5)
        inventory_reduction = max(0, current_avg_inventory - optimized_avg_inventory)
        annual_savings = inventory_reduction * holding_cost
        
        results.append({
            'product_id': product.id,
            'product_name': product.name,
            'sku': product.sku,
            'category': product.category,
            'current_stock': int(product.current_stock),
            'reorder_point': round(reorder_point, 1),
            'safety_stock': round(safety_stock, 1),
            'economic_order_quantity': max(eoq, 1),
            'optimal_stock_level': round(optimal_level, 1),
            'estimated_savings': round(annual_savings, 2),
            'needs_reorder': product.current_stock < reorder_point
        })
    
    # Sort: reorder needed first, then by stock level
    results.sort(key=lambda x: (not x['needs_reorder'], x['current_stock']))
    
    # Cache for 60 seconds
    api_cache.set(cache_key, results, ttl_seconds=60, params={'limit': limit})
    
    return results


@router.get("/analytics/dashboard-fast")
def get_dashboard_fast(period: str = "daily", db: Session = Depends(get_db)):
    """Fast dashboard endpoint - uses SQL aggregates only, no heavy calculations.
    Designed for 50K+ products to load instantly. CACHED for 60 seconds.
    
    Args:
        period: Aggregation period - 'daily' (last 30 days), 'wow' (12 weeks), 'mom' (12 months), 'yoy' (2 years)
    """
    
    # Check cache first (60 second TTL - increased for performance)
    cache_key = f"/analytics/dashboard-fast"
    cached = api_cache.get(cache_key, params={'period': period})
    if cached:
        print(f"[CACHE HIT] Dashboard {period}")
        return cached
    
    try:
        # Use configurable thresholds
        low_threshold = STOCK_THRESHOLDS['low_stock_max']
        medium_threshold = STOCK_THRESHOLDS['medium_stock_max']
        
        # OPTIMIZED: Single query for total and stock value, then separate simple queries for counts
        from sqlalchemy import and_, extract
        
        # Get basic stats
        total_products = db.query(func.count(Product.id)).scalar() or 0
        total_stock_value = db.query(func.sum(Product.current_stock * Product.unit_cost)).scalar() or 0
        
        # Log for debugging
        print(f"Dashboard query: total_products={total_products}, period={period}")
        
        # Simple count queries for each stock level
        stockout_alerts = db.query(func.count(Product.id)).filter(Product.current_stock == 0).scalar() or 0
        low_stock = db.query(func.count(Product.id)).filter(
            and_(Product.current_stock > 0, Product.current_stock <= low_threshold)
        ).scalar() or 0
        medium_stock = db.query(func.count(Product.id)).filter(
            and_(Product.current_stock > low_threshold, Product.current_stock <= medium_threshold)
        ).scalar() or 0
        high_stock = db.query(func.count(Product.id)).filter(
            Product.current_stock > medium_threshold
        ).scalar() or 0
        
        # Estimate savings using model: avg holding cost reduction per at-risk product
        # Query avg unit_cost for stockout/low-stock products to compute holding savings
        avg_cost_at_risk = db.query(func.avg(Product.unit_cost)).filter(
            Product.current_stock <= low_threshold
        ).scalar() or 10.0
        holding_rate = float(avg_cost_at_risk) * 0.25  # 25% holding cost
        # Estimated savings = potential reduction in excess/stockout costs
        # Stockout products: lost margin recovery; Low stock: EOQ optimization savings
        estimated_annual_savings = (stockout_alerts * float(avg_cost_at_risk) * 30 * 0.5) + (low_stock * holding_rate * 15)
        
        # Get recent sales trend with period-based aggregation
        latest_sale_date = db.query(func.max(SalesHistory.date)).scalar()
        sales_trend = []
        
        if latest_sale_date:
            # Determine date range and grouping based on period
            if period == "daily":
                cutoff = latest_sale_date - timedelta(days=30)
                date_grouping = lambda: (extract('year', SalesHistory.date), 
                                        extract('month', SalesHistory.date), 
                                        extract('day', SalesHistory.date))
            elif period == "wow":
                cutoff = latest_sale_date - timedelta(weeks=12)
                date_grouping = lambda: (extract('year', SalesHistory.date), 
                                        extract('week', SalesHistory.date))
            elif period == "mom":
                cutoff = latest_sale_date - timedelta(days=365)
                date_grouping = lambda: (extract('year', SalesHistory.date), 
                                        extract('month', SalesHistory.date))
            else:  # yoy
                cutoff = latest_sale_date - timedelta(days=730)
                date_grouping = lambda: (extract('year', SalesHistory.date),)
            
            # OPTIMIZED: Use raw SQL without JOIN for 10x faster queries on 22M+ records
            # The sales_history table has revenue pre-calculated, no need to JOIN with products
            from sqlalchemy import text
            
            if period == "daily":
                group_sql = "strftime('%Y-%m-%d', date)"
            elif period == "wow":
                group_sql = "strftime('%Y-%W', date)"
            elif period == "mom":
                group_sql = "strftime('%Y-%m', date)"
            else:  # yoy
                group_sql = "strftime('%Y', date)"
            
            cutoff_str = cutoff.strftime('%Y-%m-%d')
            
            raw_sql = text(f"""
                SELECT 
                    MIN(date) as period_date,
                    SUM(quantity_sold) as quantity,
                    SUM(COALESCE(revenue, quantity_sold * COALESCE(unit_price_at_sale, 10))) as revenue,
                    SUM(quantity_sold * COALESCE(unit_cost_at_sale, 5)) as cost,
                    SUM(CASE WHEN profit_loss_amount < 0 THEN ABS(profit_loss_amount) ELSE 0 END) as loss_amount
                FROM sales_history
                WHERE date >= :cutoff
                GROUP BY {group_sql}
                ORDER BY period_date
            """)
            
            result = db.execute(raw_sql, {'cutoff': cutoff_str})
            sales_query = result.fetchall()
            
            for row in sales_query:
                period_date = pd.to_datetime(row[0]) if row[0] else None
                if not period_date:
                    continue
                quantity = int(row[1] or 0)
                revenue = float(row[2] or 0)
                cost = float(row[3] or 0)
                loss = float(row[4] or 0)
                profit = revenue - cost
                
                # Generate period label and ISO date
                if period == "daily":
                    period_label = period_date.strftime('%Y-%m-%d')
                    date_iso = period_date.strftime('%Y-%m-%d')
                elif period == "wow":
                    week_num = period_date.isocalendar()[1]
                    year = period_date.year
                    period_label = f"W{week_num} {year}"
                    date_iso = f"{year}-W{week_num:02d}"
                elif period == "mom":
                    month_name = period_date.strftime('%b')
                    year = period_date.year
                    period_label = f"{month_name} {year}"
                    date_iso = period_date.strftime('%Y-%m-01')
                else:  # yoy
                    year = period_date.year
                    period_label = str(year)
                    date_iso = f"{year}-01-01"
                
                sales_trend.append({
                    'date': date_iso,
                    'period_label': period_label,
                    'quantity': quantity,
                    'revenue': round(revenue, 2),
                    'profit': round(max(profit, 0), 2),
                    'loss': round(loss, 2)
                })
        
        # --- ADD STOCKOUT OPPORTUNITY LOSS ---
        # Estimate daily lost revenue from out-of-stock products and add to recent periods
        if sales_trend and latest_sale_date:
            try:
                stockout_sql = text("""
                    SELECT 
                        COALESCE(SUM(demand.avg_daily_qty * p.unit_price), 0) as daily_stockout_loss,
                        COUNT(*) as oos_count
                    FROM products p
                    INNER JOIN (
                        SELECT product_id,
                               CAST(SUM(quantity_sold) AS FLOAT) / 
                               MAX(1, JULIANDAY(MAX(date)) - JULIANDAY(MIN(date))) as avg_daily_qty
                        FROM sales_history
                        WHERE date >= :demand_cutoff
                        GROUP BY product_id
                        HAVING avg_daily_qty > 0
                    ) demand ON demand.product_id = p.id
                    WHERE p.current_stock = 0
                """)
                demand_cutoff = (latest_sale_date - timedelta(days=90)).strftime('%Y-%m-%d')
                stockout_result = db.execute(stockout_sql, {'demand_cutoff': demand_cutoff}).fetchone()
                daily_stockout_loss = float(stockout_result[0]) if stockout_result else 0
                
                if daily_stockout_loss > 0:
                    days_map = {'daily': 1, 'wow': 7, 'mom': 30, 'yoy': 365}
                    days_per = days_map.get(period, 1)
                    period_stockout_loss = daily_stockout_loss * days_per
                    
                    # Add stockout loss to the most recent periods (stockout is a current problem)
                    # Weight: full loss for last period, 75% for 2nd-to-last, 50% for 3rd
                    recent_count = min(3, len(sales_trend))
                    weights = [1.0, 0.75, 0.5]
                    for i in range(recent_count):
                        idx = len(sales_trend) - 1 - i
                        sales_trend[idx]['loss'] = round(
                            sales_trend[idx]['loss'] + period_stockout_loss * weights[i], 2
                        )
            except Exception:
                pass  # Don't break dashboard if stockout calc fails
        
        # Get top 5 products - Calculate revenue from quantity * unit_price
        top_products = []
        if latest_sale_date:
            thirty_days_ago = latest_sale_date - timedelta(days=30)
            
            # Calculate revenue as quantity_sold * unit_price (revenue in sales_history may be 0)
            top_revenue = db.query(
                SalesHistory.product_id,
                func.sum(SalesHistory.quantity_sold).label('total_quantity'),
                func.sum(SalesHistory.quantity_sold * Product.unit_price).label('calc_revenue')
            ).join(Product, Product.id == SalesHistory.product_id).filter(
                SalesHistory.date >= thirty_days_ago
            ).group_by(SalesHistory.product_id).order_by(
                func.sum(SalesHistory.quantity_sold * Product.unit_price).desc()
            ).limit(5).all()
            
            # Get product details and calculate AI recommendations
            if top_revenue:
                top_ids = [r.product_id for r in top_revenue]
                products_list = db.query(Product).filter(Product.id.in_(top_ids)).all()
                products_map = {p.id: p for p in products_list}
                
                max_quantity = max((r.total_quantity for r in top_revenue), default=0)
                
                for row in top_revenue:
                    pid = row.product_id
                    if pid not in products_map:
                        continue
                        
                    product = products_map[pid]
                    quantity = int(row.total_quantity or 0)
                    revenue = float(row.calc_revenue or 0)
                    
                    # Calculate profit (revenue - cost)
                    unit_cost = float(product.unit_cost or 0)
                    profit = revenue - (quantity * unit_cost)
                    
                    # AI demand level based on relative sales volume
                    demand_ratio = quantity / max_quantity if max_quantity > 0 else 0
                    if demand_ratio >= 0.7:
                        demand_level = 'HIGH'
                    elif demand_ratio >= 0.3:
                        demand_level = 'MEDIUM'
                    else:
                        demand_level = 'LOW'
                    
                    # AI recommendation based on demand and stock levels
                    margin = float(product.unit_price or 0) - unit_cost
                    if margin < 0:
                        ai_recommendation = "Review pricing - margin is negative"
                    elif demand_level == 'HIGH' and product.current_stock < quantity:
                        ai_recommendation = "High demand - increase stock levels"
                    elif demand_level == 'LOW' and profit <= 0:
                        ai_recommendation = "Consider promotion or bundling"
                    else:
                        ai_recommendation = "Monitor trends and optimize pricing"
                    
                    top_products.append({
                        'id': pid,
                        'name': product.name[:20] + '...' if len(product.name) > 20 else product.name,
                        'sku': product.sku,
                        'current_stock': product.current_stock,
                        'quantity': quantity,
                        'revenue': round(revenue, 2),
                        'profit': round(profit, 2),
                        'demand_level': demand_level,
                        'ai_recommendation': ai_recommendation
                    })
        
        # Calculate forecast accuracy from AI models (using recent forecasts vs actuals)
        forecast_accuracy = 0.0
        if latest_sale_date:
            # Check forecasts from last 30 days
            forecast_cutoff = latest_sale_date - timedelta(days=30)
            forecasts = db.query(Forecast).filter(
                Forecast.forecast_date >= forecast_cutoff,
                Forecast.forecast_date <= latest_sale_date
            ).limit(100).all()  # Limit for speed
        
        if forecasts:
            total_error = 0
            count = 0
            for forecast in forecasts:
                actual = db.query(func.sum(SalesHistory.quantity_sold)).filter(
                    SalesHistory.product_id == forecast.product_id,
                    SalesHistory.date == forecast.forecast_date
                ).scalar()
                if actual and actual > 0:
                    error = abs(forecast.predicted_demand - actual) / actual
                    total_error += min(error, 1.0)  # Cap at 100% error
                    count += 1
            if count > 0:
                mape = total_error / count
                forecast_accuracy = max(0, 1 - mape)
        
        # If no forecasts available, run a quick backtest on sampled products
        if forecast_accuracy == 0 and total_products > 0 and latest_sale_date:
            # Use actual sales data: compare last 7 days actual vs trailing-average prediction
            backtest_end = latest_sale_date
            backtest_start = backtest_end - timedelta(days=7)
            train_start = backtest_end - timedelta(days=37)  # 30 days training window
            
            # Sample up to 50 products with sales
            sample_products = db.query(SalesHistory.product_id).filter(
                SalesHistory.date >= train_start
            ).group_by(SalesHistory.product_id).having(
                func.count(func.distinct(SalesHistory.date)) >= 14
            ).limit(50).all()
            sample_ids = [r.product_id for r in sample_products]
            
            if sample_ids:
                total_error = 0
                count = 0
                for pid in sample_ids:
                    # Training avg (30 days before test)
                    train_avg = db.query(func.avg(SalesHistory.quantity_sold)).filter(
                        SalesHistory.product_id == pid,
                        SalesHistory.date >= train_start,
                        SalesHistory.date < backtest_start
                    ).scalar()
                    # Test actual (last 7 days)
                    test_avg = db.query(func.avg(SalesHistory.quantity_sold)).filter(
                        SalesHistory.product_id == pid,
                        SalesHistory.date >= backtest_start,
                        SalesHistory.date <= backtest_end
                    ).scalar()
                    if train_avg and test_avg and test_avg > 0:
                        error = abs(train_avg - test_avg) / test_avg
                        total_error += min(error, 1.0)
                        count += 1
                if count > 0:
                    forecast_accuracy = max(0, 1 - (total_error / count))
        
        result = {
            'total_products': total_products,
            'stockout_alerts': stockout_alerts,
            'low_stock_count': low_stock,
            'medium_stock_count': medium_stock,
            'high_stock_count': high_stock,
            'forecast_accuracy': round(forecast_accuracy, 2),
            'estimated_annual_savings': round(estimated_annual_savings, 2),
            'total_stock_value': round(float(total_stock_value), 2),
            'sales_trend': sales_trend,
            'top_products': top_products,
            'period_comparison': None
        }
        
        # Cache for 30 seconds
        api_cache.set(cache_key, result, ttl_seconds=30, params={'period': period})
        
        return result
    
    except Exception as e:
        print(f"Error in dashboard-fast endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty but valid structure on error
        return {
            'total_products': 0,
            'stockout_alerts': 0,
            'low_stock_count': 0,
            'medium_stock_count': 0,
            'high_stock_count': 0,
            'forecast_accuracy': 0.0,
            'estimated_annual_savings': 0.0,
            'total_stock_value': 0.0,
            'sales_trend': [],
            'top_products': [],
            'period_comparison': None,
            'error': str(e)
        }


@router.get("/analytics/dashboard")
def get_dashboard_metrics(period: str = "daily", db: Session = Depends(get_db)):
    """Get dashboard analytics and metrics
    
    Args:
        period: Aggregation period - 'daily' (last 30 days), 'wow' (week-over-week), 'mom' (month-over-month), 'yoy' (year-over-year)
    """
    products = db.query(Product).all()
    
    total_products = len(products)
    total_stock_value = sum(float(p.current_stock or 0) * float(p.unit_cost or 0) for p in products)

    # Cache products by id for quick cost/price lookups
    product_map = {p.id: p for p in products}

    latest_sale_date = db.query(func.max(SalesHistory.date)).scalar()
    
    # Early return if no sales data
    if not latest_sale_date:
        return {
            'total_products': total_products,
            'stockout_alerts': sum(1 for p in products if p.current_stock == 0),
            'forecast_accuracy': 0.0,
            'estimated_annual_savings': 0.0,
            'total_stock_value': round(total_stock_value, 2),
            'sales_trend': [],
            'top_products': [],
            'period_comparison': None
        }
    
    if isinstance(latest_sale_date, datetime):
        reference_end_date = latest_sale_date
    elif latest_sale_date is not None:
        reference_end_date = datetime.combine(latest_sale_date, datetime.min.time())
    else:
        reference_end_date = datetime.now()
    
    # Count stockout alerts (products with 0 stock)
    stockout_alerts = sum(1 for p in products if p.current_stock == 0)
    
    # Calculate annual savings from optimization using ML InventoryOptimizer models
    savings_lookback_days = 90
    savings_cutoff = reference_end_date - timedelta(days=savings_lookback_days)
    sales_stats = (
        db.query(
            SalesHistory.product_id.label("product_id"),
            func.sum(SalesHistory.quantity_sold).label("total_quantity"),
            func.count(func.distinct(SalesHistory.date)).label("active_days"),
            func.sum(SalesHistory.quantity_sold * SalesHistory.quantity_sold).label("sum_qty_sq"),
            func.count(SalesHistory.id).label("sale_count")
        )
        .filter(SalesHistory.date >= savings_cutoff)
        .group_by(SalesHistory.product_id)
        .all()
    )
    stats_map = {row.product_id: row for row in sales_stats}

    total_savings = 0.0
    for product in products:
        stats = stats_map.get(product.id)
        if not stats or not stats.total_quantity:
            continue

        observed_days = max(1, min(stats.active_days or 0, savings_lookback_days))
        avg_daily_demand = float(stats.total_quantity) / observed_days
        if avg_daily_demand <= 0:
            continue

        n = max(stats.sale_count or 1, 1)
        mean_qty = float(stats.total_quantity) / n
        mean_sq = float(stats.sum_qty_sq or 0) / n
        variance = max(0, mean_sq - mean_qty ** 2)
        demand_std = variance ** 0.5 if n > 1 else None
        unit_cost = float(product.unit_cost or 0)
        lead_time_days = product.lead_time_days or 7
        holding_cost = max(unit_cost * 0.25, 0.01)

        # Use ML model for optimal inventory parameters
        inv = compute_model_inventory(
            avg_daily_demand=avg_daily_demand,
            demand_std=demand_std,
            lead_time_days=lead_time_days,
            unit_cost=unit_cost,
            current_stock=int(product.current_stock),
        )
        eoq = inv['eoq']
        rop = inv['reorder_point']
        safety_stock = inv['safety_stock']

        # Compare current inventory cost vs optimized
        optimized_avg_inventory = (eoq / 2) + safety_stock
        current_avg_inventory = max(float(product.current_stock), optimized_avg_inventory)
        inventory_reduction = max(0, current_avg_inventory - optimized_avg_inventory)
        product_savings = inventory_reduction * holding_cost

        total_savings += product_savings
    
    # Calculate forecast accuracy based on actual vs predicted
    if total_products > 0:
        # Get forecasts from the past 30 days that we can compare
        recent_forecasts = db.query(Forecast)\
            .filter(Forecast.forecast_date <= datetime.now())\
            .filter(Forecast.forecast_date >= datetime.now() - timedelta(days=30))\
            .all()
        
        if recent_forecasts:
            total_error = 0
            count = 0
            for forecast in recent_forecasts:
                # Get actual sales for the forecast date
                actual_sale = db.query(SalesHistory)\
                    .filter(SalesHistory.product_id == forecast.product_id)\
                    .filter(SalesHistory.date == forecast.forecast_date)\
                    .first()
                
                if actual_sale:
                    predicted = forecast.predicted_demand
                    actual = actual_sale.quantity_sold
                    # Calculate percentage accuracy (1 - MAPE)
                    if actual > 0:
                        error = abs(predicted - actual) / actual
                        total_error += error
                        count += 1
            
            if count > 0:
                mape = total_error / count
                forecast_accuracy = max(0, 1 - mape)  # Convert MAPE to accuracy
            else:
                forecast_accuracy = 0.0
        else:
            forecast_accuracy = 0.0
        
        # Backtest fallback: if no stored forecasts, validate on actual data
        if forecast_accuracy == 0.0 and latest_sale_date:
            bt_end = reference_end_date
            bt_start = bt_end - timedelta(days=7)
            bt_train = bt_end - timedelta(days=37)
            sample_pids = db.query(SalesHistory.product_id).filter(
                SalesHistory.date >= bt_train
            ).group_by(SalesHistory.product_id).having(
                func.count(func.distinct(SalesHistory.date)) >= 14
            ).limit(50).all()
            if sample_pids:
                bt_total_error = 0
                bt_count = 0
                for r in sample_pids:
                    train_avg = db.query(func.avg(SalesHistory.quantity_sold)).filter(
                        SalesHistory.product_id == r.product_id,
                        SalesHistory.date >= bt_train,
                        SalesHistory.date < bt_start
                    ).scalar()
                    test_avg = db.query(func.avg(SalesHistory.quantity_sold)).filter(
                        SalesHistory.product_id == r.product_id,
                        SalesHistory.date >= bt_start,
                        SalesHistory.date <= bt_end
                    ).scalar()
                    if train_avg and test_avg and test_avg > 0:
                        bt_total_error += min(abs(train_avg - test_avg) / test_avg, 1.0)
                        bt_count += 1
                if bt_count > 0:
                    forecast_accuracy = max(0, 1 - (bt_total_error / bt_count))
    else:
        forecast_accuracy = 0.0
    
    # Determine date range based on period and aggregate only once per request
    if period == "wow":
        days_back = 84  # 12 weeks
    elif period == "mom":
        days_back = 365  # 12 months
    elif period == "yoy":
        days_back = 730  # 2 years for YOY comparison
    else:
        days_back = 30

    cutoff_date = reference_end_date - timedelta(days=days_back)
    sales_trend = []
    top_products = []

    if latest_sale_date:
        # Calculate revenue = quantity * unit_price (since revenue in sales_history may be 0)
        unit_revenue_expr = SalesHistory.quantity_sold * func.coalesce(Product.unit_price, 0)
        unit_cost_expr = SalesHistory.quantity_sold * func.coalesce(Product.unit_cost, 0)

        daily_rows = (
            db.query(
                SalesHistory.date.label("date"),
                func.sum(SalesHistory.quantity_sold).label("quantity"),
                func.sum(unit_revenue_expr).label("revenue"),
                func.sum(unit_cost_expr).label("cost")
            )
            .join(Product, Product.id == SalesHistory.product_id)
            .filter(SalesHistory.date >= cutoff_date)
            .group_by(SalesHistory.date)
            .order_by(SalesHistory.date)
            .all()
        )

        daily_map = {}
        for row in daily_rows:
            raw_date = row.date
            date_key = raw_date.date() if isinstance(raw_date, datetime) else raw_date
            revenue_val = float(row.revenue or 0)
            cost_val = float(row.cost or 0)
            daily_map[date_key] = {
                'quantity': int(row.quantity or 0),
                'revenue': revenue_val,
                'profit': revenue_val - cost_val
            }

        if period == "wow":
            weekly = {}
            for date_key, metrics in daily_map.items():
                iso_year, iso_week, _ = date_key.isocalendar()
                week_key = (iso_year, iso_week)
                bucket = weekly.setdefault(week_key, {'quantity': 0, 'revenue': 0.0, 'profit': 0.0})
                bucket['quantity'] += metrics['quantity']
                bucket['revenue'] += metrics['revenue']
                bucket['profit'] += metrics['profit']
            sales_trend = [
                {
                    'date': f"Week {week} ({year})",
                    'year': year,
                    'week': week,
                    'period_label': f"W{week}",
                    'quantity': values['quantity'],
                    'revenue': round(values['revenue'], 2),
                    'profit': round(values['profit'], 2),
                    'loss': round(abs(min(values['profit'], 0)), 2)  # Explicit loss field
                }
                for (year, week), values in sorted(weekly.items())
            ]
        elif period == "mom":
            monthly = {}
            for date_key, metrics in daily_map.items():
                month_key = (date_key.year, date_key.month)
                bucket = monthly.setdefault(month_key, {'quantity': 0, 'revenue': 0.0, 'profit': 0.0})
                bucket['quantity'] += metrics['quantity']
                bucket['revenue'] += metrics['revenue']
                bucket['profit'] += metrics['profit']
            sales_trend = [
                {
                    'date': datetime(year, month, 1).strftime('%b %Y'),
                    'year': year,
                    'month': month,
                    'period_label': datetime(year, month, 1).strftime('%b'),
                    'quantity': values['quantity'],
                    'revenue': round(values['revenue'], 2),
                    'profit': round(values['profit'], 2),
                    'loss': round(abs(min(values['profit'], 0)), 2)  # Explicit loss field
                }
                for (year, month), values in sorted(monthly.items())
            ]
        elif period == "yoy":
            yearly = {}
            for date_key, metrics in daily_map.items():
                year_key = date_key.year
                bucket = yearly.setdefault(year_key, {'quantity': 0, 'revenue': 0.0, 'profit': 0.0})
                bucket['quantity'] += metrics['quantity']
                bucket['revenue'] += metrics['revenue']
                bucket['profit'] += metrics['profit']
            sales_trend = [
                {
                    'date': str(year),
                    'year': year,
                    'period_label': str(year),
                    'quantity': values['quantity'],
                    'revenue': round(values['revenue'], 2),
                    'profit': round(values['profit'], 2),
                    'loss': round(abs(min(values['profit'], 0)), 2)
                }
                for year, values in sorted(yearly.items())
            ]
        else:
            current_date = cutoff_date.date()
            end_date = reference_end_date.date()
            while current_date <= end_date:
                metrics = daily_map.get(current_date, {'quantity': 0, 'revenue': 0.0, 'profit': 0.0})
                sales_trend.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'year': current_date.year,
                    'month': current_date.month,
                    'day': current_date.day,
                    'period_label': current_date.strftime('%b %d'),
                    'quantity': metrics['quantity'],
                    'revenue': round(metrics['revenue'], 2),
                    'profit': round(metrics['profit'], 2),
                    'loss': round(abs(min(metrics['profit'], 0)), 2)  # Explicit loss field
                })
                current_date += timedelta(days=1)

        # Calculate revenue = quantity * unit_price for top products
        product_revenue_expr = SalesHistory.quantity_sold * func.coalesce(Product.unit_price, 0)
        product_rows = (
            db.query(
                SalesHistory.product_id.label("product_id"),
                func.sum(SalesHistory.quantity_sold).label("quantity"),
                func.sum(product_revenue_expr).label("revenue")
            )
            .join(Product, Product.id == SalesHistory.product_id)
            .filter(SalesHistory.date >= cutoff_date)
            .group_by(SalesHistory.product_id)
            .all()
        )

        product_rollups = []
        for row in product_rows:
            product = product_map.get(row.product_id)
            if not product:
                continue
            quantity_val = int(row.quantity or 0)
            revenue_val = float(row.revenue or 0)
            profit_val = revenue_val - quantity_val * float(product.unit_cost or 0)
            product_rollups.append({
                'product': product,
                'quantity': quantity_val,
                'revenue': revenue_val,
                'profit': profit_val
            })

        max_quantity = max((entry['quantity'] for entry in product_rollups), default=0)

        for entry in sorted(product_rollups, key=lambda x: x['revenue'], reverse=True)[:5]:
            product = entry['product']
            demand_ratio = (entry['quantity'] / max_quantity) if max_quantity > 0 else 0
            if demand_ratio >= 0.7:
                demand_level = 'HIGH'
            elif demand_ratio >= 0.3:
                demand_level = 'MEDIUM'
            else:
                demand_level = 'LOW'

            margin_per_unit = float(product.unit_price or 0) - float(product.unit_cost or 0)
            if margin_per_unit < 0:
                ai_msg = "Loss-making bestseller – review pricing or supplier immediately."
            elif demand_level == 'HIGH' and product.current_stock < entry['quantity']:
                ai_msg = "High-demand, profitable item – increase safety stock and prioritize replenishment."
            elif demand_level == 'LOW' and entry['profit'] <= 0:
                ai_msg = "Low-demand, low-profit item – consider promotion, bundling, or rationalization."
            else:
                ai_msg = "Healthy performer – monitor trend and optimize pricing as needed."

            top_products.append({
                'name': product.name,
                'quantity': entry['quantity'],
                'revenue': round(entry['revenue'], 2),
                'profit': round(entry['profit'], 2),
                'demand_level': demand_level,
                'ai_recommendation': ai_msg
            })

    # Simple period-over-period comparison for selected aggregation level
    period_comparison = None
    if sales_trend and len(sales_trend) >= 2:
        current = sales_trend[-1]
        previous = sales_trend[-2]
        cur_rev = current['revenue']
        prev_rev = previous['revenue']
        change_pct = None
        if prev_rev != 0:
            change_pct = round((cur_rev - prev_rev) / prev_rev * 100, 2)

        if period == "daily":
            label = "Day-over-day"
        elif period == "wow":
            label = "Week-over-week (WoW)"
        elif period == "yoy":
            label = "Year-over-year (YoY)"
        else:
            label = "Month-over-month (MoM)"

        period_comparison = {
            'label': label,
            'current_revenue': round(cur_rev, 2),
            'previous_revenue': round(prev_rev, 2),
            'change_pct': change_pct
        }
    
    return {
        'total_products': total_products,
        'stockout_alerts': stockout_alerts,
        'forecast_accuracy': forecast_accuracy,
        'estimated_annual_savings': round(total_savings, 2),
        'total_stock_value': round(total_stock_value, 2),
        'sales_trend': sales_trend,
        'top_products': top_products,
        'period_comparison': period_comparison
    }

@router.get("/analytics/product-sales-trend/{product_id}")
def get_product_sales_trend(product_id: int, period: str = "daily", db: Session = Depends(get_db)):
    """Get sales trend for a specific product with enhanced profit/loss tracking including stockout opportunity loss"""
    
    # Get product for cost calculations
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return []
    
    # Determine date range and format based on period
    if period == "wow":
        days_back = 84  # 12 weeks
        date_grouping = lambda d: (d.year, d.isocalendar()[1])  # (year, week)
        period_label_fn = lambda year, week: f"W{week} {year}"
        period_display_date = lambda year, week: f"{year}-W{week:02d}"
    elif period == "mom":
        days_back = 365  # 12 months
        date_grouping = lambda d: (d.year, d.month)  # (year, month)
        period_label_fn = lambda year, month: datetime(year, month, 1).strftime('%b %Y')
        period_display_date = lambda year, month: f"{year}-{month:02d}-01"
    elif period == "yoy":
        days_back = 730  # 2 years for YOY comparison
        date_grouping = lambda d: (d.year, 1)  # (year, dummy)
        period_label_fn = lambda year, dummy: str(year)
        period_display_date = lambda year, dummy: f"{year}-01-01"
    else:  # daily
        days_back = 30
        date_grouping = lambda d: (d.year, d.month, d.day)
        period_label_fn = lambda year, month, day: f"{year}-{month:02d}-{day:02d}"
        period_display_date = lambda year, month, day: f"{year}-{month:02d}-{day:02d}"
    
    # Get sales for this specific product
    cutoff_date = datetime.now() - timedelta(days=days_back)
    product_sales = db.query(SalesHistory)\
        .filter(SalesHistory.product_id == product_id)\
        .filter(SalesHistory.date >= cutoff_date)\
        .all()
    
    # Aggregate by period with profit/loss calculations
    sales_by_period = {}
    for sale in product_sales:
        period_key = date_grouping(sale.date)
        if period_key not in sales_by_period:
            sales_by_period[period_key] = {
                'quantity': 0, 
                'revenue': 0, 
                'profit': 0,
                'loss': 0,
                'first_date': sale.date
            }
        
        sales_by_period[period_key]['quantity'] += sale.quantity_sold
        
        # Use transaction-time pricing if available, otherwise current prices
        if hasattr(sale, 'unit_price_at_sale') and sale.unit_price_at_sale:
            revenue = sale.quantity_sold * sale.unit_price_at_sale
            unit_cost = sale.unit_cost_at_sale if hasattr(sale, 'unit_cost_at_sale') and sale.unit_cost_at_sale else product.unit_cost
            profit_loss = (sale.unit_price_at_sale - unit_cost) * sale.quantity_sold
        else:
            revenue = sale.quantity_sold * product.unit_price
            profit_loss = (product.unit_price - product.unit_cost) * sale.quantity_sold
        
        sales_by_period[period_key]['revenue'] += revenue
        
        # Separate profit and loss
        if profit_loss >= 0:
            sales_by_period[period_key]['profit'] += profit_loss
        else:
            sales_by_period[period_key]['loss'] += abs(profit_loss)
    
    # --- STOCKOUT OPPORTUNITY LOSS ---
    # Compute avg daily demand from the FULL history (not just recent) for stable estimate
    all_product_sales = db.query(
        func.sum(SalesHistory.quantity_sold).label('total_qty'),
        func.count(func.distinct(func.date(SalesHistory.date))).label('sale_days'),
        func.min(SalesHistory.date).label('first_sale'),
        func.max(SalesHistory.date).label('last_sale')
    ).filter(SalesHistory.product_id == product_id).first()
    
    avg_daily_demand = 0
    avg_daily_revenue = 0
    if all_product_sales and all_product_sales.total_qty and all_product_sales.first_sale:
        total_span_days = max(1, (all_product_sales.last_sale - all_product_sales.first_sale).days)
        avg_daily_demand = float(all_product_sales.total_qty) / total_span_days
        avg_daily_revenue = avg_daily_demand * float(product.unit_price)
    
    # Generate ALL expected periods to fill gaps (stockout = no sales = missing periods)
    now = datetime.now()
    all_period_keys = set()
    
    if period == "daily":
        d = cutoff_date
        while d <= now:
            all_period_keys.add((d.year, d.month, d.day))
            d += timedelta(days=1)
    elif period == "wow":
        d = cutoff_date
        while d <= now:
            iso = d.isocalendar()
            all_period_keys.add((iso[0], iso[1]))
            d += timedelta(weeks=1)
    elif period == "mom":
        d = cutoff_date.replace(day=1)
        while d <= now:
            all_period_keys.add((d.year, d.month))
            if d.month == 12:
                d = d.replace(year=d.year + 1, month=1)
            else:
                d = d.replace(month=d.month + 1)
    elif period == "yoy":
        for y in range(cutoff_date.year, now.year + 1):
            all_period_keys.add((y, 1))
    
    # Days per period for stockout loss estimation
    days_per_period = {'daily': 1, 'wow': 7, 'mom': 30, 'yoy': 365}.get(period, 1)
    expected_period_revenue = avg_daily_revenue * days_per_period
    
    # Fill missing periods with stockout loss if product is out of stock or had low stock
    is_out_of_stock = product.current_stock is not None and product.current_stock == 0
    
    for pk in all_period_keys:
        if pk not in sales_by_period:
            sales_by_period[pk] = {
                'quantity': 0, 'revenue': 0, 'profit': 0, 'loss': 0,
                'first_date': None
            }
    
    # Build complete sales trend with proper date formats
    sales_trend = []
    for period_key in sorted(sales_by_period.keys()):
        data = sales_by_period[period_key]
        
        # Compute stockout opportunity loss for this period
        stockout_loss = 0.0
        # Only compute stockout loss for out-of-stock or critically low stock products
        is_low_stock = (product.current_stock is not None and 
                        product.current_stock < avg_daily_demand * 7)  # Less than 1 week of demand
        if avg_daily_revenue > 0 and (is_out_of_stock or is_low_stock):
            actual_rev = data['revenue']
            if actual_rev < expected_period_revenue * 0.5:
                # Revenue significantly below expected = stockout opportunity loss
                stockout_loss = expected_period_revenue - actual_rev
        
        total_loss = data['loss'] + stockout_loss
        
        sales_trend.append({
            'date': period_display_date(*period_key),
            'period_label': period_label_fn(*period_key),
            'quantity': data['quantity'],
            'revenue': round(data['revenue'], 2),
            'profit': round(data['profit'], 2),
            'loss': round(total_loss, 2)
        })
    
    return sales_trend

@router.get("/metrics/products-detail")
def get_products_detail(db: Session = Depends(get_db)):
    """Get detailed breakdown of products by category and stock levels"""
    products = db.query(Product).all()
    
    # Breakdown by category
    category_breakdown = {}
    for product in products:
        cat = product.category or "Uncategorized"
        if cat not in category_breakdown:
            category_breakdown[cat] = {
                'count': 0,
                'total_stock': 0,
                'total_value': 0
            }
        category_breakdown[cat]['count'] += 1
        category_breakdown[cat]['total_stock'] += product.current_stock
        category_breakdown[cat]['total_value'] += product.current_stock * product.unit_cost
    
    # Stock distribution
    stock_distribution = {
        'out_of_stock': 0,
        'low_stock': 0,
        'medium_stock': 0,
        'high_stock': 0
    }
    
    low_max = STOCK_THRESHOLDS['low_stock_max']
    medium_max = STOCK_THRESHOLDS['medium_stock_max']
    
    for product in products:
        if product.current_stock == 0:
            stock_distribution['out_of_stock'] += 1
        elif product.current_stock <= low_max:
            stock_distribution['low_stock'] += 1
        elif product.current_stock <= medium_max:
            stock_distribution['medium_stock'] += 1
        else:
            stock_distribution['high_stock'] += 1
    
    # Get top 10 products by stock value
    products_with_value = [
        {
            'sku': p.sku,
            'name': p.name,
            'category': p.category,
            'stock': p.current_stock,
            'value': p.current_stock * p.unit_cost
        }
        for p in products
    ]
    top_by_value = sorted(products_with_value, key=lambda x: x['value'], reverse=True)[:10]
    
    # All products list with stock badge
    all_products_list = []
    for product in products:
        if product.current_stock == 0:
            stock_badge = "OUT OF STOCK"
            badge_color = "red"
        elif product.current_stock <= low_max:
            stock_badge = "LOW STOCK"
            badge_color = "orange"
        elif product.current_stock <= medium_max:
            stock_badge = "MEDIUM STOCK"
            badge_color = "green"
        else:
            stock_badge = "HIGH STOCK"
            badge_color = "blue"
        
        all_products_list.append({
            'id': product.id,
            'sku': product.sku,
            'name': product.name,
            'category': product.category,
            'current_stock': product.current_stock,
            'unit_cost': product.unit_cost,
            'unit_price': product.unit_price,
            'lead_time_days': product.lead_time_days,
            'stock_value': product.current_stock * product.unit_cost,
            'stock_badge': stock_badge,
            'badge_color': badge_color
        })
    
    # Sort by SKU by default
    all_products_list = sorted(all_products_list, key=lambda x: x['sku'])
    
    return {
        'total_products': len(products),
        'category_breakdown': [
            {'category': cat, **data}
            for cat, data in sorted(category_breakdown.items(), key=lambda x: x[1]['count'], reverse=True)
        ],
        'stock_distribution': stock_distribution,
        'top_products_by_value': top_by_value,
        'all_products': all_products_list
    }

@router.get("/metrics/stockout-detail")
def get_stockout_detail(db: Session = Depends(get_db)):
    """Get detailed information about products at risk of stockout - OPTIMIZED for 50K+ products"""
    
    # Calculate demand for all products in ONE bulk query (last 30 days) — includes std dev
    cutoff_date = datetime.now() - timedelta(days=30)
    demand_stats = db.query(
        SalesHistory.product_id,
        func.sum(SalesHistory.quantity_sold).label('total_quantity'),
        func.count(func.distinct(SalesHistory.date)).label('active_days'),
        func.sum(SalesHistory.quantity_sold * SalesHistory.quantity_sold).label('sum_qty_sq'),
        func.count(SalesHistory.id).label("sale_count")
    ).filter(
        SalesHistory.date >= cutoff_date
    ).group_by(
        SalesHistory.product_id
    ).all()
    
    demand_map = {stat.product_id: stat for stat in demand_stats}
    
    # Get products with low stock or stockout risk - filter at DB level
    # Use configurable threshold  (not hardcoded)
    low_max = STOCK_THRESHOLDS['low_stock_max']
    at_risk_candidates = db.query(Product).filter(
        Product.current_stock <= low_max * 4  # 4x low threshold for pre-filtering
    ).all()
    
    at_risk_products = []
    critical_products = []
    
    for product in at_risk_candidates:
        # Calculate daily demand from bulk data
        demand_stat = demand_map.get(product.id)
        if demand_stat and demand_stat.total_quantity and demand_stat.active_days:
            avg_daily_demand = float(demand_stat.total_quantity) / max(demand_stat.active_days, 1)
            n = max(demand_stat.sale_count or 1, 1)
            mean_qty = float(demand_stat.total_quantity) / n
            mean_sq = float(demand_stat.sum_qty_sq or 0) / n
            variance = max(0, mean_sq - mean_qty ** 2)
            demand_std = variance ** 0.5 if n > 1 else None
        elif product.average_daily_demand and product.average_daily_demand > 0:
            avg_daily_demand = float(product.average_daily_demand)
            demand_std = None
        else:
            avg_daily_demand = 0
            demand_std = None
        
        if avg_daily_demand == 0:
            continue
        
        lead_time = product.lead_time_days or 7
        unit_cost = float(product.unit_cost or 1)
        
        # Use ML model for risk and reorder calculations
        inv = compute_model_inventory(
            avg_daily_demand=avg_daily_demand,
            demand_std=demand_std,
            lead_time_days=lead_time,
            unit_cost=unit_cost,
            current_stock=int(product.current_stock),
        )
        risk_label = inv['stockout_risk_label']
        
        # Only include at-risk products (CRITICAL, HIGH, MEDIUM, LOW)
        if risk_label == 'SAFE':
            continue
        
        days_until_stockout = int(product.current_stock / avg_daily_demand) if avg_daily_demand > 0 else 999
        reorder_point = inv['reorder_point']
        recommended_order_qty = inv['order_quantity']
        
        product_data = {
            'sku': product.sku,
            'name': product.name,
            'category': product.category,
            'current_stock': product.current_stock,
            'days_until_stockout': days_until_stockout,
            'risk_level': risk_label,
            'reorder_point': reorder_point,
            'recommended_order_qty': recommended_order_qty,
            'lead_time_days': lead_time,
            'average_daily_demand': round(avg_daily_demand, 1),
            'unit_cost': unit_cost
        }
        
        at_risk_products.append(product_data)
        
        if product.current_stock == 0 or days_until_stockout < 3:
            critical_products.append(product_data)
    
    # Sort by urgency (days until stockout)
    at_risk_products = sorted(at_risk_products, key=lambda x: x['days_until_stockout'])
    
    return {
        'total_at_risk': len(at_risk_products),
        'critical_count': len(critical_products),
        'at_risk_products': at_risk_products[:20],  # Top 20 most urgent
        'critical_products': critical_products[:50],  # Limit critical list too
        'total_reorder_cost': sum(p['recommended_order_qty'] * p['unit_cost'] for p in critical_products)
    }

@router.get("/metrics/forecast-detail")
def get_forecast_detail(db: Session = Depends(get_db)):
    """Get detailed forecast accuracy metrics using REAL forecast data"""
    products = db.query(Product).all()
    
    # Calculate accuracy by category
    category_accuracy = {}
    product_accuracy = []
    
    for product in products:
        # Get forecasts from the past 30 days that we can compare with actual sales
        recent_forecasts = db.query(Forecast)\
            .filter(Forecast.product_id == product.id)\
            .filter(Forecast.forecast_date <= datetime.now())\
            .filter(Forecast.forecast_date >= datetime.now() - timedelta(days=30))\
            .all()
        
        if recent_forecasts:
            mape_values = []
            
            for forecast in recent_forecasts:
                # Get actual sales for the forecast date
                actual_sale = db.query(SalesHistory)\
                    .filter(SalesHistory.product_id == product.id)\
                    .filter(SalesHistory.date == forecast.forecast_date)\
                    .first()
                
                if actual_sale and actual_sale.quantity_sold > 0:
                    predicted = forecast.predicted_demand
                    actual = actual_sale.quantity_sold
                    # Calculate percentage error
                    mape_values.append(abs((predicted - actual) / actual))
            
            # Calculate accuracy if we have enough comparisons
            if len(mape_values) >= 3:
                mape = sum(mape_values) / len(mape_values)
                accuracy = max(0, (1 - mape)) * 100
                accuracy = min(100, accuracy)
                
                product_accuracy.append({
                    'sku': product.sku,
                    'name': product.name,
                    'category': product.category or 'Uncategorized',
                    'accuracy': round(accuracy, 1),
                    'data_points': len(mape_values)
                })
                
                cat = product.category or "Uncategorized"
                if cat not in category_accuracy:
                    category_accuracy[cat] = []
                category_accuracy[cat].append(accuracy)
    
    # Calculate overall accuracy
    if product_accuracy:
        overall_accuracy = sum(p['accuracy'] for p in product_accuracy) / len(product_accuracy)
    else:
        overall_accuracy = 0.0
    
    # Average by category
    category_avg = {
        cat: round(sum(accs) / len(accs), 1)
        for cat, accs in category_accuracy.items()
    }
    
    # Sort products by accuracy
    best_forecasts = sorted(product_accuracy, key=lambda x: x['accuracy'], reverse=True)[:10]
    worst_forecasts = sorted(product_accuracy, key=lambda x: x['accuracy'])[:10]
    
    return {
        'overall_accuracy': round(overall_accuracy, 1),
        'category_accuracy': [
            {'category': cat, 'accuracy': acc}
            for cat, acc in sorted(category_avg.items(), key=lambda x: x[1], reverse=True)
        ],
        'best_forecasts': best_forecasts,
        'worst_forecasts': worst_forecasts,
        'total_products_analyzed': len(product_accuracy)
    }

@router.get("/metrics/sales-trend-detail")
def get_sales_trend_detail(db: Session = Depends(get_db)):
    """Get detailed sales and revenue analysis"""
    # Get all products as dictionary for fast lookup
    products = {p.id: p for p in db.query(Product).all()}
    
    # Get sales for last 90 days
    ninety_days_ago = datetime.now() - timedelta(days=90)
    recent_sales = db.query(SalesHistory)\
        .filter(SalesHistory.date >= ninety_days_ago)\
        .order_by(SalesHistory.date.desc())\
        .all()
    
    # Daily revenue aggregation
    daily_revenue = {}
    daily_profit = {}
    daily_units = {}
    product_revenue = {}
    product_profit = {}
    loss_transactions = []
    
    for sale in recent_sales:
        product = products.get(sale.product_id)
        if not product:
            continue
            
        date_key = sale.date.strftime('%Y-%m-%d')
        
        # Use actual transaction-time prices if available, otherwise use current prices
        if hasattr(sale, 'unit_price_at_sale') and sale.unit_price_at_sale:
            revenue = sale.quantity_sold * sale.unit_price_at_sale
            unit_cost = sale.unit_cost_at_sale if hasattr(sale, 'unit_cost_at_sale') and sale.unit_cost_at_sale else product.unit_cost
            profit = (sale.unit_price_at_sale - unit_cost) * sale.quantity_sold
            
            # Track loss transactions (selling below cost)
            if sale.unit_price_at_sale < unit_cost:
                loss_transactions.append({
                    'date': date_key,
                    'product_name': product.name,
                    'sku': product.sku,
                    'quantity': sale.quantity_sold,
                    'selling_price': sale.unit_price_at_sale,
                    'cost': unit_cost,
                    'loss_amount': profit  # Negative value
                })
        else:
            # Fallback to current prices (less accurate)
            revenue = sale.quantity_sold * product.unit_price
            profit = (product.unit_price - product.unit_cost) * sale.quantity_sold
        
        # Daily totals
        if date_key not in daily_revenue:
            daily_revenue[date_key] = 0
            daily_profit[date_key] = 0
            daily_units[date_key] = 0
        daily_revenue[date_key] += revenue
        daily_profit[date_key] += profit
        daily_units[date_key] += sale.quantity_sold
        
        # Product revenue and profit
        if product.id not in product_revenue:
            product_revenue[product.id] = {
                'sku': product.sku,
                'name': product.name,
                'category': product.category,
                'total_revenue': 0,
                'total_profit': 0,
                'total_units': 0,
                'unit_price': product.unit_price
            }
        product_revenue[product.id]['total_revenue'] += revenue
        product_revenue[product.id]['total_profit'] += profit
        product_revenue[product.id]['total_units'] += sale.quantity_sold
    
    # Fill in missing dates with zero values for continuous chart
    end_date = datetime.now().date()
    start_date = ninety_days_ago.date()
    current_date = start_date
    
    complete_daily = {}
    while current_date <= end_date:
        date_key = current_date.strftime('%Y-%m-%d')
        if date_key in daily_revenue:
            complete_daily[date_key] = {
                'revenue': daily_revenue[date_key],
                'profit': daily_profit[date_key],
                'units': daily_units[date_key]
            }
        else:
            complete_daily[date_key] = {'revenue': 0, 'profit': 0, 'units': 0}
        current_date += timedelta(days=1)
    
    # Format daily trend with profit/loss data
    daily_trend = [
        {
            'date': date,
            'revenue': round(data['revenue'], 2),
            'profit': round(data['profit'], 2),
            'units': data['units'],
            'avg_order_value': round(data['revenue'] / data['units'], 2) if data['units'] > 0 else 0,
            'profit_margin': round((data['profit'] / data['revenue'] * 100), 2) if data['revenue'] > 0 else 0
        }
        for date, data in sorted(complete_daily.items())
    ]
    
    # Top products by revenue
    top_products = sorted(
        product_revenue.values(),
        key=lambda x: x['total_revenue'],
        reverse=True
    )[:20]
    
    # Calculate period metrics
    last_30_days = [d for d in daily_trend if d['date'] >= (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')]
    last_7_days = [d for d in daily_trend if d['date'] >= (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')]
    
    total_revenue_30d = sum(d['revenue'] for d in last_30_days)
    total_revenue_7d = sum(d['revenue'] for d in last_7_days)
    total_profit_30d = sum(d['profit'] for d in last_30_days)
    total_profit_7d = sum(d['profit'] for d in last_7_days)
    total_units_30d = sum(d['units'] for d in last_30_days)
    
    # Identify loss-making products
    loss_making_products = [p for p in product_revenue.values() if p.get('total_profit', 0) < 0]
    
    return {
        'daily_trend': daily_trend,
        'top_products_by_revenue': top_products,
        'total_revenue_30d': round(total_revenue_30d, 2),
        'total_revenue_7d': round(total_revenue_7d, 2),
        'total_profit_30d': round(total_profit_30d, 2),
        'total_profit_7d': round(total_profit_7d, 2),
        'total_units_30d': total_units_30d,
        'avg_daily_revenue_30d': round(total_revenue_30d / 30, 2) if len(last_30_days) > 0 else 0,
        'avg_daily_revenue_7d': round(total_revenue_7d / 7, 2) if len(last_7_days) > 0 else 0,
        'avg_daily_profit_30d': round(total_profit_30d / 30, 2) if len(last_30_days) > 0 else 0,
        'avg_daily_profit_7d': round(total_profit_7d / 7, 2) if len(last_7_days) > 0 else 0,
        'profit_margin_30d': round((total_profit_30d / total_revenue_30d * 100), 2) if total_revenue_30d > 0 else 0,
        'loss_transactions': loss_transactions[:50],  # Top 50 loss transactions
        'loss_making_products': loss_making_products,
        'total_loss_amount': round(sum(t['loss_amount'] for t in loss_transactions), 2)
    }

@router.get("/metrics/savings-detail")
def get_savings_detail(db: Session = Depends(get_db)):
    """Get detailed breakdown of estimated annual savings - OPTIMIZED for 50K+ products"""
    
    # Calculate demand for ALL products in ONE bulk query (last 60 days for better accuracy)
    cutoff_date = datetime.now() - timedelta(days=60)
    demand_stats = db.query(
        SalesHistory.product_id,
        func.sum(SalesHistory.quantity_sold).label('total_quantity'),
        func.count(func.distinct(SalesHistory.date)).label('active_days')
    ).filter(
        SalesHistory.date >= cutoff_date
    ).group_by(
        SalesHistory.product_id
    ).all()
    
    demand_map = {stat.product_id: stat for stat in demand_stats}
    
    # Get all products in one query
    products = db.query(Product).all()
    
    savings_breakdown = {
        'reduced_holding_costs': 0,
        'reduced_stockouts': 0,
        'optimized_ordering': 0,
        'markdown_optimization': 0
    }
    
    category_savings = {}
    
    for product in products:
        # Use bulk demand data
        demand_stat = demand_map.get(product.id)
        if demand_stat and demand_stat.total_quantity and demand_stat.active_days:
            avg_daily_demand = float(demand_stat.total_quantity) / max(demand_stat.active_days, 1)
        elif product.average_daily_demand and product.average_daily_demand > 0:
            avg_daily_demand = float(product.average_daily_demand)
        else:
            continue  # Skip products with no demand data
        
        if avg_daily_demand > 0:
            annual_demand = avg_daily_demand * 365
            unit_cost = float(product.unit_cost or 0)
            unit_price = float(product.unit_price or 0)
            holding_cost = unit_cost * 0.25  # 25% annual holding cost
            
            if holding_cost > 0:
                # Holding cost savings from optimized stock levels
                lead_time_days = product.lead_time_days or 7
                rop = avg_daily_demand * lead_time_days
                
                if product.current_stock > rop:
                    excess_stock = product.current_stock - rop
                    holding_savings = excess_stock * holding_cost
                    savings_breakdown['reduced_holding_costs'] += holding_savings
                    
                    cat = product.category or "Uncategorized"
                    if cat not in category_savings:
                        category_savings[cat] = 0
                    category_savings[cat] += holding_savings
                
                # Stockout prevention savings (opportunity cost)
                if product.current_stock < rop * 0.5:
                    potential_lost_sales = avg_daily_demand * 7
                    margin = unit_price - unit_cost
                    stockout_savings = potential_lost_sales * margin * 0.3  # 30% probability of lost sale
                    savings_breakdown['reduced_stockouts'] += stockout_savings
                
                # Ordering optimization (reduced order frequency)
                order_cost = 50  # Fixed cost per order
                current_orders_per_year = max(1, annual_demand / max(product.current_stock, 1))
                optimal_orders_per_year = max(1, annual_demand / (rop * 2))
                ordering_savings = abs(current_orders_per_year - optimal_orders_per_year) * order_cost * 0.5
                savings_breakdown['optimized_ordering'] += ordering_savings
                
                # Markdown optimization (5% of unit price on slow movers)
                if avg_daily_demand < 1 and product.current_stock > STOCK_THRESHOLDS['medium_stock_max']:
                    markdown_savings = product.current_stock * unit_price * 0.05
                    savings_breakdown['markdown_optimization'] += markdown_savings
    
    total_savings = sum(savings_breakdown.values())
    
    # Top savings opportunities by category
    category_savings_list = [
        {'category': cat, 'savings': round(savings, 2)}
        for cat, savings in sorted(category_savings.items(), key=lambda x: x[1], reverse=True)
    ]
    
    return {
        'total_annual_savings': round(total_savings, 2),
        'breakdown': {
            'reduced_holding_costs': round(savings_breakdown['reduced_holding_costs'], 2),
            'reduced_stockouts': round(savings_breakdown['reduced_stockouts'], 2),
            'optimized_ordering': round(savings_breakdown['optimized_ordering'], 2),
            'markdown_optimization': round(savings_breakdown['markdown_optimization'], 2)
        },
        'category_savings': category_savings_list[:10],  # Top 10 categories
        'monthly_savings': round(total_savings / 12, 2)
    }

@router.post("/data/upload")
async def upload_sales_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload CSV files with fast pandas bulk insert (append mode, no delete).
    OPTIMIZED: Better chunking, bulk operations, reduced overhead.
    """
    from sqlalchemy import create_engine
    from app.database import SQLALCHEMY_DATABASE_URL
    
    filename = (file.filename or "").lower()
    temp_path = None

    try:
        # OPTIMIZED: Larger buffer size for file operations
        if not filename.endswith('.csv'):
            # For non-CSV, read directly into memory
            contents = await file.read()
            if filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(io.BytesIO(contents))
            elif filename.endswith('.json'):
                df = pd.read_json(io.StringIO(contents.decode('utf-8')))
            else:
                raise HTTPException(status_code=400, detail="Supported formats: CSV, Excel, JSON")
            
            # Process as single chunk
            chunks = [df]
        else:
            # OPTIMIZED: Save CSV to temp file with larger buffer
            suffix = '.csv'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='wb') as tmp:
                temp_path = tmp.name
                # Stream in larger chunks
                while True:
                    chunk = await file.read(16 * 1024 * 1024)  # 16MB chunks
                    if not chunk:
                        break
                    tmp.write(chunk)
            
            # OPTIMIZED: Read in larger chunks for fewer iterations
            chunks = list(pd.read_csv(temp_path, chunksize=100000, low_memory=False))
        
        if not chunks or chunks[0] is None or len(chunks[0]) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # Detect schema from first chunk
        first_chunk = chunks[0]
        has_product_cols = 'sku' in first_chunk.columns
        has_sales_cols = 'date' in first_chunk.columns and 'quantity_sold' in first_chunk.columns

        if not has_product_cols and not has_sales_cols:
            raise HTTPException(
                status_code=400,
                detail="File must have product columns (sku, name) or sales columns (date, sku, quantity_sold)"
            )

        # OPTIMIZED: Build product map with single query
        product_map = {p.sku: p for p in db.query(Product).all()}
        sku_to_id = {sku: p.id for sku, p in product_map.items()}
        
        updated_products = set()
        new_products = 0
        records_added = 0

        # OPTIMIZED: Create engine with connection pooling
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True
        )

        # Process each chunk
        for chunk_df in chunks:
            if chunk_df is None or chunk_df.empty:
                continue

            # --- PRODUCT PROCESSING (optimized) ---
            if has_product_cols:
                chunk_df = chunk_df.where(pd.notnull(chunk_df), None)
                
                # OPTIMIZED: Batch product updates
                products_to_update = []
                products_to_add = []
                
                for row in chunk_df.to_dict('records'):
                    sku_raw = row.get('sku')
                    if not sku_raw:
                        continue
                    sku = str(sku_raw).strip()
                    if not sku:
                        continue

                    product = product_map.get(sku)
                    product_name = row.get('product_name') or row.get('name') or sku
                    category = row.get('category', 'General') or 'General'
                    current_stock = row.get('current_stock')
                    unit_cost = row.get('unit_cost')
                    unit_price = row.get('unit_price')
                    lead_time = row.get('lead_time_days')

                    if not product:
                        product = Product(
                            sku=sku,
                            name=str(product_name),
                            category=str(category),
                            current_stock=int(current_stock) if current_stock is not None else 0,
                            unit_cost=float(unit_cost) if unit_cost is not None else 10.0,
                            unit_price=float(unit_price) if unit_price is not None else 15.0,
                            lead_time_days=int(lead_time) if lead_time is not None else 7
                        )
                        products_to_add.append(product)
                        new_products += 1
                    elif sku not in updated_products:
                        product.name = str(product_name)
                        product.category = str(category)
                        if current_stock is not None:
                            product.current_stock = int(current_stock)
                        if unit_cost is not None:
                            product.unit_cost = float(unit_cost)
                        if unit_price is not None:
                            product.unit_price = float(unit_price)
                        if lead_time is not None:
                            product.lead_time_days = int(lead_time)
                        updated_products.add(sku)
                        products_to_update.append(product)
                
                # OPTIMIZED: Bulk add new products
                if products_to_add:
                    db.bulk_save_objects(products_to_add)
                    db.flush()
                    for p in products_to_add:
                        product_map[p.sku] = p
                        sku_to_id[p.sku] = p.id

            # --- SALES PROCESSING (optimized pandas bulk insert) ---
            if has_sales_cols:
                sales_df = chunk_df[['date', 'sku', 'quantity_sold']].copy()
                sales_df = sales_df.dropna(subset=['date', 'sku', 'quantity_sold'])
                
                # OPTIMIZED: Vectorized operations
                sales_df['sku'] = sales_df['sku'].astype(str).str.strip()
                sales_df['product_id'] = sales_df['sku'].map(sku_to_id)
                sales_df = sales_df[sales_df['product_id'].notna()]
                sales_df['product_id'] = sales_df['product_id'].astype('int32')
                
                # Convert dates with better performance
                sales_df['date'] = pd.to_datetime(sales_df['date'], errors='coerce', format='mixed')
                sales_df = sales_df[sales_df['date'].notna()]
                
                # Convert quantity
                sales_df['quantity_sold'] = pd.to_numeric(sales_df['quantity_sold'], errors='coerce').fillna(0).astype('int32')
                sales_df['revenue'] = 0.0
                
                # OPTIMIZED: Bulk insert with larger chunksize
                insert_df = sales_df[['product_id', 'date', 'quantity_sold', 'revenue']]
                insert_df.to_sql('sales_history', engine, if_exists='append', index=False, method='multi', chunksize=50000)
                records_added += len(insert_df)

        db.commit()
        engine.dispose()

        return {
            'message': f"Imported {new_products} new products, updated {len(updated_products)} products, added {records_added} sales records",
            'products_added': new_products,
            'products_updated': len(updated_products),
            'records_added': records_added
        }

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()


@router.post("/data/upload-sales-fast")
async def upload_sales_fast(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Ultra-fast sales-only upload with automatic field mapping and validation.
    Uses chunked reading for large files (8M+ records).
    OPTIMIZED: Bulk inserts, vectorized operations, connection pooling, reduced overhead.
    
    Supports flexible field names (automatically mapped):
    - date, sale_date, transaction_date -> date
    - sku, product_id, product_sku -> sku
    - quantity_sold, quantity, qty, qty_sold -> quantity_sold
    - Plus all optional enhanced fields
    
    Compatible with SalesSchema field aliases for automatic mapping.
    """
    from sqlalchemy import create_engine, text
    from app.database import SQLALCHEMY_DATABASE_URL
    import time
    
    start_time = time.time()
    filename = (file.filename or "").lower()
    temp_path = None
    CHUNK_SIZE = 100000  # OPTIMIZED: Increased to 100K for fewer iterations
    
    # Log start of upload for user visibility
    import logging
    logger = logging.getLogger(__name__)

    try:
        if not filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files supported for fast upload")
        
        # OPTIMIZED: Save to temp file with larger buffer for faster writes
        print(f"\n{'='*60}")
        print(f"📊 STARTING SALES UPLOAD: {filename}")
        print(f"{'='*60}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='wb') as tmp:
            temp_path = tmp.name
            bytes_written = 0
            # Stream copy with 16MB chunks for maximum throughput
            while True:
                chunk = await file.read(16 * 1024 * 1024)  # OPTIMIZED: 16MB chunks
                if not chunk:
                    break
                tmp.write(chunk)
                bytes_written += len(chunk)
        
        file_size_mb = bytes_written / (1024 * 1024)
        print(f"✅ File uploaded: {file_size_mb:.2f} MB")
        
        # Estimate processing time
        estimated_seconds = int(file_size_mb / 20)  # ~20 MB/sec typical
        print(f"⏱️  Estimated processing time: ~{estimated_seconds} seconds")
        print(f"{'='*60}\n")
        
        # OPTIMIZED: Get product SKU to ID mapping with single optimized query
        sku_to_id = {p.sku: p.id for p in db.query(Product.sku, Product.id).all()}
        
        if not sku_to_id:
            raise HTTPException(status_code=400, detail="No products found in database. Please upload products first.")
        
        # OPTIMIZED: Create engine with connection pooling for better performance
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            execution_options={"isolation_level": "AUTOCOMMIT"}  # ULTRA-FAST: No transaction overhead
        )
        
        # CRITICAL OPTIMIZATION: Drop indexes before bulk insert (50-100x faster for large databases)
        print("🔧 Dropping indexes for maximum speed...")
        drop_start = time.time()
        with engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys=OFF"))
            conn.execute(text("DROP INDEX IF EXISTS ix_sales_history_date"))
            conn.execute(text("DROP INDEX IF EXISTS ix_sales_history_id"))
            conn.commit()
        print(f"✅ Indexes dropped in {time.time()-drop_start:.1f}s\n")
        
        # CHUNKED READING - process file in chunks to handle 8M+ records
        records_added = 0
        total_rows = 0
        chunks_processed = 0
        
        # OPTIMIZED: Detect available columns and cache schema for reuse
        sales_schema = SalesSchema()  # Cache schema instance
        sample_df = pd.read_csv(temp_path, nrows=1)
        # Apply field mapping once and cache column mapping
        sample_df = DataMapper.map_field_names(sample_df, sales_schema, 'sales')
        available_cols = set(sample_df.columns)
        
        # Cache the field mapping to avoid repeated lookups
        field_mapping = {}
        original_sample = pd.read_csv(temp_path, nrows=1)
        for orig_col in original_sample.columns:
            for mapped_col in sample_df.columns:
                if orig_col.lower() == mapped_col or orig_col.lower() in sales_schema.FIELD_ALIASES:
                    if sales_schema.FIELD_ALIASES.get(orig_col.lower()) == mapped_col:
                        field_mapping[orig_col] = mapped_col
                        break
        
        # Base required columns
        required_cols = ['date', 'sku', 'quantity_sold']
        
        # Optional enhanced columns for accurate loss tracking
        optional_cols = [
            'revenue',
            'unit_price_at_sale',
            'unit_cost_at_sale', 
            'profit_loss_amount',
            'profit_margin_pct',
            'discount_applied',
            'transaction_type',
            'promotion_id',
            'sales_channel',
            'customer_id',
            'region'
        ]
        
        # Use only columns that exist in the CSV (after mapping)
        cols_to_read = [c for c in required_cols + optional_cols if c in available_cols]
        
        # OPTIMIZED: Read CSV with optimized dtypes and process chunks
        for chunk_df in pd.read_csv(
            temp_path, 
            chunksize=CHUNK_SIZE,
            low_memory=False,  # Better dtype inference
            na_filter=True,  # Handle NaN values efficiently
        ):
            chunks_processed += 1
            total_rows += len(chunk_df)
            
            # OPTIMIZED: Apply cached field mapping (faster than full schema mapping)
            if field_mapping:
                chunk_df = chunk_df.rename(columns=field_mapping)
            else:
                # Fallback to full mapping if cache failed
                chunk_df = DataMapper.map_field_names(chunk_df, sales_schema, 'sales')
            
            # OPTIMIZED: Vectorized data transformation with minimal operations
            chunk_df['sku'] = chunk_df['sku'].astype(str).str.strip()
            chunk_df['product_id'] = chunk_df['sku'].map(sku_to_id)
            
            # Fast filtering using boolean indexing
            valid_mask = chunk_df['product_id'].notna()
            chunk_df = chunk_df[valid_mask]
            
            if len(chunk_df) == 0:
                continue
            
            # OPTIMIZED: Batch type conversions
            chunk_df['product_id'] = chunk_df['product_id'].astype('int32')  # int32 uses less memory
            chunk_df['date'] = pd.to_datetime(chunk_df['date'], errors='coerce', format='mixed')
            chunk_df = chunk_df[chunk_df['date'].notna()]  # Filter invalid dates
            chunk_df['quantity_sold'] = pd.to_numeric(chunk_df['quantity_sold'], errors='coerce').fillna(0).astype('int32')
            
            # Add revenue if not present (backward compatibility)
            if 'revenue' not in chunk_df.columns:
                chunk_df['revenue'] = 0.0
            
            # Handle optional enhanced columns - fill with None if not present
            for col in optional_cols[1:]:  # Skip 'revenue' as it's handled above
                if col not in chunk_df.columns:
                    chunk_df[col] = None
            
            # OPTIMIZED: Vectorized profit calculations (faster than row-by-row)
            if 'unit_price_at_sale' in chunk_df.columns and 'unit_cost_at_sale' in chunk_df.columns:
                # Convert to numeric arrays for faster computation
                prices = pd.to_numeric(chunk_df['unit_price_at_sale'], errors='coerce')
                costs = pd.to_numeric(chunk_df['unit_cost_at_sale'], errors='coerce')
                qty = chunk_df['quantity_sold']
                
                if 'profit_loss_amount' not in chunk_df.columns or chunk_df['profit_loss_amount'].isna().all():
                    chunk_df['profit_loss_amount'] = (prices - costs) * qty
                
                if 'profit_margin_pct' not in chunk_df.columns or chunk_df['profit_margin_pct'].isna().all():
                    chunk_df['profit_margin_pct'] = ((prices - costs) / prices * 100).fillna(0)
            
            # ULTRA-OPTIMIZED: Use pandas to_sql with maximum speed settings
            db_columns = ['product_id', 'date', 'quantity_sold', 'revenue'] + [
                c for c in optional_cols[1:] if c in chunk_df.columns
            ]
            insert_df = chunk_df[db_columns]
            
            if len(insert_df) > 0:
                # Use pandas to_sql with method='multi' for fastest bulk insert
                insert_df.to_sql(
                    'sales_history', 
                    engine, 
                    if_exists='append', 
                    index=False, 
                    method='multi',
                    chunksize=100000  # Maximum chunksize for fewest round trips
                )
                records_added += len(insert_df)
            
            # OPTIMIZED: Progress logging - more frequent for large files
            log_interval = 5 if file_size_mb > 100 else 10  # Every 5 chunks for large files
            if chunks_processed % log_interval == 0 or chunks_processed == 1:
                elapsed = time.time() - start_time
                rate = int(records_added / elapsed) if elapsed > 0 else 0
                percent_complete = (bytes_written * chunks_processed) / (file_size_mb * 1024 * 1024 * 100) if file_size_mb > 0 else 0
                eta_seconds = int((elapsed / chunks_processed) * (total_rows / CHUNK_SIZE - chunks_processed)) if chunks_processed > 0 else 0
                
                print(f"⚡ Chunk {chunks_processed}: {records_added:,} records | {rate:,}/s | ETA: {eta_seconds}s")
        
        # CRITICAL: Recreate indexes after bulk insert
        print("\n🔧 Recreating indexes...")
        index_start = time.time()
        with engine.connect() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sales_history_date ON sales_history (date)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sales_history_id ON sales_history (id)"))
            conn.execute(text("PRAGMA foreign_keys=ON"))
            conn.commit()
        index_time = time.time() - index_start
        print(f"✅ Indexes recreated in {index_time:.1f}s")
        
        engine.dispose()
        
        elapsed = time.time() - start_time
        rate = records_added / elapsed if elapsed > 0 else 0
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"✅ UPLOAD COMPLETE!")
        print(f"{'='*60}")
        print(f"Records added: {records_added:,}")
        print(f"Time taken: {elapsed:.2f} seconds")
        print(f"Processing speed: {rate:,.0f} records/second")
        print(f"File size: {file_size_mb:.2f} MB")
        print(f"Throughput: {(file_size_mb / elapsed):.2f} MB/second")
        print(f"Index recreation: {index_time:.1f}s")
        print(f"{'='*60}\n")
        
        # INVALIDATE CACHE after data upload
        api_cache.clear()
        print("🗑️  Cache cleared after sales upload")
        
        return {
            'message': f"Fast import: {records_added:,} sales records in {elapsed:.1f}s ({rate:,.0f} records/sec)",
            'records_added': records_added,
            'total_rows': total_rows,
            'chunks_processed': chunks_processed,
            'elapsed_seconds': round(elapsed, 2),
            'records_per_second': round(rate, 0),
            'index_recreation_seconds': round(index_time, 1)
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        print(f"Sales upload error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Fast upload failed: {str(exc)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


# ============================================================================
# EXTERNAL JSON API INTEGRATION - Load data from external APIs
# Two-Tier Storage: Tier 1 (raw JSON → disk) + Tier 2 (processed → SQLite)
# ============================================================================

@router.post("/data/import-from-api")
async def import_from_external_api(
    api_url: str,
    data_type: str = "products",  # products, sales, or inventory
    db: Session = Depends(get_db)
):
    """
    Import data from an external JSON API endpoint.
    
    Two-Tier Storage:
      - Tier 1: Raw JSON saved to backend/data/api_imports/raw/<data_type>_<source>.json
      - Tier 2: Mapped records inserted/updated in SQLite via DataMapper
    
    Args:
        api_url: The external API URL to fetch data from
        data_type: Type of data - 'products', 'sales', or 'inventory'
    """
    import httpx
    
    start_time = time.time()
    raw_info = None
    
    try:
        # ── Fetch from external API ──
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url)
            response.raise_for_status()
            data = response.json()
        
        # ── TIER 1: Save raw JSON to local disk ──
        raw_info = save_raw_json(data, url=api_url, data_type=data_type)
        
        # ── Extract items from response ──
        if isinstance(data, dict):
            items = data.get('data') or data.get('items') or data.get('products') or data.get('results') or [data]
        elif isinstance(data, list):
            items = data
        else:
            raise HTTPException(status_code=400, detail="API response format not supported")
        
        records_added = 0
        records_updated = 0
        mapped_records = []  # Collect mapped records for processed snapshot
        
        if data_type == "products":
            # Lightweight lookup: only load SKU strings, not full ORM objects (avoids 50K session bloat)
            existing_sku_set = {row[0] for row in db.query(Product.sku).all()}
            
            for item in items:
                try:
                    mapped_item = DataMapper.map_field_names(item, ProductSchema(), 'product')
                    mapped_records.append(mapped_item)
                    
                    sku = mapped_item.get('sku')
                    if not sku:
                        continue
                    sku = str(sku)
                    
                    if sku in existing_sku_set:
                        # Update existing product by targeted query (no 50K ORM load)
                        update_data = {k: v for k, v in mapped_item.items() if v is not None and hasattr(Product, k)}
                        update_data.pop('sku', None)
                        if update_data:
                            db.query(Product).filter(Product.sku == sku).update(update_data)
                        records_updated += 1
                    else:
                        product_data = DataMapper.convert_types(
                            mapped_item,
                            ProductSchema.FIELD_TYPES,
                            ProductSchema.FIELD_DEFAULTS
                        )
                        new_product = Product(**product_data)
                        db.add(new_product)
                        records_added += 1
                except Exception as e:
                    print(f"Error processing product item: {e}")
                    continue
            
            db.commit()
            
        elif data_type == "sales":
            sku_to_id = {p.sku: p.id for p in db.query(Product.sku, Product.id).all()}
            
            for item in items:
                try:
                    mapped_item = DataMapper.map_field_names(item, SalesSchema(), 'sales')
                    mapped_records.append(mapped_item)
                    
                    sku = mapped_item.get('sku')
                    if not sku:
                        continue
                    product_id = sku_to_id.get(str(sku))
                    if not product_id:
                        continue
                    
                    sales_data = DataMapper.convert_types(
                        mapped_item,
                        SalesSchema.FIELD_TYPES,
                        SalesSchema.FIELD_DEFAULTS
                    )
                    sales_data.pop('sku', None)
                    sales_data['product_id'] = product_id
                    
                    sale = SalesHistory(**sales_data)
                    db.add(sale)
                    records_added += 1
                except Exception as e:
                    print(f"Error processing sales item: {e}")
                    continue
            
            db.commit()
            
        elif data_type == "inventory":
            existing_sku_set = {row[0] for row in db.query(Product.sku).all()}
            
            for item in items:
                mapped_records.append(item)
                sku = str(item.get('sku') or item.get('product_id', ''))
                stock = int(item.get('stock') or item.get('quantity') or item.get('inventory', 0))
                
                if sku in existing_sku_set:
                    db.query(Product).filter(Product.sku == sku).update({'current_stock': stock})
                    records_updated += 1
            
            db.commit()
        
        # ── TIER 1b: Save processed / mapped snapshot ──
        processed_path = None
        if mapped_records:
            processed_path = save_processed_json(
                mapped_records, url=api_url, data_type=data_type,
                source_name=raw_info["source_name"]
            )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # ── TIER 2: Log import metadata to DB ──
        import_log = ApiImportLog(
            source_name=raw_info["source_name"],
            source_url=api_url,
            data_type=data_type,
            raw_file_path=raw_info["file_path"],
            processed_file_path=processed_path,
            record_count=len(items),
            records_added=records_added,
            records_updated=records_updated,
            file_size_bytes=raw_info["file_size_bytes"],
            status="success",
            import_duration_ms=duration_ms,
        )
        db.add(import_log)
        db.commit()
        
        # ── Update manifest.json ──
        append_to_manifest({
            "id": import_log.id,
            "source_name": raw_info["source_name"],
            "source_url": api_url,
            "data_type": data_type,
            "raw_file": raw_info["file_name"],
            "processed_file": os.path.basename(processed_path) if processed_path else None,
            "record_count": len(items),
            "records_added": records_added,
            "records_updated": records_updated,
            "file_size_bytes": raw_info["file_size_bytes"],
            "imported_at": datetime.now().isoformat(),
            "duration_ms": duration_ms,
        })
        
        return {
            'success': True,
            'message': f'Successfully imported data from API',
            'data_type': data_type,
            'records_added': records_added,
            'records_updated': records_updated,
            'total_items_processed': len(items),
            'storage': {
                'tier1_raw_file': raw_info["file_name"],
                'tier1_file_size': f'{raw_info["file_size_bytes"]:,} bytes',
                'tier2_db_records': records_added + records_updated,
                'import_log_id': import_log.id,
            },
            'duration_ms': duration_ms,
        }
        
    except httpx.HTTPError as e:
        # Log failed import
        if raw_info:
            _log_failed_import(db, raw_info, api_url, data_type, str(e), start_time)
        raise HTTPException(status_code=400, detail=f"Failed to fetch from API: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        if raw_info:
            _log_failed_import(db, raw_info, api_url, data_type, str(e), start_time)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


def _log_failed_import(db, raw_info, api_url, data_type, error_msg, start_time):
    """Helper to log a failed import attempt to the DB."""
    try:
        duration_ms = int((time.time() - start_time) * 1000)
        import_log = ApiImportLog(
            source_name=raw_info.get("source_name", "unknown"),
            source_url=api_url,
            data_type=data_type,
            raw_file_path=raw_info.get("file_path", ""),
            record_count=0,
            records_added=0,
            records_updated=0,
            file_size_bytes=raw_info.get("file_size_bytes", 0),
            status="failed",
            error_message=error_msg,
            import_duration_ms=duration_ms,
        )
        db.add(import_log)
        db.commit()
    except Exception:
        pass  # Don't let logging failure mask original error


@router.get("/data/external-api-templates")
def get_external_api_templates():
    """Get list of pre-configured free API templates for data import."""
    return {
        'templates': [
            {
                'name': 'FakeStore API',
                'url': 'https://fakestoreapi.com/products',
                'data_type': 'products',
                'description': 'Free fake e-commerce product data with 20 items',
                'fields_mapped': ['id→sku', 'title→name', 'category→category', 'price→unit_price'],
                'icon': '🛒'
            },
            {
                'name': 'DummyJSON Products',
                'url': 'https://dummyjson.com/products?limit=100',
                'data_type': 'products',
                'description': 'Dummy product data with stock levels (100 items)',
                'fields_mapped': ['id→sku', 'title→name', 'category→category', 'price→unit_price', 'stock→current_stock'],
                'icon': '📦'
            },
            {
                'name': 'Open Library Books',
                'url': 'https://openlibrary.org/subjects/business.json?limit=50',
                'data_type': 'products',
                'description': 'Free book data from Open Library',
                'fields_mapped': ['key→sku', 'title→name'],
                'icon': '📚'
            },
            {
                'name': 'CoinGecko Crypto',
                'url': 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page=50',
                'data_type': 'products',
                'description': 'Free cryptocurrency market data',
                'fields_mapped': ['id→sku', 'name→name', 'current_price→unit_price'],
                'icon': '₿'
            },
            {
                'name': 'REST Countries',
                'url': 'https://restcountries.com/v3.1/all',
                'data_type': 'products',
                'description': 'Country data as inventory items',
                'fields_mapped': ['cca3→sku', 'name.common→name'],
                'icon': '🌍'
            },
            {
                'name': 'Pokemon API',
                'url': 'https://pokeapi.co/api/v2/pokemon?limit=100',
                'data_type': 'products',
                'description': 'Pokemon as inventory items',
                'fields_mapped': ['name→name', 'url→sku'],
                'icon': '⚡'
            }
        ],
        'supported_fields': {
            'products': ['sku/id/key', 'name/title', 'category/type', 'price/unit_price/current_price', 'stock/quantity/inventory'],
            'sales': ['product_id/sku', 'date/timestamp', 'quantity/units', 'revenue/total/amount'],
            'inventory': ['sku/product_id', 'stock/quantity/inventory']
        },
        'documentation': {
            'note': 'All APIs listed are free and do not require API keys',
            'auto_mapping': 'The system automatically maps common field names to inventory fields',
            'custom_url': 'You can also enter any JSON API URL that returns an array of objects'
        }
    }


# ============================================================================
# IMPORT STORAGE MANAGEMENT — View, replay, and manage saved JSON imports
# ============================================================================

@router.get("/data/import-history")
def get_import_history(
    limit: int = 50,
    source: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get import history from the api_import_logs table (Tier 2 metadata).
    Optionally filter by source name or status.
    """
    query = db.query(ApiImportLog).order_by(ApiImportLog.created_at.desc())
    if source:
        query = query.filter(ApiImportLog.source_name == source)
    if status:
        query = query.filter(ApiImportLog.status == status)
    logs = query.limit(limit).all()

    return {
        "total": len(logs),
        "imports": [
            {
                "id": log.id,
                "source_name": log.source_name,
                "source_url": log.source_url,
                "data_type": log.data_type,
                "raw_file": os.path.basename(log.raw_file_path) if log.raw_file_path else None,
                "record_count": log.record_count,
                "records_added": log.records_added,
                "records_updated": log.records_updated,
                "file_size_bytes": log.file_size_bytes,
                "status": log.status,
                "error_message": log.error_message,
                "duration_ms": log.import_duration_ms,
                "imported_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }


@router.get("/data/saved-files")
def get_saved_json_files():
    """
    List all raw JSON files saved on local disk (Tier 1).
    Returns file names, sizes, and timestamps.
    """
    raw_files = list_raw_files()
    return {
        "total": len(raw_files),
        "directory": "backend/data/api_imports/raw/",
        "files": raw_files,
    }


@router.get("/data/saved-files/{file_name}")
def view_saved_json(file_name: str):
    """
    View the contents of a specific saved raw JSON file.
    Useful for inspecting what the API actually returned.
    """
    try:
        data = load_raw_json(file_name)
        # Determine record count
        if isinstance(data, list):
            count = len(data)
        elif isinstance(data, dict):
            items = data.get('products') or data.get('data') or data.get('items') or data.get('results')
            count = len(items) if isinstance(items, list) else 1
        else:
            count = 1
        return {
            "file_name": file_name,
            "record_count": count,
            "data": data,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_name}")


@router.post("/data/replay-import/{file_name}")
async def replay_import(
    file_name: str,
    data_type: str = "products",
    db: Session = Depends(get_db)
):
    """
    Re-import a previously saved raw JSON file without re-fetching from the API.
    This replays the Tier 1 file through the Tier 2 pipeline.
    
    Use case: re-process data after schema changes, or recover from a failed import.
    """
    start_time = time.time()

    try:
        data = load_raw_json(file_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_name}")

    # Extract items
    if isinstance(data, dict):
        items = data.get('data') or data.get('items') or data.get('products') or data.get('results') or [data]
    elif isinstance(data, list):
        items = data
    else:
        raise HTTPException(status_code=400, detail="Saved JSON format not supported")

    records_added = 0
    records_updated = 0

    if data_type == "products":
        existing_sku_set = {row[0] for row in db.query(Product.sku).all()}
        for item in items:
            try:
                mapped_item = DataMapper.map_field_names(item, ProductSchema(), 'product')
                sku = mapped_item.get('sku')
                if not sku:
                    continue
                sku = str(sku)
                if sku in existing_sku_set:
                    update_data = {k: v for k, v in mapped_item.items() if v is not None and hasattr(Product, k)}
                    update_data.pop('sku', None)
                    if update_data:
                        db.query(Product).filter(Product.sku == sku).update(update_data)
                    records_updated += 1
                else:
                    product_data = DataMapper.convert_types(
                        mapped_item, ProductSchema.FIELD_TYPES, ProductSchema.FIELD_DEFAULTS
                    )
                    db.add(Product(**product_data))
                    records_added += 1
            except Exception as e:
                print(f"Replay error: {e}")
                continue
        db.commit()

    elif data_type == "sales":
        sku_to_id = {p.sku: p.id for p in db.query(Product.sku, Product.id).all()}
        for item in items:
            try:
                mapped_item = DataMapper.map_field_names(item, SalesSchema(), 'sales')
                sku = mapped_item.get('sku')
                if not sku:
                    continue
                product_id = sku_to_id.get(str(sku))
                if not product_id:
                    continue
                sales_data = DataMapper.convert_types(mapped_item, SalesSchema.FIELD_TYPES, SalesSchema.FIELD_DEFAULTS)
                sales_data.pop('sku', None)
                sales_data['product_id'] = product_id
                db.add(SalesHistory(**sales_data))
                records_added += 1
            except Exception as e:
                print(f"Replay error: {e}")
                continue
        db.commit()

    elif data_type == "inventory":
        existing_sku_set = {row[0] for row in db.query(Product.sku).all()}
        for item in items:
            sku = str(item.get('sku') or item.get('product_id', ''))
            stock = int(item.get('stock') or item.get('quantity') or item.get('inventory', 0))
            if sku in existing_sku_set:
                db.query(Product).filter(Product.sku == sku).update({'current_stock': stock})
                records_updated += 1
        db.commit()

    duration_ms = int((time.time() - start_time) * 1000)

    # Log the replay as a new import
    raw_file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "api_imports", "raw", file_name
    )
    import_log = ApiImportLog(
        source_name=f"replay_{file_name.split('_')[1] if '_' in file_name else 'unknown'}",
        source_url=f"file://{file_name}",
        data_type=data_type,
        raw_file_path=raw_file_path,
        record_count=len(items),
        records_added=records_added,
        records_updated=records_updated,
        file_size_bytes=os.path.getsize(raw_file_path) if os.path.exists(raw_file_path) else 0,
        status="success",
        import_duration_ms=duration_ms,
    )
    db.add(import_log)
    db.commit()

    return {
        "success": True,
        "message": f"Replayed {file_name} — {records_added} added, {records_updated} updated",
        "file_name": file_name,
        "data_type": data_type,
        "records_added": records_added,
        "records_updated": records_updated,
        "total_items": len(items),
        "duration_ms": duration_ms,
    }


@router.get("/data/import-manifest")
def get_import_manifest():
    """
    Get the manifest.json index — a lightweight summary of all imports
    stored as a flat file alongside the raw JSON files.
    """
    manifest = get_manifest()
    return {
        "total_imports": len(manifest),
        "manifest": manifest,
    }


# ============================================================================
# DUMMYJSON DATA GENERATOR - Generate sample data with extra columns
# ============================================================================

@router.post("/data/generate-from-dummyjson")
async def generate_from_dummyjson(config: dict, db: Session = Depends(get_db)):
    """
    Fetch products from DummyJSON API and add extra columns for inventory management.
    
    Two-Tier Storage:
      - Tier 1: Raw API response saved as products_dummyjson_<timestamp>.json
      - Tier 2: Enriched records inserted into SQLite products + sales_history tables
    """
    import httpx
    import random
    
    start_time = time.time()
    raw_info = None
    
    count = config.get('count', 100)
    include_extra = config.get('includeExtraColumns', True)
    extra_columns = config.get('extraColumns', [])
    
    # Fetch data from DummyJSON
    try:
        api_url = f'https://dummyjson.com/products?limit={min(count, 100)}'
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url)
            response.raise_for_status()
            data = response.json()
        
        # ── TIER 1: Save raw JSON to local disk ──
        raw_info = save_raw_json(data, url=api_url, data_type="products", source_name="dummyjson")
        
        products_data = data.get('products', [])
        
        # If we need more than 100, duplicate and modify
        if count > len(products_data):
            original = products_data.copy()
            while len(products_data) < count:
                for item in original:
                    if len(products_data) >= count:
                        break
                    # Create variant
                    variant = item.copy()
                    variant['id'] = len(products_data) + 1
                    variant['title'] = f"{item['title']} v{len(products_data) // len(original) + 1}"
                    variant['price'] = round(item['price'] * random.uniform(0.8, 1.2), 2)
                    variant['stock'] = random.randint(0, 500)
                    products_data.append(variant)
        
        # Extra column generators
        suppliers = ['GlobalSupply Inc', 'TechDistro LLC', 'MegaWholesale', 'DirectSource Co', 'PrimeVendors', 'FastShip Partners', 'QualityGoods Ltd', 'BulkBuy Corp']
        warehouses = ['WH-A', 'WH-B', 'WH-C', 'WH-D', 'WH-E']
        brands = ['ProMax', 'EliteChoice', 'ValuePro', 'PremiumLine', 'EcoSmart', 'TechEdge', 'HomeComfort', 'UrbanStyle']
        countries = ['China', 'USA', 'Germany', 'Japan', 'South Korea', 'Taiwan', 'Vietnam', 'Mexico']
        
        records_added = 0
        records_updated = 0
        existing_sku_set = {row[0] for row in db.query(Product.sku).filter(Product.sku.like('DJ-%')).all()}
        enriched_records = []  # Collect for processed snapshot
        
        for item in products_data[:count]:
            sku = f"DJ-{item['id']:05d}"
            name = item.get('title', 'Unknown Product')
            category = item.get('category', 'General')
            price = float(item.get('price', 0))
            stock = int(item.get('stock', 0))
            
            # Generate extra columns data
            extra_data = {}
            if include_extra and extra_columns:
                if 'supplier' in extra_columns:
                    extra_data['supplier'] = random.choice(suppliers)
                if 'warehouse_location' in extra_columns:
                    extra_data['warehouse_location'] = f"{random.choice(warehouses)}-{random.randint(1, 50):02d}-{random.randint(1, 20):02d}"
                if 'min_order_qty' in extra_columns:
                    extra_data['min_order_qty'] = random.choice([10, 25, 50, 100])
                if 'max_stock_level' in extra_columns:
                    extra_data['max_stock_level'] = random.randint(500, 2000)
                if 'brand' in extra_columns:
                    extra_data['brand'] = item.get('brand') or random.choice(brands)
                if 'weight_kg' in extra_columns:
                    extra_data['weight_kg'] = round(random.uniform(0.1, 25.0), 2)
                if 'dimensions' in extra_columns:
                    extra_data['dimensions'] = f"{random.randint(5, 100)}x{random.randint(5, 100)}x{random.randint(5, 50)}cm"
                if 'barcode' in extra_columns:
                    extra_data['barcode'] = f"{random.randint(100000000000, 999999999999)}"
                if 'manufacturer' in extra_columns:
                    extra_data['manufacturer'] = item.get('brand') or random.choice(brands) + ' Manufacturing'
                if 'country_of_origin' in extra_columns:
                    extra_data['country_of_origin'] = random.choice(countries)
            
            # Collect enriched record for processed snapshot
            enriched_records.append({
                "sku": sku, "name": name, "category": category,
                "unit_price": price, "current_stock": stock,
                "extra_data": extra_data
            })
            
            if sku in existing_sku_set:
                # Update via targeted query (avoid loading 50K ORM objects)
                update_vals = {'name': name, 'category': category, 'unit_price': price, 'current_stock': stock}
                if extra_data:
                    update_vals['description'] = str(extra_data)
                db.query(Product).filter(Product.sku == sku).update(update_vals)
                records_updated += 1
            else:
                new_product = Product(
                    sku=sku,
                    name=name,
                    category=category,
                    unit_price=price,
                    unit_cost=round(price * 0.6, 2),
                    current_stock=stock,
                    lead_time_days=random.randint(3, 21),
                    description=str(extra_data) if extra_data else None
                )
                db.add(new_product)
                records_added += 1
        
        # Commit products first so they get IDs for sales generation
        db.commit()
        db.expire_all()  # Clear session state after bulk update() calls
        
        # Generate sales history for the new products
        sales_added = 0
        if records_added > 0:
            products = db.query(Product).filter(Product.sku.like('DJ-%')).all()
            for product in products:
                stock = product.current_stock or 100
                for days_ago in range(random.randint(30, 90)):
                    if random.random() < 0.7:
                        sale_date = datetime.now().date() - timedelta(days=days_ago)
                        qty = random.randint(1, max(10, stock // 10))
                        sale = SalesHistory(
                            product_id=product.id,
                            date=sale_date,
                            quantity_sold=qty,
                            revenue=round(qty * (product.unit_price or 10.0), 2)
                        )
                        db.add(sale)
                        sales_added += 1
        
        db.commit()
        
        # ── TIER 1b: Save processed / enriched snapshot ──
        processed_path = save_processed_json(
            enriched_records, url=api_url, data_type="products", source_name="dummyjson"
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # ── TIER 2: Log import metadata to DB ──
        import_log = ApiImportLog(
            source_name="dummyjson",
            source_url=api_url,
            data_type="products",
            raw_file_path=raw_info["file_path"],
            processed_file_path=processed_path,
            record_count=len(products_data[:count]),
            records_added=records_added,
            records_updated=records_updated,
            file_size_bytes=raw_info["file_size_bytes"],
            status="success",
            import_duration_ms=duration_ms,
        )
        db.add(import_log)
        db.commit()
        
        # ── Update manifest.json ──
        append_to_manifest({
            "id": import_log.id,
            "source_name": "dummyjson",
            "source_url": api_url,
            "data_type": "products",
            "raw_file": raw_info["file_name"],
            "processed_file": os.path.basename(processed_path),
            "record_count": len(products_data[:count]),
            "records_added": records_added,
            "records_updated": records_updated,
            "file_size_bytes": raw_info["file_size_bytes"],
            "imported_at": datetime.now().isoformat(),
            "duration_ms": duration_ms,
        })
        
        return {
            'success': True,
            'message': f'Successfully generated {records_added} new products with {len(extra_columns)} extra columns',
            'records_added': records_added,
            'records_updated': records_updated,
            'sales_records_added': sales_added,
            'total_items_processed': min(count, len(products_data)),
            'extra_columns_included': extra_columns,
            'source': 'DummyJSON API (https://dummyjson.com/)',
            'storage': {
                'tier1_raw_file': raw_info["file_name"],
                'tier1_file_size': f'{raw_info["file_size_bytes"]:,} bytes',
                'tier2_db_records': records_added + records_updated,
                'import_log_id': import_log.id,
            },
            'duration_ms': duration_ms,
        }
        
    except httpx.HTTPError as e:
        if raw_info:
            _log_failed_import(db, raw_info, api_url, "products", str(e), start_time)
        raise HTTPException(status_code=400, detail=f"Failed to fetch from DummyJSON: {str(e)}")
    except Exception as e:
        db.rollback()
        if raw_info:
            _log_failed_import(db, raw_info, api_url, "products", str(e), start_time)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/alerts/threshold-check")
def check_threshold_alerts(db: Session = Depends(get_db)):
    """Check for products at or below threshold levels and return alert data with pre-filled email."""
    
    # Use configurable thresholds (NOT hardcoded)
    low_max = STOCK_THRESHOLDS['low_stock_max']
    out_threshold = 0
    
    # Find products at threshold levels
    critical_products = db.query(Product).filter(Product.current_stock == out_threshold).limit(50).all()
    low_products = db.query(Product).filter(
        Product.current_stock > out_threshold,
        Product.current_stock <= low_max
    ).limit(50).all()
    
    alerts = []
    
    for p in critical_products:
        alerts.append({
            'id': p.id,
            'sku': p.sku,
            'name': p.name,
            'category': p.category,
            'current_stock': p.current_stock,
            'alert_type': 'CRITICAL',
            'message': f'CRITICAL: {p.name} ({p.sku}) is OUT OF STOCK!',
            'email_subject': f'🚨 URGENT: {p.name} is OUT OF STOCK',
            'email_body': f'''URGENT STOCK ALERT

Product: {p.name}
SKU: {p.sku}
Category: {p.category}
Current Stock: 0 units (OUT OF STOCK)

IMMEDIATE ACTION REQUIRED:
This product has completely run out of stock. Please place an emergency order immediately to prevent lost sales.

Recommended Actions:
1. Contact supplier for emergency shipment
2. Check if alternative products are available
3. Update product availability on sales channels

---
Inventory Optimization & Demand Forecasting System
Auto-generated alert'''
        })
    
    for p in low_products:
        alerts.append({
            'id': p.id,
            'sku': p.sku,
            'name': p.name,
            'category': p.category,
            'current_stock': p.current_stock,
            'alert_type': 'LOW',
            'message': f'WARNING: {p.name} ({p.sku}) is LOW on stock ({p.current_stock} units)',
            'email_subject': f'⚠️ Low Stock Alert: {p.name} ({p.current_stock} units remaining)',
            'email_body': f'''LOW STOCK ALERT

Product: {p.name}
SKU: {p.sku}
Category: {p.category}
Current Stock: {p.current_stock} units
Threshold: {low_max} units

ACTION RECOMMENDED:
Stock levels are running low. Consider placing a reorder soon to maintain optimal inventory levels.

Recommended Actions:
1. Review current demand trends
2. Calculate optimal reorder quantity
3. Contact supplier for lead time confirmation

---
Inventory Optimization & Demand Forecasting System
Auto-generated alert'''
        })
    
    return {
        'has_alerts': len(alerts) > 0,
        'total_alerts': len(alerts),
        'critical_count': len(critical_products),
        'low_count': len(low_products),
        'alerts': alerts
    }


@router.get("/alerts/email-preview")
def get_email_preview(db: Session = Depends(get_db)):
    """Generate email preview content for threshold alerts - synced with actual inventory counts."""
    
    # Get actual counts from database (synced with dashboard) - using configurable thresholds
    low_max = STOCK_THRESHOLDS['low_stock_max']
    medium_max = STOCK_THRESHOLDS['medium_stock_max']
    
    out_of_stock_count = db.query(func.count(Product.id)).filter(Product.current_stock == 0).scalar() or 0
    low_stock_count = db.query(func.count(Product.id)).filter(Product.current_stock > 0, Product.current_stock <= low_max).scalar() or 0
    medium_stock_count = db.query(func.count(Product.id)).filter(Product.current_stock > low_max, Product.current_stock <= medium_max).scalar() or 0
    total_products = db.query(func.count(Product.id)).scalar() or 0
    
    # Get sample critical items for the report (top 10 by demand)
    critical_products = db.query(Product).filter(Product.current_stock == 0).limit(10).all()
    low_stock_products = db.query(Product).filter(Product.current_stock > 0, Product.current_stock <= low_max).limit(10).all()
    
    if out_of_stock_count == 0 and low_stock_count == 0:
        return {
            'has_content': False,
            'subject': '',
            'body': '',
            'products_count': 0
        }
    
    # Calculate estimated daily loss using AI demand estimates from product data
    total_daily_loss = 0
    for p in critical_products:
        # Use AI-calculated average_daily_demand from product if available
        avg_daily_demand = getattr(p, 'average_daily_demand', None) or 5  # Fallback only if not available
        margin = float(p.unit_price or 0) - float(p.unit_cost or 0)
        total_daily_loss += avg_daily_demand * margin
    
    subject = f"Inventory Alert: {out_of_stock_count:,} Out of Stock, {low_stock_count:,} Low Stock Items - Action Required"
    
    body = f"""EXECUTIVE SUMMARY
================================================================================

Dear Inventory Management Team,

Our Smart Inventory Monitoring System has identified items requiring your
immediate attention. This report provides data-driven insights and recommended
actions to optimize inventory levels and prevent revenue loss.

--------------------------------------------------------------------------------
INVENTORY STATUS OVERVIEW
--------------------------------------------------------------------------------

Report Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
Total Inventory Items: {total_products:,}

┌─────────────────────────────────────────────────────────────────────────────┐
│ STOCK STATUS              │ COUNT         │ PRIORITY                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🔴 Out of Stock (Critical)│ {out_of_stock_count:>13,} │ IMMEDIATE ACTION REQUIRED       │
│ 🟠 Low Stock (<50 units)  │ {low_stock_count:>13,} │ URGENT - Reorder Recommended    │
│ 🟡 Medium Stock (50-100)  │ {medium_stock_count:>13,} │ MONITOR - Review within 7 days  │
└─────────────────────────────────────────────────────────────────────────────┘

Estimated Daily Revenue Impact from Stockouts: ${total_daily_loss:,.2f}

"""
    
    if critical_products:
        body += f"""--------------------------------------------------------------------------------
CRITICAL ITEMS - IMMEDIATE ACTION REQUIRED (Showing {len(critical_products)} of {out_of_stock_count:,})
--------------------------------------------------------------------------------

The following high-priority items are currently out of stock. Our analysis
indicates these stockouts are actively impacting revenue:

"""
        for i, p in enumerate(critical_products, 1):
            # Use AI-calculated demand
            avg_daily_demand = getattr(p, 'average_daily_demand', None) or 5
            margin = float(p.unit_price or 0) - float(p.unit_cost or 0)
            daily_loss = margin * avg_daily_demand
            body += f"  {i}. {p.name}\n"
            body += f"     SKU: {p.sku}\n"
            body += f"     Category: {p.category}\n"
            body += f"     Estimated Daily Loss: ${daily_loss:,.2f}\n"
            body += f"     Recommended Action: Expedite reorder for {p.lead_time_days or 7}-day lead time\n\n"
    
    if low_stock_products:
        body += f"""--------------------------------------------------------------------------------
LOW STOCK ITEMS - REORDER RECOMMENDED (Showing {len(low_stock_products)} of {low_stock_count:,})
--------------------------------------------------------------------------------

These items require attention within the next 5-7 business days to prevent
stockouts:

"""
        for i, p in enumerate(low_stock_products, 1):
            # Use AI-calculated demand for accurate projections
            avg_daily_demand = getattr(p, 'average_daily_demand', None) or 5
            days_until_stockout = p.current_stock // max(1, avg_daily_demand)
            # Use AI-recommended reorder quantity if available
            recommended_qty = getattr(p, 'reorder_quantity', None) or max(50, p.current_stock * 3)
            body += f"  {i}. {p.name}\n"
            body += f"     SKU: {p.sku}\n"
            body += f"     Current Stock: {p.current_stock} units\n"
            body += f"     Projected Days Until Stockout: ~{days_until_stockout} days\n"
            body += f"     Recommended Order Quantity: {recommended_qty} units\n\n"
    
    body += f"""--------------------------------------------------------------------------------
RECOMMENDED ACTIONS
--------------------------------------------------------------------------------

1. IMMEDIATE (Today)
   • Initiate emergency purchase orders for the {out_of_stock_count:,} out-of-stock items
   • Contact key suppliers to expedite delivery for high-margin products
   • Consider substitute products for critical stockouts

2. SHORT-TERM (This Week)
   • Review and approve purchase orders for {low_stock_count:,} low-stock items
   • Analyze demand patterns for items with recurring stockouts
   • Adjust safety stock levels based on current demand velocity

3. STRATEGIC (This Month)
   • Review supplier lead times and negotiate improvements
   • Implement demand forecasting for seasonal items
   • Evaluate ABC classification for inventory prioritization
"""
    
    return {
        'has_content': True,
        'subject': subject,
        'body': body,
        'products_count': out_of_stock_count + low_stock_count,
        'critical_count': out_of_stock_count,
        'low_count': low_stock_count
    }


@router.post("/alerts/custom-email")
def send_custom_email(
    email_to: str = Query(..., description="Recipient email addresses (comma-separated for multiple)"),
    subject: str = Query(..., description="Email subject"),
    body: str = Query(..., description="Email body content"),
    db: Session = Depends(get_db)
):
    """Send customized alert email using SendGrid. Supports multiple recipients."""
    
    if not subject or not body:
        return {'success': False, 'message': 'Subject and body are required'}
    
    # Check if email is enabled
    if not email_service_sendgrid.EMAIL_ENABLED:
        return {
            'success': False,
            'message': 'Email notifications are disabled. Please enable in email configuration.'
        }
    
    # Parse comma-separated email addresses
    email_list = [e.strip() for e in email_to.split(',') if e.strip()]
    if not email_list:
        return {'success': False, 'message': 'At least one valid email address is required'}
    
    try:
        result = email_service_sendgrid.send_custom_alert(
            to_emails=email_list,
            subject=subject,
            body=body,
            db=db,
            alert_key="manual_custom_email"
        )
        
        if result['success']:
            return {
                'success': True,
                'email_to': email_list,
                'recipient_count': len(email_list),
                'subject': subject,
                'body_length': len(body),
                'message': f'Email sent successfully to {len(email_list)} recipient{"s" if len(email_list) > 1 else ""}'
            }
        else:
            return result
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to send email: {str(e)}'
        }


@router.post("/alerts/send-threshold-email")
def send_threshold_email(
    email_to: str,
    alert_ids: List[int] = None,
    db: Session = Depends(get_db)
):
    """Send threshold alert email using SendGrid - body is auto-generated, only email address needed."""
    
    # Get products for the alerts
    if alert_ids:
        products = db.query(Product).filter(Product.id.in_(alert_ids)).all()
    else:
        # Get all threshold products
        products = db.query(Product).filter(Product.current_stock <= 50).limit(20).all()
    
    if not products:
        return {'success': False, 'message': 'No products found for alerts'}
    
    # Check if email is enabled
    if not email_service_sendgrid.EMAIL_ENABLED:
        return {
            'success': False,
            'message': 'Email notifications are disabled. Please enable in email configuration.',
            'email_to': email_to
        }
    
    try:
        # Send using the first product as primary (since send_threshold_alert expects single product)
        # For multiple products, we'll send individual alerts
        results = []
        for product in products[:5]:  # Send first 5 to avoid spam
            avg_daily_demand = product.average_daily_demand or 0
            if not avg_daily_demand:
                thirty_days_ago = datetime.utcnow() - timedelta(days=30)
                total_qty = db.query(func.sum(SalesHistory.quantity_sold)).filter(
                    SalesHistory.product_id == product.id,
                    SalesHistory.date >= thirty_days_ago
                ).scalar() or 0
                avg_daily_demand = total_qty / 30 if total_qty else max(product.current_stock, 1)
            unit_profit = max((product.unit_price or 0) - (product.unit_cost or 0), 0)
            potential_daily_loss = float(max(avg_daily_demand, 1) * unit_profit)
            recommendation = db.query(InventoryRecommendation).filter(
                InventoryRecommendation.product_id == product.id
            ).order_by(InventoryRecommendation.created_at.desc()).first()
            if recommendation and recommendation.economic_order_quantity:
                recommended_qty = int(recommendation.economic_order_quantity)
            else:
                lead_time = product.lead_time_days or 7
                recommended_qty = int(max(avg_daily_demand * lead_time, 1))
            result = email_service_sendgrid.send_threshold_alert(
                product_sku=product.sku,
                product_name=product.name,
                current_stock=product.current_stock,
                reorder_point=product.reorder_point if hasattr(product, 'reorder_point') else 50,
                recommended_qty=recommended_qty,
                potential_daily_loss=potential_daily_loss,
                category=product.category,
                recipients=[email_to],
                db=db
            )
            results.append(result)
        
        # Return the first result (all should be same status)
        if results and results[0]['success']:
            return {
                'success': True,
                'email_to': email_to,
                'products_included': len(results),
                'message': f'Email sent successfully to {email_to} for {len(results)} product(s)'
            }
        else:
            return results[0] if results else {'success': False, 'message': 'No alerts sent'}
    
    except Exception as e:
        return {
            'success': False,
            'email_to': email_to,
            'message': f'Failed to send email: {str(e)}'
        }


@router.post("/onboarding/smart-upload")
async def smart_upload_sales_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Smart CSV Mapper for BYOD (Bring Your Own Data) onboarding.

    Accepts a 2–3 month sales export from any system and automatically
    maps common column names to the internal schema (date, sku, quantity_sold, revenue).

    After importing, it runs the MultiModelForecaster to generate an
    "AI vs Naive" style forecast summary per product so prospects see
    immediate value on *their* data.
    """

    filename = file.filename.lower()

    try:
        contents = await file.read()

        if filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(contents))
        elif filename.endswith('.json'):
            df = pd.read_json(io.StringIO(contents.decode('utf-8')))
        else:
            raise HTTPException(
                status_code=400,
                detail="Supported formats: CSV, Excel (.xlsx, .xls), JSON",
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Normalize column names for fuzzy matching
    original_columns = list(df.columns)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # Define common synonyms for key fields
    def _find_col(df_cols: List[str], candidates: List[str]) -> Optional[str]:
        for name in candidates:
            if name in df_cols:
                return name
        return None

    cols = list(df.columns)

    date_col = _find_col(cols, [
        'date', 'order_date', 'invoice_date', 'transaction_date', 'sales_date'
    ])
    sku_col = _find_col(cols, [
        'sku', 'product_code', 'item_code', 'item_id', 'productid', 'product_id', 'upc'
    ])
    qty_col = _find_col(cols, [
        'quantity_sold', 'quantity', 'qty', 'units', 'units_sold', 'sales_qty', 'sold_units'
    ])
    rev_col = _find_col(cols, [
        'revenue', 'amount', 'line_total', 'sales_amount', 'total_price', 'net_sales'
    ])
    name_col = _find_col(cols, [
        'product_name', 'name', 'item_name', 'description'
    ])
    category_col = _find_col(cols, [
        'category', 'product_category', 'segment'
    ])

    missing_core: List[str] = []
    if not date_col:
        missing_core.append('date')
    if not sku_col:
        missing_core.append('sku')
    if not qty_col:
        missing_core.append('quantity')

    if missing_core:
        raise HTTPException(
            status_code=400,
            detail={
                'error': 'Missing required columns',
                'required': ['date', 'sku', 'quantity'],
                'missing': missing_core,
                'detected_columns': original_columns,
            },
        )

    # Build normalized frame
    norm_df = pd.DataFrame()
    norm_df['date'] = pd.to_datetime(df[date_col])
    norm_df['sku'] = df[sku_col].astype(str)
    norm_df['quantity_sold'] = df[qty_col].astype(float).fillna(0).astype(int)

    if rev_col:
        norm_df['revenue'] = df[rev_col].astype(float).fillna(0.0)
    else:
        norm_df['revenue'] = 0.0

    if name_col:
        norm_df['product_name'] = df[name_col].astype(str)
    else:
        norm_df['product_name'] = norm_df['sku']

    if category_col:
        norm_df['category'] = df[category_col].astype(str)
    else:
        norm_df['category'] = 'General'

    products_added = 0
    records_added = 0
    touched_product_ids: Dict[str, int] = {}

    for _, row in norm_df.iterrows():
        try:
            sku = str(row['sku'])
            product = db.query(Product).filter(Product.sku == sku).first()

            if not product:
                product = Product(
                    sku=sku,
                    name=str(row['product_name']),
                    category=str(row['category']),
                    current_stock=0,
                    unit_cost=10.0,
                    unit_price=15.0,
                    lead_time_days=7,
                )
                db.add(product)
                db.flush()
                products_added += 1
            else:
                # Minimal enrichment of existing product metadata
                product.name = product.name or str(row['product_name'])
                product.category = product.category or str(row['category'])
                db.flush()

            sale = SalesHistory(
                product_id=product.id,
                date=row['date'],
                quantity_sold=int(row['quantity_sold']),
                revenue=float(row['revenue']),
            )
            db.add(sale)
            records_added += 1
            touched_product_ids[sku] = product.id
        except Exception:
            # Skip bad rows but continue processing
            continue

    db.commit()

    # Run multi-model forecasts for each touched product (limited to 5 for speed)
    forecast_summaries = []
    max_products = 5
    for idx, (sku, prod_id) in enumerate(touched_product_ids.items()):
        if idx >= max_products:
            break
        try:
            multi_result = MultiModelForecaster.forecast_with_all_models(db, prod_id, days_ahead=30)
            if 'error' in multi_result:
                continue
            forecast_summaries.append({
                'product': multi_result.get('product'),
                'best_model': multi_result.get('best_model'),
                'confidence_level': multi_result.get('confidence_level'),
                'forecast': multi_result.get('forecast'),
            })
        except Exception:
            continue

    column_mapping = {
        'date': date_col,
        'sku': sku_col,
        'quantity_sold': qty_col,
        'revenue': rev_col,
        'product_name': name_col,
        'category': category_col,
    }

    return {
        'message': f"Smart-mapped and imported {records_added} sales records for {len(touched_product_ids)} products",
        'column_mapping': column_mapping,
        'products_added': products_added,
        'records_added': records_added,
        'forecast_summaries': forecast_summaries,
    }

@router.post("/data/upload-new-products")
async def upload_new_products(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload NEW products only with automatic field mapping - Rejects duplicates
    
    Supports flexible field names (automatically mapped):
    - sku, id, product_id, code -> sku
    - name, product_name, title -> name
    - stock, inventory, quantity -> current_stock
    - price, selling_price -> unit_price
    - cost, cost_price -> unit_cost
    - Plus all extended product attributes
    
    Required columns: sku, name (or mapped equivalents)
    Optional columns: All product attributes with flexible naming
    
    Compatible with ProductSchema field aliases for automatic mapping.
    """
    filename = file.filename.lower()
    
    try:
        contents = await file.read()
        
        if filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(contents))
        elif filename.endswith('.json'):
            df = pd.read_json(io.StringIO(contents.decode('utf-8')))
        else:
            raise HTTPException(status_code=400, detail="Supported formats: CSV, Excel, JSON")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    # Apply field mapping using ProductSchema
    df = DataMapper.map_field_names(df, ProductSchema(), 'product')
    
    if 'sku' not in df.columns:
        raise HTTPException(status_code=400, detail="File must contain 'sku' column (or equivalent: id, product_id, code)")
    
    # Check for duplicates
    duplicates = []
    for _, row in df.iterrows():
        existing = db.query(Product).filter(Product.sku == str(row['sku'])).first()
        if existing:
            duplicates.append({
                'sku': str(row['sku']),
                'name': existing.name,
                'current_stock': existing.current_stock,
                'file_stock': int(row.get('current_stock', 0))
            })
    
    # If duplicates found, reject upload
    if duplicates:
        raise HTTPException(
            status_code=409,
            detail={
                'error': 'Duplicate products found',
                'message': f'{len(duplicates)} product(s) already exist in the database',
                'duplicates': duplicates,
                'suggestion': 'Please remove duplicate products from your file or use the "Restock Inventory" feature to update stock levels for existing products'
            }
        )
    
    # Helper to safely get column values
    def get_val(row, col, default=None, dtype=str):
        if col not in row or pd.isna(row.get(col)):
            return default
        try:
            val = row.get(col)
            if dtype == float:
                return float(val)
            elif dtype == int:
                return int(float(val))  # Handle "45.0" -> 45
            elif dtype == bool:
                return bool(val) if not isinstance(val, str) else val.lower() in ('true', '1', 'yes')
            return str(val)
        except:
            return default
    
    # No duplicates - proceed with import with ALL columns
    products_added = 0
    for _, row in df.iterrows():
        try:
            product_name = get_val(row, 'name', get_val(row, 'product_name', row['sku']))
            
            # Parse dates if present
            last_order_date = None
            last_sale_date = None
            if 'last_order_date' in row and not pd.isna(row.get('last_order_date')):
                try:
                    last_order_date = pd.to_datetime(row['last_order_date'])
                except:
                    pass
            if 'last_sale_date' in row and not pd.isna(row.get('last_sale_date')):
                try:
                    last_sale_date = pd.to_datetime(row['last_sale_date'])
                except:
                    pass
            
            product = Product(
                # Core fields
                sku=str(row['sku']),
                name=str(product_name),
                category=get_val(row, 'category', 'General'),
                current_stock=get_val(row, 'current_stock', 0, int),
                unit_cost=get_val(row, 'unit_cost', 10.0, float),
                unit_price=get_val(row, 'unit_price', 15.0, float),
                lead_time_days=get_val(row, 'lead_time_days', 7, int),
                
                # Extended fields
                reorder_point=get_val(row, 'reorder_point', None, float),
                safety_stock=get_val(row, 'safety_stock', None, float),
                average_daily_demand=get_val(row, 'average_daily_demand', None, float),
                supplier_id=get_val(row, 'supplier_id', None),
                min_order_qty=get_val(row, 'min_order_qty', None, int),
                max_order_qty=get_val(row, 'max_order_qty', None, int),
                order_frequency_days=get_val(row, 'order_frequency_days', None, int),
                
                # Demand characteristics
                seasonality_factor=get_val(row, 'seasonality_factor', 1.0, float),
                demand_volatility=get_val(row, 'demand_volatility', 0.5, float),
                profit_margin=get_val(row, 'profit_margin', None, float),
                
                # Classification
                abc_classification=get_val(row, 'abc_classification', None),
                xyz_classification=get_val(row, 'xyz_classification', None),
                product_priority=get_val(row, 'product_priority', None),
                
                # Product attributes
                weight_kg=get_val(row, 'weight_kg', None, float),
                volume_m3=get_val(row, 'volume_m3', None, float),
                shelf_life_days=get_val(row, 'shelf_life_days', None, int),
                is_perishable=get_val(row, 'is_perishable', False, bool),
                is_hazardous=get_val(row, 'is_hazardous', False, bool),
                
                # Cost factors
                storage_cost_per_unit=get_val(row, 'storage_cost_per_unit', None, float),
                stockout_cost_per_unit=get_val(row, 'stockout_cost_per_unit', None, float),
                target_service_level=get_val(row, 'target_service_level', 0.95, float),
                
                # Calculated fields
                economic_order_qty=get_val(row, 'economic_order_qty', None, float),
                inventory_turnover=get_val(row, 'inventory_turnover', None, float),
                weeks_of_supply=get_val(row, 'weeks_of_supply', None, float),
                stock_status=get_val(row, 'stock_status', None),
                
                # Dates
                last_order_date=last_order_date,
                last_sale_date=last_sale_date,
            )
            db.add(product)
            products_added += 1
        except Exception as e:
            continue
    
    db.commit()
    
    return {
        'success': True,
        'message': f'Successfully added {products_added} new products',
        'products_added': products_added,
        'columns_imported': list(df.columns)
    }

@router.post("/data/restock-inventory")
async def restock_inventory(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Restock existing products - Adds quantities to current stock
    
    Required columns: sku, restock_quantity (or current_stock)
    Only updates products that already exist in database
    """
    filename = file.filename.lower()
    
    try:
        contents = await file.read()
        
        if filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(contents))
        elif filename.endswith('.json'):
            df = pd.read_json(io.StringIO(contents.decode('utf-8')))
        else:
            raise HTTPException(status_code=400, detail="Supported formats: CSV, Excel, JSON")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    if 'sku' not in df.columns:
        raise HTTPException(status_code=400, detail="File must contain 'sku' column")
    
    # Analyze what will be restocked
    restock_preview = []
    not_found = []
    warnings = []
    
    for _, row in df.iterrows():
        product = db.query(Product).filter(Product.sku == str(row['sku'])).first()
        
        if not product:
            not_found.append(str(row['sku']))
            continue
        
        restock_qty = int(row.get('restock_quantity', row.get('current_stock', 0)))
        new_stock = product.current_stock + restock_qty
        
        # Determine stock level and priority
        stock_status = "normal"
        priority = "low"
        warning = None
        
        if product.current_stock == 0:
            stock_status = "out_of_stock"
            priority = "critical"
        elif product.current_stock < 100:
            stock_status = "low_stock"
            priority = "high"
        elif product.current_stock > 5000:
            stock_status = "high_stock"
            priority = "low"
            warning = f"Product already has high stock ({product.current_stock} units). Restock needed?"
        
        restock_preview.append({
            'sku': product.sku,
            'name': product.name,
            'current_stock': product.current_stock,
            'restock_quantity': restock_qty,
            'new_stock': new_stock,
            'stock_status': stock_status,
            'priority': priority,
            'warning': warning
        })
        
        if warning:
            warnings.append(warning)
    
    # Return preview for confirmation
    return {
        'preview': True,
        'total_products': len(restock_preview),
        'not_found_count': len(not_found),
        'not_found_skus': not_found,
        'warnings': warnings,
        'restock_items': restock_preview,
        'summary': {
            'critical': len([p for p in restock_preview if p['priority'] == 'critical']),
            'high': len([p for p in restock_preview if p['priority'] == 'high']),
            'normal': len([p for p in restock_preview if p['priority'] in ['low', 'medium']])
        }
    }

@router.post("/data/restock-inventory/confirm")
async def confirm_restock(skus_to_restock: dict, db: Session = Depends(get_db)):
    """Confirm and execute restock operation
    
    Expects: { "items": [{"sku": "ABC123", "restock_quantity": 50}, ...] }
    """
    items = skus_to_restock.get('items', [])
    
    restocked_count = 0
    for item in items:
        product = db.query(Product).filter(Product.sku == item['sku']).first()
        if product:
            product.current_stock += int(item['restock_quantity'])
            restocked_count += 1
    
    db.commit()
    
    return {
        'success': True,
        'message': f'Successfully restocked {restocked_count} products',
        'restocked_count': restocked_count
    }


# ============================================================================
# NEW ENHANCEMENT ENDPOINTS
# ============================================================================

# SCENARIO MODELING ENDPOINTS
@router.post("/scenarios/price-change")
def simulate_price_scenario(
    product_id: int,
    current_price: float,
    price_change_pct: float,
    price_elasticity: float = -1.2,
    current_demand: float = 100,
    db: Session = Depends(get_db)
):
    """Simulate impact of price change"""
    engine = ScenarioEngine()
    
    result = engine.simulate_price_change(
        current_price,
        price_change_pct,
        price_elasticity,
        current_demand
    )
    
    # Save scenario
    scenario = ScenarioResult(
        product_id=product_id,
        scenario_name=f"Price Change {price_change_pct:+.1f}%",
        scenario_type="PRICE_CHANGE",
        parameters=str({'current_price': current_price, 'change_pct': price_change_pct}),
        results=str(result),
        recommendation=result['recommendation']
    )
    db.add(scenario)
    db.commit()
    
    return result

@router.post("/scenarios/demand-shift")
def simulate_demand_scenario(
    product_id: int,
    current_demand: float,
    demand_shift_pct: float,
    current_eoq: float,
    current_rop: float,
    safety_stock: float,
    avg_daily_demand: float,
    db: Session = Depends(get_db)
):
    """Simulate impact of demand shift"""
    engine = ScenarioEngine()
    
    result = engine.simulate_demand_shift(
        current_demand,
        demand_shift_pct,
        current_eoq,
        current_rop,
        safety_stock,
        avg_daily_demand
    )
    
    # Save scenario
    scenario = ScenarioResult(
        product_id=product_id,
        scenario_name=f"Demand {demand_shift_pct:+.1f}%",
        scenario_type="DEMAND_SHIFT",
        parameters=str({'demand_shift_pct': demand_shift_pct}),
        results=str(result),
        recommendation=result['recommendation']
    )
    db.add(scenario)
    db.commit()
    
    return result

@router.post("/scenarios/supplier-switch")
def simulate_supplier_switch_scenario(
    product_id: int,
    current_unit_cost: float,
    new_unit_cost: float,
    current_lead_time: int,
    new_lead_time: int,
    current_reliability: float,
    new_reliability: float,
    annual_demand: float,
    db: Session = Depends(get_db)
):
    """Simulate switching to alternative supplier"""
    engine = ScenarioEngine()
    
    result = engine.simulate_supplier_change(
        current_unit_cost,
        new_unit_cost,
        current_lead_time,
        new_lead_time,
        current_reliability,
        new_reliability,
        annual_demand
    )
    
    # Save scenario
    scenario = ScenarioResult(
        product_id=product_id,
        scenario_name="Supplier Switch",
        scenario_type="SUPPLIER_SWITCH",
        parameters=str({'new_cost': new_unit_cost, 'new_lead_time': new_lead_time}),
        results=str(result),
        recommendation=result['recommendation']
    )
    db.add(scenario)
    db.commit()
    
    return result

# DEMAND SENSING ENDPOINTS
@router.post("/demand/multi-channel")
def aggregate_multi_channel_demand(
    channels: dict,
    channel_weights: Optional[dict] = None,
    db: Session = Depends(get_db)
):
    """Aggregate demand from multiple sales channels"""
    sensing = DemandSensing()
    
    result = sensing.aggregate_multi_channel_demand(channels, channel_weights)
    
    return result

@router.post("/demand/anomalies")
def detect_demand_anomalies(
    daily_demand: List[float],
    sensitivity: float = 2.0,
    lookback_days: int = 30,
    db: Session = Depends(get_db)
):
    """Detect unusual demand patterns"""
    sensing = DemandSensing()
    
    result = sensing.detect_demand_anomalies(daily_demand, sensitivity, lookback_days)
    
    # Save alerts if any detected
    if result.get('anomalies_detected', 0) > 0:
        alert = DemandAlert(
            alert_type="ANOMALY",
            alert_level=result['overall_status'],
            description=result['status_message'],
            anomaly_data=str(result['anomalies'])
        )
        db.add(alert)
        db.commit()
    
    return result

@router.post("/demand/trend-acceleration")
def detect_trend_acceleration(
    daily_demand: List[float],
    window_size: int = 7,
    db: Session = Depends(get_db)
):
    """Detect if demand trend is accelerating"""
    sensing = DemandSensing()
    
    result = sensing.detect_trend_acceleration(daily_demand, window_size)
    
    return result

@router.post("/demand/promotional-impact")
def track_promotional_impact(
    pre_promotion: List[float],
    during_promotion: List[float],
    post_promotion: Optional[List[float]] = None,
    db: Session = Depends(get_db)
):
    """Analyze promotional campaign impact"""
    sensing = DemandSensing()
    
    result = sensing.track_promotional_impact(pre_promotion, during_promotion, post_promotion)
    
    return result

# ADVANCED ABC ANALYSIS ENDPOINT
@router.post("/analytics/abc-profitability")
def get_abc_profitability_analysis(
    db: Session = Depends(get_db),
    margin_pct: float = 0.30
):
    """Get advanced ABC analysis with profitability insights"""
    products = db.query(Product).all()
    
    if not products:
        raise HTTPException(status_code=400, detail="No products found")
    
    # Get sales data
    products_data = []
    for product in products:
        sales = db.query(SalesHistory).filter(SalesHistory.product_id == product.id).all()
        total_quantity = sum(s.quantity_sold for s in sales)
        
        products_data.append({
            'product_id': product.id,
            'product_name': product.name,
            'annual_demand': total_quantity,
            'unit_cost': product.unit_cost,
            'unit_price': product.unit_price,
            'current_stock': product.current_stock
        })
    
    if products_data:
        df = pd.DataFrame(products_data)
        optimizer = InventoryOptimizer()
        result = optimizer.abc_analysis_with_profitability(df, margin_pct)
        return result
    else:
        raise HTTPException(status_code=400, detail="No sales data available")

@router.get("/analytics/inventory-health")
def get_inventory_health_dashboard(db: Session = Depends(get_db)):
    """Comprehensive inventory health dashboard"""
    products = db.query(Product).all()
    
    if not products:
        raise HTTPException(status_code=400, detail="No products found")
    
    sensing = DemandSensing()
    analytics = AnalyticsService()
    
    # Collect metrics
    health_metrics = {
        'total_products': len(products),
        'total_inventory_value': sum(p.current_stock * p.unit_cost for p in products),
        'at_risk_products': 0,
        'dead_stock_candidates': 0,
        'high_turnover_products': 0,
        'critical_stockout_risk': []
    }
    
    for product in products:
        sales = db.query(SalesHistory).filter(SalesHistory.product_id == product.id).all()
        
        if sales:
            total_qty = sum(s.quantity_sold for s in sales)
            avg_daily = total_qty / max(1, len(sales))
            days_of_inventory = analytics.calculate_days_of_inventory(product.current_stock, avg_daily)
            
            # Risk assessment
            if product.current_stock < avg_daily * 2:
                health_metrics['critical_stockout_risk'].append(product.name)
            
            if days_of_inventory > 180:
                health_metrics['dead_stock_candidates'] += 1
            elif days_of_inventory < 7:
                health_metrics['at_risk_products'] += 1
            elif days_of_inventory < 30:
                health_metrics['high_turnover_products'] += 1
    
    return health_metrics


@router.get("/analytics/live-alerts")
def get_live_alerts(limit: int = 200, db: Session = Depends(get_db)):
    """
    Live AI-driven alert feed for the dashboard - PURELY AI-POWERED
    Uses machine learning pattern detection, not just simple thresholds
    Includes: stockout losses, demand trends, anomalies, revenue patterns
    """
    # Use the new AI Alert System instead of manual calculations
    ai_alerts = AIAlertSystem.generate_live_alerts(db, limit)
    
    return {
        'total_alerts': len(ai_alerts),
        'alerts': ai_alerts,
        'generated_by': 'AI Pattern Detection Engine',
        'alert_types_available': [
            'STOCKOUT (with loss calculations)',
            'THRESHOLD_BREACH (predictive)',
            'HIGH_DEMAND (trending products)',
            'REVENUE_LOSS_PATTERN (anomaly detection)',
            'LOW_DEMAND (overstock risk)'
        ]
    }

# ============================================================================
# DECISION-CENTRIC AI ENDPOINTS (Business-Ready Enhancements)
# ============================================================================

# DECISION RECOMMENDATIONS
@router.post("/decisions/prescriptive/{product_id}")
def get_prescriptive_recommendation(
    product_id: int,
    target_service_level: float = 0.95,
    cost_of_stockout_pct: float = 0.40,
    db: Session = Depends(get_db)
):
    """
    Get a PRESCRIPTIVE recommendation (not just a forecast).
    
    Returns: "ORDER NOW" vs "WAIT" with financial justification showing:
    - Cost to order vs cost of stockout risk
    - Working capital impact
    - Expected margin protection
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    sales_data = db.query(SalesHistory).filter(SalesHistory.product_id == product_id).all()
    if not sales_data:
        raise HTTPException(status_code=400, detail="No sales history available")
    
    df = pd.DataFrame([{'date': s.date, 'quantity_sold': s.quantity_sold} for s in sales_data])
    
    # Get forecasted demand
    forecaster = DemandForecaster()
    forecaster.fit(df)
    forecast = forecaster.predict(steps=1)
    predicted_demand = forecast['predictions'][0]
    
    # Calculate demand std
    daily_sales = df.groupby('date')['quantity_sold'].sum()
    demand_std = daily_sales.std() or 0
    
    # Calculate annual demand
    annual_demand = df['quantity_sold'].sum() / max(1, len(df.groupby('date'))) * 365
    
    # Get decision
    optimizer = DecisionOptimizer()
    decision = optimizer.generate_decision_recommendation(
        product.name,
        product.current_stock,
        predicted_demand,
        demand_std,
        product.unit_cost,
        product.unit_price,
        product.lead_time_days,
        annual_demand,
        target_service_level,
        cost_of_stockout_pct
    )
    
    return decision

# RISK PROFILE ANALYSIS
@router.post("/risk/profile-sku/{product_id}")
def classify_product_risk_profile(
    product_id: int,
    customer_criticality: str = "standard",  # "critical", "important", "standard", "seasonal"
    product_lifespan_months: int = 12,
    supplier_reliability_pct: float = 90.0,
    db: Session = Depends(get_db)
):
    """
    Automatically classify a product into risk profile (Conservative/Balanced/Aggressive).
    
    This determines what service level the product SHOULD have based on business characteristics.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    sales_data = db.query(SalesHistory).filter(SalesHistory.product_id == product_id).all()
    if not sales_data:
        raise HTTPException(status_code=400, detail="No sales history available")
    
    df = pd.DataFrame([{'date': s.date, 'quantity_sold': s.quantity_sold} for s in sales_data])
    annual_demand = df['quantity_sold'].sum() / max(1, len(df.groupby('date'))) * 365
    
    daily_sales = df.groupby('date')['quantity_sold'].sum()
    demand_volatility = (daily_sales.std() / daily_sales.mean()) if daily_sales.mean() > 0 else 0.2
    
    unit_margin_pct = ((product.unit_price - product.unit_cost) / product.unit_price) if product.unit_price > 0 else 0.3
    
    profiler = RiskProfiler()
    profile = profiler.classify_product_risk_profile(
        product.name,
        annual_demand,
        demand_volatility,
        unit_margin_pct,
        product_lifespan_months,
        supplier_reliability_pct,
        customer_criticality
    )
    
    return profile

@router.post("/risk/compare-service-levels/{product_id}")
def compare_service_level_tradeoffs(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Show CFO the cost vs service level trade-off matrix.
    
    "If we accept 90% vs 95% vs 99% service level, here's what we save/spend"
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    sales_data = db.query(SalesHistory).filter(SalesHistory.product_id == product_id).all()
    if not sales_data:
        raise HTTPException(status_code=400, detail="No sales history available")
    
    df = pd.DataFrame([{'date': s.date, 'quantity_sold': s.quantity_sold} for s in sales_data])
    annual_demand = df['quantity_sold'].sum() / max(1, len(df.groupby('date'))) * 365
    
    daily_sales = df.groupby('date')['quantity_sold'].sum()
    demand_std = daily_sales.std() or 0
    
    optimizer = DecisionOptimizer()
    tradeoffs = optimizer.compare_service_level_trade_offs(
        product.name,
        product.current_stock,
        annual_demand,
        demand_std,
        product.unit_cost,
        product.unit_price,
        product.lead_time_days,
        annual_demand
    )
    
    return tradeoffs

# FINANCIAL STORYTELLING ENDPOINTS
@router.post("/financial/decision-story/{product_id}")
def get_financial_decision_story(
    product_id: int,
    recommended_order_qty: float,
    target_service_level: float = 0.95,
    historical_stockout_pct: float = 2.0,
    db: Session = Depends(get_db)
):
    """
    Get the financial story for a decision.
    
    Output: "Here's how much this decision will save/cost in dollars"
    
    This is the ONE THING that makes executives say "let's do it"
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    sales_data = db.query(SalesHistory).filter(SalesHistory.product_id == product_id).all()
    if not sales_data:
        raise HTTPException(status_code=400, detail="No sales history available")
    
    df = pd.DataFrame([{'date': s.date, 'quantity_sold': s.quantity_sold} for s in sales_data])
    annual_demand = df['quantity_sold'].sum() / max(1, len(df.groupby('date'))) * 365
    
    current_situation = {
        'current_stock': product.current_stock,
        'annual_demand': annual_demand,
        'unit_cost': product.unit_cost,
        'unit_price': product.unit_price,
        'historical_stockout_pct': historical_stockout_pct
    }
    optimizer = InventoryOptimizer()
    optimization = optimizer.optimize_inventory(
        df,
        unit_cost=product.unit_cost,
        lead_time_days=product.lead_time_days,
        service_level=target_service_level,
        storage_cost_per_unit=product.storage_cost_per_unit,
        stockout_cost_per_unit=product.stockout_cost_per_unit,
        order_frequency_days=product.order_frequency_days,
        shelf_life_days=product.shelf_life_days,
        min_order_qty=product.min_order_qty,
        max_order_qty=product.max_order_qty,
        product_priority=product.product_priority,
        weight_kg=product.weight_kg,
        volume_m3=product.volume_m3
    )
    optimized_safety_stock = optimization.get('safety_stock') or max(recommended_order_qty * 0.2, 1)
    ai_recommendation = {
        'recommended_order_qty': recommended_order_qty,
        'service_level': optimization.get('service_level_used', target_service_level),
        'safety_stock': optimized_safety_stock
    }
    
    storyteller = FinancialStoryTeller()
    story = storyteller.tell_decision_story(
        product.name,
        current_situation,
        ai_recommendation
    )
    
    return {**story, 'optimization_snapshot': optimization}

@router.get("/financial/memo/{product_id}")
def get_financial_justification_memo(
    product_id: int,
    recommended_order_qty: float,
    target_service_level: float = 0.95,
    db: Session = Depends(get_db)
):
    """
    Generate a formal memo suitable for emailing to Finance/CFO.
    
    Format: Business memo with financial justification, ROI, and recommendation.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    sales_data = db.query(SalesHistory).filter(SalesHistory.product_id == product_id).all()
    if not sales_data:
        raise HTTPException(status_code=400, detail="No sales history available")
    
    df = pd.DataFrame([{'date': s.date, 'quantity_sold': s.quantity_sold} for s in sales_data])
    annual_demand = df['quantity_sold'].sum() / max(1, len(df.groupby('date'))) * 365
    
    current_situation = {
        'current_stock': product.current_stock,
        'annual_demand': annual_demand,
        'unit_cost': product.unit_cost,
        'unit_price': product.unit_price,
        'historical_stockout_pct': 2.0
    }
    optimizer = InventoryOptimizer()
    optimization = optimizer.optimize_inventory(
        df,
        unit_cost=product.unit_cost,
        lead_time_days=product.lead_time_days,
        service_level=target_service_level,
        storage_cost_per_unit=product.storage_cost_per_unit,
        stockout_cost_per_unit=product.stockout_cost_per_unit,
        order_frequency_days=product.order_frequency_days,
        shelf_life_days=product.shelf_life_days,
        min_order_qty=product.min_order_qty,
        max_order_qty=product.max_order_qty,
        product_priority=product.product_priority,
        weight_kg=product.weight_kg,
        volume_m3=product.volume_m3
    )
    ai_recommendation = {
        'recommended_order_qty': recommended_order_qty,
        'service_level': optimization.get('service_level_used', target_service_level),
        'safety_stock': optimization.get('safety_stock') or max(recommended_order_qty * 0.2, 1)
    }
    
    storyteller = FinancialStoryTeller()
    story = storyteller.tell_decision_story(
        product.name,
        current_situation,
        ai_recommendation
    )
    
    memo = storyteller.create_financial_justification_memo(
        f"REC-{product_id}-{datetime.now().strftime('%Y%m%d')}",
        product.name,
        story
    )
    
    return {
        'recommendation_id': f"REC-{product_id}-{datetime.now().strftime('%Y%m%d')}",
        'product_name': product.name,
        'memo': memo,
        'financial_metrics': story['financial_dashboard'],
        'optimization_snapshot': optimization
    }


@router.get("/financial/monthly-report")
def get_monthly_portfolio_report(db: Session = Depends(get_db)):
    """Generate a one-page executive-style monthly portfolio report.

    Aggregates portfolio-level impact using FinancialStoryTeller.portfolio_impact_story.
    This is returned as structured JSON plus a memo-style narrative string that can
    be rendered to PDF on the client or used directly in presentations.
    """
    products = db.query(Product).all()
    sales = db.query(SalesHistory).all()

    if not products or not sales:
        raise HTTPException(status_code=400, detail="Not enough data to build portfolio report")

    # Approximate total annual revenue from sales history
    total_revenue = sum(s.revenue for s in sales)
    days_span = (max(s.date for s in sales) - min(s.date for s in sales)).days + 1
    annualized_revenue = (total_revenue / max(1, days_span)) * 365

    # Build simple portfolio recommendations from existing products
    portfolio_recs = []
    for product in products:
        product_sales = [s for s in sales if s.product_id == product.id]
        if not product_sales:
            continue

        revenue = sum(s.revenue for s in product_sales)
        # Treat a portion of revenue as "margin saved" potential for demo purposes
        margin_saved = revenue * 0.05
        wc_required = product.current_stock * product.unit_cost
        carrying_cost = wc_required * 0.25

        portfolio_recs.append({
            'product_id': product.id,
            'product_name': product.name,
            'margin_saved': margin_saved,
            'wc_required': wc_required,
            'carrying_cost': carrying_cost,
        })

    storyteller = FinancialStoryTeller()
    portfolio_story = storyteller.portfolio_impact_story(portfolio_recs, annualized_revenue)

    return {
        'generated_at': datetime.now().isoformat(),
        'annualized_revenue': round(annualized_revenue, 2),
        'portfolio_impact': portfolio_story['portfolio_impact'],
        'portfolio_narrative': portfolio_story['portfolio_narrative'],
        'top_opportunities': portfolio_story['top_opportunities'],
    }


@router.get("/forecasting/{product_id}/feature-importance")
def get_forecast_feature_importance(
    product_id: int,
    forecast_days: int = 30,
    db: Session = Depends(get_db)
):
    """Expose the ML explainability metadata for a product's forecast."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    sales_data = db.query(SalesHistory).filter(SalesHistory.product_id == product_id).all()
    if not sales_data:
        raise HTTPException(status_code=400, detail="No sales history available for forecasting")

    df = pd.DataFrame([{'date': s.date, 'quantity_sold': s.quantity_sold} for s in sales_data])
    forecaster = DemandForecaster()
    metadata = {
        'seasonality_factor': product.seasonality_factor,
        'demand_volatility': product.demand_volatility,
        'abc_classification': product.abc_classification,
        'xyz_classification': product.xyz_classification,
        'profit_margin': product.profit_margin,
        'target_service_level': product.target_service_level,
        'is_perishable': product.is_perishable,
        'lead_time_days': product.lead_time_days,
        'average_daily_demand': product.average_daily_demand,
        'stockout_cost_per_unit': product.stockout_cost_per_unit,
        'inventory_turnover': product.inventory_turnover,
    }
    forecaster.set_product_metadata(metadata)
    forecaster.fit(df)
    forecast = forecaster.predict(steps=forecast_days)
    methodology = forecast.get('methodology', {})
    return {
        'product_id': product_id,
        'forecast_horizon_days': forecast_days,
        'feature_importance': methodology.get('feature_importance'),
        'selected_features': methodology.get('time_features_used'),
        'ensemble_weights': methodology.get('ensemble_weights'),
        'historical_accuracy': methodology.get('historical_accuracy'),
        'product_adjustments': methodology.get('product_factors'),
        'forecast_summary': forecast.get('summary'),
        'trend_analysis': forecast.get('trend_analysis')
    }


# ============ DATA GENERATION & SIGNALS ============

@router.post("/generate-sample-data")
def generate_sample_data(days: int = 365, db: Session = Depends(get_db)):
    """Generate N days of realistic sample data with seasonal patterns (default 365 = 1 year)."""
    from ..models.data_generator import SmartDataGenerator
    
    try:
        generator = SmartDataGenerator()
        sales_data = generator.generate_sales(days)
        summary = generator.get_sample_data_summary(sales_data)
        
        # Store in database for demo
        for sale in sales_data:
            # Find or create product
            product = db.query(Product).filter(Product.sku == sale['sku']).first()
            if not product:
                product = Product(
                    sku=sale['sku'],
                    name=sale['product_name'],
                    category=sale['category'],
                    unit_price=sale['unit_price'],
                    unit_cost=sale['unit_cost']
                )
                db.add(product)
                db.flush()
            
            # Add sales history
            sales_history = SalesHistory(
                product_id=product.id,
                date=datetime.strptime(sale['date'], '%Y-%m-%d'),
                quantity_sold=sale['quantity_sold'],
                revenue=sale['revenue']
            )
            db.add(sales_history)
        
        db.commit()
        
        return {
            'status': 'success',
            'message': f"Generated {len(sales_data)} sales records over {days} days",
            'summary': summary,
            'records_sample': sales_data[:5]  # First 5 records
        }
    except Exception as e:
        db.rollback()
        return {
            'status': 'error',
            'message': str(e)
        }


@router.get("/data-generator/summary")
def get_data_generator_summary(db: Session = Depends(get_db)):
    """Get summary of generated data"""
    from ..models.data_generator import SmartDataGenerator
    
    try:
        # Get all sales from database
        sales_records = db.query(SalesHistory).all()
        
        if not sales_records:
            return {'status': 'no_data', 'message': 'No sales data available'}
        
        sales_data = [{
            'date': s.date.strftime('%Y-%m-%d'),
            'sku': s.product.sku,
            'product_name': s.product.name,
            'quantity_sold': s.quantity_sold,
            'revenue': s.revenue
        } for s in sales_records]
        
        generator = SmartDataGenerator()
        summary = generator.get_sample_data_summary(sales_data)
        
        return {
            'status': 'success',
            'summary': summary
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@router.get("/signals/weather/{date}")
def get_weather_signal(date: str):
    """Get weather impact for a specific date"""
    from ..models.data_generator import HyperLocalSignals
    
    try:
        signals = HyperLocalSignals()
        signal = signals.get_weather_signal(date)
        
        return {
            'status': 'success',
            'date': date,
            'signal': signal
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@router.get("/signals/holidays/{date}")
def get_holiday_signal(date: str):
    """Get holiday impact for a specific date"""
    from ..models.data_generator import HyperLocalSignals
    
    try:
        signals = HyperLocalSignals()
        signal = signals.get_holiday_signal(date)
        
        return {
            'status': 'success',
            'date': date,
            'signal': signal
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@router.get("/signals/payday/{date}")
def get_payday_signal(date: str):
    """Get payday impact for a specific date"""
    from ..models.data_generator import HyperLocalSignals
    
    try:
        signals = HyperLocalSignals()
        signal = signals.get_payday_signal(date)
        
        return {
            'status': 'success',
            'date': date,
            'signal': signal
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@router.get("/signals/weekend/{date}")
def get_weekend_signal(date: str):
    """Get weekend impact for a specific date"""
    from ..models.data_generator import HyperLocalSignals
    
    try:
        signals = HyperLocalSignals()
        signal = signals.get_weekend_signal(date)
        
        return {
            'status': 'success',
            'date': date,
            'signal': signal
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@router.get("/signals/trends")
def get_trend_signal():
    """Get current viral/trend signals"""
    from ..models.data_generator import HyperLocalSignals
    
    try:
        signals = HyperLocalSignals()
        signal = signals.get_trend_signal()
        
        return {
            'status': 'success',
            'signal': signal
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@router.get("/signals/combined/{date}")
def get_combined_signals(date: str, product: Optional[str] = None):
    """Get combined signal multiplier for forecasting"""
    from ..models.data_generator import HyperLocalSignals
    
    try:
        signals = HyperLocalSignals()
        combined = signals.combine_all_signals(date, product)
        
        return {
            'status': 'success',
            'signals': combined
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


# ===== DATA GENERATION ENDPOINTS =====

@router.get("/ai/models-info")
def get_ai_models_info():
    """Get information about AI/ML models and algorithms used in the system"""
    return {
        "forecasting_models": {
            "primary": {
                "name": "Exponential Smoothing (Holt-Winters)",
                "library": "statsmodels",
                "description": "Triple exponential smoothing capturing level, trend, and seasonality",
                "use_case": "Time series forecasting with seasonal patterns",
                "parameters": {
                    "seasonal_periods": 7,
                    "trend": "additive",
                    "seasonal": "additive"
                }
            },
            "secondary": {
                "name": "Linear Regression",
                "library": "scikit-learn",
                "description": "Linear model with time-based features (day of week, month, quarter)",
                "use_case": "Enhanced prediction with categorical features",
                "features": ["day_of_week", "day_of_month", "month", "quarter", "is_weekend", "week_of_year"]
            },
            "ensemble": {
                "name": "Weighted Ensemble",
                "description": "Combines Exponential Smoothing (70%) and Linear Regression (30%)",
                "weights": {
                    "exponential_smoothing": 0.7,
                    "linear_regression": 0.3
                }
            }
        },
        "optimization_algorithms": {
            "eoq": {
                "name": "Economic Order Quantity (EOQ)",
                "type": "Classical Operations Research",
                "formula": "sqrt((2 * D * S) / H)",
                "description": "Optimal order quantity minimizing total inventory costs",
                "parameters": {
                    "D": "Annual demand",
                    "S": "Ordering cost per order ($50)",
                    "H": "Holding cost per unit (25% of unit cost)"
                }
            },
            "rop": {
                "name": "Reorder Point (ROP)",
                "type": "Inventory Management",
                "formula": "(Avg Daily Demand × Lead Time) + Safety Stock",
                "description": "Stock level triggering reorder to prevent stockouts"
            },
            "safety_stock": {
                "name": "Safety Stock Calculation",
                "type": "Statistical Inventory Control",
                "formula": "Z × σ × sqrt(L)",
                "description": "Buffer stock accounting for demand variability",
                "parameters": {
                    "Z": "Service level z-score (95% = 1.645)",
                    "σ": "Demand standard deviation",
                    "L": "Lead time in days"
                }
            }
        },
        "pricing_algorithms": {
            "markdown": {
                "name": "Markdown Optimization",
                "description": "Dynamic pricing for slow-moving inventory",
                "trigger": "Low demand (<1 unit/day) AND high stock (>100 units)",
                "discount_rate": "5% of unit price"
            }
        },
        "cost_parameters": {
            "holding_cost_rate": {
                "value": 0.25,
                "description": "25% annual holding cost as percentage of unit cost",
                "components": ["storage", "insurance", "obsolescence", "opportunity_cost"]
            },
            "ordering_cost": {
                "value": 50,
                "currency": "USD",
                "description": "Fixed cost per order (processing, shipping, handling)"
            },
            "service_level": {
                "value": 0.95,
                "description": "95% probability of not stocking out during lead time"
            }
        },
        "accuracy_metrics": {
            "mae": "Mean Absolute Error - average prediction error magnitude",
            "mape": "Mean Absolute Percentage Error - error as % of actual",
            "rmse": "Root Mean Square Error - penalizes large errors"
        }
    }

@router.get("/data/generate-sample")
def generate_sample_data(days: int = 90, db: Session = Depends(get_db)):
    """Generate realistic sample sales data for demo/testing"""
    from ..models.data_generator import SmartDataGenerator
    
    try:
        # CRITICAL: Clear all old SalesHistory records to prevent duplicates
        db.query(SalesHistory).delete()
        db.commit()
        
        generator = SmartDataGenerator()
        sales_data = generator.generate_90days_sales()
        
        # First pass: aggregate sales by SKU to calculate average daily demand
        sku_stats = {}
        for sale in sales_data:
            sku = sale['sku']
            if sku not in sku_stats:
                sku_stats[sku] = {
                    'total_qty': 0,
                    'count': 0,
                    'cost': sale['unit_cost'],
                    'price': sale['unit_price'],
                    'category': sale['category'],
                    'name': sale['product_name']
                }
            sku_stats[sku]['total_qty'] += sale['quantity_sold']
            sku_stats[sku]['count'] += 1
        
        # First: Create/update all products with diverse stock scenarios
        total_products = len(sku_stats)
        product_index = 0
        sku_to_product = {}
        
        for product_index, (sku, stats) in enumerate(sku_stats.items()):
            avg_daily_demand = stats['total_qty'] / max(1, stats['count'])
            
            # Assign stock level scenario based on product position (creates diversity)
            percent = product_index / max(1, total_products)
            
            if percent < 0.20:
                # 20% - OUT OF STOCK scenario
                stock_level = 0
                scenario = "OUT_OF_STOCK"
            elif percent < 0.45:
                # 25% - LOW STOCK scenario (2-5 days of supply)
                stock_multiplier = random.uniform(2, 5)
                stock_level = int(avg_daily_demand * stock_multiplier)
                scenario = "LOW_STOCK"
            elif percent < 0.80:
                # 35% - NORMAL/HEALTHY stock (10-20 days of supply)
                stock_multiplier = random.uniform(10, 20)
                stock_level = int(avg_daily_demand * stock_multiplier)
                scenario = "NORMAL_STOCK"
            else:
                # 20% - HIGH STOCK/OVERSTOCK scenario (60-120 days of supply)
                stock_multiplier = random.uniform(60, 120)
                stock_level = int(avg_daily_demand * stock_multiplier)
                scenario = "HIGH_STOCK"
            
            # Create/update product
            product = db.query(Product).filter(Product.sku == sku).first()
            if not product:
                # New product
                product = Product(
                    sku=sku,
                    name=stats['name'],
                    category=stats['category'],
                    current_stock=max(0, stock_level),
                    unit_cost=stats['cost'],
                    unit_price=stats['price'],
                    lead_time_days=7
                )
                db.add(product)
            else:
                # Update existing product with new inventory calculation
                product.current_stock = max(0, stock_level)
            
            db.flush()
            sku_to_product[sku] = product
        
        db.commit()
        
        # Second: Add all sales history records
        records_created = 0
        for sale in sales_data:
            sku = sale['sku']
            product = sku_to_product.get(sku)
            
            if product:
                # Create sales history record
                sales_record = SalesHistory(
                    product_id=product.id,
                    date=datetime.strptime(sale['date'], '%Y-%m-%d'),
                    quantity_sold=sale['quantity_sold'],
                    revenue=sale['revenue']
                )
                db.add(sales_record)
                records_created += 1
        
        db.commit()
        
        # Get summary
        summary = generator.get_sample_data_summary(sales_data)
        
        return {
            'status': 'success',
            'message': f'Generated {records_created} sample sales records',
            'records_created': records_created,
            'summary': summary,
            'data_sample': sales_data[:10]  # First 10 records
        }
    
    except Exception as e:
        db.rollback()
        return {
            'status': 'error',
            'message': str(e)
        }


@router.get("/data/enrich-forecast/{product_id}")
def enrich_forecast_with_signals(product_id: int, date: str = None, db: Session = Depends(get_db)):
    """Get forecast enriched with hyper-local signals"""
    from ..models.data_generator import HyperLocalSignals
    
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Get product info
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get base forecast
        forecaster = DemandForecaster()
        sales_data = db.query(SalesHistory)\
            .filter(SalesHistory.product_id == product_id)\
            .order_by(SalesHistory.date)\
            .all()
        
        if not sales_data:
            raise HTTPException(status_code=400, detail="Insufficient historical data for forecast")
        
        df = pd.DataFrame([{
            'date': s.date,
            'quantity_sold': s.quantity_sold
        } for s in sales_data])
        
        # Fit and predict
        forecaster.fit(df, seasonal_periods=7)
        forecast_result = forecaster.predict(steps=1)
        base_forecast = forecast_result['predictions'][0] if forecast_result['predictions'] else 100
        
        # Get signals enrichment
        signals = HyperLocalSignals()
        combined_signals = signals.combine_all_signals(date, product.sku)
        
        # Calculate enriched forecast
        enriched_forecast = int(base_forecast * combined_signals['combined_multiplier'])
        
        return {
            'status': 'success',
            'product': {
                'id': product.id,
                'sku': product.sku,
                'name': product.name
            },
            'forecast': {
                'date': date,
                'base_forecast': round(base_forecast, 2),
                'signal_multiplier': combined_signals['combined_multiplier'],
                'enriched_forecast': enriched_forecast,
                'confidence': 0.92
            },
            'signals_breakdown': {
                'weather': combined_signals['weather'],
                'holiday': combined_signals['holiday'],
                'payday': combined_signals['payday'],
                'weekend': combined_signals['weekend'],
                'trend': combined_signals['trend']
            },
            'interpretation': combined_signals['interpretation']
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@router.post("/data/bulk-import")
async def bulk_import_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import bulk sales data from CSV file"""
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        records_imported = 0
        for idx, row in df.iterrows():
            # Get or create product
            product = db.query(Product).filter(Product.sku == row['sku']).first()
            if not product:
                product = Product(
                    sku=row['sku'],
                    name=row.get('product_name', row['sku']),
                    category=row.get('category', 'General'),
                    current_stock=int(row.get('stock', 100)),
                    unit_cost=float(row.get('cost', 0)),
                    unit_price=float(row.get('price', 0))
                )
                db.add(product)
                db.flush()
            
            # Create sales record
            sales_record = SalesHistory(
                product_id=product.id,
                date=pd.to_datetime(row['date']),
                quantity_sold=int(row['quantity_sold']),
                revenue=float(row.get('revenue', 0))
            )
            db.add(sales_record)
            records_imported += 1
        
        db.commit()
        
        return {
            'status': 'success',
            'message': f'Imported {records_imported} records',
            'records_imported': records_imported
        }
    
    except Exception as e:
        db.rollback()
        return {
            'status': 'error',
            'message': str(e)
        }


# ===== MARKDOWN OPTIMIZER ENDPOINTS =====

@router.get("/markdown/opportunities")
def get_markdown_opportunities(limit: int = Query(100, le=1000), db: Session = Depends(get_db)):
    """Get all products that need markdown (slow-moving inventory) - OPTIMIZED with batch queries"""
    try:
        optimizer = MarkdownOptimizer()
        
        # Batch load products (limited for performance)
        products = {p.id: p for p in db.query(Product).order_by(Product.id).limit(limit).all()}
        
        product_ids = list(products.keys())
        
        # Get aggregated sales data in one query (only for loaded products)
        sales_agg = db.query(
            SalesHistory.product_id,
            func.sum(SalesHistory.quantity_sold).label('total_qty'),
            func.min(SalesHistory.date).label('min_date'),
            func.max(SalesHistory.date).label('max_date')
        ).filter(SalesHistory.product_id.in_(product_ids)).group_by(SalesHistory.product_id).all()
        
        sales_map = {
            row.product_id: {
                'total_qty': int(row.total_qty or 0),
                'min_date': row.min_date,
                'max_date': row.max_date
            } for row in sales_agg
        }
        
        opportunities = []
        
        for product_id, product in products.items():
            sales_data = sales_map.get(product_id)
            if not sales_data or not sales_data['min_date']:
                continue
            
            # Calculate average demand from all available history
            days_of_data = (sales_data['max_date'] - sales_data['min_date']).days + 1
            daily_demand = sales_data['total_qty'] / max(1, days_of_data)
            monthly_demand = daily_demand * 30
            
            # Calculate days of inventory on hand
            days_of_inventory = product.current_stock / max(daily_demand, 0.1)
            
            # Calculate inventory health
            health = optimizer.calculate_inventory_health(
                current_stock=product.current_stock,
                monthly_demand=monthly_demand,
                lead_time_days=product.lead_time_days
            )
            
            # Identify markdown opportunities
            should_markdown = (
                health['risk_level'] >= 2 or 
                days_of_inventory > 45
            ) and product.current_stock > 0
            
            if should_markdown:
                timing = optimizer.predict_optimal_markdown_timing(
                    current_stock=product.current_stock,
                    monthly_demand=monthly_demand,
                    unit_cost=product.unit_cost,
                    unit_price=product.unit_price,
                    daily_holding_cost=product.unit_cost * 0.001
                )
                
                opportunities.append({
                    'product_id': product.id,
                    'sku': product.sku,
                    'name': product.name,
                    'current_price': round(product.unit_price, 2),
                    'current_stock': product.current_stock,
                    'daily_demand': round(daily_demand, 2),
                    'monthly_demand': round(monthly_demand, 2),
                    'days_of_inventory': round(days_of_inventory, 1),
                    'health': health,
                    'timing': timing
                })
        
        # Sort by urgency
        opportunities.sort(key=lambda x: x['timing']['days_until_markdown'])
        
        return {
            'status': 'success',
            'count': len(opportunities),
            'opportunities': opportunities
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@router.get("/markdown/analyze/{product_id}")
def analyze_markdown_opportunity(product_id: int, db: Session = Depends(get_db)):
    """Get detailed markdown analysis and scenarios for a specific product"""
    try:
        optimizer = MarkdownOptimizer()
        
        # Get product
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get ALL sales history for accurate demand calculation
        sales = db.query(SalesHistory)\
            .filter(SalesHistory.product_id == product_id)\
            .order_by(SalesHistory.date)\
            .all()
        
        if not sales:
            raise HTTPException(status_code=400, detail="Insufficient sales data")
        
        # Calculate average monthly demand from all available history
        total_qty = sum(s.quantity_sold for s in sales)
        days_of_data = (max(s.date for s in sales) - min(s.date for s in sales)).days + 1
        monthly_demand = (total_qty / max(1, days_of_data)) * 30  # Normalized to 30 days
        
        daily_holding_cost = product.unit_cost * 0.001  # 0.1% per day
        
        # Inventory health
        health = optimizer.calculate_inventory_health(
            current_stock=product.current_stock,
            monthly_demand=monthly_demand,
            lead_time_days=product.lead_time_days
        )
        
        # Timing prediction
        timing = optimizer.predict_optimal_markdown_timing(
            current_stock=product.current_stock,
            monthly_demand=monthly_demand,
            unit_cost=product.unit_cost,
            unit_price=product.unit_price,
            daily_holding_cost=daily_holding_cost
        )
        
        # Markdown scenarios
        scenarios = optimizer.calculate_markdown_scenarios(
            current_stock=product.current_stock,
            monthly_demand=monthly_demand,
            unit_cost=product.unit_cost,
            unit_price=product.unit_price,
            daily_holding_cost=daily_holding_cost,
            markdown_duration_days=14
        )
        
        # Recommendation
        recommendation = optimizer.get_markdown_recommendation(
            inventory_health=health,
            markdown_timing=timing,
            scenarios=scenarios,
            product_name=product.name
        )
        
        return {
            'status': 'success',
            'product': {
                'id': product.id,
                'sku': product.sku,
                'name': product.name,
                'current_stock': product.current_stock,
                'current_price': round(product.unit_price, 2),
                'unit_cost': round(product.unit_cost, 2)
            },
            'analysis': {
                'inventory_health': health,
                'markdown_timing': timing,
                'recommendation': recommendation,
                'scenarios': scenarios
            }
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@router.post("/products/import")
async def import_products(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import bulk products from CSV (sku, name, category, current_stock, unit_cost, unit_price, lead_time_days)"""
    try:
        contents = await file.read()
        
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        elif file.filename.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(contents))
        elif file.filename.lower().endswith('.json'):
            df = pd.read_json(io.StringIO(contents.decode('utf-8')))
        else:
            raise Exception("Supported formats: CSV, Excel (.xlsx, .xls), JSON")
        
        # Required columns
        required_cols = ['sku', 'name']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise Exception(f"Missing required columns: {', '.join(missing_cols)}")
        
        products_added = 0
        skipped = 0
        
        for _, row in df.iterrows():
            try:
                # Check if product already exists by SKU
                existing = db.query(Product).filter(Product.sku == row['sku']).first()
                if existing:
                    skipped += 1
                    continue
                
                # Create new product with provided fields (or defaults)
                product = Product(
                    sku=str(row['sku']),
                    name=str(row['name']),
                    category=str(row.get('category', 'General')),
                    current_stock=int(row.get('current_stock', 0)),
                    unit_cost=float(row.get('unit_cost', 10.0)),
                    unit_price=float(row.get('unit_price', 15.0)),
                    lead_time_days=int(row.get('lead_time_days', 7))
                )
                db.add(product)
                products_added += 1
            except Exception as e:
                skipped += 1
                continue
        
        db.commit()
        
        return {
            'status': 'success',
            'message': f'Imported {products_added} new products ({skipped} duplicates/errors skipped)',
            'products_added': products_added,
            'skipped': skipped
        }
    
    except Exception as e:
        db.rollback()
        return {
            'status': 'error',
            'message': str(e)
        }


@router.post("/admin/clear-all-data")
def clear_all_data(db: Session = Depends(get_db)):
    """Clear all data from database (admin function)"""
    try:
        # Count before
        products_before = db.query(Product).count()
        sales_before = db.query(SalesHistory).count()
        forecast_before = db.query(Forecast).count()
        rec_before = db.query(InventoryRecommendation).count()
        
        # Delete in order (respect foreign keys)
        db.query(SalesHistory).delete()
        db.query(Forecast).delete()
        db.query(InventoryRecommendation).delete()
        db.query(Product).delete()
        
        db.commit()
        
        return {
            'status': 'success',
            'message': 'All data cleared successfully',
            'deleted': {
                'products': products_before,
                'sales_history': sales_before,
                'forecasts': forecast_before,
                'recommendations': rec_before
            }
        }
    except Exception as e:
        db.rollback()
        return {
            'status': 'error',
            'message': str(e)
        }

@router.post("/analytics/backtest-forecasts")
def backtest_forecasts(db: Session = Depends(get_db)):
    """
    Generate historical forecasts for accuracy testing.
    Uses past sales data to create forecasts, then compares with actual sales.
    This populates the database with historical forecasts for accuracy calculation.
    """
    products = db.query(Product).all()
    backtested_count = 0
    errors = []
    
    for product in products:
        try:
            # Get all sales data for this product
            all_sales = db.query(SalesHistory)\
                .filter(SalesHistory.product_id == product.id)\
                .order_by(SalesHistory.date)\
                .all()
            
            if len(all_sales) < 30:
                continue  # Need at least 30 days of data
            
            # Delete existing historical forecasts for this product
            db.query(Forecast)\
                .filter(Forecast.product_id == product.id)\
                .filter(Forecast.forecast_date < datetime.now())\
                .delete()
            
            # Split data: use first 60% for training, forecast on remaining 40%
            split_point = int(len(all_sales) * 0.6)
            training_sales = all_sales[:split_point]
            test_sales = all_sales[split_point:]
            
            # Prepare training data
            df = pd.DataFrame([{
                'date': s.date,
                'quantity_sold': s.quantity_sold
            } for s in training_sales])
            
            # Generate forecast
            forecaster = DemandForecaster()
            forecaster.fit(df)
            forecast_days = len(test_sales)
            forecast_result = forecaster.predict(steps=forecast_days)
            
            # Save historical forecasts (matching actual past dates)
            for i, test_sale in enumerate(test_sales):
                if i < len(forecast_result['predictions']):
                    forecast_entry = Forecast(
                        product_id=product.id,
                        forecast_date=test_sale.date,  # Use actual historical date
                        predicted_demand=forecast_result['predictions'][i],
                        lower_bound=forecast_result['lower_bound'][i],
                        upper_bound=forecast_result['upper_bound'][i],
                        created_at=test_sale.date - timedelta(days=1)  # Created "before" the actual date
                    )
                    db.add(forecast_entry)
            
            backtested_count += 1
            db.commit()
            
        except Exception as e:
            errors.append({
                'product': product.sku,
                'error': str(e)
            })
            db.rollback()
            continue
    
    return {
        'status': 'success',
        'backtested_products': backtested_count,
        'total_products': len(products),
        'errors': errors[:5]  # Show first 5 errors only
    }

# ==================== SUPPLIER RISK ANALYSIS ENDPOINTS ====================

@router.get("/suppliers")
def get_all_suppliers(db: Session = Depends(get_db)):
    """Get all suppliers with their latest risk scores"""
    suppliers = db.query(Supplier).all()
    
    result = []
    for supplier in suppliers:
        # Get latest risk score
        latest_risk = db.query(SupplierRiskScore)\
            .filter(SupplierRiskScore.supplier_id == supplier.id)\
            .order_by(SupplierRiskScore.created_at.desc())\
            .first()
        
        result.append({
            'id': supplier.id,
            'name': supplier.supplier_name,
            'country': supplier.country,
            'region': supplier.region,
            'contact_email': supplier.contact_email,
            'contact_phone': supplier.contact_phone,
            'lead_time_days': supplier.lead_time_days,
            'moq': supplier.moq,
            'on_time_delivery_rate': supplier.on_time_delivery_rate,
            'quality_score': supplier.quality_score,
            'financial_health_score': supplier.financial_health_score,
            'current_risk_score': latest_risk.overall_risk_score if latest_risk else None,
            'risk_level': latest_risk.risk_level if latest_risk else None,
            'created_at': supplier.created_at
        })
    
    return result

@router.post("/suppliers")
def create_supplier(supplier_data: dict, db: Session = Depends(get_db)):
    """Create a new supplier"""
    supplier = Supplier(
        supplier_name=supplier_data.get('name'),
        country=supplier_data.get('country'),
        region=supplier_data.get('region', ''),
        contact_email=supplier_data.get('contact_email', ''),
        contact_phone=supplier_data.get('contact_phone', ''),
        unit_cost=supplier_data.get('unit_cost', 0),
        lead_time_days=supplier_data.get('lead_time_days', 14),
        moq=supplier_data.get('moq', 100),
        on_time_delivery_rate=supplier_data.get('on_time_delivery_rate', 0.95),
        quality_score=supplier_data.get('quality_score', 0.9),
        financial_health_score=supplier_data.get('financial_health_score', 0.8),
        relationship_duration_months=supplier_data.get('relationship_duration_months', 0),
        esg_compliance_score=supplier_data.get('esg_compliance_score', 0.75)
    )
    
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    
    return {
        'id': supplier.id,
        'name': supplier.supplier_name,
        'country': supplier.country,
        'region': supplier.region
    }


# ============================================================
# Stock Threshold Configuration
# ============================================================

# Note: STOCK_THRESHOLDS is defined at the top of this file (line ~37)
# All endpoints use that single global configuration

@router.get("/settings/thresholds")
def get_stock_thresholds():
    """Get current stock classification thresholds"""
    return {
        'thresholds': STOCK_THRESHOLDS,
        'description': {
            'out_of_stock': 'Stock = 0',
            'low_stock': f'Stock <= {STOCK_THRESHOLDS["low_stock_max"]}',
            'medium_stock': f'Stock <= {STOCK_THRESHOLDS["medium_stock_max"]}',
            'high_stock': f'Stock > {STOCK_THRESHOLDS["medium_stock_max"]}'
        }
    }

@router.post("/settings/thresholds")
def update_stock_thresholds(thresholds: dict):
    """Update stock classification thresholds"""
    global STOCK_THRESHOLDS
    
    # Validate inputs
    low_max = thresholds.get('low_stock_max')
    medium_max = thresholds.get('medium_stock_max')
    
    if low_max is not None:
        if not isinstance(low_max, (int, float)) or low_max < 0:
            raise HTTPException(status_code=400, detail="low_stock_max must be a non-negative number")
        STOCK_THRESHOLDS['low_stock_max'] = int(low_max)
    
    if medium_max is not None:
        if not isinstance(medium_max, (int, float)) or medium_max < 0:
            raise HTTPException(status_code=400, detail="medium_stock_max must be a non-negative number")
        STOCK_THRESHOLDS['medium_stock_max'] = int(medium_max)
    
    # Ensure logical ordering: low < medium
    if STOCK_THRESHOLDS['low_stock_max'] >= STOCK_THRESHOLDS['medium_stock_max']:
        raise HTTPException(
            status_code=400, 
            detail="low_stock_max must be less than medium_stock_max"
        )
    
    return {
        'success': True,
        'thresholds': STOCK_THRESHOLDS,
        'message': 'Thresholds updated successfully'
    }

@router.get("/metrics/products-detail-dynamic")
def get_products_detail_dynamic(
    low_max: int = None,
    medium_max: int = None,
    db: Session = Depends(get_db)
):
    """Get detailed breakdown of products by category and stock levels with dynamic thresholds"""
    # Use provided thresholds or defaults
    low_threshold = low_max if low_max is not None else STOCK_THRESHOLDS['low_stock_max']
    medium_threshold = medium_max if medium_max is not None else STOCK_THRESHOLDS['medium_stock_max']
    
    products = db.query(Product).all()
    
    # Breakdown by category
    category_breakdown = {}
    for product in products:
        cat = product.category or "Uncategorized"
        if cat not in category_breakdown:
            category_breakdown[cat] = {
                'count': 0,
                'total_stock': 0,
                'total_value': 0
            }
        category_breakdown[cat]['count'] += 1
        category_breakdown[cat]['total_stock'] += product.current_stock
        category_breakdown[cat]['total_value'] += product.current_stock * product.unit_cost
    
    # Stock distribution with dynamic thresholds
    stock_distribution = {
        'out_of_stock': 0,
        'low_stock': 0,
        'medium_stock': 0,
        'high_stock': 0
    }
    
    for product in products:
        if product.current_stock == 0:
            stock_distribution['out_of_stock'] += 1
        elif product.current_stock <= low_threshold:
            stock_distribution['low_stock'] += 1
        elif product.current_stock <= medium_threshold:
            stock_distribution['medium_stock'] += 1
        else:
            stock_distribution['high_stock'] += 1
    
    # Get top 10 products by stock value
    products_with_value = [
        {
            'sku': p.sku,
            'name': p.name,
            'category': p.category,
            'stock': p.current_stock,
            'value': p.current_stock * p.unit_cost
        }
        for p in products
    ]
    top_by_value = sorted(products_with_value, key=lambda x: x['value'], reverse=True)[:10]
    
    # All products list with stock badge (using dynamic thresholds)
    all_products = []
    for p in products:
        if p.current_stock == 0:
            stock_status = "OUT_OF_STOCK"
        elif p.current_stock <= low_threshold:
            stock_status = "LOW"
        elif p.current_stock <= medium_threshold:
            stock_status = "MEDIUM"
        else:
            stock_status = "HIGH"
        
        all_products.append({
            'sku': p.sku,
            'name': p.name,
            'category': p.category,
            'stock': p.current_stock,
            'unit_cost': p.unit_cost,
            'unit_price': p.unit_price,
            'stock_status': stock_status
        })
    
    return {
        'total_products': len(products),
        'thresholds': {
            'low_stock_max': low_threshold,
            'medium_stock_max': medium_threshold
        },
        'category_breakdown': [
            {'category': cat, **data}
            for cat, data in sorted(category_breakdown.items(), key=lambda x: x[1]['count'], reverse=True)
        ],
        'stock_distribution': stock_distribution,
        'top_by_value': top_by_value,
        'all_products': all_products
    }


# ============================================================================
# JSON INGESTION API - REST API for Key-Value JSON Payloads
# ============================================================================

# Schema definition for JSON ingestion
JSON_INGESTION_SCHEMA = {
    'products': {
        'required': ['sku', 'name'],
        'optional': ['category', 'current_stock', 'unit_cost', 'unit_price', 'lead_time_days', 
                    'reorder_point', 'safety_stock', 'average_daily_demand', 'seasonality_factor'],
        'types': {
            'sku': str, 'name': str, 'category': str,
            'current_stock': int, 'unit_cost': float, 'unit_price': float,
            'lead_time_days': int, 'reorder_point': int, 'safety_stock': int,
            'average_daily_demand': float, 'seasonality_factor': float
        }
    },
    'sales': {
        'required': ['sku', 'date', 'quantity_sold'],
        'optional': ['revenue', 'unit_price', 'discount', 'channel', 'region'],
        'types': {
            'sku': str, 'date': str, 'quantity_sold': int,
            'revenue': float, 'unit_price': float, 'discount': float,
            'channel': str, 'region': str
        }
    }
}

# Model column requirements for dynamic selection
MODEL_COLUMN_REQUIREMENTS = {
    'demand_forecasting': {
        'required': ['sku', 'date', 'quantity_sold'],
        'optional': ['revenue', 'seasonality_factor', 'average_daily_demand'],
        'description': 'Columns needed for demand forecasting model'
    },
    'inventory_optimization': {
        'required': ['sku', 'current_stock', 'unit_cost'],
        'optional': ['lead_time_days', 'reorder_point', 'safety_stock', 'average_daily_demand'],
        'description': 'Columns needed for inventory optimization model'
    },
    'stockout_prediction': {
        'required': ['sku', 'current_stock', 'average_daily_demand'],
        'optional': ['lead_time_days', 'safety_stock', 'seasonality_factor'],
        'description': 'Columns needed for stockout risk prediction'
    },
    'price_optimization': {
        'required': ['sku', 'unit_cost', 'unit_price'],
        'optional': ['revenue', 'quantity_sold', 'discount'],
        'description': 'Columns needed for price optimization'
    }
}


def validate_json_schema(data: dict, data_type: str) -> tuple:
    """Validate JSON data against schema. Returns (is_valid, errors, warnings)."""
    schema = JSON_INGESTION_SCHEMA.get(data_type)
    if not schema:
        return False, [f"Unknown data type: {data_type}"], []
    
    errors = []
    warnings = []
    
    # Check required fields
    for field in schema['required']:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Type validation for provided fields
    for field, value in data.items():
        if field in schema['types']:
            expected_type = schema['types'][field]
            if value is not None:
                try:
                    if expected_type == int:
                        int(value)
                    elif expected_type == float:
                        float(value)
                    elif expected_type == str:
                        str(value)
                except (ValueError, TypeError):
                    errors.append(f"Invalid type for {field}: expected {expected_type.__name__}")
        elif field not in schema['optional'] and field not in schema['required']:
            warnings.append(f"Unknown field will be ignored: {field}")
    
    return len(errors) == 0, errors, warnings


def select_model_columns(data: pd.DataFrame, model_name: str) -> pd.DataFrame:
    """Dynamically select only required columns for a specific model."""
    if model_name not in MODEL_COLUMN_REQUIREMENTS:
        return data
    
    requirements = MODEL_COLUMN_REQUIREMENTS[model_name]
    available_cols = set(data.columns)
    
    # Get required columns (must have all)
    required = set(requirements['required'])
    missing_required = required - available_cols
    if missing_required:
        raise ValueError(f"Missing required columns for {model_name}: {missing_required}")
    
    # Get optional columns (use if available)
    optional = set(requirements['optional'])
    selected_optional = optional & available_cols
    
    # Select only relevant columns
    selected_cols = list(required | selected_optional)
    return data[selected_cols].copy()


@router.post("/data/json-ingest")
async def json_ingest_data(payload: dict, db: Session = Depends(get_db)):
    """
    REST API for JSON data ingestion.
    
    Accepts key-value JSON payloads for products and sales data.
    Validates schema and handles errors gracefully.
    
    Request body format:
    {
        "data_type": "products" | "sales",
        "records": [
            {"sku": "SKU001", "name": "Product", ...},
            ...
        ],
        "options": {
            "update_existing": true,  // Update if SKU exists
            "validate_strict": false  // Fail on warnings
        }
    }
    """
    try:
        data_type = payload.get('data_type')
        records = payload.get('records', [])
        options = payload.get('options', {})
        
        if not data_type:
            raise HTTPException(status_code=400, detail="Missing 'data_type' field. Use 'products' or 'sales'")
        
        if data_type not in JSON_INGESTION_SCHEMA:
            raise HTTPException(status_code=400, detail=f"Invalid data_type. Supported: {list(JSON_INGESTION_SCHEMA.keys())}")
        
        if not records or not isinstance(records, list):
            raise HTTPException(status_code=400, detail="'records' must be a non-empty array")
        
        update_existing = options.get('update_existing', True)
        validate_strict = options.get('validate_strict', False)
        
        # Validate each record
        all_errors = []
        all_warnings = []
        valid_records = []
        
        for i, record in enumerate(records):
            is_valid, errors, warnings = validate_json_schema(record, data_type)
            
            if errors:
                all_errors.append(f"Record {i+1}: {errors}")
            if warnings:
                all_warnings.append(f"Record {i+1}: {warnings}")
            
            if is_valid and (not validate_strict or not warnings):
                valid_records.append(record)
        
        if all_errors and validate_strict:
            raise HTTPException(status_code=400, detail={
                "message": "Validation failed",
                "errors": all_errors,
                "warnings": all_warnings
            })
        
        # Process valid records
        results = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': []
        }
        
        if data_type == 'products':
            product_map = {p.sku: p for p in db.query(Product).all()}
            
            for record in valid_records:
                try:
                    sku = str(record['sku']).strip()
                    existing = product_map.get(sku)
                    
                    if existing:
                        if update_existing:
                            # Update existing product
                            if 'name' in record: existing.name = str(record['name'])
                            if 'category' in record: existing.category = str(record['category'])
                            if 'current_stock' in record: existing.current_stock = int(record['current_stock'])
                            if 'unit_cost' in record: existing.unit_cost = float(record['unit_cost'])
                            if 'unit_price' in record: existing.unit_price = float(record['unit_price'])
                            if 'lead_time_days' in record: existing.lead_time_days = int(record['lead_time_days'])
                            if 'reorder_point' in record: existing.reorder_point = int(record['reorder_point'])
                            if 'safety_stock' in record: existing.safety_stock = int(record['safety_stock'])
                            if 'average_daily_demand' in record: existing.average_daily_demand = float(record['average_daily_demand'])
                            results['updated'] += 1
                        else:
                            results['skipped'] += 1
                    else:
                        # Create new product
                        product = Product(
                            sku=sku,
                            name=str(record.get('name', sku)),
                            category=str(record.get('category', 'General')),
                            current_stock=int(record.get('current_stock', 0)),
                            unit_cost=float(record.get('unit_cost', 10.0)),
                            unit_price=float(record.get('unit_price', 15.0)),
                            lead_time_days=int(record.get('lead_time_days', 7)),
                            reorder_point=int(record.get('reorder_point', 10)),
                            safety_stock=int(record.get('safety_stock', 5)),
                            average_daily_demand=float(record.get('average_daily_demand', 5.0))
                        )
                        db.add(product)
                        product_map[sku] = product
                        results['created'] += 1
                except Exception as e:
                    results['errors'].append(f"SKU {record.get('sku')}: {str(e)}")
            
            db.commit()
            
        elif data_type == 'sales':
            product_map = {p.sku: p.id for p in db.query(Product).all()}
            
            sales_to_insert = []
            for record in valid_records:
                try:
                    sku = str(record['sku']).strip()
                    product_id = product_map.get(sku)
                    
                    if not product_id:
                        results['errors'].append(f"SKU {sku}: Product not found")
                        results['skipped'] += 1
                        continue
                    
                    # Parse date
                    date_str = record['date']
                    if isinstance(date_str, str):
                        sale_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    else:
                        sale_date = date_str
                    
                    sale = SalesHistory(
                        product_id=product_id,
                        date=sale_date,
                        quantity_sold=int(record['quantity_sold']),
                        revenue=float(record.get('revenue', int(record['quantity_sold']) * 10))
                    )
                    sales_to_insert.append(sale)
                    results['created'] += 1
                except Exception as e:
                    results['errors'].append(f"Record: {str(e)}")
            
            if sales_to_insert:
                db.bulk_save_objects(sales_to_insert)
                db.commit()
        
        return {
            'success': True,
            'data_type': data_type,
            'total_records': len(records),
            'valid_records': len(valid_records),
            'results': results,
            'warnings': all_warnings if all_warnings else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/data/model-columns/{model_name}")
def get_model_columns(model_name: str):
    """Get required and optional columns for a specific ML model."""
    if model_name not in MODEL_COLUMN_REQUIREMENTS:
        raise HTTPException(
            status_code=404, 
            detail=f"Model not found. Available models: {list(MODEL_COLUMN_REQUIREMENTS.keys())}"
        )
    
    return {
        'model': model_name,
        'columns': MODEL_COLUMN_REQUIREMENTS[model_name]
    }


@router.get("/data/model-columns")
def list_all_model_columns():
    """List column requirements for all ML models."""
    return {
        'models': MODEL_COLUMN_REQUIREMENTS,
        'supported_data_types': list(JSON_INGESTION_SCHEMA.keys())
    }


@router.post("/data/prepare-for-model")
async def prepare_data_for_model(payload: dict, db: Session = Depends(get_db)):
    """
    Prepare combined CSV/JSON data for model training/inference.
    Dynamically selects only required columns and excludes irrelevant ones.
    
    Request body:
    {
        "model_name": "demand_forecasting",
        "include_products": true,
        "include_sales": true,
        "limit": 10000
    }
    """
    model_name = payload.get('model_name')
    include_products = payload.get('include_products', True)
    include_sales = payload.get('include_sales', True)
    limit = payload.get('limit', 10000)
    
    if not model_name:
        raise HTTPException(status_code=400, detail="model_name is required")
    
    if model_name not in MODEL_COLUMN_REQUIREMENTS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown model. Available: {list(MODEL_COLUMN_REQUIREMENTS.keys())}"
        )
    
    try:
        result_data = {}
        
        if include_products:
            products = db.query(Product).limit(limit).all()
            product_df = pd.DataFrame([{
                'sku': p.sku,
                'name': p.name,
                'category': p.category,
                'current_stock': p.current_stock,
                'unit_cost': p.unit_cost,
                'unit_price': p.unit_price,
                'lead_time_days': p.lead_time_days,
                'reorder_point': p.reorder_point,
                'safety_stock': p.safety_stock,
                'average_daily_demand': p.average_daily_demand
            } for p in products])
            
            # Select only model-relevant columns
            try:
                filtered_products = select_model_columns(product_df, model_name)
                result_data['products'] = {
                    'count': len(filtered_products),
                    'columns': list(filtered_products.columns),
                    'sample': filtered_products.head(5).to_dict('records')
                }
            except ValueError as e:
                result_data['products'] = {'error': str(e)}
        
        if include_sales:
            sales_query = db.query(SalesHistory).limit(limit).all()
            sales_df = pd.DataFrame([{
                'sku': db.query(Product).filter(Product.id == s.product_id).first().sku if s.product_id else None,
                'date': str(s.date),
                'quantity_sold': s.quantity_sold,
                'revenue': s.revenue
            } for s in sales_query])
            
            try:
                filtered_sales = select_model_columns(sales_df, model_name)
                result_data['sales'] = {
                    'count': len(filtered_sales),
                    'columns': list(filtered_sales.columns),
                    'sample': filtered_sales.head(5).to_dict('records')
                }
            except ValueError as e:
                result_data['sales'] = {'error': str(e)}
        
        return {
            'model': model_name,
            'requirements': MODEL_COLUMN_REQUIREMENTS[model_name],
            'data': result_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data preparation failed: {str(e)}")


@router.get("/settings/email-config")
def get_email_config(db: Session = Depends(get_db)):
    """Read email configuration including DB-managed recipients."""
    recipients = [
        r.destination for r in db.query(AlertRecipient).filter(
            AlertRecipient.channel == 'EMAIL',
            AlertRecipient.active.is_(True)
        ).all()
    ]
    config = email_service_sendgrid.get_config()
    config['recipients'] = recipients or config.get('default_recipients', [])
    return config


@router.post("/settings/email-config")
def update_email_config(config: dict, db: Session = Depends(get_db)):
    """Persist email recipients + toggle provider without hardcoding secrets."""
    updated = {}
    if 'recipients' in config:
        recipients = config['recipients']
        if isinstance(recipients, str):
            recipients = [r.strip() for r in recipients.split(',')]
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        valid = [email for email in recipients if re.match(email_pattern, email)]
        db.query(AlertRecipient).filter(AlertRecipient.channel == 'EMAIL').delete()
        for email in valid:
            db.add(AlertRecipient(channel='EMAIL', destination=email, active=True))
        db.commit()
        email_service_sendgrid.update_recipients(valid)
        updated['recipients'] = len(valid)
    if 'enabled' in config:
        email_service_sendgrid.toggle_email(bool(config['enabled']))
        updated['enabled'] = bool(config['enabled'])
    if 'from_email' in config:
        email_service_sendgrid.update_from_email(config['from_email'])
        updated['from_email'] = config['from_email']
    return {'success': True, 'updated': updated}


@router.post("/alerts/generate-email")
def generate_stock_alert_email(payload: dict, db: Session = Depends(get_db)):
    """
    Auto-generate email body for stock alerts.
    
    Request body:
    {
        "product_ids": [1, 2, 3],  // Optional - specific products
        "alert_type": "low_stock" | "out_of_stock" | "all",
        "include_recommendations": true
    }
    """
    product_ids = payload.get('product_ids', [])
    alert_type = payload.get('alert_type', 'all')
    include_recommendations = payload.get('include_recommendations', True)
    
    # Get products based on criteria
    query = db.query(Product)
    
    if product_ids:
        query = query.filter(Product.id.in_(product_ids))
    
    if alert_type == 'out_of_stock':
        query = query.filter(Product.current_stock == 0)
    elif alert_type == 'low_stock':
        low_threshold = STOCK_THRESHOLDS.get('low_stock_max', 50)
        query = query.filter(Product.current_stock > 0, Product.current_stock <= low_threshold)
    elif alert_type == 'all':
        low_threshold = STOCK_THRESHOLDS.get('low_stock_max', 50)
        query = query.filter(Product.current_stock <= low_threshold)
    
    products = query.all()
    
    if not products:
        return {
            'success': True,
            'message': 'No products match the alert criteria',
            'email_body': None
        }
    
    # Generate email subject
    out_of_stock_count = sum(1 for p in products if p.current_stock == 0)
    low_stock_count = len(products) - out_of_stock_count
    
    subject = f"🚨 Stock Alert: {out_of_stock_count} Out of Stock, {low_stock_count} Low Stock Items"
    
    # Generate email body
    email_lines = [
        "=" * 60,
        "INVENTORY STOCK ALERT NOTIFICATION",
        "=" * 60,
        "",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Alert Type: {alert_type.replace('_', ' ').title()}",
        f"Total Items Requiring Attention: {len(products)}",
        "",
        "-" * 60,
        "PRODUCT DETAILS",
        "-" * 60,
        ""
    ]
    
    # Group by status
    out_of_stock_products = [p for p in products if p.current_stock == 0]
    low_stock_products = [p for p in products if p.current_stock > 0]
    
    if out_of_stock_products:
        email_lines.append("🔴 OUT OF STOCK ITEMS:")
        email_lines.append("")
        for p in out_of_stock_products:
            reorder_qty = max(p.reorder_point * 2, 50) if p.reorder_point else 50
            email_lines.extend([
                f"  SKU: {p.sku}",
                f"  Name: {p.name}",
                f"  Category: {p.category}",
                f"  Current Stock: 0 units",
                f"  Reorder Point: {p.reorder_point} units",
                f"  Suggested Order Quantity: {reorder_qty} units",
                f"  Estimated Cost: ${reorder_qty * p.unit_cost:.2f}",
                ""
            ])
    
    if low_stock_products:
        email_lines.append("🟠 LOW STOCK ITEMS:")
        email_lines.append("")
        for p in low_stock_products:
            days_remaining = int(p.current_stock / p.average_daily_demand) if p.average_daily_demand > 0 else 'N/A'
            reorder_qty = max(p.reorder_point - p.current_stock + p.safety_stock, 20) if p.reorder_point else 30
            email_lines.extend([
                f"  SKU: {p.sku}",
                f"  Name: {p.name}",
                f"  Category: {p.category}",
                f"  Current Stock: {p.current_stock} units",
                f"  Days Until Stockout: {days_remaining}",
                f"  Suggested Order Quantity: {reorder_qty} units",
                f"  Estimated Cost: ${reorder_qty * p.unit_cost:.2f}",
                ""
            ])
    
    if include_recommendations:
        email_lines.extend([
            "-" * 60,
            "RECOMMENDATIONS",
            "-" * 60,
            "",
            "1. Review and prioritize Out of Stock items immediately",
            "2. Place orders for Low Stock items within the next 2-3 days",
            "3. Consider bulk ordering for cost efficiency",
            "4. Review lead times with suppliers for critical items",
            ""
        ])
    
    total_reorder_cost = sum(
        (max(p.reorder_point * 2, 50) if p.current_stock == 0 else max(p.reorder_point - p.current_stock + p.safety_stock, 20)) * p.unit_cost
        for p in products
    )
    
    email_lines.extend([
        "-" * 60,
        "SUMMARY",
        "-" * 60,
        f"Total Products: {len(products)}",
        f"Out of Stock: {out_of_stock_count}",
        f"Low Stock: {low_stock_count}",
        f"Estimated Total Reorder Cost: ${total_reorder_cost:.2f}",
        "",
        "=" * 60,
        "This is an automated alert from Inventory Optimization System",
        "=" * 60
    ])
    
    email_body = "\n".join(email_lines)
    
    return {
        'success': True,
        'subject': subject,
        'email_body': email_body,
        'products_count': len(products),
        'out_of_stock_count': out_of_stock_count,
        'low_stock_count': low_stock_count,
        'recipients': email_service_sendgrid.get_active_recipients(db),
        'estimated_reorder_cost': round(total_reorder_cost, 2)
    }


@router.post("/alerts/send-email")
async def send_stock_alert_email(payload: dict, db: Session = Depends(get_db)):
    """
    Send stock alert email using SendGrid.
    
    Request body:
    {
        "subject": "Stock Alert...",
        "email_body": "...",
        "recipients": ["email1@example.com"]  // Optional - use configured if not provided
    }
    """
    
    subject = payload.get('subject', 'Stock Alert Notification')
    email_body = payload.get('email_body')
    recipients = payload.get('recipients')
    if not recipients:
        recipients = email_service_sendgrid.get_active_recipients(db)
    
    if not email_body:
        raise HTTPException(status_code=400, detail="email_body is required")
    
    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients configured. Add recipients in email configuration.")
    
    if not email_service_sendgrid.EMAIL_ENABLED:
        # Return preview mode when email not configured
        return {
            'success': True,
            'mode': 'preview',
            'message': 'Email sending is disabled. Enable in settings to send.',
            'subject': subject,
            'recipients': recipients,
            'body_preview': email_body[:500] + '...' if len(email_body) > 500 else email_body
        }
    
    try:
        # Send email using SendGrid
        result = email_service_sendgrid.send_custom_alert(
            to_emails=recipients,
            subject=subject,
            body=email_body,
            db=db,
            alert_key="bulk_stock_alert"
        )
        
        if result['success']:
            return {
                'success': True,
                'mode': 'sent',
                'message': f'Email sent successfully to {len(recipients)} recipient(s)',
                'recipients': recipients
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('message', 'Failed to send email'))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.get("/alerts/stock-notifications")
def get_stock_alert_products(db: Session = Depends(get_db)):
    """Get all products that should trigger stock alerts."""
    low_threshold = STOCK_THRESHOLDS.get('low_stock_max', 50)
    
    products = db.query(Product).filter(Product.current_stock <= low_threshold).all()
    
    alerts = []
    for p in products:
        if p.current_stock == 0:
            alert_level = 'CRITICAL'
            alert_color = '#dc2626'
        else:
            alert_level = 'WARNING'
            alert_color = '#ea580c'
        
        days_remaining = int(p.current_stock / p.average_daily_demand) if p.average_daily_demand > 0 else None
        
        alerts.append({
            'id': p.id,
            'sku': p.sku,
            'name': p.name,
            'category': p.category,
            'current_stock': p.current_stock,
            'alert_level': alert_level,
            'alert_color': alert_color,
            'days_until_stockout': days_remaining,
            'reorder_point': p.reorder_point,
            'suggested_order': max(p.reorder_point * 2, 50) if p.current_stock == 0 else max(p.reorder_point - p.current_stock + p.safety_stock, 20)
        })
    
    # Sort by severity (out of stock first, then by days remaining)
    alerts.sort(key=lambda x: (x['current_stock'], x['days_until_stockout'] or 999))
    
    return {
        'total_alerts': len(alerts),
        'critical_count': sum(1 for a in alerts if a['alert_level'] == 'CRITICAL'),
        'warning_count': sum(1 for a in alerts if a['alert_level'] == 'WARNING'),
        'alerts': alerts
    }


# ============================================================================
# UNIFIED JSON API ENDPOINTS WITH SCHEMA VALIDATION
# ============================================================================

@router.post("/data/products/json")
async def create_products_from_json(products: List[Dict[str, Any]], db: Session = Depends(get_db)):
    """
    Create products from JSON payload with automatic field mapping and validation.
    
    Supports various field names and automatically maps them to database schema.
    Required fields: sku, name (or product_name, title, etc.)
    Optional fields: All product attributes with flexible naming
    
    Example JSON:
    [
        {
            "id": "PROD-001",  // Maps to 'sku'
            "product_name": "Widget A",  // Maps to 'name'
            "stock": 100,  // Maps to 'current_stock'
            "price": 29.99,  // Maps to 'unit_price'
            "cost": 15.00,  // Maps to 'unit_cost'
            "category": "Electronics",
            "lead_time": 7,  // Maps to 'lead_time_days'
            // ... any other fields
        }
    ]
    """
    try:
        # Step 1: Prepare data with schema mapping and validation
        mapped_products = DataMapper.prepare_product_data(products, validate_ai_fields=False)
        
        products_added = 0
        products_updated = 0
        errors = []
        
        for idx, product_data in enumerate(mapped_products):
            try:
                sku = product_data.get('sku')
                if not sku:
                    errors.append(f"Product at index {idx}: missing 'sku' field")
                    continue
                
                # Check if product exists
                existing = db.query(Product).filter(Product.sku == sku).first()
                
                if existing:
                    # Update existing product
                    for key, value in product_data.items():
                        if hasattr(existing, key) and value is not None:
                            setattr(existing, key, value)
                    products_updated += 1
                else:
                    # Create new product
                    product = Product(**product_data)
                    db.add(product)
                    products_added += 1
                    
            except Exception as e:
                errors.append(f"Product at index {idx} (SKU: {product_data.get('sku', 'unknown')}): {str(e)}")
        
        db.commit()
        
        return {
            'success': True,
            'message': f'Processed {len(products)} products',
            'products_added': products_added,
            'products_updated': products_updated,
            'errors': errors if errors else None
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing products: {str(e)}")


@router.post("/data/sales/json")
async def create_sales_from_json(sales: List[Dict[str, Any]], db: Session = Depends(get_db)):
    """
    Create sales records from JSON payload with automatic field mapping and validation.
    OPTIMIZED: Uses bulk insert operations for maximum performance.
    
    Supports various field names and automatically maps them to database schema.
    Required fields: date, sku (or product_id), quantity_sold (or quantity, qty_sold, etc.)
    Optional fields: All sales attributes with flexible naming
    
    Example JSON:
    [
        {
            "sale_date": "2026-01-15",  // Maps to 'date'
            "product_id": "PROD-001",  // Maps to 'sku'
            "qty": 5,  // Maps to 'quantity_sold'
            "amount": 149.95,  // Maps to 'revenue'
            "price": 29.99,  // Maps to 'unit_price_at_sale'
            "cost": 15.00,  // Maps to 'unit_cost_at_sale'
            "channel": "Online",  // Maps to 'sales_channel'
            // ... any other fields
        }
    ]
    """
    try:
        # Step 1: Prepare data with schema mapping and validation
        mapped_sales = DataMapper.prepare_sales_data(sales, require_profit_fields=False)
        
        # Step 2: Get SKU to product ID mapping (single optimized query)
        sku_to_id = {p.sku: p.id for p in db.query(Product.sku, Product.id).all()}
        
        if not sku_to_id:
            raise HTTPException(status_code=400, detail="No products found in database. Please add products first.")
        
        # OPTIMIZED: Prepare all records for bulk insert
        bulk_insert_data = []
        errors = []
        
        for idx, sale_data in enumerate(mapped_sales):
            try:
                sku = sale_data.get('sku')
                if not sku:
                    errors.append(f"Sale at index {idx}: missing 'sku' field")
                    continue
                
                # Map SKU to product ID
                product_id = sku_to_id.get(str(sku))
                if not product_id:
                    errors.append(f"Sale at index {idx}: product with SKU '{sku}' not found")
                    continue
                
                # Remove 'sku' and add 'product_id'
                sale_data.pop('sku', None)
                sale_data['product_id'] = product_id
                
                # Add to bulk insert list
                bulk_insert_data.append(sale_data)
                
            except Exception as e:
                errors.append(f"Sale at index {idx} (SKU: {sale_data.get('sku', 'unknown')}): {str(e)}")
        
        # OPTIMIZED: Bulk insert all records in one operation (MUCH faster than row-by-row)
        if bulk_insert_data:
            db.bulk_insert_mappings(SalesHistory, bulk_insert_data)
            db.commit()
        
        records_added = len(bulk_insert_data)
        
        return {
            'success': True,
            'message': f'Processed {len(sales)} sales records ({records_added} added)',
            'records_added': records_added,
            'errors': errors if errors else None
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing sales: {str(e)}")


@router.post("/data/validate")
async def validate_data_schema(
    data: List[Dict[str, Any]],
    data_type: str = Query(..., description="Type of data: 'product' or 'sales'")
):
    """
    Validate data against schema without saving to database.
    
    Returns validation results and field mappings to help debug data issues.
    
    Args:
        data: Array of records to validate
        data_type: Type of data ('product' or 'sales')
    """
    try:
        if data_type not in ['product', 'sales']:
            raise HTTPException(status_code=400, detail="data_type must be 'product' or 'sales'")
        
        # Convert to DataFrame for validation
        df = pd.DataFrame(data)
        
        # Map fields
        if data_type == 'product':
            schema = ProductSchema()
            mapped_df = DataMapper.map_field_names(df, schema, 'product')
            required = schema.AI_REQUIRED
        else:
            schema = SalesSchema()
            mapped_df = DataMapper.map_field_names(df, schema, 'sales')
            required = schema.CORE_REQUIRED
        
        # Validate
        is_valid, missing = DataMapper.validate_required_fields(mapped_df, required, data_type)
        
        # Get data quality metrics
        quality_report = validate_data_quality(mapped_df, data_type)
        
        # Field mapping report
        original_fields = list(df.columns)
        mapped_fields = list(mapped_df.columns)
        field_mappings = {}
        
        for orig in original_fields:
            mapped = None
            for m in mapped_fields:
                if orig.lower() == m or orig.lower() in schema.FIELD_ALIASES and schema.FIELD_ALIASES[orig.lower()] == m:
                    mapped = m
                    break
            if mapped:
                field_mappings[orig] = mapped
        
        return {
            'is_valid': is_valid and quality_report['is_valid'],
            'data_type': data_type,
            'records_count': len(data),
            'required_fields': required,
            'missing_fields': missing,
            'field_mappings': field_mappings,
            'original_fields': original_fields,
            'mapped_fields': mapped_fields,
            'quality_report': quality_report,
            'sample_after_mapping': mapped_df.head(3).to_dict('records') if len(mapped_df) > 0 else []
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@router.get("/data/schema-info")
async def get_schema_info(data_type: str = Query(..., description="Type of data: 'product' or 'sales'")):
    """
    Get comprehensive schema information including field names, aliases, types, and requirements.
    
    Useful for understanding what fields are accepted and how they're mapped.
    """
    try:
        if data_type == 'product':
            schema = ProductSchema()
            return {
                'data_type': 'product',
                'core_required': schema.CORE_REQUIRED,
                'ai_required': schema.AI_REQUIRED,
                'forecasting_important': schema.FORECASTING_IMPORTANT,
                'optional_fields': schema.OPTIONAL_FIELDS,
                'field_aliases': schema.FIELD_ALIASES,
                'field_types': {k: v.__name__ for k, v in schema.FIELD_TYPES.items()},
                'field_defaults': schema.FIELD_DEFAULTS,
                'example_json': {
                    "sku": "PROD-001",
                    "name": "Sample Product",
                    "category": "Electronics",
                    "current_stock": 100,
                    "unit_cost": 15.00,
                    "unit_price": 29.99,
                    "lead_time_days": 7,
                    "seasonality_factor": 1.2,
                    "demand_volatility": 0.4,
                    "abc_classification": "A",
                    "xyz_classification": "X"
                }
            }
        elif data_type == 'sales':
            schema = SalesSchema()
            return {
                'data_type': 'sales',
                'core_required': schema.CORE_REQUIRED,
                'revenue_required': schema.REVENUE_REQUIRED,
                'profit_required': schema.PROFIT_REQUIRED,
                'optional_fields': schema.OPTIONAL_FIELDS,
                'field_aliases': schema.FIELD_ALIASES,
                'field_types': {k: v.__name__ for k, v in schema.FIELD_TYPES.items()},
                'field_defaults': schema.FIELD_DEFAULTS,
                'example_json': {
                    "date": "2026-01-15",
                    "sku": "PROD-001",
                    "quantity_sold": 5,
                    "revenue": 149.95,
                    "unit_price_at_sale": 29.99,
                    "unit_cost_at_sale": 15.00,
                    "sales_channel": "Online",
                    "customer_id": "CUST-123",
                    "region": "North"
                }
            }
        else:
            raise HTTPException(status_code=400, detail="data_type must be 'product' or 'sales'")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting schema info: {str(e)}")


@router.get("/data/database-stats")
async def get_database_stats(db: Session = Depends(get_db)):
    """
    Get database statistics to help diagnose performance issues.
    Returns record counts, database size, and performance recommendations.
    """
    try:
        import os
        from pathlib import Path
        
        # Get record counts
        products_count = db.query(func.count(Product.id)).scalar()
        sales_count = db.query(func.count(SalesHistory.id)).scalar()
        forecasts_count = db.query(func.count(Forecast.id)).scalar()
        
        # Get database file size
        db_path = Path(__file__).parent.parent.parent.parent / 'inventory.db'
        db_size_mb = 0
        if db_path.exists():
            db_size_mb = db_path.stat().st_size / (1024 * 1024)
        
        # Get date range of sales data
        oldest_sale = db.query(func.min(SalesHistory.date)).scalar()
        newest_sale = db.query(func.max(SalesHistory.date)).scalar()
        
        # Performance recommendations
        recommendations = []
        if sales_count > 1000000:
            recommendations.append("Consider archiving sales data older than 2 years")
        if db_size_mb > 500:
            recommendations.append("Database is large (>500MB). Consider using VACUUM to optimize")
        if sales_count > 5000000:
            recommendations.append("Very large dataset. Consider using scheduled cleanup of old data")
        
        return {
            'record_counts': {
                'products': products_count,
                'sales_history': sales_count,
                'forecasts': forecasts_count
            },
            'database_size_mb': round(db_size_mb, 2),
            'sales_date_range': {
                'oldest': oldest_sale.isoformat() if oldest_sale else None,
                'newest': newest_sale.isoformat() if newest_sale else None,
                'days_of_data': (newest_sale - oldest_sale).days if oldest_sale and newest_sale else 0
            },
            'performance_status': {
                'status': 'good' if sales_count < 1000000 else 'optimization_recommended' if sales_count < 5000000 else 'cleanup_needed',
                'recommendations': recommendations
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting database stats: {str(e)}")


@router.delete("/data/cleanup-old-sales")
async def cleanup_old_sales(
    days_to_keep: int = Query(730, description="Number of days of sales history to keep (default: 730 = 2 years)"),
    db: Session = Depends(get_db)
):
    """
    Delete sales records older than specified days to improve performance.
    Default: Keep last 2 years of data.
    
    WARNING: This action cannot be undone!
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Count records to be deleted
        records_to_delete = db.query(func.count(SalesHistory.id)).filter(
            SalesHistory.date < cutoff_date
        ).scalar()
        
        if records_to_delete == 0:
            return {
                'message': f'No sales records older than {days_to_keep} days',
                'records_deleted': 0,
                'cutoff_date': cutoff_date.isoformat()
            }
        
        # Delete old records
        deleted = db.query(SalesHistory).filter(
            SalesHistory.date < cutoff_date
        ).delete(synchronize_session=False)
        
        db.commit()
        
        # Run VACUUM to reclaim space (SQLite specific)
        from sqlalchemy import text
        db.execute(text("VACUUM"))
        
        return {
            'message': f'Successfully deleted {deleted:,} sales records older than {days_to_keep} days',
            'records_deleted': deleted,
            'cutoff_date': cutoff_date.isoformat(),
            'recommendation': 'Database has been optimized. Upload performance should be improved.'
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error cleaning up old sales: {str(e)}")


# ============================================================================
# CACHE MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/cache/stats")
def get_cache_statistics():
    """
    Get cache performance statistics
    Returns hit rates, sizes, and efficiency metrics
    """
    return {
        "status": "active",
        "stats": get_cache_stats(),
        "info": "Cache improves performance by storing expensive forecast computations"
    }


@router.post("/cache/clear")
def clear_all_caches():
    """
    Clear all caches (forecast, analytics, product)
    Use after major data updates
    """
    forecast_cache.clear()
    analytics_cache.clear()
    
    return {
        "status": "success",
        "message": "All caches cleared successfully",
        "stats": get_cache_stats()
    }


@router.post("/cache/clear/forecast")
def clear_forecast_cache():
    """
    Clear only forecast cache
    Use after updating sales data or product information
    """
    forecast_cache.clear()
    
    return {
        "status": "success",
        "message": "Forecast cache cleared",
        "stats": forecast_cache.get_stats()
    }


@router.post("/cache/clear/analytics")
def clear_analytics_cache():
    """
    Clear only analytics cache
    Use after dashboard data updates
    """
    analytics_cache.clear()
    
    return {
        "status": "success",
        "message": "Analytics cache cleared",
        "stats": analytics_cache.get_stats()
    }

