"""Rule-based + analytics-backed inventory chatbot.

This is designed so you can later plug in a GenAI provider
(e.g., Azure OpenAI) while already having good business logic
for inventory questions and forecasts.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pandas as pd

from ..database.models import Product, SalesHistory
from ..services.analytics_service import AnalyticsService
from ..models.demand_forecaster import DemandForecaster
from ..models.inventory_optimizer import InventoryOptimizer
from ..models.business_advisor import BusinessRecommendationEngine
from ..models.financial_storyteller import FinancialStoryTeller


class InventoryChatbot:
    """Lightweight NLP-ish assistant for inventory Q&A.

    For this POC it uses keyword intents + analytics.
    You can later replace/augment `generate_answer`
    with a large language model.
    """

    def __init__(self, db: Session):
        self.db = db
        self.analytics = AnalyticsService()

    def _get_top_products(self, limit: int = 5) -> List[Dict[str, Any]]:
        cutoff = datetime.utcnow() - timedelta(days=365)
        rows = (
            self.db.query(SalesHistory)
            .filter(SalesHistory.date >= cutoff)
            .all()
        )
        aggregates: Dict[int, Dict[str, Any]] = {}
        for r in rows:
            agg = aggregates.setdefault(
                r.product_id,
                {
                    "product_id": r.product_id,
                    "name": r.product.name if r.product else "Unknown",
                    "sku": r.product.sku if r.product else "",
                    "revenue": 0.0,
                    "units": 0,
                },
            )
            agg["revenue"] += float(r.revenue or 0)
            agg["units"] += int(r.quantity_sold or 0)
        sorted_prods = sorted(aggregates.values(), key=lambda x: x["revenue"], reverse=True)
        return sorted_prods[:limit]

    def _get_stock_snapshot(self) -> Dict[str, Any]:
        products = self.db.query(Product).all()
        total_stock_value = 0.0
        total_units = 0
        out_of_stock = 0
        low_stock = 0

        for p in products:
            units = int(p.current_stock or 0)
            total_units += units
            total_stock_value += units * float(p.unit_cost or 0)
            if units == 0:
                out_of_stock += 1
            elif units <= 50:
                low_stock += 1

        avg_daily_sales = max(total_units / 365.0, 0.1)  # very rough proxy
        days_of_inventory = self.analytics.calculate_days_of_inventory(total_units, avg_daily_sales)

        return {
            "total_products": len(products),
            "total_units": total_units,
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
            "total_stock_value": round(total_stock_value, 2),
            "days_of_inventory": round(days_of_inventory, 1),
        }

    def _find_product(self, text: str) -> Product | None:
        text = text.lower()
        # Try by SKU exact/contains
        product = (
            self.db.query(Product)
            .filter(Product.sku.ilike(f"%{text}%"))
            .first()
        )
        if product:
            return product
        # Try by name contains
        return (
            self.db.query(Product)
            .filter(Product.name.ilike(f"%{text}%"))
            .first()
        )

    def _forecast_for_product(self, product: Product, horizon_days: int) -> Dict[str, Any]:
        """Run DemandForecaster for a given product and horizon."""
        sales_rows = (
            self.db.query(SalesHistory)
            .filter(SalesHistory.product_id == product.id)
            .all()
        )
        if not sales_rows:
            return {
                "answer": f"I couldn't find any sales history for {product.name} (SKU {product.sku}), so I cannot forecast yet.",
                "intent": "product_forecast_no_history",
            }

        df = pd.DataFrame(
            [
                {"date": r.date, "quantity_sold": r.quantity_sold}
                for r in sales_rows
            ]
        )

        forecaster = DemandForecaster(model_type="auto")
        forecaster.fit(df)
        result = forecaster.predict(steps=horizon_days)

        preds = result["predictions"]
        total_forecast = float(sum(preds))
        avg_daily = float(total_forecast / max(horizon_days, 1))
        model_used = result.get("model_used", "Unknown")

        current_stock = int(product.current_stock or 0)
        coverage_days = None
        if avg_daily > 0:
            coverage_days = current_stock / avg_daily

        horizon_label = f"{horizon_days} days"
        if horizon_days == 180:
            horizon_label = "6 months"
        elif horizon_days == 365:
            horizon_label = "12 months"

        base = (
            f"Based on {model_used}, I expect around {total_forecast:.0f} units "
            f"of {product.name} (SKU {product.sku}) over the next {horizon_label}, "
            f"which is about {avg_daily:.1f} units per day. "
        )

        recommendation = ""
        if coverage_days is not None:
            if coverage_days < horizon_days:
                shortage = max(total_forecast - current_stock, 0)
                recommendation = (
                    f"You currently have {current_stock} units on hand, which covers only "
                    f"about {coverage_days:.0f} days of that period. "
                    f"Plan to order roughly {shortage:.0f} additional units across the horizon, "
                    f"taking into account your lead time of {product.lead_time_days} days."
                )
            else:
                recommendation = (
                    f"You currently have {current_stock} units on hand, which should comfortably "
                    f"cover the forecasted demand for this horizon. Monitor trends but no urgent "
                    f"reorder is required based on this forecast alone."
                )

        answer = base + recommendation

        return {
            "answer": answer,
            "intent": "product_forecast",
            "horizon_days": horizon_days,
            "model_used": model_used,
        }

    def _optimize_inventory_for_product(self, product: Product) -> Dict[str, Any]:
        """Run inventory optimization and summarize recommendations."""
        sales_rows = (
            self.db.query(SalesHistory)
            .filter(SalesHistory.product_id == product.id)
            .all()
        )
        if not sales_rows:
            return {
                "answer": f"I don't have sales history for {product.name} (SKU {product.sku}), so I cannot optimize inventory yet.",
                "intent": "inventory_opt_no_history",
            }

        df = pd.DataFrame(
            [
                {"date": r.date, "quantity_sold": r.quantity_sold}
                for r in sales_rows
            ]
        )

        optimizer = InventoryOptimizer()
        rec = optimizer.optimize_inventory(
            df,
            unit_cost=float(product.unit_cost or 0),
            lead_time_days=int(product.lead_time_days or 7),
            service_level=0.95,
        )

        answer = (
            f"For {product.name} (SKU {product.sku}), the optimized reorder point is "
            f"{rec['reorder_point']:.0f} units with safety stock of {rec['safety_stock']:.0f} units. "
            f"The economic order quantity (EOQ) is {rec['economic_order_quantity']:.0f} units, "
            f"leading to an optimal on-hand stock level of {rec['optimal_stock_level']:.0f} units. "
            f"At this policy, we expect about {rec['inventory_turnover']:.1f} inventory turns per year "
            f"and approximately ${rec['estimated_annual_savings']:,.0f} in annual holding cost savings "
            f"versus a less optimized policy."
        )

        return {"answer": answer, "intent": "inventory_optimization", "details": rec}

    def _financial_story_for_product(self, product: Product, recommended_order_qty: float) -> Dict[str, Any]:
        """Generate a financial story for an ordering decision using FinancialStoryTeller."""
        sales_rows = (
            self.db.query(SalesHistory)
            .filter(SalesHistory.product_id == product.id)
            .all()
        )
        if not sales_rows:
            return {
                "answer": f"I can't build a financial story for {product.name} yet because there is no sales history.",
                "intent": "financial_story_no_history",
            }

        df = pd.DataFrame(
            [
                {"date": r.date, "quantity_sold": r.quantity_sold}
                for r in sales_rows
            ]
        )
        annual_demand = (
            df["quantity_sold"].sum()
            / max(1, len(df.groupby("date")))
            * 365
        )

        current_situation = {
            "current_stock": int(product.current_stock or 0),
            "annual_demand": float(annual_demand),
            "unit_cost": float(product.unit_cost or 0),
            "unit_price": float(product.unit_price or 0),
            "historical_stockout_pct": 2.0,
        }

        ai_recommendation = {
            "recommended_order_qty": float(recommended_order_qty),
            "service_level": 0.95,
            "safety_stock": float(recommended_order_qty) * 0.3,
        }

        storyteller = FinancialStoryTeller()
        story = storyteller.tell_decision_story(
            product.name,
            current_situation,
            ai_recommendation,
        )

        headline = story["executive_summary"]["headline"]
        cfo_summary = story["executive_summary"]["cfo_summary"]

        answer = (
            f"Financially, acting on the AI order recommendation for {product.name} "
            f"results in: {headline} {cfo_summary}."
        )

        return {"answer": answer, "intent": "financial_story", "story": story}

    def generate_answer(self, question: str) -> Dict[str, Any]:
        q = (question or "").strip()
        if not q:
            return {
                "answer": "Please ask me about stock levels, sales trends, or top products.",
                "intent": "clarification",
            }

        q_lower = q.lower()

        # 1) High-level stock health
        if any(k in q_lower for k in ["inventory", "stock overall", "overall stock", "how is my stock"]):
            snapshot = self._get_stock_snapshot()
            answer = (
                f"You currently have {snapshot['total_products']} active products with "
                f"{snapshot['total_units']} units on hand. "
                f"{snapshot['out_of_stock']} are out of stock and {snapshot['low_stock']} are low. "
                f"Total stock value is about ${snapshot['total_stock_value']:.0f}, "
                f"with roughly {snapshot['days_of_inventory']} days of inventory coverage."
            )
            return {"answer": answer, "intent": "inventory_overview", "snapshot": snapshot}

        # 2) Explicit out-of-stock list
        if "out of stock" in q_lower or "stockout" in q_lower or "stock out" in q_lower:
            out_products = self.db.query(Product).filter(Product.current_stock == 0).all()
            if not out_products:
                return {
                    "answer": "Great news: no products are currently out of stock.",
                    "intent": "out_of_stock_list",
                }
            lines = []
            for p in out_products:
                lines.append(f"- {p.sku} - {p.name}")
            answer = "These products are currently out of stock:\n" + "\n".join(lines)
            return {"answer": answer, "intent": "out_of_stock_list", "count": len(out_products)}

        # 3) Forecast questions (e.g., next 30 days / 6 months / 1 year)
        if any(k in q_lower for k in ["next", "forecast", "prediction", "predict", "future sales"]):
            # Determine horizon
            horizon_days = 30
            if "6 month" in q_lower or "six month" in q_lower:
                horizon_days = 180
            elif "year" in q_lower or "12 month" in q_lower or "one year" in q_lower:
                horizon_days = 365
            elif "90 day" in q_lower or "3 month" in q_lower:
                horizon_days = 90
            elif "30 day" in q_lower:
                horizon_days = 30

            # Try to detect a product from the question (SKU or name)
            tokens = [t for t in q_lower.replace("?", "").split() if len(t) >= 3]
            target_product = None
            for t in tokens:
                prod = self._find_product(t)
                if prod:
                    target_product = prod
                    break

            if not target_product:
                return {
                    "answer": "Please mention a specific product or SKU, for example 'ELEC002', so I can forecast its future sales.",
                    "intent": "product_forecast_missing_product",
                }

            return self._forecast_for_product(target_product, horizon_days)

        # 4) Optimization / recommendation questions
        if any(k in q_lower for k in ["optimize", "optimization", "reorder point", "safety stock", "eoq", "order quantity", "recommendation"]):
            tokens = [t for t in q_lower.replace("?", "").split() if len(t) >= 3]
            target_product = None
            for t in tokens:
                prod = self._find_product(t)
                if prod:
                    target_product = prod
                    break

            if target_product:
                return self._optimize_inventory_for_product(target_product)

        # 5) Top sellers
        if "top" in q_lower or "best seller" in q_lower or "best-selling" in q_lower:
            top = self._get_top_products(limit=5)
            if not top:
                return {"answer": "I couldn't find any sales history yet.", "intent": "top_products"}
            lines = []
            for i, p in enumerate(top, start=1):
                lines.append(
                    f"{i}. {p['sku']} - {p['name']} (revenue ${p['revenue']:.0f}, units {p['units']})"
                )
            answer = "Here are your top products by revenue over the last 12 months:\n" + "\n".join(lines)
            return {"answer": answer, "intent": "top_products", "items": top}

        # 6) Product-specific stock question
        if ("stock" in q_lower or "on hand" in q_lower or "available" in q_lower) and "out of stock" not in q_lower:
            # Try to detect a product token (very simple heuristic)
            tokens = [t for t in q_lower.replace("?", "").split() if len(t) >= 3]
            candidate = None
            for t in tokens:
                prod = self._find_product(t)
                if prod:
                    candidate = prod
                    break
            if candidate:
                answer = (
                    f"{candidate.name} (SKU {candidate.sku}) currently has "
                    f"{candidate.current_stock} units in stock. Lead time is "
                    f"{candidate.lead_time_days} days and unit cost is ${candidate.unit_cost:.2f}."
                )
                return {
                    "answer": answer,
                    "intent": "product_stock",
                    "product": {
                        "id": candidate.id,
                        "sku": candidate.sku,
                        "name": candidate.name,
                        "current_stock": candidate.current_stock,
                        "lead_time_days": candidate.lead_time_days,
                        "unit_cost": candidate.unit_cost,
                        "unit_price": candidate.unit_price,
                    },
                }

            # 7) Generic description of AI capabilities
        if "what can you do" in q_lower or "help" in q_lower:
            return {
                "answer": (
                    "I can answer questions about stock levels, top-selling products, "
                    "and overall inventory health. This assistant can also be wired "
                    "to a GenAI model (e.g., Azure OpenAI) to provide richer natural "
                    "language answers using your data."
                ),
                "intent": "capabilities",
            }

        # Fallback generic answer
        return {
            "answer": (
                "I didn't fully understand that. Try asking things like "
                "'Which products are top sellers?', 'How is my inventory overall?', "
                "or 'How many units of ICE_CREAM are in stock?'."
            ),
            "intent": "fallback",
        }
