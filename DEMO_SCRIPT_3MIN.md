# 3-Minute Technical Demo — AI Inventory Optimization

**Start on:** Dashboard (`/`)

---

### [0:00 – 0:12] INTRO

*Dashboard visible*

> "Hi, I'm Mohit Rao from Data and AI Engineering. This is an AI-powered inventory optimization engine — fifty thousand SKUs, two million sales records, FastAPI backend on SQLite WAL, React frontend. It runs seven ML models for demand forecasting, an EOQ optimizer with newsvendor service-level tuning for reorder quantities, and a log-log price elasticity model for markdown pricing. Every product gets auto-classified into a demand segment that drives which model runs."

---

### [0:12 – 0:45] DASHBOARD

**→ Point to Total Products → click it**

> "Fifty thousand products classified into four stock tiers. These thresholds are configurable — click Configure and it reclassifies all fifty thousand in real time."

**→ Click Stockout Alerts card**

> "This is the reorder engine. Days-to-stockout is just current stock divided by rolling average daily demand. The optimal order quantity uses EOQ — square root of two times annual demand times ordering cost, divided by holding cost — where holding cost defaults to 25% of unit cost. Safety stock sits on top — z-score of 1.65 for 95% service level, times demand standard deviation, times square root of lead time. If we have stockout cost data, it switches to a newsvendor critical ratio — undersale cost divided by undersale plus oversale — clamped between 85% and 99% service level."

*(close modal)*

**→ Click Annual Savings**

> "This is the cost delta — EOQ-optimized ordering versus naive ordering across the full catalog. It factors in holding cost, ordering cost, and expected stockout cost using the standard normal loss function."

---

### [0:45 – 1:05] SALES TREND & ALERTS TABLE

**→ Point to Sales Trend chart**

> "Raw time series data feeding all our models — daily, weekly, monthly, yearly granularity, across quantity, revenue, profit, or loss. Filterable to any single product."

**→ Scroll to Inventory Alerts table**

> "Every row is computed, not rule-based. Buffer days equal days-to-stockout minus supplier lead time. Loss per day comes from linear trend extrapolation — numpy polyfit degree one on the trailing 30-day window — times unit margin. The order-by date subtracts lead time from projected stockout. Email alerts dispatch via SendGrid when buffer breaches threshold."

---

### [1:05 – 1:35] PRODUCTS — AI SEGMENTATION

**→ Click Products**

> "Before any forecast runs, every product gets classified into one of seven demand segments using three engineered features. First — coefficient of variation, sigma over mu. CV under 0.4 is stable, above 0.6 is volatile. Second — zero-sales percentage. Above 25% flags intermittent demand. Third — seasonality strength via additive STL decomposition, testing periods at 7, 14, 30, and 90 days — it's seasonal variance divided by seasonal-plus-residual variance. Above 0.3 means seasonal. Trend direction comes from linear regression on the time index."

> "Decision logic runs in priority order — Intermittent first, then Seasonal-Stable, Seasonal-Volatile, Volatile, Stable-Trending, Stable-Flat, then Moderate as default. Each segment maps to a specific model priority list."

**→ Click a product row**

> "Full AI output — reorder point, EOQ quantity, safety stock, demand characteristics, and prioritized suggestions ranked by financial impact."

---

### [1:35 – 2:15] FORECASTING — ML PIPELINE

**→ Click Forecasting → select product → Generate Forecast**

> "The core ML pipeline. Sales data is aggregated to weekly internally to avoid zero-inflation from sparse daily sales — if under 50% of weeks have sales, it drops to biweekly. Seven models. Holt-Winters tries five configurations — additive, multiplicative, damped, linear, monthly — picks by AIC. SARIMA runs order 1-1-1 times 1-0-1 with seasonal period 13 or 4 weeks. Seasonal Naive repeats the last full cycle. Decomposition does additive STL plus linear regression on trend. XGBoost — 100 estimators, max depth 4, features are week, month, quarter, lags at 1, 2, 4, 8, 13 weeks, plus rolling mean and standard deviation at windows 4, 8, 13. Prophet adds weekly and yearly seasonality, additive mode."

> "Model selection is segment-driven. Seasonal-stable tries SARIMA first, then Holt-Winters. Volatile starts with XGBoost. Intermittent starts with Seasonal Naive. First successful model wins. If forecast CV is under 12%, it overlays the STL seasonal pattern for enrichment."

*(point to chart)*

> "Purple area — actual sales. Teal dashed — AI prediction. Shaded band is 95% confidence — 1.96 times residual standard deviation, widening 2 to 5 percent per forecast step."

---

### [2:15 – 2:50] OPTIMIZATION — MARKDOWN PRICING

**→ Click Optimization → select product**

> "Markdown optimizer using category-specific price elasticity — Electronics at negative 1.8, Baby Products at negative 0.9 — adjusted by margin bracket. Optimal discount formula is absolute elasticity minus one, over two times absolute elasticity, constrained between 5% and 40% max."

> "Five scenarios — 10% through 30% off over a 14-day window. Each computes demand lift, units cleared, revenue, and net profit. Best scenario selected by maximum net profit — that's the highlighted row. Urgency score is a 0-to-100 composite — inventory days factor up to 40 points, velocity inverse up to 30, elasticity up to 20, margin factor up to 10."

---

### [2:50 – 3:00] CLOSE

> "So — seven ML models with automatic segment-driven selection, EOQ plus newsvendor reorder optimization, category-specific price elasticity for markdown pricing. Fifty thousand products, two million records, fully automated. This is an excellent applied AI project for real-world inventory optimization. Happy to take questions."

---

### TIMING GUIDE

| Section              | Duration     | Words |
|:---------------------|:-------------|:------|
| Intro                | 0:00 – 0:12 | ~45   |
| Dashboard            | 0:12 – 0:45 | ~105  |
| Sales Trend & Alerts | 0:45 – 1:05 | ~80   |
| Products Segmentation| 1:05 – 1:35 | ~90   |
| Forecasting          | 1:35 – 2:15 | ~120  |
| Optimization         | 2:15 – 2:50 | ~100  |
| Close                | 2:50 – 3:00 | ~35   |
| **Total**            | **3:00**     | **~575** |

*Pace: ~190 wpm (conversational-fast). Very comfortable for live delivery.*

---

### IF YOU'RE ASKED TECHNICAL FOLLOW-UPS

| Question | Quick Answer |
|:---------|:-------------|
| "What's the EOQ formula?" | "Square root of 2 times annual demand times ordering cost, divided by holding cost." |
| "How does safety stock work?" | "Z-score times demand standard deviation times square root of lead time. We use 1.65 for 95% service level." |
| "What features does XGBoost use?" | "Week number, month, quarter, lags at 1, 2, 4, 8, and 13 weeks, plus rolling mean and standard deviation." |
| "How do you measure seasonality?" | "STL decomposition — seasonal variance divided by seasonal-plus-residual variance. Above 0.3 is seasonal." |
| "What's the price elasticity model?" | "Log-log regression — log of quantity against log of price. Different base elasticity per product category." |
| "How is optimal discount calculated?" | "Elasticity minus one, divided by two times elasticity — then constrained to max 40% or 80% of margin." |
| "What confidence interval?" | "95% — that's 1.96 times the residual standard deviation, widening slightly each forecast step." |
| "How many models?" | "Seven — Holt-Winters, SARIMA, Seasonal Naive, Decomposition, XGBoost, Prophet, and ensemble." |

---

### FORMULAS CHEAT SHEET (for your reference, not for speaking)

| Algorithm | Formula |
|:----------|:--------|
| EOQ | Q* = √(2DS/H) |
| Safety Stock | SS = z × σ_d × √L |
| Days-to-Stockout | DTS = stock / avg_daily_demand |
| Reorder Point | ROP = (avg_demand × lead_time) + safety_stock |
| CV | σ / μ |
| Seasonality | Var(seasonal) / Var(seasonal + residual) |
| Confidence Interval | forecast ± 1.96 × σ_residual |
| Price Elasticity | ln(Q) = α + ε·ln(P) |
| Optimal Discount | d* = (|ε| − 1) / (2|ε|) |
