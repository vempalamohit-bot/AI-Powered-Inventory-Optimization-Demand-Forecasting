# Technical Document — AI-Powered Inventory Optimization & Demand Forecasting

**Author:** Mohit Rao — Data and AI Engineering, Miracle Software Systems  
**Version:** 1.0  
**Date:** February 2026  
**Repository:** [github.com/vempalamohit-bot/AI-Powered-Inventory-Optimization-Demand-Forecasting](https://github.com/vempalamohit-bot/AI-Powered-Inventory-Optimization-Demand-Forecasting)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Backend — FastAPI Server](#4-backend--fastapi-server)
5. [Database Schema](#5-database-schema)
6. [AI/ML Models & Algorithms](#6-aiml-models--algorithms)
7. [API Reference — 124 Endpoints](#7-api-reference--124-endpoints)
8. [Frontend — React Application](#8-frontend--react-application)
9. [Data Pipeline](#9-data-pipeline)
10. [Deployment — Google Colab](#10-deployment--google-colab)
11. [Integration Layer](#11-integration-layer)
12. [Performance & Caching](#12-performance--caching)
13. [Security & Configuration](#13-security--configuration)
14. [Testing & Validation](#14-testing--validation)
15. [Appendix](#15-appendix)

---

## 1. Executive Summary

This system is an **end-to-end AI/ML-powered inventory optimization engine** built to answer three questions at scale: *What to order, how much, and when.* It processes **50,000 products** and **2 million sales records** using **7 forecasting models**, real-time stockout detection, automated reorder recommendations, and markdown optimization — all accessible through a modern web dashboard.

### Key Capabilities

| Capability | Description |
|:-----------|:------------|
| **Demand Forecasting** | 7 ML models with automatic per-product selection based on demand segmentation |
| **Stockout Detection** | Real-time alerts with dollar-level impact quantification |
| **Reorder Optimization** | AI-computed order quantities using EOQ, safety stock, and lead time analysis |
| **Markdown Optimization** | Linear regression + price elasticity models for clearance pricing decisions |
| **Risk Profiling** | Product-level risk classification with service level trade-off analysis |
| **Scenario Planning** | What-if simulations for price changes, demand shifts, and supplier switches |
| **NLP Explanations** | Plain-English explanations for every AI recommendation |
| **Multi-Channel Alerts** | Email (SendGrid), Slack, and Microsoft Teams notifications |

### Scale

- **50,000 SKUs** with 36 attributes per product
- **2,000,000+ sales records** with transaction-level pricing
- **124 REST API endpoints** across 15 functional domains
- **27 AI/ML model files** implementing 20+ algorithms
- **Single-click deployment** via Google Colab (no installation required)

---

## 2. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Browser                           │
│   React 18.2 SPA (Vite 5) — Dashboard, Products, Forecasting   │
│   Recharts · axios · react-router-dom · In-Memory Cache         │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP / REST
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ API Router   │  │ Integrations │  │ Chat Router            │ │
│  │ 114 endpoints│  │ 8 endpoints  │  │ 2 endpoints (NLP Q&A)  │ │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬───────────┘ │
│         │                 │                        │             │
│  ┌──────▼─────────────────▼────────────────────────▼───────────┐│
│  │                    Service Layer                             ││
│  │  Analytics · Alert Scheduler · Notification · Email · Cache ││
│  └──────┬──────────────────────────────────────────────────────┘│
│         │                                                        │
│  ┌──────▼──────────────────────────────────────────────────────┐│
│  │                   AI/ML Model Layer                          ││
│  │  27 model files · 7 forecasters · Segmentation · Optimizer  ││
│  │  Risk Profiler · Markdown · Scenarios · NLP Explainer       ││
│  └──────┬──────────────────────────────────────────────────────┘│
│         │                                                        │
│  ┌──────▼──────────────────────────────────────────────────────┐│
│  │                   Data Access Layer                          ││
│  │  SQLAlchemy ORM · SQLite WAL · Connection Pool (20+40)      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │     SQLite Database    │
                │  inventory.db (~300MB) │
                │  11 tables · WAL mode  │
                │  64MB cache · 256MB    │
                │  mmap · Pool 20+40     │
                └───────────────────────┘
```

### Colab Deployment Architecture

```
Google Colab Runtime
├── FastAPI backend (124 API endpoints)          ← /api/*
├── React frontend (production build)            ← /*
├── SQLite database (50K products, 2M sales)     ← backend/inventory.db
└── Public tunnel (localtunnel / cloudflared)     ← https://xyz.loca.lt
         ↕
Your Browser → Full AI Dashboard
```

### Component Communication

| From | To | Protocol | Purpose |
|:-----|:---|:---------|:--------|
| React SPA | FastAPI | HTTP REST + JSON | All data operations |
| FastAPI | SQLite | SQLAlchemy ORM | Data persistence |
| FastAPI | SendGrid | HTTPS API | Email alerts |
| FastAPI | Slack | Webhook POST | Slack notifications |
| FastAPI | Teams | Webhook POST | Teams notifications |
| FastAPI | OpenAI | HTTPS API | GenAI explanations (optional) |
| Colab | localtunnel | WebSocket tunnel | Public URL access |

---

## 3. Technology Stack

### Backend

| Technology | Version | Purpose |
|:-----------|:--------|:--------|
| Python | 3.9+ (3.12 on Colab, 3.14 local) | Runtime |
| FastAPI | ≥ 0.109.0 | Web framework (async, auto-docs) |
| Uvicorn | ≥ 0.27.0 | ASGI server |
| SQLAlchemy | ≥ 2.0.25 | ORM + connection pooling |
| SQLite | 3.x (WAL mode) | Embedded database |
| Pandas | ≥ 2.1.0 | Data manipulation & CSV loading |
| NumPy | ≥ 1.24.0 | Numerical computing |
| scikit-learn | ≥ 1.4.0 | ML algorithms (Decision Trees, Linear Regression) |
| statsmodels | ≥ 0.14.0 | Time series (ARIMA, Holt-Winters, SARIMAX) |
| SciPy | ≥ 1.12.0 | Statistical functions (norm CDF, linregress) |
| XGBoost | ≥ 2.0.0 | Gradient boosting models |
| Prophet | ≥ 1.1.0 | Facebook Prophet forecasting |
| Pydantic | ≥ 2.5.0 | Data validation & serialization |
| SendGrid | ≥ 6.11.0 | Email delivery (100/day free tier) |
| httpx | ≥ 0.25.0 | Async HTTP client (webhooks) |
| OpenAI | ≥ 1.1.0 | GenAI integration (optional) |

### Frontend

| Technology | Version | Purpose |
|:-----------|:--------|:--------|
| React | 18.2.0 | UI framework |
| Vite | 5.0.11 | Build tool & dev server |
| react-router-dom | 6.21.1 | Client-side routing |
| Recharts | 2.10.3 | Chart visualizations |
| axios | 1.6.5 | HTTP client |

### Infrastructure

| Component | Details |
|:----------|:--------|
| Database | SQLite 3 — WAL mode, 64 MB cache, 256 MB mmap |
| Deployment | Google Colab (one-click), local dev (Vite + Uvicorn) |
| Tunneling | localtunnel / cloudflared for public Colab access |
| Node.js | v20 LTS (required for Vite frontend build) |

---

## 4. Backend — FastAPI Server

### Application Entry Point

**File:** `backend/main.py`

The FastAPI application is configured with:

- **Title:** AI-Powered Inventory Optimization API v1.0.0
- **Host:** `0.0.0.0:8000`
- **CORS:** Localhost origins (5173, 5174, 3000) plus regex patterns for Colab tunnels (ngrok, loca.lt, trycloudflare)
- **Database Init:** `Base.metadata.create_all()` with graceful fallback on startup
- **Background Services:** Alert scheduler starts on app startup, stops on shutdown

### Router Architecture

| Router | Prefix | File | Endpoints |
|:-------|:-------|:-----|:----------|
| Main API | `/api` | `backend/app/api/routes.py` | 114 |
| Integrations | `/api/integrations` | `backend/app/api/integrations.py` | 8 |
| Chat | `/api/chat` | `backend/app/api/chat.py` | 2 |

### Service Layer

| Service | File | Purpose |
|:--------|:-----|:--------|
| Analytics Service | `services/analytics_service.py` | Inventory turnover, DOI, slow movers, fill rate, carrying cost |
| Alert Scheduler | `services/alert_scheduler.py` | Background async scheduler with configurable interval, deduplication |
| Notification Service | `services/notification_service.py` | Multi-channel dispatch: Slack webhooks, Teams webhooks, markdown formatting |
| Email Service | `services/email_service_sendgrid.py` | SendGrid integration, DB-backed recipient management, notification logging (549 lines) |
| Cache Service | `services/cache_service.py` | Server-side forecast and analytics caching with TTL |

### Configuration

**File:** `backend/app/config.py`

| Setting | Default | Description |
|:--------|:--------|:------------|
| `environment` | `development` | Runtime environment |
| `sendgrid_api_key` | — | SendGrid API key |
| `email_from` | — | Sender email address |
| `email_enabled` | `False` | Enable/disable email alerts |
| `alert_scheduler_enabled` | `True` | Enable background alert scheduler |
| `alert_scheduler_interval_seconds` | `900` | Alert check interval (15 minutes) |
| `alert_dedupe_window_minutes` | `120` | Deduplication window (2 hours) |
| `slack_webhook_url` | — | Slack incoming webhook URL |
| `teams_webhook_url` | — | Microsoft Teams webhook URL |

---

## 5. Database Schema

**Engine:** SQLite 3 with WAL journal mode  
**File:** `backend/inventory.db`  
**ORM:** SQLAlchemy 2.0+

### Performance Configuration

```
PRAGMA journal_mode = WAL
PRAGMA synchronous = NORMAL
PRAGMA cache_size = -64000    (64 MB)
PRAGMA page_size = 8192
PRAGMA mmap_size = 268435456  (256 MB)
PRAGMA temp_store = MEMORY
```

**Connection Pool:** pool_size=20, max_overflow=40

### Entity-Relationship Diagram

```
┌──────────────┐       ┌──────────────────┐       ┌────────────────────┐
│   Product    │──1:N──│   SalesHistory   │       │     Forecast       │
│  (products)  │       │ (sales_history)  │       │   (forecasts)      │
│              │──1:N──│                  │       │                    │
│  50K records │       │  2M records      │       │                    │
└──────┬───────┘       └──────────────────┘       └────────────────────┘
       │
       ├──1:N── InventoryRecommendation (inventory_recommendations)
       │
       ├──1:N── DemandAlert (demand_alerts)
       │
       └──1:N── ScenarioResult (scenario_results)

┌──────────────┐       ┌───────────────────────┐
│   Supplier   │──1:N──│  SupplierPerformance  │
│ (suppliers)  │       │(supplier_performance) │
│              │──1:N──│                       │
│              │       │  SupplierRiskScore    │
└──────────────┘       │(supplier_risk_scores) │
                       └───────────────────────┘

┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  CountryRisk     │   │  AlertRecipient  │   │ NotificationLog  │
│ (country_risks)  │   │(alert_recipients)│   │(notification_logs│
└──────────────────┘   └──────────────────┘   └──────────────────┘

┌──────────────────┐
│  ApiImportLog    │
│ (api_import_logs)│
└──────────────────┘
```

### Table Definitions

#### `products` — 36 columns

| Column | Type | Constraints | Description |
|:-------|:-----|:------------|:------------|
| `id` | Integer | PK, indexed | Auto-increment ID |
| `sku` | String(255) | Unique, indexed | Stock Keeping Unit code |
| `name` | String(255) | Indexed | Product display name |
| `category` | String(255) | Indexed | Product category |
| `current_stock` | Integer | Default 0 | Units currently in stock |
| `unit_cost` | Float | | Cost per unit |
| `unit_price` | Float | | Selling price per unit |
| `lead_time_days` | Integer | Default 7 | Supplier lead time in days |
| `created_at` | DateTime | | Record creation timestamp |
| `reorder_point` | Float | Nullable | Computed reorder threshold |
| `safety_stock` | Float | Nullable | Buffer stock quantity |
| `average_daily_demand` | Float | Nullable | Mean daily units sold |
| `supplier_id` | String(50) | Nullable | Supplier identifier |
| `min_order_qty` | Integer | Nullable | Minimum order quantity |
| `max_order_qty` | Integer | Nullable | Maximum order quantity |
| `order_frequency_days` | Integer | Nullable | Typical order interval |
| `seasonality_factor` | Float | Default 1.0 | Seasonal demand multiplier |
| `demand_volatility` | Float | Default 0.5 | Demand variability (0–1) |
| `profit_margin` | Float | Nullable | Unit profit margin |
| `abc_classification` | String(1) | Nullable | ABC analysis class (A/B/C) |
| `xyz_classification` | String(1) | Nullable | XYZ analysis class (X/Y/Z) |
| `product_priority` | String(20) | Nullable | Priority level (CRITICAL/HIGH/MEDIUM/LOW) |
| `weight_kg` | Float | Nullable | Product weight |
| `volume_m3` | Float | Nullable | Product volume |
| `shelf_life_days` | Integer | Nullable | Shelf life in days |
| `is_perishable` | Boolean | Default False | Perishable flag |
| `is_hazardous` | Boolean | Default False | Hazardous material flag |
| `storage_cost_per_unit` | Float | Nullable | Warehousing cost per unit |
| `stockout_cost_per_unit` | Float | Nullable | Cost of stockout per unit |
| `target_service_level` | Float | Default 0.95 | Target service level (95%) |
| `economic_order_qty` | Float | Nullable | Computed EOQ |
| `inventory_turnover` | Float | Nullable | Annual turnover ratio |
| `weeks_of_supply` | Float | Nullable | Current weeks of supply |
| `stock_status` | String(20) | Nullable | Status label |
| `last_order_date` | DateTime | Nullable | Last purchase order date |
| `last_sale_date` | DateTime | Nullable | Most recent sale date |
| `description` | Text | Nullable | Free-text description |

**Relationships:** `sales` → SalesHistory, `forecasts` → Forecast, `recommendations` → InventoryRecommendation

#### `sales_history` — 15 columns

| Column | Type | Constraints | Description |
|:-------|:-----|:------------|:------------|
| `id` | Integer | PK | Auto-increment ID |
| `product_id` | Integer | FK → products.id | Product reference |
| `date` | DateTime | Indexed | Transaction date |
| `quantity_sold` | Integer | | Units sold |
| `revenue` | Float | | Transaction revenue |
| `unit_price_at_sale` | Float | Nullable | Actual selling price at transaction time |
| `unit_cost_at_sale` | Float | Nullable | Unit cost at transaction time |
| `profit_loss_amount` | Float | Nullable | (price − cost) × quantity |
| `profit_margin_pct` | Float | Nullable | (price − cost) / price as percentage |
| `discount_applied` | Float | Nullable | Discount percentage (0.15 = 15%) |
| `transaction_type` | String(20) | Nullable | Normal / Clearance / Promotional / Markdown |
| `promotion_id` | String(50) | Nullable | Promotion campaign ID |
| `sales_channel` | String(20) | Nullable | Online / Store / Wholesale / B2B |
| `customer_id` | String(50) | Nullable | Customer identifier |
| `region` | String(50) | Nullable | Geographic region |

#### `forecasts` — 7 columns

| Column | Type | Description |
|:-------|:-----|:------------|
| `id` | Integer | PK |
| `product_id` | Integer | FK → products.id |
| `forecast_date` | DateTime | Predicted date |
| `predicted_demand` | Float | Forecasted units |
| `lower_bound` | Float | Lower confidence bound |
| `upper_bound` | Float | Upper confidence bound |
| `confidence_level` | Float | Default 0.95 (95%) |

#### `inventory_recommendations` — 8 columns

| Column | Type | Description |
|:-------|:-----|:------------|
| `id` | Integer | PK |
| `product_id` | Integer | FK → products.id |
| `reorder_point` | Float | Suggested reorder threshold |
| `safety_stock` | Float | Suggested safety stock |
| `economic_order_quantity` | Float | Optimal order size |
| `optimal_stock_level` | Float | Target stock level |
| `estimated_cost_savings` | Float | Projected savings |
| `recommendation_notes` | Text | AI-generated notes |

#### Additional Tables

| Table | Key Fields | Purpose |
|:------|:-----------|:--------|
| `suppliers` | name, country, lead_time, MOQ, on_time_rate, quality_score | Supplier master data |
| `supplier_performance` | supplier_id, overall_score, rating (A+/A/B/C/D) | Performance tracking |
| `supplier_risk_scores` | supplier_id, risk_level (LOW/MEDIUM/HIGH/CRITICAL) | Risk assessment |
| `country_risks` | country (unique), risk_index (0–100), risk_factors (JSON) | Geopolitical risk |
| `demand_alerts` | product_id, alert_type, alert_level, anomaly_data (JSON) | AI-generated alerts |
| `scenario_results` | product_id, scenario_type, parameters (JSON), results (JSON) | What-if outputs |
| `alert_recipients` | channel, destination, severity_filter, active | Notification routing |
| `notification_logs` | channel, subject, status, response_code, alert_key | Audit trail |
| `api_import_logs` | source_url, data_type, record_count, status, duration_ms | Import history |

### Indexes

```sql
CREATE INDEX ix_products_id ON products (id);
CREATE UNIQUE INDEX ix_products_sku ON products (sku);
CREATE INDEX ix_products_name ON products (name);
CREATE INDEX ix_products_category ON products (category);
CREATE INDEX ix_sales_history_id ON sales_history (id);
CREATE INDEX ix_sales_history_date ON sales_history (date);
CREATE INDEX ix_sales_product_id ON sales_history (product_id);
```

---

## 6. AI/ML Models & Algorithms

### 6.1 Multi-Model Demand Forecasting Engine

**Primary File:** `backend/app/models/enhanced_forecaster.py` (1,041 lines)  
**Class:** `EnhancedDemandForecaster`

This is the **core forecasting engine**. It implements intelligent model selection — instead of using one algorithm for all products, it segments each product by its demand characteristics and selects the best-fit model automatically.

#### Model Selection Pipeline

```
Input: Product sales history (daily)
         │
         ▼
┌─────────────────────────────┐
│  Product Segmentation       │
│  (ProductSegmenter)         │
│                             │
│  Metrics computed:          │
│  • Coefficient of Variation │
│  • Zero-sales percentage    │
│  • Seasonality strength     │
│  • Trend detection          │
│                             │
│  Output: STABLE | SEASONAL  │
│          VOLATILE | INTERMIT│
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│  Model Selection Matrix                      │
│                                              │
│  STABLE      → Holt-Winters (additive)       │
│  SEASONAL    → SARIMA / Holt-Winters (multi) │
│  VOLATILE    → XGBoost / Weighted Ensemble    │
│  INTERMITTENT→ Seasonal Naive / Croston-like  │
└──────────┬──────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│  Preprocessing                               │
│  • Weekly aggregation (sparse data)          │
│  • Day-of-week weighting                     │
│  • Smoothing (_smooth_weekly_data)           │
│  • Seasonal enrichment (_enrich_seasonality) │
│  • Outlier capping at 2× upper bound        │
└──────────┬──────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│  Forecast Generation                         │
│  • Point forecast (predicted demand)         │
│  • Confidence intervals (95%)                │
│  • Model metadata & accuracy metrics         │
│  • Plain-English explanation                 │
└─────────────────────────────────────────────┘
```

#### 7 Forecasting Models

| # | Model | Algorithm | Best For | Key Parameters |
|:--|:------|:----------|:---------|:---------------|
| 1 | **Holt-Winters (Additive)** | Exponential Smoothing with trend + seasonal components | Stable demand with additive seasonality | `seasonal_periods=7`, relaxed constraints |
| 2 | **Holt-Winters (Multiplicative)** | Exponential Smoothing with multiplicative seasonality | Seasonal demand with proportional variation | `seasonal='mul'`, epsilon for zeros |
| 3 | **SARIMA** | Seasonal ARIMA (p,d,q)(P,D,Q,s) | Seasonal patterns with autocorrelation | `order=(1,1,1)`, `seasonal_order=(1,1,1,7)` |
| 4 | **Seasonal Naive** | Last-season repeat with trend adjustment | Intermittent or sparse data | Uses median of same day-of-week |
| 5 | **XGBoost** | Gradient Boosted Decision Trees | Volatile demand with complex patterns | Features: lag, rolling mean, day/month/quarter |
| 6 | **Prophet** | Facebook Prophet (additive regression) | Strong seasonality + holidays | `yearly_seasonality=True`, `weekly_seasonality=True` |
| 7 | **Weighted Ensemble** | Weighted average of top-performing models | General-purpose best accuracy | Weights by inverse MAPE |

#### Product Segmentation Logic

**File:** `backend/app/models/product_segmentation.py` (231 lines)  
**Class:** `ProductSegmenter`

| Segment | Criteria | % of Typical Catalog |
|:--------|:---------|:---------------------|
| **STABLE** | CV < 0.5, low zero-sales %, no strong seasonality | ~40% |
| **SEASONAL** | Seasonality strength > 0.3 (via STL decomposition) | ~25% |
| **VOLATILE** | CV > 1.0, unpredictable but non-zero | ~20% |
| **INTERMITTENT** | Zero-sales > 30%, sporadic demand | ~15% |

#### Preprocessing Techniques

| Technique | Purpose | Implementation |
|:----------|:--------|:---------------|
| **Weekly Aggregation** | Handles sparse daily data by rolling up to weekly | Sum daily values into 7-day bins |
| **Smoothing** | Reduces noise in weekly time series | Moving average with configurable window |
| **Seasonal Enrichment** | Amplifies seasonal signal before model fitting | Adds synthetic seasonal component from historical patterns |
| **Outlier Capping** | Prevents extreme values from skewing forecasts | Caps at 2× the 75th percentile |
| **Day-of-Week Weighting** | Accounts for weekday vs weekend patterns | Weighted aggregation factors |

#### Accuracy Metrics

| Metric | Description | Target |
|:-------|:------------|:-------|
| **MAPE** | Mean Absolute Percentage Error | < 25% |
| **MAE** | Mean Absolute Error | Context-dependent |
| **RMSE** | Root Mean Squared Error | Context-dependent |
| **R²** | Coefficient of Determination | > 0.70 |
| **Bias** | Systematic over/under prediction | Near 0 |

### 6.2 Inventory Optimization

**File:** `backend/app/models/inventory_optimizer.py` (673 lines)  
**Class:** `InventoryOptimizer`

| Algorithm | Formula | Purpose |
|:----------|:--------|:--------|
| **Economic Order Quantity (EOQ)** | $EOQ = \sqrt{\frac{2DS}{H}}$ where D=annual demand, S=ordering cost, H=holding cost | Optimal order size to minimize total cost |
| **Reorder Point** | $ROP = \bar{d} \times L + SS$ where $\bar{d}$=avg daily demand, L=lead time, SS=safety stock | When to place an order |
| **Safety Stock** | $SS = z_\alpha \times \sigma_d \times \sqrt{L}$ where $z_\alpha$=service level z-score, $\sigma_d$=demand std dev | Buffer against demand uncertainty |
| **Total Cost Optimization** | $TC = \frac{D}{Q}S + \frac{Q}{2}H + p \times P(stockout)$ | Balances ordering, holding, and stockout costs |
| **ABC Analysis** | Pareto classification by revenue contribution | A (top 80%), B (next 15%), C (bottom 5%) |

### 6.3 Markdown Optimization

**File:** `backend/app/models/markdown_optimizer.py` (520 lines)  
**Class:** `MarkdownOptimizer`

Determines optimal clearance pricing for slow-moving inventory.

| Method | Algorithm | Output |
|:-------|:----------|:-------|
| **Trend Detection** | Linear regression on sales velocity | Demand trajectory (rising/falling/flat) |
| **Demand Velocity** | Units sold per day over rolling window | Velocity score (0–1) |
| **Seasonality Detection** | Periodic pattern analysis | Seasonal coefficients |
| **Price Elasticity** | $E = \frac{\%\Delta Q}{\%\Delta P}$ — estimated from historical markdown data | Elasticity coefficient |
| **Revenue Optimization** | Monte Carlo simulation across discount scenarios | 5 scenarios (5%–40% off) with demand lift, units cleared, net profit |

**Output:** Five discount scenarios with the AI-highlighted "sweet spot" — the discount level where clearance volume outweighs margin loss.

### 6.4 Risk Profiling

**File:** `backend/app/models/risk_profiler.py` (310 lines)  
**Classes:** `RiskProfiler`, `RiskProfile` (Enum)

| Profile | Service Level | Strategy | When Used |
|:--------|:-------------|:---------|:----------|
| **Conservative** | 99% | Maximize availability, accept higher holding cost | Critical items, high-margin A-class |
| **Balanced** | 95% | Standard trade-off | Most products |
| **Aggressive** | 90% | Minimize inventory investment | Low-margin, C-class items |

**Scoring Factors:** Criticality (product priority), Demand Volatility (CV), Margin Impact, Shelf Life / Perishability.

### 6.5 Decision Optimizer

**File:** `backend/app/models/decision_optimizer.py` (344 lines)  
**Class:** `DecisionOptimizer`

Converts forecasts into prescriptive order decisions with full financial justification:

- Holding cost analysis
- Stockout cost projection
- Working capital impact
- Service level optimization
- ROI calculation for reorder decisions

### 6.6 Scenario Engine

**File:** `backend/app/models/scenario_engine.py` (316 lines)  
**Class:** `ScenarioEngine`

| Scenario Type | Parameters | Analysis |
|:-------------|:-----------|:---------|
| **Price Change** | New price, elasticity estimate | Revenue impact, volume change, margin effect |
| **Demand Shift** | Shift percentage, duration | Stock sufficiency, reorder timing, cost impact |
| **Supplier Switch** | New lead time, new cost, MOQ | Total cost comparison, transition risk, payback period |

### 6.7 Demand Sensing

**File:** `backend/app/models/demand_sensing.py` (351 lines)  
**Class:** `DemandSensing`

| Capability | Method | Output |
|:-----------|:-------|:-------|
| **Multi-Channel Aggregation** | Combines Online + Store + Wholesale + B2B | Unified demand signal |
| **Anomaly Detection** | Statistical outlier detection (z-score based) | Anomaly alerts with severity |
| **Trend Acceleration** | Rate-of-change analysis on demand slope | Acceleration/deceleration detection |
| **Promotional Impact** | Before/after comparison on promotion periods | Lift percentage, cannibalization estimate |

### 6.8 NLP & Explanation Layer

| File | Class | Purpose |
|:-----|:------|:--------|
| `ai_explainer.py` (546 lines) | `AIExplainer` | Generates plain-English explanations for every AI calculation — includes the math formula, data inputs with sources, natural language interpretation, and actionable recommendations |
| `financial_storyteller.py` (291 lines) | `FinancialStoryTeller` | Translates recommendations into executive language: revenue at risk, cash tied up, margin impact, payback period |
| `chatbot.py` (413 lines) | `InventoryChatbot` | Rule-based + analytics-backed Q&A — keyword intent detection, product lookup, stock snapshots, forecast summaries |
| `genai_client.py` (129 lines) | `GenAIClient` | Optional OpenAI wrapper (gpt-4.1-mini) — rewrites structured answers into executive-friendly language. No-op if not configured |

### 6.9 Alert System

**File:** `backend/app/models/ai_alert_system.py` (367 lines)  
**Class:** `AIAlertSystem`

- ML-based pattern detection (beyond simple threshold checks)
- Batch-optimized database queries
- Generates alerts for all stock tiers: Out of Stock, Low, Medium, High
- AI-predicted demand with 10% growth factor
- Urgency categorization: OUT_OF_STOCK / LOW / MEDIUM

### 6.10 Complete Model Inventory

| # | File | Lines | Class | Purpose |
|:--|:-----|:------|:------|:--------|
| 1 | `enhanced_forecaster.py` | 1,041 | `EnhancedDemandForecaster` | Primary multi-model forecasting engine |
| 2 | `demand_forecaster.py` | 923 | `DemandForecaster` | Base forecaster (ARIMA, Holt-Winters, LR, Prophet) |
| 3 | `multi_model_forecaster.py` | 364 | `MultiModelForecaster` | Model comparison (SES, DES, MA, WMA, LR) |
| 4 | `inventory_optimizer.py` | 673 | `InventoryOptimizer` | EOQ, ROP, Safety Stock, ABC Analysis |
| 5 | `product_segmentation.py` | 231 | `ProductSegmenter` | STABLE / SEASONAL / VOLATILE / INTERMITTENT |
| 6 | `ai_alert_system.py` | 367 | `AIAlertSystem` | ML-based stock alerts |
| 7 | `demand_sensing.py` | 351 | `DemandSensing` | Real-time multi-channel demand sensing |
| 8 | `decision_optimizer.py` | 344 | `DecisionOptimizer` | Prescriptive ordering decisions |
| 9 | `risk_profiler.py` | 310 | `RiskProfiler` | Conservative / Balanced / Aggressive profiles |
| 10 | `financial_storyteller.py` | 291 | `FinancialStoryTeller` | Executive-language financial narratives |
| 11 | `loss_calculator.py` | 309 | `LossCalculator` | Stockout revenue loss calculation |
| 12 | `markdown_optimizer.py` | 520 | `MarkdownOptimizer` | Clearance pricing optimization |
| 13 | `reorder_calculator.py` | 185 | `ReorderCalculator` | Reorder point + safety stock (1.5× multiplier) |
| 14 | `business_advisor.py` | 233 | `BusinessRecommendationEngine` | Actionable business recommendations |
| 15 | `ai_explainer.py` | 546 | `AIExplainer` | NLP explanation engine |
| 16 | `chatbot.py` | 413 | `InventoryChatbot` | Rule-based inventory Q&A |
| 17 | `genai_client.py` | 129 | `GenAIClient` | Optional OpenAI integration |
| 18 | `scenario_engine.py` | 316 | `ScenarioEngine` | What-if simulations |
| 19 | `exception_manager.py` | 309 | `ExceptionManager` | 80/20 alert noise reduction |
| 20 | `ml_metrics_tracker.py` | 158 | `MLMetricsTracker` | ML training metrics & feature importance |
| 21 | `data_generator.py` | 470 | `SmartDataGenerator` | Sample data (50 products, seasonal) |
| 22 | `poc_data_generator.py` | 783 | POC Generator | 500 products + 2 years sales |
| 23 | `scale_data_generator.py` | 232 | Scale Generator | 50,000 products generator |
| 24 | `validate_csv.py` | 99 | CSV Validator | Data quality validation |
| 25 | `integrations.py` | 81 | Integration Models | Webhook/API/CSV sync models |

**Total:** ~8,600 lines of AI/ML code across 25 functional model files.

---

## 7. API Reference — 124 Endpoints

### 7.1 System & Health (3 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| GET | `/` | API info and version |
| GET | `/api/system/health` | Platform readiness check (DB, email, scheduler status) |
| GET | `/api/system/metrics` | Operational metrics (notifications, failures, recipients count) |

### 7.2 Products (15 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| GET | `/api/products` | List products with stock levels and ML-based stockout risk |
| GET | `/api/products/dropdown` | Fast minimal list for dropdowns (id, name, sku) |
| GET | `/api/products/categories` | All distinct product categories |
| GET | `/api/products/paginated` | Paginated products with filters (category, stock_filter, search) |
| GET | `/api/products/summary` | Aggregate summary stats |
| GET | `/api/products/ordering-recommendations` | AI ordering recommendations |
| GET | `/api/products/{id}/forecast-comparison` | Side-by-side forecast model comparison |
| GET | `/api/products/{id}/intelligent-forecast` | Multi-model intelligent forecast with segmentation |
| GET | `/api/products/batch-intelligent-forecast` | Batch forecast for multiple products |
| GET | `/api/products/{id}/recommendations` | AI-powered business recommendations |
| GET | `/api/products/{id}/shadow-forecast` | Shadow forecast comparison |
| POST | `/api/products/import` | Import products from CSV |
| POST | `/api/data/upload-new-products` | Upload new products CSV |
| POST | `/api/data/restock-inventory` | Preview restocking changes |
| POST | `/api/data/restock-inventory/confirm` | Confirm and apply restock |

### 7.3 Forecasting (4 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| POST | `/api/forecast/{product_id}` | Generate demand forecast (params: `forecast_days`) |
| GET | `/api/forecast/{product_id}` | Retrieve stored forecast |
| GET | `/api/forecasting/{id}/feature-importance` | Feature importance for forecast model |
| POST | `/api/analytics/backtest-forecasts` | Backtest forecast accuracy |

### 7.4 Optimization (2 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| POST | `/api/optimize/{product_id}` | Run inventory optimization (params: `service_level`) |
| GET | `/api/optimize` | Get optimization results for all products |

### 7.5 ML Model Management (3 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| GET | `/api/ml/training-metrics` | Training data split, feature importance, model params |
| GET | `/api/ml/testing-results` | Test metrics, cross-validation, confusion matrix |
| POST | `/api/ml/adjust-parameters` | Adjust model parameters (max_depth, n_estimators) |

### 7.6 Analytics & Dashboard (12 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| GET | `/api/analytics/dashboard-fast` | Fast dashboard (SQL aggregates, 60s cache) |
| GET | `/api/analytics/dashboard` | Full dashboard analytics (params: `period`) |
| GET | `/api/analytics/stockout-loss` | Calculate stockout revenue loss |
| GET | `/api/analytics/low-stock-risk` | Low stock risk analysis |
| GET | `/api/analytics/product-level-loss` | Per-product loss breakdown |
| GET | `/api/analytics/product-sales-trend/{id}` | Sales trend for a product |
| GET | `/api/analytics/ai-alerts` | AI-generated alerts |
| GET | `/api/analytics/out-of-stock-breakdown` | Out-of-stock product breakdown |
| GET | `/api/analytics/inventory-health` | Full inventory health assessment |
| GET | `/api/analytics/live-alerts` | Live AI alerts (params: `limit`) |
| POST | `/api/analytics/abc-profitability` | ABC profitability analysis |

### 7.7 Metric Drill-Downs (6 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| GET | `/api/metrics/products-detail` | Product detail metrics |
| GET | `/api/metrics/stockout-detail` | Stockout detail breakdown |
| GET | `/api/metrics/forecast-detail` | Forecast detail metrics |
| GET | `/api/metrics/sales-trend-detail` | Sales trend detail |
| GET | `/api/metrics/savings-detail` | Savings detail analysis |
| GET | `/api/metrics/products-detail-dynamic` | Dynamic detail with threshold params |

### 7.8 AI Explainer (5 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| GET | `/api/ai/explain/loss/{id}` | NLP explanation of stockout loss calculation |
| GET | `/api/ai/explain/reorder/{id}` | NLP explanation of reorder recommendation |
| GET | `/api/ai/explain/forecast/{id}` | NLP explanation of forecast methodology |
| GET | `/api/ai/explain/alerts` | NLP explanation of alert logic |
| GET | `/api/ai/models-info` | Full list of AI/ML models and algorithms used |

### 7.9 Decision & Risk (4 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| POST | `/api/decisions/prescriptive/{id}` | Prescriptive decision with financial justification |
| POST | `/api/risk/profile-sku/{id}` | Risk profile classification for a product |
| POST | `/api/risk/compare-service-levels/{id}` | Compare 90% vs 95% vs 99% service levels |
| POST | `/api/financial/decision-story/{id}` | Financial narrative for a decision |

### 7.10 Financial (2 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| GET | `/api/financial/memo/{id}` | Executive financial memo for a product |
| GET | `/api/financial/monthly-report` | Monthly financial report |

### 7.11 Scenarios (3 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| POST | `/api/scenarios/price-change` | Price change what-if simulation |
| POST | `/api/scenarios/demand-shift` | Demand shift simulation |
| POST | `/api/scenarios/supplier-switch` | Supplier switch impact analysis |

### 7.12 Demand Sensing (4 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| POST | `/api/demand/multi-channel` | Multi-channel demand aggregation |
| POST | `/api/demand/anomalies` | Demand anomaly detection |
| POST | `/api/demand/trend-acceleration` | Trend acceleration detection |
| POST | `/api/demand/promotional-impact` | Promotional impact tracking |

### 7.13 Markdown Optimization (2 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| GET | `/api/markdown/opportunities` | Find markdown/clearance opportunities |
| GET | `/api/markdown/analyze/{id}` | Analyze markdown strategy for specific product |

### 7.14 Data & Import (22 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| POST | `/api/data/upload` | Upload CSV (auto-detects products or sales) |
| POST | `/api/data/upload-sales-fast` | Fast bulk sales CSV upload |
| POST | `/api/data/import-from-api` | Import from external REST API |
| GET | `/api/data/external-api-templates` | Pre-built API templates (FakeStore, DummyJSON) |
| GET | `/api/data/import-history` | History of all data imports |
| GET | `/api/data/saved-files` | List saved raw JSON files |
| GET | `/api/data/saved-files/{name}` | Get specific saved file |
| POST | `/api/data/replay-import/{name}` | Replay a saved import |
| GET | `/api/data/import-manifest` | Import manifest |
| POST | `/api/data/generate-from-dummyjson` | Generate data from DummyJSON API |
| POST | `/api/data/json-ingest` | Universal JSON ingestion |
| GET | `/api/data/model-columns/{model}` | Expected columns for a model |
| GET | `/api/data/model-columns` | List all model column schemas |
| POST | `/api/data/prepare-for-model` | Prepare data for a specific ML model |
| POST | `/api/data/bulk-import` | Bulk import data |
| GET | `/api/data/enrich-forecast/{id}` | Enrich forecast with external signals |
| GET | `/api/data/generate-sample` | Generate sample dataset |
| POST | `/api/data/products/json` | Import products from JSON payload |
| POST | `/api/data/sales/json` | Import sales from JSON payload |
| POST | `/api/data/validate` | Validate data quality |
| GET | `/api/data/schema-info` | Database schema information |
| GET | `/api/data/database-stats` | Database statistics |

### 7.15 Alerts & Email (7 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| GET | `/api/alerts/threshold-check` | Check all threshold alerts |
| GET | `/api/alerts/email-preview` | Preview alert email |
| POST | `/api/alerts/custom-email` | Send custom alert email |
| POST | `/api/alerts/send-threshold-email` | Send threshold-triggered email |
| POST | `/api/alerts/generate-email` | Generate alert email content |
| POST | `/api/alerts/send-email` | Send email via SendGrid |
| GET | `/api/alerts/stock-notifications` | Get stock alert notifications |

### 7.16 External Signals (6 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| GET | `/api/signals/weather/{date}` | Weather signals for a date |
| GET | `/api/signals/holidays/{date}` | Holiday signals |
| GET | `/api/signals/payday/{date}` | Payday signals |
| GET | `/api/signals/weekend/{date}` | Weekend signals |
| GET | `/api/signals/trends` | Trend signals |
| GET | `/api/signals/combined/{date}` | All signals combined |

### 7.17 Settings & Admin (6 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| GET | `/api/settings/thresholds` | Get stock threshold configuration |
| POST | `/api/settings/thresholds` | Update stock thresholds |
| GET | `/api/settings/email-config` | Get email configuration |
| POST | `/api/settings/email-config` | Update email configuration |
| POST | `/api/admin/clear-all-data` | Clear all data from database |
| POST | `/api/onboarding/smart-upload` | Smart onboarding upload |

### 7.18 Integrations (8 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| POST | `/api/integrations/webhook/{id}` | Receive webhook from external system |
| POST | `/api/integrations/sync/{id}` | Trigger sync with external system |
| POST | `/api/integrations/config` | Create integration config |
| GET | `/api/integrations/config` | List all integration configs |
| GET | `/api/integrations/config/{id}` | Get specific integration config |
| PUT | `/api/integrations/config/{id}` | Update integration config |
| DELETE | `/api/integrations/config/{id}` | Delete integration config |
| GET | `/api/integrations/test/{id}` | Test integration connectivity |

### 7.19 Chat (2 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| POST | `/api/chat/query` | NLP inventory Q&A (returns answer + intent) |
| POST | `/api/chat/analyze` | GenAI analysis over a full chat transcript |

### 7.20 Cache & Misc (8 endpoints)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| GET | `/api/cache/stats` | Cache statistics |
| POST | `/api/cache/clear` | Clear all caches |
| POST | `/api/cache/clear/forecast` | Clear forecast cache |
| POST | `/api/cache/clear/analytics` | Clear analytics cache |
| GET | `/api/suppliers` | List all suppliers |
| POST | `/api/suppliers` | Create/update supplier |
| POST | `/api/generate-sample-data` | Generate sample data |
| GET | `/api/data-generator/summary` | Summary of generated data |

---

## 8. Frontend — React Application

### Application Structure

```
frontend/
├── index.html                 # Entry point
├── package.json               # Dependencies (React 18, Vite 5, Recharts)
├── vite.config.js             # Build configuration
└── src/
    ├── App.jsx                # Root component with routing
    ├── main.jsx               # React DOM mount
    ├── components/            # 18 reusable UI components
    ├── pages/                 # 13 page-level components
    ├── services/              # API client + caching layer
    └── styles/                # 6 CSS files
```

### Routing

| Route | Component | Description |
|:------|:----------|:------------|
| `/` | `Dashboard` | Main dashboard with KPI cards, Sales Trend chart, Inventory Alerts table |
| `/products` | `Products` | Product grid with stock-tier filter cards and AI Insight Modals |
| `/forecasting` | `Forecasting` | Demand forecasting with product selector, chart, and explanation |
| `/markdown` | `MarkdownOptimizerPage` | Markdown/clearance pricing optimizer |
| `/settings` | `Settings` | Application and email configuration |

### Key Components (18 files)

| Component | Purpose |
|:----------|:--------|
| `Navbar.jsx` | Top navigation bar with route links |
| `MetricCard.jsx` | KPI metric card with click-to-drill-down |
| `Modal.jsx` | Reusable modal wrapper |
| `ProductInsightModal.jsx` | Product AI insights — Executive Summary, KPIs, Suggestions |
| `StockoutDetail.jsx` | Stockout alert drill-down with summary cards and tables |
| `ProductsDetail.jsx` | Product metrics drill-down |
| `SalesTrendDetail.jsx` | Sales trend analysis with period/metric selectors |
| `ForecastChart.jsx` | Recharts-based forecast visualization (historical + predicted + confidence band) |
| `ForecastDetail.jsx` | Forecast detail modal |
| `SavingsDetail.jsx` | Cost savings analysis |
| `ChatbotWidget.jsx` | Floating chat widget for NLP Q&A |
| `EmailAlertModal.jsx` | Email alert configuration modal |
| `EmailSettingsTab.jsx` | Email settings form |
| `DataSourcesTab.jsx` | Data source management |
| `DataGenerator.jsx` | Sample data generation UI |
| `SampleDataCard.jsx` | Sample data display card |
| `SignalsEnrichmentComponent.jsx` | External signals enrichment UI |

### Pages (13 files)

| Page | Lines Purpose |
|:-----|:-------------|
| `Dashboard.jsx` | Main dashboard — 3 metric cards (Total Products, Stockout Alerts, Potential Savings), Sales Trend chart, Inventory Alerts table with AI suggestions, email/webhook integration |
| `Products.jsx` | Product grid — 4 stock-tier cards (Out of Stock, Low, Medium, High) as clickable filters, Ordering Recommendations, product rows with Insight Modal |
| `Forecasting.jsx` | Demand forecasting — product selector dropdown, Generate Forecast button, historical+predicted chart with confidence band, model info, plain-English explanation |
| `MarkdownOptimizerPage.jsx` | Markdown optimizer — product selector, 5 discount scenarios (5%–40%), demand lift, units cleared, net profit, AI-highlighted sweet spot |
| `Settings.jsx` | Configuration — stock thresholds, email settings, integration config |
| `Optimization.jsx` | Inventory optimization results |
| `Suppliers.jsx` | Supplier management |
| `RiskProfilerPage.jsx` | Risk profiling interface |
| `ScenarioPlaybook.jsx` | What-if scenario planning |
| `CEOActionCenter.jsx` | Executive action dashboard |
| `ApiIntegration.jsx` | External API integration management |
| `DataGenerator.jsx` | Data generation interface |
| `DataGeneratorPage.jsx` | Full data generator page |

### API Service Layer

**File:** `frontend/src/services/api.js` (285 lines)

- **Base URL:** `window.__API_BASE__` (injected at build time for Colab) or `http://localhost:8000/api`
- **Timeout:** 30 minutes (supports large CSV uploads)
- **17 Service Modules:**
  - `productService` — CRUD, paginated list, ordering recommendations
  - `forecastService` — Generate + retrieve forecasts
  - `intelligentForecastService` — Multi-model forecasts with caching
  - `optimizationService` — Run + retrieve optimizations
  - `analyticsService` — Dashboard, trends, loss, health
  - `riskService` — Risk profiles, service level comparison
  - `financialService` — Memos, reports, decision stories
  - `scenarioService` — What-if simulations
  - `chatService` — NLP Q&A
  - `dataService` — Upload, import, validate
  - `aiExplainerService` — NLP explanations
  - `onboardingService` — Smart upload
  - `thresholdService` — Stock threshold config
  - `jsonIngestionService` — JSON data import
  - `emailService` — Email alerts
  - `externalApiService` — External API imports
  - `settingsService` — App settings

### Client-Side Caching

**File:** `frontend/src/services/cacheService.js` (216 lines)

| Feature | Details |
|:--------|:--------|
| Storage | In-memory Map |
| TTL | 5 minutes (default) |
| Max Entries | 100 (LRU eviction) |
| Key Generation | Hash of endpoint + params |
| Invalidation | Pattern-based regex matching |
| API | `cachedApiCall(key, fetchFn, ttl, forceRefresh)` |

---

## 9. Data Pipeline

### Data Sources

| File | Size | Records | Description |
|:-----|:-----|:--------|:------------|
| `data/products_50k.csv` | 9.9 MB | 50,000 | Product master data with 36+ columns |
| `data/sales_dense.csv` | 57.1 MB | 2,010,766 | 2 years of sales history (~80% daily coverage) |

### Product Data Schema (CSV)

36 columns including: `sku`, `name`, `category`, `unit_price`, `unit_cost`, `current_stock`, `lead_time_days`, `reorder_point`, `safety_stock`, `average_daily_demand`, `supplier_id`, `min_order_qty`, `max_order_qty`, `order_frequency_days`, `seasonality_factor`, `demand_volatility`, `profit_margin`, `abc_classification`, `xyz_classification`, `last_order_date`, `last_sale_date`, `shelf_life_days`, `storage_cost_per_unit`, `stockout_cost_per_unit`, `target_service_level`, `product_priority`, `weight_kg`, `volume_m3`, `is_perishable`, `is_hazardous`, `economic_order_qty`, `reorder_quantity`, `inventory_turnover`, `weeks_of_supply`, `stock_status`

**12 Product Categories:** Electronics, Apparel, Food & Beverage, Health & Beauty, Home & Garden, Sports & Outdoors, Office Supplies, Automotive, Toys & Games, Pet Care, Personal Care, Tools & Hardware

### Sales Data Schema (CSV)

Columns: `product_id`, `date`, `quantity_sold`, `revenue`, `unit_price_at_sale`, `unit_cost_at_sale`, `profit_loss_amount`, `profit_margin_pct`, `discount_applied`, `transaction_type`, `promotion_id`, `sales_channel`, `customer_id`, `region`

### Data Generation Scripts

| Script | Output | Method |
|:-------|:-------|:-------|
| `backend/app/models/scale_data_generator.py` | 50K products | Adjective + Product + Variant naming pattern, 12 categories |
| `scripts/enhance_product_data.py` | Enhanced 50K products | Adds AI/ML columns (supplier, seasonality, classification, etc.) |
| `generate_dense_sales.py` | 2M+ sales | ~80% daily coverage with seasonal, weekday, and trend patterns |
| `scripts/generate_sales_data.py` | Sales data | 2 years with 30–70% daily coverage |

### Database Loading Pipeline

```
CSV Files → Pandas read_csv → Column Filtering → SQLite bulk insert
                                    │
                          Filter to match table schema
                          (drops CSV-only columns like
                           days_since_last_order)
                                    │
                              Chunk size: 5000 (products)
                                         10000 (sales)
                                    │
                              Create indexes
                              PRAGMA optimize
```

### Data Quality Validation

**File:** `backend/app/schemas/data_schemas.py` (731 lines)

- Field mapping with aliases for flexible CSV/JSON column names
- Required field validation (sku, name, category, unit_price, unit_cost, current_stock)
- Duplicate detection and null checking
- Auto-cleaning of malformed data
- Type coercion and range validation

---

## 10. Deployment — Google Colab

### One-Click Cloud Deployment

The system deploys entirely inside a Google Colab notebook with zero local installation:

**Notebook:** `AI_Inventory_Colab.ipynb` (7 cells)

| Step | Cell | What It Does | Time |
|:-----|:-----|:-------------|:-----|
| Config | Cell 2 | Set `REPO_URL`, optional API keys, PORT, TUNNEL | — |
| Step 1 | Cell 3 | Install Node.js 20, force-reinstall numpy, clone repo, pip install, npm install | ~2 min |
| Step 2 | Cell 4 | Build SQLite DB from CSVs (subprocess to avoid numpy cache) | ~30s |
| Step 3 | Cell 5 | Inject `window.__API_BASE__`, npm run build, write `colab_server.py` (SPA fallback) | ~60s |
| Step 4 | Cell 6 | Start uvicorn, get public IP, create localtunnel/cloudflared, display URLs | ~30s |

### Colab-Specific Architecture

The Colab deployment uses a **unified server** (`colab_server.py`) that:

1. Mounts the FastAPI app at `/api/*`
2. Serves the React production build at `/*`
3. Implements SPA fallback middleware (returns `index.html` for all non-API, non-static routes)
4. Removes the default `GET /` JSON endpoint from FastAPI

### Tunnel Options

| Tunnel | Command | URL Format |
|:-------|:--------|:-----------|
| localtunnel (default) | `lt --port 8000` | `https://xyz.loca.lt` |
| cloudflared (fallback) | `cloudflared tunnel --url localhost:8000` | `https://xyz.trycloudflare.com` |

### Colab Constraints

- **Session timeout:** ~90 minutes on free tier (re-run to restart)
- **Node.js:** Must install v20 LTS (Colab default is v12)
- **numpy:** Must force-reinstall `numpy<2.0.0` to avoid binary incompatibility with Colab's pre-installed version
- **DB loading:** Must run in subprocess to avoid Colab kernel's cached numpy C extensions

---

## 11. Integration Layer

### Email Notifications (SendGrid)

**File:** `backend/app/services/email_service_sendgrid.py` (549 lines)

| Feature | Details |
|:--------|:--------|
| Provider | SendGrid (100 emails/day free tier) |
| Recipient Management | DB-backed (`alert_recipients` table) |
| Notification Logging | All sends logged to `notification_logs` table |
| Deduplication | `alert_key` based, 2-hour window |
| Email Types | Threshold alerts, custom alerts, forecast summaries |

### Slack Integration

- Webhook-based POST to Slack incoming webhook URL
- Markdown-formatted messages
- Configurable via `SLACK_WEBHOOK_URL` environment variable

### Microsoft Teams Integration

- Webhook-based POST to Teams connector URL
- Adaptive Card format messages
- Configurable via `TEAMS_WEBHOOK_URL` environment variable

### External Data Import

- REST API ingestion from external systems
- Pre-built templates for FakeStore API, DummyJSON
- Raw JSON file caching for replay
- Universal JSON/CSV ingestion with auto-mapping

### Alert Scheduler

**File:** `backend/app/services/alert_scheduler.py`

- Background async task running on configurable interval (default 15 minutes)
- Checks all threshold conditions
- Dispatches alerts to all configured channels
- Deduplication prevents repeated notifications
- Starts/stops with FastAPI lifecycle

---

## 12. Performance & Caching

### Database Performance

| Optimization | Setting | Impact |
|:-------------|:--------|:-------|
| WAL Mode | `journal_mode=WAL` | Concurrent reads during writes |
| Page Size | `page_size=8192` | Optimal for SSD |
| Cache Size | `cache_size=-64000` | 64 MB in-memory cache |
| Memory-Mapped I/O | `mmap_size=268435456` | 256 MB mmap for fast reads |
| Temp Store | `temp_store=MEMORY` | In-RAM temp tables |
| Connection Pool | `pool_size=20, max_overflow=40` | Up to 60 concurrent connections |
| Synchronous | `synchronous=NORMAL` | Balanced durability vs speed |

### Server-Side Caching

| Cache | TTL | Purpose |
|:------|:----|:--------|
| Dashboard Fast | 60 seconds | SQL aggregate results |
| Forecast Cache | 5 minutes | Forecast results per product |
| Analytics Cache | 5 minutes | Analytics computations |

### Client-Side Caching

| Setting | Value | Purpose |
|:--------|:------|:--------|
| TTL | 5 minutes | Prevent redundant API calls |
| Max Entries | 100 | Memory limit with LRU eviction |
| Key Strategy | Endpoint + params hash | Unique cache keys |
| Invalidation | Pattern-based regex | Selective cache clearing |

### Query Optimizations

- **Batch-optimized alert queries** — AIAlertSystem uses demand-first strategy (finds products with recent sales first, then loads records)
- **Indexed lookups** — Indexes on all primary query columns (sku, name, category, date, product_id)
- **Paginated results** — Products endpoint supports `page` + `page_size` with SQL LIMIT/OFFSET
- **Historical window** — Dashboard queries limited to last 30 days to reduce scan size

---

## 13. Security & Configuration

### CORS Configuration

```python
allowed_origins = [
    "http://localhost:5173",   # Vite dev server
    "http://localhost:5174",   # Vite fallback
    "http://localhost:3000",   # CRA dev server
]
allowed_origin_regex = [
    r"https://.*\.ngrok.*\.app",         # ngrok tunnels
    r"https://.*\.loca\.lt",             # localtunnel
    r"https://.*\.trycloudflare\.com",   # cloudflared
]
```

### Environment Variables

| Variable | Required | Purpose |
|:---------|:---------|:--------|
| `SENDGRID_API_KEY` | Optional | Email delivery |
| `SENDGRID_FROM_EMAIL` | Optional | Sender address |
| `OPENAI_API_KEY` | Optional | GenAI explanations |
| `SLACK_WEBHOOK_URL` | Optional | Slack notifications |
| `TEAMS_WEBHOOK_URL` | Optional | Teams notifications |

### Data Validation

- Pydantic v2 schemas for all API inputs
- `DataMapper` class with field aliases for flexible data ingestion
- `validate_data_quality()` function checks for nulls, duplicates, type mismatches
- SQL injection prevention via SQLAlchemy ORM parameterized queries

---

## 14. Testing & Validation

### System Verification

**File:** `backend/verify_system.py`

- Database connectivity check
- Table existence and row count validation
- API endpoint health checks
- Email configuration validation

### Data Quality Checks

| Check | Tool | Purpose |
|:------|:-----|:--------|
| CSV validation | `backend/app/models/validate_csv.py` | Column presence, types, duplicates |
| Data quality | `check_data_quality.py` | Comprehensive data audit |
| DB columns | `fix_db_columns.py` | Schema migration validation |
| System status | `status.py` | Overall system health |

### ML Model Validation

| Metric | Endpoint | Details |
|:-------|:---------|:--------|
| Training Metrics | `GET /api/ml/training-metrics` | 80/20 train/test split, feature importance |
| Testing Results | `GET /api/ml/testing-results` | MAE, RMSE, MAPE, R² = 0.91, cross-validation |
| Backtest | `POST /api/analytics/backtest-forecasts` | Historical accuracy validation |
| Shadow Forecast | `GET /api/products/{id}/shadow-forecast` | Side-by-side model comparison |

### API Documentation

FastAPI auto-generates interactive API documentation:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 15. Appendix

### A. File Inventory

| Directory | Files | Total Lines | Purpose |
|:----------|:------|:------------|:--------|
| `backend/app/models/` | 27 | ~8,600 | AI/ML algorithms |
| `backend/app/api/` | 5 | ~8,500 | REST API endpoints |
| `backend/app/services/` | 5 | ~1,500 | Business services |
| `backend/app/database/` | 2 | ~300 | ORM models |
| `backend/app/schemas/` | 1 | ~730 | Data schemas |
| `frontend/src/components/` | 18 | ~3,500 | UI components |
| `frontend/src/pages/` | 13 | ~4,000 | Page components |
| `frontend/src/services/` | 2 | ~500 | API + cache |

### B. Dependencies Summary

**Backend (17 packages):**
fastapi, uvicorn, sqlalchemy, pandas, numpy, scikit-learn, statsmodels, python-multipart, pydantic, python-dateutil, scipy, openpyxl, openai, httpx, sendgrid, xgboost, prophet

**Frontend (5 packages):**
react, react-dom, react-router-dom, recharts, axios

### C. Running Locally

**Prerequisites:** Python 3.9+, Node.js 20+

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
python setup_database.py
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

**Access:**
- Frontend: `http://localhost:5173`
- API Docs: `http://localhost:8000/docs`

### D. Running in Google Colab

1. Open: [Colab Notebook](https://colab.research.google.com/github/vempalamohit-bot/AI-Powered-Inventory-Optimization-Demand-Forecasting/blob/main/AI_Inventory_Colab.ipynb)
2. Runtime → Run all
3. Wait ~5 minutes
4. Click the public URL displayed in the last cell
5. Paste the IP address on the tunnel page

### E. GitHub Repository

**URL:** [github.com/vempalamohit-bot/AI-Powered-Inventory-Optimization-Demand-Forecasting](https://github.com/vempalamohit-bot/AI-Powered-Inventory-Optimization-Demand-Forecasting)

**Structure:** 117 tracked files, ~35,000+ lines of code, 2 large data files (67 MB total)

---

*Document generated February 2026 — Miracle Software Systems*
