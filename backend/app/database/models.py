from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(255), unique=True, index=True)
    name = Column(String(255), index=True)
    category = Column(String(255), index=True)
    current_stock = Column(Integer, default=0)
    unit_cost = Column(Float)
    unit_price = Column(Float)
    lead_time_days = Column(Integer, default=7)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Extended columns for better predictions
    reorder_point = Column(Float, nullable=True)
    safety_stock = Column(Float, nullable=True)
    average_daily_demand = Column(Float, nullable=True)
    supplier_id = Column(String(50), nullable=True)
    min_order_qty = Column(Integer, nullable=True)
    max_order_qty = Column(Integer, nullable=True)
    order_frequency_days = Column(Integer, nullable=True)
    
    # Demand characteristics (important for predictions)
    seasonality_factor = Column(Float, default=1.0)  # Multiplier for seasonal demand
    demand_volatility = Column(Float, default=0.5)   # 0-1 scale, higher = more volatile
    profit_margin = Column(Float, nullable=True)
    
    # Classification (for prioritization)
    abc_classification = Column(String(1), nullable=True)  # A, B, or C
    xyz_classification = Column(String(1), nullable=True)  # X, Y, or Z
    product_priority = Column(String(20), nullable=True)   # HIGH, MEDIUM, LOW, CRITICAL
    
    # Product attributes
    weight_kg = Column(Float, nullable=True)
    volume_m3 = Column(Float, nullable=True)
    shelf_life_days = Column(Integer, nullable=True)
    is_perishable = Column(Boolean, default=False)
    is_hazardous = Column(Boolean, default=False)
    
    # Cost factors
    storage_cost_per_unit = Column(Float, nullable=True)
    stockout_cost_per_unit = Column(Float, nullable=True)
    target_service_level = Column(Float, default=0.95)
    
    # Calculated/derived fields
    economic_order_qty = Column(Float, nullable=True)
    inventory_turnover = Column(Float, nullable=True)
    weeks_of_supply = Column(Float, nullable=True)
    stock_status = Column(String(20), nullable=True)
    
    # Tracking dates
    last_order_date = Column(DateTime, nullable=True)
    last_sale_date = Column(DateTime, nullable=True)
    
    # Description for extra data storage
    description = Column(Text, nullable=True)
    
    sales = relationship("SalesHistory", back_populates="product")
    forecasts = relationship("Forecast", back_populates="product")
    recommendations = relationship("InventoryRecommendation", back_populates="product")

class SalesHistory(Base):
    __tablename__ = "sales_history"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    date = Column(DateTime, index=True)
    quantity_sold = Column(Integer)
    revenue = Column(Float)
    
    # ENHANCED: Transaction-time pricing for accurate loss calculations
    unit_price_at_sale = Column(Float, nullable=True)  # Actual selling price per unit at transaction time
    unit_cost_at_sale = Column(Float, nullable=True)   # Cost per unit at transaction time
    profit_loss_amount = Column(Float, nullable=True)  # (unit_price - unit_cost) * quantity
    profit_margin_pct = Column(Float, nullable=True)   # (price - cost) / price as percentage
    
    # ENHANCED: Discount and promotion tracking
    discount_applied = Column(Float, nullable=True)    # Discount percentage (0.15 = 15% off)
    transaction_type = Column(String(20), nullable=True)  # 'Normal', 'Clearance', 'Promotional', 'Markdown'
    promotion_id = Column(String(50), nullable=True)   # Link to promotion campaign
    
    # ENHANCED: Channel and segmentation
    sales_channel = Column(String(20), nullable=True)  # 'Online', 'Store', 'Wholesale', 'B2B'
    customer_id = Column(String(50), nullable=True)    # Customer identifier for repeat analysis
    region = Column(String(50), nullable=True)         # Geographic region
    
    product = relationship("Product", back_populates="sales")

class Forecast(Base):
    __tablename__ = "forecasts"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    forecast_date = Column(DateTime, index=True)
    predicted_demand = Column(Float)
    lower_bound = Column(Float)
    upper_bound = Column(Float)
    confidence_level = Column(Float, default=0.95)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="forecasts")

class InventoryRecommendation(Base):
    __tablename__ = "inventory_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    reorder_point = Column(Float)
    safety_stock = Column(Float)
    economic_order_quantity = Column(Float)
    optimal_stock_level = Column(Float)
    estimated_cost_savings = Column(Float)
    recommendation_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="recommendations")

class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    supplier_name = Column(String(255), index=True)
    country = Column(String(100), index=True)
    region = Column(String(100))
    contact_email = Column(String(255))
    contact_phone = Column(String(50))
    unit_cost = Column(Float)
    lead_time_days = Column(Integer, default=7)
    moq = Column(Float, default=1.0)
    on_time_delivery_rate = Column(Float, default=0.95)
    quality_score = Column(Float, default=0.9)
    financial_health_score = Column(Float, default=0.8)
    relationship_duration_months = Column(Integer, default=0)
    price_trend = Column(String(50), default="stable")  # stable, increasing, decreasing
    esg_compliance_score = Column(Float, default=0.75)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    performance = relationship("SupplierPerformance", back_populates="supplier")
    risk_scores = relationship("SupplierRiskScore", back_populates="supplier")

class SupplierPerformance(Base):
    __tablename__ = "supplier_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    overall_score = Column(Float)
    delivery_score = Column(Float)
    quality_score = Column(Float)
    lead_time_score = Column(Float)
    cost_score = Column(Float)
    rating = Column(String(10))  # A+, A, B, C, D
    created_at = Column(DateTime, default=datetime.utcnow)
    
    supplier = relationship("Supplier", back_populates="performance")

class SupplierRiskScore(Base):
    __tablename__ = "supplier_risk_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    overall_risk_score = Column(Float)  # 0-100, higher = more risky
    external_risk_score = Column(Float)  # Political, natural disasters, trade
    financial_risk_score = Column(Float)  # Financial health, payment history
    operational_risk_score = Column(Float)  # On-time delivery, capacity
    quality_risk_score = Column(Float)  # Quality issues, ESG compliance
    relationship_risk_score = Column(Float)  # Partnership duration, communication
    risk_level = Column(String(20))  # LOW, MEDIUM, HIGH, CRITICAL
    recommendation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    supplier = relationship("Supplier", back_populates="risk_scores")

class CountryRisk(Base):
    __tablename__ = "country_risks"
    
    id = Column(Integer, primary_key=True, index=True)
    country = Column(String(100), unique=True, index=True)
    risk_index = Column(Float)  # 0-100, higher = more risky
    risk_level = Column(String(20))  # LOW, MEDIUM, HIGH, CRITICAL
    risk_factors = Column(Text)  # JSON: political, economic, natural_disaster, trade
    last_updated = Column(DateTime, default=datetime.utcnow)
    updated_by = Column(String(100), default="system")

class DemandAlert(Base):
    __tablename__ = "demand_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    alert_type = Column(String(50))  # ANOMALY, TREND_CHANGE, SEASONAL, PROMOTION
    alert_level = Column(String(50))  # LOW, MEDIUM, HIGH
    description = Column(Text)
    anomaly_data = Column(Text)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged = Column(String(10), default="false")

class ScenarioResult(Base):
    __tablename__ = "scenario_results"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    scenario_name = Column(String(255))
    scenario_type = Column(String(50))  # PRICE_CHANGE, DEMAND_SHIFT, SUPPLIER_SWITCH
    parameters = Column(Text)  # JSON
    results = Column(Text)  # JSON
    impact_summary = Column(Text)
    recommendation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AlertRecipient(Base):
    __tablename__ = "alert_recipients"

    id = Column(Integer, primary_key=True, index=True)
    channel = Column(String(20), default="EMAIL", index=True)
    destination = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    severity_filter = Column(String(20), default="ALL")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    channel = Column(String(20), index=True)
    subject = Column(String(255))
    recipients = Column(Text)
    status = Column(String(20), index=True)
    response_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    payload = Column(Text, nullable=True)
    alert_key = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ApiImportLog(Base):
    """Tracks every JSON API import — Tier 2 metadata for the two-tier storage system."""
    __tablename__ = "api_import_logs"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(100), index=True)          # e.g. "fakestoreapi", "dummyjson"
    source_url = Column(String(500))                        # Full API URL fetched
    data_type = Column(String(20), index=True)              # products, sales, inventory
    raw_file_path = Column(String(500))                     # Tier 1: path to raw JSON on disk
    processed_file_path = Column(String(500), nullable=True) # Path to mapped JSON (optional)
    record_count = Column(Integer, default=0)               # Number of records in the response
    records_added = Column(Integer, default=0)               # New records inserted into DB
    records_updated = Column(Integer, default=0)             # Existing records updated in DB
    file_size_bytes = Column(Integer, default=0)             # Size of raw JSON file
    status = Column(String(20), default="success", index=True)  # success, failed, partial
    error_message = Column(Text, nullable=True)              # Error details if failed
    import_duration_ms = Column(Integer, nullable=True)      # How long the import took
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
