# 🎬 3-Minute Technical Demo — AI/ML Inventory Optimization Engine

**Start on:** Dashboard (`/`)

---

### [0:00 – 0:15] INTRO
*Dashboard visible*

> "I'm Mohit Rao, Data and AI Engineering, Miracle Software Systems. This is an AI-powered inventory optimization engine — fifty thousand products, two million sales records, seven ML models answering what to order, how much, and when. Let me show you."

---

### [0:15 – 1:10] DASHBOARD

**→ Click Total Products card**

> "Three AI-computed metrics at top. Total Products shows stock distribution — Out of Stock, Low, Medium, High. The Configure Thresholds button adjusts cutoffs live — change Low Stock from 50 to 30, hit Apply, everything recalculates globally."

*(close modal)*

**→ Click Stockout Alerts card**

> "Stockout Alerts shows which products are running out."

*(point to summary cards)*

> "These three cards at the top tell you — how many products are at risk, how many will run out in less than three days, and how much it costs to restock them."

*(point to first table)*

> "This first table lists the most critical products — you can see the product name, how much stock is left, how many days before it runs out, and how many units the system recommends you order."

*(point to second table)*

> "The second table shows the top twenty most urgent items — it also includes daily demand and supplier lead time so you know exactly when to place the order."

*(close modal)*

**→ Point to Sales Trend**

> "Sales Trend — I can view sales by day, week, month, or year, and switch between quantity, revenue, profit, or loss. I can also filter down to a single product. Simple but powerful for spotting patterns."

**→ Scroll down to Inventory Alerts table**

*(point to column headers)*

> "The Alerts table — each row shows product name, current stock, days until stockout, order-by date, and daily revenue loss."

*(point to AI suggestion line)*

> "Under each product, an AI-generated reorder suggestion specific to that product's demand and lead time."

*(point to summary bar)*

> "Summary bar at bottom — total daily loss across all flagged items. That's the cost of doing nothing."

*(point to email section)*

> "Email alerts via SendGrid, plus Slack and Teams webhooks."

---

### [1:10 – 1:35] PRODUCTS

**→ Click Products in navbar**

> "Products page — four stock-tier cards, each a clickable filter."

**→ Click Out of Stock card**

> "Out of Stock shows the Ordering Recommendations — critical items with AI-computed order quantities."

**→ Click any product row**

> "Each product opens an Insight Modal — status badge, an Executive Summary in plain English telling you what's happening and what to do, a KPI table with stock level, reorder point, daily demand, days left, and lead time, and prioritized Suggestions with actions and costs."

---

### [1:35 – 2:15] FORECASTING

**→ Click Forecasting in navbar**

> "This is the demand forecasting page — it predicts how much of a product customers will buy in the future."

**→ Select a product, click Generate Forecast**

> "I pick a product and hit Generate. The system looks at past sales and figures out the pattern — is demand going up, does it repeat every few weeks, or is it random?"

> "Based on that, it automatically picks the best forecasting method. We have seven different models built in — the system tests them and uses whichever one fits this product's pattern best."

*(point to chart)*

> "This chart shows the result. The blue line is what actually sold in the past. The teal dashed line is what the AI predicts will sell going forward. The shaded area is the range — best case to worst case — so you know how confident the prediction is."

*(point to explanation box)*

> "Below the chart, the system gives you a plain-English summary — how much demand to expect, whether it's going up or down, and exactly how many units you should order to stay stocked."

---

### [2:15 – 2:35] MARKDOWN OPTIMIZER

**→ Click Optimization in navbar**

> "Markdown Optimizer. When you have slow-moving inventory, how much should you discount?"

**→ Select a product**

> "The system runs linear regression for trend and a price elasticity model for volume response."

**→ Point to scenario table**

> "Five scenarios — five to forty percent off. Each shows demand lift, units cleared, and net profit."

**→ Point to highlighted row**

> "The AI highlights the sweet spot — where clearance volume still outweighs margin loss. Beyond that, deeper cuts lose money."

---

### [2:35 – 2:45] CLOSE

> "So what you've seen is end-to-end AI for inventory — demand forecasting that picks the right model per product, real-time stockout detection with dollar-level impact, automated reorder recommendations, and markdown optimization to move slow stock profitably. All of this running across fifty thousand SKUs with two million sales records. Happy to take questions."

---

### TIMING GUIDE

| Section              | Duration    |
|:---------------------|:------------|
| Intro                | 0:00 – 0:15 |
| Dashboard            | 0:15 – 1:10 |
| Products             | 1:10 – 1:35 |
| Forecasting          | 1:35 – 2:15 |
| Markdown Optimizer   | 2:15 – 2:35 |
| Close                | 2:35 – 2:45 |
