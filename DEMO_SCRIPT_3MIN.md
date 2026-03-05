# 3-Minute Demo Script: AI-Powered Inventory Optimization

**Start on:** Intro slide or blank screen, then switch to Dashboard
**Tone:** Confident, client-focused, and value-driven.

---

### [0:00 – 0:20] INTRODUCTION: THE BUSINESS PROBLEM

*Camera on you, screen not yet visible*

> "Good morning. I'm Mohit Rao, from Data and AI Engineering. Every retail and distribution business faces a critical challenge: how to manage inventory effectively. Overstock ties up working capital, while stockouts mean lost sales. Today, I'll demonstrate how this platform uses AI and machine learning to solve this, turning your historical data into a competitive advantage."

*Switch screen to Dashboard*

---

### [0:20 – 0:40] THE DATA: YOUR UNTAPPED ASSET

> "The models are fueled by the data you already have. We start with your product catalog — in this case, a sample of 50,000 items across various categories. We then analyze the sales history, processing over two million transactions to understand the unique demand pattern of every single product. This data is the foundation for intelligent decision-making."

---

### [0:40 – 1:05] DASHBOARD: YOUR AI-POWERED COMMAND CENTER

*Point to tiles and chart*

> "This dashboard is your command center, and everything on it is driven by ML models. These tiles provide a real-time, executive summary of your inventory health — what's well-stocked, what's running low, and what needs immediate attention. This isn't a static report; it's a dynamic view, constantly updated by the AI."

**→ Click Stockout Alerts card**

> "Here, the models have identified the most urgent risks. For each high-priority product, the system calculates the days until stockout and recommends the precise quantity to order, ensuring you can act before revenue is impacted."

*(close modal)*

---

### [1:05 – 1:30] ALERTS: FROM INSIGHT TO ACTION

**→ Scroll to Inventory Alerts table**

> "The platform automates inventory monitoring at the most granular level. For each product, the AI generates specific, actionable alerts. You can see the current stock, the revenue at risk, and a clear reorder recommendation tailored to that product's demand and lead time."

**→ Point to email notification icon/feature**

> "And this intelligence isn't confined to a dashboard. When a product's stock hits a critical level, an automated email is sent directly to the responsible team or individual. This ensures the right people are empowered to take action at the right time."

---

### [1:30 – 1:55] PRODUCTS: DEEP-LEVEL INTELLIGENCE

**→ Click Products tab**

> "The AI provides deep intelligence on every item in your catalog. Here you can see each product's category, its reorder point, and its strategic safety stock buffer. We also empower your team by enabling them to set custom business rules and thresholds. The AI then seamlessly integrates this policy, recalculating priorities to align with your specific business strategy."

---

### [1:55 – 2:25] FORECASTING: THE PREDICTIVE ENGINE

**→ Click Forecasting → select a product → Generate Forecast**

> "At the heart of the platform is a powerful predictive engine. When you select a product, the system analyzes its entire sales history and runs it through a suite of advanced forecasting models. It doesn't use a one-size-fits-all approach; it automatically selects the best algorithm—whether it's for seasonal, stable, or volatile demand."

> "The result is a highly accurate 30-day forecast, complete with a confidence range and a clear, AI-generated summary of the expected trend and optimal order quantity."

---

### [2:25 – 2:50] PRICING: MAXIMIZING PROFITABILITY

**→ Click Pricing tab → select a slow-moving product**

> "Finally, let's address overstock. For products that aren't moving, the pricing model calculates the optimal markdown strategy. It analyzes price elasticity and presents scenarios that show the impact on sales, revenue, and—most importantly—net profit. The goal isn't just to clear stock, but to do so in the most profitable way possible."

---

### [2:50 – 3:00] CLOSE: YOUR STRATEGIC ADVANTAGE

> "To summarize: this is a single, unified platform that delivers real-time visibility, automates complex reorder decisions, provides intelligent demand forecasting, and optimizes pricing to protect your margins. It transforms your data into decisive action. Thank you."

---

### TIMING GUIDE

| Section | Duration | Focus |
|:--------|:---------|:------|
| Introduction | 0:00 – 0:20 | Who you are, the core business problem |
| The Data | 0:20 – 0:40 | Using existing assets (data) for intelligence |
| Dashboard — AI Command Center | 0:40 – 1:05 | Real-time, model-driven executive view |
| Alerts — Insight to Action | 1:05 – 1:30 | Automated monitoring and notifications |
| Products — Deep Intelligence | 1:30 – 1:55 | Granular control and custom business rules |
| Forecasting — Predictive Engine | 1:55 – 2:25 | Best-fit models, accurate predictions |
| Pricing — Profitability | 2:25 – 2:50 | Optimal markdowns to maximize net profit |
| Close | 2:50 – 3:00 | Summary of strategic value |
| **Total** | **3:00** | |

*Pace: ~150 wpm. Confident and client-focused.*

---

### IF A CLIENT ASKS BUSINESS QUESTIONS

| Question | Answer |
|:---------|:-------|
| "How long does it take to set up?" | "You upload your products CSV and sales history — the system profiles every product and starts generating recommendations immediately." |
| "Does it connect to our ERP / Shopify?" | "Yes — the API Integration tab supports direct data feeds. It accepts CSV, JSON, or live API pull from any system that can export sales data." |
| "What if our data is messy?" | "The system handles missing values, validates on import, and flags anomalies. It's been tested on real retail data with gaps and irregular sales patterns." |
| "How accurate are the forecasts?" | "Accuracy depends on the product — stable products with strong history generally hit under 15% MAPE. Volatile products have wider confidence bands, which the system communicates explicitly." |
| "Can we control the thresholds?" | "Yes — service levels, reorder thresholds, and alert thresholds are all configurable per product or globally. The AI recommends, you control the policy." |
| "What does it cost to run?" | "Runs on a standard cloud VM. No expensive ML infrastructure — all models run in Python on the backend. Scales horizontally if needed." |
| "Is the data secure?" | "All data stays within your deployment. No third-party ML APIs involved — the models run entirely on your own server." |

---

### IF ASKED TECHNICAL FOLLOW-UPS (for engineers in the room)

| Question | Answer |
|:---------|:-------|
| "What models are running?" | "Holt-Winters, SARIMA, Seasonal Naive, STL+LinearRegression, XGBoost, Prophet, and a Weighted Ensemble — the system uses segment-driven selection." |
| "How does it pick the right model?" | "Each product is classified into a demand segment using its coefficient of variation and sales frequency. The segment maps to a model priority list — the first to converge wins." |
| "What's the EOQ formula?" | "The classic √(2DS/H) — using annual demand, ordering cost, and holding cost per unit. Holding cost is set to 25% of unit cost by default but is overridable." |
| "How is safety stock calculated?" | "Standard formula: z × σ × √(lead time). We use a z-score of 1.645 for a 95% service level. It can switch to a newsvendor model if stockout cost data is available." |
| "What features does XGBoost use?" | "Time-based features like week and month, plus lag demand at 1, 2, 4, and 8 weeks, and rolling averages for demand and volatility." |
| "How is the markdown discount derived?" | "It's based on price elasticity theory. The optimal discount is calculated from the elasticity of the product's category, constrained to a 5–40% range to ensure realistic pricing." |

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
