# AI-Powered Inventory Optimization & Demand Forecasting

A comprehensive AI-driven system that leverages machine learning to predict product demand, optimize inventory levels, and reduce costs through intelligent stock management.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/vempalamohit-bot/AI-Powered-Inventory-Optimization-Demand-Forecasting/blob/main/AI_Inventory_Colab.ipynb)
![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![React](https://img.shields.io/badge/React-18.2+-61dafb.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## ☁️ Run Instantly in Google Colab (No Installation Required)

> **Zero setup — runs entirely in the cloud.**

### How to use

1. **Click the "Open in Colab" badge** above (or [click here](https://colab.research.google.com/github/vempalamohit-bot/AI-Powered-Inventory-Optimization-Demand-Forecasting/blob/main/AI_Inventory_Colab.ipynb))  
2. **Update the `REPO_URL`** in Cell 2 with your GitHub repo URL  
3. **Go to Runtime → Run all** (or press `Ctrl + F9`)  
4. **Wait ~5 minutes** for installation to complete  
5. The **final cell** will display a **public URL** and an **IP address (password)**  
6. **Click the URL**, paste the IP address on the tunnel page, and hit Submit  
7. **The full application loads** — Dashboard, Products, Forecasting, Markdown Optimizer 🎉  

### What happens under the hood

| Step | What it does | Time |
|:----:|:-------------|:----:|
| 1 | Installs Python packages, Node.js, and clones the repo | ~2 min |
| 2 | Builds SQLite database (50K products + 2M sales records) | ~30s |
| 3 | Builds React frontend and creates a unified server | ~60s |
| 4 | Starts FastAPI + React on one port, opens a public tunnel | ~30s |

### Architecture in Colab

```
Google Colab Runtime
├── FastAPI backend (50+ API endpoints)      ← /api/*
├── React frontend (production build)        ← /*
├── SQLite database (50K products, 2M sales) ← backend/inventory.db
└── Public tunnel (localtunnel / cloudflared) ← https://xyz.loca.lt
         ↕
Your Browser → Full AI Dashboard
```

> **Session timeout:** Colab free tier disconnects after ~90 min. Just click **Runtime → Run all** again to restart.

---

## 🌟 Features

### Phase 1: Forecasting & Optimization (Foundation)

#### 📈 Demand Forecasting
- **Time Series Analysis**: Uses exponential smoothing to capture trends and seasonal patterns
- **Feature Engineering**: Incorporates day-of-week, seasonality, and temporal features
- **Ensemble Predictions**: Combines multiple ML models for improved accuracy
- **Confidence Intervals**: Provides 95% confidence bands for uncertainty quantification

#### 📦 Inventory Optimization
- **Economic Order Quantity (EOQ)**: Calculates optimal order quantities
- **Reorder Point Calculation**: Determines when to reorder based on lead time and demand
- **Safety Stock Optimization**: Protects against demand variability
- **ABC Analysis**: Classifies inventory by revenue contribution (now with profitability dimension)
- **Stockout Risk Assessment**: Identifies products at risk of running out

#### 🔄 Supply Chain Intelligence
- **Supplier Scoring**: Multi-dimensional supplier evaluation (delivery, quality, lead time, cost)
- **Scenario Modeling**: Price/demand/supplier what-if analysis
- **Demand Sensing**: Multi-channel aggregation with anomaly detection
- **Dead Stock Detection**: Identifies slow-moving inventory for clearance

### Phase 2: Decision-Centric AI (Executive Ready) ⭐ NEW

#### 🎯 Prescriptive Recommendations
- **Decision Engine**: "ORDER NOW" vs "WAIT" with financial justification
- **Cost-Benefit Analysis**: Shows stockout risk vs holding cost trade-offs
- **ROI Quantification**: Every decision includes expected return on investment
- **Approval Workflow**: Auto-approve low-risk, route high-risk to finance/executives

#### 📊 Risk-Adjusted Planning
- **Product Risk Classification**: Conservative/Balanced/Aggressive profiles
- **Service Level Matrices**: CFO-friendly cost vs service level trade-offs
- **Working Capital Impact**: Shows exact cash freed by optimization
- **Risk Appetite Selection**: Let executives choose their risk tolerance

#### 💰 Financial Storytelling
- **Executive Narratives**: Every recommendation translated to financial language
- **5-Part Story**: Revenue at risk → working capital → carrying cost → net impact → dashboard
- **Board-Ready Output**: Email-friendly memos with ROI and payback period
- **Portfolio Aggregation**: Total financial impact across all products

### Phase 3: Enterprise Alert & Notification System 🚨 NEW

#### 📧 Multi-Channel Notifications
- **Email Integration**: SendGrid-powered delivery (100 free emails/day)
- **Slack Webhooks**: Push critical alerts to team channels
- **Microsoft Teams**: Enterprise-ready webhook integration
- **Centralized Configuration**: Environment-driven settings with `.env` support

#### ⚙️ Alert Scheduler
- **Background Processing**: Async scheduler checks alerts automatically
- **Deduplication**: Prevents alert spam with configurable time windows
- **Audit Logging**: Database-backed notification history for compliance
- **Health Monitoring**: System health and metrics endpoints

#### 🔧 Configuration Management
- **Environment-Driven**: All settings via environment variables
- **Dynamic Recipients**: Database-managed alert recipient list
- **Feature Flags**: Enable/disable scheduler via config
- **Easy Setup**: Copy `.env.example` to `.env` and configure

#### 📊 Analytics Dashboard
- **Real-time Metrics**: Track key inventory KPIs
- **Visual Analytics**: Interactive charts and graphs
- **Cost Savings Tracking**: Monitor estimated annual savings
- **Alert System**: Get notified of stockout risks

#### 🔄 Data Integration
- **CSV Upload**: Import historical sales data
- **Product Catalog**: Manage product information
- **Sales History**: Track historical performance

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Node.js 16 or higher
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On macOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables (copy `.env.example` to `.env`):
```bash
# Required for email notifications
SENDGRID_API_KEY=your_api_key_here  # Get free at https://signup.sendgrid.com
FROM_EMAIL=noreply@example.com

# Alert recipients (comma-separated)
ALERT_RECIPIENTS=admin@example.com,inventory@example.com

# Optional: Multi-channel notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/YOUR/WEBHOOK/URL

# Alert scheduler configuration
ALERT_SCHEDULER_ENABLED=true
ALERT_CHECK_INTERVAL_SECONDS=3600
ALERT_DEDUPLICATION_MINUTES=60
LOG_NOTIFICATIONS=true
```

5. Start the backend server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The application will open at `http://localhost:5173`

## 📖 Usage Guide

### 1. Upload Sales Data

1. Navigate to the **Products** page
2. Click **Upload Sales Data**
3. Select your CSV file with the following columns:
   - `date`: Date of sale (YYYY-MM-DD)
   - `sku`: Product SKU
   - `product_name`: Product name
   - `category`: Product category
   - `quantity_sold`: Quantity sold
   - `revenue`: Revenue (optional)
   - `unit_cost`: Cost per unit
   - `unit_price`: Selling price
   - `current_stock`: Current inventory level
   - `lead_time_days`: Supplier lead time

Sample data is provided in `data/sample_data.csv`

### 2. Generate Demand Forecasts

1. Go to the **Forecasting** page
2. Select a product from the dropdown
3. Choose forecast horizon (7, 14, 30, or 90 days)
4. Click **Generate Forecast**
5. View the interactive chart with predictions and confidence intervals

### 3. Optimize Inventory

1. Navigate to the **Optimization** page
2. View recommendations for all products
3. Check which products need reordering
4. Review EOQ, safety stock, and reorder points
5. See estimated cost savings

### 4. Monitor Dashboard

1. Visit the **Dashboard** page
2. View key metrics:
   - Total products
   - Stockout alerts
   - Forecast accuracy
   - Estimated annual savings
3. Analyze sales trends
4. Identify top-performing products

## 🏗️ Architecture

### Backend (Python/FastAPI)

```
backend/
├── app/
│   ├── models/
│   │   ├── demand_forecaster.py    # ML forecasting engine
│   │   └── inventory_optimizer.py  # Optimization algorithms
│   ├── api/
│   │   └── routes.py               # REST API endpoints
│   ├── services/
│   │   └── analytics_service.py    # Business logic
│   └── database/
│       ├── __init__.py             # DB connection
│       └── models.py               # SQLAlchemy models
├── requirements.txt
└── main.py                         # Application entry point
```

### Frontend (React/Vite)

```
frontend/
├── src/
│   ├── components/
│   │   ├── MetricCard.jsx          # Reusable metric display
│   │   ├── ForecastChart.jsx       # Chart component
│   │   └── Navbar.jsx              # Navigation
│   ├── pages/
│   │   ├── Dashboard.jsx           # Main dashboard
│   │   ├── Products.jsx            # Product management
│   │   ├── Forecasting.jsx         # Demand forecasting
│   │   └── Optimization.jsx        # Inventory optimization
│   ├── services/
│   │   └── api.js                  # API client
│   └── styles/
│       └── index.css               # Design system
├── package.json
└── index.html
```

## � Documentation

### Complete Feature Guides
- **Phase 1 Summary**: [ENHANCEMENTS_SUMMARY.md](ENHANCEMENTS_SUMMARY.md) - Supplier optimization, scenario engine, demand sensing
- **Phase 2 Executive Brief**: [PHASE2_EXECUTIVE_SUMMARY.md](PHASE2_EXECUTIVE_SUMMARY.md) - Decision-centric AI, risk profiles, financial storytelling
- **Phase 2 Quick Start**: [PHASE2_QUICK_START.md](PHASE2_QUICK_START.md) - API examples and financial output explanation
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md) - System design and technical details
- **Phase 1 Quick Start**: [QUICK_START_NEW_FEATURES.md](QUICK_START_NEW_FEATURES.md) - Phase 1 feature guide

## 🔌 API Endpoints

### Phase 1: Forecasting & Optimization
- `GET /api/products` - List all products with stock levels
- `POST /api/data/upload` - Upload sales data CSV
- `POST /api/forecast/{product_id}` - Generate demand forecast
- `GET /api/forecast/{product_id}` - Get existing forecasts
- `POST /api/optimize/{product_id}` - Generate inventory recommendations
- `GET /api/optimize` - Get all recommendations
- `GET /api/analytics/dashboard` - Get dashboard metrics

### Phase 1: Supplier, Scenarios, Demand Sensing
- `POST /api/suppliers/evaluate` - Score supplier performance
- `POST /api/suppliers/optimize-multi` - Multi-supplier order allocation
- `POST /api/scenarios/price-change` - Simulate price changes
- `POST /api/demand/anomalies` - Detect unusual demand patterns
- `POST /api/analytics/abc-profitability` - Advanced ABC analysis

### Phase 2: Decision-Centric AI (NEW) ⭐
- **`POST /api/decisions/prescriptive/{product_id}`** - Get ORDER/WAIT decision with financial ROI
- **`POST /api/risk/profile-sku/{product_id}`** - Classify product into Conservative/Balanced/Aggressive
- **`POST /api/risk/compare-service-levels/{product_id}`** - Show CFO cost vs service level trade-offs
- **`POST /api/financial/decision-story/{product_id}`** - Get financial narrative for any decision
- **`GET /api/financial/memo/{product_id}`** - Generate executive memo with recommendation

### Phase 3: System Monitoring & Notifications (NEW) 🚨
- **`GET /api/system/health`** - System health check with component status
- **`GET /api/system/metrics`** - System metrics (DB connections, alerts, notifications)
- **`GET /api/settings/email-config`** - Get current email/notification configuration
- **`PUT /api/settings/email-config`** - Update email notification settings
- **`POST /api/alerts/send-test`** - Send test notification to verify setup
- **`GET /api/alerts/recipients`** - List active alert recipients
- **`POST /api/alerts/recipients`** - Add new alert recipient
- **`GET /api/alerts/logs`** - Notification audit logs with filtering

**Example System Health Request**:
```bash
curl -X GET "http://localhost:8000/api/system/health"
```

**Example Health Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "components": {
    "database": "connected",
    "scheduler": "running",
    "email_service": "configured"
  }
}
```

**Example Phase 2 Request**:
```bash
curl -X POST "http://localhost:8000/api/decisions/prescriptive/1?target_service_level=0.95"
```

**Example Response**:
```json
{
  "decision": "ORDER NOW",
  "recommended_qty": 500,
  "financial_justification": {
    "cost_to_order": 5000,
    "cost_of_stockout_risk": 42000,
    "net_benefit": 37000,
    "roi_percent": 740
  },
  "approval_level": "auto_approve"
}
```

All endpoints documented in Swagger: `http://localhost:8000/docs`

## 🎨 Design System

The application features a modern, premium design with:

- **Dark Mode**: Easy on the eyes with vibrant accents
- **Glassmorphism**: Frosted glass effects for depth
- **Smooth Animations**: Micro-interactions for enhanced UX
- **Responsive Layout**: Works on all screen sizes
- **Custom Color Palette**: Purple/blue gradients with high contrast
- **Typography**: Inter font family for readability

## 🧮 Algorithms

### Demand Forecasting
- **Exponential Smoothing**: Holt-Winters method for trend and seasonality
- **Linear Regression**: Feature-based predictions
- **Ensemble Method**: Weighted combination of models

### Inventory Optimization
- **EOQ Formula**: `sqrt((2 * D * S) / H)`
- **Reorder Point**: `(Avg Daily Demand × Lead Time) + Safety Stock`
- **Safety Stock**: `Z-score × σ × sqrt(Lead Time)`

## 🔮 Future Enhancements

- [ ] Multi-location inventory management
- [ ] Supplier integration and automated ordering
- [ ] Advanced ML models (LSTM, Prophet)
- [ ] Mobile app
- [ ] Real-time data synchronization
- [ ] Custom reporting and exports
- [ ] Role-based access control
- [ ] Integration with ERP systems

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For questions or support, please open an issue on GitHub.

---

**Built with ❤️ using FastAPI, React, and Machine Learning**
