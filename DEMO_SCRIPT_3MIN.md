# 3-Minute Technical Demo — AI/ML Inventory Optimization Engine

**Start on:** Dashboard (`/`)

---

### [0:00 – 0:15] INTRO

*Dashboard visible*

> "I'm Mohit Rao, Data and AI Engineering. This is an AI-powered inventory optimization engine — fifty thousand products, two million sales records. It uses multiple ML models for demand forecasting, an EOQ optimizer for reorder quantities, and a price elasticity model for markdown pricing. The AI classifies each product's demand pattern and selects the right model automatically."

---

### [0:15 – 0:50] DASHBOARD — SUMMARY CARDS

**→ Point to Total Products**

> "Total Products — full catalog. Click it — the system segments stock into four tiers. The Configure Thresholds button recalculates all fifty thousand products in real time against new boundaries."

**→ Click Stockout Alerts card**

> "Stockout Alerts — this is the reorder engine output. The AI computes days-to-stockout for every product by dividing current stock by the rolling-average sales velocity. Reorder quantities come from an Economic Order Quantity model that minimizes total ordering plus holding cost. Safety stock is layered on top — computed from demand variability and supplier lead time. Higher variability, bigger buffer."

*(close modal)*

**→ Click Annual Savings card**

> "Annual Savings — the delta between traditional ordering cost and EOQ-optimized ordering across the entire catalog. That's the AI-driven cost reduction."

---

### [0:50 – 1:15] SALES TREND & ALERTS

**→ Point to Sales Trend chart**

> "Sales Trend — the raw time series data that feeds all our ML models. Switchable between daily, weekly, monthly, yearly — across quantity, revenue, profit, or loss. Filterable to any single product."

**→ Scroll to Inventory Alerts table**

> "Inventory Alerts — each row is AI-generated. Current stock, days until stockout, order-by date computed from lead time, daily revenue at risk, and an AI suggestion per product. These suggestions are not rules — they're computed from that product's specific demand velocity, lead time, and variability through the EOQ and safety stock models. Summary bar totals daily revenue at risk. Email alerts dispatch via SendGrid on threshold breach."

---

### [1:15 – 1:50] PRODUCTS TAB

**→ Click Products in navbar**

> "Products page — the AI segmentation engine. Before any forecast runs, the system classifies every product into six demand segments — Stable Flat, Stable Trending, Seasonal Stable, Seasonal Volatile, Volatile, or Intermittent. It computes three ML features — coefficient of variation for demand variability, zero-sales percentage for sparse demand detection, and seasonality strength via seasonal decomposition. This segmentation drives which forecasting model gets selected downstream."

**→ Click Out of Stock card**

> "Out of Stock shows the AI-computed ordering recommendations — EOQ quantities adjusted by the product's demand classification."

**→ Click a product row**

> "Product detail — the full AI output. Reorder point, EOQ quantity, demand metrics, and prioritized suggestions ranked by financial impact."

---

### [1:50 – 2:25] FORECASTING TAB

**→ Click Forecasting, select product, Generate Forecast**

> "The core ML pipeline. Four time series models — Holt-Winters for exponential smoothing with trend and seasonality, SARIMA for autocorrelated seasonal patterns, Seasonal Naive as a baseline for intermittent demand, and Trend-Seasonal Decomposition. Plus two optional ML models — XGBoost gradient-boosted trees trained on lag features and rolling averages, and Facebook Prophet for strong seasonal cycles."

> "The AI selects models based on the product's segment. Seasonal-stable tries Holt-Winters first, then SARIMA. Volatile tries Decomposition first. Intermittent starts with Seasonal Naive. First successful model wins."

*(point to chart)*

> "Solid line — actual sales. Dashed line — AI prediction. Shaded band — confidence interval from the model's residual distribution. Wider band, less certainty."

---

### [2:25 – 2:50] OPTIMIZATION TAB

**→ Click Optimization, select product**

> "Markdown optimizer — two ML models. Linear regression on sales velocity to detect demand trend direction. Then price elasticity via log-log regression — how sensitive is demand to price changes. High elasticity means discounts work, low means they won't."

> "Five scenarios simulated — five to forty percent off. Each computes demand lift, units cleared, revenue, and net profit. The highlighted row is the AI's optimal discount — the break-even point where extra volume stops compensating for margin loss."

---

### [2:50 – 3:00] CLOSE

> "AI segmentation into six classes driving automatic model selection. EOQ reorder optimization. Price elasticity markdown pricing. Fifty thousand products, two million records, all automated. Questions?"

---

### TIMING GUIDE

| Section              | Duration     | Words |
|:---------------------|:-------------|:------|
| Intro                | 0:00 – 0:15 | ~50   |
| Dashboard Cards      | 0:15 – 0:50 | ~95   |
| Sales Trend & Alerts | 0:50 – 1:15 | ~85   |
| Products Tab         | 1:15 – 1:50 | ~95   |
| Forecasting Tab      | 1:50 – 2:25 | ~105  |
| Optimization Tab     | 2:25 – 2:50 | ~70   |
| Close                | 2:50 – 3:00 | ~25   |
| **Total**            | **3:00**     | **~525** |

*Pace: ~175 wpm (brisk live demo). Tight but deliverable.*

---

### FORMULAS & ALGORITHMS REFERENCE

| Algorithm | Formula / Method | Where Shown | Purpose |
|:----------|:----------------|:------------|:--------|
| EOQ | Q* = √(2DS/H) | Dashboard, Products | Optimal order quantity minimizing total inventory cost |
| Safety Stock | SS = z × σ_d × √L | Dashboard AI suggestions | Buffer for demand uncertainty at 95% service level |
| Days-to-Stockout | DTS = stock / d̄ | Dashboard, Stockout Alerts | Time until zero inventory |
| Revenue-at-Risk | Σ P(stockout) × daily_rev | Dashboard summary bar | Aggregate opportunity cost of inaction |
| CV | σ/μ | Products segmenter | Demand variability → Stable/Volatile classification |
| Zero-Sales % | weeks_zero / total | Products segmenter | Intermittent demand detector |
| Seasonality Strength | Var(S) / Var(Y-T) | Products segmenter (STL) | Seasonal signal strength for model routing |
| Holt-Winters | α, β, γ recurrence | Forecasting (Stable) | Exponential smoothing with trend + seasonality |
| SARIMA | (p,d,q)(P,D,Q)_m MLE | Forecasting (Seasonal) | Autocorrelated seasonal modeling |
| XGBoost | Boosted trees + lag features | Forecasting (Volatile) | Non-linear demand with engineered features |
| Prophet | g(t) + s(t) + h(t) + ε | Forecasting (Seasonal) | Fourier seasonality + piecewise growth |
| Seasonal Naive | ŷ_t = y_{t-m} | Forecasting (Intermittent) | Same-period-last-cycle baseline |
| Weighted Ensemble | Σ(w_i × ŷ_i), w ∝ 1/MAPE | Forecasting (best overall) | Inverse-MAPE weighted combination |
| Confidence Interval | ŷ ± 1.96 × σ_residual | Forecast chart band | 95% prediction uncertainty |
| Price Elasticity | ε via ln(Q) = α + ε·ln(P) | Markdown Optimizer | Log-log regression for demand sensitivity |
| Optimal Markdown | argmax [rev − margin_loss] | Markdown highlighted row | Break-even discount level |
